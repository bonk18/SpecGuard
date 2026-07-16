"""Offline tests for the refinery-safety knowledge-base foundation."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.rag.chunker import chunk_pages
from app.rag.document_loader import DocumentLoadError, load_document
from app.rag.embedder import DeterministicEmbedder
from app.rag.metadata import enrich_chunks, load_manifest
from app.rag.models import DocumentPage, RetrievalQuery, RetrievalResult, SourceDocument
from app.rag.retriever import Retriever, risk_to_retrieval_query
from app.rag.text_cleaner import clean_pages, clean_text
from app.rag.vector_store import JsonVectorStore
from app.schemas import RiskEngineInput, RiskType


ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "backend/data/knowledge/manifests/documents.json"


def sample_page(text: str, page_number: int = 1) -> DocumentPage:
    return DocumentPage(
        document_id="DOC-1",
        page_number=page_number,
        text=text,
        source_title="Local safety note",
        source_path="fixture.md",
        document_type="SOP",
        authority="Test authority",
    )


def sample_risk() -> RiskEngineInput:
    return RiskEngineInput(
        alert_id="ALT-1",
        timestamp="2026-07-16T09:30:00Z",
        zone_id="ZONE_B",
        equipment_ids=["P-101"],
        risk_type="FIRE_EXPLOSION",
        risk_score=0.9,
        severity="CRITICAL",
        predicted_incident="Hydrocarbon flash fire",
        contributing_factors=[
            "RISING_LEL",
            "HOT_WORK_ACTIVE",
            "VENTILATION_FAILURE",
            "WORKERS_PRESENT",
        ],
        sensor_evidence={"lel": 8.4},
        active_permit_ids=["PTW-1"],
    )


def test_markdown_loading_and_provenance(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    path.write_text("# Heading\n\nMust not start work without a permit.", encoding="utf-8")
    document = SourceDocument(
        document_id="DOC-1",
        title="Local note",
        document_type="SOP",
        source_path=str(path),
    )

    pages = load_document(document)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].source_path == str(path)


def test_text_loading_and_empty_file_handling(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("A text source", encoding="utf-8")
    document = SourceDocument(document_id="DOC-1", title="Text", document_type="SOP", source_path=str(path))
    assert load_document(document)[0].text == "A text source"

    empty = tmp_path / "empty.txt"
    empty.touch()
    with pytest.raises(DocumentLoadError):
        load_document(document.model_copy(update={"source_path": str(empty)}))


def test_pdf_loading_preserves_page_numbers_without_network(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakeReader:
        def __init__(self, _: str) -> None:
            self.pages = [FakePage("Page one"), FakePage("Page two")]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakeReader))
    path = tmp_path / "note.pdf"
    path.write_bytes(b"%PDF-test")
    document = SourceDocument(document_id="DOC-1", title="PDF", document_type="REGULATION", source_path=str(path))

    pages = load_document(document)

    assert [page.page_number for page in pages] == [1, 2]


def test_unsupported_and_missing_file_handling(tmp_path: Path) -> None:
    document = SourceDocument(document_id="DOC-1", title="Unknown", document_type="SOP", source_path=str(tmp_path / "a.docx"))
    with pytest.raises(DocumentLoadError, match="does not exist"):
        load_document(document)
    path = tmp_path / "a.docx"
    path.write_text("content", encoding="utf-8")
    with pytest.raises(DocumentLoadError, match="Unsupported"):
        load_document(document.model_copy(update={"source_path": str(path)}))


def test_cleaning_is_conservative_and_removes_repeated_page_lines() -> None:
    assert clean_text("must   not\x00\n\n\nbe removed") == "must not\n\nbe removed"
    pages = clean_pages([sample_page("HEADER\n\nKeep this must not clause\nFOOTER", 1), sample_page("HEADER\n\nAnother clause\nFOOTER", 2)])
    assert all("HEADER" not in page.text and "FOOTER" not in page.text for page in pages)
    assert "must not" in pages[0].text


def test_chunk_ids_are_deterministic_and_overlap_is_present() -> None:
    text = " ".join(f"word{i}" for i in range(30))
    first = chunk_pages([sample_page(text)], max_tokens=10, overlap_tokens=3)
    second = chunk_pages([sample_page(text)], max_tokens=10, overlap_tokens=3)

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert len(first) > 1
    assert set(first[0].text.split()[-3:]).intersection(first[1].text.split()[:3])
    assert all(chunk.text.strip() for chunk in first)


def test_manifest_parsing_and_metadata_keyword_tagging() -> None:
    entries = load_manifest(MANIFEST)
    assert len(entries) == 6
    assert all(entry.is_synthetic for entry in entries)
    chunks = enrich_chunks(
        chunk_pages(
            [
                sample_page(
                    "Hot work permit is active. Rising LEL and ventilation failure are observed while workers are present."
                )
            ]
        )
    )
    assert "RISING_LEL" in {value.value for value in chunks[0].hazard_codes}
    assert "HOT_WORK" in {value.value for value in chunks[0].permit_types}


def test_retrieval_models_reject_invalid_scores() -> None:
    with pytest.raises(ValidationError):
        RetrievalResult(
            chunk_id="C-1",
            text="A useful evidence passage.",
            similarity_score=1.1,
            source_title="Source",
            page_start=1,
            page_end=1,
        )
    with pytest.raises(ValidationError):
        RetrievalQuery(query_text="valid query", top_k=21)


def test_vector_store_insertion_retrieval_and_filters(tmp_path: Path) -> None:
    pages = [
        sample_page("Hot work permit controls require gas testing and a fire watch."),
        DocumentPage(
            document_id="DOC-2",
            page_number=1,
            text="A historical incident involved an electrical failure.",
            source_title="Incident record",
            source_path="incident.md",
            document_type="HISTORICAL_INCIDENT",
        ),
    ]
    chunks = []
    for page_group in ([pages[0]], [pages[1]]):
        chunks.extend(enrich_chunks(chunk_pages(page_group)))
    store = JsonVectorStore(tmp_path / "store.json")
    embedder = DeterministicEmbedder()
    store.add(chunks, embedder.embed([chunk.text for chunk in chunks]))
    retriever = Retriever(store, embedder)

    results = retriever.retrieve("hot work gas testing", mode="regulations_and_sops")

    assert results
    assert all(result.metadata["document_type"] == "SOP" for result in results)
    assert "gas testing" in results[0].text.lower()
    risk_results = retriever.retrieve(
        RetrievalQuery(query_text="fire controls", risk_types=[RiskType.FIRE_EXPLOSION]),
        mode="all",
    )
    assert risk_results
    assert all("FIRE_EXPLOSION" in result.metadata["risk_types"] for result in risk_results)


def test_risk_engine_input_becomes_retrieval_query() -> None:
    query = risk_to_retrieval_query(sample_risk())
    assert "pump station" in query.query_text
    assert "hot work is active" in query.query_text
    assert query.risk_types[0].value == "FIRE_EXPLOSION"


def test_synthetic_hot_work_retrieval(tmp_path: Path) -> None:
    entries = load_manifest(MANIFEST)
    chunks = []
    for entry in entries:
        pages = clean_pages(load_document(entry.to_source_document(), ROOT))
        chunks.extend(enrich_chunks(chunk_pages(pages)))
    embedder = DeterministicEmbedder()
    store = JsonVectorStore(tmp_path / "synthetic-store.json")
    store.add(chunks, embedder.embed([chunk.text for chunk in chunks]))

    results = Retriever(store, embedder).retrieve(risk_to_retrieval_query(sample_risk()), mode="regulations_and_sops")

    assert results
    assert any("hot work" in result.text.lower() for result in results)
    assert all(result.source_title for result in results)

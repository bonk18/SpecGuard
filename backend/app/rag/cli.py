"""Command-line entry point for local knowledge-base ingestion and queries."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import os
from pathlib import Path

from app.rag.chunker import chunk_pages
from app.rag.document_loader import DocumentLoadError, load_document
from app.rag.embedder import DeterministicEmbedder, Embedder, SentenceTransformerEmbedder
from app.rag.metadata import enrich_chunks, load_manifest
from app.rag.models import RetrievalQuery
from app.rag.retriever import Retriever
from app.rag.text_cleaner import clean_pages
from app.rag.vector_store import JsonVectorStore
from app.schemas.common import HazardCode, PermitType, RiskType


REPO_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_ROOT = REPO_ROOT / "backend/data/knowledge"
DEFAULT_MANIFEST = KNOWLEDGE_ROOT / "manifests/documents.json"
DEFAULT_STORE = KNOWLEDGE_ROOT / "vector_store/chunks.json"


@dataclass
class IngestionSummary:
    """Counts and diagnostics emitted by one deterministic ingestion run."""

    documents_total: int = 0
    documents_loaded: int = 0
    documents_skipped: int = 0
    missing_files: int = 0
    extraction_failures: int = 0
    empty_extractions: int = 0
    chunks_created: int = 0
    chunks_indexed: int = 0
    persisted_chunks: int = 0
    skipped_messages: list[str] = field(default_factory=list)


def _embedder(name: str | None) -> Embedder:
    selected = name or os.getenv("RAG_EMBEDDER", "deterministic")
    if selected == "deterministic":
        return DeterministicEmbedder()
    if selected == "sentence-transformers":
        return SentenceTransformerEmbedder()
    raise ValueError(
        "embedder must be deterministic or sentence-transformers; "
        "set RAG_EMBEDDER or pass --embedder"
    )


def _source_root(manifest_path: Path) -> Path:
    """Resolve manifest paths such as ``raw/regulations/file.pdf``."""

    return manifest_path.resolve().parent.parent


def ingest_documents(
    manifest_path: Path,
    store_path: Path,
    *,
    rebuild: bool,
    embedder_name: str | None,
) -> IngestionSummary:
    entries = load_manifest(manifest_path)
    summary = IngestionSummary(documents_total=len(entries))
    chunks = []
    processed_document_ids: list[str] = []

    for entry in entries:
        if not entry.local_path:
            summary.skipped_messages.append(f"{entry.document_id}: no local_path in manifest")
            continue
        try:
            loaded = load_document(entry.to_source_document(), base_dir=_source_root(manifest_path))
        except DocumentLoadError as exc:
            message = f"{entry.document_id}: {exc}"
            summary.skipped_messages.append(message)
            if "does not exist" in str(exc):
                summary.missing_files += 1
            elif "contains no text" in str(exc) or "no extractable" in str(exc):
                summary.empty_extractions += 1
                summary.extraction_failures += 1
            else:
                summary.extraction_failures += 1
            continue

        if not loaded:
            summary.empty_extractions += 1
            summary.extraction_failures += 1
            summary.skipped_messages.append(
                f"{entry.document_id}: no extractable text; scanned PDFs need manual OCR review"
            )
            continue

        summary.documents_loaded += 1
        processed_document_ids.append(entry.document_id)
        cleaned = clean_pages(loaded)
        chunks.extend(enrich_chunks(chunk_pages(cleaned)))

    summary.chunks_created = len(chunks)
    embedder = _embedder(embedder_name)
    embeddings = embedder.embed([chunk.text for chunk in chunks])
    store = JsonVectorStore(store_path)
    if rebuild:
        store.rebuild(chunks, embeddings)
    else:
        # Replace successfully reprocessed documents so repeated ingestion is
        # idempotent even if a document's chunk boundaries have changed.
        store.delete_documents(processed_document_ids)
        store.add(chunks, embeddings)
    summary.documents_skipped = len(summary.skipped_messages)
    summary.chunks_indexed = len(chunks)
    summary.persisted_chunks = store.count
    return summary


def _print_summary(summary: IngestionSummary) -> None:
    print("Ingestion summary:")
    print(f"  Documents loaded: {summary.documents_loaded}/{summary.documents_total}")
    print(f"  Documents skipped: {summary.documents_skipped}")
    print(f"  Missing files: {summary.missing_files}")
    print(f"  Extraction failures: {summary.extraction_failures}")
    print(f"  Chunks created: {summary.chunks_created}")
    print(f"  Chunks indexed: {summary.chunks_indexed}")
    print(f"  Persisted chunks: {summary.persisted_chunks}")
    for message in summary.skipped_messages:
        print(f"  Skipped: {message}")


def ingest(
    manifest_path: Path,
    store_path: Path,
    *,
    rebuild: bool,
    embedder_name: str | None,
) -> int:
    _print_summary(
        ingest_documents(
            manifest_path,
            store_path,
            rebuild=rebuild,
            embedder_name=embedder_name,
        )
    )
    return 0


def inspect(manifest_path: Path, store_path: Path) -> int:
    entries = load_manifest(manifest_path)
    store = JsonVectorStore(store_path)
    print(f"Manifest entries: {len(entries)}")
    print(f"Persisted chunks: {store.count}")
    print(f"Embedding dimension: {store.embedding_dimension or 'none'}")
    for entry in entries:
        print(f"- {entry.document_id}: {entry.processing_status} ({entry.local_path or 'not added'})")
    return 0


def query(
    text: str,
    store_path: Path,
    *,
    top_k: int,
    mode: str,
    embedder_name: str | None,
    risk_types: list[str] | None = None,
    hazard_codes: list[str] | None = None,
    permit_types: list[str] | None = None,
    document_types: list[str] | None = None,
) -> int:
    retrieval_query = RetrievalQuery(
        query_text=text,
        top_k=top_k,
        risk_types=[RiskType(value) for value in risk_types or []],
        hazard_codes=[HazardCode(value) for value in hazard_codes or []],
        permit_types=[PermitType(value) for value in permit_types or []],
        document_types=document_types or [],
    )
    retriever = Retriever(JsonVectorStore(store_path), _embedder(embedder_name))
    results = retriever.retrieve(retrieval_query, mode=mode)
    if not results:
        print("No matching evidence found.")
        return 0
    for result in results:
        pages = (
            f"p. {result.page_start}"
            if result.page_start == result.page_end
            else f"pp. {result.page_start}-{result.page_end}"
        )
        source = result.source_path or result.source_url or "source unavailable"
        print(
            f"[final={(result.final_score if result.final_score is not None else result.similarity_score):.3f}; "
            f"raw={result.similarity_score:.3f}] {result.source_title} "
            f"({pages}; {result.document_type}; synthetic={result.is_synthetic}; source={source})"
        )
        if result.section:
            print(f"Section: {result.section}")
        print(result.text)
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SpecGuard refinery-safety knowledge-base tools")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    embedder_choices = ["deterministic", "sentence-transformers"]
    parser.add_argument("--embedder", choices=embedder_choices, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="load and index authorized local documents")
    ingest_parser.add_argument("--rebuild", action="store_true", help="replace the existing collection")
    ingest_parser.add_argument("--embedder", choices=embedder_choices, default=argparse.SUPPRESS)

    subparsers.add_parser("inspect", help="show manifest and vector-store status")

    query_parser = subparsers.add_parser("query", help="retrieve evidence for a natural-language query")
    query_parser.add_argument("query_text")
    query_parser.add_argument("--top-k", type=int, default=5)
    query_parser.add_argument(
        "--mode",
        choices=["regulations_and_sops", "similar_incidents", "all"],
        default="all",
    )
    query_parser.add_argument("--risk-type", action="append", choices=[value.value for value in RiskType])
    query_parser.add_argument("--hazard", action="append", choices=[value.value for value in HazardCode])
    query_parser.add_argument("--permit-type", action="append", choices=[value.value for value in PermitType])
    query_parser.add_argument("--document-type", action="append")
    query_parser.add_argument("--embedder", choices=embedder_choices, default=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "ingest":
        return ingest(args.manifest, args.store, rebuild=args.rebuild, embedder_name=args.embedder)
    if args.command == "inspect":
        return inspect(args.manifest, args.store)
    return query(
        args.query_text,
        args.store,
        top_k=args.top_k,
        mode=args.mode,
        embedder_name=args.embedder,
        risk_types=args.risk_type,
        hazard_codes=args.hazard,
        permit_types=args.permit_type,
        document_types=args.document_type,
    )


if __name__ == "__main__":
    raise SystemExit(main())

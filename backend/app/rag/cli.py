"""Command-line entry point for local knowledge-base ingestion and queries."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.rag.chunker import chunk_pages
from app.rag.document_loader import load_document
from app.rag.embedder import DeterministicEmbedder, Embedder, SentenceTransformerEmbedder
from app.rag.metadata import enrich_chunks, load_manifest
from app.rag.retriever import Retriever
from app.rag.text_cleaner import clean_pages
from app.rag.vector_store import JsonVectorStore


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = REPO_ROOT / "backend/data/knowledge/manifests/documents.json"
DEFAULT_STORE = REPO_ROOT / "backend/data/knowledge/vector_store/chunks.json"


def _embedder(name: str) -> Embedder:
    if name == "deterministic":
        return DeterministicEmbedder()
    if name == "sentence-transformers":
        return SentenceTransformerEmbedder()
    raise ValueError("embedder must be deterministic or sentence-transformers")


def ingest(manifest_path: Path, store_path: Path, *, rebuild: bool, embedder_name: str) -> int:
    entries = load_manifest(manifest_path)
    chunks = []
    skipped: list[str] = []
    for entry in entries:
        if not entry.local_path:
            skipped.append(f"{entry.document_id}: no local_path in manifest")
            continue
        try:
            loaded = load_document(entry.to_source_document(), base_dir=REPO_ROOT)
        except Exception as exc:
            skipped.append(f"{entry.document_id}: {exc}")
            continue
        if not loaded:
            skipped.append(
                f"{entry.document_id}: no extractable text; scanned PDFs need manual OCR review"
            )
            continue
        cleaned = clean_pages(loaded)
        chunks.extend(enrich_chunks(chunk_pages(cleaned)))
    embedder = _embedder(embedder_name)
    embeddings = embedder.embed([chunk.text for chunk in chunks])
    store = JsonVectorStore(store_path)
    if rebuild:
        store.rebuild(chunks, embeddings)
    else:
        store.add(chunks, embeddings)
    print(f"Ingested {len(chunks)} chunks from {len(entries)} manifest entries.")
    for message in skipped:
        print(f"Skipped: {message}")
    return 0


def inspect(manifest_path: Path, store_path: Path) -> int:
    entries = load_manifest(manifest_path)
    store = JsonVectorStore(store_path)
    print(f"Manifest entries: {len(entries)}")
    print(f"Persisted chunks: {store.count}")
    for entry in entries:
        print(f"- {entry.document_id}: {entry.processing_status} ({entry.local_path or 'not added'})")
    return 0


def query(text: str, store_path: Path, *, top_k: int, mode: str, embedder_name: str) -> int:
    retriever = Retriever(JsonVectorStore(store_path), _embedder(embedder_name))
    results = retriever.retrieve(text, mode=mode, top_k=top_k)
    if not results:
        print("No matching evidence found.")
        return 0
    for result in results:
        pages = f"p. {result.page_start}" if result.page_start == result.page_end else f"pp. {result.page_start}-{result.page_end}"
        print(f"[{result.similarity_score:.3f}] {result.source_title} ({pages})")
        print(result.text)
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SpecGuard refinery-safety knowledge-base tools")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--embedder", choices=["deterministic", "sentence-transformers"], default="deterministic")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="load and index authorized local documents")
    ingest_parser.add_argument("--rebuild", action="store_true", help="replace the existing collection")

    subparsers.add_parser("inspect", help="show manifest and vector-store status")

    query_parser = subparsers.add_parser("query", help="retrieve evidence for a natural-language query")
    query_parser.add_argument("query_text")
    query_parser.add_argument("--top-k", type=int, default=5)
    query_parser.add_argument("--mode", choices=["regulations_and_sops", "similar_incidents", "all"], default="all")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "ingest":
        return ingest(args.manifest, args.store, rebuild=args.rebuild, embedder_name=args.embedder)
    if args.command == "inspect":
        return inspect(args.manifest, args.store)
    return query(args.query_text, args.store, top_k=args.top_k, mode=args.mode, embedder_name=args.embedder)


if __name__ == "__main__":
    raise SystemExit(main())

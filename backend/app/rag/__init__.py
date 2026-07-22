"""Document ingestion and evidence retrieval primitives for SpecGuard."""

from app.rag.chunker import chunk_pages
from app.rag.embedder import DeterministicEmbedder, SentenceTransformerEmbedder
from app.rag.metadata import enrich_chunks, load_manifest
from app.rag.models import (
    DocumentChunk,
    DocumentPage,
    ManifestEntry,
    RetrievalQuery,
    RetrievalResult,
    SourceDocument,
)
from app.rag.retriever import RerankConfig, Retriever, risk_to_retrieval_query
from app.rag.vector_store import JsonVectorStore

__all__ = [
    "DeterministicEmbedder",
    "DocumentChunk",
    "DocumentPage",
    "JsonVectorStore",
    "ManifestEntry",
    "RetrievalQuery",
    "RetrievalResult",
    "RerankConfig",
    "Retriever",
    "SentenceTransformerEmbedder",
    "SourceDocument",
    "chunk_pages",
    "enrich_chunks",
    "load_manifest",
    "risk_to_retrieval_query",
]

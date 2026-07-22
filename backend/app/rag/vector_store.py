"""Persistent vector-store abstraction with a dependency-free JSON backend."""

from __future__ import annotations

import json
import math
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.rag.models import DocumentChunk, RetrievalResult


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions do not match")
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    # Cosine may be negative; retrieval scores are exposed as a relevance range.
    return max(0.0, min(1.0, numerator / (left_norm * right_norm)))


class VectorStore(ABC):
    """Backend-neutral operations needed by the retriever."""

    @abstractmethod
    def add(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_documents(self, document_ids: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        embedding: list[float],
        *,
        top_k: int,
        filters: dict[str, list[str]] | None = None,
    ) -> list[RetrievalResult]:
        raise NotImplementedError


class JsonVectorStore(VectorStore):
    """Small persistent store used when Chroma is not part of the project.

    The file format is intentionally inspectable. A future Chroma adapter can
    implement the same ``VectorStore`` interface without changing the retriever.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._records: list[dict[str, Any]] = []
        self._embedding_dimension: int | None = None
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Vector store must contain a JSON array: {self.path}")
        self._records = payload
        dimensions = {len(record.get("embedding", [])) for record in self._records}
        if len(dimensions) > 1 or (dimensions and 0 in dimensions):
            raise ValueError(f"Vector store contains inconsistent or empty embeddings: {self.path}")
        self._embedding_dimension = next(iter(dimensions), None)

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._records, indent=2), encoding="utf-8")

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def embedding_dimension(self) -> int | None:
        return self._embedding_dimension

    def add(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must have exactly one embedding")
        if not chunks:
            return
        dimensions = {len(embedding) for embedding in embeddings}
        if not dimensions or 0 in dimensions or len(dimensions) != 1:
            raise ValueError("All embeddings must be non-empty and have one shared dimension")
        dimension = next(iter(dimensions))
        if self._embedding_dimension is not None and dimension != self._embedding_dimension:
            raise ValueError(
                f"Embedding dimension {dimension} does not match store dimension "
                f"{self._embedding_dimension}"
            )
        by_id = {record["chunk"]["chunk_id"]: record for record in self._records}
        for chunk, embedding in zip(chunks, embeddings):
            if not embedding:
                raise ValueError(f"Embedding is empty for chunk {chunk.chunk_id}")
            by_id[chunk.chunk_id] = {
                "chunk": chunk.model_dump(mode="json"),
                "embedding": [float(value) for value in embedding],
            }
        self._records = list(by_id.values())
        self._embedding_dimension = dimension
        self._persist()

    def rebuild(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        self._records = []
        self._embedding_dimension = None
        if not chunks:
            self._persist()
            return
        self.add(chunks, embeddings)

    def delete_documents(self, document_ids: list[str]) -> None:
        targets = set(document_ids)
        self._records = [
            record for record in self._records if record["chunk"].get("document_id") not in targets
        ]
        self._persist()

    @staticmethod
    def _matches(chunk: DocumentChunk, filters: dict[str, list[str]]) -> bool:
        for key, wanted in filters.items():
            if not wanted:
                continue
            if key == "document_type":
                if chunk.document_type.upper() not in {value.upper() for value in wanted}:
                    return False
                continue
            values = {
                str(value.value if hasattr(value, "value") else value).upper()
                for value in getattr(chunk, key, [])
            }
            # A risk query commonly contains several contributing hazards. A
            # chunk matching any requested value is useful evidence; requiring
            # every tag would hide focused SOP sections that cover one control.
            if not values.intersection({value.upper() for value in wanted}):
                return False
        return True

    def query(
        self,
        embedding: list[float],
        *,
        top_k: int,
        filters: dict[str, list[str]] | None = None,
    ) -> list[RetrievalResult]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        results: list[RetrievalResult] = []
        for record in self._records:
            chunk = DocumentChunk.model_validate(record["chunk"])
            if filters and not self._matches(chunk, filters):
                continue
            score = _cosine(embedding, [float(value) for value in record["embedding"]])
            metadata = chunk.model_dump(mode="json")
            results.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    similarity_score=score,
                    final_score=score,
                    metadata=metadata,
                    source_title=chunk.document_title,
                    source_url=chunk.source_url,
                    source_path=chunk.source_path,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section=chunk.section,
                    document_type=chunk.document_type,
                    is_synthetic=chunk.is_synthetic,
                )
            )
        results.sort(key=lambda result: (-result.similarity_score, result.chunk_id))
        return results[:top_k]

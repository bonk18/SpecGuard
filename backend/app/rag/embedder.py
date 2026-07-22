"""Embedding interfaces with an offline deterministic implementation."""

from __future__ import annotations

import hashlib
import math
import os
import re
from abc import ABC, abstractmethod
from collections.abc import Sequence


class Embedder(ABC):
    """Small interface allowing tests and production models to be swapped."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError


class DeterministicEmbedder(Embedder):
    """A hash-based local embedder for tests and demos without internet access."""

    def __init__(self, dimension: int = 128) -> None:
        if dimension < 8:
            raise ValueError("dimension must be at least 8")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self._dimension
            tokens = re.findall(r"[a-z0-9_]+", text.lower()) or ["<empty>"]
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % self._dimension
                sign = 1.0 if digest[4] & 1 else -1.0
                vector[index] += sign
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors


class SentenceTransformerEmbedder(Embedder):
    """Optional local Sentence Transformers adapter.

    The model is loaded lazily by the dependency, so importing this module does
    not force a large ML install. Downloads are controlled by the user's local
    environment and are never required by the offline tests.
    """

    def __init__(self, model_name: str | None = None, batch_size: int | None = None) -> None:
        name = model_name or os.getenv(
            "RAG_EMBEDDING_MODEL",
            os.getenv("SPECGUARD_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        )
        configured_batch_size = (
            batch_size
            if batch_size is not None
            else int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "32"))
        )
        if configured_batch_size < 1:
            raise ValueError("batch_size must be positive")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Sentence Transformers is not installed. Use DeterministicEmbedder "
                "for offline tests or install the optional ML dependencies."
            ) from exc
        try:
            self._model = SentenceTransformer(name)
        except Exception as exc:
            raise RuntimeError(
                f"Could not load embedding model {name!r}. Check local model access "
                "or use the deterministic embedder."
            ) from exc
        self.model_name = name
        self.batch_size = configured_batch_size
        self._dimension = int(self._model.get_sentence_embedding_dimension())

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        encoded = self._model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        vectors = [list(map(float, vector)) for vector in encoded]
        if any(len(vector) != self.dimension for vector in vectors):
            raise RuntimeError(
                f"Embedding model returned an unexpected vector dimension; expected {self.dimension}."
            )
        return vectors

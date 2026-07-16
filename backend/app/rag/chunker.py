"""Deterministic, section-aware chunking for extracted document pages."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.rag.models import DocumentChunk, DocumentPage


DEFAULT_MAX_TOKENS = 700
DEFAULT_OVERLAP_TOKENS = 120
_HEADING = re.compile(r"^(?:#{1,6}\s+|\d+(?:\.\d+)*\s+)(.+?)\s*$")


@dataclass(frozen=True)
class _Unit:
    words: tuple[str, ...]
    page_number: int
    section: str | None


def _section_name(line: str) -> str | None:
    match = _HEADING.match(line.strip())
    if not match:
        return None
    value = match.group(1).strip().strip("#").strip()
    return value or None


def _units(pages: list[DocumentPage]) -> list[_Unit]:
    result: list[_Unit] = []
    for page in pages:
        section: str | None = None
        paragraph: list[str] = []

        def flush() -> None:
            if paragraph:
                result.append(_Unit(tuple(" ".join(paragraph).split()), page.page_number, section))
                paragraph.clear()

        for line in page.text.splitlines():
            heading = _section_name(line)
            if heading:
                flush()
                section = heading
                continue
            if not line.strip():
                flush()
                continue
            paragraph.append(line.strip())
        flush()
    return result


def _chunk_id(document_id: str, index: int, text: str) -> str:
    digest = hashlib.sha1(f"{document_id}:{index}:{text}".encode("utf-8")).hexdigest()[:16]
    return f"{document_id}-chunk-{index:04d}-{digest}"


def chunk_pages(
    pages: list[DocumentPage],
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[DocumentChunk]:
    """Chunk pages using word counts as a transparent token approximation.

    A tokenizer is intentionally not required for the prototype. The overlap
    is carried from the previous chunk so a safety condition split at a boundary
    remains visible to the next retrieval result.
    """

    if max_tokens < 1:
        raise ValueError("max_tokens must be positive")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be between zero and max_tokens - 1")
    if not pages:
        return []
    document_ids = {page.document_id for page in pages}
    if len(document_ids) != 1:
        raise ValueError("chunk_pages accepts pages from one document at a time")

    units = _units(pages)
    if not units:
        return []
    document = pages[0]
    chunks: list[DocumentChunk] = []
    current: list[_Unit] = []
    current_words = 0

    def emit(items: list[_Unit]) -> None:
        if not items:
            return
        text = " ".join(word for item in items for word in item.words).strip()
        if len(text.split()) < 3 or len(text) < 10:
            return
        start = min(item.page_number for item in items)
        end = max(item.page_number for item in items)
        sections = [item.section for item in items if item.section]
        # When a short document fits in one chunk, retain its first section as
        # a useful navigation hint even if later sections are also present.
        section = sections[0] if sections else None
        index = len(chunks)
        chunks.append(
            DocumentChunk(
                chunk_id=_chunk_id(document.document_id, index, text),
                document_id=document.document_id,
                document_title=document.source_title,
                text=text,
                page_start=start,
                page_end=end,
                section=section,
                document_type=document.document_type,
                authority=document.authority,
                is_synthetic=document.is_synthetic,
                source_url=document.source_url,
                source_path=document.source_path,
            )
        )

    for unit in units:
        words = list(unit.words)
        while words:
            available = max_tokens - current_words
            take = min(len(words), available)
            current.append(_Unit(tuple(words[:take]), unit.page_number, unit.section))
            current_words += take
            words = words[take:]
            if current_words >= max_tokens:
                emit(current)
                overlap = [word for item in current for word in item.words][-overlap_tokens:]
                current = [_Unit(tuple(overlap), current[-1].page_number, current[-1].section)] if overlap else []
                current_words = len(overlap)
    emit(current)
    return chunks

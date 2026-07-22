"""Load authorized local Markdown, text, and text-based PDF documents."""

from __future__ import annotations

from pathlib import Path

from app.rag.models import DocumentPage, SourceDocument


class DocumentLoadError(RuntimeError):
    """Raised when a source cannot be safely loaded."""


def _page(document: SourceDocument, page_number: int, text: str) -> DocumentPage:
    return DocumentPage(
        document_id=document.document_id,
        page_number=page_number,
        text=text,
        source_title=document.title,
        source_path=document.source_path,
        source_url=document.source_url,
        document_type=document.document_type,
        authority=document.authority,
        is_synthetic=document.is_synthetic,
        publication_date=document.publication_date,
        version=document.version,
        tags=document.tags,
    )


def _resolve_path(document: SourceDocument, base_dir: Path) -> Path:
    if not document.source_path:
        raise DocumentLoadError(
            f"Document {document.document_id} has no local source_path; "
            "add an authorized local file before ingesting it."
        )
    path = Path(document.source_path)
    return path if path.is_absolute() else (base_dir / path)


def load_document(document: SourceDocument, base_dir: Path | None = None) -> list[DocumentPage]:
    """Extract pages while retaining provenance and skipping empty PDF pages.

    OCR is deliberately not attempted. A scanned PDF with no extractable text
    returns an empty list so the ingestion report can flag it for manual review.
    """

    root = (base_dir or Path.cwd()).resolve()
    path = _resolve_path(document, root)
    if not path.exists():
        raise DocumentLoadError(f"Source file does not exist: {path}")
    if not path.is_file():
        raise DocumentLoadError(f"Source path is not a file: {path}")
    if path.stat().st_size == 0:
        raise DocumentLoadError(f"Source file is empty: {path}")

    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentLoadError(f"Could not decode UTF-8 source file: {path}") from exc
        if not text.strip():
            raise DocumentLoadError(f"Source file contains no text: {path}")
        return [_page(document, 1, text)]

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise DocumentLoadError(
                "PDF ingestion requires optional dependency 'pypdf'. "
                "Install requirements.txt before loading PDFs."
            ) from exc
        try:
            reader = PdfReader(str(path))
            pages = [
                _page(document, index + 1, page.extract_text() or "")
                for index, page in enumerate(reader.pages)
            ]
        except Exception as exc:  # pypdf exposes several parser exception types.
            raise DocumentLoadError(f"Could not extract PDF text from {path}: {exc}") from exc
        return [page for page in pages if page.text.strip()]

    raise DocumentLoadError(
        f"Unsupported document format {suffix or '<none>'!r}; supported formats are .pdf, .md, and .txt"
    )


def load_documents(
    documents: list[SourceDocument], base_dir: Path | None = None
) -> tuple[list[DocumentPage], list[str]]:
    """Load many documents and return pages plus human-readable skip messages."""

    pages: list[DocumentPage] = []
    skipped: list[str] = []
    for document in documents:
        try:
            extracted = load_document(document, base_dir=base_dir)
        except DocumentLoadError as exc:
            skipped.append(str(exc))
            continue
        if not extracted:
            skipped.append(
                f"No extractable text found for {document.document_id}; scanned PDFs need manual OCR review."
            )
        pages.extend(extracted)
    return pages, skipped

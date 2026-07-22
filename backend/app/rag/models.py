"""Internal contracts for the knowledge-base pipeline.

These models describe documents as they move through ingestion and retrieval.
They intentionally stay separate from the public API response models: a chunk
is an implementation detail, while an ``EvidenceReference`` is a frontend/API
contract.
"""

from datetime import date
from typing import Any

from pydantic import Field, model_validator

from app.schemas.common import (
    HazardCode,
    NonEmptyString,
    PermitType,
    RiskType,
    SpecGuardSchema,
    UsefulText,
)


class SourceDocument(SpecGuardSchema):
    """Manifest metadata describing one authorized source document."""

    document_id: NonEmptyString
    title: NonEmptyString
    document_type: NonEmptyString
    authority: NonEmptyString | None = None
    source_path: NonEmptyString | None = None
    source_url: NonEmptyString | None = None
    publication_date: date | None = None
    version: NonEmptyString | None = None
    is_synthetic: bool = False
    industry: NonEmptyString = "PETROLEUM_REFINERY"
    tags: list[NonEmptyString] = Field(default_factory=list)


class ManifestEntry(SourceDocument):
    """A source document plus repository-manifest processing controls."""

    local_path: NonEmptyString | None = None
    allowed_for_public_repo: bool = False
    checksum: NonEmptyString | None = None
    processing_status: NonEmptyString = "not_added"

    @model_validator(mode="after")
    def source_path_matches_local_path(self) -> "ManifestEntry":
        if self.source_path is None and self.local_path is not None:
            self.source_path = self.local_path
        return self

    def to_source_document(self) -> SourceDocument:
        """Return only the metadata needed by a document loader."""

        return SourceDocument(
            document_id=self.document_id,
            title=self.title,
            document_type=self.document_type,
            authority=self.authority,
            source_path=self.source_path or self.local_path,
            source_url=self.source_url,
            publication_date=self.publication_date,
            version=self.version,
            is_synthetic=self.is_synthetic,
            industry=self.industry,
            tags=self.tags,
        )


class DocumentPage(SpecGuardSchema):
    """Extracted text for one source page, retaining its provenance."""

    document_id: NonEmptyString
    page_number: int = Field(ge=1)
    text: str
    source_title: NonEmptyString
    source_path: NonEmptyString | None = None
    source_url: NonEmptyString | None = None
    document_type: NonEmptyString
    authority: NonEmptyString | None = None
    is_synthetic: bool = False
    publication_date: date | None = None
    version: NonEmptyString | None = None
    tags: list[NonEmptyString] = Field(default_factory=list)


class DocumentChunk(SpecGuardSchema):
    """A deterministic, retrievable passage with source and safety metadata."""

    chunk_id: NonEmptyString
    document_id: NonEmptyString
    document_title: NonEmptyString
    text: UsefulText
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section: NonEmptyString | None = None
    document_type: NonEmptyString
    authority: NonEmptyString | None = None
    risk_types: list[RiskType] = Field(default_factory=list)
    hazard_codes: list[HazardCode] = Field(default_factory=list)
    permit_types: list[PermitType] = Field(default_factory=list)
    equipment_types: list[NonEmptyString] = Field(default_factory=list)
    is_synthetic: bool = False
    source_url: NonEmptyString | None = None
    source_path: NonEmptyString | None = None
    publication_date: date | None = None
    version: NonEmptyString | None = None
    tags: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def page_range_is_ordered(self) -> "DocumentChunk":
        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self


class RetrievalQuery(SpecGuardSchema):
    """Validated input to the vector store and retriever."""

    query_text: UsefulText
    risk_types: list[RiskType] = Field(default_factory=list)
    hazard_codes: list[HazardCode] = Field(default_factory=list)
    permit_types: list[PermitType] = Field(default_factory=list)
    document_types: list[NonEmptyString] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievalResult(SpecGuardSchema):
    """One ranked chunk returned as evidence for a later safety response."""

    chunk_id: NonEmptyString
    text: UsefulText
    similarity_score: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_title: NonEmptyString
    source_url: NonEmptyString | None = None
    source_path: NonEmptyString | None = None
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section: NonEmptyString | None = None
    document_type: NonEmptyString
    is_synthetic: bool = False

    @model_validator(mode="after")
    def page_range_is_ordered(self) -> "RetrievalResult":
        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self

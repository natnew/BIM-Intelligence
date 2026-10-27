"""Requirements and their confirmation lifecycle (ADR-008, FR-REQ-04, C-02).

Only a requirement whose current revision has been confirmed is executable. Editing bumps the
revision and therefore invalidates the confirmation until the user confirms again.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from bim_intelligence.schemas.base import ContractModel, FrozenContractModel
from bim_intelligence.schemas.checks import CheckSpec

RequirementStatus = Literal["proposed", "confirmed", "edited", "rejected", "informational"]
RequirementOrigin = Literal["document", "ids", "builtin"]


class RequirementSource(FrozenContractModel):
    """Where a document-derived requirement came from; the quote is verbatim (FR-REQ-02)."""

    document_id: str = Field(min_length=1)
    location: str = Field(min_length=1, description="Paragraph or page identifier.")
    quote: str = Field(min_length=1, description="Exact substring of the extracted text.")


class Requirement(ContractModel):
    """A single reviewable requirement bound to exactly one CheckSpec."""

    id: str = Field(min_length=1, examples=["REQ-001"])
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    origin: RequirementOrigin
    source: RequirementSource | None = None
    check: CheckSpec
    status: RequirementStatus
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Model self-report; a sorting aid only."
    )
    revision: int = Field(default=1, ge=1)
    confirmed_revision: int | None = Field(
        default=None, ge=1, description="Revision the user confirmed, if any."
    )
    confirmed_by: str | None = None
    confirmed_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _confirmation_is_bound_to_revision(self) -> Requirement:
        if self.confirmed_revision is not None and self.confirmed_revision > self.revision:
            raise ValueError("confirmed_revision cannot exceed revision")
        if self.status == "confirmed" and self.confirmed_revision != self.revision:
            raise ValueError(
                "status 'confirmed' requires confirmed_revision to equal the current revision"
            )
        return self

    @model_validator(mode="after")
    def _document_requirements_cite_their_source(self) -> Requirement:
        if self.origin == "document" and self.source is None:
            raise ValueError("requirements extracted from a document must carry a source quote")
        return self

    @property
    def is_executable(self) -> bool:
        """True only for a confirmed requirement at its confirmed revision (FR-REQ-04)."""
        return self.status == "confirmed" and self.confirmed_revision == self.revision

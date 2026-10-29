"""Uploaded requirement documents (FR-REQ-01, FR-REQ-05).

Documents are stored content-addressed and never modified. IDS specifications become
confirmed requirements on import; narrative text remains untrusted source material until
interpretation and explicit human confirmation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bim_intelligence.schemas.base import FrozenContractModel
from bim_intelligence.schemas.elements import Sha256Hex
from bim_intelligence.schemas.requirements import Requirement

DocumentKind = Literal["ids", "text", "markdown"]


class DocumentImport(FrozenContractModel):
    """Result of importing one document: its identity and the requirements it established."""

    sha256: Sha256Hex = Field(description="SHA-256 of the stored document bytes.")
    kind: DocumentKind
    title: str = Field(description="Document title as declared inside the file.")
    requirements: list[Requirement] = Field(
        description="Requirements derived from this document, in document order."
    )

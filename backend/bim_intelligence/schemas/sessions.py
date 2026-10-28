"""Session: the directory-backed review context (ADR-006, ARCHITECTURE §10.2).

A session owns one model and any number of documents, requirements and review runs. The id is
a lower-case UUID4 and doubles as the directory name under ``data/sessions/``; the strict
pattern is what makes path traversal through a session id impossible (ARCHITECTURE §13).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from bim_intelligence.schemas.base import ContractModel
from bim_intelligence.schemas.elements import Sha256Hex

SESSION_ID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"

SessionId = Annotated[
    str, Field(pattern=SESSION_ID_PATTERN, description="Lower-case, hyphenated UUID4.")
]
SessionStatus = Literal["created", "model_ready"]


class Session(ContractModel):
    """Session metadata as returned by ``GET /sessions/{sid}``. Never carries file paths."""

    id: SessionId
    created_at: AwareDatetime
    status: SessionStatus = Field(
        description="'created' until an IFC has been indexed, then 'model_ready'."
    )
    model_hash: Sha256Hex | None = Field(
        default=None, description="SHA-256 of the stored IFC bytes; None until uploaded."
    )
    document_hashes: list[Sha256Hex] = Field(
        default_factory=list, description="SHA-256 of each uploaded requirement document."
    )

    @model_validator(mode="after")
    def _status_and_model_hash_agree(self) -> Session:
        if self.status == "model_ready" and self.model_hash is None:
            raise ValueError("status 'model_ready' requires model_hash")
        if self.status == "created" and self.model_hash is not None:
            raise ValueError("status 'created' must not carry model_hash")
        return self

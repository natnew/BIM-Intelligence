"""The Model Index: a denormalised, read-only snapshot of one uploaded model (C-03, §8.1).

Records are keyed by ``express_id`` — the identity IfcOpenShell guarantees unique — with a
``GlobalId → [express_id]`` multimap on top. Duplicate GlobalIds therefore keep every record
and make ``by_global_id`` fail explicitly instead of returning an arbitrary one (FR-VAL-06).
Malformed GlobalIds are recorded and the element is indexed with ``global_id=None``.

This module has no IfcOpenShell dependency; :mod:`bim_intelligence.bim.indexer` builds it.
"""

from __future__ import annotations

import re
from functools import cached_property

from pydantic import BaseModel, ConfigDict, Field

from bim_intelligence.bim.errors import (
    AmbiguousGlobalIdError,
    InvalidGlobalIdError,
    UnknownElementError,
)
from bim_intelligence.schemas import ElementRecord, ModelSummary
from bim_intelligence.schemas.elements import IFC_GUID_PATTERN

_GUID_RE = re.compile(IFC_GUID_PATTERN)


class ModelIndex(BaseModel):
    """Everything the backend knows about a model without reopening the IFC."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: ModelSummary
    elements: list[ElementRecord] = Field(description="Indexed records in express-id order.")
    duplicate_global_ids: dict[str, list[int]] = Field(
        default_factory=dict,
        description="GlobalIds carried by more than one record → their express ids.",
    )
    malformed_global_ids: dict[int, str | None] = Field(
        default_factory=dict,
        description="express id → raw GlobalId attribute that failed the 22-character check.",
    )

    @cached_property
    def _by_express_id(self) -> dict[int, ElementRecord]:
        return {record.ref.express_id: record for record in self.elements}

    @cached_property
    def _by_global_id(self) -> dict[str, list[int]]:
        mapping: dict[str, list[int]] = {}
        for record in self.elements:
            if record.ref.global_id is not None:
                mapping.setdefault(record.ref.global_id, []).append(record.ref.express_id)
        return mapping

    def by_express_id(self, express_id: int) -> ElementRecord:
        try:
            return self._by_express_id[express_id]
        except KeyError:
            raise UnknownElementError(f"#{express_id}") from None

    def express_ids_for(self, global_id: str) -> list[int]:
        """All express ids carrying ``global_id``; empty when unknown."""
        if not _GUID_RE.fullmatch(global_id):
            raise InvalidGlobalIdError(global_id)
        return list(self._by_global_id.get(global_id, ()))

    def by_global_id(self, global_id: str) -> ElementRecord:
        """The single record with this GlobalId; ambiguous ids fail rather than guess."""
        express_ids = self.express_ids_for(global_id)
        if not express_ids:
            raise UnknownElementError(global_id)
        if len(express_ids) > 1:
            raise AmbiguousGlobalIdError(global_id, express_ids)
        return self._by_express_id[express_ids[0]]

    def of_type(self, ifc_type: str) -> list[ElementRecord]:
        """Records whose concrete class is exactly ``ifc_type`` (no subtype expansion)."""
        return [record for record in self.elements if record.ref.ifc_type == ifc_type]

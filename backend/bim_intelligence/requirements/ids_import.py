"""IDS upload as a source of confirmed requirements (FR-REQ-05, ADR-008, ADR-018).

An IDS file is the project's own machine-readable statement of what the model must contain, so
each of its specifications becomes a ``Requirement`` that is confirmed at revision 1 the moment
it is imported. The human-confirmation step of ADR-008 applies to requirements *interpreted*
from narrative documents; a specification the project authored in IDS needs no interpretation.

The IfcTester-dependent work (XSD validation, canonicalisation, ``CheckSpec`` compilation) lives
in ``validation/``; this module only decides what a requirement record looks like and how it is
persisted.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from bim_intelligence.schemas import DocumentImport, Requirement, RequirementSource
from bim_intelligence.store import SessionStore, UploadTooLargeError
from bim_intelligence.validation import CompiledIds, CompiledSpecification, compile_ids

CONFIRMED_BY_IDS_IMPORT = "ids-import"
REQUIREMENT_ID_PREFIX = "REQ-"


@dataclass(frozen=True)
class IdsImportResult:
    """The imported document and whether this call created it (``False`` on a re-upload)."""

    document: DocumentImport
    created: bool


def import_ids_document(
    store: SessionStore, session_id: str, data: bytes, *, max_bytes: int
) -> IdsImportResult:
    """Validate, store and register an IDS document; returns its confirmed requirements.

    Idempotent on content: uploading bytes already imported returns the requirements created
    the first time without duplicating them. Raises ``InvalidIdsError`` for anything that is not
    a valid IDS 1.0 document and ``UploadTooLargeError`` before parsing an oversized one.
    """
    if len(data) > max_bytes:
        raise UploadTooLargeError(max_bytes)
    compiled = compile_ids(data)
    with store.lock_model(session_id) as lock:
        existing = store.read_requirements(session_id)
        already = requirements_for_document(existing, compiled.sha256)
        if already:
            store.add_document(lock, data, "ids")  # repairs a registration lost to a crash
            return IdsImportResult(_document(compiled, already), created=False)
        created = _requirements_from(compiled, start=len(existing) + 1, store=store)
        store.write_requirements(lock, [*existing, *created])
        store.add_document(lock, data, "ids")
    return IdsImportResult(_document(compiled, created), created=True)


def requirements_for_document(
    requirements: Sequence[Requirement], sha256: str
) -> list[Requirement]:
    """The requirements an imported document established, in document order."""
    return [
        requirement
        for requirement in requirements
        if requirement.origin == "ids"
        and requirement.source is not None
        and requirement.source.document_id == sha256
    ]


def executable_requirements(requirements: Sequence[Requirement]) -> list[Requirement]:
    """Only requirements confirmed at their current revision may run (FR-REQ-04)."""
    return [requirement for requirement in requirements if requirement.is_executable]


def _requirements_from(
    compiled: CompiledIds, *, start: int, store: SessionStore
) -> list[Requirement]:
    confirmed_at = store.now()
    return [
        Requirement(
            id=f"{REQUIREMENT_ID_PREFIX}{start + offset:03d}",
            title=spec.title,
            statement=spec.statement,
            origin="ids",
            source=_source(compiled, spec),
            check=spec.check,
            status="confirmed",
            revision=1,
            confirmed_revision=1,
            confirmed_by=CONFIRMED_BY_IDS_IMPORT,
            confirmed_at=confirmed_at,
        )
        for offset, spec in enumerate(compiled.specifications)
    ]


def _source(compiled: CompiledIds, spec: CompiledSpecification) -> RequirementSource | None:
    """Trace the requirement to its ``<specification>``; the quote is the verbatim ``name``."""
    if not spec.name:
        return None
    return RequirementSource(
        document_id=compiled.sha256,
        location=f"/ids/specifications/specification[{spec.index + 1}]",
        quote=spec.name,
    )


def _document(compiled: CompiledIds, requirements: Sequence[Requirement]) -> DocumentImport:
    return DocumentImport(
        sha256=compiled.sha256, kind="ids", title=compiled.title, requirements=list(requirements)
    )

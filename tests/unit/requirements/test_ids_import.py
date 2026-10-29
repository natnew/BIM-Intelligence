"""IDS upload establishes confirmed requirements (FR-REQ-05, AC-05, ADR-008, ADR-018).

An IDS is machine-readable intent authored by the project, so each specification becomes a
``Requirement`` that is confirmed at revision 1 and bound to an immutable ``CheckSpec``.
Narrative (BEP) extraction and interactive confirmation are later tasks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from bim_intelligence.requirements import (
    executable_requirements,
    import_ids_document,
    requirements_for_document,
)
from bim_intelligence.store import SessionStore, UploadTooLargeError
from bim_intelligence.validation import InvalidIdsError, compile_ids
from fixtures.make_minimal_ifc import SPEC_CLASSIFICATION, SPEC_FIRE_RATING
from support.ids import (
    CLASSIFICATION_SPEC,
    DOOR_SPEC,
    FIRE_RATING_SPEC,
    FIXTURE_IDS_BYTES,
    SCHEMA_INVALID_IDS,
    ids_document,
    specification,
)

NOW = datetime(2026, 10, 29, 9, 0, tzinfo=timezone.utc)
MAX_BYTES = 1 << 20


@pytest.fixture
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions", clock=lambda: NOW)


@pytest.fixture
def session_id(store: SessionStore) -> str:
    return store.create().id


def test_valid_ids_imports_two_confirmed_requirements(store: SessionStore, session_id: str) -> None:
    result = import_ids_document(store, session_id, FIXTURE_IDS_BYTES, max_bytes=MAX_BYTES)
    assert result.created is True
    document = result.document
    assert document.kind == "ids"
    assert document.title == "BIM Intelligence minimal fixture"
    assert document.sha256 == compile_ids(FIXTURE_IDS_BYTES).sha256
    assert [r.id for r in document.requirements] == ["REQ-001", "REQ-002"]
    assert [r.title for r in document.requirements] == [SPEC_FIRE_RATING, SPEC_CLASSIFICATION]
    for requirement in document.requirements:
        assert requirement.origin == "ids"
        assert requirement.status == "confirmed"
        assert requirement.revision == 1
        assert requirement.confirmed_revision == 1
        assert requirement.confirmed_at == NOW
        assert requirement.confirmed_by == "ids-import"
        assert requirement.check.kind == "ids"
        assert requirement.is_executable
        assert requirement.source is not None
        assert requirement.source.document_id == document.sha256
        assert requirement.source.quote == requirement.title
    assert (
        document.requirements[0].statement == "Every external wall shall declare its fire rating."
    )
    assert store.read_requirements(session_id) == document.requirements
    assert store.get(session_id).document_hashes == [document.sha256]


def test_two_specifications_produce_two_distinct_checks(
    store: SessionStore, session_id: str
) -> None:
    requirements = import_ids_document(
        store, session_id, FIXTURE_IDS_BYTES, max_bytes=MAX_BYTES
    ).document.requirements
    assert len({r.check.id for r in requirements}) == 2
    assert requirements[0].check.id != requirements[1].check.id


def test_malformed_ids_is_rejected_and_leaves_the_session_untouched(
    store: SessionStore, session_id: str
) -> None:
    with pytest.raises(InvalidIdsError):
        import_ids_document(store, session_id, SCHEMA_INVALID_IDS, max_bytes=MAX_BYTES)
    assert store.read_requirements(session_id) == []
    assert store.get(session_id).document_hashes == []


def test_oversized_ids_is_rejected_before_parsing(store: SessionStore, session_id: str) -> None:
    with pytest.raises(UploadTooLargeError):
        import_ids_document(store, session_id, FIXTURE_IDS_BYTES, max_bytes=16)
    assert store.get(session_id).document_hashes == []


def test_reimporting_the_same_document_is_idempotent(store: SessionStore, session_id: str) -> None:
    first = import_ids_document(store, session_id, FIXTURE_IDS_BYTES, max_bytes=MAX_BYTES)
    second = import_ids_document(store, session_id, FIXTURE_IDS_BYTES, max_bytes=MAX_BYTES)
    assert second.created is False
    assert second.document == first.document
    assert store.read_requirements(session_id) == first.document.requirements
    assert store.get(session_id).document_hashes == [first.document.sha256]


def test_a_second_document_continues_the_requirement_numbering(
    store: SessionStore, session_id: str
) -> None:
    import_ids_document(store, session_id, FIXTURE_IDS_BYTES, max_bytes=MAX_BYTES)
    second = import_ids_document(
        store, session_id, ids_document(DOOR_SPEC, title="Doors"), max_bytes=MAX_BYTES
    )
    assert [r.id for r in second.document.requirements] == ["REQ-003"]
    assert [r.id for r in store.read_requirements(session_id)] == ["REQ-001", "REQ-002", "REQ-003"]
    assert (
        requirements_for_document(store.read_requirements(session_id), second.document.sha256)
        == second.document.requirements
    )


def test_title_statement_and_source_fall_back_when_the_specification_is_unnamed(
    store: SessionStore, session_id: str
) -> None:
    unnamed = specification("", "<entity><name><simpleValue>IFCWALL</simpleValue></name></entity>")
    result = import_ids_document(store, session_id, ids_document(unnamed), max_bytes=MAX_BYTES)
    (requirement,) = result.document.requirements
    assert requirement.title == "Specification 1"
    assert requirement.statement == "Specification 1"
    assert requirement.source is None  # nothing verbatim to quote
    assert requirement.check.rule_id == "ids:specification-1"


def test_executable_requirements_filters_by_confirmation_state(
    store: SessionStore, session_id: str
) -> None:
    requirements = import_ids_document(
        store, session_id, ids_document(FIRE_RATING_SPEC, CLASSIFICATION_SPEC), max_bytes=MAX_BYTES
    ).document.requirements
    edited = requirements[1].model_copy(update={"status": "edited", "revision": 2})
    assert [r.id for r in executable_requirements([requirements[0], edited])] == ["REQ-001"]


def test_requirement_check_criteria_are_immutable(store: SessionStore, session_id: str) -> None:
    (requirement, _) = import_ids_document(
        store, session_id, FIXTURE_IDS_BYTES, max_bytes=MAX_BYTES
    ).document.requirements
    with pytest.raises(Exception, match="frozen"):
        requirement.check.ids_specification = "<specification/>"  # type: ignore[misc]

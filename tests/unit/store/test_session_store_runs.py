"""Session store: documents, requirements and run publication (ADR-006, ADR-017, ADR-018).

Documents are content-addressed and write-once; ``requirements.json`` is replaced atomically
under the session's lock; a run directory is published complete or not at all.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from bim_intelligence.schemas import (
    CheckResult,
    CheckSpec,
    ElementRef,
    Finding,
    InputManifest,
    PlannedCheck,
    Requirement,
    ReviewPlan,
    ReviewRun,
    findings_to_json,
)
from bim_intelligence.store import (
    DOCUMENTS_DIR,
    FINDINGS_FILE,
    REQUIREMENTS_FILE,
    RUN_FILE,
    RUNS_DIR,
    DocumentNotFoundError,
    InvalidRunIdError,
    RunNotFoundError,
    SessionStore,
    StorageError,
)
from support.store import publish_version, tree_digest

NOW = datetime(2026, 10, 29, 9, 0, tzinfo=timezone.utc)
IDS_BYTES = b'<ids xmlns="http://standards.buildingsmart.org/IDS"/>'


@pytest.fixture
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions", clock=lambda: NOW)


@pytest.fixture
def session_id(store: SessionStore) -> str:
    return store.create().id


def _requirement(req_id: str, name: str) -> Requirement:
    check = CheckSpec(
        kind="ids",
        rule_id=f"ids:{name}",
        rule_version="v1",
        ids_specification=f'<specification name="{name}"/>',
    )
    return Requirement(
        id=req_id,
        title=name,
        statement=name,
        origin="ids",
        check=check,
        status="confirmed",
        confirmed_revision=1,
        confirmed_by="ids-import",
        confirmed_at=NOW,
    )


def _run(session_id: str, run_id: str, findings: list[Finding]) -> ReviewRun:
    status = "failed" if findings else "passed"
    results = [
        CheckResult(
            check_id="c" * 16,
            requirement_id="REQ-001",
            status=status,
            applicable_count=1,
            finding_ids=[f.id for f in findings],
        )
    ]
    return ReviewRun(
        id=run_id,
        session_id=session_id,
        status="completed",
        plan=ReviewPlan(checks=[PlannedCheck(check_id="c" * 16, reason="default plan")]),
        plan_source="default",
        check_results=results,
        input_manifest=InputManifest(model_hash="a" * 64),
        created_at=NOW,
        finished_at=NOW,
    )


def _finding() -> Finding:
    return Finding(
        check_id="c" * 16,
        requirement_id="REQ-001",
        rule_id="ids:x",
        rule_version="v1",
        facet_index=0,
        severity="error",
        category="property_requirement",
        elements=[ElementRef(global_id=None, express_id=7, ifc_type="IfcWall")],
        observed="missing",
        expected="present",
        method="ids",
    )


# -- documents ----------------------------------------------------------------------------


def test_add_document_is_content_addressed_and_registered_on_the_session(
    store: SessionStore, session_id: str
) -> None:
    with store.lock_model(session_id) as lock:
        sha256 = store.add_document(lock, IDS_BYTES, "ids")
    assert sha256 == hashlib.sha256(IDS_BYTES).hexdigest()
    assert (store.session_dir(session_id) / DOCUMENTS_DIR / f"{sha256}.ids").read_bytes() == (
        IDS_BYTES
    )
    assert store.get(session_id).document_hashes == [sha256]
    assert store.read_document(session_id, sha256, "ids") == IDS_BYTES


def test_add_document_twice_is_idempotent(store: SessionStore, session_id: str) -> None:
    with store.lock_model(session_id) as lock:
        first = store.add_document(lock, IDS_BYTES, "ids")
        second = store.add_document(lock, IDS_BYTES, "ids")
    assert first == second
    assert store.get(session_id).document_hashes == [first]


def test_add_document_requires_the_lock(store: SessionStore, session_id: str) -> None:
    with store.lock_model(session_id) as lock:
        pass
    with pytest.raises(StorageError, match="lock"):
        store.add_document(lock, IDS_BYTES, "ids")


def test_read_unknown_document_is_not_found(store: SessionStore, session_id: str) -> None:
    with pytest.raises(DocumentNotFoundError):
        store.read_document(session_id, "0" * 64, "ids")
    with pytest.raises(ValueError, match="SHA-256"):
        store.read_document(session_id, "../session.json", "ids")


def test_documents_never_touch_the_model_version(store: SessionStore, session_id: str) -> None:
    version = publish_version(store, session_id, b"ISO-10303-21;")
    before = tree_digest(version.directory)
    with store.lock_model(session_id) as lock:
        store.add_document(lock, IDS_BYTES, "ids")
    assert tree_digest(version.directory) == before
    assert store.get(session_id).model_hash == version.sha256


# -- requirements -------------------------------------------------------------------------


def test_requirements_default_to_empty(store: SessionStore, session_id: str) -> None:
    assert store.read_requirements(session_id) == []


def test_requirements_round_trip_in_canonical_json(store: SessionStore, session_id: str) -> None:
    requirements = [_requirement("REQ-001", "a"), _requirement("REQ-002", "b")]
    with store.lock_model(session_id) as lock:
        store.write_requirements(lock, requirements)
    assert store.read_requirements(session_id) == requirements
    text = (store.session_dir(session_id) / REQUIREMENTS_FILE).read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text) == [r.model_dump(mode="json") for r in requirements]


def test_write_requirements_requires_the_lock(store: SessionStore, session_id: str) -> None:
    with store.lock_model(session_id) as lock:
        pass
    with pytest.raises(StorageError, match="lock"):
        store.write_requirements(lock, [])


def test_unreadable_requirements_file_is_a_storage_error(
    store: SessionStore, session_id: str
) -> None:
    (store.session_dir(session_id) / REQUIREMENTS_FILE).write_text("{not json", encoding="utf-8")
    with pytest.raises(StorageError, match="requirements"):
        store.read_requirements(session_id)


# -- runs ---------------------------------------------------------------------------------


def test_publish_run_writes_run_and_findings_atomically(
    store: SessionStore, session_id: str
) -> None:
    run_id = "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b"
    finding = _finding()
    run = _run(session_id, run_id, [finding])
    store.publish_run(run, [finding])

    run_dir = store.session_dir(session_id) / RUNS_DIR / run_id
    assert (run_dir / RUN_FILE).is_file() and (run_dir / FINDINGS_FILE).is_file()
    assert store.read_run(session_id, run_id) == run
    assert store.read_findings(session_id, run_id) == [finding]
    assert store.list_runs(session_id) == [run_id]
    assert [p.name for p in (store.session_dir(session_id) / RUNS_DIR).iterdir()] == [run_id]


def test_read_historical_run_without_provenance(store: SessionStore, session_id: str) -> None:
    run_id = "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b"
    store.publish_run(_run(session_id, run_id, []), [])
    run_path = store.session_dir(session_id) / RUNS_DIR / run_id / RUN_FILE
    legacy_data = json.loads(run_path.read_text(encoding="utf-8"))
    legacy_data.pop("provenance")
    run_path.write_text(json.dumps(legacy_data), encoding="utf-8")

    assert store.read_run(session_id, run_id).provenance is None


def test_publish_run_refuses_a_second_run_with_the_same_id(
    store: SessionStore, session_id: str
) -> None:
    run_id = "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b"
    store.publish_run(_run(session_id, run_id, []), [])
    with pytest.raises(StorageError, match="already"):
        store.publish_run(_run(session_id, run_id, []), [])


def test_publish_run_refuses_findings_the_run_does_not_list(
    store: SessionStore, session_id: str
) -> None:
    run_id = "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b"
    run = _run(session_id, run_id, [])
    with pytest.raises(StorageError, match="finding"):
        store.publish_run(run, [_finding()])


def test_run_lookup_validates_the_id_before_touching_disk(
    store: SessionStore, session_id: str
) -> None:
    with pytest.raises(InvalidRunIdError):
        store.read_run(session_id, "../../etc/passwd")
    with pytest.raises(RunNotFoundError):
        store.read_run(session_id, "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b")
    with pytest.raises(RunNotFoundError):
        store.read_findings(session_id, "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b")


def test_findings_json_is_the_canonical_serialisation(store: SessionStore, session_id: str) -> None:
    run_id = "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b"
    finding = _finding()
    store.publish_run(_run(session_id, run_id, [finding]), [finding])
    path = store.session_dir(session_id) / RUNS_DIR / run_id / FINDINGS_FILE
    assert path.read_text(encoding="utf-8") == findings_to_json([finding])

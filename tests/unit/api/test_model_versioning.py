"""Version binding at the HTTP boundary (ADR-017).

Every read names the model version it was answered from (``ETag`` = quoted SHA-256), the
values agree across endpoints, ``If-Match`` pins a client to one version, concurrent uploads
are refused rather than interleaved, and a restart recovers abandoned staging directories.
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX, create_app
from bim_intelligence.bim import ingest as ingest_module
from bim_intelligence.bim.indexer import build_index as real_build_index
from bim_intelligence.config import Settings
from bim_intelligence.store import MODEL_FILE, MODELS_DIR, STAGING_PREFIX, SessionStore
from fixtures.make_minimal_ifc import GLOBAL_IDS
from support.api import FIXTURE_BYTES, assert_problem, upload

BYTES_A = FIXTURE_BYTES
BYTES_B = FIXTURE_BYTES + b"\n"
HASH_A = hashlib.sha256(BYTES_A).hexdigest()
HASH_B = hashlib.sha256(BYTES_B).hexdigest()
ETAG_A, ETAG_B = f'"{HASH_A}"', f'"{HASH_B}"'
BARRIER_TIMEOUT = 30.0
W001 = GLOBAL_IDS["W-001"]


def _url(session_id: str, tail: str) -> str:
    return f"{API_PREFIX}/sessions/{session_id}/{tail}"


def _observed_versions(client: TestClient, session_id: str) -> dict[str, str]:
    """Every place a client can learn the model version, in one place."""
    session = client.get(f"{API_PREFIX}/sessions/{session_id}").json()
    summary = client.get(_url(session_id, "model/summary"))
    file = client.get(_url(session_id, "model/file"))
    element = client.get(_url(session_id, f"elements/{W001}"))
    assert summary.status_code == file.status_code == element.status_code == 200
    return {
        "session.model_hash": f'"{session["model_hash"]}"',
        "summary.model_hash": f'"{summary.json()["model_hash"]}"',
        "summary ETag": summary.headers["etag"],
        "file ETag": file.headers["etag"],
        "sha256(file body)": f'"{hashlib.sha256(file.content).hexdigest()}"',
        "element ETag": element.headers["etag"],
    }


class TestEveryReadNamesOneVersion:
    def test_upload_summary_file_element_and_session_agree(
        self, client: TestClient, session_id: str
    ) -> None:
        created = upload(client, session_id, BYTES_A)
        assert created.status_code == 201
        assert created.headers["etag"] == ETAG_A
        observed = _observed_versions(client, session_id)
        assert set(observed.values()) == {ETAG_A}, observed

    def test_reupload_moves_every_read_to_the_new_version(
        self, client: TestClient, loaded_session: str
    ) -> None:
        assert upload(client, loaded_session, BYTES_B).status_code == 201
        observed = _observed_versions(client, loaded_session)
        assert set(observed.values()) == {ETAG_B}, observed

    def test_rejected_reupload_changes_no_read(
        self, client: TestClient, loaded_session: str
    ) -> None:
        before = _observed_versions(client, loaded_session)
        assert_problem(upload(client, loaded_session, b"garbage"), 422, "ifc-unreadable")
        assert _observed_versions(client, loaded_session) == before
        assert set(before.values()) == {ETAG_A}

    def test_summary_and_element_carry_no_cache_directive_that_outlives_the_version(
        self, client: TestClient, loaded_session: str
    ) -> None:
        for tail in ("model/summary", f"elements/{W001}", "model/file"):
            response = client.get(_url(loaded_session, tail))
            assert response.headers["cache-control"] == "private, no-cache", tail


class TestIfMatch:
    @pytest.mark.parametrize("tail", ["model/summary", "model/file", f"elements/{W001}"])
    def test_matching_precondition_is_served(
        self, client: TestClient, loaded_session: str, tail: str
    ) -> None:
        ok = client.get(_url(loaded_session, tail), headers={"If-Match": ETAG_A})
        assert ok.status_code == 200
        assert ok.headers["etag"] == ETAG_A
        wildcard = client.get(_url(loaded_session, tail), headers={"If-Match": "*"})
        assert wildcard.status_code == 200
        several = client.get(_url(loaded_session, tail), headers={"If-Match": f'"x", {ETAG_A}'})
        assert several.status_code == 200

    @pytest.mark.parametrize("tail", ["model/summary", "model/file", f"elements/{W001}"])
    def test_stale_precondition_is_412_after_replacement(
        self, client: TestClient, loaded_session: str, tail: str
    ) -> None:
        assert upload(client, loaded_session, BYTES_B).status_code == 201
        stale = client.get(_url(loaded_session, tail), headers={"If-Match": ETAG_A})
        body = assert_problem(stale, 412, "model-version-mismatch", detail_contains=HASH_B)
        assert HASH_A in str(body["detail"])
        weak = client.get(_url(loaded_session, tail), headers={"If-Match": f"W/{ETAG_B}"})
        assert weak.status_code == 412, "If-Match is a strong comparison"

    def test_if_none_match_on_the_file_still_yields_304_for_the_active_version(
        self, client: TestClient, loaded_session: str
    ) -> None:
        url = _url(loaded_session, "model/file")
        assert client.get(url, headers={"If-None-Match": ETAG_A}).status_code == 304
        assert upload(client, loaded_session, BYTES_B).status_code == 201
        fresh = client.get(url, headers={"If-None-Match": ETAG_A})
        assert fresh.status_code == 200
        assert fresh.headers["etag"] == ETAG_B
        assert fresh.content == BYTES_B

    def test_precondition_before_any_upload_is_404(
        self, client: TestClient, session_id: str
    ) -> None:
        response = client.get(_url(session_id, "model/summary"), headers={"If-Match": ETAG_A})
        assert_problem(response, 404, "model-not-found")


class TestConcurrentUploads:
    def test_second_upload_while_one_is_indexing_is_409_model_locked(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = create_app(settings)
        session_id = TestClient(app).post(f"{API_PREFIX}/sessions").json()["id"]
        assert upload(TestClient(app), session_id, BYTES_A).status_code == 201

        entered, proceed, first_call = threading.Event(), threading.Event(), threading.Event()

        def gated_build_index(*args: Any, **kwargs: Any) -> Any:
            if not first_call.is_set():
                first_call.set()
                entered.set()
                assert proceed.wait(BARRIER_TIMEOUT), "test barrier timed out"
            return real_build_index(*args, **kwargs)

        monkeypatch.setattr(ingest_module, "build_index", gated_build_index)
        results: dict[str, Any] = {}

        def slow_upload() -> None:
            response = upload(TestClient(app), session_id, BYTES_B)
            results["first"] = (response.status_code, response.headers.get("etag"))

        thread = threading.Thread(target=slow_upload)
        thread.start()
        try:
            assert entered.wait(BARRIER_TIMEOUT), "first upload never reached indexing"
            probe = TestClient(app)
            refused = upload(probe, session_id, BYTES_A)
            assert_problem(refused, 409, "model-locked", detail_contains=session_id)
            # Readers are not blocked by the lock and still see the old version whole.
            assert set(_observed_versions(probe, session_id).values()) == {ETAG_A}
        finally:
            proceed.set()
            thread.join(timeout=BARRIER_TIMEOUT)
        assert results["first"] == (201, ETAG_B)
        assert set(_observed_versions(TestClient(app), session_id).values()) == {ETAG_B}

    def test_reads_during_replacement_are_always_self_consistent(self, settings: Settings) -> None:
        app = create_app(settings)
        setup = TestClient(app)
        session_id = setup.post(f"{API_PREFIX}/sessions").json()["id"]
        assert upload(setup, session_id, BYTES_A).status_code == 201

        stop = threading.Event()
        failures: list[str] = []
        reads = [0]
        counter = threading.Lock()

        def reader() -> None:
            client = TestClient(app)
            while not stop.is_set():
                try:
                    file = client.get(_url(session_id, "model/file"))
                    summary = client.get(_url(session_id, "model/summary"))
                    element = client.get(_url(session_id, f"elements/{W001}"))
                    for response in (file, summary, element):
                        assert response.status_code == 200, response.text
                        assert response.headers["etag"] in {ETAG_A, ETAG_B}
                    body_hash = f'"{hashlib.sha256(file.content).hexdigest()}"'
                    assert body_hash == file.headers["etag"], "ETag must describe the body"
                    assert f'"{summary.json()["model_hash"]}"' == summary.headers["etag"]
                    with counter:
                        reads[0] += 1
                except BaseException as exc:
                    failures.append(repr(exc))
                    return

        threads = [threading.Thread(target=reader) for _ in range(3)]
        for thread in threads:
            thread.start()
        try:
            for data in (BYTES_B, BYTES_A, BYTES_B, BYTES_A, BYTES_B):
                assert upload(setup, session_id, data).status_code == 201
        finally:
            stop.set()
            for thread in threads:
                thread.join(timeout=BARRIER_TIMEOUT)
        assert failures == [], failures
        assert reads[0] > 0
        assert set(_observed_versions(setup, session_id).values()) == {ETAG_B}


class TestRecoveryOnStartup:
    def _abandon_staging(self, settings: Settings, session_id: str) -> Path:
        directory = (
            settings.data_dir / "sessions" / session_id / MODELS_DIR / f"{STAGING_PREFIX}crash"
        )
        directory.mkdir(parents=True)
        (directory / MODEL_FILE).write_bytes(BYTES_B[:100])
        return directory

    def test_app_startup_removes_abandoned_staging_and_serves_the_committed_version(
        self, settings: Settings
    ) -> None:
        first_process: FastAPI = create_app(settings)
        client = TestClient(first_process)
        session_id = client.post(f"{API_PREFIX}/sessions").json()["id"]
        assert upload(client, session_id, BYTES_A).status_code == 201
        abandoned = self._abandon_staging(settings, session_id)

        with TestClient(create_app(settings)) as restarted:  # runs the lifespan
            assert not abandoned.exists()
            assert set(_observed_versions(restarted, session_id).values()) == {ETAG_A}
        store = SessionStore(settings.data_dir / "sessions")
        assert store.list_model_versions(session_id) == [HASH_A]
        assert store.staging_directories(session_id) == []

    def test_startup_with_no_data_directory_is_fine(self, settings: Settings) -> None:
        assert not settings.data_dir.exists()
        with TestClient(create_app(settings)) as client:
            assert client.get(f"{API_PREFIX}/health").status_code == 200

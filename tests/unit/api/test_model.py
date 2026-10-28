"""Model upload, summary and file endpoints (AC-01, AC-11; FR-ING-01..03, NFR-07)."""

from __future__ import annotations

import hashlib
import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX
from bim_intelligence.config import Settings
from fixtures.make_minimal_ifc import GLOBAL_IDS
from fixtures.variants import IFC2X3_TEXT
from support.api import FIXTURE_BYTES, assert_problem, upload

FIXTURE_HASH = hashlib.sha256(FIXTURE_BYTES).hexdigest()


class TestUpload:
    def test_fixture_upload_returns_201_and_a_model_summary(
        self, client: TestClient, session_id: str, settings: Settings
    ) -> None:
        response = upload(client, session_id, FIXTURE_BYTES)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["ifc_schema"] == "IFC4"
        assert body["model_hash"] == FIXTURE_HASH
        assert body["project_name"] == "Minimal Project"
        assert body["counts"]["IfcWall"] == 3
        assert len(body["storeys"]) == 1
        assert body["storeys"][0]["name"] == "L00"
        assert body["storeys"][0]["global_id"] == GLOBAL_IDS["L00"]
        assert str(settings.data_dir) not in response.text

    def test_stored_filename_is_never_derived_from_the_client_filename(
        self, client: TestClient, session_id: str, settings: Settings
    ) -> None:
        response = upload(client, session_id, FIXTURE_BYTES, filename="..\\..\\Evil Name.IFC")
        assert response.status_code == 201, response.text
        session_dir = settings.data_dir / "sessions" / session_id
        assert sorted(p.name for p in session_dir.iterdir()) == [
            "model.ifc",
            "model_index.json",
            "model_summary.json",
            "session.json",
        ]
        assert (session_dir / "model.ifc").read_bytes() == FIXTURE_BYTES
        assert not any(settings.data_dir.parent.glob("Evil*"))

    def test_ifc2x3_upload_is_accepted(self, client: TestClient, session_id: str) -> None:
        response = upload(client, session_id, IFC2X3_TEXT.encode("utf-8"), filename="legacy.ifc")
        assert response.status_code == 201, response.text
        assert response.json()["ifc_schema"] == "IFC2X3"
        assert response.json()["counts"]["IfcWall"] == 1

    @pytest.mark.parametrize("filename", ["notes.txt", "model.ifczip", "model.ifcxml", "model"])
    def test_disallowed_extension_is_415(
        self, client: TestClient, session_id: str, filename: str
    ) -> None:
        response = upload(client, session_id, FIXTURE_BYTES, filename=filename)
        assert_problem(response, 415, "unsupported-upload", detail_contains=".ifc")
        assert_problem(
            client.get(f"{API_PREFIX}/sessions/{session_id}/model/summary"), 404, "model-not-found"
        )

    def test_oversized_upload_is_413(self, client: TestClient, session_id: str) -> None:
        too_big = b"x" * (1024 * 1024 + 1)
        assert_problem(upload(client, session_id, too_big), 413, "upload-too-large")

    def test_malformed_ifc_is_422_without_leaking_paths(
        self, client: TestClient, session_id: str, settings: Settings
    ) -> None:
        response = upload(client, session_id, b"this is not an IFC file")
        assert_problem(response, 422, "ifc-unreadable")
        assert str(settings.data_dir) not in response.text
        assert ".part" not in response.text

    def test_unsupported_schema_is_422(self, client: TestClient, session_id: str) -> None:
        future = IFC2X3_TEXT.replace("FILE_SCHEMA(('IFC2X3'))", "FILE_SCHEMA(('IFC9X9'))")
        response = upload(client, session_id, future.encode("utf-8"))
        assert_problem(response, 422, "unsupported-ifc-schema", detail_contains="IFC9X9")

    def test_empty_upload_is_422(self, client: TestClient, session_id: str) -> None:
        assert_problem(upload(client, session_id, b""), 422, "ifc-unreadable")

    def test_failed_reupload_keeps_the_previous_model(
        self, client: TestClient, loaded_session: str
    ) -> None:
        assert_problem(upload(client, loaded_session, b"garbage"), 422, "ifc-unreadable")
        summary = client.get(f"{API_PREFIX}/sessions/{loaded_session}/model/summary")
        assert summary.status_code == 200
        assert summary.json()["model_hash"] == FIXTURE_HASH
        stored = client.get(f"{API_PREFIX}/sessions/{loaded_session}/model/file")
        assert stored.content == FIXTURE_BYTES

    def test_unknown_session_is_404(self, client: TestClient) -> None:
        response = upload(client, "0f1b7a2e-5c3d-4e8f-9a1b-2c3d4e5f6a7b", FIXTURE_BYTES)
        assert_problem(response, 404, "session-not-found")

    def test_missing_multipart_field_is_422_problem(
        self, client: TestClient, session_id: str
    ) -> None:
        response = client.post(f"{API_PREFIX}/sessions/{session_id}/model")
        assert_problem(response, 422, "request-validation", detail_contains="file")

    def test_ingestion_makes_no_network_calls(
        self, client: TestClient, session_id: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Only loopback sockets (asyncio's own self-pipe) may be opened during ingestion."""
        original_connect = socket.socket.connect

        def guarded_connect(sock: socket.socket, address: object) -> None:
            host = address[0] if isinstance(address, tuple) else address
            if host not in {"127.0.0.1", "::1", "localhost"}:
                raise AssertionError(f"outbound network access during ingestion: {address!r}")
            original_connect(sock, address)  # type: ignore[arg-type]

        def refuse_create_connection(*args: object, **kwargs: object) -> None:
            raise AssertionError(f"outbound network access during ingestion: {args!r}")

        monkeypatch.setattr(socket.socket, "connect", guarded_connect)
        monkeypatch.setattr(socket, "create_connection", refuse_create_connection)
        assert upload(client, session_id, FIXTURE_BYTES).status_code == 201
        assert client.get(f"{API_PREFIX}/sessions/{session_id}/model/summary").status_code == 200
        element = f"{API_PREFIX}/sessions/{session_id}/elements/{GLOBAL_IDS['W-001']}"
        assert client.get(element).status_code == 200


class TestSummary:
    def test_summary_matches_upload_response(self, client: TestClient, session_id: str) -> None:
        uploaded = upload(client, session_id, FIXTURE_BYTES).json()
        fetched = client.get(f"{API_PREFIX}/sessions/{session_id}/model/summary")
        assert fetched.status_code == 200
        assert fetched.json() == uploaded

    def test_summary_before_upload_is_404(self, client: TestClient, session_id: str) -> None:
        response = client.get(f"{API_PREFIX}/sessions/{session_id}/model/summary")
        assert_problem(response, 404, "model-not-found")


class TestModelFile:
    def test_returns_original_bytes_with_sha256_etag(
        self, client: TestClient, loaded_session: str
    ) -> None:
        response = client.get(f"{API_PREFIX}/sessions/{loaded_session}/model/file")
        assert response.status_code == 200
        assert response.content == FIXTURE_BYTES
        assert response.headers["etag"] == f'"{FIXTURE_HASH}"'
        assert response.headers["content-type"].startswith("application/x-step")
        assert response.headers["content-length"] == str(len(FIXTURE_BYTES))
        assert 'filename="model.ifc"' in response.headers["content-disposition"]

    def test_if_none_match_yields_304(self, client: TestClient, loaded_session: str) -> None:
        url = f"{API_PREFIX}/sessions/{loaded_session}/model/file"
        etag = client.get(url).headers["etag"]
        cached = client.get(url, headers={"If-None-Match": etag})
        assert cached.status_code == 304
        assert cached.content == b""
        assert cached.headers["etag"] == etag
        stale = client.get(url, headers={"If-None-Match": '"0000"'})
        assert stale.status_code == 200

    def test_before_upload_is_404(self, client: TestClient, session_id: str) -> None:
        response = client.get(f"{API_PREFIX}/sessions/{session_id}/model/file")
        assert_problem(response, 404, "model-not-found")

    def test_stored_bytes_are_unchanged_on_disk(
        self, client: TestClient, loaded_session: str, settings: Settings
    ) -> None:
        stored = settings.data_dir / "sessions" / loaded_session / "model.ifc"
        assert hashlib.sha256(stored.read_bytes()).hexdigest() == FIXTURE_HASH
        for _ in range(2):
            client.get(f"{API_PREFIX}/sessions/{loaded_session}/model/summary")
            client.get(f"{API_PREFIX}/sessions/{loaded_session}/elements/{GLOBAL_IDS['W-002']}")
        assert hashlib.sha256(stored.read_bytes()).hexdigest() == FIXTURE_HASH


def test_openapi_documents_the_ingestion_surface(client: TestClient) -> None:
    paths = client.get(f"{API_PREFIX}/openapi.json").json()["paths"]
    expected = {
        f"{API_PREFIX}/sessions": {"post"},
        f"{API_PREFIX}/sessions/{{session_id}}": {"get"},
        f"{API_PREFIX}/sessions/{{session_id}}/model": {"post"},
        f"{API_PREFIX}/sessions/{{session_id}}/model/summary": {"get"},
        f"{API_PREFIX}/sessions/{{session_id}}/model/file": {"get"},
        f"{API_PREFIX}/sessions/{{session_id}}/elements/{{global_id}}": {"get"},
    }
    for path, methods in expected.items():
        assert path in paths, path
        assert methods <= set(paths[path]), path
    upload_op = paths[f"{API_PREFIX}/sessions/{{session_id}}/model"]["post"]
    assert {"413", "415", "422"} <= set(upload_op["responses"])


def test_data_dir_is_the_only_place_bytes_land(
    client: TestClient, loaded_session: str, settings: Settings, tmp_path: Path
) -> None:
    written = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert written == [
        f"data/sessions/{loaded_session}/model.ifc",
        f"data/sessions/{loaded_session}/model_index.json",
        f"data/sessions/{loaded_session}/model_summary.json",
        f"data/sessions/{loaded_session}/session.json",
    ]

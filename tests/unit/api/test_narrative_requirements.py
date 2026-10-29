from __future__ import annotations

import hashlib
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bim_intelligence.api.deps import get_llm_client
from bim_intelligence.api.main import API_PREFIX
from bim_intelligence.llm.client import FakeClient
from support.api import assert_problem


def _upload_markdown(client: TestClient, session_id: str) -> tuple[str, str]:
    content = "# Requirements\n\nClassifications shall remain consistent.\n"
    response = client.post(
        f"{API_PREFIX}/sessions/{session_id}/documents",
        files={"file": ("requirements.md", content.encode(), "text/markdown")},
    )
    assert response.status_code == 201, response.text
    return response.json()["sha256"], content


def test_extraction_is_quote_verified_and_requires_explicit_confirmation(
    client: TestClient, session_id: str
) -> None:
    native = client.post(
        f"{API_PREFIX}/sessions/{session_id}/requirements/native/classification-consistency"
    )
    assert native.status_code == 201, native.text
    confirmed = native.json()
    document_id, _ = _upload_markdown(client, session_id)
    fake = FakeClient(
        [
            {
                "candidates": [
                    {
                        "title": "Classification consistency",
                        "statement": "Classifications shall remain consistent.",
                        "quote": "Classifications shall remain consistent.",
                        "location": "p-002",
                        "check_id": confirmed["check"]["id"],
                        "confidence": 0.8,
                    },
                    {
                        "title": "Invented requirement",
                        "statement": "All walls must be blue.",
                        "quote": "All walls must be blue.",
                        "location": "p-002",
                        "check_id": confirmed["check"]["id"],
                        "confidence": 1.0,
                    },
                ]
            }
        ]
    )
    cast(FastAPI, client.app).dependency_overrides[get_llm_client] = lambda: fake
    base = f"{API_PREFIX}/sessions/{session_id}/requirements"
    response = client.post(
        f"{base}/extract",
        json={"document_id": document_id, "document_kind": "markdown"},
    )
    assert response.status_code == 200, response.text
    batch = response.json()
    assert batch["rejected_count"] == 1
    assert len(batch["candidates"]) == 1
    candidate = batch["candidates"][0]
    assert candidate["status"] == "proposed"
    assert candidate["source"]["quote"] == "Classifications shall remain consistent."
    assert [item["id"] for item in client.get(base).json()] == [confirmed["id"]]

    confirmed_candidate = client.post(
        f"{base}/confirm-candidate",
        json={
            "candidate": candidate,
            "check_id": confirmed["check"]["id"],
            "confirmed_by": "reviewer",
        },
    )
    assert confirmed_candidate.status_code == 201, confirmed_candidate.text
    assert confirmed_candidate.json()["source"]["quote"] == candidate["source"]["quote"]
    assert len(client.get(base).json()) == 2


def test_candidate_confirmation_rejects_mismatched_check(
    client: TestClient, session_id: str
) -> None:
    document_id, _ = _upload_markdown(client, session_id)
    candidate = {
        "id": hashlib.sha256(
            f"{document_id}:p-002:Classifications shall remain consistent.".encode()
        ).hexdigest()[:16],
        "title": "Classification consistency",
        "statement": "Classifications shall remain consistent.",
        "source": {
            "document_id": document_id,
            "location": "p-002",
            "quote": "Classifications shall remain consistent.",
        },
        "document_kind": "markdown",
        "check_id": "registered-check",
        "confidence": 0.8,
        "status": "proposed",
    }
    response = client.post(
        f"{API_PREFIX}/sessions/{session_id}/requirements/confirm-candidate",
        json={"candidate": candidate, "check_id": "different-check"},
    )
    assert_problem(response, 422, "requirement-interpretation-invalid")


def test_requirement_extraction_is_disabled_in_off_mode(
    client: TestClient, session_id: str
) -> None:
    document_id, _ = _upload_markdown(client, session_id)
    response = client.post(
        f"{API_PREFIX}/sessions/{session_id}/requirements/extract",
        json={"document_id": document_id, "document_kind": "markdown"},
    )
    assert response.status_code == 503
    assert "disabled" in response.json()["detail"]

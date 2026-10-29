"""Explicit registration and confirmation of the native P0 requirement."""

from __future__ import annotations

from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX
from bim_intelligence.validation import CLASSIFICATION_CONSISTENCY_RULE_ID


def test_native_requirement_confirmation_is_idempotent_and_run_visible(
    client: TestClient, loaded_session: str
) -> None:
    path = f"{API_PREFIX}/sessions/{loaded_session}/requirements/native/classification-consistency"
    first = client.post(path)
    assert first.status_code == 201, first.text
    requirement = first.json()
    assert requirement["origin"] == "builtin"
    assert requirement["status"] == "confirmed"
    assert requirement["confirmed_revision"] == requirement["revision"] == 1
    assert requirement["check"]["kind"] == "native"
    assert requirement["check"]["rule_id"] == CLASSIFICATION_CONSISTENCY_RULE_ID
    assert requirement["check"]["params"] == {}

    repeated = client.post(path)
    assert repeated.status_code == 200
    assert repeated.json() == requirement
    listed = client.get(f"{API_PREFIX}/sessions/{loaded_session}/requirements")
    assert [item["id"] for item in listed.json()] == [requirement["id"]]

    run = client.post(f"{API_PREFIX}/sessions/{loaded_session}/reviews")
    assert run.status_code == 201, run.text
    native_result = next(
        result
        for result in run.json()["check_results"]
        if result["requirement_id"] == requirement["id"]
    )
    assert native_result["status"] == "not_applicable"
    assert native_result["finding_ids"] == []
    assert run.json()["status"] == "partial"

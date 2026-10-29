from __future__ import annotations

from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX


def test_budget_diagnostics_expose_only_safe_application_totals(client: TestClient) -> None:
    response = client.get(f"{API_PREFIX}/llm/budget")
    assert response.status_code == 200, response.text
    status = response.json()
    assert status == {
        "project_budget_usd": 5.0,
        "spent_usd": 0.0,
        "reserved_usd": 0.0,
        "remaining_usd": 5.0,
        "request_count": 0,
    }
    assert "api_key" not in response.text.lower()
    assert "prompt" not in response.text.lower()

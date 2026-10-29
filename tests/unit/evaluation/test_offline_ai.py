from __future__ import annotations

from evaluation.offline_ai import evaluate_offline_ai


def test_offline_t5_safety_contract_is_measured_without_network_or_live_spend() -> None:
    result = evaluate_offline_ai()

    assert result["total"] == 9
    assert result["passed"] == 9
    assert all(result["checks"].values())
    assert result["network_calls"] == 0
    assert result["live_api_calls"] == 0
    assert result["live_spend_usd"] == "0"
    assert "not live Muse Spark performance" in result["classification"]

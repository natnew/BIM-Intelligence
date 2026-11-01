"""Regression: the hermetic environment fixture must not hide owner configuration from live tests.

Before the fix, the autouse fixture stripped ``LLM_MODE`` and ``MODEL_API_KEY`` from every test,
so the named T-5 smoke test failed its own configuration guard before it could send a request.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bim_intelligence.config import Settings

ROOT_CONFTEST = Path(__file__).resolve().parents[1] / "conftest.py"

INNER_TESTS = """
import os

import pytest

from bim_intelligence.config import Settings


def test_ordinary_tests_stay_hermetic():
    assert "LLM_MODE" not in os.environ
    assert Settings.model_config["env_file"] is None


@pytest.mark.live
def test_live_tests_keep_owner_configuration():
    assert os.environ["LLM_MODE"] == "replay"
    assert Settings.model_config["env_file"] == ".env"
"""


def test_live_marked_tests_keep_configuration_while_others_stay_isolated(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    # This outer test is itself isolated; restore the production-like state for the inner run.
    monkeypatch.setenv("LLM_MODE", "replay")
    monkeypatch.setitem(Settings.model_config, "env_file", ".env")
    pytester.makeini("[pytest]\nmarkers =\n    live: owner-approved live test\n")
    pytester.makeconftest(ROOT_CONFTEST.read_text(encoding="utf-8"))
    pytester.makepyfile(test_inner_isolation=INNER_TESTS)

    result = pytester.runpytest_inprocess("-p", "no:cacheprovider")

    result.assert_outcomes(passed=2)

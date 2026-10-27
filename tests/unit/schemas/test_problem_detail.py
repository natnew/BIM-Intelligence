"""ProblemDetail follows RFC 9457 so every API error has one shape (ARCHITECTURE §14)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bim_intelligence.schemas import ProblemDetail


def test_minimal_problem_defaults_type_to_about_blank() -> None:
    problem = ProblemDetail(title="Not Found", status=404)
    assert problem.type == "about:blank"
    assert problem.detail is None
    assert problem.instance is None
    assert problem.correlation_id is None


def test_full_problem_round_trips() -> None:
    problem = ProblemDetail(
        type="https://bim-intelligence.dev/problems/run-active",
        title="A review run is already active",
        status=409,
        detail="Wait for run run-0001 to finish before starting another.",
        instance="/api/v1/sessions/sess-0001/reviews",
        correlation_id="7b2e4f1a",
    )
    assert ProblemDetail.model_validate_json(problem.model_dump_json()) == problem


@pytest.mark.parametrize("status", [99, 600])
def test_status_must_be_an_http_status_code(status: int) -> None:
    with pytest.raises(ValidationError):
        ProblemDetail(title="x", status=status)


def test_title_is_required() -> None:
    with pytest.raises(ValidationError):
        ProblemDetail.model_validate({"status": 500})

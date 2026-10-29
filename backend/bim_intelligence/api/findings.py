"""Findings of a published run (FR-VIS-02, FR-VAL-07)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from bim_intelligence.api.deps import get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.schemas import Finding, Severity
from bim_intelligence.store import SessionStore

router = APIRouter(tags=["findings"])


@router.get(
    "/sessions/{session_id}/findings",
    response_model=list[Finding],
    summary="List findings",
    description=(
        "The findings of one run in canonical order — the same order and content as the "
        "run's ``findings.json``, so two runs over identical inputs return identical bodies. "
        "Each finding names the check, requirement, rule id and version, facet, affected "
        "elements (GlobalId, express id, type, name, storey), the value IfcTester observed and "
        "the requirement it expected. ``method`` is always ``ids`` or ``native``; nothing here "
        "is model-generated. Optional filters narrow by severity, rule id or storey name."
    ),
    responses=problem_responses(400, 404, 422),
)
def list_findings(
    session_id: str,
    run_id: str = Query(description="Run whose findings to list."),
    severity: Severity | None = Query(default=None),
    rule_id: str | None = Query(default=None, description="Exact rule id, e.g. ``ids:<name>``."),
    storey: str | None = Query(default=None, description="Exact storey name of an element."),
    store: SessionStore = Depends(get_store),
) -> list[Finding]:
    findings = store.read_findings(session_id, run_id)
    return [
        finding
        for finding in findings
        if (severity is None or finding.severity == severity)
        and (rule_id is None or finding.rule_id == rule_id)
        and (storey is None or any(element.storey == storey for element in finding.elements))
    ]

"""Findings of a published run (FR-VIS-02, FR-VAL-07)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from bim_intelligence.api.deps import get_llm_client, get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.bim.ingest import load_index
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.orchestration import LLMClient
from bim_intelligence.reporting import explain_finding
from bim_intelligence.schemas import Explanation, Finding, Severity
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


@router.post(
    "/sessions/{session_id}/reviews/{run_id}/findings/{finding_id}/explanation",
    response_model=Explanation,
    summary="Explain one verified finding",
    description=(
        "Returns a separately labelled AI interpretation grounded in the run's deterministic "
        "Finding, its pinned IFC model index and the matching confirmed requirement revision. "
        "If the client is off or grounding fails, a deterministic template is returned. "
        "Explanations are never written to findings.json."
    ),
    responses=problem_responses(400, 404, 409),
)
def explain_review_finding(
    session_id: str,
    run_id: str,
    finding_id: str,
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    client: LLMClient | None = Depends(get_llm_client),
) -> Explanation:
    with store.lock_model(session_id):
        run = store.read_run(session_id, run_id)
        if finding_id not in run.finding_ids:
            raise HTTPException(status_code=404, detail="Finding not found in this review run.")
        finding = next(
            (item for item in store.read_findings(session_id, run_id) if item.id == finding_id),
            None,
        )
        if finding is None:
            raise HTTPException(status_code=404, detail="Finding not found in this review run.")
        requirement = next(
            (
                item
                for item in store.read_requirements(session_id)
                if item.id == finding.requirement_id
                and run.input_manifest.requirement_revisions.get(item.id) == item.revision
            ),
            None,
        )
        if requirement is None:
            raise HTTPException(
                status_code=409,
                detail="The requirement revision used by this run is no longer available.",
            )
        index = load_index(store.model_version(session_id, run.input_manifest.model_hash))
        return explain_finding(
            finding,
            requirement,
            index,
            client,
            run_id=run_id,
            max_output_tokens=settings.llm_max_output_tokens_per_call,
        )

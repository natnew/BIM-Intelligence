"""Findings of a published run and their separately labelled explanations.

Serves FR-VIS-02 (findings) and FR-EXP-02, FR-EXP-03, FR-EXP-05 and FR-AI-01 (explanations).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from bim_intelligence.api.deps import get_llm_client, get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.api.versioning import if_match_sha256
from bim_intelligence.bim.ingest import load_index
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.orchestration import LLMClient
from bim_intelligence.reporting import (
    ExplanationProvenanceError,
    RunModelMismatchError,
    explain_finding,
    resolve_finding_provenance,
    verify_index_provenance,
)
from bim_intelligence.schemas import Explanation, Finding, Severity
from bim_intelligence.store import IncompleteModelVersionError, SessionStore

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
        "Returns an interpretation of one deterministic Finding the run recorded, labelled by "
        "``source`` and ``grounding_status``. Before any evidence is assembled the server "
        "verifies that the stored run identity matches the requested run and session, "
        "the finding belongs to the run and to "
        "the check result that recorded it, the confirmed requirement revision, its check "
        "identity, rule version and source document match the run's input manifest, and the "
        "model index is the run's pinned model version with the finding's elements unchanged; "
        "any disagreement is 409 ``explanation-provenance-mismatch``. An unknown finding is "
        "404 ``finding-not-found``. ``If-Match`` names the model version the client is "
        "viewing; one other than the run's model is 412 ``model-version-mismatch``. When the "
        "client is off, a budget or call limit is reached, the request or response fails, or "
        "the output cites anything outside the evidence, a deterministic template is returned "
        "with ``source=deterministic_template``, ``grounding_status=fallback`` and a "
        "``fallback_reason``. An ``ai_generated`` explanation has passed grounding and names "
        "its model. Explanations are never written to ``findings.json`` and never create or "
        "change a Finding."
    ),
    responses=problem_responses(400, 404, 409, 412),
)
def explain_review_finding(
    session_id: str,
    run_id: str,
    finding_id: str,
    request: Request,
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    client: LLMClient | None = Depends(get_llm_client),
) -> Explanation:
    pinned_model_hash = if_match_sha256(request)
    with store.lock_model(session_id):
        run = store.read_run(session_id, run_id)
        if run.id != run_id:
            raise ExplanationProvenanceError(
                run_id, "The stored run identity does not match the requested run."
            )
        model_hash = run.input_manifest.model_hash
        if pinned_model_hash is not None and pinned_model_hash != model_hash:
            raise RunModelMismatchError(run.id, pinned_model_hash, model_hash)
        finding, requirement = resolve_finding_provenance(
            session_id,
            run,
            store.read_findings(session_id, run_id),
            store.read_requirements(session_id),
            finding_id,
        )
        try:
            index = load_index(store.model_version(session_id, model_hash))
        except IncompleteModelVersionError as exc:
            raise ExplanationProvenanceError(
                run.id, "The run's model version is no longer available."
            ) from exc
        verify_index_provenance(run, finding, index)
    # Published runs and model versions are immutable, so the bounded model call runs after the
    # lock is released rather than blocking uploads and reviews for its duration.
    return explain_finding(
        finding,
        requirement,
        index,
        client,
        run_id=run_id,
        max_output_tokens=settings.llm_max_output_tokens_per_call,
    )

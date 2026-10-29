# Delivery Plan and Engineering Task Register

**Reconciled:** 29 October 2026 | **Delivery window:** Monday 26 October – Wednesday 4 November 2026 | **Deadline:** Wednesday 4 November 2026; this plan does not move it.
**Status:** The repository is partially implemented. Task and milestone statuses below reflect available code, tests, commits and merged PR evidence as of this reconciliation.

Requirement IDs refer to [REQUIREMENTS.md](./REQUIREMENTS.md); architectural decisions refer to [DECISIONS.md](./DECISIONS.md). The design baseline and implementation evidence are documented in [ARCHITECTURE.md](./ARCHITECTURE.md), and evaluation objectives and results in [EVALUATION.md](./EVALUATION.md).

## 1. Delivery framework

**Milestones describe delivery capabilities; tasks describe engineering work.** A task can contribute to more than one milestone, and a milestone can depend on several tasks. A completed task is evidence toward a milestone, not proof that its exit criteria have been met.

The original M0–M4 milestones remain in force. T-0–T-8 were added to break the milestone outcomes into bounded engineering work that can be implemented, tested and evidenced. T-1.1 is an additional corrective subtask, not a renumbering of T-2–T-8.

T-1.1 followed the T-1 architecture review. Publishing a new IFC, index and summary as separate visible writes could leave readers observing a mixed model version during a replacement. The corrective task prepares and validates a content-addressed version before atomically activating it through the session record; it also adds upload locking, recovery and version-bound reads. See [ADR-017](./DECISIONS.md#adr-017-content-addressed-model-versions-with-single-pointer-publication) and [PR #5](https://github.com/natnew/BIM-Intelligence/pull/5).

Task status is determined by implementation and acceptance evidence, not by a plan checkbox, a label, or a verbal claim. Milestone status is determined by its full exit criteria. A test result verifies only the behaviour it covers; in particular, a Meta API smoke test alone cannot complete T-5.

Status vocabulary for tasks: `Not started`, `In progress`, `Implemented — verification pending`, `Verified`, `Blocked`, `Deferred`. `Verified` requires the relevant acceptance evidence to be recorded. A milestone is `Verified` only when every exit criterion has evidence; otherwise its status is `In progress` or `Not started`.

## 2. Milestone-to-task mapping

| Milestone | Contributing task IDs | Expected deliverables | Dependencies | Measurable exit criteria | Status | Supporting evidence |
|---|---|---|---|---|---|---|
| **M0 — Foundations** | T-0, T-1, T-1.1; T-3 viewer spike; T-5 Meta API capability spike | Reproducible schemas and fixtures; safe IFC ingestion and a working model API; atomic model publication; initial viewer and Meta API integration risks assessed. | None. The T-3 spike requires the T-1 API and fixture; the T-5 spike requires explicit approval before any paid/live call. | Contract/type-generation and fixture tests pass; fixture upload produces a matching model summary; replacement/read consistency tests pass; a basic viewer load/GlobalId highlight and the authorised structured-output/tool-call API spike are demonstrated or explicitly approved as deferred. The original viewer and LLM spike intent is not silently removed. | **In progress** — backend foundation is verified; both spikes remain open. | [T-0–T-1.1 history](../CHANGELOG.md#verified-implementation-history); [T-1.1 ADR](./DECISIONS.md#adr-017-content-addressed-model-versions-with-single-pointer-publication); README development-status table. |
| **M1 — Deterministic Review** | T-2, T-4, T-6 | IDS validation, native rule families, an end-to-end LLM-free review, benchmark ground truth and reproducible evaluation evidence. | M0; T-4 builds on T-2; T-6 can start after T-2 and run alongside T-4. | IDS results are cross-checked against IfcTester; required P0 native-rule tests pass; fixture review runs without an LLM; benchmark precision/recall, clean-control false positives and determinism are reported from a reproducible labelled dataset. | **In progress** — T-2 is verified; native rules, the full deterministic workflow and benchmark are outstanding. | [PR #6](https://github.com/natnew/BIM-Intelligence/pull/6); [evaluation design](./EVALUATION.md); no benchmark result is recorded. |
| **M2 — AI-Native Review** | T-4, T-5 | Meta Muse Spark-assisted requirement interpretation and objective planning, filtered against confirmed checks, with explanations grounded in deterministic evidence and a usable no-LLM fallback. | M1 deterministic execution; T-5's full integration depends on T-4. API capability verification can run independently. | Scenario tests with FakeClient/Replay cover extraction, quote verification, confirmation, plan filtering, tool caps, grounded explanations and degraded mode; any live test is explicitly authorised. A smoke test alone is insufficient. | **Not started** — no LLM client, extraction, planner or explainer implementation is evidenced. | [README development-status table](../README.md#development-status); [T-5 register](#t-5--meta-muse-spark-integration). |
| **M3 — Demo-Ready Product** | T-3, T-4, T-6, T-7 | Interactive viewer and finding coordination; traceable report; integrated workflow, tested fallback and a rehearsed demonstration. | M1 and M2; T-3 can proceed after T-1 and in parallel with T-4–T-6. T-7 integrates T-3, T-4, T-5 and T-6. | A tested browser walkthrough uses the benchmark/fixture, selection and highlighting work for a finding, reports preserve provenance, fallback works, and the smoke test and documented setup pass. | **Not started** — no viewer, report or integrated demonstration is evidenced. | [Demo requirements](./DEMO_PLAN.md); [README development-status table](../README.md#development-status). |
| **M4 — Submission** | T-8, supported by all previous completed tasks | Final hardening, verified documentation, measured evaluation results, recorded demo and owner-approved submission actions. | M3 and evidence from all applicable preceding tasks. | Final test and secret-scan evidence is recorded; claims match measured behaviour; demo and results are available; submission requirements are checked against official rules. Release, tagging or submission actions require owner approval. | **Not started** — deadline is fixed; no final evaluation, demo or submission evidence exists. | [Demo plan](./DEMO_PLAN.md); [evaluation results](./EVALUATION.md#8-results) currently states that no results exist. |

No milestone is complete solely because its contributing task labels exist. Original exit requirements remain outstanding unless explicitly met or superseded with project-owner approval.

## 3. Engineering task register

### T-0 — Schemas and Minimal IFC Fixture

- **Objective:** Establish the typed domain contract and a small, reproducible IFC/IDS fixture.
- **Responsible components:** `backend/bim_intelligence/schemas/`, `scripts/export_schemas.py`, `frontend/src/api/generated/`, `tests/fixtures/`.
- **Deliverables:** Core Pydantic schemas and generated TypeScript contract; minimal IFC and IDS fixture-generation script.
- **Dependencies:** None.
- **Acceptance tests:** Schema and canonicalisation unit tests pass; generated contract checks pass; fixture is reproducible and has the documented IDS outcomes.
- **Status:** **Verified.**
- **Milestones:** M0.
- **Evidence:** Commit [`be45c7c`](https://github.com/natnew/BIM-Intelligence/commit/be45c7c), 27 October 2026; the implementation record reports 112 passing backend tests at that point. See [ADR-015](./DECISIONS.md#adr-015-contract-model-immutable-checkspec-content-addressed-finding-per-check-checkresult).

### T-1 — IFC Ingestion, Model Indexing and Session Persistence

- **Objective:** Accept a read-only IFC upload, build a queryable model index and persist session state.
- **Responsible components:** `store/`, `bim/`, `schemas/`, `api/`, `tests/unit/`.
- **Deliverables:** Session store; IFC loading/indexing; session, upload, summary and element lookup endpoints; structured errors.
- **Dependencies:** T-0.
- **Acceptance tests:** Fixture and in-memory IFC variants cover indexing, relationships, malformed and duplicate GlobalIds, upload limits and API errors; uploaded bytes remain unchanged; upload-to-summary smoke test passes.
- **Status:** **Verified.**
- **Milestones:** M0.
- **Evidence:** [PR #4](https://github.com/natnew/BIM-Intelligence/pull/4), commit [`de63de8`](https://github.com/natnew/BIM-Intelligence/commit/de63de8), 28 October 2026; the implementation record reports 283 passing backend tests. See [ADR-016](./DECISIONS.md#adr-016-ingestion-contract-staged-upload-content-hash-etag-and-identifier-handling).

### T-1.1 — Model Publication Consistency

- **Objective:** Prevent mixed-version reads when replacing a session's active IFC model.
- **Responsible components:** `store/`, `bim/`, model/session API and their unit tests.
- **Deliverables:** Content-addressed model-version directories, private staging and validation, atomic pointer activation, per-session upload locking, abandoned-stage recovery and version-bound reads.
- **Dependencies:** T-1.
- **Acceptance tests:** Failure injection across publication steps; concurrent upload and reader tests at store and HTTP level; restart/recovery and ETag/If-Match tests.
- **Status:** **Verified.**
- **Milestones:** M0.
- **Evidence:** [PR #5](https://github.com/natnew/BIM-Intelligence/pull/5), commit [`b1fd054`](https://github.com/natnew/BIM-Intelligence/commit/b1fd054), 29 October 2026; the implementation record reports 334 passing backend tests and clean `ruff`/`mypy`. See [ADR-017](./DECISIONS.md#adr-017-content-addressed-model-versions-with-single-pointer-publication).

### T-2 — Deterministic IDS Validation

- **Objective:** Import IDS 1.0 specifications as confirmed requirements and execute each through IfcTester, producing reproducible deterministic results.
- **Responsible components:** `requirements/ids_import.py`, `validation/`, review and findings API, schemas and unit tests.
- **Deliverables:** IDS import and validation, immutable check definitions, per-check results, normalised findings and synchronous review endpoints.
- **Dependencies:** T-0, T-1 and T-1.1.
- **Acceptance tests:** Malformed/non-IDS inputs return structured errors; IDS results are cross-checked against IfcTester's JSON report; the minimal fixture produces its two expected findings; repeated runs produce byte-identical `findings.json`; the default test suite makes no live API call.
- **Status:** **Verified.**
- **Milestones:** M1.
- **Evidence:** [PR #6](https://github.com/natnew/BIM-Intelligence/pull/6), commit [`a480483`](https://github.com/natnew/BIM-Intelligence/commit/a480483), 29 October 2026. The PR validation record reports `ruff`, `mypy`, 461 backend tests and frontend lint, typecheck, tests, build, format and generated-type checks passing. See [ADR-018](./DECISIONS.md#adr-018-ids-import-establishes-confirmed-requirements-checks-are-hydrated-per-run-reviews-run-under-the-session-lock).

### T-3 — Interactive 3D BIM Viewer

- **Objective:** Load the current IFC version in the browser and connect model selection to finding selection/highlighting.
- **Responsible components:** `frontend/src/viewer/`, viewer adapter and frontend panels.
- **Deliverables:** Initial viewer spike (load, GlobalId-to-fragment resolution, highlight, viewer click); then integrated viewer and two-way finding/model selection.
- **Dependencies:** T-1 fixture and model API. The prerequisite is available; viewer development can proceed independently of T-4–T-6.
- **Acceptance tests:** Load the minimal model; highlight a known GlobalId; verify finding-to-viewer and viewer-to-element selection; exercise loading, error and empty states and the planned browser smoke test.
- **Status:** **Not started.**
- **Milestones:** M0 (viewer spike), M3 (finished interface).
- **Evidence:** No viewer implementation is present in the reconciled source inventory; the viewer spike is recorded as outstanding in the earlier implementation plan and ADR-007.

### T-4 — End-to-End Deterministic Review Workflow

- **Objective:** Complete the LLM-free path from a model and confirmed checks to a review plan, deterministic execution, findings and traceable results.
- **Responsible components:** `validation/`, `orchestration/`, review API, schemas, scenario tests and findings API.
- **Deliverables:** Native rule families; bounded/default deterministic execution over supported checks; complete LLM-off review path and scenario coverage. The IDS-only review delivered in T-2 is a verified slice, not by itself completion of this broader task.
- **Dependencies:** T-2; T-0 and T-1.1 contracts/versioning.
- **Acceptance tests:** Positive, negative and boundary unit tests for every shipped native rule; scenario test on the fixture with LLM off; schema-valid results; deterministic output on repeated runs; per-check errors never appear as passing checks.
- **Status:** **In progress** — the IDS-only deterministic review path is implemented under T-2; native rules and the complete task acceptance suite remain outstanding.
- **Milestones:** M1, M2 (integration seam), M3.
- **Evidence:** [T-2 implementation](https://github.com/natnew/BIM-Intelligence/pull/6); the README and source inventory show no native rule families yet.

### T-5 — Meta Muse Spark Integration

- **Objective:** Add bounded model-assisted requirement extraction, objective planning and grounded explanations without allowing the model to create findings or bypass human approval.
- **Responsible components:** `llm/`, `requirements/`, `orchestration/`, `reporting/`, versioned prompt files and tests.
- **Deliverables:** Meta API capability spike; provider protocol and Fake/Recording/Replay clients; BEP extraction with verbatim quote checks and human confirmation; filtered planner; grounded explanation with deterministic fallback and token accounting.
- **Dependencies:** T-4 for full integration; T-0 schemas. The API capability check can run independently but any paid/live call requires explicit session approval under C-06 and AGENTS.md §9.
- **Acceptance tests:** Fake/Replay scenario tests cover valid and invalid model output, quote rejection, unconfirmed checks, unknown/invalid tools, caps, grounding rejection and fallback. A live smoke test is optional evidence only and does not complete this task.
- **Status:** **Not started.**
- **Milestones:** M0 (API capability spike), M2 (integrated AI-native workflow).
- **Evidence:** No `llm/` implementation, prompt package or completed API spike is evidenced; see [ADR-002](./DECISIONS.md#adr-002-meta-model-api-via-the-openai-python-sdk), [ADR-008](./DECISIONS.md#adr-008-human-confirmation-of-extracted-requirements) and [ADR-009](./DECISIONS.md#adr-009-deterministic-grounding-check-on-every-explanation).

### T-6 — Benchmark and Evaluation

- **Objective:** Measure deterministic finding quality and reproducibility on labelled, redistributable test data.
- **Responsible components:** `datasets/`, `tests/evaluation/`, `docs/EVALUATION.md`.
- **Deliverables:** Synthetic benchmark, defect specification and ground truth; repeatable metric runner; dated results with commit reference.
- **Dependencies:** T-2 for initial preparation and IDS baseline; T-4 native rules for full rule-family evaluation. Preparation can run in parallel with integration.
- **Acceptance tests:** Dataset is reproducible; clean controls yield no false positives; per-rule and aggregate precision/recall and determinism are reported; any thresholds and limitations are stated; no metric is claimed before a recorded run.
- **Status:** **Not started.**
- **Milestones:** M1, M3, M4.
- **Evidence:** [EVALUATION.md](./EVALUATION.md) records a design only and explicitly states that no evaluation or metric exists.

### T-7 — Reporting, Interface Refinement and Demonstration Readiness

- **Objective:** Integrate the review workflow into a usable interface and present traceable findings and reports with a reliable demo fallback.
- **Responsible components:** `frontend/`, `reporting/`, browser/scenario tests and demo artefacts.
- **Deliverables:** Requirement and objective panels; findings/detail views; model highlighting; JSON/Markdown report with provenance; replay/off mode; rehearsed demo.
- **Dependencies:** T-3, T-4, T-5 and T-6. Begin integration as dependencies become testable, without treating incomplete upstream work as finished.
- **Acceptance tests:** Full browser walkthrough on the benchmark; findings link to their deterministic checks and model elements; report provenance is complete; replay/degraded mode works; browser smoke test passes.
- **Status:** **Not started.**
- **Milestones:** M3.
- **Evidence:** [DEMO_PLAN.md](./DEMO_PLAN.md) defines the intended walkthrough; no integrated interface, report or demo evidence exists in the source inventory.

### T-8 — Final Hardening, Documentation and Submission

- **Objective:** Complete final engineering verification and prepare evidence-backed documentation and owner-approved submission materials.
- **Responsible components:** Whole repository, CI, `README.md`, `docs/`, `CHANGELOG.md`, evaluation and demo evidence.
- **Deliverables:** Final regression/security/hygiene checks; clean-checkout setup verification; measured results; consistent public documentation; recorded demo and submission checklist.
- **Dependencies:** T-0 through T-7 as applicable; M3 exit.
- **Acceptance tests:** Agreed backend and frontend checks pass; secret scan and documentation/link checks are clean; setup reproduces; metrics link to a run and commit; demo is available; official submission requirements are checked. Release/tag/submission actions require project-owner approval.
- **Status:** **In progress — delivery-framework documentation is being reconciled here; final hardening, demo and submission acceptance have not been completed.** This documentation change does not establish product functionality or M4 completion.
- **Milestones:** M4.
- **Evidence:** This plan, [AGENTS.md §11](../AGENTS.md#11-delivery-milestones-engineering-tasks-and-progress-tracking) and [CHANGELOG.md](../CHANGELOG.md) establish the tracking requirements; final task evidence remains outstanding.

## 4. Revised delivery schedule

The original ten-day window is retained. The weekday labels below are corrected to the 2026 calendar: 26 October was Monday, not Sunday; 4 November is Wednesday. Historical completion dates below remain as recorded by commits/PRs; the schedule is not backdated or shifted to disguise slippage.

| Date | Day | Original plan context | Recorded implementation or current target |
|---|---|---|---|
| 26 Oct | Monday — Day 1 | Architecture baseline and initial LLM/viewer spikes planned. | Architecture baseline is recorded in Git on 27 Oct ([PR #1](https://github.com/natnew/BIM-Intelligence/pull/1)); neither integration spike is evidenced as complete. |
| 27 Oct | Tuesday — Day 2 | Repository foundations and T-0. | T-0 and the scaffold landed; see [T-0 commit](https://github.com/natnew/BIM-Intelligence/commit/be45c7c) and [PR #2](https://github.com/natnew/BIM-Intelligence/pull/2). |
| 28 Oct | Wednesday — Day 3 | IFC ingestion and model indexing. | T-1 delivered via [PR #4](https://github.com/natnew/BIM-Intelligence/pull/4). |
| 29 Oct | Thursday — Day 4 | Original plan targeted benchmark/evaluation; its metric exit was not achieved. | T-1.1 and T-2 delivered via [PR #5](https://github.com/natnew/BIM-Intelligence/pull/5) and [PR #6](https://github.com/natnew/BIM-Intelligence/pull/6). No benchmark or measured metric exists. |
| 30 Oct | Friday — Day 5 | Original plan targeted the requirements interpreter. | Target: advance T-4 deterministic workflow; start T-3 viewer and T-6 benchmark preparation; verify Meta API capability only with required owner approval. |
| 31 Oct–1 Nov | Saturday–Sunday — Days 6–7 | Original plan targeted orchestration and frontend integration. | Target: progress T-3 and T-6 in parallel; integrate T-5 after T-4 is testable; record API verification outcome or blocker. |
| 2 Nov | Monday — Day 8 | Original plan targeted report, hardening and docs. | Target: T-7 integration of available viewer/workflow/evaluation pieces; complete T-3 and T-6 acceptance where feasible. |
| 3 Nov | Tuesday — Day 9 | Original plan reserved a buffer and rehearsal. | Target: T-7 demo rehearsal; T-8 regression, documentation, setup and security checks. Protect this as the only full buffer day. |
| 4 Nov | Wednesday — Day 10 | Submission deadline. | T-8 final evidence and demo; any release or submission action only with owner approval. **Deadline unchanged.** |

This is a dependency-aware target, not a claim that the remaining work will fit. The original M1 benchmark exit was due on 29 October and remains unmet; preserve that historical fact in status and later reporting.

### Critical path and parallel work

```mermaid
flowchart LR
    T0["T-0 contracts and fixture"] --> T1["T-1 ingestion"]
    T1 --> T11["T-1.1 publication consistency"]
    T11 --> T2["T-2 IDS validation"]
    T2 --> T4["T-4 deterministic workflow"]
    T4 --> T5["T-5 integrated Meta workflow"]
    T5 --> T7["T-7 demo integration"]
    T7 --> T8["T-8 hardening and submission"]
    T11 --> T3["T-3 viewer"]
    T3 --> T7
    T2 --> T6["T-6 benchmark and evaluation"]
    T6 --> T7
    SPIKE["T-5 API capability check<br/>approval required for paid/live call"] --> T5
```

**Critical path:** T-2 → T-4 deterministic workflow → T-5 Meta integration → T-7 demo integration → T-8 submission. A slip on this path reduces the time available for integration and final evidence; it does not move the deadline.

**Parallel work:** T-3 can start because the T-1 API and fixture are available. T-6 preparation can begin after T-2 and proceed alongside integration. T-5's API capability check can be investigated independently of full T-5 implementation, but no paid/live call may be made without explicit authorisation.

## 5. Delivery risk and scope control

### Critical blockers and effects of slippage

| Blocker or slip | Delivery impact | Response |
|---|---|---|
| T-4 deterministic path does not complete | T-5 cannot be integrated against a complete, stable deterministic workflow; M1 remains open. | Prioritise no-LLM scenarios and native-rule acceptance; do not make an AI-only demonstration stand in for deterministic verification. |
| T-5 API capability or integration fails | M2 cannot be claimed; M3 must use an explicitly labelled replay/off fallback and M4 must not overstate AI functionality or hackathon eligibility. | Record the blocker, keep deterministic review usable, and seek owner direction; no unauthorised paid call. |
| T-3 viewer slips | M0 viewer-spike and M3 interactive-viewer criteria remain unmet. | Start in parallel against the available fixture/API; if scope must change, get approval and state the reduced viewer capability explicitly. |
| T-6 benchmark slips | No measured precision/recall claim is supportable; M1 and M4 evidence remain incomplete. | Prefer a small labelled, reproducible benchmark over unlabelled headline metrics; report limitations and results honestly. |
| T-7 integration slips | No complete browser walkthrough, report or reliable demo is evidenced. | Freeze optional polish first; retain the core review, finding traceability and fallback. |
| Any work slips past 3 Nov | There is no schedule margin before the fixed 4 Nov deadline. | Stop optional scope, report the gap and obtain the owner's decision; do not silently move dates or claim completion. |

### Minimum credible submission

The minimum credible technical demonstration should run the verified IFC/IDS path on the reproducible fixture, show deterministic findings with their check and element provenance, and present only capabilities that have passed their stated tests. A wider demo should add the T-4 no-LLM workflow, T-3 viewer, T-7 report/interface, and measured T-6 evidence as those slices become verified. Hackathon eligibility cannot be confirmed from repository evidence alone because the official rules remain unverified; do not describe a reduced or replay-only path as eligible without checking them.

### Capabilities that must not be cut

- Deterministic-only creation of `Finding`; the model must never assert model facts.
- Read-only IFC handling and model-version consistency.
- Requirement quote verification and human confirmation before any model-proposed requirement runs.
- Plan filtering, tool-call limits and schema validation for model outputs.
- Grounding checks and deterministic explanation fallback.
- Traceability from requirement through check and finding to model element.
- Safe defaults, no secret exposure and no paid/live API call without owner approval.

### Features that may be deferred, subject to owner approval

Optional P1/P2 rules, BCF export, explanation grouping/cache, PDF requirement ingestion, UI polish, and viewer click-to-select may be deferred if the P0 acceptance contract permits it. The original plan's viewer simplification still requires an initial usable GlobalId highlight path. Do not cut an integrity guarantee or silently change an accepted requirement, architecture decision or public scope.

### Evidence required before claiming completion

- Link the implementation commit/PR and the tests that cover the acceptance criteria.
- Record exact test commands and results; distinguish PR-recorded evidence from checks run during this reconciliation.
- For benchmark claims, link the reproducible dataset, run, metrics, date and commit; no result may be inferred from a plan.
- For paid/live model behaviour, record explicit owner approval and use replay/FakeClient tests for the default suite.
- For a milestone, provide evidence for every exit criterion, not merely the mapped task completion.
- Update this task register and `CHANGELOG.md` together when substantive status or scope changes.

## 6. Reconciliation notes and outstanding discrepancies

- The original milestone structure and intent are retained; task IDs supplement rather than replace it.
- The previous plan's weekday labels were incorrect. Correct dates are shown above; commit and PR completion dates are preserved.
- The implementation plan previously described as “nothing implemented” is stale. T-0, T-1, T-1.1 and T-2 are verified against implementation records, tests and PR evidence.
- The pasted reconciliation request asks to verify “all eleven task identifiers”, but its enumerated framework defines T-0 through T-8 (nine IDs) plus T-1.1 (one more): **ten distinct task identifiers**. No eleventh task is defined. This register covers all ten rather than inventing an ID.
- The hackathon rules and any eligibility criteria remain unverified; see [REQUIREMENTS.md §7](./REQUIREMENTS.md#7-open-items). No submission eligibility claim is made here.
- No evaluation has been run; [EVALUATION.md §8](./EVALUATION.md#8-results) remains authoritative for measured results.

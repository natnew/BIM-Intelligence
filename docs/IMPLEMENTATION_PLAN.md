# Delivery Plan and Engineering Task Register

**Reconciled:** 3 November 2026 | **Delivery window:** Monday 26 October – Wednesday 4 November 2026 | **Deadline:** Wednesday 4 November 2026; this plan does not move it.
**Status:** The repository is partially implemented. Task and milestone statuses below reflect available code, tests, commits and merged PR evidence as of this reconciliation.

Requirement IDs refer to [REQUIREMENTS.md](./REQUIREMENTS.md); architectural decisions refer to [DECISIONS.md](./DECISIONS.md). The design baseline and implementation evidence are documented in [ARCHITECTURE.md](./ARCHITECTURE.md), and evaluation objectives and results in [EVALUATION.md](./EVALUATION.md).

The owner-directed final 48-hour delivery overlay, internal 3 November target and conditional
coordination gate are recorded in [FINAL_48_HOUR_PLAN.md](./FINAL_48_HOUR_PLAN.md). This overlay
does not complete T-7/M3 or T-8/M4 and does not move the 4 November submission date.

## 1. Delivery framework

**Milestones describe delivery capabilities; tasks describe engineering work.** A task can contribute to more than one milestone, and a milestone can depend on several tasks. A completed task is evidence toward a milestone, not proof that its exit criteria have been met.

The original M0–M4 milestones remain in force. T-0–T-8 were added to break the milestone outcomes into bounded engineering work that can be implemented, tested and evidenced. T-1.1 is an additional corrective subtask, not a renumbering of T-2–T-8.

T-1.1 followed the T-1 architecture review. Publishing a new IFC, index and summary as separate visible writes could leave readers observing a mixed model version during a replacement. The corrective task prepares and validates a content-addressed version before atomically activating it through the session record; it also adds upload locking, recovery and version-bound reads. See [ADR-017](./DECISIONS.md#adr-017-content-addressed-model-versions-with-single-pointer-publication) and [PR #5](https://github.com/natnew/BIM-Intelligence/pull/5).

Task status is determined by implementation and acceptance evidence, not by a plan checkbox, a label, or a verbal claim. Milestone status is determined by its full exit criteria. A test result verifies only the behaviour it covers; in particular, a Meta API smoke test alone cannot complete T-5.

Status vocabulary for tasks: `Not started`, `In progress`, `Implemented — verification pending`, `Verified`, `Blocked`, `Deferred`. `Verified` requires the relevant acceptance evidence to be recorded. A milestone is `Verified` only when every exit criterion has evidence; otherwise its status is `In progress` or `Not started`.

## 2. Milestone-to-task mapping

| Milestone | Contributing task IDs | Expected deliverables | Dependencies | Measurable exit criteria | Status | Supporting evidence |
|---|---|---|---|---|---|---|
| **M0 — Foundations** | T-0, T-1, T-1.1; T-3 viewer spike; T-5 Meta API capability spike | Reproducible schemas and fixtures; safe IFC ingestion and a working model API; atomic model publication; initial viewer and Meta API integration risks assessed. | None. The T-3 spike requires the T-1 API and fixture; the T-5 spike requires explicit approval before any paid/live call. | Contract/type-generation and fixture tests pass; fixture upload produces a matching model summary; replacement/read consistency tests pass; a basic viewer load/GlobalId highlight and the authorised structured-output/tool-call API spike are demonstrated or explicitly approved as deferred. The original viewer and LLM spike intent is not silently removed. | **In progress** — the T-3 viewer spike is verified; one approved T-5 structured-output smoke passed (owner-reported), but remaining spike criteria still need acceptance review. | [T-0–T-1.1 history](../CHANGELOG.md#verified-implementation-history); [T-1.1 ADR](./DECISIONS.md#adr-017-content-addressed-model-versions-with-single-pointer-publication); [T-3 evidence](#t-3--interactive-3d-bim-viewer); [T-5 smoke evidence](./EVALUATION.md#t-5-live-structured-output-smoke-1-november-2026). |
| **M1 — Deterministic Review** | T-2, T-4, T-6 | IDS validation, required non-overlapping native rule coverage, an end-to-end LLM-free review, benchmark ground truth and reproducible evaluation evidence. | M0; T-4 builds on T-2; T-6 can start after T-2 and run alongside T-4. | IDS results are cross-checked against IfcTester; required P0 native-rule tests pass; fixture review runs without an LLM; benchmark precision/recall, clean-control false positives and determinism are reported from a reproducible labelled dataset. | **In progress** — T-6 evidence passes locally; M1 remains open while its M0 prerequisite and hosted CI evidence are outstanding. | [T-2](https://github.com/natnew/BIM-Intelligence/pull/6); [T-4](#t-4--end-to-end-deterministic-review-workflow); [T-6 measured results](./EVALUATION.md#8-results); [CI evidence outstanding](#t-6--benchmark-and-evaluation). |
| **M2 — AI-Native Review** | T-4, T-5, T-5.1 | Meta Muse Spark-assisted requirement interpretation and objective planning, filtered against confirmed checks, with explanations grounded in deterministic evidence and an explicit deterministic alternative. | M1 deterministic execution; T-5's full integration depends on T-4. API capability verification can run independently. | Scenario tests with FakeClient/Replay cover extraction, quote verification, confirmation, plan filtering, tool caps, grounded explanations, strict/optional objective policy, truthful provenance and degraded mode; any live test is explicitly authorised. A smoke test alone is insufficient. | **In progress** — T-5.1's offline API contract is implemented; UI continuation affordance, live BIM-workflow verification and remaining requirements/evaluation evidence are open. | [README development-status table](../README.md#development-status); [T-5 register](#t-5--meta-muse-spark-integration); [T-5.1 register](#t-51--explicit-ai-review-policy-and-provenance). |
| **M3 — Demo-Ready Product** | T-3, T-4, T-6, T-7 | Owner-directed UI governance framework; interactive viewer and finding coordination; traceable report; integrated workflow, tested fallback and a rehearsed demonstration. | M1 and M2; T-3 can proceed after T-1 and in parallel with T-4–T-6. T-7 integrates T-3, T-4, T-5 and T-6. | A tested browser walkthrough uses the benchmark/fixture, selection and highlighting work for a finding, reports preserve provenance, fallback works, and the smoke test and documented setup pass. | **In progress** — the UI governance framework is established; report, integrated AI workflow and demonstration criteria remain. | [T-3 evidence](#t-3--interactive-3d-bim-viewer); [T-4 evidence](#t-4--end-to-end-deterministic-review-workflow); [T-6 results](./EVALUATION.md#8-results); [T-7 UI governance](./UI_SPEC.md); [Demo requirements](./DEMO_PLAN.md). |
| **M4 — Submission** | T-8, supported by all previous completed tasks | Final hardening, verified documentation, measured evaluation results, recorded demo and owner-approved submission actions. | M3 and evidence from all applicable preceding tasks. | Final test and secret-scan evidence is recorded; claims match measured behaviour; demo and results are available; submission requirements are checked against official rules. Release, tagging or submission actions require owner approval. | **Not started** — T-6 measured results are now available; final hardening, CI, demo and submission evidence remain outstanding. | [Demo plan](./DEMO_PLAN.md); [T-6 results](./EVALUATION.md#8-results); submission requirements remain unverified. |

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
- **Status:** **Verified.**
- **Milestones:** M0 (viewer spike), M3 (finished interface).
- **Evidence:** On 29 October 2026, the minimal IFC and an existing T-2 review run were loaded in the integrated browser. The canvas rendered the three-wall model; selecting the W-002 finding highlighted its wall and displayed GlobalId `0QWMtUzsnUUONCUGc8Sqsa`. Clicking W-001 populated its element record, and clicking W-002 selected the matching finding and loaded its properties. Browser request capture showed the Fragments worker and `/web-ifc/` WASM assets served from localhost; no external requests were observed. These are actual browser observations, separate from the mocked tests.
- **Automated frontend validation:** `npm test` (15 tests passed), `npm run typecheck`, `npm run lint`, `npm run format:check`, `npm run build`, and `npm run types:check` — all passed on the completed change.
- **UI-004A follow-up (1 November 2026; T-7/M3 contribution):** On the isolated
  `feature/ui-004a-viewer-corrections` branch, distinct Fit model, canonical Reset view and Focus
  selected actions, bounded camera recovery, synchronised model/finding selection, priority-aware
  issue highlighting, clear-selection behaviour and observable viewer lifecycle states were
  implemented using the installed viewer APIs. Live browser checks exercised the fixture at
  1920×1080, 1440×900, 1216×735 and 390×844, including camera recovery, W-002/W-003 selection by
  model and finding row, W-001 with no linked finding, clear-selection paths, keyboard button
  activation, independent panel scrolling, resize and failed/recovered WASM loading. Evidence and
  exact frontend commands/results are in [UI_CHANGELOG.md](./UI_CHANGELOG.md#ui-004a--professional-3d-viewer-and-navigation-corrections).
  The browser run returned two IDS findings; the deterministic scenario returns those plus a native
  classification finding after explicit native-rule confirmation. This is a different configured
  check set; no backend or deterministic review behaviour changed. This follow-up does not alter
  T-3's Verified status or complete T-7/M3.
- **UI-004A main integration (1 November 2026):** The existing implementation is reconciled on
  `feature/ui-004a-main-integration` from `main` at `a13857c`, preserving the merged T-5 and
  FED-001 work. The integration adds targeted corrections for short-height desktop scrolling and
  clearing selection while the viewer is unavailable. Verification and limitations are recorded
  in [UI_CHANGELOG.md](./UI_CHANGELOG.md#ui-004a-main-integration-verification--1-november-2026).
  FR-VIS-09 remains in progress pending cross-severity viewer styling verification; merge and
  T-7/M3 completion are not implied.
- **Scope and licence note:** The viewer does not upload models. T-4 adds a bounded standard-review action to the existing workspace. The original T-3 slice did not alter viewer selection or model loading; UI-004A later added camera and selection corrections as recorded above. `web-ifc` 0.0.77 is MPL-2.0 and is documented as an exception to the repository's permissive-or-LGPL dependency preference; owner review remains required before public distribution.

### T-4 — End-to-End Deterministic Review Workflow

- **Objective:** Complete the LLM-free path from a model and confirmed checks to a review plan, deterministic execution, findings and traceable results.
- **Responsible components:** `validation/`, `orchestration/`, review API, schemas, scenario tests and findings API.
- **Deliverables:** The non-overlapping P0 native rule; bounded/default deterministic execution over supported checks; complete LLM-off review path, persistent coverage outcomes and a minimal viewer entry point. The IDS-only review delivered in T-2 was a verified slice, not by itself completion of this broader task.
- **Dependencies:** T-2; T-0 and T-1.1 contracts/versioning.
- **Acceptance tests:** Positive, negative and applicability-boundary unit tests for every shipped native rule; fresh-session fixture scenario with LLM off; pinned model, confirmed checks, bounded execution, truthful partial coverage, model/GlobalId consistency and byte-identical findings across repeated reviews; per-check errors never appear as passing checks.
- **Status:** **Verified** — T-4 acceptance evidence below is complete. M1 remains in progress because the separate T-6 evaluation criteria are not met; T-5 AI integration and T-7 product work are unchanged.
- **Milestones:** M1, M2 (integration seam), M3.
- **Evidence:** T-4 scenario `tests/scenario/test_deterministic_review.py` imports `tests/fixtures/minimal.ifc` and `minimal.ids` into a fresh session with `LLM_MODE=off`, explicitly confirms the native rule, runs and repeats the review with identical findings JSON, verifies the pinned model hash and GlobalId element mapping, and blocks non-loopback network access. The fixture produces the IDS FireRating finding on W-002, IDS classification-presence finding on W-003, and native classification-consistency finding on W-002; W-001 is not flagged. The native mismatch evidence is `observed="'W-002' uses Uniclass 2015: WRONG-CODE."`, `expected="Type 'WT-CLASSIFIED' uses Uniclass 2015: Ss_25_10_30."`, `method="native"`, rule `classification.consistent_by_type` v1.0.0. Unit tests cover the native rule's pass/mismatch/not-applicable/invalid-spec outcomes, confirmation idempotency, plan/tool caps, skipped coverage and error continuation.
- **Backend validation (29 October 2026):** `.\.venv\Scripts\python.exe -m pytest -q` — **473 passed, 1 warning** (upstream Starlette `httpx` TestClient deprecation); focused T-4 command `.\.venv\Scripts\python.exe -m pytest tests\unit\validation\test_native_rules.py tests\unit\orchestration\test_review_runner.py tests\unit\api\test_native_requirements.py tests\scenario\test_deterministic_review.py -q` — **25 passed, 1 warning**. `ruff check .` and `ruff format --check .` — passed (98 files already formatted). `.\.venv\Scripts\python.exe -m mypy` — passed for 97 source files. `.\.venv\Scripts\python.exe -m mypy --strict backend\bim_intelligence\schemas backend\bim_intelligence\validation backend\bim_intelligence\orchestration` — passed for 21 source files; mypy emitted an unused `pyproject.toml` module-section note but no type errors.
- **Frontend validation (from `frontend/`, 29 October 2026):** `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm run types:check`, `npm test` (**3 files, 18 tests passed**) and `npm run build` — all passed.

### T-5 — Meta Muse Spark Integration

- **Objective:** Add bounded model-assisted requirement extraction, objective planning and grounded explanations without allowing the model to create findings or bypass human approval.
- **Responsible components:** `llm/`, `requirements/`, `orchestration/`, `reporting/`, versioned prompt files and tests.
- **Deliverables:** Config-gated Meta API client and offline Fake/Recording/Replay interfaces; persistent budget accounting; Markdown/TXT candidate extraction with verbatim quote checks and explicit human confirmation against an existing `CheckSpec`; filtered planner; grounded explanation with deterministic fallback and token accounting; provenance-verified explanation endpoint with labelled fallback reasons; typed frontend API functions for objective reviews and finding explanations. Full BEP-to-IDS authoring, UI panels and live workflow verification remain unfinished acceptance.
- **Dependencies:** T-4 for full integration; T-0 schemas. The API capability check can run independently but any paid/live call requires explicit session approval under C-06 and AGENTS.md §9.
- **Acceptance tests:** Offline tests cover valid/invalid structured output; no-key Off/Replay; live configuration gating; budget rejection, persistence and concurrent reservation; sanitised timeout errors; quote/source validation and human confirmation; confirmed/unknown/duplicate/excess check plans; grounding rejection and deterministic fallback; default review correctness; objective-to-planner request body; whitespace-only objective rejection; explanation run/session/finding/requirement/check/source/model-version provenance; labelled fallback reasons; unchanged run artefacts; no non-loopback network access in default configuration. Default pytest does not invoke Live. The named live test requires `-m live`, `BIMI_LIVE_LLM=1`, `BIMI_LIVE_APPROVAL=T5-META-MUSE-SPARK-SMOKE`, valid live settings and owner approval.
- **Status:** **In progress — backend/API-client verification is offline; one owner-approved live structured-output smoke test passed on 1 November 2026, as reported by the owner from a side chat.** This is basic API compatibility evidence, not verification of live planning, grounded explanations or the integrated workflow, and does not by itself complete M0 or M2. The offline-verified backend AI review path and typed API client were merged into `main` via [PR #26](https://github.com/natnew/BIM-Intelligence/pull/26). FINAL-UI-001 (2 November 2026, branch `FINAL-UI-001`, pull request pending owner review) connects the objective input and explanation request in the browser per the [UI_SPEC.md hand-off contract](./UI_SPEC.md#t-5-meta-assisted-review--frontend-integration-contract); it was verified with `LLM_MODE=off` only, so live or Replay planning and `ai_generated` explanations remain unverified in the integrated workflow.
- **Milestones:** M0 (API capability spike), M2 (integrated AI-native workflow).
- **Offline verification (29 October 2026):** `.\.venv\Scripts\python.exe -m pytest -q` — **527 passed, 1 live test skipped, 1 third-party deprecation warning**; `.\.venv\Scripts\ruff.exe check .` — passed; `.\.venv\Scripts\ruff.exe format --check .` — passed; `.\.venv\Scripts\mypy.exe` — passed. From `frontend/`, `npm run types:check`, `npm run lint`, `npm run typecheck`, `npm test` (**3 files, 18 tests passed**), `npm run format:check` and `npm run build` — all passed. The default tests made no live Meta calls.
- **Secret scan (Gitleaks 8.25.0, redacted):** `python scripts/secret_scan.py --working-tree` — no leaks; `python scripts/secret_scan.py --history` — no leaks across 37 commits. `python scripts/secret_scan.py --staged` passed with **no staged changes**. The project owner approved setting repository-local `core.hooksPath=.githooks`; the pre-commit hook ran successfully against the empty index.
- **Evidence:** Implemented contracts and routes are described in [ARCHITECTURE.md §7.6, §9 and §11](./ARCHITECTURE.md), with spend decisions in [ADR-020](./DECISIONS.md#adr-020-t-5-meta-client-spend-ledger-and-human-gates). The original configured ceiling of 8,000 estimated input and 500 output tokens gives an uncached worst-case estimate of USD 0.012125; this is not the smoke request's actual reservation or charge. The observed smoke result is recorded below and in [EVALUATION §8](./EVALUATION.md#t-5-live-structured-output-smoke-1-november-2026).
- **AI review path verification (1 November 2026, branch `Working-Muse-Spark` from `3a9a3d5`, uncommitted):**
  - **Planner path:** a non-blank objective reaches the existing planner. The tests assert the SDK request body: model, system prompt `planner.v1.md`, JSON payload with the objective, confirmed requirements and available checks, `max_tokens=500` and `response_format=json_object`. Only confirmed, registered checks execute. Unselected confirmed checks are `skipped` with an objective-specific diagnostic, and the run is `partial`. Invalid plans, request failures and budget refusals (with no SDK request) fall back to the default plan with `plan_source=default`. Whitespace-only objectives are refused with 422 before any planner call or run record.
  - **Explanation endpoint:** before evidence is assembled, it verifies run/session/finding membership (including stored run id against route id), the requirement revision and confirmation, check id and rule version, source document and the pinned model index (ARCHITECTURE §10.4). IDS/document requirements must have a source; confirmed built-in requirements may omit it. Unknown findings return 404; provenance mismatches return 409; an `If-Match` other than the run's model returns 412. `Explanation.fallback_reason` and a schema validator keep `source`, `grounding_status`, `model` and the reason consistent.
  - **Artefact and network safety:** tests confirm `run.json` and `findings.json` are byte-unchanged after explanation requests. The default configuration makes no non-loopback connection.
  - **Typed API client:** `startObjectiveReview` and `explainFinding` validate session, finding, model version and label consistency, rejecting missing, empty, unknown or non-string template fallback reasons.
  - **Out of scope here:** no UI component, viewer, IFC ingestion or planner replacement was changed.
- **Offline verification (1 November 2026, same branch):**
  - Commands ran from the isolated worktree using the existing shared Python 3.12.12 environment
    at `..\..\BIM-Intelligence\.venv\Scripts\python.exe` and its sibling Ruff/mypy executables,
    with `PYTHONPATH=backend;tests`. Below, `python` denotes that interpreter, not a worktree-local
    `.venv`. Live was disabled with `BIMI_LIVE_LLM=0`, an empty `BIMI_LIVE_APPROVAL`,
    `LLM_MODE=off` and `ALLOW_LIVE_LLM=false`.
  - Backend:
    - `python -m pytest -m "not live" -q` — **591 passed, 1 live test deselected, 1 third-party deprecation warning**. The approved smoke was not repeated.
    - `python -m pytest tests\unit\api\test_finding_explanations.py tests\unit\api\test_reviews.py tests\unit\llm\test_explanations.py tests\evaluation\test_run_eval.py -q` — **67 passed**.
    - `ruff check .` and `ruff format --check .` (157 files) — passed.
    - `mypy` — passed for 128 source files.
    - `mypy --strict backend\bim_intelligence\schemas backend\bim_intelligence\validation backend\bim_intelligence\orchestration` — passed for 23 source files (unused module-section note only).
    - `python scripts\export_schemas.py --check` — passed.
    - `python -c "import json; from evaluation.offline_ai import evaluate_offline_ai; print(json.dumps(evaluate_offline_ai(), indent=2))"` — **9/9, 0 network calls, 0 live calls, USD 0**.
  - Frontend, from `frontend/`: `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm run types:check`, `npm test` (**6 files, 74 tests passed**) and `npm run build` — all passed. Existing dependency `NodeMaterial` import and large-chunk build warnings remain; no viewer or dependency changes were made.
  - Other checks: `python scripts/secret_scan.py --working-tree` — no leaks; `git diff --check` — clean.
  - Editor syntax validation was attempted but the Pylance request timed out; no successful editor
    diagnostic result is claimed. Terminal lint, type checks and executable tests passed.
- **Live smoke-test harness defect (found and fixed 1 November 2026, same branch):**
  - The autouse `_isolated_environment` fixture in `tests/conftest.py` removed `LLM_MODE` and `MODEL_API_KEY` and disabled `.env` loading for every test, including `tests/live/test_meta_smoke.py`. The named smoke test could therefore never send a request: with every gate open it stopped at its own guard (`LLM_MODE=live and ALLOW_LIVE_LLM=true are required; no request was sent.`).
  - Fix: tests marked `live` keep the real configuration; all other tests stay hermetic. Regression test `tests\unit\test_live_test_isolation.py` fails against the original fixture and passes with the fix.
  - Offline probe after the fix, with an obvious placeholder key, temporary data directory and every outbound socket blocked in-process: the test cleared all gates, constructed the live client and reached the provider call, which failed as a sanitised `LLMRequestError (APIConnectionError)`. Nothing left the machine. The temporary ledger showed the existing conservative accounting: a provider error is charged at the reserved estimate (USD 0.002395 for this request).
- **Earlier pre-smoke configuration observation (1 November 2026; historical, superseded by the side-chat result below):**
  - `MODEL_API_KEY` is not configured; `LLM_MODE=off`, `ALLOW_LIVE_LLM=false`, `ALLOW_CONTRIBUTOR_MODELS=false`.
  - Model `muse-spark-1.3`; base URL `https://api.meta.ai/v1`; retries 0.
  - Limits: 8,000 input and 500 output tokens per call; 2 calls per run; USD 0.10 per call and per run; USD 5.00 project.
  - No spend ledger exists.
  - At that point, owner approval had not been given in this implementation chat and no key was configured, so this chat sent no live request. This is not a statement about the subsequent approved side-chat run.
- **Observed live smoke evidence (1 November 2026, owner-reported side-chat run):**
  - The owner confirms that the existing named `tests/live/test_meta_smoke.py::test_meta_muse_spark_structured_output_smoke` ran once with approval and passed using `muse-spark-1.3`, outcome `success`. Structured output matched exactly: `{"status":"T5_SMOKE_OK"}`.
  - Provider-reported usage: **42 input, 0 cached, 293 output tokens**. The application ledger holds **one request**, with **USD 0.00129775 charged against a USD 0.002395 reservation**.
  - The charge is calculated from configured prices, **not checked against Meta's prices or an invoice**. It is an application-accounting observation, not independently verified provider billing.
  - The short reply used 293 output tokens: **58.6% of the configured 500-token output cap**. This raises a headroom risk for longer structured explanations, not proof of truncation or explanation failure. See [R-API-06](./RISKS.md#3-model-and-api-limitations).
  - This records the owner's observation; the side-chat source commit and raw response/ledger were not supplied or independently inspected here. The smoke test must **not be repeated** under this request. No additional paid call, cap increase or live explanation test is authorised; live explanation compatibility remains unverified.

### T-5.1 — Explicit AI Review Policy and Provenance

- **Objective:** Make objective planning intent, selected-check revisions and actual AI execution mode traceable without silently substituting a default plan for a strict request.
- **Responsible components:** `config.py`, review/request/problem schemas, review API and orchestration, generated API contracts, tests and engineering documentation.
- **Deliverables:** Explicit production Live profile; strict-by-default objective requests with typed failure metadata; explicit optional fallback and deterministic continuation; revision-pinned selected-check scope; per-run planning/mode/model/request/fallback/check provenance; historical-run compatibility.
- **Dependencies:** T-4 and T-5; contributes only to M2 and does not complete it.
- **Acceptance tests:** Production configuration rejects Off, non-approved models and contributor mode while development remains Off by default; strict provider/budget/plan failures publish no run or findings; optional fallback and explicit continuation are distinguishable; selected scope rejects stale/unconfirmed/mismatched requirements and constrains manifest/execution; provider mode/model/attempt metadata and Replay mode persist truthfully; old run records without provenance remain readable; schema export and generated TypeScript checks match Pydantic contracts. All new tests use fakes, replay fixtures or stubbed provider transports, not a live/paid call.
- **Status:** **Verified (offline contract).** Acceptance criteria pass on the current worktree. The existing UI does not expose a dedicated deterministic-continuation control; public deployment remains unapproved and unauthenticated; no live Muse planner run is claimed. These limitations keep M2 in progress.
- **Milestones:** M2.
- **Verification (3 November 2026):** `.\.venv\Scripts\python.exe -m pytest -q` — **637 passed, 1 live test skipped, 1 third-party deprecation warning**; `.\.venv\Scripts\ruff.exe check .`, `.\.venv\Scripts\ruff.exe format --check .`, `.\.venv\Scripts\mypy.exe` (131 source files) and `.\.venv\Scripts\python.exe scripts\export_schemas.py --check` — passed. From `frontend/`, `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm run types:check`, `npm test` (**10 files, 129 tests passed**) and `npm run build` — passed; Vite's existing large-chunk warning remains. `git diff --check` — passed. The Live test was skipped and no live/paid request was made.

### T-6 — Benchmark and Evaluation

- **Objective:** Measure deterministic finding quality and reproducibility on independently labelled, redistributable test data; evaluate the T-5 offline safety contract separately from model quality.
- **Responsible components:** `tests/evaluation/`, `tests/unit/evaluation/`, `datasets/synthetic/generated/`, `docs/EVALUATION.md`.
- **Deliverables:** Deterministic IFC4 generator, versioned injection manifest, independently checked ground truth, matching IDS/BEP/objectives, metric runner and dated machine-readable and human-readable evidence.
- **Dependencies:** T-2 for initial preparation and IDS baseline; T-4 native rules for full rule-family evaluation. Preparation can run in parallel with integration.
- **Acceptance tests:** Dataset and ground truth are byte-reproducible; P0 findings match exact rule/check and GlobalId sets; clean controls yield no false positives; undefined metrics, duplicates, unmatched predictions, misses, errors, skips and non-applicable checks are explicit; IDS is compared with IfcTester; live API calls are absent.
- **Status:** **Verified locally; hosted CI evidence pending.**
- **Milestones:** M1, M3, M4.
- **Evidence:** On 29 October 2026, the documented offline runner completed on source commit `99d04633c517c052f80f87b5f7fb6f2ec640e909` (dirty worktree). It measured 15 P0 defects, seven controls, aggregate TP/FP/FN 15/0/0, precision/recall/F1 1.000/1.000/1.000, byte-identical repeated findings, 14/14 IfcTester IDS entity agreement, zero errors/skips/false positives, 9/9 offline AI contract checks and zero network/live Meta calls or spend. Focused pytest passed 14 tests; the full backend suite passed 541 tests with one live test skipped; repository Ruff and mypy passed. GitHub Actions run [40924566072](https://github.com/natnew/BIM-Intelligence/actions/runs/40924566072) on the base commit ended in `startup_failure` with no jobs, so hosted CI for this worktree remains outstanding. Outputs are regenerated under git-ignored `datasets/synthetic/generated/` and `tests/evaluation/runs/latest/`.

### T-7 — Reporting, Interface Refinement and Demonstration Readiness

- **Objective:** Integrate the review workflow into a usable interface and present traceable findings and reports with a reliable demo fallback.
- **Responsible components:** `frontend/`, `reporting/`, browser/scenario tests and demo artefacts.
- **Deliverables:** Owner-directed UI governance framework (`docs/UI_SPEC.md`, `docs/UI_REFERENCES.md`, `docs/UI_CHANGELOG.md` and `frontend/AGENTS.md`), extended by the [UI constitution](./UI_CONSTITUTION.md), [refinement skill](../.github/skills/bim-ui-refinement/SKILL.md) and restricted [designer](../.github/agents/bim-ui-designer.agent.md)/[implementer](../.github/agents/bim-ui-implementer.agent.md) roles; requirement and objective panels; findings/detail views; model highlighting; JSON/Markdown report with provenance; replay/off mode; rehearsed demo. UI-002 Revision 2 adds an owner-approved Project Home and desktop-first review-workspace concept prototype; UI-003 implements that Project Home, upload sequence and review workspace; UI-004A adds fit/reset/focus navigation and selection corrections. The model tree, visibility controls, AI explanation surface and session catalogue remain proposed.
- **Dependencies:** T-3, T-4, T-5 and T-6. Begin integration as dependencies become testable, without treating incomplete upstream work as finished.
- **Acceptance tests:** UI changes follow explicit owner approval and are recorded with repeatable visual evidence; full browser walkthrough on the benchmark; findings link to their deterministic checks and model elements; report provenance is complete; replay/degraded mode works; browser smoke test passes.
- **Status:** **In progress — owner-directed UI governance framework, isolated UI-001/UI-002 concept prototypes, UI-003 production Project Home / review workspace, UI-004A camera/selection corrections and the FINAL-UI-001 objective/explanation/recent-session integration (on its branch, pending owner review) exist; reporting, model-tree/visibility controls, the one-click synthetic sample, browser smoke test and demo acceptance remain incomplete.**
- **Milestones:** M3.
- **Evidence:** [T-3](#t-3--interactive-3d-bim-viewer) and [T-4](#t-4--end-to-end-deterministic-review-workflow) record verified interface slices; [UI_SPEC.md](./UI_SPEC.md) defines the owner-directed governance framework. The complete integrated workflow, report and demo evidence remain outstanding.
- **Framework extension (30 October 2026):** constitution-driven, bounded concept/prototype evaluation and separate implementation approval are documented; optional Copilot guards are proposed, not installed. Reference metadata checks located an ignored singular-path library; image/provider permissions remain unverified. No UI-001 or visual redesign starts here. T-7/M3 status, dependencies, exit criteria and delivery dates are unchanged.
- **UI-002 Revision 2 (30 October 2026):** owner-approved visual direction retains Concept C v2's palette, adds Project Home and specifies a desktop-first review layout. An isolated synthetic prototype and design acceptance criteria are recorded under `local-private/ui-prototypes/ui-002/` and `docs/UI_SPEC.md` §17. Project names/history, sample-project loading, category visibility, camera controls, geometric clashes and frontend upload/session workflows remain proposed; no production files changed, no task/milestone status or schedule changed, and T-7/M3 remain in progress.
- **UI-003 (30 October 2026):** owner-approved production implementation of the Concept C v2 direction on branch `feature/ui-003-production-integration` (baseline `a3e701f`). The frontend now provides Project Home (session creation, IFC and requirements upload via existing endpoints, open existing session) and a three-column review workspace with real `ModelSummary`, `ReviewRun`, `Finding`, `Requirement` and `ElementRecord` data, explicit review/coverage/mismatch/error states and client-side finding filters. Evidence: 54 frontend tests pass; a live browser walkthrough on `tests/fixtures/minimal.ifc` + `minimal.ids` (create → upload → render → orbit/pan/zoom → run review → finding ↔ element → return home) with 1920×1080, 1440×900 and 390×844 captures is recorded in [UI_CHANGELOG.md](./UI_CHANGELOG.md) §UI-003 and [UI_SPEC.md](./UI_SPEC.md) §18. PR #18 merged into `main` on 30 October 2026. At UI-003 completion, reporting, the AI surface, camera/visibility controls, the Playwright smoke test and demo rehearsal remained outstanding; UI-004A subsequently added three camera actions. Backend, viewer modules, schemas, fixtures and dependencies were unchanged by UI-003; T-7/M3 remain in progress.
- **UI-004A (1 November 2026):** owner-authorised, isolated viewer correction on `feature/ui-004a-viewer-corrections`. The live browser verified distinct Fit model / Reset view / Focus selected actions and recovery after extreme zoom/pan, GlobalId-based selection/highlighting and clearing, loading/failure states, keyboard activation, responsive layouts and independent evidence/findings scrolling. Full frontend lint, formatting, typecheck, generated-types check, tests (**8 files, 67 tests**) and build passed; screenshots and exact commands are recorded in [UI_CHANGELOG.md](./UI_CHANGELOG.md#ui-004a--professional-3d-viewer-and-navigation-corrections). The UI review returned two IDS findings while the deterministic scenario includes an additional explicitly confirmed native check; the check sets differ, and backend review logic was not changed. This contributes viewer corrections to T-3/M0 and T-7/M3 but does not complete T-7/M3. The original evidence predates [PR #25](https://github.com/natnew/BIM-Intelligence/pull/25), which merged into `chore/final-day-decisions-implementation`, not `main`; the integration branch brings that existing work onto the later `main` baseline.
- **UI-004A merged (1 November 2026):** [PR #28](https://github.com/natnew/BIM-Intelligence/pull/28)
  merged at `cf06328c874258efe8a49d0afa291d9aef278928`. The subsequent release-baseline browser
  checks are recorded in [UI_CHANGELOG.md](./UI_CHANGELOG.md#release-001--synthetic-baseline-verification).
  The separately requested final UI-001 functional work is not implemented; its required
  implementation approval packet is incomplete. T-7 and M3 remain in progress.
- **FINAL-UI-001 (2 November 2026):** owner-approved bounded implementation on
  `FINAL-UI-001` from `3636342` (pull request pending owner review). The
  workspace gains an optional review objective that dispatches to `startObjectiveReview` (blank →
  unchanged standard review), a true plan-source label with the *objective was not used* sentence,
  an explicit **Explain finding** action rendering `source`, `grounding_status`, `fallback_reason`,
  `model` and citations separately from deterministic evidence, and browser-local recent sessions
  (identifiers only, server-revalidated). Project Home subtitle, upload confirmation and
  requirement visibility were completed. Frontend lint/format/typecheck/types/build passed and
  tests grew from 91 to **109**; focused backend API/scenario tests passed (46). The Off-mode
  browser walkthrough confirmed the objective request body reaching the API, the `default` plan
  source, an `ai_disabled` template explanation, version-mismatch and missing-run safety states,
  camera/selection behaviour, recent-session reopening and the 1920/1440/390 layouts. Evidence:
  [UI_CHANGELOG.md](./UI_CHANGELOG.md#final-ui-001--meta-assisted-review-integration-project-home-completion),
  [UI_SPEC.md §22](./UI_SPEC.md#22-final-ui-001--meta-assisted-review-integration-and-project-home-completion).
  The one-click synthetic sample was not implemented because it needs files outside the approved
  paths (`frontend/scripts`, `.gitignore` or a backend endpoint). `plan_source=llm`,
  `ai_generated` and Replay labels are Vitest-verified only. T-7 and M3 remain in progress.

### T-8 — Final Hardening, Documentation and Submission

- **Objective:** Complete final engineering verification and prepare evidence-backed documentation and owner-approved submission materials.
- **Responsible components:** Whole repository, CI, `README.md`, `docs/`, `CHANGELOG.md`, evaluation and demo evidence.
- **Deliverables:** Final regression/security/hygiene checks; clean-checkout setup verification; measured results; consistent public documentation; recorded demo and submission checklist.
- **Dependencies:** T-0 through T-7 as applicable; M3 exit.
- **Acceptance tests:** Agreed backend and frontend checks pass; secret scan and documentation/link checks are clean; setup reproduces; metrics link to a run and commit; demo is available; official submission requirements are checked. Release/tag/submission actions require project-owner approval.
- **Status:** **In progress — delivery-framework documentation is being reconciled here; final hardening, demo and submission acceptance have not been completed.** This documentation change does not establish product functionality or M4 completion.
- **Milestones:** M4.
- **Evidence:** This plan, [AGENTS.md §11](../AGENTS.md#11-delivery-milestones-engineering-tasks-and-progress-tracking) and [CHANGELOG.md](../CHANGELOG.md) establish the tracking requirements; final task evidence remains outstanding.
- **31 October 2026 documentation evidence:** [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)
  records dependency metadata, web-ifc build assets and unresolved licensing/provenance checks.
  This audit does not complete T-8: final distribution-specific attribution, remaining hardening,
  demo and submission evidence are still outstanding.
- **RELEASE-001 baseline verification (1 November 2026):** the complete non-live backend suite
  passed 616 tests, the frontend suite passed 91 tests, and the synthetic IFC/IDS browser workflow
  was exercised. The latest `main` hosted CI run ended in `startup_failure` before jobs started.
  The requested final UI, recording, public repository, official submission fields and a release
  commit remain outstanding. Exact commands and limits are in
  [EVALUATION.md](./EVALUATION.md#release-001-offline-verification--1-november-2026) and
  [DEMO_PLAN.md](./DEMO_PLAN.md); T-8 is in progress and the milestone table retains M4 as not
  started.

## 4. Revised delivery schedule

The original ten-day window is retained. The weekday labels below are corrected to the 2026 calendar: 26 October was Monday, not Sunday; 4 November is Wednesday. Historical completion dates below remain as recorded by commits/PRs; the schedule is not backdated or shifted to disguise slippage.

| Date | Day | Original plan context | Recorded implementation or current target |
|---|---|---|---|
| 26 Oct | Monday — Day 1 | Architecture baseline and initial LLM/viewer spikes planned. | Architecture baseline is recorded in Git on 27 Oct ([PR #1](https://github.com/natnew/BIM-Intelligence/pull/1)); neither integration spike is evidenced as complete. |
| 27 Oct | Tuesday — Day 2 | Repository foundations and T-0. | T-0 and the scaffold landed; see [T-0 commit](https://github.com/natnew/BIM-Intelligence/commit/be45c7c) and [PR #2](https://github.com/natnew/BIM-Intelligence/pull/2). |
| 28 Oct | Wednesday — Day 3 | IFC ingestion and model indexing. | T-1 delivered via [PR #4](https://github.com/natnew/BIM-Intelligence/pull/4). |
| 29 Oct | Thursday — Day 4 | Original plan targeted benchmark/evaluation; its metric exit was not achieved by the original target. | T-1.1 and T-2 delivered via [PR #5](https://github.com/natnew/BIM-Intelligence/pull/5) and [PR #6](https://github.com/natnew/BIM-Intelligence/pull/6). A T-6 local benchmark result was recorded later on 29 October; hosted CI remains outstanding. |
| 30 Oct | Friday — Day 5 | Original plan targeted the requirements interpreter. | Target: advance T-4 deterministic workflow; start T-3 viewer and T-6 benchmark preparation; verify Meta API capability only with required owner approval. |
| 31 Oct–1 Nov | Saturday–Sunday — Days 6–7 | Original plan targeted orchestration and frontend integration. | Target: progress T-3 and T-6 in parallel; integrate T-5 after T-4 is testable; record API verification outcome or blocker. |
| 2 Nov | Monday — Day 8 | Original plan targeted report, hardening and docs. | Target: T-7 integration of available viewer/workflow/evaluation pieces; complete T-3 and T-6 acceptance where feasible. |
| 3 Nov | Tuesday — Day 9 | Original plan reserved a buffer and rehearsal. | Owner's internal completion target: T-7 demo rehearsal and T-8 regression, documentation, setup and security checks must be completed by this date; unresolved optional scope is dropped. |
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
- A local T-6 evaluation was recorded on 29 October; [EVALUATION.md §8](./EVALUATION.md#8-results) is authoritative for its measured scope and limitations. Hosted CI remains outstanding. The earlier “No evaluation has been run” wording was stale and is superseded by this dated reconciliation.

## 7. 1 November final delivery overlay

The project owner's internal completion deadline is **3 November 2026**. The official submission
date remains **4 November 2026**. The [final 48-hour plan](./FINAL_48_HOUR_PLAN.md) defines the
workstream order, owners, rollback, exact coordination gate and recording evidence. It is an
implementation plan, not completion evidence.

The two-model federation/clash demonstration is separately conditional and does not become an
existing M1/M2/M3 MVP criterion. Its go/no-go cutoff is **2 November 2026, 12:00 UTC**. A failed
gate drops the coordination branch and preserves the single-IFC IDS/native review. Meta-assisted
recording remains subject to real UI integration and explicit owner approval for any live call.
Official hackathon rules, eligibility and public asset rights must be checked before submission.

The earlier reconciliation used main commit
`1f3d13b78683692317e00f2279c3f0c4ac02f1c2` (31 October 2026). UI-003 and UI-004A have since
merged; the verified main baseline on 1 November is
`cf06328c874258efe8a49d0afa291d9aef278928`. T-7/M3 and T-8 remain **In progress**; the
authoritative milestone table retains M4 as **Not started** pending M3. Earlier changelog and
final-48-hour entries describe M4 as in progress; that status discrepancy is recorded rather than
silently resolved. Reporting, integrated user-facing AI, acceptance evidence, recording and
submission checks remain incomplete. No task or milestone is marked complete by this plan.

# Changelog

Significant implementation, architectural and delivery-framework changes are recorded here. Entries remain under **Unreleased** until the project owner publishes a release.

## Unreleased

### T-7 — Owner-directed UI design governance framework

- Establish [`docs/UI_SPEC.md`](./docs/UI_SPEC.md) as the evolving UI specification, separating verified behaviour, provisional design principles, owner-approved decisions and open questions without prescribing a new visual style.
- Add [`docs/UI_REFERENCES.md`](./docs/UI_REFERENCES.md) and [`docs/UI_CHANGELOG.md`](./docs/UI_CHANGELOG.md) for owner-supplied references, approval feedback and append-only iteration evidence. Third-party screenshots are to remain in private local storage unless redistribution rights are established.
- Add [`frontend/AGENTS.md`](./frontend/AGENTS.md) with mandatory owner-approval, scope, functional-regression, accessibility, testing, diff-review and no-commit/push/merge guardrails; link the frontend rules from the root [`AGENTS.md`](./AGENTS.md).
- Document a repeatable visual verification, frontend regression and safe rollback process; use existing frontend commands and do not add browser automation dependencies.
- Update the T-7 register and README documentation index. T-7 remains in progress; this framework introduces no visual redesign, no UI-001 scope, and no application behaviour changes.

### T-6 — Benchmark and Evaluation

- Add a deterministic IFC4 benchmark generator with a clean model, defective model, versioned injection manifest, independently checked ground truth, matching IDS, synthetic BEP and objective examples. Keep generated IFC/results ignored and leave the existing minimal fixtures untouched.
- Reconcile the original D01–D14 count with the target of 15–20 positive P0 instances by adding D19; retain D15–D17 as unimplemented P1 exclusions and D18 plus six explicit cases as zero-finding controls.
- Add one-to-one matching by rule id, immutable check id and exact GlobalId set; report duplicates, unmatched predictions, misses, undefined metrics, clean-control false positives and execution coverage separately.
- Add an offline runner for LLM-disabled reviews, byte-identical persisted findings, IfcTester JSON agreement, SHA-256/version metadata and Fake/Replay safety-contract checks. No live Meta request or spend was made.
- Record the 29 October 2026 local result in [docs/EVALUATION.md](./docs/EVALUATION.md): 15/15 TP, 0 FP, 0 FN; precision/recall/F1 1.000; seven clean controls with no false positives; deterministic findings; 14/14 IDS entity agreement; and 9/9 offline AI contract checks. This measures only the labelled synthetic benchmark, not live model performance or general BIM accuracy. Hosted CI evidence remains outstanding.

### T-5 — Meta Muse Spark Integration (offline implementation)

- Add a typed `LLMClient` boundary with network-isolated Fake and Replay clients, response-only recordings, and a Meta Model API `LiveClient` using the existing OpenAI SDK. Live remains off by default and requires an explicit configuration gate.
- Add persistent, cross-process budget reservations and usage reconciliation with configurable Muse Spark Standard prices, USD 0.10 per-call/per-review and USD 5 cumulative application limits, a two-call review cap, 8,000 estimated input tokens, 500 output tokens and zero default retries. These are application controls, not provider billing caps.
- Add objective-based plan selection constrained to unique confirmed immutable check ids; invalid or unavailable AI plans keep the deterministic default.
- Accept Markdown/TXT source documents, produce unconfirmed quote-verified candidates, and require explicit confirmation against an existing confirmed CheckSpec. New IDS criteria are not generated.
- Add grounded per-finding explanations with exact evidence citations and deterministic fallback; explanations remain separate from `findings.json`.
- Add a safe budget-status endpoint, schema exports, offline API/client/budget tests, a gated one-call live smoke test definition and redacted Gitleaks scan tooling. No live request was made and no API spend was measured; M0 capability verification and M2 completion remain open.

### T-4 — End-to-End Deterministic Review Workflow

- Add the versioned native `classification.consistent_by_type` v1.0.0 rule as an explicitly confirmed, parameter-free built-in check, without duplicating IDS 1.0 property, naming or classification-presence checks.
- Bound stable default-plan execution with `MAX_PLAN_CHECKS` and `MAX_TOOL_CALLS_PER_RUN`; record skipped and per-check error outcomes, continue after recoverable errors, and mark skipped, errored or not-applicable coverage as `partial`.
- Add a one-click **Run standard review** action to the existing viewer workspace. It pins the run to the model summary ETag, loads the resulting run/findings through version-aware endpoints and displays per-check coverage.
- Add native-rule, cap/error, API confirmation and LLM-off end-to-end scenario tests, including repeated findings output and model/GlobalId consistency. The task record in [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md#t-4--end-to-end-deterministic-review-workflow) records exact validation evidence; benchmark metrics remain outstanding under T-6.

### T-3 — Interactive 3D BIM Viewer

- Add an on-demand browser-side That Open Components 3.6 viewer for the minimal IFC fixture, with GlobalId-to-fragment resolution, viewer-to-element selection and deterministic finding highlights.
- Connect existing model, review-run, findings and element APIs. Reject runs whose session or model hash does not match the active model; pin model-file and element requests to the summary ETag and recheck the active version after loading.
- Serve the pinned `web-ifc` WASM files and Fragments worker locally. Add finding evidence, element identity and property details, and loading, empty and error states.
- Verify actual browser rendering and both selection directions on the minimal fixture; mocked frontend API and component tests pass. See the [T-3 implementation record](./docs/IMPLEMENTATION_PLAN.md#t-3--interactive-3d-bim-viewer) for evidence and exact validation results.
- Correct the `web-ifc` licence disclosure: version 0.0.77 is MPL-2.0 and is documented as an exception to the repository's permissive-or-LGPL dependency preference; owner review remains required before public distribution.

### Delivery Framework Reconciliation — M0–M4 and T-0–T-8

- Retain the original delivery milestones: M0 Foundations, M1 Deterministic Review, M2 AI-Native Review, M3 Demo-Ready Product and M4 Submission.
- Add the task framework for more actionable engineering delivery: T-0 Schemas and Minimal IFC Fixture; T-1 IFC Ingestion, Model Indexing and Session Persistence; T-1.1 Model Publication Consistency; T-2 Deterministic IDS Validation; T-3 Interactive 3D BIM Viewer; T-4 End-to-End Deterministic Review Workflow; T-5 Meta Muse Spark Integration; T-6 Benchmark and Evaluation; T-7 Reporting, Interface Refinement and Demonstration Readiness; and T-8 Final Hardening, Documentation and Submission.
- T-1.1 is a corrective subtask introduced after review of T-1. It addresses consistency when replacing a model: versioned model artefacts are prepared and validated before the active session pointer changes, with locking, recovery and version-bound reads.
- Use milestones and tasks together because milestones describe capabilities achieved, while tasks describe engineering work. Tasks contribute to multiple milestones; neither the presence of task labels nor one task's completion establishes a milestone.
- The authoritative schedule, mapping, exit criteria, status and evidence register is [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md).
- Mapping: M0 — T-0, T-1, T-1.1, with T-3 viewer and T-5 Meta API capability spikes; M1 — T-2, T-4, T-6; M2 — T-4, T-5; M3 — T-3, T-4, T-6, T-7; M4 — T-8, supported by prior completed work. See the implementation plan for deliverables, dependencies and measurable exit criteria.
- Future substantive work must update the task and milestone evidence/status in [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md) and record the significant change here. Documentation reconciliation is not evidence that engineering functionality is complete.

### Verified implementation history

Dates below are the dates recorded in Git history or merged pull-request metadata; they are not revised to make the earlier schedule appear on time.

- **2026-10-27 — Repository foundations:** backend and frontend scaffolding, configuration, health endpoint and CI. [PR #2](https://github.com/natnew/BIM-Intelligence/pull/2), commit [`18cf8cc`](https://github.com/natnew/BIM-Intelligence/commit/18cf8cc).
- **2026-10-27 — T-0 Schemas and Minimal IFC Fixture:** typed domain contracts and reproducible IFC/IDS fixture. Commit [`be45c7c`](https://github.com/natnew/BIM-Intelligence/commit/be45c7c).
- **2026-10-28 — T-1 IFC Ingestion:** session persistence, IFC indexing and ingestion API. [PR #4](https://github.com/natnew/BIM-Intelligence/pull/4), commit [`de63de8`](https://github.com/natnew/BIM-Intelligence/commit/de63de8).
- **2026-10-29 — T-1.1 Model Publication Consistency:** content-addressed model versions and atomic activation. [PR #5](https://github.com/natnew/BIM-Intelligence/pull/5), commit [`b1fd054`](https://github.com/natnew/BIM-Intelligence/commit/b1fd054).
- **2026-10-29 — T-2 Deterministic IDS Validation:** IDS 1.0 import, confirmed requirements, IfcTester-backed review execution and deterministic findings. [PR #6](https://github.com/natnew/BIM-Intelligence/pull/6), commit [`a480483`](https://github.com/natnew/BIM-Intelligence/commit/a480483). The PR records `ruff`, `mypy`, 461 backend tests, frontend lint/typecheck/tests/build and generated-type checks as passing.

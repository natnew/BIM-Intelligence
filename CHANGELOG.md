# Changelog

Significant implementation, architectural and delivery-framework changes are recorded here. Entries remain under **Unreleased** until the project owner publishes a release.

## Unreleased

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

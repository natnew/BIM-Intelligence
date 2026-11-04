# AGENTS.md — Engineering rules for BIM Intelligence

This file governs every contributor, human or AI coding agent, working in this repository. Read it before changing anything. Where it conflicts with convenience, it wins.

## 1. Project context

BIM Intelligence is an AI-native architectural BIM review application being built for the Meta Global AI Developer Hackathon (26 October – 4 November 2026). It ingests IFC models and supported requirement documents and runs deterministic checks. Meta Muse Spark (via the Meta Model API) is the intended live provider for requirement interpretation, review planning and grounded explanations; live compatibility remains unverified.

Current phase: **pre-alpha, implementation in progress.** The checked-in implementation includes domain contracts and reproducible fixtures, version-consistent IFC ingestion, bounded IDS review and one registered classification-consistency native rule, an interactive viewer and the Project Home/review-workspace slice. T-5 has offline-tested client, extraction, planning, grounding and budget controls; T-6 has a locally measured synthetic benchmark. Live Meta verification, frontend AI integration, complete evidence/reporting, remaining viewer controls, the benchmark Playwright smoke test and demonstration acceptance remain outstanding. These slices do not establish milestone completion or release readiness.

This summary is descriptive; the engineering and approval rules below are binding. Before starting work, consult the task register and the relevant recorded evidence rather than treating this summary as a completion ledger.

- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) — architecture baseline and marked implementation evidence
- docs/REQUIREMENTS.md — what it must do (`FR-*`, `NFR-*`, `C-*` ids)
- [docs/DECISIONS.md](./docs/DECISIONS.md) — why (`ADR-*`); open questions (`OQ-*`)
- docs/IMPLEMENTATION_PLAN.md and [CHANGELOG.md](./CHANGELOG.md) — delivery mapping, status and implementation history
- docs/EVALUATION.md — evaluation scope, reproduction, recorded results and limitations
- docs/RISKS.md — risks and unresolved mitigations

When sources disagree, distinguish their authority:

1. Source code and executable schemas establish implemented behaviour, not design approval.
2. Tests and recorded runs establish verification only for the behaviour and baseline they cover.
3. The task register and changelog establish delivery status; apply each milestone's exit criteria.
4. Adopted ADRs establish design decisions; proposals and open questions are not adopted decisions.
5. Requirements establish intended functionality and acceptance criteria.
6. The [README](./README.md) describes the public-facing product; it is not implementation evidence.

Report contradictions rather than silently resolving them. Code that conflicts with an adopted ADR is an implementation gap, not permission to rewrite the ADR or weaken a valid rule. Use the checked-out baseline; do not present unmerged work as implemented. Distinguish local tests, recorded browser observations, hosted CI results, owner approval and release readiness.

If you need to make an architectural assumption the documents do not cover, **stop and record it** as a new ADR or open question before implementing.

## 2. Engineering principles

1. **Findings are deterministic.** Only IfcTester or a registered native rule may create a `Finding`. No LLM output is ever written into `findings.json`. (`ADR-001`, `C-01`, `C-02`)
2. **The model proposes; code verifies; the human decides.** Requirement candidates need verbatim quotes and human confirmation; plans are filtered against the registry; explanations pass a grounding check. (`ADR-008`, `ADR-009`)
3. **Smallest effective architecture.** One process, one orchestrator, file-system storage. Do not add services, queues, databases or frameworks without an ADR. (`C-08`)
4. **Schemas are the contract.** Domain models live in `backend/bim_intelligence/schemas/` (Pydantic v2) and are exported to the frontend. Change a schema → regenerate types → update tests. (`C-07`, `ADR-014`)
5. **The IFC is read-only.** Never write to or re-save an uploaded model. (`C-04`)
6. **Say only what is true.** Documentation describes the system as built; metrics appear only after they are measured. Prefer "designed to" and "intended to" over "does" until there is a test.
7. **Preserve version integrity.** Bind reviews and reads to the model hash, document hashes, confirmed requirement revisions and rule versions. Preserve session locks, atomic publication and `ETag`/`If-Match` guards; a mismatch must fail visibly rather than mix versions. (`ADR-015`–`ADR-019`)

## 3. Directory conventions

See [ARCHITECTURE.md Appendix A](./docs/ARCHITECTURE.md#appendix-a--recommended-repository-structure). Rules:

- Create a directory only when adding its first real file. No placeholder folders.
- `backend/bim_intelligence/<package>/` — one package per component. API modules may import their own route modules, configuration and package version, and `schemas/`, `store/`, `orchestration/`, `bim/`, `requirements/`, `reporting/` entry points. Preserve the allowlist enforced by `tests/unit/test_import_boundaries.py`; do not bypass component boundaries.
- `llm/` is the **only** package that imports the `openai` SDK.
- `bim/` and `validation/` are the **only** packages that import `ifcopenshell` / `ifctester`.
- Prompts live in `orchestration/prompts/` and `reporting/prompts/` as versioned files (`planner.v1.md`, `requirements.v1.md`, `explanation.v1.md`); the narrative extractor loads `orchestration/prompts/requirements.v1.md`. Never inline long prompts in code.
- `tests/unit/` mirrors the backend package layout; `tests/scenario/` holds end-to-end tests; small hand-built IFC/IDS fixtures go in `tests/fixtures/`.
- `tests/evaluation/` holds the opt-in metrics runner and evaluation regression tests, which may import the backend as a library. Its `test_*.py` files are collected by default `pytest`; the standalone runner is invoked separately. Generated benchmark inputs, results and response recordings remain in ignored paths. See [datasets/README.md](./datasets/README.md) and EVALUATION §7 for provenance and reproduction.
- `frontend/src/viewer/` is the only place that imports `@thatopen/*`, `web-ifc` or `three`.
- For any frontend UI change, also read [`frontend/AGENTS.md`](./frontend/AGENTS.md) and
  `docs/UI_SPEC.md` before editing. The owner-directed UI reference and
  iteration records are `docs/UI_REFERENCES.md` and
  `docs/UI_CHANGELOG.md`.
- Apply the binding `UI constitution` and the bounded
  [`bim-ui-refinement` skill](./.github/skills/bim-ui-refinement/SKILL.md) for T-7 design work.
  The [designer](./.github/agents/bim-ui-designer.agent.md) is read-only; the
  [implementer](./.github/agents/bim-ui-implementer.agent.md) needs separate iteration approval.
  Concept exploration is not redesign permission; stop at the agreed checkpoint.
- `docs/` holds engineering documentation only. No planning notes, scratch files or meeting logs.
- `data/` is runtime storage and is git-ignored.
- `hackathon-private/` is confidential and git-ignored. Never copy its contents into tracked files;
  publish a non-sensitive summary only with owner authorisation.
- `local-private/` is the ignored, owner-managed workspace for private source materials and
  testing evidence. Its intended layout is below; the owner creates and populates these folders
  locally. Do not create placeholder files or change the synthetic benchmark or tracked fixtures.

```text
local-private/
  bim-models/
  bim-documents/
  ui-references/
  test-results/
  professional-feedback/
```

## 4. Dependency management

- **Python 3.10–3.12 only** (`requires-python = ">=3.10,<3.13"`); develop on 3.12. This is the adopted support range, based on the recorded IfcOpenShell wheel check, not a claim about all current upstream releases. CI configures Python 3.12 on Ubuntu and Windows. (`ADR-005`)
- Backend dependencies in the root `pyproject.toml` with pinned minimums and upper bounds for `ifcopenshell`, `ifctester`, `openai`, `fastapi`, `pydantic`. Dev extras under `[project.optional-dependencies] dev`. Install from the repository root with `pip install -e ".[dev]"`.
- Frontend dependencies in `frontend/package.json` with a committed lockfile. Respect That Open Components peer ranges (`three >= 0.182.0`, `web-ifc >= 0.0.77`).
- Frontend CI configures Node.js 20 and 22. Use the locked dependencies with `npm ci` from `frontend/`; a configured CI matrix is not evidence of a successful hosted run.
- Adding a dependency requires: a one-line justification in the PR/commit message, licence check (permissive or LGPL as installed package), and an entry in the README licence table if user-facing.
- `web-ifc` is MPL-2.0: [ADR-007](./docs/DECISIONS.md#adr-007-browser-side-geometry-with-that-open-components) records the existing viewer-stack exception, not a general waiver. Consult [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) for the current inventory and unresolved distribution obligations; owner review remains required before distribution.
- Do not install packages speculatively. Do not add an agent framework; the orchestrator is intentionally hand-rolled (`ADR-002`, `ADR-003`).

## 5. Code quality requirements

**Python**

- Type hints on all public functions and dataclass/Pydantic fields. Run `mypy` with the root `pyproject.toml`: strict overrides apply to `schemas/`, `validation/` and `orchestration/`; configured checks elsewhere also reject untyped definitions and check untyped bodies.
- `ruff` for lint and format (`ruff check`, `ruff format`); line length 100.
- Small, composable functions; explicit inputs/outputs; no module-level mutable state.
- Custom exception types per component (`IfcLoadError`, `PlanViolation`, `GroundingError`, …) with contextual messages.
- I/O, business logic, model calls and evaluation logic in separate modules.
- Comments only where the _why_ is not obvious. No commented-out code.

**TypeScript / React**

- `strict: true`; no `any` in domain types. Do not hand-edit generated API schemas/types; regenerate them from Pydantic and check both generation stages (§10).
- Functional components and hooks; one component per file; presentation separated from state and data fetching.
- Every data-bearing component handles loading, empty, error and success states.
- Semantic HTML and ARIA labels on interactive controls; keyboard-reachable finding list.
- `oxlint` + `prettier` with the repository configuration (`npm run lint`, `npm run format:check`).

**Both**

- British English in documentation, UI copy and comments.
- No TODO/FIXME without an issue reference or an `OQ-*` id.

## 6. Testing standards

- **Unit tests are mandatory** for: Model Index construction, every native rule (positive, negative and boundary cases), IDS compilation (XSD-valid output), grounding checker (including adversarial fixtures), tool registry (unknown tool, invalid args, cap), configuration validation (contributor-model rejection), finding normaliser.
- **Scenario tests** run the full review on a fixture with `FakeClient`; one scenario per planned objective; one for `LLM_MODE=off`; one for LLM failure mid-run.
- **Regression tests** for every fixed bug, named after the issue.
- **No live API calls in the default test run.** Live tests are marked `@pytest.mark.live` and require explicit session spend approval (`C-06`). The existing T-5 smoke test additionally requires `-m live`, `BIMI_LIVE_LLM=1`, `BIMI_LIVE_APPROVAL=T5-META-MUSE-SPARK-SMOKE` and valid live settings; see the T-5 register. A configured gate is not owner approval.
- **Determinism:** tests must not depend on wall-clock time, random ordering or network. Seed anything random.
- Frontend: Vitest + React Testing Library for panels. The required Playwright smoke test on the benchmark remains outstanding; mocked viewer tests and recorded fixture browser walkthroughs do not replace it.
- Evaluation runs (`tests/evaluation/run_eval.py`) produce scoped metrics, separate from regression tests. Apply the existing NFR-02 precision/recall target and EVALUATION criteria; do not invent new thresholds or generalise the small synthetic result to real projects or live model quality. Keep counts, dates and hashes in the evidence records, not permanent instructions.

## 7. Documentation responsibilities

When you change behaviour, update documentation in the same change:

| Change                         | Update                                                                            |
| ------------------------------ | --------------------------------------------------------------------------------- |
| New or changed endpoint        | ARCHITECTURE §11 and the OpenAPI description strings                              |
| New rule, tool or schema field | ARCHITECTURE §7/§8/§10; REQUIREMENTS acceptance criteria if affected              |
| Architectural choice           | New ADR in DECISIONS.md (never edit an adopted ADR's decision text; supersede it) |
| Setup or command change        | README setup/testing sections — run the commands before writing them              |
| Metric produced                | EVALUATION §8 with commit hash and date                                           |
| New risk or closed risk        | RISKS.md                                                                          |

Mermaid diagrams must render on GitHub; check syntax before committing. Keep terminology consistent: _Finding_, _Requirement_, _CheckSpec_, _EvidenceBundle_, _Explanation_, _ReviewPlan_, _ModelIndex_.

## 8. Security requirements

- Secrets only from environment variables or an ignored local `.env`; `.env.example` lists names with empty or safe values. Never log or return `MODEL_API_KEY`. `/health` may expose only its defined safe diagnostics (including LLM mode and a key-configured boolean), never secrets or a configuration dump.
- Default model ids are Standard mode; `-contributor` ids are rejected unless `ALLOW_CONTRIBUTOR_MODELS=true`. (`ADR-010`, `NFR-08`)
- Uploads: extension allow-list, size limits, fixed stored filenames, session-scoped directories. No user-controlled paths.
- Model-assisted plans reference confirmed check IDs only; T-5 exposes no model-callable tools. The planned tool boundary remains read-only with respect to IFC; deterministic execution may persist session/run artefacts under the existing locks. No shell, file-system or arbitrary network tools may be exposed to the model.
- Outbound service calls go only to `LLM_BASE_URL`, constrained to `https://api.meta.ai/v1`. Serve viewer workers/WASM locally; disable remote IDS schema loading. No telemetry, no analytics.
- `LLM_MODE=off` is the default. Live requires `MODEL_API_KEY` and `ALLOW_LIVE_LLM=true` as well as explicit session approval; Off/Replay must never silently fall back to Live. Preserve fail-closed budget reservations and usage accounting under `DATA_DIR/llm/`. These are application safeguards, not provider-enforced billing caps. (`ADR-020`)
- Server binds to `127.0.0.1` unless `ALLOW_REMOTE=true`.
- Treat BEP/document content as untrusted input (prompt-injection surface). Validate all model output by schema; never execute anything derived from document text without the plan filter and human confirmation.
- Run the redacted [secret scanner](./scripts/secret_scan.py) before any push; preserve the staged [pre-commit hook](./.githooks/pre-commit) and CI scan. See [README testing](./README.md#testing) for staged, working-tree and history commands. Never commit `.ifc` files outside `tests/fixtures/`, `datasets/synthetic/` or `datasets/permitted/`, anything under `data/`, `local-private/` or `hackathon-private/`. Generated dataset/result/recording paths remain ignored even within those locations.

### Private data handling and provenance

- Private materials must never be committed or copied into tracked directories. This includes
  real BIM models, client/project documents, screenshots, AEC tester feedback and private testing
  evidence. Git ignore rules are not access controls and do not protect files already tracked.
- Inspect private files only for the explicitly owner-authorised task; access or local availability
  does not grant permission to inspect unrelated material.
- Do not transmit real BIM files, client documents, screenshots or AEC tester feedback to an LLM
  service without explicit owner approval and applicable data rights. This includes attachments,
  tool output, extracted text and derived excerpts; approval for local inspection is not approval
  for transmission.
- Do not publish model-derived facts or private project names without authorisation. Keep raw
  feedback and evidence private; tracked registers may contain only non-sensitive reference
  identifiers and authorised interpretations or decisions.
- Public demonstration templates must use synthetic or expressly redistributable data. Record
  provenance and redistribution rights for any non-synthetic public input; preserve the T-6
  synthetic benchmark and existing fixtures.
- Label AI explanations separately from deterministic model findings; an explanation must never
  be presented or persisted as a `Finding` (`C-01`, `C-02`).
- Any change involving private data handling requires a documented security and provenance review
  before implementation. Record the authorised task, source/reference identifiers, ownership and
  applicable rights, inspection scope, storage/access, proposed transmission or publication,
  owner approvals, retention/deletion arrangements and verification. Keep sensitive review details
  in `local-private/test-results/`; tracked change records contain only a non-sensitive summary
  and review identifier. Unresolved permissions block use, transmission or publication.

## 9. Agent boundaries and prohibited actions

AI coding agents working in this repository **must not**:

- Commit, push, open a PR or merge without explicit approval from the project owner.
- Make live Meta Model API calls (or any paid call) without explicit authorisation for that session.
- Perform hackathon submission actions, create releases, or deploy anywhere.
- Modify, re-save or "fix" any uploaded or fixture IFC file in place; generate new fixtures via scripts instead.
- Write a `Finding` from LLM output or add an `llm` value to `Finding.method`.
- Bypass the plan filter, tool-call cap, verbatim quote check or grounding check "temporarily".
- Add dependencies, services, databases or frameworks without an ADR.
- Change public positioning, naming, scope or architecture without recommending first and obtaining approval.
- Copy proprietary code, UI assets or documentation from Revit, Navisworks, Solibri, BIMcollab or any other product.
- Copy `hackathon-private/` content into tracked files.
- Assert in any document that functionality works, or that a metric was achieved, without an implemented test or a recorded evaluation run.
- Create markdown planning notes, scratch files or TODO lists in the repository; use session artefacts or issues.
- Work outside this repository's directory.

When blocked by any of these, stop, explain the constraint, and ask.

## 10. Working pattern for a change

1. Read the relevant requirement ids and ADRs.
2. For behaviour changes, write or update the failing test. For documentation-only changes, verify claims, paths, links and documented commands against the current baseline; do not run unnecessary application tests or install dependencies.
3. Implement the smallest complete change that satisfies the requirement — including error handling and documentation.
4. For backend changes, run `ruff check .`, `ruff format --check .`, `mypy` and `pytest` from the repository root with the development environment active. For frontend changes, run `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm run types:check`, `npm test` and `npm run build` from `frontend/`. Run commands separately and stop on failures; do not use shell syntax unsupported by the host.
5. Update docs per §7.
6. Summarise: what changed, which requirement ids it serves, what was validated, what needs the owner's decision.

When domain schemas change, run `python scripts\export_schemas.py` from the root, then `npm run types:generate` from `frontend/`. Verify with `python scripts\export_schemas.py --check` and `npm run types:check` in their respective directories and run the contract tests. Reproduce fixtures with `python tests\fixtures\make_minimal_ifc.py` only for an authorised fixture change; never repair an existing IFC in place.

## 11. Delivery Milestones, Engineering Tasks and Progress Tracking

This section applies to every human and AI contributor, including Codex, Claude Code, Gemini and GitHub Copilot.

1. `docs/IMPLEMENTATION_PLAN.md` is the authoritative delivery schedule, milestone-to-task mapping and engineering task register.
2. `CHANGELOG.md` records significant implementation, architectural and delivery-framework changes.
3. Read the task-to-milestone mapping before starting work.
4. Task IDs and milestone IDs are not interchangeable. Milestones describe delivery capabilities; tasks describe engineering work.
5. Every implementation task, pull request and completion report must reference its T-ID and contributing M-ID or M-IDs.
6. Do not independently renumber, rename or reinterpret existing tasks.
7. Do not mark a task complete without implementation and verification evidence. A plan entry, code presence or agent assertion alone is not evidence.
8. Do not infer milestone completion from a task's completion alone; apply that milestone's exit criteria.
9. A task scope change requires corresponding updates to `docs/IMPLEMENTATION_PLAN.md` and `CHANGELOG.md`.
10. New corrective subtasks use decimal identifiers such as T-1.1; do not shift subsequent task numbers.
11. Record all substantive completed work in `CHANGELOG.md`.
12. If documentation and repository evidence disagree, report the discrepancy rather than inventing a resolution.
13. Preserve the current delivery schedule and accepted architecture unless the project owner explicitly approves a change. Do not move the 4 November 2026 submission deadline.

Every implementation completion report must use this format:

- Task ID:
- Associated milestone(s):
- Implementation status:
- Files changed:
- Acceptance criteria passed:
- Test evidence:
- Changelog updated:
- Implementation plan updated:
- Remaining blockers:
- Recommended next task:

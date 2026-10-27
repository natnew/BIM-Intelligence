# AGENTS.md — Engineering rules for BIM Intelligence

This file governs every contributor, human or AI coding agent, working in this repository. Read it before changing anything. Where it conflicts with convenience, it wins.

## 1. Project context

BIM Intelligence is an AI-native architectural BIM review application built for the Meta Global AI Developer Hackathon (26 October – 4 November 2026). It ingests IFC models and project requirement documents, runs deterministic checks, and uses Meta Muse Spark (via the Meta Model API) to interpret requirements, plan reviews and explain findings.

Current phase: **architecture complete, implementation not started.** Authoritative design documents:

- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) — how the system is built
- [docs/REQUIREMENTS.md](./docs/REQUIREMENTS.md) — what it must do (`FR-*`, `NFR-*`, `C-*` ids)
- [docs/DECISIONS.md](./docs/DECISIONS.md) — why (`ADR-*`); open questions (`OQ-*`)
- [docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md) — when
- [docs/EVALUATION.md](./docs/EVALUATION.md) — how we know it works

If you need to make an architectural assumption the documents do not cover, **stop and record it** as a new ADR or open question before implementing.

## 2. Engineering principles

1. **Findings are deterministic.** Only IfcTester or a registered native rule may create a `Finding`. No LLM output is ever written into `findings.json`. (`ADR-001`, `C-01`, `C-02`)
2. **The model proposes; code verifies; the human decides.** Requirement candidates need verbatim quotes and human confirmation; plans are filtered against the registry; explanations pass a grounding check. (`ADR-008`, `ADR-009`)
3. **Smallest effective architecture.** One process, one orchestrator, file-system storage. Do not add services, queues, databases or frameworks without an ADR. (`C-08`)
4. **Schemas are the contract.** Domain models live in `backend/bim_intelligence/schemas/` (Pydantic v2) and are exported to the frontend. Change a schema → regenerate types → update tests. (`C-07`, `ADR-014`)
5. **The IFC is read-only.** Never write to or re-save an uploaded model. (`C-04`)
6. **Say only what is true.** Documentation describes the system as built; metrics appear only after they are measured. Prefer "designed to" and "intended to" over "does" until there is a test.

## 3. Directory conventions

See [ARCHITECTURE.md Appendix A](./docs/ARCHITECTURE.md#appendix-a--recommended-repository-structure). Rules:

- Create a directory only when adding its first real file. No placeholder folders.
- `backend/bim_intelligence/<package>/` — one package per component; no cross-imports from `api/` into anything but `schemas/`, `store/`, `orchestration/`, `bim/`, `requirements/`, `reporting/` entry points.
- `llm/` is the **only** package that imports the `openai` SDK.
- `bim/` and `validation/` are the **only** packages that import `ifcopenshell` / `ifctester`.
- Prompts live in `orchestration/prompts/` and `reporting/prompts/` as versioned files (`planner.v1.md`); never inline long prompts in code.
- `tests/unit/` mirrors the backend package layout; `tests/scenario/` holds end-to-end tests; small hand-built IFC/IDS fixtures go in `tests/fixtures/`.
- `tests/evaluation/` holds the metrics runner and LLM recordings; it is not part of the default `pytest` run and may import the backend as a library. Benchmark inputs live in `datasets/` (see its README for the synthetic/permitted policy).
- `frontend/src/viewer/` is the only place that imports `@thatopen/*`, `web-ifc` or `three`.
- `docs/` holds engineering documentation only. No planning notes, scratch files or meeting logs.
- `data/` is runtime storage and is git-ignored.
- `hackathon-private/` is confidential and git-ignored. Never copy its contents into tracked files; summarise.

## 4. Dependency management

- **Python 3.10–3.12 only** (`requires-python = ">=3.10,<3.13"`); develop on 3.12. IfcOpenShell has no wheels for 3.13+. (`ADR-005`)
- Backend dependencies in the root `pyproject.toml` with pinned minimums and upper bounds for `ifcopenshell`, `ifctester`, `openai`, `fastapi`, `pydantic`. Dev extras under `[project.optional-dependencies] dev`. Install from the repository root with `pip install -e ".[dev]"`.
- Frontend dependencies in `frontend/package.json` with a committed lockfile. Respect That Open Components peer ranges (`three >= 0.182.0`, `web-ifc >= 0.0.77`).
- Adding a dependency requires: a one-line justification in the PR/commit message, licence check (permissive or LGPL as installed package), and an entry in the README licence table if user-facing.
- Do not install packages speculatively. Do not add an agent framework; the orchestrator is intentionally hand-rolled (`ADR-002`, `ADR-003`).

## 5. Code quality requirements

**Python**

- Type hints on all public functions and dataclass/Pydantic fields; `mypy --strict` on `schemas/`, `validation/`, `orchestration/`; `mypy` default elsewhere.
- `ruff` for lint and format (`ruff check`, `ruff format`); line length 100.
- Small, composable functions; explicit inputs/outputs; no module-level mutable state.
- Custom exception types per component (`IfcLoadError`, `PlanViolation`, `GroundingError`, …) with contextual messages.
- I/O, business logic, model calls and evaluation logic in separate modules.
- Comments only where the *why* is not obvious. No commented-out code.

**TypeScript / React**

- `strict: true`; no `any` in domain types; generated API types are read-only.
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
- **No live API calls in the default test run.** Live tests are marked `@pytest.mark.live`, skipped unless `BIMI_LIVE_LLM=1`, and require explicit spend approval from the project owner (`C-06`).
- **Determinism:** tests must not depend on wall-clock time, random ordering or network. Seed anything random.
- Frontend: Vitest + React Testing Library for panels; one Playwright smoke test on the benchmark.
- Evaluation runs (`tests/evaluation/run_eval.py`) are not tests; they produce metrics that are reported, never asserted as passing until thresholds are agreed.

## 7. Documentation responsibilities

When you change behaviour, update documentation in the same change:

| Change | Update |
|---|---|
| New or changed endpoint | ARCHITECTURE §11 and the OpenAPI description strings |
| New rule, tool or schema field | ARCHITECTURE §7/§8/§10; REQUIREMENTS acceptance criteria if affected |
| Architectural choice | New ADR in DECISIONS.md (never edit an adopted ADR's decision text; supersede it) |
| Setup or command change | README setup/testing sections — run the commands before writing them |
| Metric produced | EVALUATION §8 with commit hash and date |
| New risk or closed risk | RISKS.md |

Mermaid diagrams must render on GitHub; check syntax before committing. Keep terminology consistent: *Finding*, *Requirement*, *CheckSpec*, *EvidenceBundle*, *Explanation*, *ReviewPlan*, *ModelIndex*.

## 8. Security requirements

- Secrets only from environment variables; `.env` is git-ignored; `.env.example` lists names with empty or safe values. Never log `MODEL_API_KEY` or echo configuration from `/health`.
- Default model ids are Standard mode; `-contributor` ids are rejected unless `ALLOW_CONTRIBUTOR_MODELS=true`. (`ADR-010`, `NFR-08`)
- Uploads: extension allow-list, size limits, fixed stored filenames, session-scoped directories. No user-controlled paths.
- The LLM tool registry is read-only; no shell, file-system or network tools are ever exposed to the model.
- Outbound network calls go only to `LLM_BASE_URL`. No telemetry, no analytics.
- Server binds to `127.0.0.1` unless `ALLOW_REMOTE=true`.
- Treat BEP/document content as untrusted input (prompt-injection surface). Validate all model output by schema; never execute anything derived from document text without the plan filter and human confirmation.
- Run a secret scan before any push. Never commit `.ifc` files outside `tests/fixtures/` or `datasets/`, anything under `data/`, or anything under `hackathon-private/`.

## 9. Agent boundaries and prohibited actions

AI coding agents working in this repository **must not**:

- Commit or push without explicit approval from the project owner.
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
2. Write or update the failing test.
3. Implement the smallest complete change that satisfies the requirement — including error handling and documentation.
4. Run `ruff check . && ruff format --check . && mypy && pytest` (backend, from the repository root) or `npm run lint && npm run format:check && npm run typecheck && npm test` (frontend).
5. Update docs per §7.
6. Summarise: what changed, which requirement ids it serves, what was validated, what needs the owner's decision.

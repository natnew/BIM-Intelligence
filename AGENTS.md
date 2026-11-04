# AGENTS.md — Engineering rules for BIM Intelligence

These rules apply to every contributor, human or AI coding agent. Read them before changing
anything; frontend changes also follow [`frontend/AGENTS.md`](./frontend/AGENTS.md).

## 1. Project context

BIM Intelligence is an AI-assisted architectural BIM model-review application. It ingests an IFC
model and IDS requirements, runs deterministic checks with IfcTester and registered native rules,
and shows the resulting findings in an interactive 3D viewer. Meta Muse Spark, through the Meta
Model API, proposes review plans over confirmed checks and writes grounded explanations of
findings. It never establishes a finding itself.

Reference documents:

- [README](./README.md) — product overview, setup and limitations
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) — technical architecture and component boundaries
- [docs/DECISIONS.md](./docs/DECISIONS.md) — architectural decision records (`ADR-*`) and open
  questions (`OQ-*`)
- [CHANGELOG.md](./CHANGELOG.md) — release history

When sources disagree: source code and schemas define implemented behaviour; tests show what has
been verified; adopted ADRs record design decisions. Report a contradiction rather than silently
resolving it. Code that conflicts with an adopted ADR is a defect, not a reason to rewrite the ADR.

If a change needs an architectural assumption the documents do not cover, record it as a new ADR
or open question before implementing it.

## 2. Engineering principles

1. **Findings are deterministic.** Only IfcTester or a registered native rule may create a
   `Finding`. No model output is ever written into `findings.json`. (`ADR-001`)
2. **The model proposes; code verifies; the human decides.** Requirement candidates need verbatim
   quotes and human confirmation; plans are filtered against the confirmed-check registry;
   explanations pass a grounding check. (`ADR-008`, `ADR-009`)
3. **Smallest effective architecture.** One process, one orchestrator, file-system storage. Do not
   add services, queues, databases or frameworks without an ADR.
4. **Schemas are the contract.** Domain models live in `backend/bim_intelligence/schemas/`
   (Pydantic v2) and are exported to the frontend. Change a schema → regenerate types → update
   tests. (`ADR-014`)
5. **The IFC is read-only.** Never write to or re-save an uploaded model.
6. **Say only what is true.** Documentation describes the system as built, and metrics appear only
   after they are measured.
7. **Preserve version integrity.** Bind reviews and reads to the model hash, document hashes,
   confirmed requirement revisions and rule versions. Keep session locks, atomic publication and
   `ETag`/`If-Match` guards; a mismatch must fail visibly rather than mix versions.
   (`ADR-015`–`ADR-019`)

## 3. Directory conventions

See [ARCHITECTURE.md Appendix A](./docs/ARCHITECTURE.md#appendix-a--repository-structure).

- Create a directory only when adding its first real file. No placeholder folders.
- `backend/bim_intelligence/<package>/` holds one package per component. Respect the import
  allow-list enforced by `tests/unit/test_import_boundaries.py`.
- `llm/` is the **only** package that imports the `openai` SDK.
- `bim/` and `validation/` are the **only** packages that import `ifcopenshell` / `ifctester`.
- Prompts live in `orchestration/prompts/` and `reporting/prompts/` as versioned files
  (`planner.v2.md`, `requirements.v1.md`, `explanation.v1.md`). Never inline long prompts in code.
- `tests/unit/` mirrors the backend package layout; `tests/scenario/` holds end-to-end tests; small
  hand-built IFC/IDS fixtures go in `tests/fixtures/`.
- `tests/evaluation/` holds the synthetic benchmark runner and its regression tests. Generated
  benchmark inputs, results and response recordings stay in git-ignored paths. See
  [datasets/README.md](./datasets/README.md).
- `frontend/src/viewer/` is the only place that imports `@thatopen/*`, `web-ifc` or `three`.
- `docs/` holds public technical documentation only: no planning notes, scratch files or logs.
- `data/` is runtime storage and is git-ignored.
- `local-private/` is a git-ignored workspace for private models, documents and test evidence on
  your own machine. Nothing in it may be copied into tracked files.

## 4. Dependency management

- **Python 3.10–3.12 only** (`requires-python = ">=3.10,<3.13"`); develop on 3.12. IfcOpenShell
  publishes wheels for these versions only. (`ADR-005`)
- Backend dependencies are declared in the root `pyproject.toml` with minimums and upper bounds;
  development tools are in the `dev` extra. Install with `pip install -e ".[dev]"`.
- Frontend dependencies are in `frontend/package.json` with a committed lockfile; install with
  `npm ci`. Respect That Open Components' peer ranges (`three >= 0.182.0`, `web-ifc >= 0.0.77`).
- A new dependency needs a one-line justification in the pull request, a licence check (permissive,
  or LGPL as an installed package) and an entry in
  [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
- `web-ifc` is MPL-2.0; [ADR-007](./docs/DECISIONS.md#adr-007-browser-side-geometry-with-that-open-components)
  records this as a viewer-stack exception, not a general waiver.
- Do not add an agent framework; the orchestrator is intentionally hand-written
  (`ADR-002`, `ADR-003`).

## 5. Code quality requirements

**Python**

- Type hints on all public functions and on dataclass and Pydantic fields. `mypy` runs with the
  root `pyproject.toml`; strict mode applies to `schemas/`, `validation/` and `orchestration/`.
- `ruff` for lint and format (`ruff check`, `ruff format`); line length 100.
- Small, composable functions with explicit inputs and outputs; no module-level mutable state.
- Custom exception types per component (`IfcLoadError`, `PlanViolation`, `GroundingError`, …) with
  contextual messages.
- Keep I/O, business logic, model calls and evaluation logic in separate modules.
- Comment only where the _why_ is not obvious. No commented-out code.

**TypeScript / React**

- `strict: true`; no `any` in domain types. Never hand-edit generated API schemas or types;
  regenerate them from Pydantic (§10).
- Functional components and hooks; one component per file; presentation separated from state and
  data fetching.
- Every data-bearing component handles loading, empty, error and success states.
- Semantic HTML and ARIA labels on interactive controls; the finding list is keyboard-reachable.
- `oxlint` and `prettier` with the repository configuration (`npm run lint`,
  `npm run format:check`).

**Both**

- British English in documentation, UI copy and comments.
- No TODO or FIXME without an issue reference.

## 6. Testing standards

- **Unit tests are required** for Model Index construction, every native rule (positive, negative
  and boundary cases), IDS compilation, the grounding checker (including adversarial inputs), plan
  filtering, configuration validation (including contributor-model rejection) and the finding
  normaliser.
- **Scenario tests** run the full review on a fixture with `FakeClient`, including
  `LLM_MODE=off` and a model failure mid-run.
- **Regression tests** for every fixed defect.
- **No live API calls in the default test run.** The single live smoke test is marked
  `@pytest.mark.live` and runs only with `-m live`, `BIMI_LIVE_LLM=1`,
  `BIMI_LIVE_APPROVAL=T5-META-MUSE-SPARK-SMOKE` and valid live settings. It makes a billed request.
- **Determinism:** tests must not depend on wall-clock time, random ordering or the network. Seed
  anything random.
- Frontend: Vitest and React Testing Library.
- The synthetic benchmark (`tests/evaluation/run_eval.py`) produces scoped measurements separate
  from the regression tests. Do not generalise its small synthetic result to real projects or to
  live model quality.

## 7. Documentation responsibilities

When you change behaviour, update the documentation in the same change:

| Change                         | Update                                                                     |
| ------------------------------ | -------------------------------------------------------------------------- |
| New or changed endpoint        | ARCHITECTURE §11 and the OpenAPI description strings                       |
| New rule, tool or schema field | ARCHITECTURE §7, §8 or §10                                                 |
| Architectural choice           | A new ADR in DECISIONS.md (never edit an adopted decision; supersede it)   |
| Setup or command change        | The README setup and testing sections; run the commands before writing them |
| New dependency or asset        | THIRD_PARTY_NOTICES.md                                                     |
| User-visible change            | CHANGELOG.md                                                               |

Mermaid diagrams must render on GitHub. Keep terminology consistent: _Finding_, _Requirement_,
_CheckSpec_, _EvidenceBundle_, _Explanation_, _ReviewPlan_, _ModelIndex_.

## 8. Security requirements

- Secrets come only from environment variables or an ignored local `.env`; `.env.example` lists
  names with empty or safe values. Never log or return `MODEL_API_KEY`. `/health` may report only
  its defined safe diagnostics, including the LLM mode and whether a key is configured.
- Default model ids are Standard mode; `-contributor` ids are rejected unless
  `ALLOW_CONTRIBUTOR_MODELS=true`. (`ADR-010`)
- Uploads use an extension allow-list, size limits, fixed stored file names and session-scoped
  directories. No user-controlled paths.
- Model-assisted plans may reference confirmed check ids only. No shell, file-system or network
  tools are exposed to the model.
- Outbound calls go only to `LLM_BASE_URL`, which is constrained to `https://api.meta.ai/v1`. Serve
  viewer workers and WASM locally and disable remote IDS schema loading. No telemetry or
  analytics.
- `LLM_MODE=off` is the default. Live mode requires `MODEL_API_KEY` and `ALLOW_LIVE_LLM=true`; Off
  and Replay must never fall back to Live. Preserve the fail-closed budget reservations and usage
  accounting under `DATA_DIR/llm/`. (`ADR-020`)
- The server binds to `127.0.0.1` unless `ALLOW_REMOTE=true`.
- Treat requirement-document content as untrusted input (a prompt-injection surface). Validate all
  model output against a schema, and never act on document text without the plan filter and human
  confirmation.
- Run the [secret scanner](./scripts/secret_scan.py) before pushing, and keep the
  [pre-commit hook](./.githooks/pre-commit). Never commit `.ifc` files outside `tests/fixtures/`,
  `datasets/synthetic/` or `datasets/permitted/`, or anything under `data/` or `local-private/`.

### Private data handling and provenance

- Never commit private material or copy it into tracked directories. This includes real BIM
  models, client or project documents, screenshots, tester feedback and private test evidence.
  Ignore rules are not access controls and do not protect files that are already tracked.
- Do not send real BIM files, client documents, screenshots or feedback to a model provider unless
  you have the right to share them. This includes extracted text and derived excerpts.
- Do not publish model-derived facts or private project names from someone else's data.
- Public demonstrations and tests use synthetic or openly licensed data. Record the source and
  licence of any non-synthetic public input in [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
- Label AI explanations separately from deterministic findings. An explanation must never be
  presented or stored as a `Finding`.

## 9. AI coding agent boundaries

AI coding agents working in this repository **must not**:

- push to `main`, merge a pull request, create a release or deploy without a maintainer's explicit
  instruction;
- make live Meta Model API calls, or any other paid call, without explicit permission for that
  session;
- modify, re-save or "fix" an uploaded or fixture IFC in place; generate new fixtures with the
  scripts instead;
- write a `Finding` from model output or add an `llm` value to `Finding.method`;
- bypass the plan filter, tool-call cap, verbatim-quote check or grounding check, even
  temporarily;
- add dependencies, services, databases or frameworks without an ADR;
- copy proprietary code, UI assets or documentation from Revit, Navisworks, Solibri, BIMcollab or
  any other product;
- claim that functionality works, or that a metric was achieved, without a test or a recorded
  evaluation run;
- add planning notes, scratch files or TODO lists to the repository;
- work outside this repository's directory.

When one of these blocks you, stop, explain the constraint and ask.

## 10. Working pattern for a change

1. Read the relevant ADRs and the code you are changing.
2. For a behaviour change, write or update a failing test first. For a documentation-only change,
   check every claim, path, link and command against the current code.
3. Implement the smallest complete change, including error handling and documentation.
4. Run the checks. Backend, from the repository root: `ruff check .`, `ruff format --check .`,
   `mypy` and `pytest`. Frontend, from `frontend/`: `npm run lint`, `npm run format:check`,
   `npm run typecheck`, `npm run types:check`, `npm test` and `npm run build`.
5. Update the documentation as described in §7.
6. Summarise what changed, what you checked and anything that needs a maintainer's decision.

When domain schemas change, run `python scripts/export_schemas.py` from the root, then
`npm run types:generate` from `frontend/`, and verify with `python scripts/export_schemas.py --check`
and `npm run types:check`. Regenerate the minimal fixture with
`python tests/fixtures/make_minimal_ifc.py` only when the fixture itself must change; never repair
an existing IFC in place.

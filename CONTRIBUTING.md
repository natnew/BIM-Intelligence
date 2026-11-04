# Contributing to BIM Intelligence

Thank you for your interest in BIM Intelligence, an AI-assisted BIM model-review application. It
is an early prototype, so read the [README](./README.md) for what it does and its current
limitations before starting work. The [engineering rules](./AGENTS.md) apply to every contributor,
human or AI coding agent; this guide summarises how to work within them.

## Development environment

- Python 3.10–3.12 (3.12 recommended).
- Node.js 20.19+ (20.x) or 22.12+ (22.x).
- Git and npm.

From the repository root, create and activate a virtual environment and install the backend:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Install the frontend dependencies with `npm ci` from `frontend/`. Run the two parts in separate
terminals:

```bash
# Repository root
uvicorn bim_intelligence.api.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

```bash
# frontend/
npm run dev
```

The API listens on loopback by default. All configuration is described in
[`.env.example`](./.env.example); AI calls are off by default. To run the secret scan before
each commit (it needs the Gitleaks CLI), run `git config core.hooksPath .githooks`.

## Repository map

| Path                                      | Responsibility                                            |
| ----------------------------------------- | --------------------------------------------------------- |
| `backend/bim_intelligence/api/`           | FastAPI routes and the HTTP boundary                      |
| `backend/bim_intelligence/schemas/`       | Pydantic domain and API contracts                         |
| `backend/bim_intelligence/bim/`           | IFC loading, indexing and ingestion                       |
| `backend/bim_intelligence/requirements/`  | IDS import and narrative requirement handling             |
| `backend/bim_intelligence/validation/`    | IfcTester integration and registered deterministic rules  |
| `backend/bim_intelligence/orchestration/` | Bounded review planning and execution                     |
| `backend/bim_intelligence/reporting/`     | Grounded finding explanations                             |
| `backend/bim_intelligence/llm/`           | Model-client boundary and spend controls                  |
| `backend/bim_intelligence/store/`         | Session-scoped file-system persistence                    |
| `frontend/`                               | React and TypeScript application                          |
| `tests/unit/`, `tests/scenario/`          | Unit and end-to-end fixture tests                         |
| `tests/evaluation/`, `datasets/`          | Synthetic benchmark generator, runner and dataset notes   |
| `examples/`                               | Example collections and draft IDS files                   |
| `docs/`                                   | Technical architecture and architectural decision records |

The [architecture](./docs/ARCHITECTURE.md) describes component boundaries and the
[decision records](./docs/DECISIONS.md) explain the main design choices.

## Engineering expectations

Follow [AGENTS.md](./AGENTS.md) for Python, TypeScript, React, formatting, typing, privacy and
testing rules. In particular:

- Keep changes focused, typed and consistent with existing patterns.
- Update the relevant documentation in the same change, and describe only behaviour that is
  implemented and tested.
- Add a regression test for every fixed defect and tests for new behaviour.
- Discuss new dependencies, services or architectural changes in an issue first; significant
  design choices are recorded as a new ADR in [DECISIONS.md](./docs/DECISIONS.md).

**Findings are deterministic.** Only IfcTester or a registered native rule may create a `Finding`.
Model-generated text may propose a plan or explain a finding, but it can never assert a model defect
or write to `findings.json`. Extracted requirements need verbatim source quotes and human
confirmation, and model plans and explanations are validated by code.

### Tests and checks

Backend, from the repository root:

```bash
ruff check .
ruff format --check .
mypy
pytest
```

Frontend, from `frontend/`:

```bash
npm run lint
npm run format:check
npm run typecheck
npm run types:check
npm test
npm run build
```

The default test suites make no live model API calls. The synthetic benchmark is run separately
and produces measurements rather than pass/fail results; see
[`datasets/README.md`](./datasets/README.md). The single live smoke test is opt-in and makes a
billed request, so run it only with your own API key and budget.

## IFC, IDS and test data

Use the committed synthetic fixtures for tests. Never modify or re-save an uploaded or fixture IFC
in place; generate new fixtures with the fixture scripts instead. Keep real or client-derived
models, documents, screenshots and feedback out of the repository; only synthetic or openly
licensed material belongs in tests and demonstrations. See the
[private-data rules](./AGENTS.md#private-data-handling-and-provenance).

The upload path accepts `.ifc` models and `.ids`, `.md` or `.txt` requirement documents. IDS 1.0
specifications are validated and imported as confirmed requirements. Markdown and text documents
are stored as untrusted source material and do not become executable requirements automatically.
PDF ingestion is not implemented.

## Schema and generated contract changes

Pydantic schemas are the domain and API contract. If a schema changes, update its tests and
regenerate the exported JSON Schemas and TypeScript types:

```bash
python scripts/export_schemas.py
cd frontend
npm run types:generate
npm run types:check
```

Do not edit files under `frontend/src/api/generated/` by hand. Review the schema and generated diff
together, then run the backend and frontend checks.

## Branches and pull requests

Work on a focused branch from the current `main`, then open a pull request using the
[pull-request template](./.github/pull_request_template.md). Summarise what changed and why, the
checks you ran and anything that needs a maintainer's decision. Add an entry to
[`CHANGELOG.md`](./CHANGELOG.md) for user-visible changes. Do not claim functionality or metrics
you have not tested.

Opening a pull request does not guarantee it will be accepted or reviewed within a set time.

## Current limitations

BIM Intelligence is not a released or hosted service. Its rule library, AI workflow, evaluation
coverage and reporting are still limited, and it has no authentication or hosted deployment. An
empty findings list is not proof of compliance. See
[Status and limitations](./README.md#status-and-limitations) in the README.

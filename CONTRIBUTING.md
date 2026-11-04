# Contributing to BIM Intelligence

BIM Intelligence is an AI-native architectural BIM review application. Its current implementation
is pre-alpha and incomplete; read the [README](./README.md) before choosing work. This guide complements
the repository-wide [engineering rules](./AGENTS.md); it does not replace them.

## Development environment

- Python 3.10–3.12; develop on Python 3.12.
- Node.js 20 or 22 for the frontend workflows used in CI.
- Git and npm.

From the repository root, create and activate a virtual environment, then install the backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

For macOS or Linux, activate with `source .venv/bin/activate`. To install the frontend dependencies,
run `npm ci` from `frontend/`.

The backend and frontend can be run in separate terminals:

```powershell
# Repository root
uvicorn bim_intelligence.api.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

```powershell
# frontend/
npm run dev
```

The API listens on loopback by default. Configuration is described in
[`.env.example`](./.env.example); live model use is off by default and requires explicit
configuration. See the [README setup and testing instructions](./README.md#local-setup).

## Repository map

| Path                                      | Responsibility                                                     |
| ----------------------------------------- | ------------------------------------------------------------------ |
| `backend/bim_intelligence/api/`           | FastAPI routes and HTTP boundary                                   |
| `backend/bim_intelligence/schemas/`       | Pydantic domain and API contracts                                  |
| `backend/bim_intelligence/bim/`           | IFC loading, indexing and ingestion                                |
| `backend/bim_intelligence/requirements/`  | IDS import and narrative requirement handling                      |
| `backend/bim_intelligence/validation/`    | IfcTester integration and registered deterministic rules           |
| `backend/bim_intelligence/orchestration/` | Bounded review planning and execution                              |
| `backend/bim_intelligence/llm/`           | Model-client boundary and budget controls                          |
| `backend/bim_intelligence/store/`         | Session-scoped file-system persistence                             |
| `frontend/`                               | React and TypeScript application                                   |
| `tests/unit/`, `tests/scenario/`          | Unit and end-to-end fixture tests                                  |
| `tests/evaluation/`, `datasets/`          | Opt-in evaluation code and synthetic/permitted data                |
| `docs/`                                   | Technical architecture and decision records                         |

The [technical architecture](./docs/ARCHITECTURE.md) describes component boundaries and the
[decision records](./docs/DECISIONS.md) explain the main design choices.

## Engineering and review expectations

Follow [AGENTS.md](./AGENTS.md) for Python, TypeScript, React, formatting, typing, privacy and
testing rules. In particular:

- Keep changes focused, typed and consistent with existing patterns.
- Update relevant documentation when behaviour changes. Describe only functionality supported by
  implementation and evidence.
- Add regression coverage for fixed defects and tests for new behaviour.
- Reference the applicable T-ID and milestone in delivery work; do not mark a task complete without
  its acceptance evidence.
- Do not add dependencies, services, frameworks or architectural behaviour without the required
  owner approval and decision record.

**Findings are deterministic.** Only IfcTester or a registered native rule may create a `Finding`.
Model-generated text may propose or explain, but it cannot independently assert a model defect or
write to `findings.json`. Requirement candidates need verbatim source quotes and human confirmation;
model plans and explanations are validated by code.

### Tests and checks

Run the backend checks from the repository root:

```bash
ruff check .
ruff format --check .
mypy
pytest
```

Run frontend checks from `frontend/`:

```bash
npm run lint
npm run format:check
npm run typecheck
npm run types:check
npm test
npm run build
```

The default test suites do not make live model API calls. Evaluation runs are separate from tests
and produce measurements rather than pass/fail claims; see
[`datasets/README.md`](./datasets/README.md). Live tests require explicit project-owner approval.

## IFC, IDS and test data

Use the committed small synthetic fixtures for tests. Do not modify or re-save an uploaded or
fixture IFC in place. Generate new synthetic fixtures through the documented fixture tooling and
keep private or client-derived models, documents, screenshots and feedback out of tracked files.
Only synthetic or expressly redistributable material belongs in public demonstrations; see
[AGENTS.md private-data rules](./AGENTS.md#8-security-requirements).

The implemented upload path accepts `.ifc` models and `.ids`, `.md` or `.txt` requirement documents.
IDS 1.0 specifications are validated and imported as confirmed requirements. Markdown and text
documents are stored as untrusted source material; they do not automatically become executable
requirements. PDF ingestion and parts of the planned requirement workflow remain unimplemented.
The [README status and limitations](./README.md#status-and-limitations) describe the verified
scope.

## Schema and generated contract changes

Pydantic schemas are the domain/API contract. If a schema changes, update its tests and regenerate
the exported JSON Schemas and TypeScript types using the repository tooling:

```bash
python scripts/export_schemas.py
cd frontend
npm run types:generate
npm run types:check
```

Do not edit files under `frontend/src/api/generated/` by hand. Review the schema and generated
diff together, then run the relevant backend and frontend checks.

## Branches and pull requests

Work on a focused branch based on the current `main` branch, then open a pull request using the
[repository pull-request template](./.github/pull_request_template.md). Summarise the purpose,
requirements or task IDs served, validation actually performed and any owner decision needed.
Update `CHANGELOG.md` for substantive implementation or delivery-framework work. Do not claim
unverified functionality or metrics. A pull request does not imply acceptance or a response
timeframe; no broader external-contributor policy is stated here.

## Current limitations

The application is under active development, not a released or hosted service. The UI, rule library,
AI workflow, evaluation coverage and reporting are incomplete; the project does not provide
authentication or hosted deployment. Do not treat an empty findings list as proof of compliance.
Consult the README and task register for current evidence and outstanding work.

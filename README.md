# BIM-Intelligence

**AI-native architectural BIM model review.** Upload an IFC model and your project's BIM Execution Plan, state what you want reviewed in plain language, and get deterministic, traceable findings — explained in context, highlighted in 3D, and exported as a review report.

> **Development status: implementation in progress.** Verified slices cover domain contracts and a reproducible fixture, IFC ingestion and version-consistent storage, deterministic IDS/native review, the T-3 viewer, and the T-5 offline AI integration path. No live Meta request has been authorised or made; API compatibility remains unverified, the frontend AI panels and benchmark remain outstanding, and no benchmark metrics have been measured. See [Development status](#development-status).

Built for the Meta Global AI Developer Hackathon (26 October – 4 November 2026) using Meta Muse Spark via the Meta Model API.

---

## The professional problem

Before an architectural model is issued, someone has to confirm that it carries the information the project demands: the right property sets, agreed naming, correct classification codes, a valid spatial structure. Those demands live in prose — BIM Execution Plans and Exchange Information Requirements — and have to be turned into checks by hand. Checker output then arrives as hundreds of unexplained flags that a coordinator must triage without a clear line back to the clause that caused each one.

BIM Intelligence targets that gap for Architects, BIM Managers and BIM Coordinators.

## Core innovation

Most AI-in-BIM demonstrations put a language model in front of model data and ask it what is wrong. We do the opposite:

- **Findings are deterministic.** Every defect is produced by IfcTester (buildingSMART IDS) or a versioned Python rule. The model never asserts a model fact.
- **The model works on the parts that are genuinely linguistic:** reading the BEP into candidate requirements (with verbatim source quotes), turning a plain-language objective into a bounded review plan, and explaining findings from a structured evidence bundle.
- **Every explanation is grounded by a deterministic check** against that evidence before it is shown, and is labelled as AI-generated.
- **Nothing runs on an unconfirmed requirement.** A human confirms, edits or rejects each extracted requirement before it becomes a check.

The result is intended to be an assistant that behaves like a careful coordinator: it reads the project's own rules, runs the right checks, shows you the affected elements, and tells you why — without inventing anything.

## High-level architecture

```mermaid
flowchart LR
    IFC["IFC model"] --> IDX["Model Index<br/>IfcOpenShell"]
    BEP["BEP / IDS"] --> REQ["Requirements Interpreter<br/>Muse Spark · structured output<br/>verbatim quotes · human confirmation"]
    OBJ["Review objective"] --> ORC["Review Orchestrator<br/>Muse Spark plans · Python executes<br/>typed read-only tools"]
    REQ --> ORC
    IDX --> VAL["Deterministic Validation<br/>IfcTester IDS · native rules"]
    ORC --> VAL
    VAL --> FND["Findings<br/>observed · expected · elements · rule version"]
    FND --> EVD["Evidence Collector"]
    EVD --> EXP["Explainer<br/>Muse Spark · grounding check"]
    FND --> UI["3D viewer + triage<br/>That Open Components"]
    EXP --> UI
    FND --> RPT["Report · Markdown · JSON · BCF"]
    EXP --> RPT
```

A single Python (FastAPI) backend and a single-page TypeScript frontend; no microservices, queues or databases in the MVP. Full design: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

## Technology stack

| Layer | Choice | Why |
|---|---|---|
| LLM | Meta **Muse Spark** (`muse-spark-1.3`) via the **Meta Model API**, called with the OpenAI Python SDK (`base_url=https://api.meta.ai/v1`) | Tool calling, JSON-schema structured output, 1M-token context; Standard mode does not train on submitted content |
| BIM processing | **IfcOpenShell** 0.9, **IfcTester** 0.9 (IDS 1.0), optional `ifcclash`, `bcf-client` | Reference openBIM tooling, pip-installable |
| Backend | **Python 3.12**, **FastAPI**, **Pydantic v2**, **pytest** | Typed schemas shared with the frontend; simple async API with SSE progress |
| Frontend | **React**, **TypeScript**, **Three.js**, **That Open Components** 3.6 (`web-ifc`) | Browser-side IFC Fragments viewer with GlobalId selection and deterministic finding highlights |
| Evaluation | Synthetic benchmark generated with `ifcopenshell.api`, defect injection, replayable LLM recordings | Reproducible precision/recall and grounding metrics without API spend |

Verified versions and sources: [docs/ARCHITECTURE.md — Appendix B](./docs/ARCHITECTURE.md#appendix-b--verified-technology-facts-26-october-2026-viewer-packages-checked-29-october-2026).

## Intended user workflow

1. **Upload** an IFC (IFC2X3 or IFC4) and a simplified BEP (Markdown/TXT/PDF) and/or an IDS file.
2. **Confirm requirements** — review extracted candidates with their source quotes and compiled checks; confirm, edit or reject.
3. **State an objective** — e.g. "Check fire-rating and classification completeness on external walls and doors for Stage 4 issue."
4. **Watch the plan run** — the orchestrator selects checks from a bounded tool registry; progress streams live.
5. **Triage in 3D** — select a finding to highlight affected elements; see observed vs expected, the BEP quote and the grounded explanation.
6. **Export** a traceable report (requirement → rule → finding → element) with provenance.

## Development status

| Area | Status |
|---|---|
| Architecture, requirements, decisions, delivery plan, evaluation design, risks, demo plan | Written — see [docs/](./docs) |
| Repository foundation: Python/FastAPI, Vite/React frontend, health panel and CI | **Done (Day 2)** — end-to-end review and AI-assisted workflows remain in progress |
| Domain schemas (`Finding`, `CheckSpec`, `Requirement`, `CheckResult`, `ReviewRun`, …), generated TypeScript contract, reproducible minimal IFC/IDS fixture | **Done (Day 2, T-0)** — see [ADR-015](./docs/DECISIONS.md#adr-015-contract-model-immutable-checkspec-content-addressed-finding-per-check-checkresult) |
| IFC ingestion: session store, read-only IFC loading and Model Index, `sessions` / `model` / `elements` endpoints with RFC 9457 errors | **Done (Day 3, T-1)** — tested on the minimal fixture and in-memory variants only; see [ADR-016](./docs/DECISIONS.md#adr-016-ingestion-contract-staged-upload-content-hash-etag-and-identifier-handling) |
| Deterministic IDS validation: IDS 1.0 import as confirmed requirements, per-check IfcTester execution, `Finding` / `CheckResult` normalisation, synchronous review run, `documents` / `requirements` / `reviews` / `findings` endpoints | **Done (Day 4, T-2)** — produces the two expected findings on the minimal fixture with byte-identical `findings.json` across runs; see [ADR-018](./docs/DECISIONS.md#adr-018-ids-import-establishes-confirmed-requirements-checks-are-hydrated-per-run-reviews-run-under-the-session-lock) |
| T-3 viewer: local IFC rendering, GlobalId selection, version-pinned findings and element details | **Verified on the minimal fixture** — see [T-3 evidence](./docs/IMPLEMENTATION_PLAN.md#t-3--interactive-3d-bim-viewer) |
| T-4 deterministic review workflow: bounded default plan, explicit native classification-consistency check, pinned run and viewer hand-off | **Verified on the minimal fixture** — no LLM calls; benchmark evaluation remains open under T-6 |
| T-5 offline AI interfaces: quote-verified TXT/Markdown candidates, bounded objective planning, grounded explanations, Fake/Replay clients and persistent spend safeguards | **Implemented and offline-tested** — no live API call; only existing confirmed CheckSpecs can be selected; full BEP-to-IDS authoring is out of scope |
| Meta API compatibility and integrated frontend AI panels | **Not verified / not implemented** — M0 API capability spike remains open; M2 is in progress |
| T-6 synthetic benchmark | **Measured locally** — 15 independently labelled P0 defects, seven clean controls; 1.000 precision/recall/F1 on this narrow IFC4 benchmark, byte-identical repeated findings and 14/14 IfcTester IDS entity agreement. This is not a general BIM accuracy or live model-quality result; see [docs/EVALUATION.md](./docs/EVALUATION.md). |
| Hackathon rule verification | Outstanding (see [docs/REQUIREMENTS.md — Open items](./docs/REQUIREMENTS.md#7-open-items)) |

## Development roadmap

See the authoritative [implementation plan](./docs/IMPLEMENTATION_PLAN.md), [changelog](./CHANGELOG.md) and [consolidated architecture review](./docs/BAKEOFF_ARCHITECTURE_REVIEW.md). M0–M4 are delivery milestones; T-0–T-8 are engineering tasks that contribute to one or more milestones, with T-1.1 as a corrective subtask. Read the mapping and task register before taking implementation work.

## Repository layout

| Path | Purpose |
|---|---|
| `backend/bim_intelligence/` | Python API, AI orchestration and BIM validation (installed from the root `pyproject.toml`) |
| `frontend/` | Interactive BIM review interface (Vite, React, TypeScript) |
| `tests/` | Unit, scenario and evaluation tests; small IFC/IDS fixtures |
| `datasets/` | Synthetic and permitted IFC test models with their requirement artefacts |
| `docs/` | Technical architecture, decisions and engineering plans |
| `.github/` | CI workflows, PR template and Dependabot configuration |
| `hackathon-private/` | Untracked event documents and project briefs (git-ignored) |
| `AGENTS.md` | Engineering rules for human and AI contributors |
| `.env.example` | Configuration variable names without secret values |

## Local setup

Verified on Windows 11 with Python 3.12.12 and Node.js 24 (27 October 2026).

**Prerequisites:** Python **3.10–3.12** (IfcOpenShell publishes wheels for these versions only — Python 3.13+ will not install), Node.js 20+, a Meta Model API key for live LLM features (optional; the deterministic pipeline runs without one).

```bash
git clone https://github.com/natnew/BIM-Intelligence.git
cd BIM-Intelligence
cp .env.example .env            # LLM_MODE=off by default; Live requires explicit approval and opt-in

# Backend (from the repository root)
python -m venv .venv
# Windows: .venv\Scripts\activate   macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn bim_intelligence.api.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
# → http://127.0.0.1:8000/api/v1/health  and  /api/v1/docs

# Frontend (second terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173, proxies /api to :8000
```

Configuration variables are documented in [.env.example](./.env.example). The server refuses to bind to a non-loopback address unless `ALLOW_REMOTE=true`, and rejects `-contributor` model ids unless `ALLOW_CONTRIBUTOR_MODELS=true`.

### Upload and inspect a model

With the backend running, the ingestion endpoints can be exercised from a shell (run on 28 October 2026 against the committed fixture):

```bash
BASE=http://127.0.0.1:8000/api/v1
SID=$(curl -s -X POST $BASE/sessions | python -c "import json,sys; print(json.load(sys.stdin)['id'])")
curl -s -F "file=@tests/fixtures/minimal.ifc" $BASE/sessions/$SID/model
# {"ifc_schema":"IFC4","model_hash":"f2bd0007…","project_name":"Minimal Project",
#  "counts":{"IfcBuilding":1,"IfcBuildingStorey":1,"IfcSite":1,"IfcWall":3},"storeys":[…]}
curl -s $BASE/sessions/$SID/elements/21KH8X9wHPWw7JLiY2NtSZ    # W-001: psets, classification, container
curl -sI $BASE/sessions/$SID/model/file | grep -i etag          # ETag: "<sha256 of the stored bytes>"
```

Uploads are stored byte-for-byte under `DATA_DIR/sessions/<uuid>/models/<sha256>/model.ifc` (git-ignored) beside the index and summary built from those bytes, capped at `MAX_IFC_MB`, and made active by a single atomic write of the session record, so no read can mix two model versions ([ADR-017](./docs/DECISIONS.md#adr-017-content-addressed-model-versions-with-single-pointer-publication)). Every model read carries `ETag` = the version's quoted SHA-256 and honours `If-Match`. Errors are `application/problem+json`; the full surface is in [docs/ARCHITECTURE.md §11](./docs/ARCHITECTURE.md#11-api-architecture-and-principal-endpoints).

### Import an IDS and run a deterministic review

Continuing in the same session (run on 29 October 2026 against the committed fixtures):

```bash
curl -s -F "file=@tests/fixtures/minimal.ids" $BASE/sessions/$SID/documents
# 201 {"sha256":"e602233d…","kind":"ids","title":"BIM Intelligence minimal fixture",
#      "requirements":[{"id":"REQ-001","title":"External walls carry a fire rating","status":"confirmed",
#                       "check":{"id":"bca0b103d592b6d2","kind":"ids","rule_id":"ids:External walls carry a fire rating",…}},
#                      {"id":"REQ-002","title":"Walls carry a classification reference",…}]}
RUN=$(curl -s -X POST $BASE/sessions/$SID/reviews | python -c "import json,sys; print(json.load(sys.stdin)['id'])")
curl -s $BASE/sessions/$SID/reviews/$RUN
# {"status":"completed","plan_source":"default",
#  "check_results":[{"check_id":"bca0b103d592b6d2","requirement_id":"REQ-001","status":"failed","applicable_count":2,"finding_ids":["3473dbb1b87e93bd"],…},
#                   {"check_id":"4f00f7fd6f41e4a6","requirement_id":"REQ-002","status":"failed","applicable_count":3,"finding_ids":["e062895b2cf67af1"],…}],
#  "input_manifest":{"model_hash":"f2bd0007…","ids_hashes":["e602233d…"],"requirement_revisions":{"REQ-001":1,"REQ-002":1},…},…}
curl -s "$BASE/sessions/$SID/findings?run_id=$RUN"
# [{"id":"e062895b2cf67af1","requirement_id":"REQ-002","category":"classification_requirement",
#   "elements":[{"global_id":"2qvnbd6oPPKR1ac5HegGTJ","express_id":79,"ifc_type":"IfcWall","name":"W-003","storey":"L00"}],
#   "observed":"The entity has no classification","expected":"Shall be classified using Uniclass 2015","method":"ids",…},
#  {"id":"3473dbb1b87e93bd","requirement_id":"REQ-001","category":"property_requirement",
#   "elements":[{"global_id":"0QWMtUzsnUUONCUGc8Sqsa","express_id":59,"ifc_type":"IfcWall","name":"W-002","storey":"L00"}],
#   "observed":"The property set does not contain the required property",
#   "expected":"FireRating data shall be provided in the dataset Pset_WallCommon","method":"ids",…}]
```

Each `<specification>` of the IDS becomes a confirmed `Requirement` bound to an immutable, content-addressed `CheckSpec`. The default plan deduplicates confirmed checks in stable order and applies `MAX_PLAN_CHECKS` and `MAX_TOOL_CALLS_PER_RUN`; skipped, errored or not-applicable checks make the run `partial`. Findings have no timestamps, so `findings.json` is byte-identical across repeated runs over the same inputs. Nothing in this path calls a language model or the network ([ADR-018](./docs/DECISIONS.md#adr-018-ids-import-establishes-confirmed-requirements-checks-are-hydrated-per-run-reviews-run-under-the-session-lock)).

For the built-in P0 check that IDS 1.0 cannot express, explicitly add the parameter-free native classification-consistency requirement with `POST /sessions/$SID/requirements/native/classification-consistency`. In the existing viewer workspace, enter the session id and select **Run standard review** to start a model-version-pinned run and load its findings; per-check coverage is shown alongside the existing viewer. The registered rule is `classification.consistent_by_type` v1.0.0. IDS continues to check classification presence/system, required properties and expressible naming patterns; no P1/P2 native rules are included. IDS boolean values should be written in lower case (`true`/`false`); see [RISKS.md R-DEP-08](./docs/RISKS.md).

## Testing

```bash
# Backend, from the repository root (no API calls in the default run)
ruff check . && ruff format --check .
mypy
pytest

# Frontend
cd frontend
npm run lint && npm run format:check && npm run typecheck
npm run types:check             # generated contract types are current (ADR-014)
npm test
npm run build
cd ..

# Secret scanning (requires Gitleaks CLI; all findings are redacted)
python scripts/secret_scan.py --staged   # staged changes, also used by .githooks/pre-commit
python scripts/secret_scan.py --working-tree # tracked and untracked non-ignored files
python scripts/secret_scan.py            # full repository Git history

# Regenerate committed artefacts after changing them (then re-run the checks above)
python scripts/export_schemas.py          # Pydantic schemas → frontend/src/api/generated/*.schema.json
(cd frontend && npm run types:generate)   # JSON Schema → frontend/src/api/generated/types.ts
python tests/fixtures/make_minimal_ifc.py # tests/fixtures/minimal.ifc + minimal.ids (byte-reproducible)

# Offline synthetic benchmark (generates ignored data/results; no network or Meta API calls)
python -c "import sys; sys.path.insert(0, 'tests'); from evaluation.run_eval import main; raise SystemExit(main())"
python -m pytest tests/unit/evaluation tests/evaluation/test_run_eval.py -q

# Evaluation results, scope and known gaps: docs/EVALUATION.md
BIMI_LIVE_LLM=1 BIMI_LIVE_APPROVAL=T5-META-MUSE-SPARK-SMOKE pytest tests/live/test_meta_smoke.py -m live
```

The live command is an exact one-request smoke test, not general authorisation. It additionally requires `LLM_MODE=live`, `ALLOW_LIVE_LLM=true`, a backend `MODEL_API_KEY`, and sufficient remaining application budget. Do not run it until the project owner approves that session. The repository-local staged hook at `.githooks/pre-commit` is enabled through the repository-local `core.hooksPath` setting and runs the redacted staged Gitleaks scan. This setting overrides the prior global hook path for this repository; the project owner approved that change. The hook was verified against an empty index (no staged files). The same test, lint and type-check commands run in CI on Ubuntu and Windows ([.github/workflows/ci.yml](./.github/workflows/ci.yml)). Evaluation design, metrics and thresholds: [docs/EVALUATION.md](./docs/EVALUATION.md).

## Documentation

| Document | Purpose |
|---|---|
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Full technical architecture (20 sections, diagrams) |
| [docs/REQUIREMENTS.md](./docs/REQUIREMENTS.md) | Functional and non-functional requirements with traceability ids |
| [docs/DECISIONS.md](./docs/DECISIONS.md) | Architectural decision records and open questions |
| [docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md) | Ten-day schedule, milestones, critical path, scope reduction |
| [docs/EVALUATION.md](./docs/EVALUATION.md) | Benchmark design, metrics, reproduction |
| [docs/RISKS.md](./docs/RISKS.md) | Risk register |
| [docs/DEMO_PLAN.md](./docs/DEMO_PLAN.md) | Three-minute demo storyline and fallbacks |
| [AGENTS.md](./AGENTS.md) | Engineering rules for human and AI contributors |

## Hackathon context

Developed for the Meta Global AI Developer Hackathon, 26 October – 4 November 2026. The design uses Meta Muse Spark via the Meta Model API for planning, requirement interpretation and explanation. Event rules, judging criteria and submission constraints had not been verified at the time of writing and are tracked as open items.

## Limitations

- The MVP targets one architectural IFC, one simplified BEP and one IDS; multidisciplinary clash detection, voice input and image analysis are future work.
- Detection coverage is bounded by the rule library and IDS facets; the system does not "notice" defect types it has no rule for.
- The ≥ 90 % precision and recall target was met on the 15-instance synthetic IFC4 benchmark; this small result is scoped to its labelled defects and does not establish accuracy on other models or live Muse Spark quality. See [docs/EVALUATION.md](./docs/EVALUATION.md#8-results).
- No authentication or hosted deployment; local use only.

## Attribution and licences

Project code is released under the [MIT License](./LICENSE).

| Dependency | Licence | Note |
|---|---|---|
| IfcOpenShell, IfcTester, IfcClash, bcf-client | LGPL-3.0-or-later | Used as installed packages; no source vendored (IfcTester classifier to be confirmed) |
| That Open Components (`@thatopen/*`) | MIT | |
| Three.js | MIT | |
| `web-ifc` 0.0.77 | MPL-2.0 | Required by the selected IFC viewer stack. This is an exception to the repository's permissive-or-LGPL dependency preference; no source is vendored. Review the [upstream project](https://github.com/ThatOpen/engine_web-ifc) before distributing builds. |
| FastAPI, Pydantic, React, Vite | MIT | |
| xmlschema | MIT | Loads IfcTester's bundled IDS 1.0 XSD with remote imports disabled ([ADR-018](./docs/DECISIONS.md#adr-018-ids-import-establishes-confirmed-requirements-checks-are-hydrated-per-run-reviews-run-under-the-session-lock)) |
| buildingSMART IDS schema | See [buildingSMART/IDS](https://github.com/buildingSMART/IDS) | Standard reference only |

Meta, Muse and the Meta Model API are trademarks of Meta Platforms, Inc. Autodesk Revit, Navisworks, Solibri and BIMcollab are referenced as prior art only; no proprietary code or assets are used.

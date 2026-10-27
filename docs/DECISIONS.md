# Architectural Decisions

**Status:** v0.1, 26 October 2026. Decisions are numbered and immutable once adopted; superseding decisions reference the original.

Each record states the decision, the alternatives considered, the trade-offs, the evidence relied upon, and anything still unresolved. Evidence URLs were verified on 26 October 2026 unless stated otherwise.

| ADR | Title | Status |
|---|---|---|
| [ADR-001](#adr-001-findings-are-deterministic-the-llm-never-asserts-model-facts) | Findings are deterministic; the LLM never asserts model facts | Adopted |
| [ADR-002](#adr-002-meta-model-api-via-the-openai-python-sdk) | Meta Model API via the OpenAI Python SDK | Adopted |
| [ADR-003](#adr-003-single-orchestrator-with-typed-tool-registry) | Single orchestrator with typed tool registry | Adopted |
| [ADR-004](#adr-004-ifcopenshell--ifctester-for-model-access-and-ids-validation) | IfcOpenShell + IfcTester for model access and IDS validation | Adopted |
| [ADR-005](#adr-005-python-312-pinned) | Python 3.12 pinned | Adopted |
| [ADR-006](#adr-006-file-system-session-store-no-database) | File-system session store, no database | Adopted |
| [ADR-007](#adr-007-browser-side-geometry-with-that-open-components) | Browser-side geometry with That Open Components | Adopted, API spike pending |
| [ADR-008](#adr-008-human-confirmation-of-extracted-requirements) | Human confirmation of extracted requirements | Adopted |
| [ADR-009](#adr-009-deterministic-grounding-check-on-every-explanation) | Deterministic grounding check on every explanation | Adopted |
| [ADR-010](#adr-010-standard-mode-model-ids-only) | Standard-mode model ids only | Adopted |
| [ADR-011](#adr-011-synthetic-benchmark-with-defect-injection) | Synthetic benchmark with defect injection | Proposed, approval needed |
| [ADR-012](#adr-012-chat-completions-protocol-first) | Chat Completions protocol first | Adopted, revisit |
| [ADR-013](#adr-013-fastapi-background-tasks-and-sse-no-task-queue) | FastAPI background tasks and SSE, no task queue | Adopted |
| [ADR-014](#adr-014-frontend-types-generated-from-pydantic-json-schema) | Frontend types generated from Pydantic JSON Schema | Adopted |

---

## ADR-001 Findings are deterministic; the LLM never asserts model facts

**Decision.** A `Finding` may only be created by IfcTester (IDS) or a native Python rule. The `Finding.method` enumeration has no `llm` member. The LLM plans, proposes requirements, and explains; its outputs are validated by schema and, for explanations, by a grounding check against evidence.

**Alternatives.**
1. LLM inspects model data directly and reports defects — fastest to prototype; violates C-01/C-02 and makes precision unmeasurable.
2. LLM proposes findings that a deterministic step then verifies — adds a round-trip per finding; verification would re-implement the rules anyway.

**Trade-offs.** Coverage is bounded by the rule library; novel defect types cannot be "noticed" by the model. This is accepted: the brief requires measurable, verifiable findings, and the rule library can grow.

**Evidence.** Brief §2 (C-01, C-02), §5 ("design against hallucinated model facts"), §10.

**Unresolved.** None.

---

## ADR-002 Meta Model API via the OpenAI Python SDK

**Decision.** Call Meta Muse models through the OpenAI Python SDK configured with `base_url="https://api.meta.ai/v1"` and `api_key=MODEL_API_KEY`. Wrap it behind an `LLMClient` protocol with Fake, Recording and Replay implementations.

**Alternatives.**
1. Raw `httpx` client — more code, no benefit; the API is OpenAI-compatible.
2. LangChain / LlamaIndex / an agent framework — heavier dependency, obscures the tool loop we need to control tightly (NFR-06), and complicates cost accounting.
3. Muse Code SDK — TypeScript-only, aimed at driving the Muse Code CLI, not inference.

**Trade-offs.** Dependence on the OpenAI SDK's compatibility with Meta's implementation of `response_format` and tool calling; mitigated by the protocol abstraction and a Day-1 smoke test.

**Evidence.** dev.meta.ai/docs/quickstart (recommends `pip install openai`), /docs/protocols, /docs/structured-output, /docs/tool-calling; `openai` on PyPI requires Python ≥ 3.10.

**Unresolved.** Hackathon-specific credits or endpoints (none found publicly). Whether strict JSON-schema mode supports every Pydantic construct we use (test on Day 1).

---

## ADR-003 Single orchestrator with typed tool registry

**Decision.** Implement one orchestrator that (a) asks the model for a `ReviewPlan` via structured output, (b) filters the plan against the registry and confirmed requirements, (c) executes tools deterministically with a hard iteration cap, and (d) invokes the explainer. Requirement extraction and explanation are separate structured-output calls, not tools in the loop.

**Alternatives.**
1. Six cooperating LLM agents mirroring the brief's logical responsibilities — more calls, more failure modes, inter-agent protocol to design and debug; no capability gained because four of the six responsibilities are deterministic.
2. Fully deterministic pipeline with no planner — robust and cheap but fails FR-REQ-06 (interpreting natural-language objectives) and removes the AI-native differentiator.
3. Free-running tool-calling agent without a plan step — harder to cap, explain and evaluate; plan-then-execute gives an inspectable artefact.

**Trade-offs.** Plan-then-execute is less adaptive than an open loop; the model cannot react to intermediate results except through the single corrective re-prompt on tool errors. Accepted for the MVP; an iterative refinement step is a P2 proposal.

**Evidence.** Brief §5 ("favour the smallest effective orchestration architecture"); NFR-05, NFR-06.

**Unresolved.** Whether the planner adds measurable value over the default plan for the benchmark objectives — to be evaluated (EVALUATION §5).

---

## ADR-004 IfcOpenShell + IfcTester for model access and IDS validation

**Decision.** Use `ifcopenshell` 0.9.x for all IFC access and `ifctester` 0.9.x as the IDS 1.0 engine. Native rules supplement IDS for checks IDS cannot express.

**Alternatives.**
1. Write a custom IDS validator — duplicates a maintained reference implementation.
2. `web-ifc` on the backend via Node — would split the backend across runtimes.
3. Commercial checker APIs — not open, not permitted by the hackathon spirit of the brief.

**Trade-offs.** LGPL-3.0-or-later licence (dynamic use from Python is unproblematic for MIT project code). Geometry support is strongest for IFC2X3 and IFC4; IFC4X3 geometry is partial.

**Evidence.** pypi.org/project/ifcopenshell (0.9.0.post1, LGPL), docs.ifcopenshell.org/ifctester.html (IDS API and reporters), github.com/buildingSMART/IDS (schema 1.0.0).

**Unresolved.** `ifctester` licence classifier not shown on PyPI; assumed to follow IfcOpenShell (LGPL) — verify in source before publishing the licence table.

---

## ADR-005 Python 3.12 pinned

**Decision.** `requires-python = ">=3.10,<3.13"`; development and CI on 3.12.

**Alternatives.** Python 3.13+ — no IfcOpenShell wheels on PyPI; source build requires OpenCASCADE toolchain.

**Trade-offs.** Lose newer language features; negligible for this project.

**Evidence.** pypi.org/simple/ifcopenshell lists cp310–cp312 wheels only (checked 26 Oct 2026) despite `requires_python <3.16` metadata.

---

## ADR-006 File-system session store, no database

**Decision.** Each session is a directory under `data/sessions/{uuid}/` containing the original IFC, documents, `model_index.json`, `requirements.json`, `runs/{runId}/findings.json`, explanations, report and run log. Writes are atomic (write-to-temp then rename).

**Alternatives.**
1. SQLite — easy upgrade path; adds schema migrations and query code without a current need.
2. Postgres/Redis — infrastructure the brief explicitly discourages (§9).

**Trade-offs.** No concurrent multi-user access, no querying across sessions. Acceptable for a single-user hackathon demo. The `SessionStore` interface is the seam for SQLite later.

**Evidence.** Brief §9 ("avoid unnecessary … databases and infrastructure").

---

## ADR-007 Browser-side geometry with That Open Components

**Decision.** The frontend loads the IFC with `@thatopen/components` `IfcLoader` (web-ifc worker → Fragments) and highlights by GlobalId. The backend performs no geometry processing in the MVP.

**Alternatives.**
1. Backend tessellation with `ifcopenshell.geom` → glTF → Three.js — second pipeline, slow for large models, loses IFC semantics in the viewer.
2. Plain Three.js + web-ifc without That Open Components — more code for selection, culling and UI.
3. xeokit — strong viewer but AGPL/commercial licensing; That Open Components is MIT.

**Trade-offs.** The IFC is parsed twice (backend for semantics, browser for geometry). The join relies on GlobalId being present in both; IFC guarantees it. The 3.x Fragments pipeline and exact `Highlighter` API are a known uncertainty.

**Evidence.** registry.npmjs.org (`@thatopen/components` 3.6.0, MIT, peer `three >= 0.182.0`, `web-ifc >= 0.0.77`); thatopen.github.io/engine_components lists `core/IfcLoader`, `core/FragmentsManager`, `front/Highlighter`, `core/IDSSpecifications`, `core/BCFTopics` examples.

**Unresolved.** Exact GlobalId → fragment id lookup and highlight API in 3.6 — Day-1 spike (docs.thatopen.com unreachable from the research environment). Whether the `IDSSpecifications` component could run IDS in-browser as a cross-check (P2 curiosity, not planned).

---

## ADR-008 Human confirmation of extracted requirements

**Decision.** Requirements extracted from a BEP start as `proposed`. Only `confirmed` (or user-`edited`) requirements are executable. Uploaded IDS files are treated as confirmed because they are already machine-readable project artefacts.

**Alternatives.** Auto-confirm above a confidence threshold — the model's confidence is uncalibrated and a false requirement would generate false findings that look verified.

**Trade-offs.** One extra UI step; strongly aligned with the professional workflow and C-02.

**Evidence.** Brief §2, §5 ("uncontrolled tool execution"); ISO 19650 practice places requirement definition under human information-management control.

---

## ADR-009 Deterministic grounding check on every explanation

**Decision.** Explanations are structured outputs that must list the GlobalIds and properties they cite. A deterministic checker verifies all citations against the evidence bundle. Failures regenerate once, then fall back to a template.

**Alternatives.** LLM-as-judge for faithfulness — costs a second call, is itself fallible, and is unnecessary when evidence is structured.

**Trade-offs.** Explanations are constrained to cite only bundled evidence; broader architectural advice must be phrased generically. Numeric matching is heuristic (tolerant string match) and may produce false rejections; those are logged and fall back safely.

**Evidence.** Brief §2 (C-02), §5; repository instruction set ("prefer deterministic checks for invariants").

---

## ADR-010 Standard-mode model ids only

**Decision.** Configuration rejects model ids ending in `-contributor` unless `ALLOW_CONTRIBUTOR_MODELS=true`. Default model `muse-spark-1.3`.

**Alternatives.** Contributor mode — roughly 12× cheaper input tokens, but grants Meta permission to train on submitted content, which may include confidential project documents and model data.

**Trade-offs.** Higher cost per run; acceptable given the token budget (NFR-05).

**Evidence.** dev.meta.ai/docs/models and /docs/pricing-rate-limits (Standard mode: content not used for training; Contributor mode: opt-in training).

---

## ADR-011 Synthetic benchmark with defect injection

**Decision (proposed).** Generate a small, clean architectural IFC programmatically with `ifcopenshell.api` (storeys, walls, doors, windows, slabs, spaces, type objects, psets, classification), then inject 15–20 labelled defects by script to produce `benchmark.ifc` and `ground_truth.json`. Optionally run the same injector against an openly licensed sample IFC as a second dataset.

**Alternatives.**
1. Hand-edit a public sample IFC — licence and redistribution must be verified per file; manual edits are error-prone and hard to reproduce.
2. Use a real project model — confidentiality; cannot be committed.

**Trade-offs.** A synthetic model is simpler than a real one and may under-represent messy real-world data; the injector makes ground truth exact and the benchmark reproducible and redistributable under the repository licence.

**Evidence.** Brief §6 (15–20 labelled defects, clean reference cases, ≥ 90 % precision/recall); `ifcopenshell.api` authoring documented at docs.ifcopenshell.org.

**Unresolved.** **Requires owner approval** (OPEN-04). Candidate open sample sources to licence-check if a second dataset is wanted: buildingSMART Sample-Test-Files repository; IfcOpenShell test files.

---

## ADR-012 Chat Completions protocol first

**Decision.** Use `POST /v1/chat/completions` for planner, extractor and explainer calls.

**Alternatives.** Responses API (recommended by Meta, supports cross-turn reasoning replay); Messages API (Anthropic-compatible).

**Trade-offs.** Chat Completions is the most broadly compatible with the OpenAI SDK's structured-output helpers (`beta.chat.completions.parse` with Pydantic). Responses may offer better multi-step behaviour; revisit after the MVP if planning quality is the bottleneck.

**Evidence.** dev.meta.ai/docs/protocols, /docs/protocols/chat-completions, /docs/structured-output.

---

## ADR-013 FastAPI background tasks and SSE, no task queue

**Decision.** Review runs execute as in-process background tasks; progress streams via Server-Sent Events.

**Alternatives.** Celery/RQ with Redis — infrastructure the brief discourages; WebSockets — bidirectional capability not needed.

**Trade-offs.** A crash mid-run loses in-memory progress (persisted artefacts survive). Long IFC indexing could block the event loop; mitigation is a `ProcessPoolExecutor` if measured.

**Evidence.** Brief §9; FastAPI 0.162 documentation for `BackgroundTasks` and `StreamingResponse`.

---

## ADR-014 Frontend types generated from Pydantic JSON Schema

**Decision.** Export JSON Schema from `schemas/` with `model_json_schema()` and generate TypeScript types during the frontend build (`json-schema-to-typescript`). Generated files are committed so the frontend builds without Python.

**Alternatives.** Hand-written TS interfaces — drift risk; OpenAPI client generation — heavier, and FastAPI's OpenAPI already embeds the same schemas, so either route is acceptable.

**Trade-offs.** One generation step to maintain; guarantees identical `Finding`/`Requirement`/`Explanation` shapes on both sides (C-07).

**Evidence.** docs.pydantic.dev/latest/concepts/json_schema (`model_json_schema()`).

---

## Open questions register

| ID | Question | Related | Needed by |
|---|---|---|---|
| OQ-01 | Exact That Open Components 3.6 API for GlobalId lookup and highlighting | ADR-007 | Day 1 |
| OQ-02 | Does Meta's strict JSON-schema mode accept nested Pydantic models with enums and optional fields as we define them? | ADR-002, ADR-012 | Day 1 |
| OQ-03 | Benchmark base model choice and licence | ADR-011 | Day 2 |
| OQ-04 | Does the planner add measurable value over the default plan? | ADR-003 | Day 7 evaluation |
| OQ-05 | `ifctester` licence string | ADR-004 | Before publishing licence table |
| OQ-06 | Hackathon rules and submission constraints | — | Before demo recording |
| OQ-07 | API spend authorisation and budget | ADR-002 | Before any live call |

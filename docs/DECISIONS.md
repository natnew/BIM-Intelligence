# Architectural Decisions

**Status:** v0.4, 29 October 2026. Decisions are numbered and immutable once adopted; superseding decisions reference the original.

Each record states the decision, the alternatives considered, the trade-offs, the evidence relied upon, and anything still unresolved. Evidence URLs were verified on 26 October 2026 unless stated otherwise.

| ADR | Title | Status |
|---|---|---|
| [ADR-001](#adr-001-findings-are-deterministic-the-llm-never-asserts-model-facts) | Findings are deterministic; the LLM never asserts model facts | Adopted |
| [ADR-002](#adr-002-meta-model-api-via-the-openai-python-sdk) | Meta Model API via the OpenAI Python SDK | Adopted |
| [ADR-003](#adr-003-single-orchestrator-with-typed-tool-registry) | Single orchestrator with typed tool registry | Adopted |
| [ADR-004](#adr-004-ifcopenshell--ifctester-for-model-access-and-ids-validation) | IfcOpenShell + IfcTester for model access and IDS validation | Adopted |
| [ADR-005](#adr-005-python-312-pinned) | Python 3.12 pinned | Adopted |
| [ADR-006](#adr-006-file-system-session-store-no-database) | File-system session store, no database | Adopted; layout refined by ADR-017 |
| [ADR-007](#adr-007-browser-side-geometry-with-that-open-components) | Browser-side geometry with That Open Components | Adopted; API verified in T-3 |
| [ADR-008](#adr-008-human-confirmation-of-extracted-requirements) | Human confirmation of extracted requirements | Adopted |
| [ADR-009](#adr-009-deterministic-grounding-check-on-every-explanation) | Deterministic grounding check on every explanation | Adopted |
| [ADR-010](#adr-010-standard-mode-model-ids-only) | Standard-mode model ids only | Adopted |
| [ADR-011](#adr-011-synthetic-benchmark-with-defect-injection) | Synthetic benchmark with defect injection | Proposed, approval needed |
| [ADR-012](#adr-012-chat-completions-protocol-first) | Chat Completions protocol first | Adopted, revisit |
| [ADR-013](#adr-013-fastapi-background-tasks-and-sse-no-task-queue) | FastAPI background tasks and SSE, no task queue | Adopted |
| [ADR-014](#adr-014-frontend-types-generated-from-pydantic-json-schema) | Frontend types generated from Pydantic JSON Schema | Adopted |
| [ADR-015](#adr-015-contract-model-immutable-checkspec-content-addressed-finding-per-check-checkresult) | Contract model: immutable `CheckSpec`, content-addressed `Finding`, per-check `CheckResult` | Adopted |
| [ADR-016](#adr-016-ingestion-contract-staged-upload-content-hash-etag-and-identifier-handling) | Ingestion contract: staged upload, content-hash ETag and identifier handling | Adopted; §1 superseded by ADR-017 |
| [ADR-017](#adr-017-content-addressed-model-versions-with-single-pointer-publication) | Content-addressed model versions with single-pointer publication | Adopted |
| [ADR-018](#adr-018-ids-import-establishes-confirmed-requirements-checks-are-hydrated-per-run-reviews-run-under-the-session-lock) | IDS import establishes confirmed requirements; checks are hydrated per run; reviews run under the session lock | Adopted |
| [ADR-019](#adr-019-t-4-native-rule-scope-and-bounded-deterministic-execution) | T-4 native rule scope and bounded deterministic execution | Adopted |
| [ADR-020](#adr-020-t-5-meta-client-spend-ledger-and-human-gates) | T-5 Meta client, spend ledger and human gates | Adopted |
| [ADR-021](#adr-021-bounded-model-federation-is-separate-from-a-session) | Bounded model federation is separate from a session | Adopted; implementation conditional on feasibility |
| [ADR-022](#adr-022-deterministic-geometric-coordination-results) | Deterministic geometric coordination results | Adopted; implementation conditional on feasibility |
| [ADR-023](#adr-023-ui-004-viewer-integrity-and-visual-continuity) | UI-004 viewer integrity and visual continuity | Adopted |
| [ADR-024](#adr-024-muse-spark-remains-an-optional-grounded-interpretation-provider) | Muse Spark remains an optional, grounded interpretation provider | Adopted |
| [ADR-025](#adr-025-hackathon-release-gate-and-demonstration-fallback) | Hackathon release gate and demonstration fallback | Adopted |
| [ADR-026](#adr-026-explicit-ai-review-policy-and-run-provenance) | Explicit AI review policy and run provenance | Adopted |
| [ADR-027](#adr-027-fix-002-muse-spark-structured-review-planning) | FIX-002 Muse Spark structured review planning | Adopted |
| [ADR-028](#adr-028-fix-003-muse-spark-grounded-explanation-allowance-and-token-limit-labelling) | FIX-003 Muse Spark grounded explanation allowance and token-limit labelling | Proposed; awaiting owner acceptance of the FIX-003 implementation |

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

**Status note (28 October 2026).** The on-disk layout of the model artefacts is refined by [ADR-017](#adr-017-content-addressed-model-versions-with-single-pointer-publication): model bytes, index and summary live together under `models/{sha256}/` rather than directly in the session directory. The decision not to use a database stands.

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

**Evidence.** registry.npmjs.org (`@thatopen/components` 3.6.0, MIT, peer `three >= 0.182.0`, `web-ifc >= 0.0.77`); thatopen.github.io/engine_components lists `core/IfcLoader`, `core/FragmentsManager` and `front/Highlighter`.

**Implementation evidence (T-3, 29 October 2026).** On the minimal IFC, browser verification exercised `getLocalIdsByGuids`, `getGuidsByLocalIds` and `Highlighter.highlightByID`; selecting a finding highlighted its wall, and clicking that wall resolved its GlobalId and selected the matching finding. See [the T-3 implementation record](./IMPLEMENTATION_PLAN.md#t-3--interactive-3d-bim-viewer).

**Licence note.** `web-ifc` 0.0.77 is MPL-2.0, not MIT. It is installed unchanged because it is required by the selected viewer stack; this is a documented exception to the repository's permissive-or-LGPL dependency preference. Owner review of distribution obligations remains required before public distribution.

**Out of scope.** Whether the `IDSSpecifications` component could run IDS in-browser as a cross-check remains a P2 curiosity, not planned work.

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

**Implementation note (27 October 2026, ADR-015).** Generated files are committed and checked, not produced "during build": `python scripts/export_schemas.py` writes `frontend/src/api/generated/bim_intelligence.schema.json` (a pytest asserts it is current); `npm run types:generate` writes `types.ts` from it with `json-schema-to-typescript`, and `npm run types:check` fails CI when stale. The frontend build therefore never requires Python.

---

## ADR-015 Contract model: immutable `CheckSpec`, content-addressed `Finding`, per-check `CheckResult`

**Status.** Adopted 27 October 2026 as the owner-approved technical direction for the vertical slice ([BAKEOFF_ARCHITECTURE_REVIEW.md](./BAKEOFF_ARCHITECTURE_REVIEW.md) C-02, C-03, C-05). Implemented in `backend/bim_intelligence/schemas/`.

**Decision.**

1. **`CheckSpec` is immutable and content-addressed.** `CheckSpec.id = sha1(kind | rule_id | rule_version | payload)[:16]`, where the payload is the serialised IDS `<specification>` for `kind="ids"` or the canonical JSON of `params` for `kind="native"`. A `ReviewPlan` item carries only `{check_id, reason}`; the orchestrator resolves the id to the confirmed `CheckSpec` server-side. No code path accepts model-supplied parameters, so a plan can select which confirmed checks run but can never weaken what a check asserts.
2. **A `Requirement` is executable only at its confirmed revision.** `status="confirmed"` requires `confirmed_revision == revision`; an edit bumps `revision`, and `edited` is never executable until the user re-confirms. A requirement with `origin="document"` must carry a verbatim `source` quote.
3. **`Finding` identity and order are canonical.** `Finding.id = sha1(check_id | rule_version | facet_index | sorted element keys)[:16]`, where an element key is its GlobalId or `#express_id` when none exists. `elements` are stored in key order; `findings.json` is serialised with sorted keys, findings ordered by `(check_id, facet_index, first element key, id)`. `Finding` has **no** `created_at` and **no** `run_id`: both would break the byte-identity NFR-01 demands, and the run already lists its findings through `CheckResult.finding_ids`. `method` remains `ids | native` only (ADR-001).
4. **Execution status is separate from defects.** `CheckResult {check_id, requirement_id, status ∈ passed | failed | error | skipped | not_applicable, applicable_count, finding_ids[], diagnostics[]}`; `failed` ⇔ `finding_ids` non-empty, `error` requires a diagnostic, `not_applicable` requires zero applicable elements. `ReviewRun {id, session_id, status ∈ queued | running | completed | partial | failed | interrupted, plan, plan_source ∈ llm | default, check_results[], input_manifest, created_at, finished_at}` is the only record that carries timestamps. An IfcTester exception, a cap hit or a required specification with no applicable entities is a `CheckResult` status, never a finding; this supersedes the `check_error` finding category in [ARCHITECTURE.md §14](./ARCHITECTURE.md).
5. **`ElementRef.global_id` is nullable; `express_id` is always present.** GlobalId remains the viewer join key (ADR-007); `express_id` is diagnostic and the fallback identity for non-`IfcRoot` entities.
6. **Contract models forbid unknown fields** and are exported in serialisation mode, so every field is required in the TypeScript types and an unexpected key (such as `params` on a plan item or `created_at` on a finding) is a validation error, not a silent drop.

**Alternatives.** UUID finding ids with timestamps (not reproducible; NFR-01 untestable); modelling errors and zero applicability as finding categories (pollutes precision and lets skipped checks read as compliance); letting plans pass `params` (schema-valid plans could check weaker conditions than the user confirmed).

**Trade-offs.** Identity is bound to `rule_version`, so a rule change renames every finding it produced — intended, since the finding's meaning changed. Content-addressed ids are not globally unique across models; they are scoped to a session's inputs. `CheckSpec.params` is typed as JSON, which is acceptable because `CheckSpec` is never sent to the model.

**Evidence.** `tests/unit/schemas/` (identity, ordering, invariants, drift); `ifctester` 0.9.0 verified locally: `Specification.failed_entities` is a `set`, `applicable_entities` an ordered list, and each `requirement.failures` entry is a `dict` `{"element": entity, "reason": str}`; `Facet.to_string(clause_type, specification, requirement)` renders the `expected` text (closes Q-03 of the review).

**Unresolved.** Whether the two native rules that overlap IDS facets are retained (review Q-06); how `ids_specification` is re-hydrated into an `ifctester` object in the runner (slice step 7).

---

## ADR-016 Ingestion contract: staged upload, content-hash ETag and identifier handling

**Status.** Adopted 28 October 2026 with the T-1 implementation (`store/`, `bim/`, `api/`). Records assumptions the earlier documents did not cover; the owner may revise any point before T-2 builds on it. **§1 is superseded by [ADR-017](#adr-017-content-addressed-model-versions-with-single-pointer-publication)** (T-1.1), which replaces the four-step publication with a single-pointer transaction; §2–§6 stand.

**Decision.**

1. **Uploads are staged, validated, then published.** `SessionStore.stage_model()` writes the upload to a temporary file inside the session directory while hashing it and enforcing `MAX_IFC_MB`. The staged bytes are parsed and indexed in place; only after indexing succeeds is the file renamed to `model.ifc` and the index and summary written. A malformed or oversized upload therefore never replaces a previously indexed model (ARCHITECTURE §14), and the stored bytes are the client's bytes (C-04, FR-ING-03).
2. **The model hash is the cache key.** `GET /sessions/{sid}/model/file` serves the stored bytes with `ETag` equal to the quoted SHA-256 and honours `If-None-Match` with 304 (C-07). `Session.model_hash` and `ModelSummary.model_hash` carry the same value, so viewer, validator and `InputManifest` always refer to the same bytes.
3. **Identifiers are validated at the boundary, not trusted.** Session ids must be lower-case UUID4 and artefact names come from a fixed allow-list before any path is formed; a malformed session id or GlobalId is 400, an unknown one 404. Client filenames are used only for the extension check.
4. **Malformed GlobalIds do not abort ingestion.** An `IfcRoot` whose `GlobalId` fails the 22-character check is indexed with `ElementRef.global_id = None` and listed in `ModelIndex.malformed_global_ids`; this extends ADR-015 §5 (nullable `global_id`) from non-`IfcRoot` entities to invalid ids. Duplicate GlobalIds keep every record (`duplicate_global_ids`), `by_global_id()` raises, and the API returns 409. Both are inputs to the P1 `identity.unique_global_id` rule (FR-VAL-06) rather than findings in themselves (ADR-001).
5. **Problem types are project-scoped URIs.** `ProblemDetail.type` is `https://github.com/natnew/BIM-Intelligence/problems/<slug>`, mirroring the schema bundle's `$id`; it identifies the problem class for clients without implying a resolvable document.
6. **Property provenance is reproduced, not reinvented.** `ElementRecord.psets` reproduces `ifcopenshell.util.element.get_psets()`'s merge (type first, instance overrides, property by property) and flags each value `inherited` when it comes from the type object; the tests assert equality with IfcOpenShell for every indexed entity.

**Alternatives.** Writing `model.ifc` directly and deleting it on failure (a window in which a session has no model, and a re-upload failure destroys the old one); treating a malformed GlobalId as a 422 (rejects real-world files the validator should be able to report on); `about:blank` problem types (no client-side discrimination).

**Trade-offs.** FastAPI's `UploadFile` spools the whole request body before the handler runs, so the byte cap is enforced after receipt rather than during it; acceptable for a localhost MVP, revisit if `ALLOW_REMOTE` is used. `GET /elements/{globalId}` re-reads `model_index.json` per request; an in-process cache keyed by `model_hash` is the obvious optimisation once the orchestrator needs the index in memory anyway. Index, summary and session record are three separate atomic writes, not one transaction.

**Evidence.** `tests/unit/store/`, `tests/unit/bim/`, `tests/unit/api/` (171 tests, 28 October 2026): fixture SHA-256 equals the stored hash and the `ETag`; AC-01, AC-02, AC-03, AC-04 and AC-11 of the Bakeoff review are covered; a `curl` round trip against `uvicorn` reproduced the test results.

**Unresolved.** Materials and storey elevations are not indexed (FR-ING-02 partial, FR-VAL-05); `409` on model re-upload during an active run (AC-12) awaits the run lifecycle in T-3; whether IFC4X3 should remain accepted once a benchmark exists for it (FR-ING-05 is P3).

---

## ADR-017 Content-addressed model versions with single-pointer publication

**Status.** Adopted 28 October 2026 (T-1.1, hardening review of the T-1 ingestion slice). Supersedes ADR-016 §1 and refines the ADR-006 layout. Implemented in `store/session_store.py`, `store/locking.py`, `bim/ingest.py`, `api/versioning.py`, `api/model.py`, `api/elements.py`, `api/main.py`.

**Context.** The T-1 sequence published an upload in four independent steps — rename `model.ifc`, write `model_index.json`, write `model_summary.json`, update `session.json` — each atomic on its own but not as a set. A failure after the first step left a session whose bytes, index, summary and hash described different models, permanently; a reader between steps saw the same; two concurrent uploads could interleave the steps and finish in a mixed state; and `GET /model/file` read the hash before opening a file that could have been replaced in between. ADR-016 recorded the gap ("three separate atomic writes, not one transaction"). The invariant this record establishes: *a client can never observe a committed session whose IFC file, indexed elements, summary and model hash refer to different model versions.*

**Decision.**

1. **A model version is an immutable, content-addressed directory.** `models/{sha256}/` holds `model.ifc`, `model_index.json` and `model_summary.json`, all built from exactly those bytes. The directory is assembled in a private `models/.staging-{hex}/`, validated (every artefact present, the model file's size equals the bytes written, the summary parses and its `model_hash` equals the upload's SHA-256), fsynced and moved into place with **one rename**. A version directory therefore exists complete or not at all and is never modified afterwards. Re-uploading bytes already present as a complete version discards the staging directory and reuses the existing version; a damaged copy is replaced.
2. **Activation is one atomic write.** `Session.model_hash` is the pointer to the active version; `SessionStore.set_model()` refuses a hash whose directory is incomplete and publishes the pointer with the existing atomic replace of `session.json`. Publication is therefore a two-step transaction (commit directory, swap pointer); a crash between the steps leaves a complete but inactive version, which is harmless and prunable.
3. **Readers resolve the version once.** `SessionStore.active_model()` returns a `ModelVersion`; bytes, index and summary are read only through it, so a single request cannot mix versions. Every model read (`/model/summary`, `/model/file`, `/elements/{globalId}`) carries `ETag` = the quoted SHA-256 of the version it was answered from, and the upload response carries the new version's. Clients may send `If-Match` to pin a sequence of reads to one version; a mismatch is **412 `model-version-mismatch`** naming the active hash. `If-None-Match` on the file keeps its 304 behaviour. `/model/file` streams from the version directory, so its ETag always describes its body.
4. **Publication is serialised by a per-session advisory file lock** (`model.lock`; `fcntl.flock` on POSIX, `msvcrt.locking` on Windows — both conflict between threads of one process and between processes). The lock object is the capability required to stage, commit, activate, prune or discard staging, so none of those can be reached without it. Acquisition does not wait: a second upload while one is in progress is **409 `model-locked`**. Readers never take the lock. The same lock is the seam T-3 holds for the duration of a review run so that an upload mid-run is refused (AC-12), or, equivalently, a run may pin `input_manifest.model_hash` and read `store.model_version(sid, hash)`, which survives replacement.
5. **Superseded versions are retained until pruned.** A re-upload makes a new version active and leaves the previous directory intact, so an in-flight download or a run pinned to the old hash keeps a consistent snapshot. `SessionStore.prune_model_versions(lock, keep=…)` removes complete versions other than the active and kept ones, best-effort per directory; nothing calls it automatically yet (see Trade-offs).
6. **Abandoned staging is recovered, never served.** Staging directories are invisible to readers by construction. `ingest_model` discards any present once it holds the lock (with the lock held they can only be abandoned), and the application lifespan runs `sweep_all_staging()` at startup, skipping sessions whose lock is busy.
7. **Windows sharing violations are retried, not surfaced.** `session.json` is the only file ever replaced in place; its write and its read retry a bounded number of times on `PermissionError`, which is how Windows reports a replace racing a concurrent open. All other files are written once into a directory nobody else reads.

**Alternatives.**
- *Keep the flat layout and order the writes carefully.* No ordering of four independent files yields an atomic set; a crash after any step is a mixed state.
- *A manifest file listing hash-suffixed flat files.* Equivalent to version directories with a worse pruning story.
- *SQLite with a transaction.* Would resolve the atomicity but adds a database for a single pointer swap (ADR-006, C-08).
- *Blocking lock (queue the second upload).* Friendlier for a single user but makes the response time of an upload depend on another and the tests timing-dependent; a non-blocking 409 is explicit and retryable.
- *Prune superseded versions on publish.* Simplest for disk, but breaks any reader or run that resolved the old version; rejected until runs can declare what they pin.
- *Expose `/models/{hash}/…` routes.* Clean version addressing, but a new API surface; `If-Match` is the HTTP-native way to pin and changes no contract.

**Trade-offs.**
- Disk usage grows by one version per distinct re-upload per session until `prune_model_versions` is called. Acceptable for a localhost MVP whose `data/` is disposable; the retention policy (prune on run completion, on session delete, or keep the last *n*) is for T-3 to decide once runs exist (R-PER-05).
- Index and summary are not re-parsed as `ModelIndex`/`ModelSummary` at commit beyond the summary hash check: they were serialised moments earlier from validated objects via canonical JSON and fsynced, and `ingest_model` asserts `index.summary.model_hash` equals the staged hash before writing. A full re-parse would double the memory cost of large indexes for no additional guarantee.
- Reusing an existing version for identical bytes means an index built by an older indexer is served again until `data/` is cleared; the index format is not versioned yet.
- `If-Match` protects a client that asks for protection; a client that ignores ETags can still read version B after loading version A, which is inherent to a multi-request protocol.
- The directory rename and pointer swap are durable on POSIX (directory fsync) and best-effort on Windows, which cannot fsync directories.

**Evidence.** `tests/unit/store/test_session_store.py`, `tests/unit/store/test_locking.py`, `tests/unit/bim/test_ingest_publication.py`, `tests/unit/api/test_model_versioning.py` (51 new tests; `pytest` 334 passed, 28 October 2026, Windows/Python 3.12): failure injected before publication, while writing the index, while writing the summary, during the directory rename and during the pointer swap each leave the session byte-identical or with only a complete inactive version; two concurrent uploads yield one 201 and one 409 with no interleaving; three HTTP reader threads observe no mixed artefact across five replacements and four store-level reader threads across seven; a restart removes abandoned staging; upload response, session, summary, file ETag, body hash and element ETag all agree.

**Unresolved.** Retention policy for superseded versions (T-3); whether to version the index format so a stale reused version is rebuilt. ~~`session.json` is also the future home of `document_hashes`, whose writers must take the same lock or a sibling to avoid a lost update~~ — resolved by [ADR-018](#adr-018-ids-import-establishes-confirmed-requirements-checks-are-hydrated-per-run-reviews-run-under-the-session-lock) §4: every writer of `session.json` takes the model lock.

---

## ADR-018 IDS import establishes confirmed requirements; checks are hydrated per run; reviews run under the session lock

**Status.** Adopted 29 October 2026 with the T-2 implementation (`validation/`, `requirements/`, `orchestration/`, `api/documents.py`, `api/requirements.py`, `api/reviews.py`, `api/findings.py`, store additions). Closes the ADR-015 "unresolved" item on re-hydrating `ids_specification` and the ADR-017 item on `document_hashes` writers. Records assumptions the earlier documents did not cover; the owner may revise any point before T-3 builds on it.

**Context.** T-2 is the first slice that produces a `Finding`. It had to decide how an uploaded IDS becomes executable checks without giving `requirements/` an IfcTester dependency (Bakeoff D-05), how a check is executed from the `CheckSpec` alone rather than from the document it came from (ADR-015 §1), how zero applicability, prohibited specifications, schema mismatches and engine exceptions are reported without inventing findings (ADR-015 §4, C-05), and how a run keeps one model version for its whole duration before the asynchronous run lifecycle exists (ADR-017 §4).

**Decision.**

1. **An imported IDS is a set of confirmed requirements.** `requirements.import_ids_document` creates one `Requirement` per `<specification>` with `origin="ids"`, `status="confirmed"`, `revision=confirmed_revision=1`, `confirmed_by="ids-import"`, and a `source` whose `document_id` is the document's SHA-256, `location` the element's position (`/ids/specifications/specification[n]`) and `quote` the verbatim `name` attribute; an unnamed specification has no `source`. ADR-008's human confirmation applies to requirements *interpreted* from narrative text; an IDS is the project's own machine-readable statement and needs no interpretation (FR-REQ-05). Requirement ids are sequential per session (`REQ-001`, …); re-uploading the same bytes returns the existing requirements (HTTP 200) rather than duplicating them. Only `.ids` is accepted by `POST /documents` in this slice.
2. **The `CheckSpec` payload is the canonical specification element, and it is the only thing a run executes.** `validation.compile_ids` validates the document against IfcTester's bundled IDS 1.0 XSD and stores each `<specification>` in XML Canonical Form (C14N 2.0) with whitespace-only text removed; `rule_version = content_hash(payload)` and `rule_id = "ids:<identifier or name>"`, so identically-specified checks have the same id regardless of file formatting. `validation.hydrate_specification` rebuilds an `ifctester.ids.Specification` from the payload alone through the same XSD, after confirming the payload still hashes to `rule_version`; a mismatch is `CheckSpecIntegrityError`, which the runner reports as `CheckResult.status="error"`. There is no code path from a stored document, a plan or a client to the criteria of a confirmed check (C-02).
3. **Each check runs in its own single-specification `Ids` through `Ids.validate`.** That is IfcTester's public entry point and the one that resets its property caches, so checks cannot leak state into each other and an exception in one is contained. Outcomes map as follows: `ifcVersion` does not list the model's schema → `skipped` (never run, never passed); required or optional specification with no applicable entity → `not_applicable`; prohibited specification → one `prohibited_entity` finding per matching entity, or `passed` when nothing matches; facet failures → `failed` with one finding per (facet, entity), `observed` = IfcTester's reason, `expected` = the facet's rendered requirement text, `category` = `<facet>_requirement`, `severity` = `error`; any exception → `error` with `"<Type>: <message>"` in `diagnostics`. Element references come from the Model Index of the same version so findings, element API and viewer agree.
4. **A review holds the session's model lock from version resolution to publication.** `orchestration.run_review` takes the lock, resolves the active version once, refuses a pinned hash that is not active (412), builds the default plan (every executable requirement, once per `CheckSpec`, in requirement-id order), records the `InputManifest` (model hash, sorted IDS hashes, requirement revisions, rule versions), runs the checks and publishes `runs/{runId}/run.json` + `findings.json` with one rename. An upload, an IDS import or a second review in the meantime is 409 `model-locked`, and nothing can prune the version under the run. The same lock now guards every write to `session.json` (model activation and document registration), so the session record has exactly one writer. The run is synchronous; ADR-013 stands for when runs are long enough to need background execution and SSE.
5. **Run status is derived, never asserted.** `completed` when every check executed; `partial` when any ended in `error`. A session without a model (404) or without an executable requirement (409 `no-executable-checks`) records no run, so an empty run cannot read as compliance.
6. **The IDS XSD is loaded offline.** `ids.xsd` imports the W3C XML and XSD namespaces by URL; with xmlschema's defaults the first load attempts those URLs before using bundled copies. The compiler constructs `XMLSchema(ids.xsd, allow="local")` itself, which makes `xmlschema` a direct, pinned dependency (MIT) and removes the only outbound request the backend would otherwise have made (ARCHITECTURE §13). A test clears the schema cache and compiles under a socket guard.

**Alternatives.**
- *Keep the whole IDS executable and run `Ids.validate` once per document.* Simpler, but a check would then be defined by a file rather than by its `CheckSpec`, errors in one specification would abort the others, and a plan could not select checks individually.
- *Store the raw `<specification>` text.* Formatting changes would rename every finding; C14N with whitespace stripping keeps identity semantic without altering values.
- *Treat zero applicability of a required specification as `failed` (IfcTester's own status).* IfcTester marks the specification failed; a finding needs an element, and "nothing to check" is a coverage fact, not a defect (ADR-015 §4).
- *Run specifications whose `ifcVersion` excludes the model anyway (IfcTester's default).* The IDS author scoped the rule; executing it against another schema can produce confident nonsense in either direction.
- *Pin the run by hash without the lock and rely on retained versions.* Also offered by ADR-017 §4; rejected for now because pruning policy does not exist yet and the lock additionally gives 409 on a concurrent run (AC-12) at no cost.
- *A category per IfcTester reason string.* Would be more descriptive but couples the contract to prose in a non-semver library; the facet type is stable and the reason is preserved verbatim in `observed`.

**Trade-offs.**
- Requirement ids are per-session and sequential, so `findings.json` is byte-identical across sessions only when documents are imported in the same order; within a session it is byte-identical across runs (NFR-01 as tested).
- `rule_versions` in the manifest is keyed by `rule_id`; two specifications sharing a name but differing in content collapse to one key there, while `requirement_revisions` and `ids_hashes` still identify the inputs exactly.
- Holding the lock for a synchronous run blocks uploads for its duration — seconds on the fixture; the background-task design is the remedy for large models.
- `severity` is `error` for every IDS finding; IDS 1.0 has no severity concept and inventing one from cardinality would be speculative.
- IfcTester 0.9.0 recognises only lower-case `true`/`false` for boolean `simpleValue`s; `TRUE` happens to work (`bool("TRUE")`) and `FALSE` does not. Authors of IDS files for this system should write booleans in lower case; the fixture is unaffected because it only tests `TRUE`. Recorded in RISKS.md.

**Evidence.** `tests/unit/validation/` (32), `tests/unit/requirements/` (9), `tests/unit/orchestration/` (19), `tests/unit/store/test_session_store_runs.py` (14), `tests/unit/api/test_documents.py`, `test_reviews.py`, `test_cors.py` (31), `tests/unit/schemas/test_document_import.py` (2); `pytest` 461 passed, `ruff`, `mypy --strict` on `schemas/`, `validation/`, `orchestration/` clean, 29 October 2026, Windows/Python 3.12.12, ifcopenshell 0.9.0.post1, ifctester 0.9.0, xmlschema 4.3.2. On the committed fixture: two confirmed requirements, two `failed` check results, exactly two findings (W-002 `0QWMtUzsnUUONCUGc8Sqsa` for the FireRating specification, W-003 `2qvnbd6oPPKR1ac5HegGTJ` for the classification specification), W-003 outside the first specification's two applicable entities, findings equal to `ifctester.reporter.Json` element for element, three consecutive HTTP runs with identical `findings.json` SHA-256, model version directory byte-identical before and after, an upload attempted from inside a run refused with 409, and no socket opened during compile, hydrate or run.

**Unresolved.** When the review becomes asynchronous (T-3), whether the lock is held for the run or replaced by hash pinning plus a retention rule; whether `POST /documents` should accept a batch; how a later `PATCH /requirements/{rid}` edit of an IDS-origin requirement re-compiles its payload (the current contract makes it `edited`, non-executable, until re-confirmed).

## ADR-019 — T-4 native rule scope and bounded deterministic execution

**Status:** Adopted 29 October 2026 with the T-4 implementation.

**Context.** T-2 already executes IDS 1.0 checks as confirmed, immutable `CheckSpec`s. T-4 must add the minimum P0 native capability without creating duplicate checks for requirements IDS already expresses, and must ensure execution limits or recoverable failures cannot be reported as full coverage.

**Decision.** This ADR supersedes ADR-018's earlier all-checks-execute plan description and its run-status condition where execution caps and `not_applicable` coverage are concerned; model locking, input manifests and atomic publication remain unchanged.

1. Ship only `classification.consistent_by_type` v1.0.0 as a native P0 rule. It compares effective `(system, identification-or-name)` classification references on a classified type and each occurrence, emits a deterministic finding for a mismatch, and reports `not_applicable` when no classified type occurrence exists. Its immutable `CheckSpec` is parameter-free; invalid parameters, rule ids or versions are execution errors.
2. Keep IDS 1.0 as the implementation for required-property checks, expressible naming patterns, classification presence and classification-system checks. Do not register native duplicates for those checks. Do not implement P1/P2 rules in T-4.
3. Make the native rule an explicit built-in confirmed requirement through the classification-consistency endpoint. Repeated confirmation is idempotent; the model-version lock protects requirement persistence from an active review.
4. Build the default plan from confirmed executable requirements, deduplicate by immutable check id and preserve requirement order. Apply `MAX_PLAN_CHECKS` and `MAX_TOOL_CALLS_PER_RUN`; report unexecuted checks as `skipped`, continue after a per-check `error`, and mark any run with `error`, `skipped` or `not_applicable` results `partial`.

**Alternatives.** Implement overlapping native property/classification-presence/naming rules; rejected because IDS 1.0 already expresses them and duplicate execution would create conflicting or repeated findings. Automatically add the native rule to every session; rejected because this is an additional confirmed check and should be explicitly selected. Stop the review after a check error or cap; rejected because later checks should still execute and every omitted check should remain visible in coverage.

**Trade-offs.** The current native registry contains one rule, not a general-purpose plugin system. Its parameter-free contract avoids exposing unverified configuration that could weaken a confirmed requirement. A `partial` run is intentionally conservative: `not_applicable` is not a defect, but it does not demonstrate coverage. Benchmark precision/recall and clean-control results are not available until T-6.

**Evidence.** Native rule positive, mismatch, applicability and invalid-spec tests; explicit confirmation API tests; bounded-plan/error tests; and the LLM-off fixture scenario in `tests/unit/validation/test_native_rules.py`, `tests/unit/api/test_native_requirements.py`, `tests/unit/orchestration/test_review_runner.py` and `tests/scenario/test_deterministic_review.py`. Exact commands and results are recorded in [T-4](./IMPLEMENTATION_PLAN.md#t-4--end-to-end-deterministic-review-workflow).

---

## ADR-020 T-5 Meta client, spend ledger and human gates

**Status: Adopted.**

**Decision.** Keep the T-5 integration behind the existing process boundary and OpenAI SDK. `LLMClient.complete` returns a Pydantic-validated response and typed usage. `LiveClient` alone can perform network requests; Fake, Recording and Replay are offline-capable, and Replay/Off never fall back to Live. The default mode is `off`. Live requires a configured `MODEL_API_KEY`, Standard-mode model id and the additional `ALLOW_LIVE_LLM=true` opt-in. The endpoint is restricted to `https://api.meta.ai/v1`; retries default to zero.

Before each live call, reserve application budget using configured per-million token rates, estimated input and the full output cap. Persist reservations, usage, actual calculated costs and outcomes in a lock-protected JSON ledger under `DATA_DIR/llm/`. Unknown usage is charged at the reserved amount; unreadable ledger state or unavailable locks disable Live. Defaults are 8,000 estimated input tokens, 500 output tokens, two live calls per review, USD 0.10 per call and per review, and USD 5.00 cumulative project allowance. These are local application safeguards, not provider-enforced account caps or guarantees against external spending.

**Requirement workflow.** Narrative Markdown/TXT candidates preserve a source hash, paragraph id and verbatim quote; the quote, paragraph, hash and candidate identity are checked again on confirmation. The model may only map a candidate to an already confirmed immutable `CheckSpec`. Human confirmation is mandatory. T-5 does not generate or compile new IDS criteria.

**Explanation workflow.** An AI explanation is a separate response contract, grounded against the deterministic finding, matching requirement revision and model index. Every citation binds finding, GlobalId, requirement, rule, expected and observed values. Multi-element findings and any grounding failure use a deterministic template. Explanation output never enters `findings.json`.

**Alternatives.** Provider-side billing alerts were rejected as hard limits because they are not reliable spending caps. Automatically enabling Live when a key is present was rejected because it creates an implicit cost path. Persisting prompts in recordings was rejected because it retains private project text unnecessarily. Letting the model create CheckSpecs was rejected because free-form output could invent validation semantics.

**Trade-offs and remaining risks.** A byte-based input estimate plus message overhead is conservative for ordinary UTF-8 prompts but is not provider tokenisation. Provider usage is reconciled after a request; if returned usage exceeds the reservation, the actual amount is recorded and further requests are blocked, but the provider may already have billed more than the reservation. Deleting the local ledger or spending outside this application is outside the safeguard. Meta endpoint, model access and structured-output compatibility have not been verified by a live call; each live test requires explicit owner approval.

**Evidence.** Offline tests cover Fake/Replay, schema validation, quote verification, plan filtering, grounding fallback, API routes, timeout/error sanitisation, reservation persistence and concurrent accounting. Muse Spark Standard price defaults are configurable and sourced from [Meta's published pricing](https://dev.meta.ai/docs/pricing-rate-limits). The exact smoke-test plan and offline validation results are recorded in [T-5](./IMPLEMENTATION_PLAN.md#t-5--meta-muse-spark-integration); no API usage has been measured.

---

## Resolved questions

| ID | Question | Resolution |
|---|---|---|
| OQ-01 | Exact That Open Components 3.6 API for GlobalId lookup and highlighting | Resolved in T-3 by browser verification of GlobalId lookup and `Highlighter.highlightByID`; see [ADR-007](#adr-007-browser-side-geometry-with-that-open-components) and the [T-3 evidence](./IMPLEMENTATION_PLAN.md#t-3--interactive-3d-bim-viewer). |

## Open questions register

| ID | Question | Related | Needed by |
|---|---|---|---|
| OQ-02 | Does Meta accept the FIX-002 non-strict JSON Schema response format for live Muse Spark review planning? | ADR-002, ADR-012, ADR-027 | VERIFY-009 |
| OQ-08 | Does Muse Spark return a complete, schema-valid and grounded explanation within the FIX-003 2,000-token allowance at low reasoning effort? The one live VERIFY-009 explanation exhausted the prior 500-token allowance on reasoning tokens alone. | ADR-009, ADR-027, ADR-028 | Owner-approved live explanation retest |
| OQ-03 | Benchmark base model choice and licence | ADR-011 | Day 2 |
| OQ-04 | Does the planner add measurable value over the default plan? | ADR-003 | Day 7 evaluation |
| OQ-05 | `ifctester` licence string | ADR-004 | Before publishing licence table |
| OQ-06 | Hackathon rules and submission constraints | — | Before demo recording |
| OQ-07 | API spend authorisation and budget | ADR-002 | Before any live call |

---

## ADR-021 Bounded model federation is separate from a session

**Status: Adopted 1 November 2026; implementation is conditional on the feasibility gate in
[FINAL_48_HOUR_PLAN.md](./FINAL_48_HOUR_PLAN.md).**

**Decision.** Preserve the existing `Session` contract: one session has at most one active IFC
model version. Do not overload a session or replace its uploaded IFC to represent another
discipline. Only after a bounded feasibility check succeeds may the application add a separate
`ModelSet`/coordination-set manifest referencing immutable IFC versions. The initial demonstration
is exactly two model sources and one explicitly selected A/B pair.

Each manifest member records a stable member identity, source session, immutable model SHA-256,
explicit discipline label, source coordinate-frame description, and relative or absolute placement
metadata. The set declares one common coordinate frame, including its units and the evidence used
to validate placement. Unknown, unsupported, or ambiguous alignment is rejected; it is never
assumed from model extents, filenames, or discipline names.

Every federated element reference is scoped by model-member identity and immutable model hash, then
by `GlobalId` when available. A documented fallback is `(ifc_type, express_id)` within that model
hash only. `GlobalId` alone is never a federation key. Model bytes remain read-only and existing
per-file upload limits apply; the demo also has an explicit two-model and aggregate-size cap.
Private or third-party source files require the provenance, rights, storage, and transmission
approvals in `AGENTS.md`; local availability is not permission to inspect, transmit, or publish.

**Alternatives.** Expanding `Session` to contain several models would break its current contract
and version guards. Replacing the active IFC would lose the first discipline's version identity.
Guessing alignment from geometry would create plausible but unverified intersections.

**Trade-offs.** A separate manifest and read-only references add a narrow coordination boundary.
They do not provide general project management, model authoring, or enterprise federation. This
decision does not approve an API schema or implementation before feasibility is demonstrated.

**Evidence.** `backend/bim_intelligence/schemas/sessions.py` defines one `model_hash` per
`Session`; `backend/bim_intelligence/bim/ingest.py` atomically activates one immutable model
version. No model-set contract is implemented.

**Unresolved.** Whether the currently installed geometry stack can load and compare the selected
IFC pair in a verified common frame within the deadline; whether the preferred external candidate
has redistribution rights.

---

## ADR-022 Deterministic geometric coordination results

**Status: Adopted 1 November 2026; implementation is conditional on ADR-021 and a successful
feasibility gate.**

**Decision.** A coordination run may use only an installed, version-verified IfcOpenShell/IfcClash
capability or another deterministic geometric capability whose provenance, API and behaviour have
been verified before implementation. At the checked-out baseline, IfcOpenShell 0.9.0.post1 and
IfcTester 0.9.0 are installed, but no `ifcclash` distribution or import is present. No package is
to be installed speculatively; a dependency change requires a separately approved dependency and
licence decision.

The first run evaluates one declared A/B model pair only after both immutable hashes and their
common coordinate frame have been validated. Each run records its run identity, both model hashes
and member identities, algorithm and version, explicit distance tolerance and units, exclusions,
placement assumptions, and tested IFC entity scope. There is no implicit tolerance or alignment
default; missing or unsupported inputs produce a visible non-analysis/error state.

Keep three concepts separate: raw computed geometric intersections, deterministic groups of those
intersections, and coordination issues assessed by a human. A geometric intersection is not
automatically an actionable defect. Coordination output is not written as an information-quality
`Finding`, does not change IDS/native criteria, and does not become an AI-authored model fact. AI
must not create clash coordinates, intersections, counts, or issue states.

The externally visible run state distinguishes `unavailable`, `not_analysed`, `zero_clashes`,
`analysis_error`, and `results_available`. Counts are emitted only from a successfully completed
run; a zero is never substituted for unavailable or failed analysis. Repeated inputs and settings
must produce stable results within the verified algorithm's stated limits.

**Alternatives.** Treat every intersection as a defect (misleading); use LLM-generated
coordinates (unverifiable); or reuse `Finding` for clashes (conflates separate result semantics).

**Trade-offs.** This is a small geometric coordination demonstration, not enterprise clash
management, issue assignment, lifecycle management, federation-wide search, or code compliance.
The capability and entity scope remain unverified and therefore cannot be promised or recorded in
a demonstration until tested.

**Evidence.** The current repository contains deterministic IDS/native validation and a synthetic
information-quality benchmark, but no clash implementation or clash results. The local Python
environment does not contain IfcClash.

**Unresolved.** Feasible engine and tested IFC entity scope; grouping rule; suitable tolerance and
units; approved sample model and redistribution rights.

---

## ADR-023 UI-004 viewer integrity and visual continuity

**Status: Adopted 1 November 2026; implementation remains subject to the T-7 UI change-control
process.**

**Decision.** Retain the current BIM Intelligence application shell, owner-approved architectural
colour palette and typography, Project Home, and working single-IFC workflow. A bounded Clash
Matrix and 3D Investigation, if the coordination gate passes, are modes within this application;
they are not a second product or a redesign.

The viewer/application selection state must remain coherent. Selection styling is neutral and
visibly distinct from deterministic issue severity/highlighting. Evidence inspection must not
replace or unexpectedly reset the desktop viewport. Provide Fit All, Reset View and Focus
Selection only where the installed viewer supports them and they pass regression tests; never
display inert controls. Model loading is described by observed states, without invented percentage
progress.

**Alternatives.** A separate coordination application would duplicate the shell and fragment
review context. Severity-coloured selection would conflate user focus with verified defect status.
Fabricated progress or unsupported camera controls would misrepresent behaviour.

**Trade-offs.** Camera recovery and coordinated multi-model selection may require a separately
verified viewer API. Existing selection, finding identity, viewer lifecycle, version guards,
read-only model handling, accessibility and palette take precedence over adding controls.

**Evidence.** UI-003 is implemented on `main` and its browser walkthrough is recorded in
`docs/UI_CHANGELOG.md`. The current viewer exposes orbit, pan, zoom and selection; fit/reset/focus
controls are explicitly deferred.

**Unresolved.** Which camera operations the installed viewer version safely exposes for a federated
scene; final keyboard and accessibility acceptance for any new controls.

---

## ADR-024 Muse Spark remains an optional, grounded interpretation provider

**Status: Adopted 1 November 2026.**

**Decision.** Retain Meta Muse Spark via the existing Meta Model API client as the intended provider
for bounded objective planning and grounded finding explanations. Reuse the existing planner,
explanation path, model-output validation, grounding check, budget ledger, and deterministic
fallback. The first user-facing integration may expose a bounded review objective and/or a
grounded explanation; it must show the actual `ReviewRun.plan_source`, the actual explanation
`source`, and whether the deterministic fallback was used.

Verified model evidence and deterministic `Finding` records remain separate from AI interpretation.
The model cannot create or edit a `Finding`, coordinates, results, or approved check criteria.
`LLM_MODE=off` remains the default. Live API verification or inference requires explicit owner
approval for that session and secured backend credentials; no live call is authorised by this ADR
or by the current documentation task.

**Alternatives.** Claiming a live AI result from a default/offline plan, presenting a deterministic
template as AI, or allowing AI to change validation semantics would misstate provenance and breach
the finding contract.

**Trade-offs.** Offline deterministic review remains demonstrable when the provider is unavailable.
It is not a substitute for proving live API compatibility or a user-facing Meta-assisted workflow.

**Evidence.** ADR-020 and the T-5 register record offline Fake/Replay tests, default-off behaviour,
grounded explanations and spend safeguards. The frontend currently shows a fixed note that the AI
explanation is not connected; live API compatibility remains unverified.

**Unresolved.** Live endpoint compatibility, owner-approved credentials/spend, and the final
user-facing integration.

---

## ADR-025 Hackathon release gate and demonstration fallback

**Status: Adopted 1 November 2026.**

**Decision.** The internal completion target is 3 November 2026; the hackathon submission date
remains 4 November 2026. A functioning three-minute video is mandatory for the delivery plan.
Federation and clash detection are an optional, conditional demonstration, with a no-later-than
2 November 2026 12:00 UTC go/no-go cutoff. Include coordination only if every technical, evidence,
rights, privacy, regression and recording condition in `docs/FINAL_48_HOUR_PLAN.md` passes.

If that gate fails, do not show or narrate unverified coordination. Keep the primary demonstration
on the working deterministic IDS/native review, with the Meta-assisted path included only if its
frontend integration and the required owner-authorised live/replay evidence are real and labelled
accurately. If the Meta gate also fails, disclose that limitation; do not imply that the
deterministic-only recording is Meta-assisted or that hackathon eligibility is established.
Unverified features are omitted from the recording. Check public-repository and third-party asset
rights before submission.

**Alternatives.** Stretch coordination regardless of evidence, or represent a planned feature as
working, would jeopardise a credible submission. Removing the verified deterministic workflow to
make time for optional scope is rejected.

**Trade-offs.** The plan protects the known working workflow and allows the coordination branch to
stop without blocking it. Official rules and eligibility remain subject to owner verification.

**Evidence.** The main branch contains the single-model review workflow, offline-tested T-5
components and recorded T-6 synthetic benchmark results. It does not contain a clash engine,
browser AI integration or a complete release demonstration.

**Unresolved.** The official event rules/eligibility and owner approval for any live Meta call,
external model use, recording, and final submission.

---

## ADR-026 Explicit AI review policy and run provenance

**Status: Adopted 3 November 2026.**

**Context.** ADR-024 keeps Muse optional and Off by default. Once the review API accepts a plain-
language objective, silently running the deterministic default after an unavailable or rejected AI
plan can misrepresent whether the user's requested review was performed. A persisted run also needs
to distinguish Live, Replay and Off planning without inferring the mode from current configuration.
User-selected checks must remain bound to the exact confirmed requirement revision from which they
were selected.

**Decision.** Preserve ADR-024's development defaults and optional-provider architecture, while
making objective intent explicit:

- An objective requires an accepted AI plan unless the request explicitly sets `ai_required=false`.
- `continue_without_ai=true` is a distinct, explicit choice to skip planning and run the
  deterministic plan. Strict planning failures return typed errors and publish neither a run nor
  findings. Unsupported scope is never replaced with a broader default plan.
- Optional AI failures may use the deterministic plan, with the failure reason persisted in run
  provenance. Explicit continuation is recorded separately from an attempted-but-rejected plan.
- Optional selected checks are identified by `check_id`, `requirement_id` and
  `requirement_revision`; stale, unconfirmed or mismatched selections are rejected before
  execution. Both planning and deterministic continuation are restricted to that scope.
- Each new run records whether planning was requested, whether a provider request was attempted,
  the actual client mode and model when available, the planning outcome, fallback reason, selected
  check ids and executed check ids. Historical runs without this field remain readable and are not
  assigned retrospective provenance. Strict failures return equivalent safe metadata in a typed
  problem response.
- `BIMI_ENVIRONMENT=production` is an explicit configuration profile requiring the approved
  Standard-mode `muse-spark-1.3` Live configuration and rejecting contributor mode. Development
  remains Off by default.

This configuration profile is not a public-deployment approval or security claim. The application
still lacks authentication; a production profile must not be interpreted as permission to expose
project data publicly.

**Alternatives.** Keep implicit deterministic fallback for every objective; infer provenance from
the current global mode; or pin selection only to a check id. Each loses user intent, historical
truthfulness or revision-level traceability.

**Trade-offs.** Strict objective requests can now fail visibly when AI is unavailable. The API
supports explicit deterministic continuation, but the existing UI does not yet expose a dedicated
continuation control. The caller must handle the typed error or send the explicit continuation
field; UI work remains outside this task's approved file scope.

**Evidence.** T-5.1 offline tests cover strict failure without run publication, budget refusal before
a provider request, rejected Live plan metadata, selected-check revision validation, Replay
provenance retrieval and historical-run compatibility. These tests use stubs and make no live Meta
request.

**Unresolved.** User-approved Live planner evidence, UI exposure of explicit continuation, and
authentication and access controls before any public deployment.

---

## ADR-027 FIX-002 Muse Spark structured review planning

**Status: Adopted 3 November 2026 under explicit owner approval for FIX-002.**

**Context.** The owner-reported FIX-001 investigation found five Muse Spark 1.3 planning requests
with usage but no visible completion; each consumed the full 500-token output allowance. The
ledger recorded `missing_output`, and JSON parsing, Pydantic validation and plan-registry checks
were not reached. The observed failure was therefore not a schema failure. Reasoning-token
exhaustion is the leading explanation, but remains unconfirmed because the original requests did
not capture finish reason or reasoning-token usage. The private evidence remains in its owner-
managed location and was not inspected or copied for this change.

**Decision.** Give objective review planning a separate maximum completion allowance of 2,000
tokens and send `reasoning_effort="low"`; retain the 500-token ceiling for other workflows. Use
Chat Completions `max_completion_tokens`, which Meta documents as supported while retaining
`max_tokens` only as a deprecated alias. Meta documents `low` reasoning effort and explicitly
states that `"none"` is unsupported for Muse Spark. Request a JSON Schema response format derived
from the Pydantic response model, with the plan's `checks` field required; omit the optional
`strict` flag and continue to validate locally, including confirmed-check, duplicate, scope and
execution-cap rules. Use the versioned `planner.v2.md` contract.

Record only safe response metadata in the budget ledger: actual model id, response id, finish
reason, total completion tokens (`output_tokens`), reasoning tokens when present, visible-content
presence and outcome. Do not retain prompts, response text, refusal text or credentials. Treat
truncation and completion-limit exhaustion as `token_limit`; reserve `invalid_output` for content
that is present but fails JSON/Pydantic validation. Missing output below the limit, refusals and
content-filter outcomes are distinct ledger outcomes with sanitised exceptions.

Keep application budgets unchanged: 8,000 estimated input tokens; USD 0.10 per call and per
review; two calls per review; and USD 5.00 project allowance. At Standard rates of USD 1.25/M
input and USD 4.25/M output, the uncached 8,000/2,000 worst-case reservation is USD 0.01850,
within the existing per-call ceiling. Reservations still occur before the provider request and
the ledger remains fail-closed.

**Alternatives.** Raising the shared 500-token cap would also change extraction and explanation
workflows; rejected. Disabling reasoning would be rejected by Muse Spark. Enabling strict
provider-side schema mode without compatibility evidence would be speculative; strict mode is
omitted. Reclassifying missing content as schema-invalid would repeat the observed diagnostic
error; rejected.

**Trade-offs.** The planning allowance increases the maximum reserved amount for a planning
request, but remains below the unchanged USD 0.10 call/review budgets. The local stub verifies
request construction and deterministic error classification only. Provider acceptance of this
JSON Schema and live planning relevance remain unverified and require the separately approved
VERIFY-009 live gate. No live request is authorised by this decision.

**Evidence.** FIX-001 owner-reported observations; offline LiveClient transport tests; Meta's
[Chat Completions parameter reference](https://dev.meta.ai/docs/protocols/chat-completions);
and the FIX-002 offline verification record in [T-5](./IMPLEMENTATION_PLAN.md#t-5--meta-muse-spark-integration)
and [EVALUATION §8](./EVALUATION.md#fix-002-offline-review-planning-correction-3-november-2026).

## ADR-028 FIX-003 Muse Spark grounded explanation allowance and token-limit labelling

**Status: Proposed 3 November 2026; awaiting owner acceptance of the FIX-003 implementation.**

**Context.** The owner-approved VERIFY-009 live session (candidate
`b95dadbe2d0475aa3c107227a9d0af2cae2c2c47`) accepted a Muse Spark 1.3 review plan on the first
request, but the single authorised explanation request returned `finish_reason=length` with 500
completion tokens, of which 498 were reasoning tokens, and no visible content. The ledger recorded
`token_limit`; explanation JSON validation and deterministic grounding were never reached. The
application returned a correctly labelled deterministic template, but mapped the failure to
`budget_limit`, and the inspector described it as an exhausted spend or call limit although no
monetary or call limit had been reached. Explanation requests were also sent without the
`reasoning_effort="low"` setting that FIX-002 adopted for planning.

**Decision.** Give finding explanations their own completion allowance,
`LLM_MAX_EXPLANATION_OUTPUT_TOKENS` (default and ceiling 2,000), and send explanation requests at
`reasoning_effort="low"`, matching the verified planning request shape. Other workflows keep the
500-token default. Retain the existing JSON Schema response format, the `_ExplanationDraft`
contract, local Pydantic validation and the deterministic `_verify_grounding` checks unchanged;
the explanation prompt `explanation.v1.md` is unchanged because no evidence shows the prompt
caused the failure.

Separate the explanation fallback vocabulary: `token_limit` is raised when the provider exhausts
the completion allowance (`TokenLimitError`), and `budget_limit` is reserved for application
spending or call limits (`BudgetLimitError`). The frontend states the token-limit case as "The AI
explanation reached its completion-token limit. The verified finding remains available, and a
deterministic explanation is shown instead." Neither case is described as a provider outage,
schema error or insufficient financial budget.

Keep every monetary limit unchanged. At configured Standard rates the uncached 8,000-input /
2,000-completion explanation reservation is USD 0.01850, within the USD 0.10 per-call limit; a
planning and an explanation reservation together are USD 0.03700, within the USD 0.10 per-review
limit and the USD 5.00 project allowance. The two-call review cap and pre-request reservation
remain in force, and the ledger's per-request output ceiling is the maximum of the three configured
allowances so a reservation is never rejected for an allowance the client permits.

**Alternatives.** Raising the shared 500-token cap would also change extraction; rejected, as in
ADR-027. Keeping `budget_limit` as a combined category would continue to misreport the observed
failure to users; rejected. Reducing citation requirements so that shorter output passes would
weaken ADR-009 grounding; rejected. Revising the prompt before measuring the effect of the
allowance would add an unverified variable; deferred until evidence requires it.

**Trade-offs.** A planning plus explanation review may now reserve up to USD 0.03700 instead of
USD 0.030625, still within unchanged limits. Offline stub tests verify the request body,
classification and labels only; whether Muse Spark completes a grounded explanation within 2,000
tokens at low reasoning effort is OQ-08 and requires a separately approved live retest. No live
request is authorised by this decision.

**Evidence.** The sanitised VERIFY-009 live result recorded in
[T-5](./IMPLEMENTATION_PLAN.md#t-5--meta-muse-spark-integration); offline `LiveClient`
stub-transport and API regression tests named for VERIFY-009 and FIX-003; and the FIX-003 offline
verification record in [EVALUATION §8](./EVALUATION.md#fix-003-offline-grounded-explanation-correction-3-november-2026).

## Implementation outcomes — 1 November 2026

These observations supplement, and do not change, the adopted decisions above.

- **ADR-023:** UI-004A was merged into `main` in PR #28 at
  `cf06328c874258efe8a49d0afa291d9aef278928`. The synthetic fixture browser checks exercised
  Fit model, Reset view, Focus selected and bidirectional finding/element selection. Cross-severity
  viewer styling and a complete accessibility audit remain open.
- **ADR-024:** The owner reported one approved basic `muse-spark-1.3` structured-output smoke;
  its original request recording and source commit were not provided. This does not verify a live
  BIM planner or explanation. On the release baseline, an offline objective request produced the
  deterministic default plan and an explanation request returned an `ai_disabled` deterministic
  template; neither is an AI response. The browser objective and explanation controls remain
  unimplemented.
- **ADR-025:** The separate FED-001 harness produced synthetic geometric feasibility evidence,
  but no coordination API, matrix or federated viewer is integrated. The repository is private,
  the video and official submission fields have not been verified, and release remains no-go.
  Further live calls, publication and submission still require their existing owner gates.

The precise test commands, baseline and limitations are recorded in
[EVALUATION.md](./EVALUATION.md#release-001-offline-verification--1-november-2026) and
[DEMO_PLAN.md](./DEMO_PLAN.md).

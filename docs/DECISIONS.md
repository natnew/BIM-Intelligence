# Architectural Decisions

This file records the main architectural decisions behind BIM Intelligence. Each record states the
decision, the alternatives considered, the trade-offs and the evidence it relies on, and lists
anything still unresolved. Decisions are numbered and are not edited once adopted; a later record
supersedes an earlier one and says so.

| ADR | Title | Status |
|---|---|---|
| [ADR-001](#adr-001-findings-are-deterministic-the-llm-never-asserts-model-facts) | Findings are deterministic; the LLM never asserts model facts | Adopted |
| [ADR-002](#adr-002-meta-model-api-via-the-openai-python-sdk) | Meta Model API via the OpenAI Python SDK | Adopted |
| [ADR-003](#adr-003-single-orchestrator-with-typed-tool-registry) | Single orchestrator with typed tool registry | Adopted |
| [ADR-004](#adr-004-ifcopenshell--ifctester-for-model-access-and-ids-validation) | IfcOpenShell + IfcTester for model access and IDS validation | Adopted |
| [ADR-005](#adr-005-python-310312-supported-developed-on-312) | Python 3.10–3.12 supported, developed on 3.12 | Adopted |
| [ADR-006](#adr-006-file-system-session-store-no-database) | File-system session store, no database | Adopted; layout refined by ADR-017 |
| [ADR-007](#adr-007-browser-side-geometry-with-that-open-components) | Browser-side geometry with That Open Components | Adopted |
| [ADR-008](#adr-008-human-confirmation-of-extracted-requirements) | Human confirmation of extracted requirements | Adopted |
| [ADR-009](#adr-009-deterministic-grounding-check-on-every-explanation) | Deterministic grounding check on every explanation | Adopted |
| [ADR-010](#adr-010-standard-mode-model-ids-only) | Standard-mode model ids only | Adopted |
| [ADR-011](#adr-011-synthetic-benchmark-with-defect-injection) | Synthetic benchmark with defect injection | Adopted |
| [ADR-012](#adr-012-chat-completions-protocol-first) | Chat Completions protocol first | Adopted |
| [ADR-013](#adr-013-synchronous-in-process-review-runs-no-task-queue) | Synchronous in-process review runs, no task queue | Adopted |
| [ADR-014](#adr-014-frontend-types-generated-from-pydantic-json-schema) | Frontend types generated from Pydantic JSON Schema | Adopted |
| [ADR-015](#adr-015-contract-model-immutable-checkspec-content-addressed-finding-per-check-checkresult) | Contract model: immutable `CheckSpec`, content-addressed `Finding`, per-check `CheckResult` | Adopted |
| [ADR-016](#adr-016-ingestion-contract-staged-upload-content-hash-etag-and-identifier-handling) | Ingestion contract: staged upload, content-hash ETag and identifier handling | Adopted; §1 superseded by ADR-017 |
| [ADR-017](#adr-017-content-addressed-model-versions-with-single-pointer-publication) | Content-addressed model versions with single-pointer publication | Adopted |
| [ADR-018](#adr-018-ids-import-establishes-confirmed-requirements-checks-are-hydrated-per-run-reviews-run-under-the-session-lock) | IDS import establishes confirmed requirements; checks are hydrated per run; reviews run under the session lock | Adopted |
| [ADR-019](#adr-019-native-rule-scope-and-bounded-deterministic-execution) | Native rule scope and bounded deterministic execution | Adopted |
| [ADR-020](#adr-020-meta-client-spend-ledger-and-live-mode-safeguards) | Meta client, spend ledger and Live-mode safeguards | Adopted |
| [ADR-021](#adr-021-bounded-model-federation-is-separate-from-a-session) | Bounded model federation is separate from a session | Adopted; not implemented |
| [ADR-022](#adr-022-deterministic-geometric-coordination-results) | Deterministic geometric coordination results | Adopted; not implemented |
| [ADR-023](#adr-023-viewer-integrity-and-visual-continuity) | Viewer integrity and visual continuity | Adopted |
| [ADR-024](#adr-024-muse-spark-remains-an-optional-grounded-interpretation-provider) | Muse Spark remains an optional, grounded interpretation provider | Adopted |
| [ADR-025](#adr-025-show-only-verified-capabilities) | Show only verified capabilities | Adopted |
| [ADR-026](#adr-026-explicit-ai-review-policy-and-run-provenance) | Explicit AI review policy and run provenance | Adopted |
| [ADR-027](#adr-027-structured-review-planning-request) | Structured review-planning request | Adopted |
| [ADR-028](#adr-028-explanation-completion-allowance-and-token-limit-labelling) | Explanation completion allowance and token-limit labelling | Adopted |
| [ADR-029](#adr-029-live-structured-output-evidence-and-retained-validation) | Live structured-output evidence and retained validation | Adopted |

---

## ADR-001 Findings are deterministic; the LLM never asserts model facts

**Decision.** A `Finding` may only be created by IfcTester (IDS) or a registered native Python rule.
The `Finding.method` enumeration has no `llm` member. The language model plans, proposes
requirements and explains; its outputs are validated by schema and, for explanations, by a
grounding check against the evidence.

**Alternatives.**
1. The model inspects model data directly and reports defects: fastest to prototype, but findings
   would be unverifiable and precision unmeasurable.
2. The model proposes findings that a deterministic step then verifies: adds a round trip per
   finding, and the verification would re-implement the rules anyway.

**Trade-offs.** Coverage is bounded by the rule library; the model cannot "notice" a defect type
with no rule. This is accepted: findings must be measurable and verifiable, and the rule library
can grow.

**Unresolved.** None.

---

## ADR-002 Meta Model API via the OpenAI Python SDK

**Decision.** Call Meta Muse models through the OpenAI Python SDK configured with
`base_url="https://api.meta.ai/v1"` and `api_key=MODEL_API_KEY`, behind an `LLMClient` protocol with
Fake, Recording and Replay implementations.

**Alternatives.**
1. A raw `httpx` client: more code and no benefit, since the API is OpenAI-compatible.
2. LangChain, LlamaIndex or another agent framework: a heavier dependency that obscures the tool
   loop we need to control tightly and complicates cost accounting.
3. The Muse Code SDK: TypeScript-only and aimed at driving the Muse Code CLI, not inference.

**Trade-offs.** Depends on the OpenAI SDK remaining compatible with Meta's implementation of
`response_format`; mitigated by the protocol abstraction and an opt-in live smoke test.

**Evidence.** Meta's [quickstart](https://dev.meta.ai/docs/quickstart) recommends the `openai`
package; see also its protocol and structured-output documentation. The `openai` package requires
Python 3.10 or later.

**Unresolved.** Whether Meta accepts every JSON Schema construct generated from our Pydantic models
across all request types (see ADR-029).

---

## ADR-003 Single orchestrator with typed tool registry

**Decision.** One orchestrator (a) asks the model for a `ReviewPlan` through structured output,
(b) filters the plan against the registry and the confirmed requirements, (c) executes checks
deterministically under a hard cap and (d) invokes the explainer on request. Requirement extraction
and explanation are separate structured-output calls, not tools in a loop.

**Alternatives.**
1. Several cooperating LLM agents: more calls, more failure modes and an inter-agent protocol to
   design and debug, with no capability gained because most of the responsibilities are
   deterministic.
2. A fully deterministic pipeline with no planner: robust and cheap, but cannot interpret a
   plain-language review objective.
3. A free-running tool-calling agent without a plan step: harder to cap, explain and evaluate;
   plan-then-execute leaves an inspectable artefact.

**Trade-offs.** Plan-then-execute is less adaptive than an open loop: the model cannot react to
intermediate results. Accepted; an iterative refinement step is possible later.

**Unresolved.** Whether the planner adds measurable value over the default plan across a range of
objectives (OQ-04).

---

## ADR-004 IfcOpenShell + IfcTester for model access and IDS validation

**Decision.** Use `ifcopenshell` 0.9.x for all IFC access and `ifctester` 0.9.x as the IDS 1.0
engine. Native rules supplement IDS for checks IDS cannot express.

**Alternatives.**
1. A custom IDS validator: duplicates a maintained reference implementation.
2. `web-ifc` on the backend through Node: would split the backend across two runtimes.
3. Commercial checker APIs: not open source.

**Trade-offs.** IfcOpenShell is LGPL-3.0-or-later, which is compatible with MIT project code when
used as an installed package. Geometry support is strongest for IFC2X3 and IFC4; IFC4X3 geometry is
partial.

**Evidence.** [IfcOpenShell on PyPI](https://pypi.org/project/ifcopenshell/) (0.9.0.post1, LGPL),
the [IfcTester documentation](https://docs.ifcopenshell.org/ifctester.html) and the
[buildingSMART IDS repository](https://github.com/buildingSMART/IDS) (schema 1.0.0). IfcTester's
PyPI classifier is LGPLv3+.

**Unresolved.** None.

---

## ADR-005 Python 3.10–3.12 supported, developed on 3.12

**Decision.** `requires-python = ">=3.10,<3.13"`; development and CI use Python 3.12.

**Alternatives.** Python 3.13 or later: IfcOpenShell publishes no wheels for it, and a source build
needs the OpenCASCADE toolchain.

**Trade-offs.** Newer language features are unavailable; negligible for this project.

**Evidence.** The IfcOpenShell wheel index lists cp310–cp312 wheels only, despite broader
`requires_python` metadata.

---

## ADR-006 File-system session store, no database

**Decision.** Each session is a directory under `data/sessions/{uuid}/` holding its model versions,
documents, `requirements.json`, review runs and explanations. Writes are atomic (write to a
temporary file, then rename). [ADR-017](#adr-017-content-addressed-model-versions-with-single-pointer-publication)
refines the model layout: model bytes, index and summary live together under `models/{sha256}/`.

**Alternatives.**
1. SQLite: an easy upgrade path, but adds migrations and query code without a current need.
2. Postgres or Redis: infrastructure out of proportion to a single-user local application.

**Trade-offs.** No concurrent multi-user access and no querying across sessions; acceptable for a
single-user local application. The `SessionStore` interface is the seam for a database later.

---

## ADR-007 Browser-side geometry with That Open Components

**Decision.** The frontend loads the IFC with `@thatopen/components` `IfcLoader` (web-ifc worker →
Fragments) and highlights elements by GlobalId. The backend does no geometry processing.

**Alternatives.**
1. Backend tessellation with `ifcopenshell.geom` → glTF → Three.js: a second pipeline, slow for
   large models, and it loses IFC semantics in the viewer.
2. Plain Three.js and web-ifc without That Open Components: more code for selection, culling and
   UI.
3. xeokit: a strong viewer, but AGPL or commercial licensing; That Open Components is MIT.

**Trade-offs.** The IFC is parsed twice: on the backend for semantics and in the browser for
geometry. The join relies on GlobalId, which IFC requires on every rooted entity.

**Evidence.** `@thatopen/components` 3.6.0 (MIT; peers `three >= 0.182.0`, `web-ifc >= 0.0.77`).
Browser checks on the minimal fixture exercised `getLocalIdsByGuids`, `getGuidsByLocalIds` and
`Highlighter.highlightByID`: selecting a finding highlights its wall, and clicking the wall selects
the matching finding.

**Licence note.** `web-ifc` 0.0.77 is MPL-2.0, not MIT. It is installed unchanged because the viewer
stack requires it; this is a documented exception to the project's permissive-or-LGPL dependency
preference. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for redistribution obligations.

**Out of scope.** Running IDS in the browser with the `IDSSpecifications` component as a
cross-check.

---

## ADR-008 Human confirmation of extracted requirements

**Decision.** Requirements extracted from narrative documents start as `proposed`. Only `confirmed`
requirements are executable. Uploaded IDS files are treated as confirmed because they are already
machine-readable project specifications.

**Alternatives.** Auto-confirm above a confidence threshold: the model's confidence is
uncalibrated, and a false requirement would generate false findings that look verified.

**Trade-offs.** One extra step for the user, in line with ISO 19650 practice, which places
requirement definition under human information-management control.

---

## ADR-009 Deterministic grounding check on every explanation

**Decision.** Explanations are structured outputs that must list the GlobalIds and properties they
cite. A deterministic checker verifies every citation against the evidence. A failure falls back to
a clearly labelled deterministic template.

**Alternatives.** An LLM judge for faithfulness: costs a second call, is itself fallible, and is
unnecessary when the evidence is structured.

**Trade-offs.** Explanations can cite only the supplied evidence, so broader advice must be phrased
generically. Matching values is heuristic and may reject a valid explanation; rejections fall back
safely.

---

## ADR-010 Standard-mode model ids only

**Decision.** Configuration rejects model ids ending in `-contributor` unless
`ALLOW_CONTRIBUTOR_MODELS=true`. The default model is `muse-spark-1.3`.

**Alternatives.** Contributor mode: much cheaper input tokens, but it permits Meta to train on the
submitted content, which may include confidential project documents and model data.

**Trade-offs.** A higher cost per request, kept small by the spend controls in ADR-020.

**Evidence.** Meta's [models](https://dev.meta.ai/docs/models) and
[pricing](https://dev.meta.ai/docs/pricing-rate-limits) documentation: Standard-mode content is not
used for training; Contributor mode opts in to training.

---

## ADR-011 Synthetic benchmark with defect injection

**Decision.** Generate a small, clean architectural IFC programmatically with `ifcopenshell.api`
(storeys, walls, doors, windows, slabs, spaces, type objects, property sets and classification),
then inject labelled defects by script to produce a defective model and its ground truth. The
benchmark lives in `tests/evaluation/` and is regenerated on demand.

**Alternatives.**
1. Hand-edit a public sample IFC: licence and redistribution must be checked per file, and manual
   edits are error-prone and hard to reproduce.
2. Use a real project model: confidential, and cannot be committed.

**Trade-offs.** A synthetic model is simpler than a real one and under-represents messy real-world
data. In return, the ground truth is exact and the benchmark is reproducible and redistributable
under the project licence.

**Evidence.** The benchmark has 15 labelled defects in three rule families and seven clean
controls; the deterministic validator scores 1.000 precision and recall on it. See
[datasets/README.md](../datasets/README.md).

**Unresolved.** Whether to add a second dataset based on an openly licensed public model (OQ-03).
Candidates include the buildingSMART sample test files and the IfcOpenShell test files.

---

## ADR-012 Chat Completions protocol first

**Decision.** Use `POST /v1/chat/completions` for planning, extraction and explanation calls.

**Alternatives.** The Responses API, which Meta recommends and which supports cross-turn reasoning
replay; the Anthropic-compatible Messages API.

**Trade-offs.** Chat Completions is the most broadly compatible with the OpenAI SDK's
structured-output support. Responses may behave better for multi-step work; revisit if planning
quality becomes the bottleneck.

**Evidence.** Meta's [protocol documentation](https://dev.meta.ai/docs/protocols).

---

## ADR-013 Synchronous in-process review runs, no task queue

**Decision.** A review runs synchronously inside the request that starts it, under the session lock
(ADR-018 §4), and returns the completed run. There is no task queue and no progress stream.

**Alternatives.**
1. Celery or RQ with Redis: infrastructure out of proportion to a local application.
2. FastAPI background tasks with Server-Sent Events: the original design, deferred because runs on
   the supported model sizes complete in seconds.
3. WebSockets: bidirectional communication is not needed.

**Trade-offs.** A long run blocks the request and holds the session lock, so uploads to that session
wait for it. Background execution with a progress stream is the planned remedy for large models.

---

## ADR-014 Frontend types generated from Pydantic JSON Schema

**Decision.** Export JSON Schema from `schemas/` with `model_json_schema()` and generate TypeScript
types with `json-schema-to-typescript`. Both generated files are committed and checked, so the
frontend builds without Python:

- `python scripts/export_schemas.py` writes `frontend/src/api/generated/bim_intelligence.schema.json`;
  a test asserts it is current.
- `npm run types:generate` writes `types.ts` from it, and `npm run types:check` fails CI when it is
  stale.

**Alternatives.** Hand-written TypeScript interfaces (they drift); OpenAPI client generation
(heavier; FastAPI's OpenAPI embeds the same schemas, so either route works).

**Trade-offs.** One generation step to maintain, in exchange for identical `Finding`,
`Requirement` and `Explanation` shapes on both sides.

**Evidence.** The Pydantic [JSON Schema documentation](https://docs.pydantic.dev/latest/concepts/json_schema/).

---

## ADR-015 Contract model: immutable `CheckSpec`, content-addressed `Finding`, per-check `CheckResult`

**Decision.** Implemented in `backend/bim_intelligence/schemas/`.

1. **`CheckSpec` is immutable and content-addressed.** `CheckSpec.id = sha1(kind | rule_id |
   rule_version | payload)[:16]`, where the payload is the serialised IDS `<specification>` for
   `kind="ids"` or the canonical JSON of `params` for `kind="native"`. A `ReviewPlan` item carries
   only `{check_id, reason}`; the orchestrator resolves the id to the confirmed `CheckSpec` on the
   server. No code path accepts model-supplied parameters, so a plan can choose which confirmed
   checks run but can never weaken what a check asserts.
2. **A `Requirement` is executable only at its confirmed revision.** `status="confirmed"` requires
   `confirmed_revision == revision`; an edit increments `revision`, and an `edited` requirement is
   not executable until it is confirmed again. A requirement with `origin="document"` must carry a
   verbatim `source` quote.
3. **`Finding` identity and order are canonical.** `Finding.id = sha1(check_id | rule_version |
   facet_index | sorted element keys)[:16]`, where an element key is its GlobalId, or
   `#express_id` when there is none. Elements are stored in key order; `findings.json` uses sorted
   keys, with findings ordered by `(check_id, facet_index, first element key, id)`. `Finding` has
   **no** `created_at` and **no** `run_id`: both would break byte-identical output across runs, and
   the run already lists its findings through `CheckResult.finding_ids`. `method` is `ids` or
   `native` only (ADR-001).
4. **Execution status is separate from defects.** `CheckResult {check_id, requirement_id, status ∈
   passed | failed | error | skipped | not_applicable, applicable_count, finding_ids[],
   diagnostics[]}`: `failed` if and only if `finding_ids` is non-empty, `error` requires a
   diagnostic, and `not_applicable` requires zero applicable elements. `ReviewRun` is the only
   record with timestamps. An IfcTester exception, a cap being reached or a specification with no
   applicable entities is a `CheckResult` status, never a finding.
5. **`ElementRef.global_id` is nullable; `express_id` is always present.** GlobalId remains the
   viewer join key (ADR-007); `express_id` is diagnostic and the fallback identity for entities that
   are not `IfcRoot`.
6. **Contract models forbid unknown fields** and are exported in serialisation mode, so every field
   is required in the TypeScript types and an unexpected key (such as `params` on a plan item) is a
   validation error, not a silent drop.

**Alternatives.** UUID finding ids with timestamps (not reproducible); modelling errors and zero
applicability as finding categories (pollutes precision and lets skipped checks read as
compliance); letting plans pass `params` (a schema-valid plan could check weaker conditions than
the user confirmed).

**Trade-offs.** Identity is bound to `rule_version`, so a rule change renames every finding it
produced; this is intended, since the finding's meaning changed. Content-addressed ids are scoped
to a session's inputs, not globally unique. `CheckSpec.params` is typed as JSON, which is acceptable
because a `CheckSpec` is never sent to the model.

**Evidence.** `tests/unit/schemas/` (identity, ordering, invariants and schema drift). With
`ifctester` 0.9.0, `Specification.failed_entities` is a set, `applicable_entities` an ordered list,
and each `requirement.failures` entry is `{"element": entity, "reason": str}`;
`Facet.to_string(clause_type, specification, requirement)` renders the expected text.

---

## ADR-016 Ingestion contract: staged upload, content-hash ETag and identifier handling

**Status.** §1 is superseded by
[ADR-017](#adr-017-content-addressed-model-versions-with-single-pointer-publication), which replaces
the multi-step publication with a single-pointer transaction. §2–§6 stand.

**Decision.**

1. **Uploads are staged, validated, then published.** `SessionStore.stage_model()` writes the
   upload to a temporary file inside the session directory while hashing it and enforcing
   `MAX_IFC_MB`. The staged bytes are parsed and indexed in place, and published only after indexing
   succeeds. A malformed or oversized upload therefore never replaces a previously indexed model,
   and the stored bytes are exactly the client's bytes.
2. **The model hash is the cache key.** `GET /sessions/{sid}/model/file` serves the stored bytes
   with an `ETag` equal to the quoted SHA-256 and answers `If-None-Match` with 304.
   `Session.model_hash` and `ModelSummary.model_hash` carry the same value, so the viewer, the
   validator and the run's input manifest always refer to the same bytes.
3. **Identifiers are validated at the boundary.** Session ids must be lower-case UUID4s, and
   artefact names come from a fixed allow-list before any path is formed. A malformed session id or
   GlobalId is a 400 and an unknown one a 404. Client file names are used only for the extension
   check.
4. **Malformed GlobalIds do not abort ingestion.** An `IfcRoot` whose `GlobalId` fails the
   22-character check is indexed with `ElementRef.global_id = None` and listed in
   `ModelIndex.malformed_global_ids`. Duplicate GlobalIds keep every record
   (`duplicate_global_ids`), `by_global_id()` raises, and the API returns 409. Both are inputs to a
   future identity rule, not findings in themselves (ADR-001).
5. **Problem types are project-scoped URIs.** `ProblemDetail.type` is
   `https://github.com/natnew/BIM-Intelligence/problems/<slug>`, mirroring the schema bundle's
   `$id`. It identifies the problem class for clients without implying a resolvable document.
6. **Property provenance is reproduced, not reinvented.** `ElementRecord.psets` reproduces
   `ifcopenshell.util.element.get_psets()`'s merge (type first, instance overrides, property by
   property) and flags a value `inherited` when it comes from the type object; tests assert
   equality with IfcOpenShell for every indexed entity.

**Alternatives.** Writing `model.ifc` directly and deleting it on failure (a window in which a
session has no model, and a failed re-upload destroys the old one); treating a malformed GlobalId as
a 422 (rejects real-world files the validator should report on); `about:blank` problem types (no
client-side discrimination).

**Trade-offs.** FastAPI's `UploadFile` spools the whole request body before the handler runs, so the
size cap is enforced after receipt rather than during it; acceptable for a local application, to
revisit if remote binding is used.

**Evidence.** `tests/unit/store/`, `tests/unit/bim/` and `tests/unit/api/`: the fixture's SHA-256
equals the stored hash and the `ETag`.

**Unresolved.** Materials and storey elevations are not indexed; whether IFC4X3 should stay accepted
before a benchmark covers it.

---

## ADR-017 Content-addressed model versions with single-pointer publication

**Status.** Supersedes ADR-016 §1 and refines the ADR-006 layout. Implemented in
`store/session_store.py`, `store/locking.py`, `bim/ingest.py`, `api/versioning.py`, `api/model.py`,
`api/elements.py` and `api/main.py`.

**Context.** Publishing an upload as four independent writes (model file, index, summary, session
record) is atomic per file but not as a set. A failure part-way, a concurrent reader or two
concurrent uploads could leave or observe a session whose bytes, index, summary and hash describe
different models. The invariant this record establishes: *a client can never observe a committed
session whose IFC file, indexed elements, summary and model hash refer to different model
versions.*

**Decision.**

1. **A model version is an immutable, content-addressed directory.** `models/{sha256}/` holds
   `model.ifc`, `model_index.json` and `model_summary.json`, all built from exactly those bytes. The
   directory is assembled in a private `models/.staging-{hex}/`, validated (every artefact present,
   the file size equals the bytes written, the summary's `model_hash` equals the upload's SHA-256),
   fsynced and moved into place with **one rename**. A version directory therefore exists complete
   or not at all and is never modified afterwards. Re-uploading bytes that already exist as a
   complete version reuses it; a damaged copy is replaced.
2. **Activation is one atomic write.** `Session.model_hash` points to the active version;
   `SessionStore.set_model()` refuses a hash whose directory is incomplete and publishes the pointer
   with an atomic replace of `session.json`. A crash between committing the directory and swapping
   the pointer leaves a complete but inactive version, which is harmless.
3. **Readers resolve the version once.** `SessionStore.active_model()` returns a `ModelVersion`, and
   bytes, index and summary are read only through it, so a single request cannot mix versions.
   Every model read (`/model/summary`, `/model/file`, `/elements/{globalId}`) carries an `ETag` of
   the quoted SHA-256 of the version it was answered from. Clients may send `If-Match` to pin a
   sequence of reads to one version; a mismatch is **412 `model-version-mismatch`**, naming the
   active hash.
4. **Publication is serialised by a per-session advisory file lock** (`model.lock`; `fcntl.flock`
   on POSIX, `msvcrt.locking` on Windows, both of which conflict between threads and processes).
   The lock object is the capability required to stage, commit, activate, prune or discard staging.
   Acquisition does not wait: a second upload in progress is **409 `model-locked`**. Readers never
   take the lock.
5. **Superseded versions are retained until pruned.** A re-upload activates a new version and leaves
   the previous directory intact, so an in-flight download or a run pinned to the old hash keeps a
   consistent snapshot. `SessionStore.prune_model_versions(lock, keep=…)` removes other complete
   versions; nothing calls it automatically yet.
6. **Abandoned staging is recovered, never served.** Staging directories are invisible to readers.
   `ingest_model` discards any it finds once it holds the lock, and application start-up sweeps
   them, skipping sessions whose lock is busy.
7. **Windows sharing violations are retried.** `session.json` is the only file replaced in place;
   its write and read retry a bounded number of times on `PermissionError`, which is how Windows
   reports a replace racing a concurrent open.

**Alternatives.**
- *Keep the flat layout and order the writes carefully.* No ordering of four independent files
  gives an atomic set.
- *A manifest file listing hash-suffixed flat files.* Equivalent to version directories, with a
  worse pruning story.
- *SQLite with a transaction.* Solves atomicity, but adds a database for a single pointer swap
  (ADR-006).
- *A blocking lock that queues the second upload.* Makes one upload's response time depend on
  another; a non-blocking 409 is explicit and retryable.
- *Prune superseded versions on publish.* Breaks any reader or run that resolved the old version.
- *`/models/{hash}/…` routes.* Clean addressing, but a new API surface; `If-Match` is the
  HTTP-native way to pin.

**Trade-offs.**
- Disk use grows by one version per distinct re-upload per session until pruning; acceptable while
  `data/` is disposable.
- Reusing an existing version for identical bytes serves an index built by an older indexer until
  `data/` is cleared; the index format is not versioned yet.
- `If-Match` protects only clients that ask for it.
- The directory rename and pointer swap are durable on POSIX (directory fsync) and best-effort on
  Windows, which cannot fsync directories.

**Evidence.** `tests/unit/store/test_session_store.py`, `tests/unit/store/test_locking.py`,
`tests/unit/bim/test_ingest_publication.py` and `tests/unit/api/test_model_versioning.py`. Failures
injected at each stage of publication leave the session unchanged or with only a complete inactive
version; two concurrent uploads give one 201 and one 409; concurrent readers never observe a mixed
artefact across repeated replacements; a restart removes abandoned staging.

**Unresolved.** A retention policy for superseded versions; whether to version the index format so
that a stale reused version is rebuilt.

---

## ADR-018 IDS import establishes confirmed requirements; checks are hydrated per run; reviews run under the session lock

**Status.** Implemented in `validation/`, `requirements/`, `orchestration/`, `api/documents.py`,
`api/requirements.py`, `api/reviews.py` and `api/findings.py`.

**Context.** This decides how an uploaded IDS becomes executable checks without giving
`requirements/` an IfcTester dependency; how a check runs from its `CheckSpec` alone rather than from
the document it came from (ADR-015 §1); how zero applicability, prohibited specifications, schema
mismatches and engine exceptions are reported without inventing findings (ADR-015 §4); and how a run
keeps one model version for its whole duration (ADR-017 §4).

**Decision.**

1. **An imported IDS is a set of confirmed requirements.** One `Requirement` is created per
   `<specification>`, with `origin="ids"`, `status="confirmed"`, `revision = confirmed_revision = 1`,
   `confirmed_by="ids-import"` and a `source` recording the document's SHA-256, the specification's
   position and its verbatim `name`. ADR-008's human confirmation applies to requirements
   *interpreted* from narrative text; an IDS is the project's own machine-readable statement.
   Requirement ids are sequential per session (`REQ-001`, …), and re-uploading the same bytes
   returns the existing requirements (HTTP 200) rather than duplicating them.
2. **The `CheckSpec` payload is the canonical specification element, and it is the only thing a
   run executes.** `validation.compile_ids` validates the document against IfcTester's bundled
   IDS 1.0 XSD and stores each `<specification>` in XML Canonical Form (C14N 2.0) with
   whitespace-only text removed; `rule_version = content_hash(payload)` and `rule_id =
   "ids:<identifier or name>"`, so identically specified checks have the same id regardless of file
   formatting. `validation.hydrate_specification` rebuilds an `ifctester.ids.Specification` from the
   payload alone, after confirming it still hashes to `rule_version`; a mismatch is a
   `CheckSpecIntegrityError`, reported as `CheckResult.status="error"`. There is no code path from a
   stored document, a plan or a client to the criteria of a confirmed check.
3. **Each check runs in its own single-specification `Ids` through `Ids.validate`.** That is
   IfcTester's public entry point and the one that resets its property caches, so checks cannot leak
   state into each other and an exception in one is contained. Outcomes:
   - the specification's `ifcVersion` excludes the model's schema → `skipped`;
   - a required or optional specification with no applicable entity → `not_applicable`;
   - a prohibited specification → one `prohibited_entity` finding per matching entity, or `passed`;
   - facet failures → `failed`, with one finding per (facet, entity): `observed` is IfcTester's
     reason, `expected` the facet's rendered requirement, `category` `<facet>_requirement` and
     `severity` `error`;
   - any exception → `error`, with `"<Type>: <message>"` in `diagnostics`.

   Element references come from the Model Index of the same version, so findings, the element API
   and the viewer agree.
4. **A review holds the session's model lock from version resolution to publication.**
   `orchestration.run_review` takes the lock, resolves the active version once, refuses a pinned
   hash that is not active (412), builds the plan, records the `InputManifest` (model hash, sorted
   IDS hashes, requirement revisions and rule versions), runs the checks and publishes
   `runs/{runId}/run.json` and `findings.json` with one rename. An upload, an IDS import or a second
   review in the meantime is 409 `model-locked`, and nothing can prune the version under the run.
   The same lock guards every write to `session.json`, so the session record has one writer.
5. **Run status is derived, never asserted.** A session without a model (404) or without an
   executable requirement (409 `no-executable-checks`) records no run, so an empty run cannot read as
   compliance. Status rules for caps and coverage are refined in ADR-019.
6. **The IDS XSD is loaded offline.** `ids.xsd` imports the W3C XML and XSD namespaces by URL. The
   compiler constructs `XMLSchema(ids.xsd, allow="local")` itself, which makes `xmlschema` a direct
   dependency (MIT) and removes the only outbound request the backend would otherwise make. A test
   compiles under a socket guard.

**Alternatives.**
- *Run `Ids.validate` once per document.* Simpler, but a check would be defined by a file rather than
  its `CheckSpec`, an error in one specification would abort the others, and a plan could not select
  checks individually.
- *Store the raw `<specification>` text.* Formatting changes would rename every finding; C14N keeps
  identity semantic.
- *Treat zero applicability of a required specification as `failed`* (IfcTester's own status). A
  finding needs an element; "nothing to check" is a coverage fact, not a defect.
- *Run specifications whose `ifcVersion` excludes the model anyway.* The IDS author scoped the rule;
  running it against another schema can give confident nonsense.
- *A finding category per IfcTester reason string.* Couples the contract to library prose; the
  facet type is stable and the reason is kept verbatim in `observed`.

**Trade-offs.**
- Requirement ids are per session and sequential, so `findings.json` is byte-identical across
  sessions only when documents are imported in the same order; within a session it is
  byte-identical across runs.
- `rule_versions` in the manifest is keyed by `rule_id`, so two specifications that share a name but
  differ in content collapse to one key there; `requirement_revisions` and `ids_hashes` still
  identify the inputs exactly.
- A synchronous run holds the lock for its duration (ADR-013).
- `severity` is `error` for every IDS finding; IDS 1.0 has no severity concept.
- IfcTester 0.9.0 recognises only lower-case `true`/`false` for boolean `simpleValue`s, so IDS files
  for this system should write booleans in lower case.

**Evidence.** `tests/unit/validation/`, `tests/unit/requirements/`, `tests/unit/orchestration/`,
`tests/unit/store/test_session_store_runs.py`, `tests/unit/api/test_documents.py` and
`tests/unit/api/test_reviews.py`. On the committed fixture, two confirmed requirements give two
`failed` results and exactly two findings (W-002 `0QWMtUzsnUUONCUGc8Sqsa` for the fire-rating
specification and W-003 `2qvnbd6oPPKR1ac5HegGTJ` for the classification specification). The findings
match `ifctester.reporter.Json` element for element, repeated runs give identical `findings.json`,
the model version is unchanged afterwards, an upload attempted during a run is refused with 409,
and no socket is opened during compile, hydrate or run.

**Unresolved.** Whether `POST /documents` should accept a batch; how an edit to an IDS-origin
requirement recompiles its payload (today the edit makes it `edited` and non-executable until it is
confirmed again).

---

## ADR-019 Native rule scope and bounded deterministic execution

**Status.** Supersedes ADR-018's all-checks plan description and its run-status rule where execution
caps and `not_applicable` coverage are concerned; model locking, input manifests and atomic
publication are unchanged.

**Decision.**

1. Ship one native rule, `classification.consistent_by_type` v1.0.0. It compares the effective
   `(system, identification-or-name)` classification references of a classified type and each of
   its occurrences, emits a deterministic finding for each mismatch, and reports `not_applicable`
   when no classified type occurrence exists. Its `CheckSpec` has no parameters; invalid
   parameters, rule ids or versions are execution errors.
2. Keep IDS 1.0 as the implementation for required properties, expressible naming patterns,
   classification presence and classification-system checks, and register no native duplicates.
3. Add the native rule only as an explicit, built-in confirmed requirement through
   `POST /sessions/{sid}/requirements/native/classification-consistency`. Repeated confirmation is
   idempotent, and the model lock protects it from an active review.
4. Build the default plan from the confirmed executable requirements, deduplicated by check id in
   requirement order. Apply `MAX_PLAN_CHECKS` and `MAX_TOOL_CALLS_PER_RUN`; report unexecuted
   checks as `skipped`, continue after a per-check `error`, and mark any run with an `error`,
   `skipped` or `not_applicable` result as `partial`.

**Alternatives.** Overlapping native property, classification-presence or naming rules (rejected:
IDS already expresses them, and duplicates would repeat findings). Adding the native rule to every
session automatically (rejected: it is an additional check and should be chosen). Stopping the
review after an error or cap (rejected: later checks should still run, and every omitted check
should stay visible in coverage).

**Trade-offs.** The native registry holds one rule, not a plugin system. Its parameter-free contract
avoids configuration that could weaken a confirmed requirement. A `partial` run is deliberately
conservative: `not_applicable` is not a defect, but it does not demonstrate coverage.

**Evidence.** `tests/unit/validation/test_native_rules.py`,
`tests/unit/api/test_native_requirements.py`, `tests/unit/orchestration/test_review_runner.py` and
`tests/scenario/test_deterministic_review.py`.

---

## ADR-020 Meta client, spend ledger and Live-mode safeguards

**Decision.** Keep the Meta integration behind the `llm/` package boundary and the OpenAI SDK.
`LLMClient.complete` returns a Pydantic-validated response and typed usage. `LiveClient` alone can
make network requests; Fake, Recording and Replay work offline, and Replay and Off never fall back
to Live. The default mode is `off`. Live requires `MODEL_API_KEY`, a Standard-mode model id and
`ALLOW_LIVE_LLM=true`. The endpoint is restricted to `https://api.meta.ai/v1`, and retries default
to zero.

Before each live call, the application reserves budget using the configured per-million-token
prices, the estimated input and the full output allowance. Reservations, usage, calculated costs
and outcomes are persisted in a lock-protected JSON ledger under `DATA_DIR/llm/`. Unknown usage is
charged at the reserved amount, and an unreadable ledger or unavailable lock disables Live. The
defaults are 8,000 estimated input tokens per call, two live calls per review, USD 0.10 per call
and per review, and a USD 5.00 cumulative allowance. These are local application safeguards, not
provider-enforced limits.

**Requirement workflow.** Narrative Markdown or text candidates keep a source hash, paragraph id and
verbatim quote, all checked again on confirmation. The model may map a candidate only to an existing
confirmed `CheckSpec`, and human confirmation is mandatory. The application does not generate new
IDS criteria.

**Explanation workflow.** An AI explanation is a separate response contract, grounded against the
deterministic finding, the matching requirement revision and the model index. Every citation binds
finding, GlobalId, requirement, rule, and expected and observed values. Multi-element findings and
any grounding failure use the deterministic template. Explanation output never enters
`findings.json`.

**Alternatives.** Provider billing alerts as hard limits (rejected: they are not reliable caps).
Enabling Live automatically when a key is present (rejected: an implicit cost path). Persisting
prompts in recordings (rejected: retains project text unnecessarily). Letting the model create
`CheckSpec`s (rejected: free-form output could invent validation semantics).

**Trade-offs.** The byte-based input estimate is conservative for ordinary UTF-8 but is not the
provider's tokenisation. Usage is reconciled after a request; if it exceeds the reservation, the
actual amount is recorded and further requests are blocked, but the provider may already have
billed it. Deleting the ledger, or spending outside the application, bypasses the safeguard.

**Evidence.** Offline tests cover Fake and Replay, schema validation, quote verification, plan
filtering, grounding fallback, API routes, error sanitisation, reservation persistence and
concurrent accounting. Price defaults come from Meta's
[published pricing](https://dev.meta.ai/docs/pricing-rate-limits) and are configurable.

---

## ADR-021 Bounded model federation is separate from a session

**Status.** Adopted as the design boundary for future multi-model coordination. Not implemented.

**Decision.** Keep the existing `Session` contract: a session has at most one active IFC model
version. Do not overload a session, or replace its IFC, to represent another discipline. A future
`ModelSet` manifest may reference immutable IFC versions from several sessions. A first version
would support exactly two models and one selected pair.

Each member records a stable identity, its source session, the immutable model SHA-256, a
discipline label, its coordinate frame and its placement. The set declares one common coordinate
frame, with units and the evidence used to validate placement. Unknown or ambiguous alignment is
rejected, never guessed from model extents, file names or discipline names.

Every federated element reference is scoped by member identity and model hash, then by GlobalId
where available, with `(ifc_type, express_id)` as a fallback within one model hash. GlobalId alone
is never a federation key. Model bytes stay read-only and per-file upload limits still apply.

**Alternatives.** Expanding `Session` to hold several models would break its contract and version
guards; replacing the active IFC would lose the first model's version identity; guessing alignment
from geometry would produce plausible but unverified intersections.

**Trade-offs.** A separate manifest adds a narrow coordination boundary, not general project
management, model authoring or enterprise federation.

**Evidence.** `schemas/sessions.py` defines one `model_hash` per `Session`, and `bim/ingest.py`
activates one immutable model version. No model-set contract exists. A synthetic test harness in
`tests/feasibility/` exercises geometric intersection and alignment only.

**Unresolved.** Whether the installed geometry stack can load and compare a model pair in a verified
common frame; a suitable openly licensed sample pair.

---

## ADR-022 Deterministic geometric coordination results

**Status.** Adopted as the design boundary for future clash detection. Not implemented; depends on
ADR-021.

**Decision.** A coordination run may use only an installed, version-verified geometric capability,
such as IfcClash, whose provenance, API and behaviour have been checked first. IfcClash is not
currently installed, and no package will be added without a dependency and licence review.

A run evaluates one declared model pair only after both model hashes and their common frame have
been validated. It records the run identity, both model hashes and member identities, the algorithm
and version, an explicit distance tolerance and units, exclusions, placement assumptions and the
tested IFC entity scope. There is no implicit tolerance or alignment; missing or unsupported inputs
produce a visible error state.

Three concepts stay separate: raw geometric intersections, deterministic groups of them, and
coordination issues assessed by a person. An intersection is not automatically a defect.
Coordination output is never written as a `Finding`, never changes IDS or native criteria, and is
never authored by AI: the model must not create clash coordinates, intersections, counts or issue
states.

The run state distinguishes `unavailable`, `not_analysed`, `zero_clashes`, `analysis_error` and
`results_available`. Counts come only from a completed run, and zero is never substituted for an
unavailable or failed analysis.

**Alternatives.** Treating every intersection as a defect (misleading); model-generated coordinates
(unverifiable); reusing `Finding` for clashes (conflates two result types).

**Trade-offs.** A small, verifiable coordination capability, not enterprise clash management, issue
assignment or code compliance.

**Unresolved.** The engine and tested entity scope; the grouping rule; a suitable tolerance; an
openly licensed sample pair.

---

## ADR-023 Viewer integrity and visual continuity

**Decision.** Keep one application shell, colour palette and typography across Project Home and the
review workspace. Future features such as coordination are modes within this application, not a
second product.

Viewer and application selection state must stay coherent. Selection styling is neutral and visibly
distinct from finding highlights. Inspecting evidence must not replace or unexpectedly reset the
viewport. Camera controls are offered only where the installed viewer supports them and they pass
regression tests; the application never shows inert controls. Model loading is described by
observed states, without invented percentage progress.

**Alternatives.** A separate coordination application (duplicates the shell and fragments the review
context); severity-coloured selection (conflates user focus with defect status); fabricated progress
or unsupported controls (misrepresents behaviour).

**Trade-offs.** Existing selection, finding identity, viewer lifecycle, version guards, read-only
model handling, accessibility and palette take precedence over adding controls.

**Evidence.** The viewer exposes orbit, pan, zoom, selection, and **Focus**, **Fit** and **Reset**
controls. Browser checks on the synthetic fixture exercised these controls and two-way
finding/element selection.

**Unresolved.** Which camera operations the viewer can safely expose for a multi-model scene; a
complete accessibility audit.

---

## ADR-024 Muse Spark remains an optional, grounded interpretation provider

**Decision.** Meta Muse Spark, through the existing Meta Model API client, is the provider for
bounded review planning and grounded finding explanations. These reuse the planner, the explanation
path, output validation, the grounding check, the spend ledger and the deterministic fallback. The
interface shows the actual plan source (`ReviewRun.plan_source`), the actual explanation source, and
whether the deterministic fallback was used.

Deterministic findings stay separate from AI interpretation. The model cannot create or edit a
`Finding`, coordinates, results or check criteria. `LLM_MODE=off` remains the default, and Live use
requires backend credentials configured by the operator.

**Alternatives.** Presenting a default or offline plan as a live AI result, presenting a template as
AI, or letting AI change validation semantics would all misstate provenance and break the finding
contract.

**Trade-offs.** The deterministic review stays fully usable when the provider is unavailable.

**Evidence.** The review workspace offers **Run AI Review** with a review objective, an explicit
**Continue without AI** path and on-request explanations, each labelled with its source.

---

## ADR-025 Show only verified capabilities

**Decision.** Public material, including the README and any demonstration, shows only capabilities
that are implemented and verified. Planned features, such as multi-model federation and clash
detection (ADR-021, ADR-022), are described as planned and never presented as working. A
demonstration of the deterministic review without AI is labelled as such, never as Meta-assisted.

**Alternatives.** Presenting planned features as working, or stretching scope at the expense of the
verified workflow, would undermine trust in the results the application does produce.

**Trade-offs.** Some planned capabilities are visible only in the roadmap and the decision records.

---

## ADR-026 Explicit AI review policy and run provenance

**Context.** Once the review API accepts a plain-language objective, silently running the
deterministic default after an unavailable or rejected AI plan would misrepresent whether the
requested review was performed. A persisted run also needs to record whether planning used Live,
Replay or Off, without inferring it from the current configuration, and user-selected checks must
stay bound to the exact requirement revision they were selected from.

**Decision.**

- An objective requires an accepted AI plan unless the request sets `ai_required=false`.
- `continue_without_ai=true` is an explicit choice to skip planning and run the deterministic plan.
  Strict planning failures return typed errors and publish neither a run nor findings. Unsupported
  scope is never replaced with a broader default plan.
- Optional AI failures may use the deterministic plan, with the failure reason recorded in the run.
  Explicit continuation is recorded separately from an attempted-but-rejected plan.
- Selected checks are identified by `check_id`, `requirement_id` and `requirement_revision`; stale,
  unconfirmed or mismatched selections are rejected before execution, and both planning and
  continuation are restricted to that scope.
- Each run records whether planning was requested, whether a provider request was attempted, the
  client mode and model, the planning outcome, any fallback reason, and the selected and executed
  check ids. Older runs without this record remain readable and are not given retrospective
  provenance.
- `BIMI_ENVIRONMENT=production` is a configuration profile that requires the Standard-mode
  `muse-spark-1.3` Live configuration and rejects Contributor mode. Development remains Off by
  default.

The production profile is not a deployment or security claim: the application has no
authentication and must not be exposed to an untrusted network.

**Alternatives.** Implicit deterministic fallback for every objective; inferring provenance from the
current mode; pinning a selection to a check id alone. Each loses user intent, historical accuracy
or revision-level traceability.

**Trade-offs.** A strict objective request now fails visibly when AI is unavailable; the interface
offers **Continue without AI** as the explicit alternative.

**Evidence.** Offline tests cover strict failure without run publication, budget refusal before a
provider request, rejected plan metadata, selected-check revision validation, Replay provenance and
compatibility with older runs.

**Unresolved.** Authentication and access control before any shared deployment.

---

## ADR-027 Structured review-planning request

**Context.** Early planning requests at a 500-token completion allowance returned usage but no
visible content: the allowance was used up before any output, so JSON parsing and validation were
never reached. The failure was not a schema error. Reasoning-token exhaustion is the likely cause.

**Decision.** Give review planning its own completion allowance of 2,000 tokens
(`LLM_MAX_PLANNING_OUTPUT_TOKENS`) and send `reasoning_effort="low"`; other workflows keep the
500-token default. Use Chat Completions `max_completion_tokens`, which Meta documents as supported
(`max_tokens` is a deprecated alias). Meta documents `low` reasoning effort for Muse Spark and does
not support `"none"`. Request a JSON Schema response format derived from the Pydantic response
model, with the plan's `checks` field required; omit the optional `strict` flag and keep validating
locally, including confirmed-check, duplicate, scope and cap rules. The prompt is the versioned
`planner.v2.md`.

The ledger records only safe response metadata: model id, response id, finish reason, completion
tokens, reasoning tokens when present, whether visible content was returned, and the outcome. It
never keeps prompts, response text, refusal text or credentials. Truncation and an exhausted
completion allowance are `token_limit`; `invalid_output` is reserved for content that is present
but fails JSON or Pydantic validation. Missing output below the limit, refusals and content-filter
outcomes are separate ledger outcomes.

Monetary limits are unchanged. At Standard rates of USD 1.25 per million input tokens and USD 4.25
per million output tokens, the uncached worst-case reservation for 8,000 input and 2,000 completion
tokens is USD 0.01850, within the USD 0.10 per-call limit.

**Alternatives.** Raising the shared 500-token cap (rejected: it would also change extraction and
explanation); disabling reasoning (not supported by Muse Spark); provider-side strict schema mode
(not adopted without compatibility evidence); reclassifying missing content as invalid output
(rejected: it would misreport the failure).

**Trade-offs.** A larger maximum reservation per planning request, still well within the per-call
and per-review limits.

**Evidence.** Offline `LiveClient` transport tests and Meta's
[Chat Completions parameter reference](https://dev.meta.ai/docs/protocols/chat-completions).

---

## ADR-028 Explanation completion allowance and token-limit labelling

**Context.** A live explanation request at the 500-token allowance returned `finish_reason=length`,
with 498 of its 500 completion tokens spent on reasoning and no visible content. The application
correctly fell back to the deterministic template, but labelled the fallback `budget_limit`, and the
interface described it as an exhausted spend limit although no monetary limit had been reached.
Explanation requests were also sent without the low reasoning effort adopted for planning.

**Decision.** Give finding explanations their own completion allowance,
`LLM_MAX_EXPLANATION_OUTPUT_TOKENS` (default and ceiling 2,000), and send them at
`reasoning_effort="low"`, matching the planning request. Other workflows keep the 500-token default.
The explanation schema, the `_ExplanationDraft` contract, local validation, the grounding checks and
the prompt `explanation.v1.md` are unchanged.

Separate the fallback reasons: `token_limit` when the provider exhausts the completion allowance
(`TokenLimitError`), and `budget_limit` only for application spend or call limits
(`BudgetLimitError`). The interface states the token-limit case as: "The AI explanation reached its
completion-token limit. The verified finding remains available, and a deterministic explanation is
shown instead."

Monetary limits are unchanged. A planning and an explanation reservation together come to
USD 0.03700, within the USD 0.10 per-review limit. The ledger's per-request output ceiling is the
largest of the three configured allowances, so a reservation is never rejected for an allowance the
client permits.

**Alternatives.** Raising the shared cap (rejected, as in ADR-027); keeping a combined
`budget_limit` category (rejected: it misreports the failure); reducing citation requirements so
shorter output passes (rejected: weakens ADR-009); revising the prompt before measuring the effect
of the allowance (deferred).

**Trade-offs.** A slightly larger maximum reservation per review, within unchanged limits.

**Evidence.** Offline `LiveClient` stub-transport and API regression tests reproduce the truncated
response and check the request body, classification and labels.

---

## ADR-029 Live structured-output evidence and retained validation

**Decision.** Keep the request shapes in ADR-027 and ADR-028 (non-strict JSON Schema,
`max_completion_tokens`, 2,000-token allowances, low reasoning effort) together with all local
validation: Pydantic schemas, confirmed-scope and cap checks for plans, and deterministic grounding
for explanations, with distinct `token_limit` and `budget_limit` outcomes.

**Evidence.** In a live run against the synthetic fixture, Muse Spark 1.3 returned a valid plan
(`finish_reason=stop`, 331 completion tokens including 288 reasoning tokens) that selected a
confirmed check, and a schema-valid explanation that passed the grounding check (542 completion
tokens including 330 reasoning tokens). The deterministic run and findings were unchanged after the
explanation. Before the allowance change, the same explanation request had exhausted the 500-token
allowance (ADR-028).

**Alternatives.** Reverting to 500 tokens would restore the observed failure; attributing the
original missing output to a schema defect would contradict the evidence; raising monetary budgets,
weakening citation checks or presenting a template as a live explanation would reduce safety or
misrepresent the result.

**Trade-offs.** One successful scenario shows that the request shape and evidence contract work for
that fixture and objective. It does not establish availability, behaviour on other models or
objectives, or the correctness of every sentence of an explanation.

**Unresolved.** OQ-02 and OQ-08.

---

## Open questions

| ID | Question | Related |
|---|---|---|
| OQ-02 | Does Meta consistently accept the non-strict JSON Schema planning request across objectives and models? One live synthetic scenario has passed. | ADR-002, ADR-012, ADR-027, ADR-029 |
| OQ-03 | Should a second benchmark use an openly licensed public model, and which? | ADR-011 |
| OQ-04 | Does the planner add measurable value over the default plan across objectives? | ADR-003 |
| OQ-08 | How reliably does Muse Spark return a complete, grounded explanation within the 2,000-token allowance? | ADR-009, ADR-028, ADR-029 |

Resolved: **OQ-01** (That Open Components 3.6 API for GlobalId lookup and highlighting; see
ADR-007), **OQ-05** (IfcTester licence; see ADR-004).

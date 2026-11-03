# Changelog

Significant implementation, architectural and delivery-framework changes are recorded here. Entries remain under **Unreleased** until the project owner publishes a release.

## Unreleased

### FIX-002 / T-5 / M2 — Structured Muse Spark review planning (3 November 2026)

- Give objective planning a dedicated 2,000-token completion allowance and low reasoning effort;
  preserve the 500-token cap for other workflows and migrate Chat Completions to
  `max_completion_tokens`. Request a JSON Schema response format without assuming provider strict
  mode, and version the exact planning contract in `planner.v2.md`.
- Record safe response metadata in the budget ledger and distinguish completion-limit failures,
  missing output, refusals, content filters and genuine schema-invalid output. Preserve the 8,000
  input cap, two-call limit, USD 0.10 per-call/review limits and USD 5.00 project allowance; the
  uncached 8,000/2,000 planning reservation at configured Standard rates is USD 0.01850.
- Offline stub tests verify the actual `LiveClient` request body and response diagnostics. No live
  Meta request or paid call was made; provider acceptance and planner quality remain subject to
  VERIFY-009. FIX-002 does not complete T-5 or M2.

### UI-005E / T-7 / M3 — Automatic architectural reel and product-led captions (3 November 2026)

- Add a 7-second autoplay to the Project Home reel, with a Play/Pause control. It pauses on
  hover, keyboard focus and hidden tabs, respects reduced motion, restarts the timer after manual
  navigation and cleans up on unmount. Replace the six scene captions with the owner-supplied
  product copy while keeping the images, order, alt text and Home composition. Slide 6 retains
  its concept-visualisation disclosure.
- Frontend lint, formatting, typecheck, generated-types check and production build pass; all
  **148 tests in 10 files** pass. Local browser checks confirmed the interval, wrap, pauses and
  reduced-motion behaviour. The integrated browser did not reliably honour requested viewports,
  so the 1920 × 1080 and 390 px targets remain unverified. No dependency, backend or paid call
  changed or occurred; owner review is pending and T-7/M3 remain in progress. See
  [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#ui-005e--automatic-architectural-reel-and-product-led-captions).

### UI-008 / T-7 / M3 — Guided AI review with an objective dock (3 November 2026)

- Add explicit all-or-selected confirmed-requirement scope, a custom objective, revision-pinned
  checks, typed AI-failure recovery and persisted run provenance. **Retry AI Review** and
  **Continue without AI** are separate choices; findings remain deterministic, and AI
  explanations remain separately labelled.
- Frontend lint, formatting, typecheck, generated-types check and production build pass; all
  **132 tests in 10 files** pass. Synthetic AI-Off browser checks confirmed no provider request,
  explicit continuation and persisted fallback/mode display. The browser could not expose a true
  1920 × 1080 CSS viewport, so that visual target remains unverified. No paid/live request or
  publication action occurred; owner review remains pending and T-7/M3 remain in progress. See
  [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#ui-008--guided-ai-review-with-an-objective-dock) for
  exact commands, evidence, limitations and rollback.

### AI-007 / T-5.1 / M2 — Explicit AI review policy and provenance (3 November 2026)

- Require an accepted AI plan for objective requests by default; expose typed safe errors instead
  of silently widening a strict request to the deterministic default. Preserve optional fallback
  only when requested, and distinguish it from an explicit choice to continue without AI.
- Pin user-selected check scope to confirmed requirement revisions and persist per-run mode, model
  when known, provider-attempt status, planning outcome, fallback reason and executed checks.
  Historical runs remain readable without fabricated provenance. Add an explicit production Live
  configuration profile; development remains Off by default. This is not a public-deployment
  approval, and the existing UI still needs a continuation control.
- Verification: backend `pytest -q` **637 passed, 1 live test skipped, 1 third-party warning**;
  Ruff check/format, mypy (131 files) and schema export check pass. Frontend lint, format, typecheck,
  generated-types check, **129 tests** and production build pass; existing Vite chunk-size warning
  remains. No live/paid request was made. T-5.1 is verified; M2 remains in progress. The
  continuation UI and public-deployment authentication remain unresolved.

### UI-007 / T-7 / M3 — Project Home introduction beside the reel (2 November 2026)

- Add the owner-supplied introduction to the left of the existing architectural reel and align
  the reel to the right. On narrow screens the text stacks above it; the reel's size, images,
  controls and other page sections are unchanged.
- Frontend lint, formatting, type checks, 128 tests and the build pass; existing dependency/chunk
  warnings remain. Synthetic desktop and narrow browser checks cover layout and carousel
  interactions. The existing 320 px horizontal overflow remains; local screenshots await owner
  visual review. See [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#ui-007--project-home-introduction-and-right-aligned-reel)
  for evidence and rollback. T-7 and M3 remain in progress.

### UI-006B / T-7 / M3 — Human-readable building storeys (2 November 2026)

- Show original storey names in supplied order, with an *Unnamed storey* fallback and compact,
  keyboard-operable details for the full IFC identity. Long names remain available without
  dominating the collapsed list; storey rows do not imply viewer navigation. No backend or
  schema changes.
- Frontend lint, format, typecheck, generated-types check, 128 tests and production build pass;
  existing dependency/chunk warnings remain. Local synthetic browser checks cover desktop,
  390 px and 360 px layouts, details and protected viewer interactions. The mock is not an
  end-to-end backend review; the owner accepted the desktop comparison and mobile after capture. See
  [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#ui-006b--human-readable-building-storeys) for
  evidence and rollback. T-7 and M3 remain in progress.

### UI-005D / T-7 / M3 — Architectural reel and research graphics (2 November 2026)

- Add an owner-supplied six-scene Project Home reel and the two requested README graphics, with
  a concept-image disclaimer, keyboard/touch controls and responsive layout. Frontend checks,
  118 tests and the production build pass; existing dependency/chunk warnings remain. Local
  synthetic browser checks cover 1920 × 1080, 1440 × 900 and 390 × 844. Image pixels were not
  inspected by the model; owner visual review and research-claim verification remain open.
  See [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#ui-005d--architectural-image-reel-and-research-statistics)
  for evidence and limitations. T-7 and M3 remain in progress.
- At the owner's request, centre the reel at half its original width with proportional image
  height; retain accessible controls and responsive reflow without changing other page sections.

### UI-005C / T-7 / M3 — Core product features on Project Home (2 November 2026)

- Add four non-interactive capability cards below the review workflow, with original monochrome
  SVG icons, existing design tokens and a configuration/verification qualification for AI
  interpretation. No backend, API, viewer or application behaviour changes.
- Frontend lint, formatting, typecheck, generated-types check, 112 tests and production build
  pass; existing viewer-dependency and chunk-size build warnings remain. Isolated synthetic
  browser checks cover 1920 × 1080, 1440 × 900, 1024 × 768 and 390 × 844. See
  [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#ui-005c--project-home-core-product-features) for
  measurements, regression evidence and limitations. Owner review is pending; T-7 and M3 remain
  in progress.

### UI-005B / T-7 / M3 — Review workflow cards on Project Home (2 November 2026)

- Add a *How BIM Intelligence works* section directly below *Choose how to begin*: four
  informational, non-interactive cards (Import your model, Validate information, Investigate in
  3D, Interpret with AI) with original inline-SVG isometric line drawings and existing design
  tokens. Each caption maps to current functionality; the AI card notes that availability depends
  on server configuration and that AI output never creates findings. No assets, dependencies, API
  requests or behavioural change.
- Frontend lint, format, typecheck, 111 tests (one new) and the production build pass. Verified
  in headless Edge at 1920 × 1080, 1440 × 900, 1024 × 768 and 390 × 844: 4/4/2/1 columns, equal
  card heights per row, no horizontal overflow. See
  [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#ui-005b--project-home-review-workflow-cards). Branch
  `feature/ui-005b-home-workflows`, uncommitted, pending owner review; T-7 and M3 remain in
  progress.

### UI-005A / T-7 / M3 — Architectural banner on Project Home (2 November 2026)

- Add the owner-supplied architectural banner above the *Project workspace* hero as one
  optimised WebP (2172 × 724, 226 KB, down from a 2.4 MB PNG), shown whole at every width with
  reserved dimensions and alt text that repeats its embedded wording. Owner confirmed public
  redistribution rights. No overlay text, motion, new colours, dependencies or behavioural change.
- Frontend lint, format, typecheck, 110 tests (one new) and the production build pass. Verified
  at 1920 × 1080, 1440 × 900 and 390 × 844 with no horizontal overflow or failed asset request.
  At 390 px the embedded tagline is too small to read comfortably; a narrow-screen variant would
  need separate owner approval. See
  [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#ui-005a--project-home-architectural-banner). Branch
  `feature/ui-005a-home-hero`, uncommitted, pending owner review; T-7 and M3 remain in progress.

### FINAL-UI-001 / T-5, T-7 / M3 — Meta-assisted review interface and Project Home completion (2 November 2026)

- Connect the existing T-5 API client to the Concept C review workspace: an optional review
  objective dispatches to `startObjectiveReview` (blank keeps the standard deterministic review),
  the coverage panel shows the server's actual `plan_source` with an explicit *objective was not
  used* sentence, and an explicit **Explain finding** action renders `source`, `grounding_status`,
  `fallback_reason`, `model` and evidence citations separately from deterministic evidence. No
  explanation is requested automatically; results are cached per session/run/version/finding and
  aborted on selection change. Replay is labelled as recorded, never live.
- Complete Project Home: subtitle *AEC Model Review*, browser-local recent sessions (session and
  run identifiers only, revalidated through the session API), clearer upload confirmation,
  per-document requirement listing and IDS terminology. The one-click synthetic sample was not
  implemented because it needs files outside the approved paths; the page says so.
- Frontend tests grow from 91 to 109; lint, format, typecheck, generated-types check and build
  pass; focused backend API/scenario tests pass (46). Browser verification with `LLM_MODE=off`
  is recorded in [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#final-ui-001--meta-assisted-review-integration-project-home-completion)
  and [EVALUATION.md](./docs/EVALUATION.md#final-ui-001-frontend-integration-verification--2-november-2026).
  Branch `FINAL-UI-001`, submitted for owner review as a pull request; T-5, T-7 and M3
  remain in progress.

### RELEASE-001 / T-7, T-8 / M3, M4 — Synthetic release baseline (1 November 2026)

- Record UI-004A's merge into `main` and verify the existing synthetic single-IFC/IDS workflow in
  the integrated browser, including selection, camera controls, desktop and narrow layouts, and
  explicit session/run reopening. The objective/explanation UI, recent sessions and one-click
  sample remain absent; final UI-001 application work has not started.
- On the clean implementation baseline, pass 616 non-live backend tests, backend lint/format/type
  and schema checks, and all frontend checks including 91 tests and the production build. Rerun
  the isolated synthetic benchmark: TP/FP/FN 15/0/0, precision/recall/F1 1.000, with no network or
  live model calls. The latest hosted main CI run failed before jobs started.
- Reconcile the current documentation, synthetic-fixture attribution and a 180-second proposed
  storyboard without claiming a completed recording, public repository, live BIM workflow or
  integrated clash feature. See [EVALUATION.md](./docs/EVALUATION.md#release-001-offline-verification--1-november-2026),
  [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#release-001--synthetic-baseline-verification) and
  [DEMO_PLAN.md](./docs/DEMO_PLAN.md). T-7/M3 and T-8 remain in progress; the authoritative
  milestone table lists M4 as not started, despite older changelog wording.

### FED-001 / W5 — Two-model federation and clash feasibility experiment (feasibility only)

- Add an isolated feasibility harness under `tests/feasibility/`. It generates deterministic
  synthetic architectural and building-services IFC4 fixtures into the ignored
  `datasets/synthetic/generated/fed001/`, with an independent box-arithmetic oracle. The harness
  gates federation on matching `IfcMapConversion`, CRS, units, engineering frame and manifest
  hashes. It never transforms or re-saves source geometry.
- Run a deterministic A/B comparison with IfcOpenShell 0.9.0 (`opencascade` geometry). Exact B-rep
  selection (`opencascade.brep`) classifies hard intersections and touch/contact. The triangulated
  BVH engine is recorded as a cross-check because it missed coplanar-face overlaps during
  exploration. Mesh-only results are reported as `unsupported`, never promoted. Results are raw
  geometric records keyed by model member, file hash and GlobalId, with
  `professional_action: not_assessed`. They are not `Finding`s.
- Add a Node probe (`webifc_viewer_probe.mjs`) to check that the installed web-ifc 0.0.77 places
  both models in a consistent viewer frame. Add 25 focused tests. The synthetic run and its
  rerun reproduce the same result digest, and the feasibility decision is GO. Reports are written
  only to the ignored `local-private/test-results/final-48h/`. No production API, viewer, schema
  or dependency changes, and no private models were accessed. The mypy override in
  `pyproject.toml` now includes `feasibility.*`.

### T-5 / M0, M2 — Verified AI review path and provenance-checked explanations (1 November 2026)

- Verify the existing objective-to-planner path offline. A whitespace-only objective is now refused
  with 422 before any planner request or run record. Confirmed checks that an accepted AI plan does
  not select are recorded as skipped with an objective-specific diagnostic, rather than a cap
  message. Tests assert the real planner request body, default-plan fallback for invalid plans,
  failed requests and budget refusals, and the reported `plan_source`.
- Harden `POST /sessions/{sid}/reviews/{runId}/findings/{fid}/explanation`. The endpoint verifies
  that the finding belongs to the run, the run to the session and the stored run id matches the
  route id. It also checks the run's requirement revision, confirmation, check identity, rule
  version, source document and pinned model index before evidence is assembled, and holds the
  session lock while it does so. IDS/document requirements need a source; confirmed built-ins
  may omit it, with an API positive-control test using the existing synthetic native-defect
  generator. The endpoint returns 404 `finding-not-found`, 409 `explanation-provenance-mismatch`, or 412
  `model-version-mismatch` for an `If-Match` other than the run's model.
- Add `Explanation.fallback_reason` with a schema validator that keeps `source`,
  `grounding_status`, `model` and the reason consistent. Regenerate the JSON Schema bundle and
  frontend types.
- Add typed frontend API functions `startObjectiveReview` and `explainFinding` with Vitest
  coverage, including rejection of missing, empty, unknown and non-string template fallback
  reasons. No UI component or viewer file changes. Record the frontend integration contract in
  [UI_SPEC.md](./docs/UI_SPEC.md#t-5-meta-assisted-review--frontend-integration-contract).
- Add a shared offline SDK stub (`tests/support/llm_stub.py`), API tests for explanation provenance
  and fallbacks, and a guard that the default configuration opens no non-loopback connection.
- Fix a test-harness defect that made the named live smoke test unreachable: the autouse
  environment-isolation fixture stripped `LLM_MODE` and `MODEL_API_KEY` from every test, including
  `live`-marked ones. Tests marked `live` now keep the owner's configuration and retain their own
  marker, environment and approval-token gates; all other tests stay hermetic. Regression test:
  `tests/unit/test_live_test_isolation.py`. A socket-blocked offline probe with a placeholder key
  confirmed the smoke test now reaches the provider boundary without sending anything.
- Backend: 591 passed, 1 live test explicitly deselected; focused T-5 modules: 67 passed.
  Frontend: 74 tests passed. Backend lint/format/type checks, generated-schema/type parity and
  frontend lint/format/type checks/build passed; offline AI evaluation: 9/9 with zero network
  calls or spend. Existing frontend dependency/chunk warnings remain.
- Record the owner's observed result from one approved live smoke in a side chat on
  1 November 2026: `muse-spark-1.3`, `success`, exact `{"status":"T5_SMOKE_OK"}` response,
  42 input / 0 cached / 293 output tokens, one ledger request, USD 0.00129775 calculated charge
  against a USD 0.002395 reservation. Configured prices have not been checked against Meta's;
  this is not independently verified provider billing. See [EVALUATION §8](./docs/EVALUATION.md#t-5-live-structured-output-smoke-1-november-2026).
- Record R-API-06: the short smoke reply consumed 58.6% of the 500-token output cap, so structured
  explanation headroom needs separately approved verification. No cap or budget was increased.
  Correct current README live-status claims without treating the smoke as live BIM-workflow
  acceptance. This chat did not repeat the smoke or make another paid call. No dependency change,
  commit, push or merge. UI integration and live explanations remain pending; T-5, M0 and M2 remain
  in progress.
### T-3 / M0 and T-7 / M3 — UI-004A viewer corrections (1 November 2026)

- Add distinct Fit model, canonical Reset view and Focus selected actions using verified installed
  viewer APIs; keep zoom/pan recoverable and retain the current approved visual identity.
- Synchronise pointer, finding and application selection; Clear selection removes viewer styling
  without moving the camera. Preserve active issue highlights over neutral selection and reject
  stale asynchronous highlight results.
- Expose observable model-download, geometry-preparation, ready and failed states. Keep desktop
  evidence/findings panels independently scrollable and preserve the narrow single-column layout.
- Record live browser verification at 1920×1080, 1440×900, 1216×735 and 390×844, plus the complete
  frontend validation set and private ignored screenshot evidence in [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md).
- The browser's two IDS findings and the deterministic scenario's additional native finding use
  different configured check sets; no backend review behaviour, API/schema, fixture or dependency
  changed. T-3 remains verified, T-7/M3 remain in progress. The original evidence predates PR #25;
  integration into `main` remains pending.
- Reconcile the existing implementation onto `main` at `a13857c` without changing the merged T-5
  API or FED-001 harness. Correct short-desktop-height scrolling and allow application selection
  to clear while the viewer is preparing or has failed. Fresh integration evidence is recorded in
  [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md#ui-004a-main-integration-verification--1-november-2026).
- FR-VIS-08 and FR-VIS-11 have recorded acceptance evidence. FR-VIS-09 remains in progress:
  the viewer uses a single issue style and its behaviour across finding severities is not yet
  verified. Integration into `main` remains subject to review and merge.

### T-7 / M3 — Final delivery decisions and implementation contracts (1 November 2026)

- Append ADR-021–ADR-025 for bounded federation, deterministic clash analysis, visual integrity,
  Muse Spark boundaries and the conditional hackathon release gate. Add evidence-based, prioritised
  requirements and preserve the existing single-model review contract.
- Document the proposed coordination flow, narrow API/UI boundary, sample-data and private-material
  policy, conditional go/no-go criteria, final 48-hour workstreams and truthful three-minute demo.
- Reconcile the current UI-003 merge status and outdated README/UI instructions without rewriting
  historical decision records. Documentation only: no production code, dependencies, IFC data, live
  API calls, release or submission actions. T-7/M3 and T-8/M4 remain in progress.

### T-8 / M4 — Open-source documentation foundation

- Add root-level contribution, security, support and software-citation guidance based on the
  verified implementation and current pre-alpha status. No application, dependency, test or CI
  changes.
- Record that no private security-reporting channel is verified; do not publish an invented
  contact. Defer a Code of Conduct pending an approved reporting/enforcement route and defer a
  separate third-party notices file pending a complete distribution and asset-licence review.
- Keep the minimal README link update as a separate proposal for owner review. T-8 and M4 remain
  in progress; no release or submission action is taken.

### T-8 / M4 — Third-party notices and version audit (31 October 2026)

- Add [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) after reviewing Python and npm manifests,
  the npm lockfile, installed Python metadata, tracked visual assets and generated web-ifc WASM.
  Record unresolved attribution and licensing evidence explicitly; this inventory is not a
  distribution compliance certification.
- Confirm `pyproject.toml` as the recommended canonical application version (`0.1.0`). The
  backend `__version__` and frontend package also repeat `0.1.0`; the npm lockfile mirrors its
  package version. No root `VERSION` file or CI consistency check is added. No application code,
  dependency, test, README, licence or release changes.
- Record maintainer-documentation gaps as recommendations only. README links remain a proposal for
  owner review. T-8 and M4 remain in progress.

### T-7 / M3 — README project header

- Add project, CI, release and licence branding to the README header, with links to existing
  setup, workflow, technology-stack and documentation sections, plus the requested application
  panel image. No application behaviour, task status or delivery schedule changes; T-7 and M3
  remain in progress.

### T-7 / M3 — UI-003 production Project Home and review workspace

- Replace the bare frontend entry page with a Project Home that creates a session
  (`POST /sessions`), uploads one `.ifc` model and `.ids`/`.md`/`.txt` requirement documents
  through the existing endpoints with explicit uploading/indexed/rejected states, and opens the
  review workspace. Existing sessions can be opened by id; recent sessions and sample projects are
  shown as unavailable because no API supports them.
- Rebuild the review workspace on the owner-approved Concept C v2 direction: application header,
  review bar, model information panel (from `ModelSummary`), dominant `ViewerCanvas` viewport with
  truthful navigation hints, findings register with client-side search/severity filter, review
  coverage, and an evidence inspector that traces Finding → Requirement/check/rule version →
  GlobalId → `ElementRecord`. States for loading, running, completed/partial/failed runs, review
  errors, model-version mismatch (typed `ModelVersionMismatchError`), no executable requirements
  and empty findings are represented explicitly; zero findings are never presented as compliance.
- API client gains `createSession`, `fetchSession`, `uploadModel`, `uploadDocument`,
  `fetchRequirements`, upload-extension classification and `isExecutableRequirement`; version-aware
  reads are unchanged. View state lives in the query string (`session_id`, `run_id`); nothing is
  stored client-side.
- Frontend tests grow from 18 to 54 (API client, Project Home/setup, workspace states and
  selection coordination, app routing, source hygiene). A live browser walkthrough on the synthetic
  fixture (create → upload IFC/IDS → render → orbit/pan/zoom → run review → finding ↔ element →
  return home) and 1920×1080 / 1440×900 / 390×844 captures are recorded in
  [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md). Backend, viewer (`IfcViewer.ts`, `ViewerCanvas.tsx`),
  generated types, schemas, fixtures, dependencies and CI are unchanged. Viewer camera/visibility
  controls, model tree, AI explanation panel and session catalogue are deferred to UI-004. Owner
  review and merge remain pending; see [PR #18](https://github.com/natnew/BIM-Intelligence/pull/18).
  T-7 and M3 remain in progress.

### T-7 / M3 — UI-002 Revision 2 Project Home and desktop workspace prototype

- Extend the isolated UI-002 design prototype with a Project Home concept (new project, quick
  upload, synthetic samples and a proposed recent-session area) and a refined desktop-first review
  workspace. Preserve the approved Concept C v2 palette and clearly label synthetic data and
  non-functional controls.
- Distinguish existing backend session/upload endpoints from frontend capabilities; document
  proposed metadata persistence, session history, sample loading, category visibility, camera
  controls and geometric clashes as unimplemented and separately approval-gated.
- Update the UI specification, append the UI-002 Revision 2 iteration record and make a minimal
  T-7 scope note. All prototype output remains ignored under `local-private/ui-prototypes/ui-002/`;
  production code, backend, viewer, schemas, tests and dependencies are unchanged. Owner review is
  pending; no commit, push or merge is authorised. See [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md).

### T-7 / M3 — UI-002 Concept C v2 prototype

- Refine UI-001 Concept C as an isolated synthetic-only HTML prototype with a dominant model
  viewport, proposed project hierarchy, collapsible finding register and separate evidence/AI
  inspector. Add nine Chrome 156.0.8078.76 screenshots covering model-loaded, finding-selected and
  element-selected states at 1920×1080, 1440×900 and 390×844; outputs remain ignored under
  `local-private/ui-prototypes/ui-002/`.
- One bounded responsive pass replaced the narrow finding table with cards, reduced narrow toolbar
  density, enlarged small evidence text and added native disclosures. Browser checks verified the
  static states/disclosures and no horizontal document overflow at the narrow viewport; no
  production tests or React/viewer changes were made.
- Reference screenshots remain unprocessed under the prior synthetic-only decision; no
  image-derived influence is claimed. UI-002 is proposed pending owner review; UI-003 scope is a
  proposal only. No commit, push or merge is authorised. See
  [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md).

### T-7 / M3 — UI-001 review-workspace concept study

- Produce three owner-reviewable, static workspace prototypes with a shared synthetic IFC-review
  example and local screenshots. Keep all prototype and image outputs under the Git-ignored
  `local-private/ui-prototypes/` path; no production React, viewer, API, schema, test or dependency
  files change.
- Record the weighted comparison and a conditional recommendation in the private concept report.
  The owner selected synthetic-only reference processing, so the four reference collections were
  inventoried by metadata only; no screenshots were opened and no REF-ID influence is claimed.
- Desktop captures use the same Chrome 156.0.8078.76 viewport (1920×1080); supplementary narrow
  captures (390×844) expose clipping/overlap that must be resolved before any implementation
  proposal. No concept is approved, and UI-002 is not authorised. T-7/M3 remain in progress.

### T-7 — Constitution-driven autonomous UI design framework

- Add [UI_CONSTITUTION.md](./docs/UI_CONSTITUTION.md) with binding BIM workflow, spatial context,
  evidence integrity, accessibility, originality, approval and reversibility principles; no layout
  or visual direction is approved.
- Add the [bim-ui-refinement skill](./.github/skills/bim-ui-refinement/SKILL.md) and restricted
  [designer](./.github/agents/bim-ui-designer.agent.md) /
  [implementer](./.github/agents/bim-ui-implementer.agent.md) custom agents. Define progressive
  context loading, three concepts, comparative visual prototypes, a weighted rubric, separate
  owner gates, bounded revisions and supervised time/cost limits.
- Align UI specifications, handling rules, iteration history and agent instructions; extend the
  existing T-7 deliverable links without changing T-7/M3 status or the delivery schedule.
- Record metadata-only reference checks under `GOV-UI-002`: the ignored library uses singular
  `local-private/ui-reference/`; the preferred plural location is absent. Image/provider rights
  remain unverified, so no images were opened. Recommend owner-managed relocation only.
- Propose harness-specific pre-tool path and final changed-file safeguards, but install no hooks;
  preserve `.githooks/pre-commit` secret scanning. No application, viewer, API, generated contract,
  fixture, benchmark, dependency or CI changes; no external API calls, commit or push.
- This establishes the design system only: no UI-001, redesign, measured design scores or
  application/browser verification is claimed. See [UI_CHANGELOG.md](./docs/UI_CHANGELOG.md)
  for boundaries, limitations and rollback.

### Private reference and test data governance

- Preserve the explicit `local-private/` exclusion in [`.gitignore`](./.gitignore); document
  owner-created `bim-models/`, `bim-documents/`, `ui-references/`, `test-results/` and
  `professional-feedback/` subdirectories without adding folders or placeholders.
- Extend the root and frontend agent rules with task-scoped private inspection, no private
  commits/copies, separate owner approval and data rights for LLM transmission, authorised
  publication, synthetic/redistributable public demonstrations, separately labelled AI
  explanations and mandatory security/provenance reviews.
- Prefer `local-private/ui-references/` for owner-supplied visual references. Align the reference
  register, UI verification records and dataset guidance around non-sensitive identifiers and
  authorised design decisions rather than private source content.
- **Security and provenance review `GOV-PRIVATE-001` (30 October 2026):** the owner authorised
  repository organisation and governance only. Inspection was limited to governance documents,
  Git status/diffs and tracked filenames; no private source contents were opened or copied.
  No private data rights or transmission/publication approval were inferred. Storage is
  owner-managed and ignored, not access-controlled by Git; no retention period is imposed, and
  the owner must establish access, rights and retention/deletion arrangements before private use.
  No private data was transmitted, no application behaviour changed, and the T-6 benchmark and
  tracked fixtures remain untouched. Filename review found no tracked private/reference paths;
  the sole BIM/document/image candidate was the existing `tests/fixtures/minimal.ifc`.
  `git check-ignore -v` confirmed all five intended private categories are ignored; fixture and
  benchmark source controls remain unignored, generated T-6 output remains ignored, and protected
  application/benchmark/fixture/dependency/CI path diffs are empty. `git diff --check` passed.

### T-7 — Owner-directed UI design governance framework

- Establish [`docs/UI_SPEC.md`](./docs/UI_SPEC.md) as the evolving UI specification, separating verified behaviour, provisional design principles, owner-approved decisions and open questions without prescribing a new visual style.
- Add [`docs/UI_REFERENCES.md`](./docs/UI_REFERENCES.md) and [`docs/UI_CHANGELOG.md`](./docs/UI_CHANGELOG.md) for owner-supplied references, approval feedback and append-only iteration evidence. Third-party screenshots are to remain in private local storage unless redistribution rights are established.
- Add [`frontend/AGENTS.md`](./frontend/AGENTS.md) with mandatory owner-approval, scope, functional-regression, accessibility, testing, diff-review and no-commit/push/merge guardrails; link the frontend rules from the root [`AGENTS.md`](./AGENTS.md).
- Document a repeatable visual verification, frontend regression and safe rollback process; use existing frontend commands and do not add browser automation dependencies.
- Update the T-7 register and README documentation index. T-7 remains in progress; this framework introduces no visual redesign, no UI-001 scope, and no application behaviour changes.

### T-6 — Benchmark and Evaluation

- Add a deterministic IFC4 benchmark generator with a clean model, defective model, versioned injection manifest, independently checked ground truth, matching IDS, synthetic BEP and objective examples. Keep generated IFC/results ignored and leave the existing minimal fixtures untouched.
- Reconcile the original D01–D14 count with the target of 15–20 positive P0 instances by adding D19; retain D15–D17 as unimplemented P1 exclusions and D18 plus six explicit cases as zero-finding controls.
- Add one-to-one matching by rule id, immutable check id and exact GlobalId set; report duplicates, unmatched predictions, misses, undefined metrics, clean-control false positives and execution coverage separately.
- Add an offline runner for LLM-disabled reviews, byte-identical persisted findings, IfcTester JSON agreement, SHA-256/version metadata and Fake/Replay safety-contract checks. No live Meta request or spend was made.
- Record the 29 October 2026 local result in [docs/EVALUATION.md](./docs/EVALUATION.md): 15/15 TP, 0 FP, 0 FN; precision/recall/F1 1.000; seven clean controls with no false positives; deterministic findings; 14/14 IDS entity agreement; and 9/9 offline AI contract checks. This measures only the labelled synthetic benchmark, not live model performance or general BIM accuracy. Hosted CI evidence remains outstanding.

### T-5 — Meta Muse Spark Integration (offline implementation)

- Add a typed `LLMClient` boundary with network-isolated Fake and Replay clients, response-only recordings, and a Meta Model API `LiveClient` using the existing OpenAI SDK. Live remains off by default and requires an explicit configuration gate.
- Add persistent, cross-process budget reservations and usage reconciliation with configurable Muse Spark Standard prices, USD 0.10 per-call/per-review and USD 5 cumulative application limits, a two-call review cap, 8,000 estimated input tokens, 500 output tokens and zero default retries. These are application controls, not provider billing caps.
- Add objective-based plan selection constrained to unique confirmed immutable check ids; invalid or unavailable AI plans keep the deterministic default.
- Accept Markdown/TXT source documents, produce unconfirmed quote-verified candidates, and require explicit confirmation against an existing confirmed CheckSpec. New IDS criteria are not generated.
- Add grounded per-finding explanations with exact evidence citations and deterministic fallback; explanations remain separate from `findings.json`.
- Add a safe budget-status endpoint, schema exports, offline API/client/budget tests, a gated one-call live smoke test definition and redacted Gitleaks scan tooling. No live request was made and no API spend was measured; M0 capability verification and M2 completion remain open.

### T-4 — End-to-End Deterministic Review Workflow

- Add the versioned native `classification.consistent_by_type` v1.0.0 rule as an explicitly confirmed, parameter-free built-in check, without duplicating IDS 1.0 property, naming or classification-presence checks.
- Bound stable default-plan execution with `MAX_PLAN_CHECKS` and `MAX_TOOL_CALLS_PER_RUN`; record skipped and per-check error outcomes, continue after recoverable errors, and mark skipped, errored or not-applicable coverage as `partial`.
- Add a one-click **Run standard review** action to the existing viewer workspace. It pins the run to the model summary ETag, loads the resulting run/findings through version-aware endpoints and displays per-check coverage.
- Add native-rule, cap/error, API confirmation and LLM-off end-to-end scenario tests, including repeated findings output and model/GlobalId consistency. The task record in [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md#t-4--end-to-end-deterministic-review-workflow) records exact validation evidence; benchmark metrics remain outstanding under T-6.

### T-3 — Interactive 3D BIM Viewer

- Add an on-demand browser-side That Open Components 3.6 viewer for the minimal IFC fixture, with GlobalId-to-fragment resolution, viewer-to-element selection and deterministic finding highlights.
- Connect existing model, review-run, findings and element APIs. Reject runs whose session or model hash does not match the active model; pin model-file and element requests to the summary ETag and recheck the active version after loading.
- Serve the pinned `web-ifc` WASM files and Fragments worker locally. Add finding evidence, element identity and property details, and loading, empty and error states.
- Verify actual browser rendering and both selection directions on the minimal fixture; mocked frontend API and component tests pass. See the [T-3 implementation record](./docs/IMPLEMENTATION_PLAN.md#t-3--interactive-3d-bim-viewer) for evidence and exact validation results.
- Correct the `web-ifc` licence disclosure: version 0.0.77 is MPL-2.0 and is documented as an exception to the repository's permissive-or-LGPL dependency preference; owner review remains required before public distribution.

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

# BIM Intelligence UI Specification

**Status:** Governance baseline; the owner-approved UI-002 Revision 2 visual direction is recorded
in §13, the UI-003 production implementation in §18, and the owner-authorised UI-004A viewer
corrections in §20. Remaining scope (model tree, catalogue, clashes and AI explanation) remains
proposed.
**Status correction (1 November 2026):** On the UI-004A integration branch, §3 and §4 describe the
UI-003 production baseline with the viewer corrections. The UI-002 proposal in §17 is a dated
pre-implementation snapshot; its former statements that Project Home and upload were absent are
not current production status.
**Later correction:** UI-004A merged into `main` through PR #28 at
`cf06328c874258efe8a49d0afa291d9aef278928`. The requested final UI-001 objective, explanation,
browser-local history and one-click sample remain unimplemented; the implementation approval
packet required by the constitution is incomplete. See §21 and
[UI_CHANGELOG.md](./UI_CHANGELOG.md#release-001--synthetic-baseline-verification).
The detailed implementation and browser evidence in §§18 and 20 and `docs/UI_CHANGELOG.md` remain
the evidence record.
**Scope:** Owner-directed interface refinement under T-7, contributing to M3.
**Authority:** The project owner approves visual decisions. This document records verified
behaviour, provisional design principles, approved decisions and unresolved questions separately.

The [UI constitution](./UI_CONSTITUTION.md) supplies binding quality criteria and the conflict
order; it does not prescribe a layout. The [refinement skill](../.github/skills/bim-ui-refinement/SKILL.md)
supplies the bounded design workflow and reusable weighted rubric. Use
[BIM UI Designer](../.github/agents/bim-ui-designer.agent.md) for read-only proposals and
[BIM UI Implementer](../.github/agents/bim-ui-implementer.agent.md) only after separate scope
approval. These development-time roles do not change the application's orchestrator.

## 1. Product and user context

BIM Intelligence is an architectural BIM coordination and information-quality review application.
Its professional users include Architects, BIM Managers and BIM Coordinators preparing or
coordinating an information exchange. They need to compare a versioned IFC model with confirmed
project requirements, inspect deterministic findings in model context and retain traceability from a
requirement to the affected element and its evidence.

The interface must not imply that an AI-generated explanation is a model fact. Only IfcTester or a
registered native rule creates a `Finding`; requirement candidates require human confirmation, and
explanations are separate, grounded interpretations. See [REQUIREMENTS.md](./REQUIREMENTS.md),
[ARCHITECTURE.md](./ARCHITECTURE.md) and [DECISIONS.md](./DECISIONS.md).

## 2. Evidence and decision labels

The labels below apply throughout this document:

1. **Existing verified behaviour** — supported by current source, tests or recorded implementation
   evidence. A historical browser verification is identified as such; it is not a claim that browser
   verification was repeated for this governance change.
2. **Provisional design principles** — constraints and workflow aims for discussion. They do not
   specify an approved visual style, layout or interaction.
3. **Owner-approved design decisions** — only decisions explicitly approved by the project owner
   may appear in §13. Prototype permission does not approve production implementation.
4. **Ideas requiring further discussion** — unresolved visual, interaction and presentation choices.

Current code and CSS are evidence of the implementation, not evidence that its appearance is final.
No reference, design direction, token value or layout in this specification is owner-approved by
implication.

## 3. Primary professional workflows

### Existing verified behaviour

- Use Project Home to create a server session or open an existing session by ID; upload one IFC
  and supported IDS/Markdown/TXT source documents, then open the review workspace.
- Start the deterministic default **Run review** action from the workspace. A session without
  confirmed executable checks remains viewable but cannot run a review.
- Reopen a session and optional review run with the query-string link
  (`?session_id=…&run_id=…`); no recent-session browser history is currently stored.
- Load review data only when the review run belongs to the requested session and active model
  version.
- Inspect the model summary, per-check coverage and findings.
- Select a finding to highlight its affected GlobalId values in the viewer and load an element
  record.
- Select a rendered model element to load its record and select the first matching finding in
  canonical API order.
- Use **Fit model**, **Reset view** and **Focus selected** to control camera framing; clear
  selection independently without an automatic camera move.
- Inspect element identity and property values, including whether a property is inherited.
- See loading, empty, API/version mismatch and viewer error states.

These behaviours are implemented by `App`, `ModelWorkspace`, the version-aware BIM API client and
the viewer; component and API tests cover the described review, state and selection flows. The T-3
browser verification on the minimal fixture is recorded in
[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md#t-3--interactive-3d-bim-viewer); the later
Project Home, upload and workspace browser verification is recorded under UI-003 in
[UI_CHANGELOG.md](./UI_CHANGELOG.md).

### Intended product workflow — not yet fully implemented in the UI

The broader product workflow remains only partly implemented:

1. **Implemented:** create/open a session, upload one `.ifc` and supported requirement material,
   then inspect the version-pinned model, deterministic review, findings and element evidence.
2. **Backend exists; frontend workflow not implemented:** extract narrative candidates with
   verbatim quotes and explicitly confirm them against existing checks.
3. **Backend path is offline-tested; frontend AI objective and plan display not implemented:**
   state an objective and inspect the bounded plan.
4. **Implemented for deterministic review:** run the default review and inspect check coverage;
   live progress streaming is not available in the current synchronous route.
5. **Implemented:** select findings/elements and inspect deterministic evidence in the existing
   viewer.
6. **Not implemented:** export a complete traceable JSON/Markdown report with provenance.

The backend creates unnamed review sessions, accepts one `.ifc` model and supports `.ids`,
`.md` or `.txt` requirement material. IDS specifications become confirmed requirements; Markdown
and text remain untrusted source until separate interpretation and human confirmation. The
frontend does not currently expose candidate confirmation or a user-facing Meta explanation.
Endpoint capability does not establish a complete UI workflow or live provider verification.

## 4. Navigation and workspace information hierarchy

### Existing verified behaviour

The existing React application has a Project Home and a review workspace within one application
shell. Project Home creates or opens a session and guides one IFC/document upload. The workspace
shows model information, a dominant 3D viewport, findings, requirements, review coverage and an
evidence inspector. Desktop uses the recorded three-column layout; narrower layouts stack the
panels. Navigation and session/run deep links use the URL, not a stored project catalogue.

### Owner-approved direction — UI-002 Revision 2

The approved Concept C v2 direction retains its restrained professional styling and colour palette,
while evolving to a desktop-first product with a Project Home and a dominant model viewport. The
static screens in the local UI-002 prototype demonstrate that direction only; they do not establish
production routes, a project catalogue, working upload controls or a persistent project model.

### Provisional design principles

- Keep project/session identity and active model version understandable in the context of a review.
- Preserve a clear relationship between review objective, confirmed requirements, run progress,
  check coverage, findings, selected model elements and report provenance as those capabilities are
  implemented.
- Keep review evidence and model context discoverable without obscuring the task the owner
  prioritises.
- Treat any grouping above as a conceptual information hierarchy, not a prescribed navigation
  system, panel arrangement or page layout.

### Ideas requiring further discussion

- How the owner wants production navigation, project persistence and session-history behaviour
  implemented; the proposed Project Home visual hierarchy is recorded in §13.
- The priority and grouping of review setup, model context, findings and evidence.
- How project, session, model version and review-run identity should appear.
- Whether panel size, position or visibility should be adjustable.

## 5. 3D model viewport

### Existing verified behaviour

- The browser loads the IFC bytes into the That Open Components viewer; the backend remains the
  source of review findings and element data.
- The viewer and its library imports are isolated to `frontend/src/viewer/`.
- GlobalId is the join key between findings and rendered objects. Finding selection resolves
  GlobalIds to viewer-local IDs and applies the deterministic issue highlight; model selection
  resolves viewer-local IDs back to GlobalIds.
- UI-004A adds distinct model fit, canonical isometric reset and selected-element focus actions;
  camera zoom and pan remain recoverable through Fit model.
- Pointer, finding and application selection stay synchronised. Clear selection removes viewer
  selection styling without clearing issue highlights or moving the camera.
- Viewer lifecycle states distinguish model download, geometry preparation, ready and failed.
- The current viewer reports loading and initialisation errors. The review workspace carries the
  pinned model hash and checks the active model version around its API reads.
- The minimal fixture's W-002 finding-to-model highlight and model-to-element selection were
  verified in the browser as recorded in the T-3 implementation evidence.

### Provisional design principles

- Preserve clear model identity and the relationship between selected findings and highlighted
  elements.
- Do not let decoration, overlays or controls conceal model geometry or make selection state
  ambiguous.
- Make viewer loading, empty-geometry and error states distinguishable from a successfully loaded
  model.
- Preserve IFC read-only handling and the existing model-version consistency contract.
- Keep category visibility, hide/show/isolate and controls requiring new viewer/data interfaces
  marked as proposed. Fit, reset and selected-element focus are implemented by UI-004A.

### Ideas requiring further discussion

- Viewport prominence, surrounding tool controls, selection appearance and any additional model
  navigation affordances.
- How the viewport adapts to small screens and how users inspect the model without a pointer.
- Whether the current viewer background, highlight colour and camera framing remain appropriate.

### Proposed model browser and visibility scope

The UI-002 Revision 2 prototype shows a proposed hierarchy of storeys and IFC categories, plus
visibility, hide, show-all and isolate affordances. These are not existing application features.
The current model summary exposes storeys and counts per IFC class, not a complete element
hierarchy; the frontend has no category-visibility interface, and viewer camera controls are
internal to the viewer. A working browser or visibility controls require a separately approved
functional scope and focused viewer/data acceptance criteria.

## 6. Issue register and finding detail

### Existing verified behaviour

The current findings list presents severity, rule ID, a leading element name (or category), and the
expected condition. Selecting a finding exposes its observed and expected values, requirement ID,
rule version and deterministic method. The list exposes the selected item with `aria-pressed`. An
explicit empty state appears when a review returns no findings.

### Provisional design principles

- Keep finding status/severity and rule identity distinguishable from explanatory prose.
- Preserve the exact observed and expected values and deterministic method; do not paraphrase them
  into a stronger claim.
- Keep selected-finding state visibly and programmatically connected to the viewer selection.
- Preserve existing finding identity, ordering and semantics; do not hide results to simplify a
  layout.

### Ideas requiring further discussion

- Which filters, grouping, sorting or search controls are useful to the owner.
- How severity, check outcome and any future finding lifecycle status should be distinguished.
- Whether finding details should be inline, in a side panel, or presented another way.

### Finding domains

The prototype labels the current synthetic examples as information-quality findings and explicitly
marks geometric clash detection as unavailable. The reviewed implementation and task register
provide no geometric clash engine or clash results. Information-quality checks and any future
geometric clash workflow must remain separate in the interface; no clash result, coverage or
capability may be implied until an implementation and evidence source are approved.

## 7. Element properties and evidence

### Existing verified behaviour

The selected-element details show name or IFC type, GlobalId, IFC type, storey and the available
property-set/property values. Inherited property values are labelled. The backend element contract
also contains other indexed information, but the current frontend does not display all of it.

Finding evidence currently includes observed and expected text, requirement ID, rule ID/version,
method, affected element references and severity/category from the generated API contract. The
current frontend does not display a source requirement quotation or fetch/present an AI
explanation. The backend has an explanation endpoint, but the current frontend review data contract
does not include an explanation. The UI-002 prototype's explanation copy is wholly synthetic,
illustrative and disconnected from that endpoint.

### Provisional design principles

- Preserve GlobalId as the element identity used to link API evidence and viewer selection.
- Keep property-set and property names attached to their values, and retain inherited-value
  provenance when shown.
- Display source evidence and model-derived data as distinct kinds of information.
- Keep deterministic evidence authoritative; label any future model-generated explanation
  separately and retain its grounding/citation semantics.

### Ideas requiring further discussion

- Whether classification, container, type, quantity or other indexed attributes should be exposed.
- How large property sets should be navigated, searched or expanded.
- How source requirement quotations and explanation citations should appear when those features
  reach the frontend.

## 8. Review objective, requirements and progress

### Existing verified behaviour

The frontend accepts session and run identifiers to load a review, and can start the standard
deterministic review for a session. It displays run status and per-check coverage, including
diagnostics returned by the API. Review loading and failures have explicit status/alert messages.

### Provisional design principles

- Make it clear which inputs and confirmed checks are in scope for a review.
- Distinguish proposed requirements from confirmed requirements; never imply an unconfirmed
  candidate has been executed.
- Distinguish run-level status from per-check outcomes and incomplete coverage.
- Make version mismatch and review failure explicit; never present them as an empty successful
  result.

### Ideas requiring further discussion

- How a user sets an objective and inspects a proposed plan.
- How extracted requirements and verbatim quotations are confirmed, edited or rejected.
- Whether and how progress is streamed, and which progress detail is useful.
- How to present replay/offline/degraded modes without implying live model behaviour.

## 9. Reporting and export

The project plan describes traceable Markdown/JSON reporting and other future report formats, but
report generation and an export interface are not currently implemented in the frontend.

**Provisional design principles:** any future report workflow should retain traceability from
requirement through check and finding to element, and preserve model/run provenance. Exported
content must not conflate deterministic findings with separately generated explanations.

**Ideas requiring further discussion:** supported formats, report preview, scope selection,
provenance presentation, download behaviour and how failed or partial reviews are represented.

No export format or layout is approved by this specification.

## 10. Design tokens and states

The first table is a snapshot of the existing `frontend/src/index.css`, included to make the
starting point inspectable. These application CSS values are not the approved concept palette.
The owner-approved UI-002 Revision 2 direction retains the separate Concept C v2 prototype palette
below; this does not change `frontend/src/index.css` or approve production token implementation.

| Existing CSS token or rule                  | Current value                                           | Status                       |
| ------------------------------------------- | ------------------------------------------------------- | ---------------------------- |
| `--colour-bg`                               | `#f2f4f6`                                               | Existing implementation only |
| `--colour-surface`                          | `#ffffff`                                               | Existing implementation only |
| `--colour-text`                             | `#202a32`                                               | Existing implementation only |
| `--colour-muted`                            | `#63717b`                                               | Existing implementation only |
| `--colour-border`                           | `#dce2e5`                                               | Existing implementation only |
| `--colour-error-bg` / `--colour-error-text` | `#fdecec` / `#8a1c1c`                                   | Existing implementation only |
| `--colour-accent` / `--colour-accent-soft`  | `#176f65` / `#e3f2ef`                                   | Existing implementation only |
| `--colour-dark`                             | `#19333a`                                               | Existing implementation only |
| `--colour-focus`                            | `#236fd5`                                               | Existing implementation only |
| Font family                                 | System UI stack; monospace stack for `code`             | Existing implementation only |
| Spacing and sizing                          | Primarily literal `rem` values; no shared spacing scale | Existing implementation only |

### Owner-approved Concept C v2 palette

These are the prototype's CSS values retained by the UI-002 Revision 2 approval. They describe the
visual direction, not production CSS tokens or accessibility certification.

| Prototype token | Value | Role |
|---|---|---|
| `--ink` / `--ink-strong` | `#1b2b36` / `#10232e` | Primary and highest-emphasis text |
| `--muted` / `--line` | `#64737d` / `#d7dfe3` | Supporting text and panel boundaries |
| `--paper` / `--surface` | `#f2f5f6` / `#ffffff` | Workspace canvas and cards |
| `--navy` / `--navy-deep` | `#183541` / `#142a35` | Primary actions and dark shell accents |
| `--teal` / `--teal-soft` | `#167c79` / `#e2f2ef` | Selection and primary accent |
| `--amber` / `--amber-soft` | `#be7718` / `#fff2dc` | Warning and high-severity state |
| `--red` / `--red-soft` | `#b44943` / `#f9e9e7` | Error state |
| `--green` / `--green-soft` | `#2f795a` / `#e5f1e9` | Positive state |
| `--blue` / `--blue-soft` | `#2876a2` / `#e8f2f8` | Model-element selection |

Typography, spacing, sizes, borders, motion and component implementation remain subject to a
separate production iteration and accessibility review.

**UI-003 (30 October 2026):** `frontend/src/index.css` now defines these prototype values as
production custom properties (`--ink`, `--teal`, `--amber`, … with `--focus: #236fd5` retained for
focus rings) and keeps the earlier `--colour-*` names as aliases for the unchanged health panel and
viewer styles. Base size is 14 px with a system/Segoe UI stack; no contrast audit has been run.

### Verified component states

The health panel and review workspace expose loading, error, empty and data-bearing states; the
viewer exposes loading, ready and error states. Existing CSS includes hover, disabled, selected,
severity and `:focus-visible` treatments. This inventory does not establish that every contrast,
keyboard or assistive-technology outcome has been audited.

### Provisional token principles

The Concept C v2 prototype palette is owner-approved for this visual direction only. Production
token mapping still needs a separately approved implementation scope. Record semantic intent and
affected states in the iteration entry and verify readable contrast, focus visibility and
consistency. Typography, scales, spacing, sizing, radii, elevation and motion remain open.

## 11. Responsive layout and accessibility

### Existing verified behaviour

The current CSS caps the application width at `90rem`, uses fluid page padding, and stacks the model
and review panel at a `40rem` breakpoint. Existing controls use labels and native buttons, the
finding list uses pressed-state semantics, and several asynchronous states use `status` or `alert`
roles. The stylesheet includes a visible `:focus-visible` outline.

These facts describe current implementation only. The existing component tests cover important
loading, empty, error, review and selection paths, but do not constitute a complete responsive,
contrast, keyboard or screen-reader audit. Keyboard access to 3D model selection in particular
requires explicit verification.

### Provisional design principles

- Keep information usable at narrow widths and browser zoom without requiring hidden pointer-only
  interactions.
- Use a desktop-first composition for design review, retaining a deliberate narrow adaptation
  rather than shrinking a dense desktop workspace or clipping panels.
- Preserve semantic headings, labels, lists, descriptions and status announcements.
- Maintain visible keyboard focus and readable text/background contrast.
- Provide an accessible way to understand and operate any interaction introduced by an iteration;
  document limitations where the 3D viewer cannot provide an equivalent interaction.

### Ideas requiring further discussion

- Production breakpoint and zoom acceptance beyond the UI-002 prototype review sizes of
  1920 × 1080, 1440 × 900 and 390 × 844.
- Keyboard alternatives for model selection and accessible descriptions of highlighted geometry.
- Required contrast target, screen-reader support matrix, reduced-motion policy and acceptance
  criteria for an accessibility audit.

## 12. Behaviour protected during redesign

The following are regression boundaries, not optional design preferences:

1. Preserve generated API contracts and do not manually edit generated TypeScript schema files.
2. Preserve existing review initiation/loading and version-aware reads, including session/run/model
   hash checks, ETags and explicit mismatch errors.
3. Keep the IFC read-only.
4. Preserve viewer rendering and the GlobalId mapping in both directions.
5. Preserve finding-to-model highlighting, model-to-finding selection and element inspection.
6. Preserve finding severity, identity, method, observed/expected evidence, requirement/check
   references and rule version.
7. Preserve property values and inherited-value provenance.
8. Preserve deterministic finding semantics, check coverage and status meaning. Do not present an
   AI explanation as a `Finding`.
9. Preserve loading, empty, error and degraded states; do not turn an error into a success-shaped
   empty screen.
10. Preserve keyboard access, semantic structure, focus visibility and readable contrast; add
    interaction-specific tests when an iteration changes an interaction.
11. Do not remove functionality to simplify presentation or change API/backend behaviour as part of
    a visual-only iteration.

The owner may propose functional scope separately. If a visual request requires a functional,
architectural, schema, API or dependency change, stop and request explicit approval before changing
that scope.

## 13. Owner-approved design decisions

### UI-002 Revision 2 — 30 October 2026

The owner approved this **visual direction and one isolated prototype iteration**, not production
implementation:

- Retain Concept C v2's restrained styling and prototype palette listed in §10.
- Make the IFC model the dominant desktop working surface; improve navigation discoverability and
  technical-information presentation.
- Add Project Home concepts for new project setup, quick upload and synthetic sample exploration.
- Treat desktop as the primary design target and show a responsive narrow adaptation.
- Keep project/session catalogue, model-category visibility, hide/show/isolate, geometric clash
  detection and new upload/session UI capabilities explicitly proposed until separately approved.
- Maintain information-quality findings separately from any future geometric-clash workflow.

No reference screenshots were inspected; no REF-ID influence is claimed. This approval does not
change production routes, backend/API/schema/viewer behaviour, dependencies, UI-003 scope or delivery
status.

### UI-003 — 30 October 2026

The owner explicitly approved **production implementation** of the Concept C v2 / Revision 2
direction in the existing React application, bounded to the frontend file scope in §18. The
approval excludes the BIM validation engine, backend schemas, `IfcViewer.ts`, `ViewerCanvas.tsx`,
generated types, fixtures, dependencies, CI, credentials and deployment. The implemented result and
its deviations from the prototype are recorded in §18 and in the UI-003 entry of
[UI_CHANGELOG.md](./UI_CHANGELOG.md). T-7 and M3 remain in progress.

## 14. Open visual questions

The following remain open for owner judgement; the approved prototype direction does not settle
production interaction or implementation:

- Which software, product or project references should be studied, and which specific interaction
  or visual feature matters in each?
- Which Project Home metadata and review-workspace hierarchy should be persisted in a production
  project/session model?
- Which property, finding, requirement and provenance details need to be immediately visible?
- Which production typography, spacing and component-state tokens should be adopted from the
  prototype palette?
- What responsive viewport range and accessibility acceptance criteria should govern iterations?
- What reporting formats and report-preview workflow should be prioritised?

Record references and feedback in [UI_REFERENCES.md](./UI_REFERENCES.md). Record each authorised
implementation iteration and its evidence in [UI_CHANGELOG.md](./UI_CHANGELOG.md).

## 15. UI change-control process

For exploratory design before implementation, use the skill's sequence: reference inventory ->
professional workflow analysis -> three alternative concepts -> comparative visual prototype ->
evaluation -> owner selection. Analysis and proposals may be autonomous within the agreed
checkpoint; application edits may not. A read-only chat wireframe is not an implemented viewer.
An isolated rendered prototype needs separate output/path approval and must not modify application
source. Concept selection alone does not grant implementation approval.

Use the [constitution's checkpoints](./UI_CONSTITUTION.md#3-execution-boundary-and-checkpoints),
budgets, revision limits and stop conditions before following the implementation sequence below.
The [weighted rubric](../.github/skills/bim-ui-refinement/SKILL.md#weighted-evaluation-rubric)
compares professional BIM usability (25%), spatial clarity (20%), visual refinement/originality
(20%), evidence integrity/interaction clarity (20%), accessibility/responsiveness (10%) and
feasibility (5%). Scores require comparative evidence and explicit limitations, not invented
measurements, and cannot override a protected invariant or owner approval.

1. **Owner supplies a reference or design objective.**
2. **Agent proposes** a small, bounded implementation and identifies affected files, protected
   behaviour and checks.
3. **Owner approves the scope.** No visual change begins before this approval.
4. **Agent implements only the approved change**, on a separate iteration branch from the latest
   approved baseline.
5. **Agent runs appropriate checks and captures before/after visual evidence** using the protocol
   below; it records functional and accessibility regression results.
6. **Owner reviews the result** and decides whether to approve, reject, revise or revert it.
7. **Approved work is recorded** in `UI_CHANGELOG.md` and significant merged work is summarised in
   the root `CHANGELOG.md`.
8. **Commit, push and merge occur only with project-owner approval.**

### Visual verification protocol

No browser automation is currently configured in the frontend package; its declared test runner is
Vitest. Use a manual, repeatable check until an automation change is separately approved:

1. Use a fixed browser viewport of **1920 × 1080** for the primary before/after capture. This
   matches the existing demo-plan recording size; it is a verification condition, not an approved
   target layout. Add a narrow viewport capture if the approved scope affects responsive behaviour;
   record its dimensions in the iteration entry.
2. Use the committed `tests/fixtures/minimal.ifc` and `tests/fixtures/minimal.ids` through Project
   Home's existing session and upload workflow. Record the fixture/model hash, browser
   name/version, and session/run IDs in the private evidence record so the selection state can be
   repeated. Do not copy fixture or private model bytes into a prototype or evidence directory.
3. Load the same review run and wait for the viewer and findings to finish loading. Capture an
   unselected baseline, then select the IDS FireRating finding for W-002 (GlobalId
   `0QWMtUzsnUUONCUGc8Sqsa`) and capture the highlighted model and details. Also exercise selection
   from the model where the approved scope can affect that path.
4. Save private before/after evidence in the owner-managed, git-ignored
   `local-private/test-results/`, or an owner-approved private store outside the working tree.
   Owner-supplied visual references preferably belong in `local-private/ui-references/`. Record
   only non-sensitive evidence/reference identifiers or neutral paths and the tested
   browser/viewport in `UI_CHANGELOG.md`; keep private project names, model-derived facts and raw
   feedback out of tracked records unless publication is authorised. Private materials must never
   be copied into tracked directories. Inspection and any LLM transmission require the separate
   authorisations and applicable rights defined in [AGENTS.md](../AGENTS.md).
5. Inspect alignment, clipping, legibility, selection/error states and the relevant keyboard/focus
   behaviour at the fixed viewport. Compare against the approved objective and reference—not a
   presumed redesign target.
6. If a fixture, session, browser or viewport differs between captures, record the difference; do
   not present the images as a controlled comparison.

### Regression verification

For frontend changes, use the existing scripts from `frontend/`:

```powershell
npm run lint
npm run format:check
npm run typecheck
npm run types:check
npm test
npm run build
```

The package has `types:check` and `types:generate`, not `npm run types`. `npm run format` is a
write-mode Prettier command over the frontend tree; use it only when its full formatting diff is
within the approved scope. `format:check` is the non-mutating check. Add or run focused Vitest and
React Testing Library coverage for affected interactions. Run the full list when scope warrants it;
record exact commands and results rather than claiming checks that were not run.

Verify, as applicable to the change:

- Model loading and navigation.
- GlobalId selection and finding-to-model highlighting.
- Model-to-finding selection and property inspection.
- Review initiation and per-check coverage.
- Model-version mismatch handling.
- Loading, error, empty and degraded states.
- Keyboard operation, focus visibility, semantic announcements and readable contrast.

The frontend package currently does not configure Playwright or another browser automation tool.
Do not install dependencies or add automation without separate owner approval.

### Rollback

If the owner rejects an iteration or a regression cannot be resolved within its approved scope,
stop the change and agree whether to revise or revert it. Prefer a new revert commit or restore only
the specific files changed by that iteration to the latest approved baseline. Inspect the worktree
and diff first; preserve unrelated user changes. Do not use destructive reset/checkout operations
against unrelated work. Record the decision, affected files and rollback method in
`UI_CHANGELOG.md`.

## 16. Optional Copilot safeguards — proposal only

**Inspection, 30 October 2026:** `core.hooksPath` resolves to `.githooks`. Its existing
`pre-commit` invokes `scripts/secret_scan.py --staged`, preferring the repository virtual
environment. No repository `.github/hooks/` configuration was found. Git hooks and Copilot tool
hooks are separate mechanisms. Do not replace, bypass or alter the secret-scanning hook.
User-profile hook configuration was not inspected; no absence outside this repository is asserted.

The proposed safeguards below require separate owner approval; **none is installed by this
framework**:

1. **Pre-tool path guard:** accept a reviewed iteration packet containing the baseline and exact
   allowed paths. Before any mutation, resolve paths against the repository root, canonicalise
   case/separators on Windows, resolve symlinks/junctions and reject escapes, traversal, unexpected
   renames/deletes and edits to the guard/approval packet itself. Inspect every target in a
   multi-file edit. Unknown tool/input forms must deny or request approval, not silently allow.
   Shell execution can bypass edit-tool path checks: deny general shell mutation, nested shells,
   redirects and opaque scripts; separately allow only reviewed validation commands, with their
   known output paths and approval. A path-only edit hook is not a shell sandbox.
2. **Changed-file scope check:** compare the approved baseline and initial dirty/untracked
   inventory with final staged, unstaged, renamed, deleted and untracked paths. Distinguish
   pre-existing owner work from this iteration; report unexpected paths without reverting them.
   Check after mutation and before completion. A post-tool check detects an escape but cannot
   undo an already completed side effect; it complements rather than replaces the pre-tool guard.
3. **Compatibility and approval test:** validate the actual Copilot host/version, event names,
   stdin schema, tool names, permission response and Windows command runner before installation.
   VS Code Copilot Chat documents `PreToolUse` / `PostToolUse`; the active Copilot SDK-backed
   surface must be checked for its own `preToolUse` support and configuration contract. Do not
   paste VS Code JSON into a CLI/SDK host and assume it works. Codex and Claude have different
   lifecycle/permission contracts. No portable hook file is asserted here.
4. **Acceptance before enablement:** owner reviews the guard and scripts, then tests allowed edits,
   blocked backend/generated/viewer paths, traversal/junctions, multi-file edits, shell bypass,
   malformed input, denied writes, timeouts and changed-file detection in the chosen harness.
   Record observed blocking behaviour and known limitations; keep secrets/private contents out
   of logs. Preserve the existing Git secret scan throughout.

Tool aliases and prompt instructions do not enforce an allow-list. Until a compatible guard is
approved and tested, use supervised tool approvals, small explicit scopes and final diff review.
Do not advertise prompt budgets as hard timeouts or these proposals as installed protection.

## 17. UI-002 Revision 2 — proposed workflow and acceptance criteria

**Historical snapshot:** this section records the UI-002 prototype and production state before
UI-003 was implemented on 30 October 2026. Rows that say Project Home, upload, recent sessions or
sample routes are absent describe that earlier state, not the current production baseline.
UI-003's current behaviour is recorded in §18; later UI-004A camera and selection behaviour is
recorded in §20 and the append-only UI changelog.

This owner-authorised prototype revision expands the visual design, not production functionality.
The Project Home and Review Workspace screens are static synthetic examples. Candidate functional
requirements below are proposals, not adopted `FR-*` requirements or approval to implement them.
The capability column is the historical UI-002 baseline; UI-003, UI-004A and FED-001 later added
the production and feasibility evidence described in §§18, 20 and 21.

### Proposed interaction contract

| Interaction | Existing production capability | UI-002 Revision 2 prototype | Further work needed |
|---|---|---|---|
| Project Home / workspace navigation | No Project Home route; the current frontend opens the health panel and workspace. | Local links navigate between static files. | Add an application route and preserve session/run/model-version state. |
| Create a project/session | `POST /sessions` creates an unnamed session; the frontend does not call it. | New-project fields are local-only; continuing changes the prototype screen only. | Wire session creation; named metadata needs an approved data/API contract. |
| IFC and requirement upload | Backend endpoints accept `.ifc` and `.ids`/`.md`/`.txt`; current frontend has no upload client or form. | Browser selects a filename and checks its extension only; no bytes are read or sent. | Add client workflow, server validation/error handling and session-safe retries. Do not invent transfer percentages; no progress stream is evidenced. |
| Narrative requirement material | `.md`/`.txt` are stored as untrusted source; they create no requirements before separate interpretation and explicit confirmation. | Copy states this distinction. | Preserve source provenance and confirmation controls if a later workflow is approved. |
| Synthetic sample route / recent sessions | No sample catalogue or sessions-list endpoint is exposed. | Pavilion opens a static, synthetic preview; recent sessions are visibly marked proposed. | Provide a curated sample source and/or session-list capability before presenting prepared or recent work as available. |
| IFC hierarchy and category visibility | Model summary exposes storeys and counts per IFC class; no full element-tree or visibility UI is exposed. Viewer selection exists, but camera controls are internal. | Storeys/categories and disabled visibility actions are illustrative. | Define element-tree data and a viewer interface for visibility, hide/show, isolate and focus; test selection/highlight consistency. |
| Camera navigation | Viewer renders and supports selection/highlighting; camera controls are not exposed through the workspace interaction API. | Orbit, pan, zoom, fit and focus controls are disabled mock controls. | Expose and test camera operations through an approved viewer scope. |
| Finding selection / evidence | Production supports finding-to-model highlight, model-to-element inspection and deterministic evidence. | Three labelled preview states use the same synthetic examples as UI-002 v2. | Preserve existing GlobalId and model-version contracts when refining the production layout. |
| Finding search/filter and collapse | No register search/filter or docked-panel collapse interaction is exposed in the current frontend. | Search/filter and inspector-collapse affordances are labelled illustrative; native disclosure controls work locally. | Implement and test keyboard-operable controls and persistence of selected evidence. |
| Geometric clashes | No geometric clash engine or clash results are evidenced. | The register distinguishes information quality from unavailable geometric clashes. | Separate approval, engine, result contract and evaluation before showing any geometric clash result. |
| AI explanation | The backend has an explanation endpoint; current frontend review data does not fetch or present it. | Copy is synthetic and clearly labelled illustrative, not model-generated evidence. | Connect only after approved data/state design; preserve grounding and label explanations separately from Findings. |

### Proposed functional requirements — owner approval required

These identifiers organise design discussion only; they are not additions to `REQUIREMENTS.md`.

1. **UI-PROP-HOME-01 — Project Home and session start.** Provide a clear new-session entry path
   without requiring users to enter a session ID. If the interface accepts a project name or
   metadata, state whether it is transient or persisted; persistence requires a separately approved
   API/schema decision because the current create-session endpoint accepts no such fields.
2. **UI-PROP-HOME-02 — Upload and validation.** Accept only the backend-supported extensions,
   explain IDS versus narrative-document semantics, expose server validation and recoverable
   errors, and never describe local filename recognition as successful upload or IFC validation.
   With the current synchronous route, show an honest in-progress/indeterminate state rather than
   a fabricated byte percentage.
3. **UI-PROP-HOME-03 — Recent sessions and samples.** Do not show unavailable history or a
   prepared sample as live. Add a real source for recent sessions and synthetic sample inputs/review
   runs before enabling those routes.
4. **UI-PROP-BROWSER-01 — Model tree and visibility.** Show only hierarchy data supported by a
   reviewed contract; connect visibility controls to the viewer and keep them independent from
   Finding filters and selected-element/highlight state.
5. **UI-PROP-FINDINGS-01 — Investigation register.** Support keyboard-accessible search/filter,
   severity, check status, element identity and coverage. Keep information-quality findings and
   any future geometric-clash results separately typed and labelled.
6. **UI-PROP-EVIDENCE-01 — Evidence and explanation.** Preserve requirement/check provenance,
   observed/expected values, GlobalId and model version. Present any connected AI explanation and
   human recommendation separately from deterministic evidence and the `Finding`.

### Prototype acceptance criteria

The static Revision 2 prototype is reviewable when all the following are true:

- Project Home shows distinct new-project, quick-upload and synthetic-example entry routes plus an
  explicitly proposed recent-session area; each route shows its own screen without leaving the
  landing screen visible behind it.
- New-project fields are described as local-only, and the unnamed-session API limitation is
  visible.
- The upload page presents supported extensions, local file-selection feedback, transfer/
  validation/not-started states and representative errors without claiming any request ran.
- IDS and narrative-document semantics are distinguishable.
- The selected synthetic sample can navigate to the matching synthetic workspace example; no
  client data or real model output is shown.
- The workspace includes loaded, Finding-selected and browser/evidence-selected views; the IFC
  illustration and repeated example data are identical to UI-002 v2.
- The workspace gives geometry the largest working area, keeps model version/status visible,
  separates model visibility from review filters, shows partial review coverage and states that
  geometric clash detection is unavailable.
- Deterministic values, source/check references, GlobalId and model version are distinguishable
  from illustrative AI explanation copy.
- The prototype has desktop captures at 1920 × 1080 and 1440 × 900 and a narrow adaptation at
  390 × 844; this is design evidence, not a responsive implementation or WCAG audit.

### Proposed UI-003 scope — not authorised

> **Superseded (30 October 2026):** the owner subsequently authorised UI-003 with a wider frontend
> file scope than listed here; the implemented scope is recorded in §18. This proposal text is kept
> unchanged as the historical record.

For a future owner-approved first implementation slice, limit the initial scope to a Project Home
shell and the existing unnamed-session / supported-upload APIs, with exact candidate files:

- `frontend/src/App.tsx`
- `frontend/src/components/ProjectHome.tsx` (new)
- `frontend/src/components/ProjectHome.test.tsx` (new)
- `frontend/src/components/ModelWorkspace.tsx`
- `frontend/src/components/ModelWorkspace.test.tsx`
- `frontend/src/api/bim.ts`
- `frontend/src/api/bim.test.ts`
- `frontend/src/index.css`

Use the existing session/model/document endpoints and generated API types; do not hand-edit
generated types. This first slice must not persist a project name, invent upload progress, add a
sample catalogue/session list, expose an incomplete model tree, add viewer visibility/camera
controls, implement geometric clashes or fabricate a frontend explanation. Those require separate
functional/architecture approval and potentially additional file scopes. The illustrative estimate
is **3–5 engineering days** for the focused frontend/API-client slice, including errors and
regression evidence; model visibility/navigation and catalogue work are excluded. Principal risks
are upload/session recovery, version consistency, stale partial reviews, accessible file input and
viewer selection/highlight regression.

No UI-003, backend change, model data exposure or production implementation is approved by this
proposal.

## 18. UI-003 — implemented design and remaining proposals

**Status:** implemented on branch `feature/ui-003-production-integration` from baseline `a3e701f`
(30 October 2026); [PR #18](https://github.com/natnew/BIM-Intelligence/pull/18) is open for owner
review. Browser evidence is recorded in
[UI_CHANGELOG.md](./UI_CHANGELOG.md). This section describes the application as built; it does not
mark T-7 or M3 complete.

**Status correction (1 November 2026):** PR #18 has since merged into `main`. The branch and
pending-review wording above is the original implementation snapshot; the UI-003 behaviour and
evidence remain as recorded, and T-7/M3 remain in progress.

### Implemented (verified by Vitest/RTL tests and a live browser walkthrough)

| Area | Behaviour | Source |
|---|---|---|
| Project Home | Product identity, backend status, **New review** (`POST /sessions`), **Open an existing session** (`GET /sessions/{id}`; routes a `created` session into setup and a `model_ready` session into the workspace) and an explicit *not available* card for recent sessions / sample projects. | `components/ProjectHome.tsx` |
| Review setup | Four-step sequence: session created → IFC model (`POST /sessions/{id}/model`, `.ifc` only) → requirements (`POST /sessions/{id}/documents`, `.ids`/`.md`/`.txt`) → open workspace. Shows uploading / indexed / rejected states, the returned `ModelSummary`, executable-requirement counts per IDS and the "narrative source only" distinction. Unsupported types (RVT, NWD, PDF…) are rejected client-side before any request and server rejections are shown verbatim. No transfer percentage is invented. | `components/ReviewSetup.tsx`, `api/bim.ts` |
| Application shell | Header with brand, Project Home / Review workspace navigation, session chip and the **Run review** action; query-string view state (`?session_id=&run_id=`) so a refresh reopens the same session and run with no client-side storage. | `components/AppHeader.tsx`, `state/useAppLocation.ts`, `App.tsx` |
| Workspace layout | At the current 14 px root font size, ≥ 980 px uses the fixed-height three-column grid (model information 15 rem · viewport + findings · requirements/coverage/inspector 20 rem) with the viewport as the largest surface and side panels scrolling internally. 785–979 px uses two columns with model information below. ≤ 784 px uses one column (viewport → findings → requirements/coverage → inspector → model information). UI-004A verified no horizontal overflow at 390 px. | `index.css`, `components/ModelWorkspace.tsx` |
| Model information | Project, schema, model version, indexed instance total, storeys in file order and instance counts per IFC class (top 8 + disclosure) from `ModelSummary`; explicit note that no element tree or visibility control exists. | `components/ModelBrowser.tsx` |
| Viewport | UI-003 established truthful navigation hints, **Clear selection** and viewer error reporting. UI-004A adds **Fit model**, canonical **Reset view**, **Focus selected**, synchronised selection/highlighting, and observable download/preparation/ready/failed states; see §20. | `components/ModelWorkspace.tsx`, `viewer/IfcViewer.ts`, `viewer/ViewerCanvas.tsx` |
| Findings register | Rows show severity, method, element name, requirement id, rule id, IFC type/storey, GlobalId (+ *n more*), observed → expected; `aria-pressed` selection; keyboard-operable (Tab/Enter verified). Client-side search and severity filter hide rows only and announce "Showing n of m"; canonical order and records are untouched. Geometric clashes labelled *not available*. Empty state states that no findings ≠ compliance. | `components/FindingRegister.tsx` |
| Review coverage | Run status chip, checks executed/passed/failed/not run (error · skipped · n/a), findings count, plan source, per-check results with diagnostics, and an alert when the run's `input_manifest.model_hash` differs from the active model. | `components/ReviewCoverage.tsx` |
| Evidence inspector | Finding evidence (id, observed/expected, requirement, check, rule + version, category, model version, affected elements) and the source `Requirement` (title, statement, origin/status/revision, verbatim quote with location when present; otherwise an explicit "no narrative quotation" note). Selected element (`ElementRecord`: GlobalId, type/predefined type, storey, object type, type object, container, classifications with inherited flag, property/quantity sets with inherited provenance) and linked findings. A fixed note states that AI explanation is not connected. | `components/EvidenceInspector.tsx` |
| Review execution | **Run review** → `POST /sessions/{id}/reviews` with `If-Match` and no objective body → `loadReviewWorkspace`. States: none, loading run, running, ready (completed/partial/failed/interrupted), **model-version mismatch** (typed `ModelVersionMismatchError`; model stays viewable, stale findings refused), error (problem detail shown, model stays viewable), and **no executable requirements** (Run review disabled, "model view only"). Requirements documents can also be added from the workspace. | `components/ModelWorkspace.tsx`, `api/bim.ts` |

### Differences from the Revision 2 prototype

- No project browser tree, category checkboxes or hide/show/isolate controls. UI-004A adds
  operational Fit/Reset/Focus actions; orbit, pan and zoom remain pointer gestures with truthful
  instructions rather than inert controls.
- The evidence inspector uses stacked native `<details>` sections instead of Finding/Element/
  Requirement tabs; requirement details are nested under the finding.
- Review coverage sits in the right column above the inspector rather than inside the empty
  inspector state; the requirements panel with an upload control is new.
- The synthetic sample route, recent-session list and project-name field are omitted or shown as
  unavailable; sessions are unnamed server objects.
- "Upload / replace IFC" is available only in the setup sequence, not in the workspace header.
- Prototype illustrative AI explanation copy is replaced by a fixed *not connected* note.

### Remaining scope beyond UI-004A (separate approval and, where noted, viewer/API scope required)

1. **Viewer interface:** orthographic/perspective toggle, direct keyboard camera navigation and an
   accessible description of highlighted geometry remain unimplemented.
2. **Visibility**: per-class or per-storey hide/isolate requires a viewer API and an element
   listing beyond `ModelSummary`.
3. **Model tree**: needs an elements-by-container/class endpoint; not derivable from `ModelSummary`.
4. **Replace IFC from the workspace** and explicit handling of the resulting version change.
5. **Explanation panel**: connect the existing explanation endpoint with grounding status and
   separate labelling (ADR-009).
6. **Session history / sample catalogue**: requires new API capability.
7. **Accessibility audit**: contrast measurement, screen-reader pass and 200 % zoom check; only
   keyboard activation of finding rows and camera buttons, plus focus visibility, were exercised.

### T-5 Meta-assisted review — frontend integration contract (pending)

Status: **not connected in the UI.** The offline-tested backend path and typed API client were
merged into `main` via PR #26; no component renders them yet. UI-004A changes the workspace and
viewer independently of this pending T-5 UI integration. Apply the following changes only at the
T-5 integration stage, keeping the approved Concept C v2 layout:

1. **Objective input** (`ModelWorkspace.tsx`, review controls beside **Run review**): add an
   optional, labelled `<textarea>` named *Review objective (optional)* with
   `maxLength={MAX_REVIEW_OBJECTIVE_LENGTH}` and helper text stating that the objective can only
   narrow the confirmed checks and never changes their criteria. In `runReview()`, call
   `startObjectiveReview(sessionId, objective, signal)` when the trimmed objective is non-empty.
   Otherwise keep `startStandardReview(sessionId, signal)` unchanged. Both feed the existing
   `loadReviewWorkspace` path and handle `ModelVersionMismatchError` in the same way.
   `startObjectiveReview` throws `ApiError` before any request for a blank or over-long
   objective; show that message inline.
2. **True plan source** (`ReviewCoverage.tsx`): the existing *Plan source* row already renders
   `run.plan_source` (`AI-selected plan` / `Deterministic default`). Keep it as the only plan
   label. When an objective was submitted and the run reports `default`, add one sentence: *The
   objective was not used; the deterministic default plan ran.* The cause may be AI off, a budget
   or call limit, a failed request or a rejected plan. Checks an AI plan did not select are
   `skipped` with the diagnostic *Not selected by the objective-specific review plan.*, and that
   run is `partial`. Present this as narrowed scope, never as a pass.
   `plan_source=llm` means a model-produced plan was accepted, not that a live request occurred.
   In Replay mode, explicitly label it *Recorded AI-selected plan (Replay; no live call)*.
3. **Explanation request** (`EvidenceInspector.tsx`, replacing the fixed *not connected* note when
   a finding is selected): add an explicit **Explain finding** button. It must never fire
   automatically, because each request may spend part of the per-run call allowance. It calls
   `explainFinding(sessionId, run.id, finding.id, modelEtag, signal)`, where `modelEtag` is the
   active model's quoted SHA-256. Disable the button with a version note when
   `runModelHash !== activeModelHash`; the server also refuses that request with 412. Render
   loading, error (`ApiError` detail; 404/409/412 never shown as an explanation) and success
   states. Cache results per `(sessionId, run.id, modelEtag, finding.id)` and abort on selection
   change. Ignore late responses whose selection/version identity no longer matches.
4. **Provenance labels**: render the explanation in its own section, below the deterministic
   evidence and visually distinct from it.
   - When `source === 'ai_generated'`, label it *AI interpretation · `{model}` · grounding
     passed*. In Replay mode add *Recorded response (Replay; no live call)*. Use the existing
     health response's `llm_mode` for the current mode, but do not use it as proof of a historical
     run's mode: the current contracts do not persist Live/Replay provenance per run or
     explanation. Never label `fake-model` as Meta or infer live verification from `source`.
   - When `source === 'deterministic_template'`, label it *Deterministic template · AI not used*
     and show `fallback_reason` text:
     - `ai_disabled`: AI is off.
     - `unsupported_evidence`: this finding cannot be grounded safely, for example a
       multi-element finding.
     - `budget_limit`: the spend or call limit was reached.
     - `ai_request_failed`: the AI request failed.
     - `ai_output_invalid`: the AI response was invalid.
     - `grounding_failed`: the AI text cited facts outside the evidence and was discarded.
   - List `citations` (GlobalId, requirement, rule, expected, observed) as links back to the
     deterministic evidence. Never style or count an explanation as a `Finding`.
5. **Call allowance**: the planner and explanations share the per-run cap of
   `LLM_MAX_CALLS_PER_RUN` (default and ceiling 2). A dispatched live planner request consumes
   one call before the first explanation; Off/Replay or rejection before reservation consumes
   no live allowance. Provider failures still count and are charged conservatively when usage
   is unavailable. Requests beyond the remaining allowance return `budget_limit` templates.
6. **Tests** (Vitest + React Testing Library): objective vs standard dispatch; blank optional
   input selects the standard review, while a direct blank `startObjectiveReview` call sends
   no request; *Plan source* for `llm` and `default`; Replay is not labelled Live; explanation
   success with each label; a 412 surfaced as a version error; no explanation request without
   a user action; selection/version changes cannot display stale explanations.

The API functions, generated `Explanation`/`ReviewRequest` types and their tests are in
`frontend/src/api/bim.ts`, `frontend/src/api/generated/types.ts` and
`frontend/src/api/bim.test.ts`.

## 19. Day 7 coordination mode — conditional proposal

The existing single-IFC Project Home and review workspace remain binding. If and only if the
coordination feasibility gate in [ADR-021–ADR-025](./DECISIONS.md) and
[FINAL_48_HOUR_PLAN.md](./FINAL_48_HOUR_PLAN.md) passes, expose **Clash Matrix** and **3D
Investigation** as modes in this same application shell. Do not redesign the product, replace the
approved colour palette/typography, or create a separate coordination product.

The conditional interaction sequence is:

1. Select a two-model coordination set whose members refer to separate immutable model versions.
2. Show the common coordinate frame and an explicit alignment-validation outcome before enabling
   analysis.
3. Select exactly one A/B pair and run the verified deterministic analysis with visible tolerance,
   units, exclusions and tested entity scope.
4. Render a compact matrix from actual run results. Distinguish raw intersections, grouped clashes,
   and human-assessed coordination issues; show unavailable, not analysed, zero, error and
   results-available states separately.
5. Selecting a result uses both model identities/version hashes and actual element references to
   investigate the computed pair in 3D. Evidence shows the run and both source hashes.
6. An optional Muse Spark explanation is labelled as AI interpretation, cites this computed
   evidence and reports whether the actual source was AI or deterministic fallback. It never
   creates or edits a Finding, clash coordinate, count or check criterion.

Keep the 3D viewport continuous on desktop while the matrix and evidence are inspected. Keep
selection styling neutral and distinct from issue severity. Reuse the verified single-model
**Fit model**, **Reset view** and **Focus selected** actions from UI-004A where appropriate; do not
show inactive controls. Use honest loading/error states without progress percentages unless they
are measured.

The minimum front-end integration boundary is a coordination-set identifier and version-pinned
matrix/result API response; frontend code must not calculate geometry or infer alignment. The
proposed API and result fields are documented in [ARCHITECTURE.md §21](./ARCHITECTURE.md#21-day-7-delivery-contract-bounded-coordination-extension);
they are not current endpoints or generated types. Conditional requirements and status evidence are
listed separately in [REQUIREMENTS.md §8.3](./REQUIREMENTS.md#83-conditional-two-model-coordination-demonstration).

For sample data, tracked `examples/` content is limited to manifests, attribution/provenance,
preparation instructions and genuinely redistributable small assets. Private BIM files,
evaluation materials and unapproved third-party assets remain in the owner-managed ignored
`local-private/` layout. Duplex Apartment is the preferred external candidate only after
compatibility and rights checks. The safe fallback is a one-click synthetic single-model review;
that product route is not yet implemented. Until it is verified, use the manual synthetic
single-model workflow; neither path is a clash demonstration.

## 20. UI-004A — Viewer camera, selection and responsive-state corrections

**Status:** Originally implemented and browser-verified on an isolated branch; commit `f55a5f5`
merged via PR #25 into `chore/final-day-decisions-implementation`. It was subsequently integrated
through PR #28 into `main` at `cf06328c874258efe8a49d0afa291d9aef278928`.
This is a bounded viewer correction, not approval for a wider redesign and not completion of T-7/M3.
Detailed interaction evidence and validation commands are recorded in
[UI_CHANGELOG.md](./UI_CHANGELOG.md#ui-004a--professional-3d-viewer-and-navigation-corrections).

### Verified behaviour

- **Fit model** frames the full model after zooming or panning and retains a useful orientation
  where possible. **Reset view** restores the canonical isometric view. **Focus selected** frames
  the selected element with surrounding context. Navigation is bounded and Fit model remains a
  recovery action.
- Camera actions use the installed That Open Components and camera-controls APIs. No new
  dependencies or viewer framework were introduced.
- Model-pointer selection, finding selection and application selection stay coordinated by
  GlobalId. Neutral selection styling is distinct from the deterministic issue highlight; an
  element with an active error retains that highlight when selected. The viewer currently uses
  the same issue colour for every finding severity; severity remains labelled in the register and
  inspector, and cross-severity viewer styling has not been verified.
- **Clear selection** clears viewer styling and the inspector/findings selection without changing
  the camera. Application selection can also be cleared while viewer preparation fails or is in
  progress. Asynchronous highlight updates cannot reapply a superseded selection.
- Model loading distinguishes **Downloading model**, **Preparing geometry**, **Ready** and
  **Failed** using observable lifecycle stages; no percentage progress is fabricated.
- On desktop, evidence and findings regions scroll independently while the model remains visible.
  The viewer yields height on short desktop screens so the findings remain accessible. At 390×844,
  the existing single-column arrangement has no horizontal document overflow.

### Scope not included

This iteration does not add orthographic/perspective switching, direct keyboard camera navigation,
model-tree or category visibility controls, a new accessibility claim, API/schema changes,
backend review changes, native-rule configuration through the UI, or coordination behaviour.
Keyboard activation of the available camera buttons was verified; it is not a full accessibility
audit.

## 21. RELEASE-001 — current verified baseline, not final UI-001

The owner requested a bounded functional integration using the existing Concept C shell and T-5 API
functions. No redesign or additional paid call is authorised by that request. The separately
required implementation packet still needs an approved iteration branch, exact path allow-list,
revision budget, evidence arrangements and rollback. No application changes were made as part of
this baseline verification.

On the merged UI-004A implementation, a fresh synthetic IFC/IDS review produced the two expected
findings and exercised the viewer at actual CSS viewport sizes of 1920 × 1080, 1440 × 900 and
390 × 844. The default plan source is visible. The objective field, explanation request, recent
sessions and one-click sample are absent; reopening by explicit session/run ID works. Direct
offline API checks returned `plan_source=default` and an `ai_disabled` deterministic explanation
template. Those API results are not a connected browser AI workflow.

The detailed checks and limitations are recorded in
[UI_CHANGELOG.md](./UI_CHANGELOG.md#release-001--synthetic-baseline-verification). T-7/M3 remain
in progress; a recorded browser walkthrough is not the missing benchmark Playwright smoke test or
an accessibility audit.

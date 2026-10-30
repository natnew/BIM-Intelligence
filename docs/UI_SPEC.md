# BIM Intelligence UI Specification

**Status:** Governance baseline; no visual redesign is approved by this document.
**Scope:** Owner-directed interface refinement under T-7, contributing to M3.
**Authority:** The project owner approves visual decisions. This document records verified
behaviour, provisional design principles, approved decisions and unresolved questions separately.

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
   may appear here. None are recorded yet.
4. **Ideas requiring further discussion** — unresolved visual, interaction and presentation choices.

Current code and CSS are evidence of the implementation, not evidence that its appearance is final.
No reference, design direction, token value or layout in this specification is owner-approved by
implication.

## 3. Primary professional workflows

### Existing verified behaviour

- Connect to an existing review using a session ID and run ID, or start a standard review for a
  session.
- Load review data only when the review run belongs to the requested session and active model
  version.
- Inspect the model summary, per-check coverage and findings.
- Select a finding to highlight its affected GlobalId values in the viewer and load an element
  record.
- Select a rendered model element to load its record and select the first matching finding in
  canonical API order.
- Inspect element identity and property values, including whether a property is inherited.
- See loading, empty, API/version mismatch and viewer error states.

These behaviours are implemented by `App`, `ModelWorkspace`, the version-aware BIM API client and
the viewer; component and API tests cover the described review, state and selection flows. The T-3
browser verification on the minimal fixture is recorded in
[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md#t-3--interactive-3d-bim-viewer).

### Intended product workflow — not yet fully implemented in the UI

The product-level workflow described by the project documents is:

1. Provide an IFC model and project requirement material.
2. Review requirement candidates with their verbatim source quotes and confirm, edit or reject
   them.
3. State a review objective and inspect the bounded plan.
4. Follow review progress and check coverage.
5. Triage findings in relation to model elements and inspect deterministic evidence.
6. Produce a traceable report with provenance.

The current frontend does not provide model/document upload, requirement-candidate confirmation,
objective planning, AI explanation panels, live progress streaming or report export. These are
planned capabilities, not existing screens. Their design and sequencing remain subject to owner
direction and implementation acceptance criteria.

## 4. Navigation and workspace information hierarchy

### Existing verified behaviour

The current application is a single page with a product heading and backend health status, followed
by the model review workspace. Within that workspace, the session/run form precedes the model
summary and viewer; a findings and element-details panel sits alongside the viewer on wider screens.
On narrow screens the model and review panel stack vertically.

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

- Whether the application needs persistent navigation, workspace tabs, a project-level landing
  view or a single review workspace.
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

### Ideas requiring further discussion

- Viewport prominence, surrounding tool controls, selection appearance and any additional model
  navigation affordances.
- How the viewport adapts to small screens and how users inspect the model without a pointer.
- Whether the current viewer background, highlight colour and camera framing remain appropriate.

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

## 7. Element properties and evidence

### Existing verified behaviour

The selected-element details show name or IFC type, GlobalId, IFC type, storey and the available
property-set/property values. Inherited property values are labelled. The backend element contract
also contains other indexed information, but the current frontend does not display all of it.

Finding evidence currently includes observed and expected text, requirement ID, rule ID/version,
method, affected element references and severity/category from the generated API contract. The
current frontend does not display a source requirement quotation or AI explanation.

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

The values below are a snapshot of the existing `frontend/src/index.css`, included to make the
starting point inspectable. They are **not a target palette, a recommended design system or
owner-approved tokens**. A future iteration may change them only when its approved scope says so.

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

### Verified component states

The health panel and review workspace expose loading, error, empty and data-bearing states; the
viewer exposes loading, ready and error states. Existing CSS includes hover, disabled, selected,
severity and `:focus-visible` treatments. This inventory does not establish that every contrast,
keyboard or assistive-technology outcome has been audited.

### Provisional token principles

If the owner approves a token change, record semantic intent and affected states in the iteration
entry. Verify readable contrast, focus visibility and consistency across affected components.
Typography families, scales, spacing, sizing, radii, elevation, motion and state colours remain
open for owner input; this document assigns no new values.

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
- Preserve semantic headings, labels, lists, descriptions and status announcements.
- Maintain visible keyboard focus and readable text/background contrast.
- Provide an accessible way to understand and operate any interaction introduced by an iteration;
  document limitations where the 3D viewer cannot provide an equivalent interaction.

### Ideas requiring further discussion

- Target viewport range, zoom expectations and any owner-selected breakpoint behaviour.
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

**None recorded.** Add a decision here only after explicit owner approval, with the related UI
iteration ID, date and reference IDs. Do not convert a provisional principle into an approved
decision without that approval.

## 14. Open visual questions

The following remain open for owner judgement:

- Which software, product or project references should be studied, and which specific interaction
  or visual feature matters in each?
- What should be the primary review workspace hierarchy and navigation model?
- Which viewport, issue-register and evidence-detail arrangements best fit the owner's coordination
  workflow?
- Which property, finding, requirement and provenance details need to be immediately visible?
- Which typography, colour, spacing and component-state directions should be retained, replaced or
  tested?
- What responsive viewport range and accessibility acceptance criteria should govern iterations?
- What reporting formats and report-preview workflow should be prioritised?

Record references and feedback in [UI_REFERENCES.md](./UI_REFERENCES.md). Record each authorised
implementation iteration and its evidence in [UI_CHANGELOG.md](./UI_CHANGELOG.md). Until the owner
answers these questions, no visual direction is implied.

## 15. UI change-control process

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
2. Use the committed `tests/fixtures/minimal.ifc` and `tests/fixtures/minimal.ids` through the
   existing API workflow. The frontend has no upload screen. Record the fixture/model hash, browser
   name/version, and session/run IDs in the private evidence record so the selection state can be
   repeated.
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

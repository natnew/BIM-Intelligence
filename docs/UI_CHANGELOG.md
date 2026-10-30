# UI Iteration Changelog

This is the append-only, detailed history for owner-directed interface iterations under T-7. It
records proposals and their evidence; it does not grant design approval, commit approval or merge
approval. Keep the root [CHANGELOG.md](../CHANGELOG.md) for significant implementation and merged
changes rather than duplicating this detailed record.

## Record status

The UI-001 design proposal and private prototype evidence are recorded below. The owner selected
Concept C as the UI-002 conceptual foundation and, on 30 October 2026, approved UI-003: the
production implementation of that direction in the React application, recorded in the final entry.
UI-003 awaits owner review; T-7 and M3 remain in progress.

Keep private verification evidence in the ignored, owner-managed `local-private/test-results/`
and raw AEC tester feedback in `local-private/professional-feedback/`. Entries below use only
non-sensitive identifiers or neutral paths and authorised decision summaries, not private
materials, project names or model-derived facts without publication authorisation. Follow
[AGENTS.md](../AGENTS.md) for private inspection, LLM transmission and security/provenance review.

## Append-only entry template

Copy this entry for each iteration. Do not rewrite an earlier decision to make a later outcome look
like the original approval; add a subsequent entry and link it to the earlier iteration.

### [UI-###] — [objective]

- **UI iteration ID:**
- **Date (YYYY-MM-DD):**
- **Design objective:**
- **Source reference IDs and locations:** [non-sensitive IDs or neutral paths; private mapping otherwise]
- **Explicit owner request:** [non-sensitive link or authorised summary; retain private original locally]
- **Proposed changes:** [bounded proposal and affected files]
- **Approved scope:** [owner decision, date and exact authorised scope]
- **Files changed:** [complete list]
- **Reason for each significant change:** [file or component → reason]
- **Protected behaviour:** [applicable contracts and interactions]
- **Tests executed:** [exact command and result for each; state `Not run` where applicable]
- **Visual before/after evidence:** [non-sensitive evidence IDs or neutral private paths, viewport and browser; or `Not captured`]
- **Accessibility regression results:** [checks performed and findings; do not infer from lint]
- **Functional regression results:** [paths exercised and results]
- **Owner decision:** [Proposed / Approved / Rejected / Revised / Reverted, with date and authorised, non-sensitive feedback summary]
- **Branch, commit and PR references:** [available identifiers/links or `Not created`]
- **Rollback instructions:** [specific files/changes and safe restoration method]

## Framework establishment — 30 October 2026 (T-7 / M3; not UI-001)

- **Authorised output:** owner-requested autonomous design-system governance and reusable
  customisations only; no application redesign, reference-image processing or implementation.
- **Established:** [binding constitution](./UI_CONSTITUTION.md),
  [refinement skill](../.github/skills/bim-ui-refinement/SKILL.md), read-only
  [designer](../.github/agents/bim-ui-designer.agent.md) and approval-gated
  [implementer](../.github/agents/bim-ui-implementer.agent.md).
- **Aligned records:** UI_SPEC, UI_REFERENCES (handling rules only), frontend/root AGENTS,
  root CHANGELOG and the existing T-7 register. No task/milestone renumbering or schedule changes.
- **Design controls:** three alternatives, comparative visual sheet and weighted rubric before
  owner selection; separate prototype/implementation approvals, bounded revisions, supervised
  time/cost checkpoints and explicit stop. No layout, style or token approved.
- **Reference verification:** `GOV-UI-002` in [UI_REFERENCES](./UI_REFERENCES.md) records
  metadata-only discovery and ignore/tracking checks. No image opened; provider approval and
  rights remain unverified. No private directory moved or copied.
- **Hook inspection:** Git `core.hooksPath=.githooks`; secret-scanning pre-commit preserved.
  Optional path/scope Copilot safeguards documented in UI_SPEC §16, not installed.
- **Static validation:** inline Python/PyYAML checks passed for all three frontmatters, local
  Markdown file targets, exact rubric weights (25/20/20/20/10/5 = 100), the 11-file allow-list,
  no staged changes and no protected application/viewer/contract/fixture/benchmark/dependency/CI/
  hook changes. `git diff --check` passed. The focused formatting command below passed after
  its initial check flagged the four new files and Prettier formatted only those new files.
  No application tests or browser verification were run for this documentation/configuration task.

  ```powershell
  & .\frontend\node_modules\.bin\prettier.cmd --check frontend\AGENTS.md .github\agents\bim-ui-designer.agent.md .github\agents\bim-ui-implementer.agent.md .github\skills\bim-ui-refinement\SKILL.md docs\UI_CONSTITUTION.md
  ```

- **Authority conflicts resolved:** autonomy applies within approved design checkpoints, not
  unapproved application edits; the read-only designer emits chat prototypes, while rendered
  files require separate implementer approval. Operational governance/customisation sources are
  intentional repository inputs, not generated design outputs. Future prototype/evidence outputs
  remain ignored. Existing single-orchestrator ADRs and runtime invariants are unchanged.
- **Evidence limitations:** no application tests, browser captures, visual scores or reference
  interpretations are produced by framework establishment. Customisation discovery/tool
  restrictions must still be confirmed in the installed Copilot host before first use.
  The root project-context summary still calls the viewer outstanding whereas the T-3 register
  records verified viewer evidence; use the authoritative task register and do not infer missing
  UI capabilities from either summary. This pre-existing discrepancy is not resolved by redesign.
- **Rollback:** inspect the final diff and remove only this framework's additions with a reviewed
  inverse patch, preserving unrelated work and prior governance. New files are the constitution,
  skill and two agents; modifications are the seven aligned records listed above. No rollback,
  commit, push or merge is authorised by this entry.
- **Owner review:** pending. T-7 and M3 remain in progress. UI-001 is not started.

### UI-001 — Three independent review-workspace concepts

- **UI iteration ID:** UI-001
- **Date (YYYY-MM-DD):** 2026-10-30
- **Design objective:** Compare three substantially different review-workspace concepts for the
  same project-open, model-inspection, review, finding, element and evidence workflow.
- **Source reference IDs and locations:** No image-derived REF-ID influence is claimed. Metadata
  only: the owner-managed library is at the singular `local-private/ui-reference/`; the folders
  contain 19 Revit, 13 Snaptrude, 4 Spacemaker and 6 World_Lab files. The plural location is absent.
  The owner selected synthetic-only processing; no screenshot was opened, transmitted or copied.
- **Explicit owner request:** Create concepts A/B/C, static previews and screenshots in the ignored
  `local-private/ui-prototypes/` directory, then stop for owner assessment. The owner selected
  `synthetic-only` when asked about provider image processing.
- **Proposed changes:** Isolated HTML/CSS and screenshot artefacts only. A: Professional BIM
  Workspace; B: Spatial Intelligence Studio; C: AI Review Command Centre. No production layout or
  interaction was changed.
- **Execution boundary:** The BIM UI Designer custom role was not dispatchable from this session's
  agent tool surface. Its read-only workflow guidance was followed directly; no host-enforced
  designer tool restriction is claimed. Prototype output was created only after the owner approved
  the isolated output path.
- **Approved scope:** One metadata-only reference inventory, one initial prototype pass per concept,
  synthetic example data, desktop captures at 1920×1080, and supplementary narrow captures at
  390×844. No external assets, network calls, paid services, live Meta calls or AI-generated
  content. Output path: `local-private/ui-prototypes/`.
- **Files changed:** `local-private/ui-prototypes/index.html`; `styles.css`;
  `concept-a-professional-workspace.html`; `concept-b-spatial-studio.html`;
  `concept-c-command-centre.html`; `screenshots/concept-a-1920x1080.png`;
  `screenshots/concept-b-1920x1080.png`; `screenshots/concept-c-1920x1080.png`;
  `screenshots/concept-a-390x844.png`; `screenshots/concept-b-390x844.png`;
  `screenshots/concept-c-390x844.png`. All are Git-ignored and untracked.
- **Reason for each significant change:** `index.html` records rationale, hierarchy, interactions,
  evidence/AI treatment, accessibility, trade-offs, shared synthetic data, comparative rubric,
  recommendation and limitations; `styles.css` supplies shared primitives and three distinct
  visual systems; each concept HTML is a local static screen; six PNGs preserve controlled desktop
  and narrow viewport evidence.
- **Protected behaviour:** No application, viewer, API, schema, test, dependency, IFC, fixture or
  benchmark files changed. Static screens label all example content synthetic, keep AI copy
  separate from deterministic Finding-shaped examples, and show incomplete coverage distinctly.
  Production contracts in UI_SPEC §12 remain untouched.
- **Tests executed:** Static pages opened in the integrated browser; accessibility snapshots exposed
  headings, named regions, buttons and selected states. Google Chrome 156.0.8078.76 captured all
  desktop screenshots at 1920×1080 and narrow screenshots at 390×844; PNG dimensions were verified.
  No application test suite was run because no application code changed. Prototype controls are
  inert and were not treated as functional tests.
- **Visual before/after evidence:** No production before/after comparison. Desktop evidence:
  `local-private/ui-prototypes/screenshots/concept-{a,b,c}-1920x1080.png`. Supplementary narrow
  evidence: `local-private/ui-prototypes/screenshots/concept-{a,b,c}-390x844.png`. Browser:
  Google Chrome 156.0.8078.76.
- **Accessibility regression results:** Prototype markup includes semantic landmarks, named
  controls, selected-state attributes, skip links and visible focus styling. Narrow captures show
  horizontal clipping in A and C and inspector/model overlap in B. No zoom, keyboard-only,
  screen-reader or contrast-conformance testing was performed; none is claimed.
- **Functional regression results:** No production interactions changed; no regression test
  applies. The selected model, findings and controls are static illustrations without IFC, API or
  model calls. Loading, error, version-mismatch and empty-finding states are not illustrated.
- **Owner decision:** Proposed; owner assessment pending. C is recommended for evidence-first
  triage, with the narrow-layout failures called out. No concept is approved and UI-002 is not
  authorised.
- **Branch, commit and PR references:** `chore/ui-001-review-workspace-concepts`; commit
  [`db82306`](https://github.com/natnew/BIM-Intelligence/commit/db82306bcb747951f59d80cf66591e8b79538a96);
  [PR #15](https://github.com/natnew/BIM-Intelligence/pull/15).
- **Rollback instructions:** Remove only the listed files under
  `local-private/ui-prototypes/` if the owner rejects the prototypes. No production rollback is
  required.

### UI-002 — Concept C, Professional BIM Workspace redesign

- **UI iteration ID:** UI-002
- **Date (YYYY-MM-DD):** 2026-10-30
- **Delivery mapping:** T-7 / M3. T-7 and M3 remain in progress; this prototype does not satisfy
  the M3 browser-walkthrough exit criteria.
- **Design objective:** Refine selected UI-001 Concept C into a spatially dominant, technically
  credible BIM review workspace, preserving the same synthetic review facts in loaded, finding-
  selected and element-selected states.
- **Source reference IDs and locations:** No REF-ID influence is claimed. Eight screenshot
  filenames were shortlisted by metadata only and their intended relevance was reported to the
  owner; no reference image was opened, transmitted or visually interpreted. The prior
  synthetic-only processing decision and unverified provider/rights permissions remain in force.
- **Explicit owner request:** The owner selected C as the conceptual foundation, requested one
  refined prototype and one bounded improvement pass, and required the work to stop before
  production implementation, commit, push or merge.
- **Approved scope:** Prototype and screenshot output only under the ignored
  `local-private/ui-prototypes/ui-002/`; synthetic examples; desktop screenshots at 1920×1080 and
  1440×900; narrow screenshots at 390×844; three preview states; one bounded refinement pass.
  No React application, viewer, API, backend, schema, test, fixture, dependency or reference-image
  changes; no live Meta call, paid service or external asset.
- **Proposed changes:** An original application shell with project identity and review navigation;
  a prominent static model viewport with illustrative navigation/orientation controls; a proposed
  collapsible model hierarchy; a collapsible finding register; an evidence inspector separating
  synthetic deterministic evidence from an illustrative AI explanation; and narrow-screen finding
  cards.
- **Files changed:** `local-private/ui-prototypes/ui-002/index.html`;
  the nine screenshot files matching
  `local-private/ui-prototypes/ui-002/screenshots/concept-c-v2-{1920x1080,1440x900,390x844}-{model-loaded,finding-selected,element-selected}.png`;
  this record in `docs/UI_CHANGELOG.md`; and a summary in `CHANGELOG.md`. Prototype and screenshot
  artefacts are ignored and untracked.
- **Reason for each significant change:** The isolated HTML file supplies the complete synthetic
  prototype, preview states, responsive styles, semantic labels and explicitly illustrative
  controls. The nine PNGs document the three states at each requested viewport. The detailed and
  root changelogs record the approved scope, evidence, limitations and pending owner decision.
- **Bounded improvement pass:** The first narrow capture exposed a crowded toolbar and unreadable
  table layout. One pass replaced the narrow table with readable finding cards, exposed text
  labels and touch guidance for navigation, reduced redundant filter/icon density, tightened the
  state-selector controls, increased small evidence-text sizes and made the project browser and
  finding register native collapsible disclosures. A targeted capture correction was included in
  this same pass; no further redesign loop was performed.
- **Protected behaviour:** Production React and viewer code remain unchanged. The static illustration
  is not an IFC render, and no shown project, model, finding, property, requirement, source quotation,
  rule output, AI explanation or navigation action is live or connected. The sample explanation is
  explicitly illustrative and not a model fact.
- **Tests executed:** No application test suite was run because no application code changed.
  Google Chrome 156.0.8078.76 captured all nine PNGs; each PNG header was checked against its
  requested 1920×1080, 1440×900 or 390×844 output dimensions. Browser verification at a 390×844
  window reported a 375×844 CSS viewport (Chrome scrollbar reservation) and equal 375 px document
  and viewport widths, with no horizontal document overflow. The finding and element preview
  selectors displayed their corresponding overlays/highlights; both the issue register and mobile
  project-browser disclosures opened and closed. These checks cover only this static mock-up.
- **Visual before/after evidence:** UI-001 baseline:
  `local-private/ui-prototypes/screenshots/concept-c-1920x1080.png`. UI-002:
  `local-private/ui-prototypes/ui-002/screenshots/concept-c-v2-{1920x1080,1440x900,390x844}-{model-loaded,finding-selected,element-selected}.png`.
  The 1920 px desktop composition allocates about 69% of the width to the central model workspace,
  versus a comparatively small model pane in C v1. The selected marker, evidence inspector, run
  coverage and finding register are visible together at the desktop viewport; the narrow state
  cards avoid the prior table's horizontal squeeze. Static evidence does not establish real IFC
  geometry, camera behaviour, user task speed or WebGL occlusion.
- **Design-stage weighted evaluation:** Scores use the established 0–4 rubric and are predictions,
  not usability measurements or implementation results. The C v1 comparator is the recorded
  88.75/100 design-stage estimate; no common user study or live application test was performed.

  | Criterion | Weight | C v1 | C v2 | Evidence and limitation |
  |---|---:|---:|---:|---|
  | Professional BIM usability | 25% | 4/4 | 3/4 | Project hierarchy, coverage, issue register, selection and evidence are organised for the review task; project actions, search/filters and navigation remain illustrative, with no empty/error/version-mismatch screen. |
  | Spatial clarity | 20% | 3/4 | 4/4 | The model is the dominant central work area, with distinct finding/element outlines, an orientation cube and proposed navigation controls across the preview states. Geometry and camera interaction are static. |
  | Visual refinement and originality | 20% | 4/4 | 4/4 | A restrained professional shell, original synthetic line illustration, dense but ordered evidence cards and consistent selected states are visible in all three desktop captures. No reference images were inspected; originality is not a similarity audit. |
  | Evidence integrity and interaction clarity | 20% | 4/4 | 4/4 | Synthetic Finding, requirement, observed/expected values, check/version, GlobalId and provenance are labelled; AI copy is separately marked “Not a model fact”. No API, grounding checker or source document was exercised. |
  | Accessibility and responsive behaviour | 10% | 2/4 | 2/4 | The prototype uses labelled native state radios and disclosure controls; mobile finding cards fit without horizontal document overflow. Small text remains, detailed evidence is below the narrow first viewport, and keyboard, screen-reader, contrast and zoom conformance were not tested. |
  | Implementation feasibility | 5% | 3/4 | 3/4 | Existing workspace, finding selection, version-pinned data and GlobalId viewer wiring offer a reuse path. The current page contract has no review explanation payload, and viewer camera controls are not exposed through `ViewerCanvas`; hierarchy/control integration needs separate design and regression work. |
  | **Weighted total** | **100%** | **88.75/100** | **87.5/100** | C v2 is **1.25 points lower** under this conservative review: spatial clarity improves, while lower workflow evidence reflects unimplemented controls and untested states. Low-to-moderate confidence; no acceptance threshold is implied. |

- **Three weakest remaining aspects:** (1) most application actions, filters and camera controls are
  illustrative rather than wired; (2) narrow evidence text is small and the complete inspector
  requires scrolling; (3) the static happy path does not show real loading, empty, API-error,
  partial-run recovery or model-version mismatch behaviour. These are design limitations, not
  established production defects.
- **Accessibility regression results:** No production accessibility regression was possible.
  Browser inspection confirms named regions, labelled state choices, native disclosure semantics
  and no horizontal document overflow at the tested narrow window. No keyboard-only, screen-reader,
  contrast or browser-zoom audit was conducted. The static drawing has a text alternative, but
  there is no non-spatial production model-selection path in this prototype.
- **Functional regression results:** The three local preview states show the expected static
  finding/element marker and evidence panel; native disclosure controls were exercised. No IFC
  loading, camera operation, API interaction, model picking, review execution, AI call or production
  regression test occurred.
- **UI-003 implementation proposal — not approved:** If separately authorised, limit the initial
  application iteration to `frontend/src/App.tsx` (application shell), `frontend/src/components/ModelWorkspace.tsx`
  (review layout and existing data), `frontend/src/index.css` (responsive visual system), and
  `frontend/src/components/ModelWorkspace.test.tsx` (selection, evidence, coverage and responsive
  state regressions). Preserve the current API, generated types, ETag/version checks, finding
  normalisation, GlobalId mapping and viewer lifecycle. Keep a project tree limited to data actually
  present in `ModelSummary`/`ElementRecord`; do not imply a complete category hierarchy where the
  API supplies no element collection. `ReviewWorkspaceData` exposes findings and a run, not an
  explanation, so do not render fabricated AI content. If working orbit/pan/zoom/fit/focus buttons
  or an orientation cube are in scope, request a separate exact allow-list and tests for
  `frontend/src/viewer/ViewerCanvas.tsx` and `frontend/src/viewer/IfcViewer.ts`; the current viewer
  holds camera controls internally. No backend/API/schema change is proposed. Indicative estimate:
  2–3 engineering days for core layout, responsive interaction and regression evidence; add 1–2
  days if navigation controls need a viewer adapter, subject to repository setup and review.
  Principal risks are 3D lifecycle/resize regressions, selection/highlight drift, evidence
  truncation, unavailable hierarchy/explanation data and accessibility regressions.
- **Owner decision:** Proposed; UI-002 visual assessment and any UI-003 scope approval are pending.
  This record does not authorise production implementation, commit, push or merge.
- **Branch, commit and PR references:** `chore/ui-002-concept-c`; commit
  [`548e516`](https://github.com/natnew/BIM-Intelligence/commit/548e516a07f17285d4597c3771c7e7688c7cac23);
  [PR #16](https://github.com/natnew/BIM-Intelligence/pull/16).
- **Rollback instructions:** For rejection, remove only the ignored directory
  `local-private/ui-prototypes/ui-002/` and revert this UI-002 entry in
  `docs/UI_CHANGELOG.md` plus its corresponding UI-002 summary in `CHANGELOG.md`. Do not alter the
  UI-001 prototype, application, viewer or existing records.

## UI-002 Revision 2 — Project Home and desktop-first review workspace

- **Date / delivery mapping:** 30 October 2026; T-7 / M3. T-7 and M3 remain in progress; this
  prototype does not satisfy the M3 browser-walkthrough exit criteria.
- **Design objective:** Extend the owner-selected Concept C v2 direction with a Project Home and a
  more legible desktop review workspace, keeping the approved restrained palette and making the
  model viewport the primary working surface.
- **Explicit owner request:** The owner approved this prototype-only revision, including Project
  Home, synthetic examples, desktop-first workspace refinements, the three workspace states,
  responsive captures and one bounded corrective pass. Production implementation, commit, push,
  merge and UI-003 remain unauthorised.
- **Approved scope:** `local-private/ui-prototypes/ui-002/` and the four authorised records:
  `docs/UI_SPEC.md`, `docs/UI_CHANGELOG.md`, `docs/IMPLEMENTATION_PLAN.md` and `CHANGELOG.md`.
  The prototype uses synthetic model facts, findings, requirements and property values only.
  No private BIM model, project document or client evidence was inspected.
- **Reference treatment:** The prototype retains the previously approved Concept C v2 palette.
  No reference screenshot was opened or processed for this revision, so no REF-ID-specific
  influence is claimed. No proprietary layout, branding or asset was copied.
- **Files changed:** `local-private/ui-prototypes/ui-002/home.html` (Project Home screens);
  `local-private/ui-prototypes/ui-002/index.html` (refined workspace and preview states);
  the 15 ignored screenshot files listed below; `docs/UI_SPEC.md` (approved direction, proposed
  capabilities, acceptance criteria and UI-003 proposal); `docs/IMPLEMENTATION_PLAN.md` (T-7
  scope note only); `CHANGELOG.md` (Unreleased summary); and this append-only record.
- **Reason for significant changes:** Project Home separates session start, supported-file
  preparation and clearly synthetic sample routes from review work. The workspace improves
  desktop hierarchy, separates model categories from findings, exposes partial coverage and
  distinguishes deterministic evidence from illustrative AI explanation. Documentation records
  the production/API boundary and does not treat prototype controls as implemented functionality.
- **Screenshot evidence:** All captures are local and ignored under
  `local-private/ui-prototypes/ui-002/screenshots/`.
  - Project Home: `ui-002-r2-home-1920x1080.png`,
    `ui-002-r2-home-1440x900.png`, `ui-002-r2-home-390x844.png`.
  - New project: `ui-002-r2-new-project-1920x1080.png`.
  - Quick upload: `ui-002-r2-quick-upload-1920x1080.png`,
    `ui-002-r2-quick-upload-local-accepted-1920x1080.png`,
    `ui-002-r2-quick-upload-local-error-1920x1080.png`.
  - Synthetic sample selection: `ui-002-r2-synthetic-sample-selection-1920x1080.png`.
  - Workspace: `ui-002-r2-workspace-{1920x1080,1440x900}-{loaded,finding-selected,browser-evidence}.png`
    and `ui-002-r2-workspace-390x844-browser-evidence.png`. The six desktop captures cover the
    requested loaded, Finding-selected and browser/evidence states at both desktop sizes.
- **Bounded corrective pass:** Initial review identified (1) a wrapped register heading at 1440 px,
  (2) an apparent selected-element treatment in the unselected browser state, and (3) cramped
  desktop information sizing. Final capture review also found that the landing screen remained
  visible behind alternate Project Home routes. One pass hid inactive routes, shortened the
  register heading, tied the selected browser treatment to the element-selected state, and refined
  workspace width and text sizing. The element-selected mobile route opens the native browser
  disclosure. All Home routes were recaptured and checked for one visible screen. No further
  redesign pass was performed.
- **Remaining weakest aspects:** (1) mobile remains a long, vertically stacked screen; reaching
  the complete browser and evidence requires scrolling; (2) camera, visibility, filtering, upload
  and review controls remain illustrative, with no production connections; (3) keyboard-only,
  screen-reader, contrast and zoom conformance have not been assessed, and no user study was run.
- **Protected behaviour and capability boundaries:** The model drawing, counts and review evidence
  are synthetic, not an IFC render or client record. New-project fields are not saved, file
  selection checks only the filename extension, and no file bytes are read or sent. The sample
  route opens a static preview only. Recent sessions, a sample catalogue, frontend upload/session
  flows, category visibility, exposed camera navigation, geometric clash detection and a connected
  AI explanation remain unimplemented or separately approval-gated. Production React, viewer,
  backend, API clients, schemas, tests, fixtures, dependencies and benchmark were not changed.
- **Browser and visual checks:** The VS Code integrated browser reported
  `Chrome/150.0.7871.250` with `Electron/43.8.3`. All 15 Revision 2 PNGs were checked against
  their requested pixel dimensions. At 390×844, the home, upload and workspace pages had equal
  document and client widths (375 CSS px, due to the reserved scrollbar), with no horizontal
  document overflow. Browser checks exercised the new-project-to-upload prototype route, local
  acceptance feedback for a synthetic `.ifc` filename, local rejection of a synthetic `.pdf`
  filename, the synthetic-sample-to-workspace route, all three preview states, the mobile browser
  disclosure and an empty page-error list. These are static prototype checks, not application
  tests or upload/review execution. An initial automation attempt tried to click a visually hidden
  preview radio directly and timed out; rerunning through its visible labelled control passed.
- **Design-stage weighted evaluation:** Scores use the established 0–4 rubric. They are a
  qualitative prototype assessment, not measured task performance, implementation results,
  accessibility conformance or a user study. The earlier Concept C v2 design-stage estimate was
  87.5/100; this Revision 2 estimate is not a measured regression because it adds Project Home
  tasks and a broader screen set.

  | Criterion | Weight | Revision 2 | Evidence and limitation |
  |---|---:|---:|---|
  | Professional BIM usability | 25% | 3/4 | Distinct start paths, coverage, model hierarchy, register and inspector support a plausible review flow; session creation, upload, filtering and review execution are not connected, and real error/recovery behaviour is not exercised. |
  | Spatial clarity | 20% | 4/4 | The model is the central desktop workspace at 1920×1080 and 1440×900, with labelled synthetic selection states; no IFC geometry, camera motion or real occlusion was tested. |
  | Visual refinement and originality | 20% | 3/4 | The palette and restrained visual language are consistent across Home and workspace; denser information and vertical mobile scrolling remain limitations, and no reference-image similarity review was performed. |
  | Evidence integrity and interaction clarity | 20% | 4/4 | Synthetic provenance, requirement/check references, observed/expected values, GlobalId, model version, partial coverage and separate illustrative AI copy are labelled; no live evidence or grounding behaviour was exercised. |
  | Accessibility and responsive behaviour | 10% | 2/4 | Semantic headings, labels, focus styling and native disclosure controls are present, and no horizontal document overflow was measured at 390×844; keyboard-only, screen-reader, contrast and zoom checks remain outstanding. |
  | Implementation feasibility | 5% | 3/4 | The UI specification separates existing interfaces from proposed work and gives a bounded candidate UI-003 file list; Home/upload wiring needs focused API, routing, error-state and regression work, while viewer controls are excluded. |
  | **Weighted total** | **100%** | **82.5/100** | Complete design-stage estimate with low confidence; no passing threshold is adopted. |

- **UI-003 proposal:** See `docs/UI_SPEC.md` §17 for the exact proposed frontend file boundaries,
  retained API/type constraints, estimate and integration risks. This proposal is not an approval
  to begin implementation.
- **Owner decision:** UI-002 Revision 2 is complete for visual review; owner assessment is pending.
  T-7/M3 remain in progress. No commit, push, merge or UI-003 work is authorised.
- **Rollback instructions:** For Revision 2, this file-specific rollback supersedes the
  whole-directory rollback in the preceding Concept C v2 entry; preserve the earlier UI-002
  artefacts and history. To reject the Revision 2 addition, remove only
  `local-private/ui-prototypes/ui-002/home.html` and the 15 `ui-002-r2-*` screenshots, then revert
  this record and the corresponding Revision 2 sections in `docs/UI_SPEC.md`,
  `docs/IMPLEMENTATION_PLAN.md` and `CHANGELOG.md`. `index.html` was evolved in place from an
  ignored Concept C v2 prototype; this worktree contains no separate pre-Revision-2 source copy.
  Restoring that exact earlier file therefore requires an owner-held copy. Do not remove the whole
  prototype directory or alter the earlier UI-002 changelog history, UI-001 files, application,
  viewer or other existing records.

## UI-003 — Production implementation of Concept C v2 in the React application

- **UI iteration ID:** UI-003
- **Date (YYYY-MM-DD):** 2026-10-30
- **Delivery mapping:** T-7 / M3. T-7 and M3 remain **in progress**; this iteration delivers the
  integrated frontend workflow slice but not reporting, AI explanation, demo rehearsal or a
  Playwright smoke test.
- **Design objective:** Replace the bare entry page and session/run-ID form with a working Project
  Home → setup → 3D review workspace built on the owner-approved Concept C v2 / Revision 2 visual
  direction, using only existing API endpoints and real model data.
- **Source reference IDs and locations:** Owner-approved local prototype
  `local-private/ui-prototypes/ui-002/index.html` and `home.html` plus their 1920×1080 and
  1440×900 captures (synthetic content only). No private BIM model, client document, external
  reference image or REF-ID was inspected. No image was sent to any external service.
- **Explicit owner request:** Owner approval to implement Concept C v2 into the existing
  application within a stated frontend file scope; backend, schemas, `IfcViewer.ts`,
  `ViewerCanvas.tsx`, generated types, fixtures, dependencies, CI, credentials and deployment
  excluded. One principal pass plus one corrective pass; no Agent Bakeoff, no parallel branches, no
  new dependencies, no image generation, no live Meta API call.
- **Approved scope (as exercised):** `frontend/src/App.tsx`, `frontend/src/index.css`,
  `frontend/src/components/ModelWorkspace.tsx` (+ test), `frontend/src/api/bim.ts` (+ test), new
  focused components under `frontend/src/components/`, new focused tests and one narrow UI state
  module. Documentation: `docs/UI_SPEC.md`, `docs/UI_CHANGELOG.md`, `docs/IMPLEMENTATION_PLAN.md`,
  `CHANGELOG.md`, `README.md`.
- **Baseline and branch:** `feature/ui-003-production-integration` created from `origin/main`
  at `a3e701f` (merge of PR #17). Worktree was clean before work started.
- **Files changed:**
  - Modified: `frontend/src/App.tsx`, `frontend/src/index.css`,
    `frontend/src/components/ModelWorkspace.tsx`, `frontend/src/components/ModelWorkspace.test.tsx`,
    `frontend/src/api/bim.ts`, `frontend/src/api/bim.test.ts`.
  - Added: `frontend/src/components/AppHeader.tsx`, `ProjectHome.tsx`, `ProjectHome.test.tsx`,
    `ReviewSetup.tsx`, `ModelBrowser.tsx`, `FindingRegister.tsx`, `ReviewCoverage.tsx`,
    `EvidenceInspector.tsx`, `frontend/src/state/useAppLocation.ts`, `frontend/src/App.test.tsx`,
    `frontend/src/test/hygiene.test.ts`.
  - Documentation: `docs/UI_SPEC.md` (§status, §10, §13, §17 note, new §18),
    `docs/UI_CHANGELOG.md` (this entry), `docs/IMPLEMENTATION_PLAN.md` (T-7 note),
    `docs/ARCHITECTURE.md` (two sentences in §11/§12.3 naming the renamed **Run review** action and
    the Project Home entry), `CHANGELOG.md`, `README.md`.
  - Unchanged: `frontend/src/viewer/*`, `frontend/src/api/generated/*`, `frontend/src/api/client.ts`,
    `frontend/src/components/HealthPanel.tsx`, `frontend/src/state/useHealth.ts`, `frontend/src/main.tsx`,
    `backend/`, `tests/`, `datasets/`, `package.json`/lockfile, tsconfig, CI.
- **Reason for each significant change:**
  - `api/bim.ts` → add `createSession`, `fetchSession`, `uploadModel`, `uploadDocument`,
    `fetchRequirements`, extension classification (`.ifc`; `.ids`/`.md`/`.txt`),
    `isExecutableRequirement` and a typed `ModelVersionMismatchError` (also mapped from HTTP 412)
    so the UI can represent a stale run explicitly. Existing version-pinned reads are unchanged.
  - `App.tsx` + `state/useAppLocation.ts` → home/workspace view state driven by the query string
    (`session_id`, `run_id`) with `pushState`/`popstate`; replaces the inline session/run form.
  - `ProjectHome.tsx` / `ReviewSetup.tsx` → product identity, session creation, IFC and
    requirements upload with loading/success/rejection states, honest "not available" areas.
  - `ModelWorkspace.tsx` → separate model / review / requirements / element state channels;
    referentially stable viewer callbacks via refs so the WebGL viewer is created once per model
    version; run-review flow keeps the existing bytes when the model hash is unchanged.
  - `ModelBrowser.tsx`, `FindingRegister.tsx`, `ReviewCoverage.tsx`, `EvidenceInspector.tsx` →
    Concept C v2 panels populated solely from `ModelSummary`, `ReviewRun`, `Finding`,
    `Requirement` and `ElementRecord`.
  - `index.css` → prototype palette as production tokens, header, Project Home, setup sequence,
    fixed-height desktop grid, two-column and single-column adaptations.
  - `test/hygiene.test.ts` → asserts no credential patterns or model-provider endpoints in
    frontend sources (uses Vite `import.meta.glob`, no Node file-system access).
- **Protected behaviour:** UI_SPEC §12 items 1–11 preserved: generated types untouched; ETag /
  `If-Match` reads and the run-vs-model hash check unchanged in `bim.ts`; IFC bytes read-only;
  `ViewerCanvas`/`IfcViewer` unchanged; finding→model highlight and model→finding selection
  retained (tests + browser); finding identity, method, observed/expected, requirement/check/rule
  version displayed verbatim; inherited-property provenance labelled; coverage and run status kept
  distinct from findings; loading/empty/error/mismatch states explicit; keyboard-operable rows with
  visible focus; no functionality removed (the manual session/run entry survives as "Open an
  existing session").
- **Corrective pass (one):** (1) desktop fixed-height grid did not engage because the grid's
  column-flex basis overrode its height — fixed by sizing the shell to `100vh` and letting the grid
  flex; (2) narrow layouts clipped the findings list because desktop `min-height: 0` rules leaked —
  scoped to desktop; (3) `Start over` wrapped and the step-4 button stretched full width; (4) narrow
  viewport hints now wrap below the heading.
- **Tests executed (from `frontend/`, 30 October 2026):**
  - `npm run lint` → passed (oxlint, no warnings).
  - `npm run format:check` → passed. (`prettier --write` was applied **only** to the 17 files
    changed by this iteration; the repository-wide `npm run format` was not run.)
  - `npm run typecheck` → passed.
  - `npm run types:check` → passed (`types.ts: up to date`). There is no `npm run types` script;
    type generation was not run.
  - `npm test` → passed: 6 files, 54 tests (baseline before this iteration: 3 files, 18 tests).
  - `npm run build` → passed (`✓ built in 3.16s`). 26 `IMPORT_IS_UNDEFINED` warnings originate in
    `node_modules/@thatopen/*` and are identical on the unmodified baseline (verified by stash/build).
  - Backend `ruff`/`mypy`/`pytest` → not run (no backend file changed).
- **Browser verification (actual, not mocked):** VS Code integrated browser
  `Chrome/150.0.7871.250` (`Electron/43.8.3`), FastAPI on `127.0.0.1:8001` (`LLM_MODE=off`, no key;
  port 8000 was occupied by an unrelated process) and Vite on `127.0.0.1:5173` with
  `BIMI_API_ORIGIN=http://127.0.0.1:8001`. Inputs: `tests/fixtures/minimal.ifc` and
  `tests/fixtures/minimal.ids` (synthetic). Steps completed: open Project Home → Create review
  session (`POST /sessions`) → upload IFC (summary `Minimal Project`, IFC4, version `f2bd0007…`) →
  upload IDS (2 executable requirements) → Open review workspace → real geometry rendered (three
  walls) → left-drag orbit, right-drag pan and wheel zoom each changed the rendered pixels →
  Run review (`plan_source: default`, 2 checks executed, 2 findings) → select finding W-002 →
  element highlighted red in the viewer and `ElementRecord` shown (`Pset_WallCommon.IsExternal`,
  Uniclass classification, source requirement from the IDS) → clear selection → click a wall in
  the viewer → W-001 `ElementRecord` (`FireRating = REI 60`) with "no linked findings" →
  keyboard: Tab/Enter on the W-003 row selected it → Return to Project Home (URL cleared).
  Additional live states: IFC-only session → "No executable requirements · model view only" with
  Run review disabled; unknown run id → problem detail shown, model still viewable; second model
  version uploaded via API → deep link to the earlier run shows the version-mismatch alerts and
  refuses the stale findings while the new model loads.
  Tooling notes: the webview throttles `requestAnimationFrame` while the tab is hidden, which
  stalls the viewer's camera fit until the tab is visible (environment behaviour, not an
  application regression); desktop/narrow captures used CDP device-metrics emulation
  (`Emulation.setDeviceMetricsOverride` + `setVisibleSize`), and DOM measurements confirmed the
  layouts (1920: columns 238/1374/308 px; 1440: 238/894/308 px; 390: single column, scroll width
  390 px).
- **Visual evidence (ignored, private):** `local-private/test-results/ui-003/`:
  `ui-003-home-{1920x1080,1440x900,390x844}.png`, `ui-003-setup-uploads-complete-1920x1080.png`,
  `ui-003-workspace-finding-selected-{1920x1080,1440x900,390x844,390x844-fullpage}.png`,
  `ui-003-workspace-finding-selected-1428x783.png`, `ui-003-workspace-element-selected-1428x783.png`,
  `ui-003-workspace-after-orbit-pan-zoom-1428x783.png`,
  `ui-003-workspace-keyboard-selected-w003-1920x1080.png`,
  `ui-003-workspace-no-executable-requirements-1440x900.png`,
  `ui-003-workspace-review-error-unknown-run-1440x900.png`,
  `ui-003-workspace-model-version-mismatch-1440x900.png`. The `1428x783` files are native webview
  captures; the others are emulated-viewport captures.
- **Accessibility regression results:** semantic landmarks (`banner`, `nav`, `main`,
  `complementary`, `region`), labelled file inputs, `aria-pressed` rows, `role=status`/`alert`
  announcements and the `:focus-visible` outline are present; keyboard activation of a finding row
  verified in the browser. Not assessed: contrast measurement, screen-reader output, 200 % zoom,
  reduced motion. 3D selection remains pointer-only; the findings register is the non-spatial path.
- **Functional regression results:** All protected interactions above passed in tests and in the
  browser. Known behaviour carried from the baseline viewer: the library's green click-selection
  style persists after *Clear selection* because `IfcViewer` exposes no clear API (deferred to
  UI-004).
- **Weighted evaluation (implementation-stage, measured in browser; 0–4 rubric):** Professional
  BIM usability 3; Spatial clarity 3 (viewport dominant at both desktop sizes; no fit/focus
  control); Visual refinement 3; Evidence integrity 4; Accessibility and responsive 2 (audit
  outstanding); Implementation feasibility 4. Weighted total **77.5/100**; comparative only, no
  passing threshold adopted.
- **Owner decision:** The implementation was owner-approved; commit/push were authorised and completed, and [PR #18](https://github.com/natnew/BIM-Intelligence/pull/18) is open for owner review. Merge remains pending.
- **Branch, commit and PR references:** `feature/ui-003-production-integration`; commit
  [`decbe625`](https://github.com/natnew/BIM-Intelligence/commit/decbe62547574a16eeccac7ff7bc0437d0af9ba1);
  [PR #18](https://github.com/natnew/BIM-Intelligence/pull/18), targeting `main`.
- **Rollback instructions:** From the branch, `git checkout origin/main -- frontend/src/App.tsx
  frontend/src/index.css frontend/src/components/ModelWorkspace.tsx
  frontend/src/components/ModelWorkspace.test.tsx frontend/src/api/bim.ts frontend/src/api/bim.test.ts
  docs/UI_SPEC.md docs/IMPLEMENTATION_PLAN.md docs/ARCHITECTURE.md CHANGELOG.md README.md` and
  delete the added files
  listed above (`AppHeader.tsx`, `ProjectHome.tsx`, `ProjectHome.test.tsx`, `ReviewSetup.tsx`,
  `ModelBrowser.tsx`, `FindingRegister.tsx`, `ReviewCoverage.tsx`, `EvidenceInspector.tsx`,
  `state/useAppLocation.ts`, `App.test.tsx`, `test/hygiene.test.ts`), then remove this entry.
  Private evidence under `local-private/test-results/ui-003/` is owner-managed and ignored.

---
name: bim-ui-refinement
description: "Use when proposing or refining the BIM Intelligence UI: workflow analysis, three alternative concepts, visual prototypes, comparative evaluation and a bounded implementation with regression evidence."
---

# BIM UI refinement

A repeatable workflow for improving a BIM Intelligence interface without breaking its BIM
behaviour.

## Using it in VS Code Copilot

In a Copilot Chat surface that supports workspace skills, type `/bim-ui-refinement` with the
objective, or ask Copilot to load `bim-ui-refinement`. Pick **BIM UI Designer** to propose options
or **BIM UI Implementer** to build an agreed one. Both agents disable automatic sub-agent
invocation and set no model override. They are development tools, not part of the application.

Discovery depends on your VS Code and Copilot versions; reload the chat if the skill or agents do
not appear. Loading this file by hand gives you the guidance but not the agents' tool
restrictions.

## Context to load

1. The [root rules](../../../AGENTS.md) and [frontend rules](../../../frontend/AGENTS.md).
2. The relevant ADRs in [DECISIONS.md](../../../docs/DECISIONS.md), especially ADR-007 and
   ADR-023 for the viewer.
3. The component props, state, and viewer and API interfaces involved. For review triage, start
   with `ModelWorkspace`, `ViewerCanvas`, `IfcViewer` and `api/bim.ts`, and their tests. Read
   generated type definitions only as needed.

Do not load the whole repository, private folders or credentials.

## Workflow

### 1. Workflow analysis

Map actor → task → current interaction → deterministic evidence → element and model context.
Support each claim with a source file, test or ADR, and separate observed behaviour from
hypotheses and unimplemented features. Cover error, empty, loading, partial-coverage and
version-mismatch states as well as the happy path.

### 2. Three alternative concepts

Propose exactly three genuinely different concepts for the same task. For each, give:

- the workflow hypothesis, primary action, and spatial and evidence hierarchy;
- the interfaces reused, the behaviour preserved and the related ADRs;
- any reference principle and how it is adapted originally;
- trade-offs, keyboard and narrow-view approach, implementation scope and open questions.

Do not edit the application or add functional scope at this stage.

### 3. Visual prototype

The designer returns a comparative visual sheet in chat: three labelled wireframes or original
text/SVG markup, showing viewport size, geometry and evidence regions, and selected and error
states. It is a specification, not a working viewer.

A rendered HTML/CSS prototype is built by the implementer in an isolated, git-ignored location,
with synthetic content only, no dependencies, no external services and no proprietary assets.
Label mocked interactions and unavailable features.

### 4. Comparative evaluation

Score the current design and all three concepts with the rubric below, for the same task, states
and viewports. Link each score to an observable feature, test or prototype annotation. Wireframes
cannot establish task time, WebGL behaviour or accessibility conformance. Recommend a concept and
leave the choice to the maintainer.

### 5. Bounded implementation

The implementer changes only the agreed files and interactions, preserving API and generated
types, viewer behaviour, validation semantics, version checks and IFC bytes. Add or update focused
regression tests first. Stop if the change needs backend, API, schema or dependency changes.

### 6. Regression checks

Run focused Vitest and React Testing Library tests, then the frontend checks in
[frontend/AGENTS.md](../../../frontend/AGENTS.md#checks). Record exact commands and results.

In a browser, using the synthetic fixture, compare unselected, finding-selected and
element-selected states, and check orbit, pan and zoom, GlobalId and highlight coordination,
properties, coverage, errors, and keyboard focus. Check a 1920 × 1080 view and a narrow view.
Record the browser, version and dimensions. If no browser check was possible, say so.

### 7. Review

Summarise the changed files, tests, evidence, limitations and how to revert. Add a CHANGELOG
entry for user-visible changes. Do not start another iteration automatically.

## Weighted evaluation rubric

Score each criterion from 0 to 4: **0** fails or absent, **1** serious weaknesses, **2** partially
addresses the task with material gaps, **3** convincing with minor limitations, **4** compelling
evidence across the agreed states. A criterion without evidence is **unassessed**, not 4 and not
0, and a total is complete only when every criterion has evidence.

| Criterion                                  | Weight | Required comparative evidence                                                                 |
| ------------------------------------------ | ------ | --------------------------------------------------------------------------------------------- |
| Professional BIM usability                 | 25%    | Same triage task, action and attention transitions, coverage discovery and recovery paths     |
| Spatial clarity                            | 20%    | Useful geometry area, occlusion, orientation and legibility of selected/highlighted elements  |
| Visual refinement and originality          | 20%    | Hierarchy, density, typography and state consistency, and the rationale for the adaptation    |
| Evidence integrity and interaction clarity | 20%    | Requirement/check/finding/GlobalId trace, provenance, labels and failure-state clarity        |
| Accessibility and responsive behaviour     | 10%    | Keyboard and focus path, semantics, contrast, narrow view and zoom; 3D limitations            |
| Implementation feasibility                 | 5%     | Reuse of current interfaces, contained scope, testability and no speculative dependency       |

**Total /100 = sum(weight × score / 4)**; the weights sum to 100. Show per-criterion scores,
evidence and confidence for the current design and each concept, and label design-stage
predictions separately from measured results.

Any security or data-integrity violation, deterministic correctness failure, functional
regression or accessibility regression rules a concept out, whatever its score.

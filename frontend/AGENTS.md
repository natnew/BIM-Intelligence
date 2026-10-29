# Frontend UI Change Rules

These instructions apply to every AI coding agent working on frontend UI changes. They supplement
the repository-wide [AGENTS.md](../AGENTS.md); they do not grant approval to change product
direction, architecture, dependencies or visual design.

## Mandatory rules

1. Read the root `AGENTS.md` and [`docs/UI_SPEC.md`](../docs/UI_SPEC.md) before editing.
2. Reference a specific owner-authorised UI iteration ID in every visual change. Do not invent an
   iteration scope; stop if no applicable approved scope exists.
3. Do not invent or assume owner-approved design decisions. Use `UI_SPEC.md` and
   [`docs/UI_REFERENCES.md`](../docs/UI_REFERENCES.md) to distinguish verified behaviour, provisional
   principles, approved decisions and open questions.
4. Change only the explicitly authorised UI scope. Do not bundle unrelated cleanup or redesign.
5. Preserve existing API contracts, application state and validated behaviour.
6. Never change backend files for a visual-only request.
7. Never manually modify generated TypeScript schemas or generated API types.
8. Preserve IFC model rendering, GlobalId mapping, issue highlighting, element selection and
   model-version consistency.
9. Preserve deterministic evidence, citations and finding status semantics. An AI explanation is
   not a `Finding`.
10. Do not remove functionality to simplify a visual layout.
11. Do not change application dependencies without separate owner approval.
12. Maintain keyboard access, visible focus, semantic structure and readable contrast. Verify
    accessibility behaviours affected by the iteration; do not treat lint as an accessibility
    audit.
13. Test both visual presentation and functional behaviour. Record exact commands, results, viewport,
    browser and before/after evidence in `docs/UI_CHANGELOG.md`; never claim browser verification
    that was not performed.
14. Inspect the final Git diff and report every changed file.
15. Stop and request owner approval if the requested UI requires architectural or functional
    changes, API/schema changes, new dependencies or work outside the approved scope.
16. Never commit, push or merge without project-owner approval.

A visually successful change that breaks functionality is a failed iteration.

## Change-control sequence

Follow the owner-directed process in [`docs/UI_SPEC.md`](../docs/UI_SPEC.md): owner supplies a
reference or objective; agent proposes a bounded scope and affected files; owner approves; agent
implements only that scope on a separate branch from the latest approved baseline; agent runs
checks and captures repeatable visual evidence; owner reviews and decides; approved work is recorded
in the UI changelog and summarised in the root changelog. Commit, push and merge require separate
owner approval.

Use the visual and regression verification protocol in `docs/UI_SPEC.md`. If the approved request
cannot be implemented without crossing its boundary, stop rather than silently broadening scope.

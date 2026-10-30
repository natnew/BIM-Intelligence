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

## Private references and testing evidence

- Private materials must never be committed or copied into tracked directories. Use the ignored,
  owner-managed `local-private/ui-references/` for owner-supplied visual references,
  `local-private/test-results/` for private verification evidence, and
  `local-private/professional-feedback/` for raw AEC tester feedback. The owner creates these
  folders locally; do not add placeholders.
- Inspect private files only for the explicitly owner-authorised task. Local availability is not
  permission to inspect unrelated models, documents, screenshots or feedback.
- Do not transmit real BIM files, client documents, screenshots or AEC tester feedback to an LLM
  service without explicit owner approval and applicable data rights, including through tool
  output, attachments, extracted text or excerpts. Local inspection approval is not transmission
  approval.
- Do not publish model-derived facts or private project names without authorisation. The tracked
  reference register and UI changelog contain only non-sensitive reference/evidence identifiers,
  authorised design interpretations and approval decisions, never raw private materials.
- Public demonstration templates must use synthetic or expressly redistributable data with
  recorded provenance and rights. Preserve the T-6 synthetic benchmark and existing test fixtures.
- Keep AI explanations separately labelled from deterministic model findings. An explanation is
  not a `Finding` and must not replace deterministic evidence.
- Any change involving private data handling requires a documented security and provenance review
  before implementation, following the root `AGENTS.md` review requirements. Keep sensitive review
  details private and record only the non-sensitive summary and review identifier in tracked
  documentation. Unresolved permissions block use, transmission or publication.

## Change-control sequence

The [UI constitution](../docs/UI_CONSTITUTION.md) is binding for design quality, conflict
resolution and bounded autonomy. Use the
[bim-ui-refinement skill](../.github/skills/bim-ui-refinement/SKILL.md) for progressive context
loading, reference inventory, three alternatives, comparative prototypes and the weighted rubric.
Select [BIM UI Designer](../.github/agents/bim-ui-designer.agent.md) for read-only proposals;
select [BIM UI Implementer](../.github/agents/bim-ui-implementer.agent.md) only for an explicitly
approved iteration or isolated prototype.

Agree checkpoint outputs, paths, provider permissions, budget and revision cap before starting.
Concept selection is not application-edit approval. The designer cannot create prototype files;
rendered isolated prototypes require separate output approval. Stop after the agreed checkpoint;
no unlimited revisions, unrestricted parallel agents, speculative dependencies or automatic next
task. Time limits in prompts are advisory and require session supervision or supported external
limits. Verify actual host discovery/tools; agent files are not a path sandbox. Optional Copilot
guards in [UI_SPEC §16](../docs/UI_SPEC.md#16-optional-copilot-safeguards--proposal-only)
are proposals only and must not disrupt the Git secret-scanning hook.

Follow the owner-directed process in [`docs/UI_SPEC.md`](../docs/UI_SPEC.md): owner supplies a
reference or objective; agent proposes a bounded scope and affected files; owner approves; agent
implements only that scope on a separate branch from the latest approved baseline; agent runs
checks and captures repeatable visual evidence; owner reviews and decides; approved work is recorded
in the UI changelog and summarised in the root changelog. Commit, push and merge require separate
owner approval.

Use the visual and regression verification protocol in `docs/UI_SPEC.md`. If the approved request
cannot be implemented without crossing its boundary, stop rather than silently broadening scope.

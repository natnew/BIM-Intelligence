# Frontend UI change rules

These rules apply to every contributor, human or AI coding agent, changing the frontend. They
supplement the repository-wide [AGENTS.md](../AGENTS.md).

## Rules

1. Read the root [AGENTS.md](../AGENTS.md) and the components you are changing before editing.
2. Keep each change to the agreed scope. Do not bundle unrelated clean-up or redesign, and discuss
   significant visual or interaction changes in an issue first.
3. Preserve existing API contracts, application state and tested behaviour.
4. Never change backend files for a visual-only change.
5. Never edit generated TypeScript schemas or API types by hand; regenerate them (root AGENTS.md
   §10).
6. Preserve IFC rendering, GlobalId mapping in both directions, finding highlights, element
   selection, camera controls and model-version consistency.
7. Preserve deterministic evidence, citations and finding status. An AI explanation is not a
   `Finding` and must stay visibly labelled as AI-generated or as a template.
8. Do not remove functionality to simplify a layout.
9. Do not add or change dependencies without discussing them first (root AGENTS.md §4).
10. Maintain keyboard access, visible focus, semantic structure and readable contrast. Check the
    accessibility of the behaviour you changed; lint is not an accessibility audit.
11. Test both appearance and behaviour. In the pull request, record the commands you ran, their
    results, and the browser and viewport you checked. Never claim a browser check you did not
    perform; mocked component tests are not a rendered-viewer check.
12. Review the final diff and list every changed file in the pull request.
13. Stop and ask if the change needs architectural or functional changes, API or schema changes,
    or new dependencies.

A change that looks right but breaks functionality is a failed change.

## Checks

From `frontend/`:

```bash
npm run lint
npm run format:check
npm run typecheck
npm run types:check
npm test
npm run build
```

Where a change affects the viewer, also check it in a browser with the synthetic fixture
([`tests/fixtures/minimal.ifc`](../tests/fixtures/minimal.ifc) and
[`minimal.ids`](../tests/fixtures/minimal.ids)): unselected, finding-selected and
element-selected states; orbit, pan and zoom; Focus, Fit and Reset; and keyboard navigation of the
finding list.

## Visual references and test data

- Use synthetic or openly licensed data in screenshots, tests and demonstrations.
- Keep private references, screenshots and feedback outside the repository; never commit or copy
  them into tracked folders. See the
  [private-data rules](../AGENTS.md#private-data-handling-and-provenance).
- Do not send real BIM files, client documents or screenshots of project information to a model
  provider unless you have the right to share them.
- Do not copy proprietary UI assets, code or documentation from other BIM products.

## Optional AI design tooling

The repository includes optional VS Code Copilot customisations for UI work: the
[`bim-ui-refinement` skill](../.github/skills/bim-ui-refinement/SKILL.md), a read-only
[BIM UI Designer](../.github/agents/bim-ui-designer.agent.md) agent for proposing alternatives,
and a [BIM UI Implementer](../.github/agents/bim-ui-implementer.agent.md) agent for implementing an
agreed change. They are development aids, not part of the application, and the rules above apply
to them too.

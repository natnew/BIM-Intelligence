## Summary

<!-- One or two sentences: what changed and why. -->

## Requirement ids served

<!-- e.g. FR-ING-01, NFR-08, ADR-010 — see docs/REQUIREMENTS.md and docs/DECISIONS.md -->

## Validation

- [ ] `ruff check . && ruff format --check .`
- [ ] `mypy`
- [ ] `pytest`
- [ ] Frontend: `npm run lint && npm run typecheck && npm test && npm run build`
- [ ] Documentation updated per AGENTS.md §7 (or not applicable)

## Integrity checklist

- [ ] No `Finding` is created from LLM output (ADR-001)
- [ ] No live API calls added to the default test run (C-06)
- [ ] No files from `hackathon-private/`, `data/` or `.env` are included
- [ ] No claim of working functionality or achieved metrics without a test or recorded run

## Decisions needed from the owner

<!-- Leave empty if none. -->

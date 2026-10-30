# UI Iteration Changelog

This is the append-only, detailed history for owner-directed interface iterations under T-7. It
records proposals and their evidence; it does not grant design approval, commit approval or merge
approval. Keep the root [CHANGELOG.md](../CHANGELOG.md) for significant implementation and merged
changes rather than duplicating this detailed record.

## Record status

No visual UI iteration has been recorded. This governance framework is not a visual iteration; it
does not create or approve a UI-001 scope. Do not fabricate prior decisions, screenshots or test
results.

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

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

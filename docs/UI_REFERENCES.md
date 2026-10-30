# UI Reference Register

This register records design interpretation, not a licence to copy. BIM Intelligence may study a
reference's interaction or information hierarchy and adapt the underlying idea to its own
requirements. Do not copy proprietary source code, interface assets, product names as branding or
vendor visual identity.

## Reference handling

- The owner supplies or approves each reference and identifies the feature to study.
- Prefer a public reference URL and describe the relevant feature in words.
- The preferred private location for owner-supplied visual references is the git-ignored
  `local-private/ui-references/`. The owner creates and populates it locally; do not add
  placeholders. An owner-approved private store outside the working tree remains an alternative.
- Private screenshots and source materials must never be committed or copied into tracked
  directories. Availability is not permission to inspect: inspect only for the explicitly
  authorised task, and do not transmit private references to an LLM service without explicit
  owner approval and applicable data rights.
- Record non-sensitive reference identifiers and interpreted design decisions here, not the
  private materials. Use neutral filenames such as `REF-001.png`; if a path reveals private project
  or personal information, record only the reference ID and keep its location mapping private.
  Do not publish model-derived facts or private project names without authorisation.
- Keep raw AEC tester feedback in `local-private/professional-feedback/` and private verification
  evidence in `local-private/test-results/`. Record only authorised, non-sensitive decision
  summaries here. Private data handling changes require the security and provenance review
  defined in [AGENTS.md](../AGENTS.md).
- A reference is not an approved design. Record owner feedback and approval status explicitly.
- Link every implementation to its UI iteration ID in `UI_CHANGELOG.md`.

## Register

No owner references have been supplied or approved yet.

## Entry template

Copy this section for each reference. Assign an ID only when the owner supplies or approves the
reference.

### REF-___ — [short feature name]

- **Reference ID:** `REF-___`
- **Software or design source:** [product, publication, design system or project]
- **Screenshot or reference location:** [public URL, neutral path under
  `local-private/ui-references/`, or reference ID with location mapping kept private]
- **Specific design feature being studied:** [name the interaction or visual feature]
- **Why that feature may be useful:** [workflow need it may address]
- **Proposed adaptation to BIM Intelligence:** [interpretation; do not copy source assets or code]
- **Interpreted design decision:** [non-sensitive interpretation and rationale; not approval]
- **Owner feedback:** [authorised, non-sensitive decision summary; `Awaiting owner input` until supplied]
- **Approval status:** [Awaiting owner input / Proposed / Approved / Rejected / Superseded]
- **Related UI iteration ID:** [ID or `None`]

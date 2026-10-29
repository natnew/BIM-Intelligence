# UI Reference Register

This register records design interpretation, not a licence to copy. BIM Intelligence may study a
reference's interaction or information hierarchy and adapt the underlying idea to its own
requirements. Do not copy proprietary source code, interface assets, product names as branding or
vendor visual identity.

## Reference handling

- The owner supplies or approves each reference and identifies the feature to study.
- Prefer a public reference URL and describe the relevant feature in words.
- If an image is needed, keep the screenshot in an owner-approved private local reference store
  outside the repository working tree, or in a pre-existing git-ignored location, unless its
  redistribution rights are established. Do not add third-party screenshots to tracked files as a
  convenience.
- Record a local path only if it is private and accessible to the owner; do not place secrets,
  credentials or private project data in this register.
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
- **Screenshot or reference location:** [public URL or private local path outside tracked source]
- **Specific design feature being studied:** [name the interaction or visual feature]
- **Why that feature may be useful:** [workflow need it may address]
- **Proposed adaptation to BIM Intelligence:** [interpretation; do not copy source assets or code]
- **Owner feedback:** [verbatim or concise decision record; `Awaiting owner input` until supplied]
- **Approval status:** [Awaiting owner input / Proposed / Approved / Rejected / Superseded]
- **Related UI iteration ID:** [ID or `None`]

# Changelog

All notable changes to BIM Intelligence are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 4 November 2026

First public version, built for the Meta Global AI Developer Hackathon
(26 October – 4 November 2026).

### Added

**Model and requirement ingestion**

- Upload one IFC model per review session (IFC2X3, IFC4 and IFC4X3). Each upload is stored
  byte-for-byte as a content-addressed version and indexed with IfcOpenShell; the model is never
  modified.
- Import buildingSMART IDS 1.0 files. Each specification becomes a confirmed requirement bound to
  an immutable, versioned check.
- Store Markdown and plain-text documents as untrusted source material.
- Add the built-in `classification.consistent_by_type` native rule for a check IDS 1.0 cannot
  express.

**Deterministic review**

- Run reviews with IfcTester and registered native rules. Each finding records the affected
  elements, expected and observed values, the requirement and the rule version.
- Pin every review run to the model hash, document hashes and requirement revisions. Repeated runs
  over the same inputs produce byte-identical findings.
- Report skipped, errored and not-applicable checks explicitly, so they are never mistaken for a
  pass.

**Muse Spark assistance (Meta Model API)**

- AI review planning: Muse Spark interprets a plain-language objective and selects from the
  confirmed checks only. Plans that reference unknown, unconfirmed or duplicate checks, or exceed
  the execution caps, are rejected.
- Grounded explanations on request: a finding's explanation is schema-validated and its citations
  are checked against the recorded evidence, with a clearly labelled deterministic template when
  that check fails. Explanations are always shown separately from findings.
- Narrative requirement extraction (API only): requirement candidates extracted from Markdown or
  text must quote their source verbatim and be confirmed by a person.
- Off, Replay and Live modes, with Off as the default. Live mode needs explicit configuration and
  is protected by a persistent spend ledger with per-call, per-review and per-installation caps.

**Web application**

- Project Home with new-review setup, reopening a session by id or link, recent sessions remembered
  in the browser, and an overview of the review workflow.
- Review workspace with requirement scope selection, a review objective, **Run AI Review** and an
  explicit **Continue without AI** path.
- Interactive 3D viewer built on That Open Components: selecting a finding highlights its element,
  clicking an element shows its properties and linked findings, and Focus, Fit and Reset camera
  controls.
- Evidence inspector showing observed and expected values, plan provenance and the source of each
  explanation.

**Quality and evaluation**

- A synthetic IFC4 benchmark generator with defect injection, and a runner that reports precision,
  recall and F1 by rule family. On the 15-defect benchmark every metric is 1.000; this is a
  narrow synthetic result, not a measure of accuracy on real projects.
- Backend (pytest) and frontend (Vitest) test suites that make no live API calls, with a single
  opt-in live smoke test.
- Redacted secret scanning with a pre-commit hook.

### Known limitations

- One IFC model per session; no federation or clash detection.
- Narrative requirement confirmation is available through the API only, not in the browser.
- No report export, PDF upload or one-click sample loader.
- No authentication or hosted deployment.

[Unreleased]: https://github.com/natnew/BIM-Intelligence/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/natnew/BIM-Intelligence/releases/tag/v0.1.0

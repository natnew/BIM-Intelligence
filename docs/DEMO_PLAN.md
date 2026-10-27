# Demo Plan

**Status:** v0.1. Format constraints (video length, live vs recorded, judging criteria) are **unverified** because the hackathon rules were not available at the time of writing (OPEN-02). The plan assumes a three-minute video as stated in the brief.

## 1. Storyline (3:00)

**Persona:** a BIM Coordinator preparing an architectural model for a Stage 4 issue.
**Message:** "Project requirements in, verified findings out — explained, in 3D, and traceable."

| Time | Beat | On screen | Narration (key points) |
|---|---|---|---|
| 0:00–0:20 | Problem | Title card → split view: a BEP page and a wall of checker output | Pre-issue QA means turning prose requirements into checks and triaging hundreds of unexplained flags. |
| 0:20–0:45 | Ingest | Upload IFC → model summary; upload BEP | The model is indexed with IfcOpenShell; the BEP is read as text. |
| 0:45–1:15 | Requirements | Extracted candidates with verbatim quotes and compiled IDS checks; coordinator confirms two, edits one, rejects one | Muse Spark proposes requirements; every proposal carries its source quote; nothing runs until a human confirms. |
| 1:15–1:40 | Objective and plan | Type "Check fire-rating and classification completeness on external walls and doors for Stage 4" → plan appears with reasons; progress stream | The orchestrator selects checks from a bounded tool registry. Findings come only from IfcTester and deterministic rules. |
| 1:40–2:20 | Triage in 3D | Findings list → click a finding → affected walls highlight → detail panel shows observed vs expected, the BEP quote, and the AI explanation labelled as AI-generated with a "grounded" badge | Each finding is verified by rule; the explanation can only cite evidence the system has. |
| 2:20–2:45 | Report | Open Markdown report: traceability matrix requirement → rule → finding → element; provenance block | A traceable report, with model hash, rule versions and the model id used. |
| 2:45–3:00 | Evidence and close | Evaluation table: measured precision/recall on the labelled benchmark, grounding rate, token cost | State the measured numbers, whatever they are. Close on the design principle. |

## 2. Required functional capabilities

The demo cannot be recorded until each row is implemented and passes its acceptance criterion.

| Beat | Requirements | Milestone |
|---|---|---|
| Ingest | FR-ING-01, FR-ING-02, FR-REQ-01 | M0 / M2 |
| Requirements | FR-REQ-02, FR-REQ-03, FR-REQ-04 | M2 |
| Objective and plan | FR-REQ-06, FR-REQ-07, FR-VIS-05 | M2 |
| Triage | FR-VAL-01..04, FR-EXP-01..03, FR-EXP-05, FR-VIS-01..04 | M1 / M3 |
| Report | FR-REP-01, FR-REP-02 | M3 |
| Evidence | NFR-01, NFR-02, NFR-03, NFR-05 measured | M4 |

## 3. Visual sequence and assets

- Screen recording at 1920×1080, browser only (no terminal with environment variables visible).
- Benchmark model with injected defects (`datasets/synthetic/benchmark.ifc`) — small enough to load in seconds.
- Pre-scripted objective text and requirement decisions so the run is reproducible.
- Title and closing cards: project name, one-line description, link to repository, "Built with Meta Muse Spark via the Meta Model API".
- Lower-third labels on AI-generated content so the audience sees the labelling convention.

## 4. Technical evidence to show

1. The `Finding.method` value (`ids` or `native`) and rule version chip — proves deterministic origin.
2. The verbatim BEP quote next to the compiled IDS facet — proves requirement traceability.
3. The run log excerpt: plan, tool calls, token usage — proves bounded orchestration and cost awareness.
4. The grounding badge and one example where the grounding check rejected a draft (from the log) — proves the safeguard is real, not decorative.
5. The evaluation metrics table with commit hash.

## 5. Live-demo fallback strategy

| Failure | Fallback |
|---|---|
| API unreachable or rate-limited | Start the backend with `LLM_MODE=replay`; recorded responses from the rehearsal replay the identical plan and explanations. |
| Replay mismatch (changed inputs) | `LLM_MODE=off`; default plan runs; templated explanations; degraded banner is itself a talking point. |
| Viewer fails to load | Findings panel and report still work; switch to a pre-captured viewer clip. |
| Complete environment failure | Play the pre-recorded video. |

The primary submission is the **recorded video**; a live walkthrough, if required, follows the same script with the replay fallback armed.

## 6. Rehearsal checklist (Day 9)

- [ ] Fresh session; benchmark loads in < 10 s in the browser.
- [ ] Extraction produces the expected candidates from `benchmark_bep.md` (replay).
- [ ] Objective produces the expected plan (replay).
- [ ] Highlight sync works for every finding in the demo path.
- [ ] Report renders; traceability matrix complete.
- [ ] Recording captured; replay fixtures committed; `LLM_MODE=replay` tested end to end.
- [ ] No secrets visible in any frame.

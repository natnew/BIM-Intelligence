# Demo Plan

**Required output:** one functioning three-minute video. This is the owner-directed delivery
requirement; confirm the official event rules and eligibility before submission (OPEN-02).
**Status, 1 November 2026:** the script below is an exactly 180-second **proposed fallback**, not a
recording. No video, actual duration or working video link has been supplied or verified. The
deterministic workflow was exercised on the synthetic fixture; the requested user-facing Meta
workflow and one-click sample are not implemented. Do not claim that this fallback meets
unverified event eligibility.

## 1. Product and evidence boundary

BIM Intelligence is one AI-native AEC model-review application. The existing demonstrable
workflow is a single IFC session with deterministic IDS/native checks, source-backed findings and
3D element inspection. UI-003's Project Home, upload and viewer walkthrough is recorded in
[UI_CHANGELOG.md](./UI_CHANGELOG.md). The T-6 benchmark has a locally recorded result on a small
synthetic IFC4 model; its limitations and the outstanding hosted-CI status are in
[EVALUATION.md](./EVALUATION.md).

Do not script or narrate the following as working before the gates pass:

| Capability | Current evidence | Recording rule |
|---|---|---|
| One-IFC Project Home and review workspace | UI-003 tests and recorded browser walkthrough | May show the tested session → IFC/IDS upload → workspace → review path. |
| Deterministic IDS/native checks and source-backed evidence | Tests and UI-003 browser walkthrough on committed synthetic fixtures | May show only the actual run, check outcomes, selected finding and element evidence. |
| Muse Spark-assisted workflow | Backend planner/explanation have offline Fake/Replay tests; one basic live smoke is owner-reported, but live BIM use and frontend integration are unverified | Show a Meta-assisted objective/explanation only after a real approved integration test. Label the actual plan/explanation source and any fallback. Never present default, Fake or Replay output as a live inference. |
| Report/export | Run manifests and evidence exist in API contracts; complete report endpoint/UI remains outstanding | Do not show a fabricated report or download. Include only after the actual export passes provenance checks. |
| Camera recovery controls | UI-004A Fit, Reset and Focus are merged and were exercised in the synthetic browser walkthrough | Show the real controls and their actual effect; do not imply unimplemented camera modes. |
| Recent sessions / sample catalogue | Project Home marks them unavailable | A one-click synthetic sample may be included only after it exists and is tested; until then use the current create/upload workflow. |
| Two-model federation and clashes | FED-001 is a synthetic geometry feasibility harness, not an integrated application workflow | Include only after every coordination go/no-go condition passes; otherwise omit all clash/federation claims. |

If coordination is a no-go, the intended delivery fallback is the working IDS/native review with
the Meta-assisted path only when its frontend integration and required owner-authorised verification
are real. If Meta integration or live use is not approved/verified, say so plainly; a deterministic
only recording must not be described as Meta-assisted or as satisfying an unverified eligibility
rule.

## 2. Three-minute storyboard

**Persona:** a BIM Coordinator reviewing one architectural IFC against a confirmed project IDS.
The ten shots below total **180 seconds**. Timing is a target until a real recording is measured.
Use the actual application throughout; the final title card is a labelled closing graphic.

| Time | Shot and actual screen action | Concise narration |
|---|---|---|
| 0:00–0:12 | **1 — Home:** show BIM Intelligence and the offline health state. | “BIM Intelligence is an AEC model-review prototype built during this hackathon. This walkthrough uses synthetic data with AI switched off.” |
| 0:12–0:32 | **2 — Inputs:** create a session; choose the synthetic IFC and IDS; show the indexed and two-requirement confirmations. | “A reviewer creates a session, imports one read-only IFC and an IDS, and sees which requirements are executable.” |
| 0:32–0:50 | **3 — Model:** open the workspace, show the IFC4 summary and three rendered walls, then orbit the model. | “The viewer renders the actual model. Its version hash ties subsequent evidence to these source bytes.” |
| 0:50–1:10 | **4 — Review:** select **Run review** and show coverage and **Deterministic default**. | “The deterministic review executes two IDS checks. The run completed, but both checks found an issue; completion does not mean compliance.” |
| 1:10–1:35 | **5 — Fire rating:** select W-002; show the highlighted wall, observed and expected values, rule and source requirement. | “W-002 is an external wall without the required fire rating. The finding links the affected element to the exact check and source requirement.” |
| 1:35–1:55 | **6 — Classification:** select W-003 and show its linked element and missing classification evidence. | “W-003 lacks the required classification. These findings come from the deterministic IDS checks, not from a language model.” |
| 1:55–2:15 | **7 — Model selection:** reset the view and click W-001; show its properties and zero linked findings. | “Selecting a wall in the model opens its element record. No linked finding here means only that this run did not flag it.” |
| 2:15–2:35 | **8 — Navigation:** reselect W-002, use **Focus selected**, pan or zoom, then **Fit model** and **Reset view**. | “Finding and model selection stay connected. Focus, Fit and Reset provide a way to investigate and recover the view.” |
| 2:35–2:50 | **9 — AI boundary:** show the selected finding's **AI explanation · not connected** notice. | “Muse Spark is the intended interpretation provider, but this build does not expose that workflow. No AI response is shown.” |
| 2:50–3:00 | **10 — Close:** display the final title card below. | “Our original work links versioned IFC review, deterministic evidence and 3D investigation, using open-source BIM tools.” |

### Dataset, attribution and evidence captions

- Use the committed, project-authored synthetic
  [`minimal.ifc`](../tests/fixtures/minimal.ifc) and
  [`minimal.ids`](../tests/fixtures/minimal.ids), generated by
  [`make_minimal_ifc.py`](../tests/fixtures/make_minimal_ifc.py) and covered by the repository
  [MIT licence](../LICENSE). The IFC SHA-256 is
  `f2bd00074c54866d95c5c344a1c604e01cdb8ea394b9b20937952b7b38c74348`; the IDS SHA-256 is
  `e602233db1e9aa8e77b2a4f90371db42df9879ee2f6331251f7aab84f2f1ce74`.
- Suggested on-screen captions: **Synthetic IFC/IDS · AI off**; **IFC4 · model version f2bd00074c54**;
  **2 IDS checks · 2 findings · deterministic default**; **W-002 · missing FireRating**;
  **W-003 · missing classification**; **W-001 · no linked findings in this run**.
  Captions describe actual results and must not hide a different or failed run.
- Credit the project's original session/version integration, deterministic review/evidence
  workflow and 3D interaction as hackathon work. Identify IfcOpenShell, IfcTester and That Open
  Components as third-party tools, not original project code. Distribution-specific notices and
  image/logo rights remain subject to [third-party review](../THIRD_PARTY_NOTICES.md).
- Repository history records the minimal fixture/contracts in `be45c7c` on 27 October, IFC
  ingestion in `de63de8` on 28 October and the 3D viewer in `6b6cd15` on 29 October 2026.
  These dates establish when those project contributions appeared, not authorship of the
  third-party libraries.

### Browser preparation and recording

1. Use a fresh local session and the exact synthetic fixtures above. Start the existing backend and
   frontend using the [setup instructions](../README.md#local-setup), with `LLM_MODE=off` and
   `ALLOW_LIVE_LLM=false`; verify the health panel. Do not open private models or documents.
2. Prewarm the application and local viewer assets, then return to Project Home. Have the two
   fixture files ready in the file chooser; do not pre-populate or substitute findings. Rehearse
   the real upload, review and selection path before recording.
3. Use a 1920 × 1080 desktop viewport, 100% browser zoom, a legible cursor and the existing
   Concept C shell. Close unrelated tabs, notifications and applications; do not expose credentials,
   private paths or unrelated sessions.
4. Record screen and narration at 1920 × 1080, 30 fps, SDR, using a broadly playable H.264 MP4
   and clear audio; avoid unlicensed music. Preserve the unedited source in an owner-approved
   ignored location. Do not crop or edit the recording to imply that a failed or absent feature
   worked.
5. After recording, measure the exported duration and check audio, legibility, actual captions,
   source attribution and the final link. A planned 3:00 timeline is not evidence of a 3:00 file.

**Final title card, 2:50–3:00:** “BIM Intelligence | AEC model review” followed by
“Synthetic IFC/IDS · deterministic findings · AI off”. Add a small attribution line:
“Built during the hackathon with IfcOpenShell, IfcTester and That Open Components”. Do not display
a repository or video link as public until it is accessible and verified.

## 3. Coordination insert — all conditions required

Include the optional matrix/3D insert only if, by the cutoff in
[FINAL_48_HOUR_PLAN.md](./FINAL_48_HOUR_PLAN.md):

1. Two separate immutable IFC model versions, hashes, member identities, discipline labels and
   placement metadata are present; the one-model `Session` contract is unchanged.
2. Both models have a tested, explicit common coordinate frame; unknown or unsupported alignment
   is rejected before analysis.
3. An installed, version-verified deterministic geometric capability passes intersection,
   no-intersection, tolerance-boundary, exclusions, unsupported-entity, stale-hash and repeated-run
   tests. No unapproved dependency or private model is used.
4. The matrix contains only actual computed counts, clearly separates raw intersections, grouped
   clashes and human-assessed issues, and shows every required unavailable/zero/error state
   honestly.
5. Selecting a result loads and highlights the actual model-scoped element pair and shows evidence
   with both hashes and the run identity.
6. Rights, attribution, privacy, regression and browser-recording checks pass; all source files are
   approved for the exact inspection/recording/publication scope.

The preferred external candidate is Duplex Apartment, subject to model compatibility and explicit
rights verification. Do not inspect `local-private/` without task-specific authorisation. If the
candidate is unsuitable or rights are unresolved, omit coordination; the one-click synthetic
single-model sample is not yet available. Use the manual synthetic IFC/IDS workflow instead; it
is not a clash substitute.

## 4. Recording and submission checks

- Record at 1920 × 1080 with browser chrome minimised; no secrets, environment values, private paths,
  client data or unrelated processes may be visible.
- Use a fresh, reproducible session and record the exact fixture/model hash, run ID and app commit in
  private evidence notes. Use only permitted synthetic or explicitly redistributable inputs.
- Capture only real application states. AI labels, `plan_source`, explanation source and fallback
  must match the run. Findings remain deterministic.
- Save the unedited recording and verification notes under an owner-approved ignored/private
  location, not tracked `docs/`, `examples/` or `datasets/`. Upload/submit only through the
  owner-approved event process.
- Recheck video duration, audio, readability, no secret exposure, public repository links,
  attribution and third-party asset rights. Confirm the official rules and submission format.
- Do not release, tag, deploy or submit without the project owner's explicit approval.

## 5. Safe fallback

If a live provider, optional coordination path, report, viewer control or recording step fails,
remove that segment and retain only the last verified single-model review path. A recorded clip is
not a substitute for an untested product feature. If the remaining recording cannot truthfully
meet the Meta-assisted or official submission criteria, report that gap to the owner rather than
claiming success.

If a session has expired, create a new one and re-upload the two synthetic fixtures. If a required
viewer interaction fails, stop and report the failure rather than substituting a static image. A
Replay may be shown only when its original genuine Meta request and response are preserved and
verified, its use is authorised, and it is visibly labelled as a recording. The owner-reported
smoke has no raw request/response recording in this repository, so it cannot be turned into a
verified replay here. Never invent one.

## 6. RELEASE-001 release report — no-go

1. **Working:** manual single-IFC/IDS upload, deterministic review, two-way finding/element
   selection, evidence inspection and the UI-004A camera controls were exercised on synthetic
   data. Explicit session/run-ID reopening works.
2. **Tests:** 616 non-live backend tests and 91 frontend tests passed; backend lint, formatting,
   typing and schema parity, frontend checks and build passed. Build warnings and the upstream
   deprecation warning are recorded in [EVALUATION.md](./EVALUATION.md#release-001-offline-verification--1-november-2026).
   Hosted main CI ended in `startup_failure` before running jobs.
3. **Meta:** one earlier owner-reported `muse-spark-1.3` basic structured-output smoke is
   recorded in [EVALUATION.md](./EVALUATION.md#t-5-live-structured-output-smoke-1-november-2026).
   Its raw request and source commit were not supplied. No live BIM objective/explanation or
   new paid call was verified; offline API fallback was correctly labelled deterministic.
4. **Clashes:** the synthetic FED-001 feasibility harness has tests, but no production matrix,
   federated viewer or matrix/3D linkage is integrated. Omit clash claims from the video.
5. **Video:** this is a 180-second script, not a recorded or rehearsed video. Actual duration
   and a working video link are unavailable.
6. **Limitations:** final UI-001 objective/explanation controls, browser-local recent sessions,
   one-click sample, report export, benchmark browser smoke and complete accessibility review
   remain open. The benchmark is small and synthetic.
7. **Publication:** the repository is private; the redacted history scan found no leaks in 96
   scanned commits, and the checked Git paths contained no private/runtime files or IFCs outside
   allowed locations. This is not a guarantee. Dependency distribution obligations and the
   recorded image/logo provenance questions still require owner review; a clean-install setup
   and public access have not been verified.
8. **Blockers:** the required UI-001 implementation approval packet and implementation, hosted
   CI, video and link, public-access decision, third-party rights, official event rules and
   submission fields remain outstanding. The milestone table lists M4 as not started while older
   changelog/final-48-hour wording says in progress; neither records completion. No release,
   publication or submission is authorised.
9. **Exact baseline:** implementation commit `484b71c7988295159083121fab77e1713c825903`;
   merged `main` commit `cf06328c874258efe8a49d0afa291d9aef278928`, with the same tree. There is
   no verified final release commit.
10. **Recommendation:** **NO-GO** for release or submission until the missing work and owner
    decisions are completed and the integrated candidate is reverified.

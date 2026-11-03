# Demo Plan

**Required output:** one functioning three-minute video. This is the owner-directed delivery
requirement; confirm the official event rules and eligibility before submission (OPEN-02).
**Status, 3 November 2026:** the storyboard below is a **planned 180-second recording**, not
evidence that a video was recorded, rehearsed, uploaded or accepted. VERIFY-010 passed one
authorised live synthetic plan and grounded explanation on
`588e6adf9ca71079eadc0e5b33422dc6605df743`; the preceding VERIFY-009 acceptance failed.
Any new paid request needs separate owner approval. Official event rules and eligibility remain
unverified.

## 1. Product and evidence boundary

BIM Intelligence is one AI-native AEC model-review application. The existing demonstrable
workflow is a single IFC session with guided objective planning, deterministic IDS/native checks,
source-backed findings, 3D element inspection and an on-request explanation. UI-003's Project
Home, upload and viewer walkthrough is recorded in
[UI_CHANGELOG.md](./UI_CHANGELOG.md). The T-6 benchmark has a locally recorded result on a small
synthetic IFC4 model; its limitations and the outstanding hosted-CI status are in
[EVALUATION.md](./EVALUATION.md).

Do not script or narrate the following as working before the gates pass:

| Capability | Current evidence | Recording rule |
|---|---|---|
| One-IFC Project Home and review workspace | UI-003 tests and recorded browser walkthrough | May show the tested session → IFC/IDS upload → workspace → review path. |
| Deterministic IDS/native checks and source-backed evidence | Tests and UI-003 browser walkthrough on committed synthetic fixtures | May show only the actual run, check outcomes, selected finding and element evidence. |
| Muse Spark-assisted workflow | VERIFY-010 passed one owner-approved live synthetic planner and grounded explanation; VERIFY-009 failed at explanation generation | Show a genuine Live plan/explanation only if the actual recording session is separately approved and succeeds. Label source, model and grounding; never present default, Fake or Replay output as a live inference. |
| Report/export | Run manifests and evidence exist in API contracts; complete report endpoint/UI remains outstanding | Do not show a fabricated report or download. Include only after the actual export passes provenance checks. |
| Camera recovery controls | UI-004A Fit, Reset and Focus are merged and were exercised in the synthetic browser walkthrough | Show the real controls and their actual effect; do not imply unimplemented camera modes. |
| Recent sessions / sample catalogue | Browser-local recent sessions are implemented; no one-click sample catalogue | Reopen a valid local session if useful; for a fresh demo manually upload the committed synthetic fixture. |
| Two-model federation and clashes | FED-001 is a synthetic geometry feasibility harness, not an integrated application workflow | Include only after every coordination go/no-go condition passes; otherwise omit all clash/federation claims. |

Coordination is currently a no-go: omit it. If Live use is not separately approved or the
recording session fails, use the explicitly labelled deterministic fallback below. Do not describe
that fallback as Meta-assisted or as satisfying an unverified eligibility rule.

## 2. Three-minute storyboard

**Persona:** a BIM Coordinator reviewing one architectural IFC against a confirmed project IDS.
The ten shots below total **180 seconds**. Timing is a target until a real recording is measured.
Use the actual application throughout; the final title card is a labelled closing graphic.

| Time | Shot and actual screen action | Concise narration |
|---|---|---|
| 0:00–0:12 | **1 — Home:** introduce the application and its actual configuration. | “Architects and BIM Coordinators need to check project information without losing the connection to the model.” |
| 0:12–0:32 | **2 — Inputs:** create a session and manually upload the synthetic IFC and IDS. | “This prototype reads one IFC without changing it and imports the reviewed IDS specifications as confirmed checks.” |
| 0:32–0:49 | **3 — Model:** show the indexed IFC, confirmed requirements and 3D model. | “The model version and confirmed requirements bind this review to its inputs.” |
| 0:49–1:10 | **4 — Guided objective:** show the scope selector and enter the fire-rating objective; request an authorised AI review. | “The reviewer selects the permissible requirements and asks Muse Spark to propose relevant checks.” |
| 1:10–1:30 | **5 — Actual plan:** show the returned Live mode, model, selected check and coverage. | “Code validates the proposed plan against the confirmed scope and execution limits before any check runs.” |
| 1:30–1:50 | **6 — Finding:** select the W-002 fire-rating finding and show observed/expected evidence and its source check. | “IfcTester, not the model, identifies the missing fire-rating information and records the evidence.” |
| 1:50–2:10 | **7 — 3D investigation:** highlight W-002; demonstrate **Focus selected**, **Fit model** and **Reset view**, then select an element. | “The finding and the model are linked, so the reviewer can investigate the affected element in context.” |
| 2:10–2:30 | **8 — Explanation:** explicitly request and show the actual grounded AI explanation and its source label. | “On request, Muse drafts an explanation from the recorded evidence. The application checks its citations and identifiers.” |
| 2:30–2:50 | **9 — Boundaries:** show check coverage and explanation provenance, including any skipped check. | “The finding is deterministic; the explanation is model-generated. A partial review or grounded response is not a blanket compliance verdict.” |
| 2:50–3:00 | **10 — Close:** show the title card and third-party credits. | “BIM Intelligence combines versioned review, transparent evidence and 3D investigation.” |

### Dataset, attribution and evidence captions

- Use the committed, project-authored synthetic
  [`minimal.ifc`](../tests/fixtures/minimal.ifc) and
  [`minimal.ids`](../tests/fixtures/minimal.ids), generated by
  [`make_minimal_ifc.py`](../tests/fixtures/make_minimal_ifc.py) and covered by the repository
  [MIT licence](../LICENSE). The IFC SHA-256 is
  `f2bd00074c54866d95c5c344a1c604e01cdb8ea394b9b20937952b7b38c74348`; the IDS SHA-256 is
  `e602233db1e9aa8e77b2a4f90371db42df9879ee2f6331251f7aab84f2f1ce74`.
- Suggested on-screen captions: **Synthetic IFC/IDS**; **IFC4 · model version f2bd00074c54**;
  **Live Muse plan · confirmed-check scope**; **W-002 · deterministic IDS finding**;
  **AI-generated explanation · grounding passed**. Use each only if the recorded run actually
  displays it; do not hide skipped checks, a different plan or a failure.
- Credit the project's original session/version integration, deterministic review/evidence
  workflow and 3D interaction as hackathon work. Identify IfcOpenShell, IfcTester and That Open
  Components as third-party tools, not original project code. Distribution-specific notices and
  image/logo rights remain subject to [third-party review](../THIRD_PARTY_NOTICES.md).
- Repository history records the minimal fixture/contracts in `be45c7c` on 27 October, IFC
  ingestion in `de63de8` on 28 October and the 3D viewer in `6b6cd15` on 29 October 2026.
  These dates establish when those project contributions appeared, not authorship of the
  third-party libraries.

### Browser preparation and recording

1. Obtain separate owner approval for the recording session's paid calls. Use a fresh local
   session and the exact synthetic fixtures above. Start the backend and frontend using the
   [setup instructions](../README.md#local-setup) and
   [Live configuration](../README.md#configure-an-authorised-live-demonstration). Verify the
   displayed mode; health alone does not establish provider connectivity. Do not open private
   models or documents.
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
“Synthetic IFC/IDS · deterministic findings · separately labelled AI”. Add a small attribution line:
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

If Live is not approved or the provider fails, keep the same ten shot boundaries and 180-second
target, but change shots 4–5 to show **Continue without AI** and the actual deterministic plan;
change shot 8 to show the explicitly labelled deterministic template; and change shot 9 and the
title card to say **AI off / deterministic fallback**. Never reuse narration or captions that
claim a Live plan or AI-generated explanation. A failed viewer interaction or recording step
must be reported rather than fabricated. If this reduced scope cannot meet the official
submission criteria, report that gap to the owner.

If a session has expired, create a new one and re-upload the two synthetic fixtures. If a required
viewer interaction fails, stop and report the failure rather than substituting a static image. A
Replay may be shown only when its original genuine Meta request and response are preserved and
verified, its use is authorised, and it is visibly labelled as a recording. The owner-reported
smoke has no raw request/response recording in this repository, so it cannot be turned into a
verified replay here. Never invent one.

## 6. RELEASE-001 release report — historical no-go (1 November 2026)

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

## 7. Current release position — 3 November 2026

The historical report above predates the merged guided AI interface, browser-local history,
FIX-002, FIX-003 and the VERIFY-010 synthetic live pass. Its older statement that these
interfaces did not exist is not current. VERIFY-009 remains a failure, and VERIFY-010 is one
successful scenario, not general reliability evidence. The latest hosted main workflow failed
before jobs started; no clean install, benchmark Playwright smoke, video, public-access decision,
official rules or complete distribution-rights review has been verified. T-7/M3 and T-8 remain
in progress, M4 remains gated by M3, and the release/submission decision remains **NO-GO**.

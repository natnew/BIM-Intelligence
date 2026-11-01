# Demo Plan

**Required output:** one functioning three-minute video. This is the owner-directed delivery
requirement; confirm the official event rules and eligibility before submission (OPEN-02).
**Status:** the storyboard below is a recording plan, not evidence that every segment is already
implemented. Record only paths that pass their stated acceptance tests.

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
| Muse Spark-assisted workflow | Backend planner/explanation have offline Fake/Replay tests; live API and frontend integration are unverified | Show a Meta-assisted objective/explanation only after a real approved integration test. Label the actual plan/explanation source and any fallback. Never present default, Fake or Replay output as a live inference. |
| Report/export | Run manifests and evidence exist in API contracts; complete report endpoint/UI remains outstanding | Do not show a fabricated report or download. Include only after the actual export passes provenance checks. |
| Camera recovery controls | Fit/reset/focus controls are deferred | Do not show mock buttons or narrate unsupported controls. |
| Recent sessions / sample catalogue | Project Home marks them unavailable | A one-click synthetic sample may be included only after it exists and is tested; until then use the current create/upload workflow. |
| Two-model federation and clashes | No implementation; feasibility gate not yet passed | Include only after every coordination go/no-go condition passes; otherwise omit all clash/federation claims. |

If coordination is a no-go, the intended delivery fallback is the working IDS/native review with
the Meta-assisted path only when its frontend integration and required owner-authorised verification
are real. If Meta integration or live use is not approved/verified, say so plainly; a deterministic
only recording must not be described as Meta-assisted or as satisfying an unverified eligibility
rule.

## 2. Three-minute storyboard

**Persona:** a BIM Coordinator reviewing an architectural IFC against a confirmed project IDS.
**Source data:** the committed synthetic minimal IFC/IDS fixture or an approved one-click synthetic
sample. No private model, client document, unapproved third-party material, credentials or terminal
output appears in the video.

| Time | Beat | On screen | Narration and evidence |
|---|---|---|---|
| 0:00–0:12 | Product and scope | BIM Intelligence title; one-line purpose | “BIM Intelligence is an AEC model-review application. This recording shows one version-pinned IFC and deterministic checks; it does not claim enterprise clash management.” |
| 0:12–0:38 | Start review | Project Home → create a review session → upload the synthetic IFC and IDS → open workspace | Show actual upload/indexed states and the model summary. If a one-click sample is not implemented and tested, use these existing steps; do not imply a catalogue exists. |
| 0:38–0:54 | Model context | Loaded 3D model, model identity/version, storeys and coverage panels | Show the real viewer and recorded navigation. Do not claim Fit All/Reset/Focus controls. |
| 0:54–1:20 | Run a review | Run review and inspect the actual plan source/check outcomes | Default route: show `plan_source: default` and deterministic check status. Optional AI route: only if integration is verified and live use is owner-authorised; show actual `plan_source`, model identity, and whether the result was AI or fallback. Do not use Fake/Replay as evidence of live inference. |
| 1:20–1:55 | Investigate findings | Select a real failed check/finding; highlight the element; inspect observed/expected, source, rule and model version | Distinguish deterministic finding/evidence from any AI explanation. If no approved live explanation is available, show the current evidence inspector without claiming an AI panel. |
| 1:55–2:15 | Verify provenance | Show the run manifest or existing review coverage and element link | Point to actual model hash, requirement/check identity, rule version and affected element. Do not present an unimplemented export as a report. |
| 2:15–2:42 | Optional bounded feature slot | Coordination only if the gate passes; otherwise a second real finding or deterministic control | **Go:** show one computed A/B matrix row and select its actual two model-scoped elements. **No-go:** stay in the single-model workflow and show a second verified finding/coverage result. Never simulate a clash. |
| 2:42–3:00 | Results and close | Small synthetic benchmark scope/limitations; repository name | State only the locally measured T-6 result and its small synthetic scope; disclose outstanding hosted CI and any unavailable/live-unverified feature. End by 3:00. |

Keep the final video at exactly three minutes or shorter. A feature segment may replace time in the
fixed slot; it may not extend the video or be added to make an unverified release appear complete.

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
single-model sample is the safe product-demo fallback and is not a clash substitute.

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

# Evaluation

**Status:** T-6 deterministic benchmark implemented and measured locally on 29 October 2026.
The result below measures the current deterministic IDS/native checks against a small,
independently labelled synthetic IFC4 dataset. It is not a measure of live Muse Spark quality or
general BIM-model accuracy.

## 1. Evaluation objective

The benchmark checks whether the current deterministic review path:

1. detects independently injected, supported P0 defects;
2. avoids findings on a clean reference model and explicit clean controls;
3. records byte-identical persisted `findings.json` on repeated reviews;
4. agrees with IfcTester's own IDS JSON report at the failed-element level; and
5. reports execution errors, skips and non-applicable checks separately from defects.

Fake/Replay checks separately exercise the existing T-5 offline safety contract. They do not measure
live model relevance, structured-output reliability, explanation quality or token economics.
Nothing in this evaluation makes a live Meta Model API request.

The accuracy target remains **at least 90% precision and 90% recall** (NFR-02). It has not been
changed to fit the result.

## 2. Benchmark specification

### 2.1 Dataset and executable check coverage

The deterministic generator in `tests/evaluation/benchmark.py` writes its outputs to the
git-ignored `datasets/synthetic/generated/` directory. It creates a clean IFC4 reference model and
a defective copy, plus a versioned injection manifest, independently verified ground truth,
`benchmark.ids`, a synthetic BEP and objective examples. All content is synthetic and
redistributable. The generator does not modify `tests/fixtures/minimal.ifc` or
`tests/fixtures/minimal.ids`.

The model has three storeys, 12 walls, six doors, six windows, three slabs and three spaces. It also
contains project/site/building spatial aggregation, spatial containment, a wall type, classification
systems and references, relevant property sets and 30 shape representations. It is a small
architectural test model, not a representative sample of project IFCs.

The benchmark executes 11 confirmed checks: ten IDS specifications and the already registered
`classification.consistent_by_type` v1.0.0 native check. Two IDS specifications are controls, not
positive-defect checks.

| Requirement area | Exact check identities | Coverage |
|---|---|---|
| FR-VAL-02, P0 | `ids:IDS:wall_fire_rating` (`dc19ad4256982376`); `ids:IDS:door_fire_rating` (`6f44b9c642105622`); `ids:IDS:space_reference` (`6038e2cbf0c74e35`) | Required property set/property and accepted value pattern |
| FR-VAL-03, P0 | `ids:IDS:wall_name` (`0eb2cf064fc4075a`); `ids:IDS:door_name` (`bf9953688773e72d`); `ids:IDS:storey_name` (`2f25f4ea5c80deac`) | Expressible wall, door and storey naming patterns |
| FR-VAL-04, P0 | `ids:IDS:window_classification` (`d79f8c4fcb8c145a`); `ids:IDS:wall_classification` (`d1e654a86e48d825`); `classification.consistent_by_type` (`f2a6e8e62486cd54`, rule v1.0.0) | Classification presence/system and the registered type/occurrence consistency rule |
| Applicability controls | `ids:IDS:external_wall_applicability` (`1bab96d9ae113f47`); `ids:IDS:column_non_applicability` (`816a3302d0ad4a94`) | False-positive and non-applicable execution controls |

These are the current executable checks relevant to this P0 benchmark. FR-VAL-05 spatial
relationship validation and FR-VAL-06 invalid/duplicate GlobalId validation are P1 and are not
implemented; they are not counted as P0 positives or silently treated as passing.

### 2.2 Individually labelled P0 defects

The original catalogue contains 14 P0 candidate instances in D01–D14. Its D15–D17 entries are P1,
and D18 is a zero-finding control. To reach the requested 15–20 positive instances without adding
rule functionality or reclassifying controls, this benchmark adds **D19**, a third independently
labelled missing-wall-FireRating instance. This corrects the benchmark count only; it does not
rewrite the earlier catalogue's history.

The `FR-VAL-*` identifiers are traceability references to
`docs/REQUIREMENTS.md`; each `IDS:*` specification is the benchmark's confirmed executable
requirement, bound to the listed immutable check id. The native requirement is explicitly confirmed
when the runner starts. `Expected evidence` is the deterministic evidence expected from the check.
`Implemented` indicates that the exact rule/check is present in the current engine.

| Defect | IFC element GlobalId | Injected change | Confirmed requirement / exact rule and check | Expected result and observed evidence | Implemented |
|---|---|---|---|---|---|
| D01 | `3iHwMS$PTJtPqv7Do_JzPg` (`W-001`) | Remove `Pset_WallCommon.FireRating`. | FR-VAL-02 / `IDS:wall_fire_rating`; `ids:IDS:wall_fire_rating`, check `dc19ad4256982376` | Finding; `FireRating` property is absent. | Yes |
| D02 | `1kWn0MixjHGgBH4rWGTsNq` (`W-002`) | Remove `Pset_WallCommon.FireRating`. | FR-VAL-02 / `IDS:wall_fire_rating`; `ids:IDS:wall_fire_rating`, check `dc19ad4256982376` | Finding; `FireRating` property is absent. | Yes |
| D03 | `3QG$VfVnnSBQZu7u68J2gJ` (`D-003`) | Set `Pset_DoorCommon.FireRating` to an empty string. | FR-VAL-02 / `IDS:door_fire_rating`; `ids:IDS:door_fire_rating`, check `6f44b9c642105622` | Finding; `FireRating` property value is empty. | Yes |
| D04 | `3g9n53ivbOowvROIxDKQnj` (`W-003`) | Set `Pset_WallCommon.FireRating` to `TBC`. | FR-VAL-02 / `IDS:wall_fire_rating`; `ids:IDS:wall_fire_rating`, check `dc19ad4256982376` | Finding; `FireRating` property value is `TBC`. | Yes |
| D05 | `3olTV09abSauJyvdXQ5vw7` (`W-004`) | Remove the wall occurrence's `Pset_WallCommon`. | FR-VAL-02 / `IDS:wall_fire_rating`; `ids:IDS:wall_fire_rating`, check `dc19ad4256982376` | Finding; `Pset_WallCommon` is absent. | Yes |
| D06 | `04DdGClcnMwerPFSsX9F$l` (`SP-001`) | Remove the space occurrence's `Pset_SpaceCommon`. | FR-VAL-02 / `IDS:space_reference`; `ids:IDS:space_reference`, check `6038e2cbf0c74e35` | Finding; `Pset_SpaceCommon` is absent. | Yes |
| D07 | `3C4rRuvxjVsAx__1Ehdf90` (wall) | Rename the wall to `Wall 005`. | FR-VAL-03 / `IDS:wall_name`; `ids:IDS:wall_name`, check `0eb2cf064fc4075a` | Finding; `Name` is `Wall 005`, not `W-###`. | Yes |
| D08 | `3$2yhsQ3TSxR6d22pYF_Rr` (wall) | Rename the wall to `W-06`. | FR-VAL-03 / `IDS:wall_name`; `ids:IDS:wall_name`, check `0eb2cf064fc4075a` | Finding; `Name` is `W-06`, not `W-###`. | Yes |
| D09 | `03N2FoVyzUj9LDRL6uuRCZ` (`L01`) | Rename the storey to `Level 1`. | FR-VAL-03 / `IDS:storey_name`; `ids:IDS:storey_name`, check `2f25f4ea5c80deac` | Finding; `Name` is `Level 1`, not `L##`. | Yes |
| D10 | `13ARETEdrNzwa_B7cPTecM` (door) | Rename the door to `Door 005`. | FR-VAL-03 / `IDS:door_name`; `ids:IDS:door_name`, check `bf9953688773e72d` | Finding; `Name` is `Door 005`, not `D-###`. | Yes |
| D11 | `0tslii7ErLd8n8NIY9bJN$` (window) | Remove the window's classification reference. | FR-VAL-04 / `IDS:window_classification`; `ids:IDS:window_classification`, check `d79f8c4fcb8c145a` | Finding; no classification reference is present. | Yes |
| D12 | `0ojEp3WwbP1uJqTksmV4Or` (window) | Remove the window's classification reference. | FR-VAL-04 / `IDS:window_classification`; `ids:IDS:window_classification`, check `d79f8c4fcb8c145a` | Finding; no classification reference is present. | Yes |
| D13 | `0XdR5PrpPV9A5FpbROHzD6` (wall) | Replace the Uniclass classification with a different system. | FR-VAL-04 / `IDS:wall_classification`; `ids:IDS:wall_classification`, check `d1e654a86e48d825` | Finding; classification uses `Benchmark test system`, not `Uniclass 2015`. | Yes |
| D14 | `2DyYossgXISxr8D9NU$HDo` (wall occurrence) | Change its code to `WRONG-CODE` while its type remains `Ss_25_10_30`. | FR-VAL-04 / `classification.consistent_by_type`; check `f2a6e8e62486cd54`, rule v1.0.0 | Finding; occurrence classification is `WRONG-CODE`, type classification is `Ss_25_10_30`. | Yes |
| D19 | `3g$S9kLxDLvv1non6D94_r` (wall) | Remove `Pset_WallCommon.FireRating` as an additional independent instance. | FR-VAL-02 / `IDS:wall_fire_rating`; `ids:IDS:wall_fire_rating`, check `dc19ad4256982376` | Finding; `FireRating` property is absent. | Yes |

The IFC element names above are descriptive labels; GlobalIds are the matching identity. The
versioned injection manifest records the target and change for each instance.

### 2.3 P1 exclusions and zero-finding controls

P1 entries remain catalogue exclusions. No injection is made for them, no result is expected from
the current engine, and they are absent from all P0 metrics.

| Defect | Target GlobalId(s) | Proposed change | Requirement / rule | Expected result / evidence | Implemented |
|---|---|---|---|---|---|
| D15 | `1BM7mWHgjGH90cUmMN4Fvx` | Not injected: remove the door's spatial containment. | FR-VAL-05 / `spatial.contained` | Not evaluated; no observed evidence because the rule is unimplemented. | No |
| D16 | `1UZvL7cmTP2947lKAG4JS5` | Not injected: contain a wall in the wrong storey. | FR-VAL-05 / `spatial.contained` | Not evaluated; no observed evidence because the rule is unimplemented. | No |
| D17 | `2lUUwYtkbKY9sSyykfUIV5`, `2aIaII8hzGPxdcWkHkeCxI` | Not injected: duplicate a window GlobalId. | FR-VAL-06 / `identity.unique_global_id` | Not evaluated; no observed evidence because the rule is unimplemented. | No |

The benchmark has seven explicit zero-finding controls: D18 and C01–C06. No control is a positive
defect.

| Control | IFC element GlobalId | Injected change / independently checked fact | Confirmed check(s) | Expected result and observed evidence |
|---|---|---|---|---|
| D18 | `3TLpuWVBPQoxdEkImlDFw1` (`W-012-EXT`) | None; `IsExternal=false` despite the name and description indicating external design intent. | Synthetic benchmark applicability-control specification / `ids:IDS:external_wall_applicability` (`1bab96d9ae113f47`) | No finding; the element must not be flagged by the external-only applicability requirement. |
| C01 | `0_dOk9tYzVEOA9VF_QrPNI` (`W-010`) | None; compliant wall with matching type classification. | `IDS:wall_fire_rating` (`dc19ad4256982376`), `IDS:wall_name` (`0eb2cf064fc4075a`), `IDS:wall_classification` (`d1e654a86e48d825`) and native `classification.consistent_by_type` (`f2a6e8e62486cd54`) | No finding; wall properties, name and type/occurrence classification are compliant. |
| C02 | `0lUryCqB9OOxlJMHayhNUJ` (`D-006`) | None; compliant door with a valid fire rating and name. | `IDS:door_fire_rating` (`6f44b9c642105622`) and `IDS:door_name` (`bf9953688773e72d`) | No finding; door property value and name are compliant. |
| C03 | `0eorq12vHNSO48ybgfUeZN` (`WN-003`) | None; compliant window with project classification. | `IDS:window_classification` (`d79f8c4fcb8c145a`) | No finding; a project classification reference is present. |
| C04 | `2WsbEQx6HRowhXFo8j5n8H` (`SL-001`) | None; compliant slab with spatial containment. | No benchmark P0 check targets slabs. | No finding; this is a model-content control, not a P0 true positive. |
| C05 | `0_Grlt30rRdO3to515pib9` (`SP-002`) | None; compliant space with `Pset_SpaceCommon.Reference`. | `IDS:space_reference` (`6038e2cbf0c74e35`) | No finding; the required space reference is present. |
| C06 | `0wV5eBVQXInvxQ7GUwAYxL` (`L02`) | None; compliant storey name. | `IDS:storey_name` (`2f25f4ea5c80deac`) | No finding; the name matches `L##`. |

One additional IDS control, the column specification (`ids:IDS:column_non_applicability`,
`816a3302d0ad4a94`), is expected to be `not_applicable` because the model contains no columns.
This is reported as execution status, not as a clean-control positive or a defect.

### 2.4 Independent ground truth and matching

Ground truth is constructed from the injection specification, then checked against IFC facts
(including target GlobalIds, element types, names, properties, classifications and type/occurrence
relationships). It is not generated from BIM Intelligence Findings. The clean reference model is
also inspected independently. `ground_truth.json` is versioned as 1.0.0 and identifies its matching
contract.

A prediction matches a defect one-to-one only when its `rule_id`, immutable `check_id` and exact,
unordered set of element GlobalIds match. A finding containing multiple elements must match the
whole labelled set; partial or extra elements do not match. Duplicate predictions count as false
positives. A wrong GlobalId, rule or check is an unmatched prediction and leaves the expected defect
missed (one FP and one FN). The runner reports duplicates, unmatched predictions and missed defects
separately. Clean controls are scored separately and never enter the positive-defect denominator.

## 3. Deterministic accuracy metrics

| Metric | Definition | Target |
|---|---|---|
| Precision | TP / (TP + FP) | ≥ 0.90 |
| Recall | TP / (TP + FN) | ≥ 0.90 |
| F1 | Harmonic mean of precision and recall | Reported |
| Per-family metrics | Same counts and metrics, partitioned by rule family | Reported |
| Clean-model false positives | Findings on the clean reference model | 0 |
| Defective-model control false positives | Findings on D18/C01–C06 | 0 |
| Determinism | Byte comparison of two persisted `findings.json` files | Identical |

An undefined metric is `null` in JSON when its denominator is zero; it is not replaced with a perfect
score. An executed check with status `not_applicable`, `skipped` or `error` is reported separately
and does not become an FN or an FP. Only the implemented, applicable P0 defects form the positive
denominator.

## 4. Explanation evidence

The benchmark does not measure live explanation quality. The offline safety evaluation exercises
grounding rejection and deterministic fallback with Fake/Replay fixtures (see §5). It does not report
the proposed first-attempt grounding rate, citation coverage, or the subjective human rubric as
model-performance measurements. Those remain unmeasured until a separately approved evaluation
defines a suitable dataset and process.

## 5. T-5 offline safety contract

The lightweight Fake/Replay evaluation uses no live client and blocks socket connections. Its nine
deterministic contract checks are:

- schema-valid plan and registered-check selection;
- rejection of unconfirmed, unknown and duplicate checks;
- execution-cap enforcement;
- rejection of an ungrounded explanation and deterministic fallback;
- repeatable recorded/replayed responses; and
- no live client construction.

These checks report 9/9 passing in the recorded run. They are implementation-contract tests, not
evidence of Muse Spark relevance, structured-output reliability, API compatibility, cost or
token-use performance. No live Meta request or spend was made by this offline evaluation. The
separate owner-approved live smoke observation is recorded in §8.

### T-5.1 objective policy and provenance contract

The T-5.1 unit and API tests exercise the production-profile configuration gate, strict objective
failure responses, budget refusal before a provider request, rejection of an invalid Live plan
without publishing a run or findings, explicit deterministic continuation, revision-pinned check
selection, accepted Replay provenance retrieval and compatibility with historical runs that lack
provenance. Provider interactions use Fake/Replay clients or a stubbed SDK transport; the tests
make no live Meta request and report no model-quality, cost or latency metric. These are contract
tests only. The caller-visible typed errors identify mode, whether a provider request was attempted,
model when known and a safe reason code.

A rerun on 1 November 2026 (branch `Working-Muse-Spark`, uncommitted T-5 explanation hardening)
again reported 9/9, with 0 network calls, 0 live calls and USD 0. In that run, the fallback for
the "ungrounded explanation" check came from the explanation response schema (`fallback_reason=
ai_output_invalid`, because its fixture has no citations), not from the grounding checker. The
check therefore shows that an ungrounded response is rejected, but not specifically by the
grounding checker. Grounding-checker rejection (`grounding_failed`) is covered by unit tests in
`tests/unit/llm/test_explanations.py` and API tests in
`tests/unit/api/test_finding_explanations.py` instead. The metric definition is unchanged.

## 6. Baseline comparisons

| Baseline | Recorded result |
|---|---|
| IfcTester JSON report | The normalised IDS findings and IfcTester report agree on all 14 failed IDS elements: 14 vs 14, with no missing or extra elements. The additional native finding is not part of the IDS comparison. |
| Clean reference model | Zero findings; ten checks pass and the column control is not applicable. |
| LLM-disabled defective review | The current deterministic review produced the measured P0 findings without invoking an LLM. |

The benchmark does not compare the default plan against an LLM-planned run, commercial checkers,
or live model explanations. No superiority or model-quality claim is supported.

## 7. Reproduction

From a fresh checkout, install the documented backend development dependencies (`pip install -e
".[dev]"`) and run from the repository root:

```powershell
python -c "import sys; sys.path.insert(0, 'tests'); from evaluation.run_eval import main; raise SystemExit(main())"
python -m pytest tests\unit\evaluation tests\evaluation\test_run_eval.py -q
```

The runner deterministically generates or reloads the benchmark at
`datasets/synthetic/generated/`, sets `LLM_MODE=off`, blocks socket connections, runs the same
defective review twice and compares the persisted findings bytes. It writes:

- `tests/evaluation/runs/latest/results.json` — metrics, per-check execution status, identities,
  versions, source commit, cleanliness and SHA-256 hashes;
- `tests/evaluation/runs/latest/summary.md` — concise human-readable results; and
- `tests/evaluation/runs/latest/ifctester-results.json` — the IfcTester JSON report, with IFC
  entity values represented as STEP strings.

Both output locations are git-ignored; generated model files are not committed. The commands make
no network or Meta API requests.

## 8. Results

**Recorded run:** 29 October 2026, 20:09 UTC; Python 3.12.12, IfcOpenShell 0.9.0.post1, IfcTester
0.9.0; source commit `99d04633c517c052f80f87b5f7fb6f2ec640e909`. The working tree was dirty because
T-6 changes were being evaluated; the recorded source commit is the base commit, not a claim that
the working tree was committed. GitHub-hosted CI evidence is outstanding.

### Composition and confusion counts

| Rule family | Positive defects | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `property.required` | 7 | 7 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| `naming.pattern` | 4 | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| `classification.*` | 4 | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| **Aggregate** | **15** | **15** | **0** | **0** | **1.000** | **1.000** | **1.000** |

The unchanged 90% precision and recall target was met on this dataset. There were 15 predictions,
zero duplicate predictions, zero unmatched predictions and zero missed defects. These scores are
bounded by the 15 injected instances and the checks listed in §2; they are not a population estimate.

### Controls, execution and determinism

- Seven explicit clean controls: **0** false positives on the clean reference and **0** on controls
  in the defective model.
- Eleven checks executed on each review. Defective review: nine failed checks, one passed and one
  not applicable; **zero errors and zero skipped checks**. Clean review: ten passed, one not
  applicable; **zero errors and zero skipped checks**.
- The non-applicable result was the column IDS control (`REQ-010`), with no matching entities.
- Repeated `findings.json` files were byte-identical: **yes**. Both SHA-256 hashes were
  `e93e204f8fb8b63a8fd1c398da9c4dc025253de58bf86f1726a0567c17d5fd4b`.
- IfcTester agreement: **14 of 14 IDS failed elements**, no missing or extra normalised entities.
  The native classification-consistency finding is evaluated separately.

### Offline AI contract and live-call boundary

Fake/Replay safety checks: **9/9 passed**. They exercise plan schema/selection, rejection of
unconfirmed, unknown and duplicate checks, cap enforcement, grounding rejection, deterministic
fallback, replay repeatability and no live client construction. The runner reported zero network
calls, zero live Meta API requests and USD 0 spend. The configured model identifier in result
metadata is informational only; it was **not invoked**.

### FIX-002 offline review-planning correction (3 November 2026)

The approved FIX-002 changes use a planning-only 2,000-token completion allowance and
`reasoning_effort="low"`, while other workflows retain their 500-token default. The `LiveClient`
stub-transport tests verify the outgoing `max_completion_tokens` and non-strict JSON Schema request
body, as well as valid local plan validation, malformed and truncated outputs, provider refusals,
content filters, and safe response diagnostics. API regression tests verify that completion-limit
failures are reported as `token_limit`, while visible malformed JSON remains an invalid-output
failure.

Final local verification on the dirty working tree based on source commit
`cbb4361612bbdeb40d6a4c4530e1773db041544d`:

| Command | Result |
|---|---|
| `.venv\Scripts\ruff.exe check .` | Passed |
| `.venv\Scripts\ruff.exe format --check .` | Passed; 165 files already formatted |
| `.venv\Scripts\mypy.exe` | Passed; 131 source files |
| `.venv\Scripts\python.exe scripts\export_schemas.py --check` | Passed; generated schema up to date |
| `.venv\Scripts\python.exe -m pytest -q` | 653 passed, 1 live test skipped, 1 third-party deprecation warning |
| `git diff --check` | Passed |

At configured Standard rates, the 8,000-input/2,000-completion reservation is **USD 0.01850**.
The existing USD 0.10 per-call/review limits and USD 5.00 project allowance were not increased.
No live or paid provider call was made. Consequently, this verifies offline request construction,
local validation, error classification and safeguards only; Meta's live acceptance of the
non-strict JSON Schema format and end-to-end planner relevance remain unverified and require
VERIFY-009. FIX-002 does not complete T-5 or M2.

### FIX-003 offline grounded-explanation correction (3 November 2026)

The owner-approved VERIFY-009 live session on `b95dadbe2d0475aa3c107227a9d0af2cae2c2c47`
accepted a Muse Spark 1.3 review plan but the single approved explanation request stopped at
`finish_reason=length` with 500 completion tokens (498 reasoning) and no visible content, so
schema validation and grounding were never exercised live. FIX-003 gives explanations a 2,000-token
allowance at `reasoning_effort="low"`, adds the `token_limit` fallback reason and leaves planning,
the explanation prompt, schema, validation and grounding unchanged.

Offline regression coverage, all with stubbed SDK transports or `FakeClient`:

| Requirement | Test |
|---|---|
| Explanation request sends `max_completion_tokens=2000`, `reasoning_effort="low"`, no `max_tokens` | `tests/unit/llm/test_live_client.py::test_explanation_requests_use_their_own_allowance_at_low_reasoning_effort`; `tests/unit/api/test_finding_explanations.py::test_per_run_call_cap_stops_a_second_paid_explanation` |
| Planning request body unchanged | `tests/unit/llm/test_live_client.py::test_live_client_uses_stubbed_sdk_and_reconciles_usage`; `tests/unit/api/test_reviews.py` |
| Other workflows keep 500 tokens and no reasoning-effort parameter | `tests/unit/llm/test_live_client.py::test_non_planning_requests_keep_the_500_token_cap` |
| VERIFY-009 response (`length`, 500/498, no content) is `token_limit` | `tests/unit/llm/test_live_client.py::test_verify_009_explanation_exhaustion_is_a_token_limit_failure`; `tests/unit/api/test_finding_explanations.py::test_fix_003_verify_009_token_exhaustion_is_labelled_token_limit_not_budget` |
| Spending rejection remains `budget_limit` | `tests/unit/api/test_finding_explanations.py::test_budget_rejection_falls_back_before_any_provider_request` |
| Schema-valid, correctly cited explanation passes validation and grounding | `tests/unit/api/test_finding_explanations.py::test_grounded_ai_explanation_is_labelled_and_leaves_run_files_untouched`; `tests/unit/llm/test_explanations.py::test_valid_grounded_explanation_is_labelled_ai_generated` |
| Unsupported citations fail grounding with a labelled fallback | `tests/unit/api/test_finding_explanations.py::test_ungrounded_ai_output_falls_back_with_grounding_failed`, `::test_citation_for_another_element_falls_back_with_grounding_failed` |
| `run.json`/`findings.json` unchanged; monetary limits unchanged | `tests/unit/api/test_finding_explanations.py::test_explanation_cannot_exceed_its_configured_allowance_and_keeps_findings_intact`; `tests/unit/llm/test_budget.py::test_explanation_worst_case_reservation_stays_within_unchanged_budgets` |
| Frontend token-limit message and label validation | `frontend/src/components/ModelWorkspace.test.tsx` ("FIX-003: describes a completion-token limit…"); `frontend/src/api/bim.test.ts` ("accepts a token-limit fallback…") |

Local verification on the FIX-003 working tree based on `b95dadbe2d0475aa3c107227a9d0af2cae2c2c47`:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m ruff check .` | Passed |
| `.\.venv\Scripts\python.exe -m ruff format --check .` | Passed; 165 files already formatted |
| `.\.venv\Scripts\python.exe -m mypy` | Passed; 131 source files |
| `.\.venv\Scripts\python.exe scripts\export_schemas.py --check` | Passed; generated schema up to date |
| `.\.venv\Scripts\python.exe -m pytest -q` | 659 passed, 1 live test skipped, 1 third-party deprecation warning |
| `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm run types:check` (from `frontend/`) | Passed |
| `npm test` (from `frontend/`) | 150 passed in 10 files |
| `npm run build` (from `frontend/`) | Passed; existing large-chunk and Three.js `IMPORT_IS_UNDEFINED` warnings remain |

At configured Standard rates the 8,000-input/2,000-completion explanation reservation is
**USD 0.01850**; one planning and one explanation reservation in a review total **USD 0.03700**.
The USD 0.10 per-call/review limits, USD 5.00 project allowance and two-call cap were not changed.
No live or paid provider call was made. These results verify request construction, classification,
grounding logic and labels offline only; whether Muse Spark returns a complete grounded
explanation within the new allowance is OQ-08 and requires an owner-approved live retest.
FIX-003 does not complete T-5 or M2.

### Dataset hashes

| Generated input | SHA-256 |
|---|---|
| `benchmark-clean.ifc` | `f1a9fa42ca7687e43e410ab4b676fa9d126ebe522ed58588f269089496e39bb2` |
| `benchmark-defective.ifc` | `4f96679de9a809730a4e505bd33e310e7ac391ee6bd59b6037e79add127236e6` |
| `benchmark.ids` | `9fca0d79851188077993a723417e09155cfc2deba5fa50effe573914d91d32f3` |
| `defect-injections.v1.json` | `f27fcc02d122556e234051cb9ca0edf38390d63b9a0afb57de172a6084ed230b` |
| `ground_truth.json` | `54cf386c834b0740721ca0a089c7dbe46f8c97c7c5569084f7da7fa581e8e421` |
| `benchmark_bep.md` | `ed57b85e9a0eaccf70eec1cc304d52deac1358fc7918e1d82ed6b9f3ce08a166` |
| `benchmark_objectives.json` | `b37f1640c835f8b139fb9acd5fa60d7e7855ec38c73afe6147d02734b989d506` |

### Verification recorded for T-6

The focused local test command
`.\.venv\Scripts\python.exe -m pytest tests\unit\evaluation tests\evaluation\test_run_eval.py -q`
passed **14 tests**. Repository-wide Ruff lint/format and mypy checks passed. The full backend test
suite passed **541 tests** with one live test skipped and one third-party deprecation warning.
Hosted CI evidence remains outstanding: GitHub Actions run
[40924566072](https://github.com/natnew/BIM-Intelligence/actions/runs/40924566072) on the base
`main` commit ended in `startup_failure` with no jobs; it did not execute this uncommitted T-6
worktree.

### T-5 live structured-output smoke (1 November 2026)

**Evidence source:** the owner's report of one approved run in a side chat on 1 November 2026.
These are observed results reported by the owner, not a new execution by this implementation chat.
The side-chat source commit was not supplied; this evidence must not be attributed to the T-6
commit above or assumed to verify the uncommitted T-5 branch. No raw request, credential or response
recording was copied into this record, and the ledger was not independently re-read here.

| Observation | Result |
|---|---|
| Named test | `tests/live/test_meta_smoke.py::test_meta_muse_spark_structured_output_smoke` |
| Model | `muse-spark-1.3` |
| Test / request outcome | Passed / `success` |
| Structured output | Exact match: `{"status":"T5_SMOKE_OK"}` |
| Input / cached / output tokens | 42 / 0 / 293 |
| Application ledger request count | 1 |
| Reservation | USD 0.002395 |
| Calculated ledger charge | USD 0.00129775 |
| Pricing basis | Configured prices; not checked against Meta's prices |

This establishes one successful basic structured-output response through the existing
OpenAI-compatible client. The client requests JSON-object mode and validates locally with
Pydantic; this is not evidence for provider-side strict JSON-schema support, live planner relevance,
grounded explanation quality or the complete browser workflow. The calculated charge is an
application-ledger observation and approximate provider cost, not verified Meta billing.

The short reply consumed **293 output tokens, 58.6% of the configured 500-token output cap**.
A longer explanation with citations may have insufficient headroom. This observation neither
explains the token accounting nor establishes that an explanation was truncated. Keep the cap
and budgets unchanged; a synthetic grounded-explanation check needs separate owner approval and
must report schema/grounding outcomes and any cap-related failure. See [R-API-06](./RISKS.md#3-model-and-api-limitations).

**Do not repeat the smoke test under the current request.** Recording this evidence authorises no
additional live call. Further live workflow evaluation requires separate explicit approval.

### RELEASE-001 offline verification — 1 November 2026

**Scope and baseline:** Windows, Python 3.12.12, Node.js 24.19.0, npm 11.17.0, IfcOpenShell
0.9.0.post1 and IfcTester 0.9.0. The clean checked-out implementation was
`484b71c7988295159083121fab77e1713c825903`; its tree matched merged `main`
`cf06328c874258efe8a49d0afa291d9aef278928`. The following results precede this documentation
reconciliation; they are not a release commit. Live tests were explicitly excluded.

The browser backend bound to `127.0.0.1:8019` with isolated ignored storage,
`LLM_MODE=off`, `ALLOW_LIVE_LLM=false` and no configured API key. The configured default model was
`muse-spark-1.3`, but it was not invoked. The development and production-preview frontends used
local ports 5191 and 5192 respectively. The permitted demonstration input was the committed
synthetic fixture; no private BIM inputs or feedback were inspected.

An initial offline server inherited the repository environment rather than the intended isolated
environment. It was stopped; the reported browser evidence uses the credential-free restart.
`LLM_MODE=off` was enforced throughout and no model request was made.

| Check | Exact command and result |
|---|---|
| Backend lint / format | `.\.venv\Scripts\python.exe -m ruff check .` — passed; `.\.venv\Scripts\python.exe -m ruff format --check .` — passed, 160 files already formatted. |
| Backend types | `.\.venv\Scripts\python.exe -m mypy` — passed, 131 source files; `.\.venv\Scripts\python.exe -m mypy --strict backend\bim_intelligence\schemas backend\bim_intelligence\validation backend\bim_intelligence\orchestration` — passed, 23 files, with an unused-configuration note. |
| Backend regression | `.\.venv\Scripts\python.exe -m pytest -m "not live"` — 616 passed, one live test deselected, one upstream Starlette/httpx deprecation warning. The FED-001 feasibility tests are included. |
| Schema parity | `.\.venv\Scripts\python.exe scripts\export_schemas.py --check` — passed. |
| Frontend | From `frontend/`: `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm run types:check`, `npm run test` and `npm run build` — all passed; 8 test files / 91 tests. The build reported missing `TSL`/`NodeMaterial` exports in dependencies and chunks over 500 kB. |
| Secret scanning | `.\.venv\Scripts\python.exe scripts\secret_scan.py --history` — no leaks detected across 96 scanned commits; `--staged` — passed with an empty index. A scan is not proof that all secrets or private information have been identified. |

**Documentation checks:** `git --no-pager diff --check` passed. A local check verified 31 added
relative links/anchors and ten contiguous storyboard shots totalling 180 seconds. Its first timing
attempt failed because the PowerShell pipe changed the Unicode separator; a Unicode-safe rerun
passed. The changed documentation diff was scanned with
`gitleaks stdin --redact --no-banner --config .gitleaks.toml`; no leaks were detected.

**Synthetic benchmark:** At 20:01 UTC, the offline runner generated its inputs and reports in a
fresh ignored `data/release-001-verification/` subtree, rather than overwriting the existing
benchmark evidence. It measured 15 positive defects and seven controls: TP/FP/FN **15/0/0**,
precision/recall/F1 **1.000/1.000/1.000**, zero clean/control false positives, byte-identical
repeat findings and 14/14 IfcTester IDS entity agreement. Eleven checks were evaluated on each
model, with no errors or skips and one expected not-applicable control per model. The offline Fake/Replay
contract checks passed 9/9; the runner recorded zero network calls, live calls and spend. These
results measure only the declared synthetic IFC4 cases, not real-project accuracy or live AI
quality.

The command below was run from the repository root with `$runtime` set to the fresh ignored
verification directory and `TEMP`/`TMP` set to that directory. Use a new empty directory when
reproducing so earlier evidence is not overwritten.

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'tests'); from evaluation.run_eval import main; raise SystemExit(main())" --benchmark-dir (Join-Path $runtime 'benchmark') --results-dir (Join-Path $runtime 'results')
```

**Browser and API evidence:** The synthetic minimal fixture was uploaded and reviewed with a
credential-free, offline backend. Real browser interactions at 1920 × 1080, 1440 × 900 and
390 × 844 exercised the paths detailed in
[UI_CHANGELOG.md](./UI_CHANGELOG.md#release-001--synthetic-baseline-verification). A direct
objective request returned `plan_source=default`; a direct explanation request returned
`source=deterministic_template`, `grounding_status=fallback`, `fallback_reason=ai_disabled` and
no model. Neither is a live or replayed Meta response. No new live call was made.

**Hosted CI:** [main run 41343324279](https://github.com/natnew/BIM-Intelligence/actions/runs/41343324279)
at `cf06328c874258efe8a49d0afa291d9aef278928` ended in `startup_failure` with no jobs. Local
success does not establish a successful hosted run.

### FINAL-UI-001 frontend integration verification — 2 November 2026

**Scope and baseline:** branch `FINAL-UI-001` from
`36363425c6bcaec7aae4e9725261fb930e756319` (verified before commit). Windows, Python 3.12.12,
Node.js 24.19.0, IfcOpenShell 0.9.0.post1, IfcTester 0.9.0, @thatopen/components 3.6.0. The
backend ran on `127.0.0.1:8010` (port 8000 was held by an unrelated process) with the repository
`.env` (`LLM_MODE=off`, `ALLOW_LIVE_LLM=false`); `/health` reported `llm_mode=off`. No live,
Replay or paid model request was made. Only the committed synthetic fixtures were used.

| Check | Exact command and result |
|---|---|
| Frontend | From `frontend/`: `npm run lint` — 0 warnings; `npm run format:check` — passed; `npm run typecheck` — passed; `npm run types:check` — generated types up to date; `npm run test` — 8 files / **109 tests** passed (91 at RELEASE-001); `npm run build` — passed with the pre-existing dependency import and chunk-size warnings. |
| Backend | `.\.venv\Scripts\python.exe -m ruff check .` — passed; `ruff format --check .` — 160 files already formatted; `mypy` — no issues in 131 source files; `pytest -m "not live"` — 616 passed, 1 deselected (run before commit; no backend file changed). |

**Browser evidence (private, `local-private/test-results/final-ui-001/`):** a fresh session
indexed `minimal.ifc` (version `f2bd0007…`) and imported `minimal.ids` (two executable
requirements). The standard review returned the two expected findings with `plan_source=default`.
A non-empty objective produced a `POST …/reviews` whose intercepted body was the JSON objective
with `If-Match`; the Off-mode server returned `default` and the interface displayed *The objective
was not used; the deterministic default plan ran.* An explicit **Explain finding** on W-002
returned `source=deterministic_template`, `grounding_status=fallback`,
`fallback_reason=ai_disabled`, `model=null` and one citation, rendered separately from the
deterministic evidence. Version-mismatch (after a variant upload), missing-run, selection-change
and cached-explanation states behaved as specified. Recent sessions stored identifiers only and
reopened run `508400f0` with its findings. Layout metrics at 1920 × 1080, 1440 × 900 and 390 × 844
matched the established three-/three-/one-column arrangement with no horizontal overflow.

**Not measured:** `plan_source=llm`, `ai_generated` explanations and Replay labelling in the
browser (Vitest only); accessibility beyond keyboard activation; live Meta behaviour. These
results verify the interface wiring, not AI quality.

## 9. Known limitations and gaps

- This is one small synthetic IFC4 model. Precision/recall do not generalise to other projects,
  authoring tools, IFC versions, IDS suites or defect prevalence.
- Only the declared FR-VAL-02, FR-VAL-03 and FR-VAL-04 benchmark checks are measured. FR-VAL-05
  spatial relationship checks and FR-VAL-06 invalid/duplicate GlobalId checks remain unimplemented
  P1 gaps; D15–D17 are explicit exclusions.
- The classification type/occurrence result covers the single registered native rule, not every
  classification scenario.
- A benchmark BEP and objective set are generated for future planner evaluation; no planner
  relevance score was measured.
- Fake/Replay checks do not establish live Muse Spark performance, API compatibility, cost or
  token economics. The separate single live smoke observation in §8 establishes only basic
  structured-output compatibility; further live evaluation requires explicit project-owner approval.
- Runtime performance and browser rendering on this benchmark were not evaluated by this runner.
- The task result does not complete M1, M3 or M4 by itself. Their original exit criteria and
  remaining evidence are tracked in [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md).

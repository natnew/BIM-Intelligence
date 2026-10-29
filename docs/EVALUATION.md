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
token-use performance. No live Meta request or spend was made.

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
  token economics. Live evaluation still requires explicit project-owner approval.
- Runtime performance and browser rendering on this benchmark were not evaluated by this runner.
- The task result does not complete M1, M3 or M4 by itself. Their original exit criteria and
  remaining evidence are tracked in [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md).

# Evaluation

**Status:** v0.1 design. No evaluation has been run; no metric below is a result. Values will be filled in only when produced by `evaluation/run_eval.py`.

## 1. Evaluation objective

Demonstrate, with reproducible evidence, that BIM Intelligence:

1. detects the defects it claims to detect (precision/recall on a labelled benchmark);
2. produces identical deterministic findings across runs;
3. never ships an explanation that cites a model fact absent from its evidence;
4. interprets review objectives into valid, bounded plans;
5. does so within a known token budget.

Acceptance thresholds come from [REQUIREMENTS.md](./REQUIREMENTS.md) (NFR-01, NFR-02, NFR-03, NFR-05, NFR-06).

## 2. Benchmark design

### 2.1 Dataset

**Proposed (ADR-011, approval pending):** a synthetic architectural model generated with `ifcopenshell.api`, then a defect-injection pass.

Clean base model (target composition):

| Element | Count | Notes |
|---|---|---|
| IfcBuilding / IfcSite / IfcProject | 1 each | Standard spatial tree |
| IfcBuildingStorey | 3 | Elevations 0, 3.5, 7.0 m; names `L00`, `L01`, `L02` |
| IfcWall (+ IfcWallType) | ~24 | Mix of external/internal; `Pset_WallCommon` (IsExternal, FireRating, LoadBearing) |
| IfcDoor (+ IfcDoorType) | ~8 | `Pset_DoorCommon` (FireRating, IsExternal) |
| IfcWindow (+ IfcWindowType) | ~8 | `Pset_WindowCommon` |
| IfcSlab | 3 | one per storey |
| IfcSpace | ~6 | Names and `Pset_SpaceCommon` |
| Classification | Uniclass 2015 or project code set | Every type and instance classified |

Every element carries the full required property set so that the clean model yields **zero** findings under the benchmark IDS — the clean reference case.

### 2.2 Defect catalogue (target 18 defects + 6 explicit clean controls)

| Defect id | Rule family | Injection | Expected finding |
|---|---|---|---|
| D01–D04 | `property.required` | Remove `FireRating` from 2 external walls; set `FireRating=""` on 1 door; set `FireRating="TBC"` on 1 wall | 4 findings, one per element |
| D05–D06 | `property.required` | Remove entire `Pset_WallCommon` from 1 wall; remove `Pset_SpaceCommon` from 1 space | 2 findings |
| D07–D10 | `naming.pattern` | Rename 2 walls to not match `^W-\d{3}$`; rename 1 storey to `Level 1`; rename 1 door type | 4 findings |
| D11–D14 | `classification.*` | Remove classification from 2 windows; assign wrong system to 1 wall; give 1 wall instance a code differing from its type's code | 4 findings |
| D15–D16 | `spatial.contained` (P1) | Remove containment from 1 door; contain 1 wall in the wrong storey | 2 findings (P1; excluded from P0 metrics if rule not shipped) |
| D17 | `identity.unique_global_id` (P1) | Duplicate one GlobalId | 1 finding (P1) |
| D18 | IDS applicability | External wall with `IsExternal=FALSE` but external by name — tests that IDS applicability does not over-flag | 0 findings; control |
| C01–C06 | clean controls | Elements deliberately near the rule boundary (e.g. `FireRating="REI 60"`, name `W-001`, correct classification) | 0 findings |

`ground_truth.json` records for each defect: `defect_id`, `global_id(s)`, `rule_id`, `expected_observed`, `expected_expected`, `priority`.

### 2.3 Supporting artefacts

- `benchmark.ids` — IDS 1.0 encoding the property and classification requirements.
- `benchmark_bep.md` — a simplified BEP (~2 pages) whose clauses correspond to the IDS and the naming rules, used to evaluate requirement extraction.
- `benchmark_objectives.json` — 6–8 natural-language review objectives with the expected set of checks (used for planner evaluation).

### 2.4 Test data requirements

- Redistributable under the repository licence (synthetic) — satisfies NFR-15.
- Small enough to load in the browser in seconds (< 5 MB).
- Both IFC4 and IFC2X3 exports of the same model if IfcOpenShell API permits, to test schema handling.

## 3. Accuracy metrics (deterministic findings)

A finding matches a ground-truth defect when `rule_id` and the set of `global_id`s are equal.

| Metric | Definition | Threshold |
|---|---|---|
| Precision | matched findings / all findings | ≥ 0.90 (NFR-02) |
| Recall | matched defects / all defects in scope | ≥ 0.90 (NFR-02) |
| Per-rule precision/recall | as above, partitioned by `rule_id` | reported; no threshold |
| False positives on clean controls | findings whose elements are in C01–C06 | 0 |
| Determinism | `findings.json` of run 1 == run 2 (timestamps excluded) | identical (NFR-01) |

Reported as a confusion matrix per rule family plus the aggregate. P1 defects (D15–D17) are reported separately and excluded from the P0 aggregate until the rules ship.

## 4. Evidence verification (explanations)

| Metric | Definition | Threshold |
|---|---|---|
| Grounding pass rate (first attempt) | explanations passing the grounding check on the first generation | reported; target ≥ 0.80 |
| Grounding pass rate (shipped) | explanations shipped to UI/report that passed, including regeneration | 1.00 (NFR-03) |
| Fallback rate | explanations replaced by the deterministic template | reported |
| Citation coverage | fraction of affected GlobalIds cited in the explanation | reported |

**Adversarial unit fixtures** for the grounding checker: explanation citing a GlobalId from another finding; citing a property not in the bundle; quoting a numeric value not in evidence; citing nothing (should pass but be flagged `low_specificity`).

**Human rubric (sample of 10 explanations, scored 1–5 by the project owner):** technical correctness of the probable cause; actionability of the corrective action; appropriate hedging. Rubric scores are reported as subjective and are not an acceptance gate.

## 5. Agent reliability evaluation

Run over `benchmark_objectives.json` with the live model once (recorded) and replayed thereafter.

| Metric | Definition | Threshold |
|---|---|---|
| Plan schema validity | plans parsing as `ReviewPlan` without error | 1.00 |
| Plan admissibility | planned checks referencing registered tools and confirmed requirements | reported; target ≥ 0.95 |
| Plan relevance | planned check set vs expected set per objective: Jaccard similarity | reported; target ≥ 0.80 mean |
| Tool-call argument validity | tool calls whose arguments validate against the tool schema | reported; target ≥ 0.95 |
| Cap hits | runs that hit `MAX_TOOL_CALLS_PER_RUN` | 0 on benchmark |
| Requirement extraction | candidates with verbatim-verified quotes / all candidates; recall against the BEP's intended clauses | reported |
| Token usage and cost | per run from API `usage` | ≤ 150k input tokens (NFR-05) |

## 6. Baseline comparisons

| Baseline | What it shows |
|---|---|
| **IfcTester CLI alone** on `benchmark.ids` | Our IDS findings must match IfcTester's report element-for-element (FR-VAL-01). Establishes that the system adds native rules, interpretation and explanation on top of, not instead of, the reference validator. |
| **Default plan, LLM disabled** | Same deterministic findings as a planned run on the full objective — demonstrates the planner changes *which* checks run, never *what* a check finds. |
| **Templated explanations vs LLM explanations** | Human rubric on both; shows whether the LLM adds explanatory value over templates. |

Comparisons with commercial checkers are **not** made; no claim of superiority is supported or intended.

## 7. Reproduction

```bash
# from repository root, Python 3.12 virtual environment active
cd backend && pip install -e ".[dev]" && cd ..
python evaluation/benchmark/generate.py          # writes evaluation/benchmark/generated/
python evaluation/run_eval.py --replay            # deterministic, no API calls
python evaluation/run_eval.py --live              # requires MODEL_API_KEY and approval; records new fixtures
```

Outputs: `evaluation/runs/<timestamp>/metrics.json`, `confusion.md`, `run.log.jsonl`. Results are copied into §8 of this document by hand with the commit hash.

## 8. Results

_No results yet. This section will contain the measured confusion matrix, per-rule metrics, grounding rates, planner metrics and token usage, with the commit hash and date of the run._

## 9. Known limitations

- A synthetic benchmark under-represents real-world messiness (inconsistent psets, exotic classifications, proxies). Results generalise only to the defect types injected.
- Grounding checks verify citations, not reasoning quality; a grounded explanation can still give poor advice. The human rubric is small and subjective.
- Planner relevance uses hand-written expected check sets; alternative reasonable plans are penalised.
- Replayed LLM runs demonstrate pipeline determinism, not model stability over time.
- Performance targets (NFR-04) are assumptions until measured on the demonstration hardware.

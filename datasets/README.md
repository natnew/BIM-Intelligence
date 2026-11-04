# Datasets

IFC test models and their companion files (IDS, a simplified BIM Execution Plan and ground truth)
used by the synthetic benchmark.

## What may live here

| Kind | Source | Licence | Location |
|---|---|---|---|
| **Synthetic** | Generated deterministically by [`tests/evaluation/benchmark.py`](../tests/evaluation/benchmark.py) with IfcOpenShell | Project licence (MIT) | `datasets/synthetic/generated/` (generated on demand; git-ignored) |
| **Permitted** | Openly licensed sample files whose licence allows redistribution | As recorded for each file in `datasets/permitted/LICENCES.md` | `datasets/permitted/` (not used yet) |

Never commit:

- real project models, or anything derived from them;
- files larger than about 5 MB (the benchmark is designed to load in the browser in seconds);
- generated outputs (`datasets/**/generated/` is git-ignored and rebuilt by the runner).

If you add a permitted file, create `datasets/permitted/LICENCES.md` and record its source URL,
licence and required attribution there.

Fixture IFC files are read-only. Produce variants by script, never by editing a file in place.

Keep private models and documents outside the repository, for example in the git-ignored
`local-private/` folder, and only send data to a model provider if you have the right to share it.
See the [private-data rules](../AGENTS.md#private-data-handling-and-provenance).

## The synthetic benchmark

The generator builds an IFC4 reference model, a defective copy with injected defects, an IDS, an
injection manifest, independently checked ground truth, a simplified BIM Execution Plan and example
review objectives. It does not touch the minimal fixtures in `tests/fixtures/`.

Run it from the repository root, with the development environment active:

```bash
python -c "import sys; sys.path.insert(0, 'tests'); from evaluation.run_eval import main; raise SystemExit(main())"
```

The runner regenerates the inputs, runs the deterministic review and writes the results, the defect
catalogue and file hashes to `tests/evaluation/runs/latest/` (git-ignored). It makes no network or
model API calls.

The benchmark contains 15 labelled defects across three rule families (required properties, naming
patterns and classification) and seven clean controls. On this benchmark the deterministic
validator scores 1.000 precision, recall and F1. That is a narrow synthetic result: it does not
measure accuracy on real project models or the quality of Muse Spark's planning or explanations.

The evaluation regression tests run with the default test suite:

```bash
python -m pytest tests/unit/evaluation tests/evaluation/test_run_eval.py -q
```

A second dataset based on an openly licensed public model is an open question; see
[ADR-011](../docs/DECISIONS.md#adr-011-synthetic-benchmark-with-defect-injection).

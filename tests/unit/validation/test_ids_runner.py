"""IDS runner and finding normaliser on the minimal fixture (FR-VAL-01, FR-VAL-07, AC-06, AC-07).

Every expectation here is a verified IfcTester outcome: findings are cross-checked against
IfcTester's own JSON reporter so the normaliser can never claim a failure the engine did not
produce (ADR-001, C-05).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from typing import Any

import ifcopenshell
import ifctester.ids
import ifctester.reporter
import pytest

from bim_intelligence.bim import ModelIndex, build_index, open_ifc
from bim_intelligence.schemas import CheckSpec, Finding, findings_to_json
from bim_intelligence.validation import (
    CheckOutcome,
    compile_ids,
    hydrate_specification,
    run_ids_check,
)
from fixtures.make_minimal_ifc import GLOBAL_IDS, IFC_PATH, SPEC_CLASSIFICATION, SPEC_FIRE_RATING
from support.ids import (
    CLASSIFICATION_SPEC,
    DOOR_SPEC,
    FIRE_RATING_SPEC,
    FIXTURE_IDS_BYTES,
    IFC2X3_ONLY_SPEC,
    NO_INTERNAL_WALLS_SPEC,
    ids_document,
)

W1, W2, W3 = GLOBAL_IDS["W-001"], GLOBAL_IDS["W-002"], GLOBAL_IDS["W-003"]


@pytest.fixture(scope="module")
def model() -> Iterator[ifcopenshell.file]:
    yield open_ifc(IFC_PATH)


@pytest.fixture(scope="module")
def index(model: ifcopenshell.file) -> ModelIndex:
    return build_index(model, model_hash=hashlib.sha256(IFC_PATH.read_bytes()).hexdigest())


def _check(document: bytes, position: int = 0) -> CheckSpec:
    return compile_ids(document).specifications[position].check


def _run(model: ifcopenshell.file, index: ModelIndex, document: bytes, position: int = 0) -> Any:
    return run_ids_check(model, index, _check(document, position), requirement_id=f"REQ-{position}")


# -- the two fixture defects --------------------------------------------------------------


def test_fire_rating_check_fails_for_w002_only(model: ifcopenshell.file, index: ModelIndex) -> None:
    outcome = _run(model, index, FIXTURE_IDS_BYTES, 0)
    assert outcome.result.status == "failed"
    assert outcome.result.applicable_count == 2
    assert outcome.result.requirement_id == "REQ-0"
    assert [finding.elements[0].global_id for finding in outcome.findings] == [W2]
    assert outcome.result.finding_ids == [outcome.findings[0].id]


def test_w001_passes_both_specifications(model: ifcopenshell.file, index: ModelIndex) -> None:
    for position in (0, 1):
        flagged = {
            e.global_id
            for f in _run(model, index, FIXTURE_IDS_BYTES, position).findings
            for e in f.elements
        }
        assert W1 not in flagged


def test_w003_is_not_applicable_to_the_fire_rating_specification(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    outcome = _run(model, index, FIXTURE_IDS_BYTES, 0)
    assert W3 not in {e.global_id for f in outcome.findings for e in f.elements}
    assert outcome.result.applicable_count == 2  # W-001 and W-002 only


def test_classification_check_fails_for_w003_only(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    outcome = _run(model, index, FIXTURE_IDS_BYTES, 1)
    assert outcome.result.status == "failed"
    assert outcome.result.applicable_count == 3
    assert [finding.elements[0].global_id for finding in outcome.findings] == [W3]


def test_exactly_two_findings_across_the_fixture(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    findings = [
        finding
        for position in (0, 1)
        for finding in _run(model, index, FIXTURE_IDS_BYTES, position).findings
    ]
    assert len(findings) == 2
    assert {f.elements[0].global_id for f in findings} == {W2, W3}


def test_findings_carry_full_provenance(model: ifcopenshell.file, index: ModelIndex) -> None:
    check = _check(FIXTURE_IDS_BYTES, 0)
    outcome = run_ids_check(model, index, check, requirement_id="REQ-001")
    (finding,) = outcome.findings
    assert finding.method == "ids"
    assert finding.check_id == check.id
    assert finding.requirement_id == "REQ-001"
    assert finding.rule_id == f"ids:{SPEC_FIRE_RATING}"
    assert finding.rule_version == check.rule_version
    assert finding.facet_index == 0
    assert finding.severity == "error"
    assert finding.category == "property_requirement"
    assert finding.observed == "The property set does not contain the required property"
    assert finding.expected == "FireRating data shall be provided in the dataset Pset_WallCommon"
    element = finding.elements[0]
    assert element.global_id == W2
    assert element.express_id == 59
    assert element.ifc_type == "IfcWall"
    assert element.name == "W-002"
    assert element.storey == "L00"
    # The element reference is the index's own, so viewer, element API and finding agree.
    assert element == index.by_global_id(W2).ref


def test_classification_finding_text(model: ifcopenshell.file, index: ModelIndex) -> None:
    (finding,) = _run(model, index, FIXTURE_IDS_BYTES, 1).findings
    assert finding.rule_id == f"ids:{SPEC_CLASSIFICATION}"
    assert finding.category == "classification_requirement"
    assert finding.observed == "The entity has no classification"
    assert finding.expected == "Shall be classified using Uniclass 2015"


# -- cross-check against IfcTester's own report -------------------------------------------


def test_findings_match_ifctester_json_report_element_for_element(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    """FR-VAL-01 acceptance: the normaliser neither drops nor invents a failure."""
    ids = ifctester.ids.open(str(IFC_PATH.with_name("minimal.ids")), validate=True)
    ids.validate(model)
    reporter = ifctester.reporter.Json(ids)
    reporter.report()
    reported = {
        (spec["name"], facet_index, entity["global_id"], entity["reason"])
        for spec in reporter.results["specifications"]
        for facet_index, requirement in enumerate(spec["requirements"])
        for entity in requirement["failed_entities"]
    }

    normalised = {
        (finding.rule_id.removeprefix("ids:"), finding.facet_index, e.global_id, finding.observed)
        for position in (0, 1)
        for finding in _run(model, index, FIXTURE_IDS_BYTES, position).findings
        for e in finding.elements
    }
    assert normalised == reported
    assert len(reported) == 2


# -- execution semantics (AC-07) -----------------------------------------------------------


def test_required_specification_with_no_applicable_entities_is_not_applicable(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    outcome = _run(model, index, ids_document(DOOR_SPEC))
    assert outcome.result.status == "not_applicable"
    assert outcome.result.applicable_count == 0
    assert outcome.findings == ()
    assert outcome.result.finding_ids == []
    assert any("no entities" in note.lower() for note in outcome.result.diagnostics)


def test_prohibited_specification_reports_each_applicable_entity(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    check = _check(ids_document(NO_INTERNAL_WALLS_SPEC))
    outcome = run_ids_check(model, index, check, requirement_id="REQ-P")
    assert outcome.result.status == "failed"
    assert outcome.result.applicable_count == 1
    (finding,) = outcome.findings
    assert finding.category == "prohibited_entity"
    assert finding.facet_index == 0
    assert finding.elements[0].global_id == W3
    assert "prohibited" in finding.expected.lower() or "shall not" in finding.expected.lower()
    assert "W-003" in finding.observed


def test_prohibited_specification_with_no_applicable_entities_passes(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    no_doors = NO_INTERNAL_WALLS_SPEC.replace("IFCWALL", "IFCDOOR")
    outcome = _run(model, index, ids_document(no_doors))
    assert outcome.result.status == "passed"
    assert outcome.result.applicable_count == 0
    assert outcome.findings == ()


def test_specification_for_another_ifc_schema_is_skipped_not_passed(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    outcome = _run(model, index, ids_document(IFC2X3_ONLY_SPEC))
    assert outcome.result.status == "skipped"
    assert outcome.result.applicable_count == 0
    assert outcome.findings == ()
    assert any("IFC2X3" in note and "IFC4" in note for note in outcome.result.diagnostics)


def test_engine_exception_is_an_error_result_without_findings(
    model: ifcopenshell.file, index: ModelIndex, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(self: Any, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("facet evaluation failed inside ifctester")

    monkeypatch.setattr(ifctester.ids.Specification, "validate", explode)
    outcome = _run(model, index, FIXTURE_IDS_BYTES, 0)
    assert outcome.result.status == "error"
    assert outcome.findings == ()
    assert outcome.result.finding_ids == []
    assert outcome.result.applicable_count == 0
    assert any(
        "RuntimeError" in d and "facet evaluation failed" in d for d in outcome.result.diagnostics
    )


def test_tampered_check_spec_is_an_error_not_a_weaker_check(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    original = _check(FIXTURE_IDS_BYTES, 0)
    assert original.ids_specification is not None
    tampered = CheckSpec(
        kind="ids",
        rule_id=original.rule_id,
        rule_version=original.rule_version,
        ids_specification=original.ids_specification.replace("FireRating", "Name"),
    )
    outcome = run_ids_check(model, index, tampered, requirement_id="REQ-T")
    assert outcome.result.status == "error"
    assert outcome.findings == ()
    assert any("rule_version" in d for d in outcome.result.diagnostics)


# -- determinism and read-only guarantees --------------------------------------------------


def test_repeated_runs_serialise_to_identical_findings_json(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    def run_all() -> list[Finding]:
        return [f for p in (0, 1) for f in _run(model, index, FIXTURE_IDS_BYTES, p).findings]

    first, second = findings_to_json(run_all()), findings_to_json(run_all())
    assert first == second
    assert first.endswith("\n")


def test_running_checks_does_not_modify_the_model_file(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    before = IFC_PATH.read_bytes()
    for position in (0, 1):
        _run(model, index, FIXTURE_IDS_BYTES, position)
    assert IFC_PATH.read_bytes() == before


def test_outcome_is_immutable(model: ifcopenshell.file, index: ModelIndex) -> None:
    outcome: CheckOutcome = _run(model, index, FIXTURE_IDS_BYTES, 0)
    with pytest.raises(AttributeError):
        outcome.findings = ()  # type: ignore[misc]


def test_hydrated_specifications_are_independent_per_run(
    model: ifcopenshell.file, index: ModelIndex
) -> None:
    """Each run hydrates afresh, so IfcTester state from one run cannot leak into the next."""
    check = _check(ids_document(FIRE_RATING_SPEC, CLASSIFICATION_SPEC), 0)
    first = hydrate_specification(check)
    second = hydrate_specification(check)
    assert first is not second
    assert first.failed_entities == set() and second.failed_entities == set()

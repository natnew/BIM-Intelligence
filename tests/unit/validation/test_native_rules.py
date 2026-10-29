"""Registered native rule outcomes, applicability and parameter integrity (FR-VAL-04)."""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.api.classification
import ifcopenshell.api.root
import ifcopenshell.api.type

from bim_intelligence.bim import ModelIndex, build_index
from bim_intelligence.schemas import CheckSpec
from bim_intelligence.validation import (
    CLASSIFICATION_CONSISTENCY_RULE_ID,
    CLASSIFICATION_CONSISTENCY_RULE_VERSION,
    classification_consistency_check,
    run_native_check,
)
from fixtures.make_minimal_ifc import GLOBAL_IDS, build_minimal_ifc
from fixtures.variants import add_misclassified_w002_type, wall


def _index(model: ifcopenshell.file) -> ModelIndex:
    return build_index(model, model_hash="0" * 64)


def _classified_type(model: ifcopenshell.file) -> None:
    wall_type = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcWallType", name="WT-CONSISTENT"
    )
    system = model.by_type("IfcClassification")[0]
    ifcopenshell.api.classification.add_reference(
        model,
        products=[wall_type],
        identification="Ss_25_10_30",
        name="Wall classification",
        classification=system,
    )
    ifcopenshell.api.type.assign_type(
        model, related_objects=[wall(model, "W-002")], relating_type=wall_type
    )


def test_classification_consistency_passes_for_inherited_type_classification() -> None:
    model = build_minimal_ifc()
    _classified_type(model)

    outcome = run_native_check(
        _index(model), classification_consistency_check(), requirement_id="R1"
    )

    assert outcome.result.status == "passed"
    assert outcome.result.applicable_count == 1
    assert outcome.findings == ()


def test_classification_consistency_finds_an_instance_that_disagrees_with_its_type() -> None:
    model = build_minimal_ifc()
    add_misclassified_w002_type(model)
    check = classification_consistency_check()

    outcome = run_native_check(_index(model), check, requirement_id="R1")

    assert outcome.result.status == "failed"
    assert outcome.result.applicable_count == 1
    (finding,) = outcome.findings
    assert finding.check_id == check.id
    assert finding.rule_id == CLASSIFICATION_CONSISTENCY_RULE_ID
    assert finding.rule_version == CLASSIFICATION_CONSISTENCY_RULE_VERSION
    assert finding.method == "native"
    assert finding.category == "classification_inconsistent"
    assert finding.elements[0].global_id == GLOBAL_IDS["W-002"]
    assert finding.observed == "'W-002' uses Uniclass 2015: WRONG-CODE."
    assert finding.expected == "Type 'WT-CLASSIFIED' uses Uniclass 2015: Ss_25_10_30."


def test_untyped_or_unclassified_type_is_not_applicable() -> None:
    model = build_minimal_ifc()

    outcome = run_native_check(
        _index(model), classification_consistency_check(), requirement_id="R1"
    )

    assert outcome.result.status == "not_applicable"
    assert outcome.result.applicable_count == 0
    assert outcome.result.finding_ids == []
    assert outcome.result.diagnostics
    assert outcome.findings == ()


def test_invalid_native_parameters_are_an_error_not_a_weaker_pass() -> None:
    model = build_minimal_ifc()
    add_misclassified_w002_type(model)
    invalid_check = CheckSpec(
        kind="native",
        rule_id=CLASSIFICATION_CONSISTENCY_RULE_ID,
        rule_version=CLASSIFICATION_CONSISTENCY_RULE_VERSION,
        params={"expected": "WRONG-CODE"},
    )

    outcome = run_native_check(_index(model), invalid_check, requirement_id="R1")

    assert outcome.result.status == "error"
    assert outcome.result.finding_ids == []
    assert any("accepts no parameters" in item for item in outcome.result.diagnostics)
    assert outcome.findings == ()


def test_unknown_rule_and_version_are_execution_errors() -> None:
    base = classification_consistency_check()
    cases = (
        CheckSpec(
            kind="native",
            rule_id="classification.unknown",
            rule_version=base.rule_version,
        ),
        CheckSpec(
            kind="native",
            rule_id=base.rule_id,
            rule_version="0.0.0",
        ),
    )

    for check in cases:
        outcome = run_native_check(_index(build_minimal_ifc()), check, requirement_id="R1")
        assert outcome.result.status == "error"
        assert outcome.result.finding_ids == []
        assert outcome.findings == ()


def test_rule_configuration_has_no_user_mutable_parameters() -> None:
    check = classification_consistency_check()

    assert check.kind == "native"
    assert check.params == {}
    assert check.rule_id == CLASSIFICATION_CONSISTENCY_RULE_ID
    assert check.rule_version == CLASSIFICATION_CONSISTENCY_RULE_VERSION

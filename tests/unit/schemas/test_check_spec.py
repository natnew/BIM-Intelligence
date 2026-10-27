"""CheckSpec: immutable, content-addressed description of what a check asserts (C-02)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bim_intelligence.schemas import CheckSpec

IDS_XML = (
    '<specification name="External walls carry a fire rating" minOccurs="1" maxOccurs="unbounded">'
    "<applicability/><requirements/></specification>"
)


def test_ids_check_id_is_derived_from_content() -> None:
    first = CheckSpec(
        kind="ids", rule_id="ids:fire", rule_version="9f8e7d6c", ids_specification=IDS_XML
    )
    second = CheckSpec(
        kind="ids", rule_id="ids:fire", rule_version="9f8e7d6c", ids_specification=IDS_XML
    )
    assert first.id == second.id
    assert len(first.id) == 16
    assert first == second


def test_native_check_id_changes_when_params_change() -> None:
    strict = CheckSpec(
        kind="native",
        rule_id="naming.pattern",
        rule_version="1.0.0",
        params={"ifc_type": "IfcWall", "pattern": "^W-\\d{3}$"},
    )
    loose = CheckSpec(
        kind="native",
        rule_id="naming.pattern",
        rule_version="1.0.0",
        params={"ifc_type": "IfcWall", "pattern": "^W-.*$"},
    )
    assert strict.id != loose.id


def test_param_key_order_does_not_change_identity() -> None:
    a = CheckSpec(kind="native", rule_id="r", rule_version="1", params={"x": 1, "y": [1, 2]})
    b = CheckSpec(kind="native", rule_id="r", rule_version="1", params={"y": [1, 2], "x": 1})
    assert a.id == b.id


def test_rule_version_is_part_of_identity() -> None:
    a = CheckSpec(kind="native", rule_id="r", rule_version="1.0.0")
    b = CheckSpec(kind="native", rule_id="r", rule_version="1.0.1")
    assert a.id != b.id


def test_supplied_id_must_match_content() -> None:
    spec = CheckSpec(kind="native", rule_id="r", rule_version="1")
    assert CheckSpec.model_validate(spec.model_dump()) == spec
    with pytest.raises(ValidationError, match="content-addressed"):
        CheckSpec(id="0123456789abcdef", kind="native", rule_id="r", rule_version="1")


def test_ids_kind_requires_specification_and_forbids_params() -> None:
    with pytest.raises(ValidationError, match="ids_specification"):
        CheckSpec(kind="ids", rule_id="ids:x", rule_version="1")
    with pytest.raises(ValidationError, match="params"):
        CheckSpec(
            kind="ids",
            rule_id="ids:x",
            rule_version="1",
            ids_specification=IDS_XML,
            params={"a": 1},
        )


def test_native_kind_forbids_ids_specification() -> None:
    with pytest.raises(ValidationError, match="ids_specification"):
        CheckSpec(kind="native", rule_id="r", rule_version="1", ids_specification=IDS_XML)


def test_only_ids_and_native_kinds_exist() -> None:
    with pytest.raises(ValidationError):
        CheckSpec.model_validate({"kind": "llm", "rule_id": "r", "rule_version": "1"})


def test_check_spec_is_immutable() -> None:
    spec = CheckSpec(kind="native", rule_id="r", rule_version="1")
    with pytest.raises(ValidationError):
        spec.rule_version = "2"  # type: ignore[misc]

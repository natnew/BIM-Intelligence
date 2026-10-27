"""Finding identity, ordering and the deterministic-method invariant (AC-10, AC-18, C-03)."""

from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from bim_intelligence.schemas import ElementRef, Finding, findings_to_json, sort_findings

W1 = ElementRef(
    global_id="2O2Fr$t4X7Zf8NOew3FLKr", express_id=101, ifc_type="IfcWall", name="W-001"
)
W2 = ElementRef(
    global_id="1hqIFTRjfV6AWq_bMtnZwI", express_id=102, ifc_type="IfcWall", name="W-002"
)
W3 = ElementRef(
    global_id="0b3b5c5f1e2d4a6b8c9d0e", express_id=103, ifc_type="IfcWall", name="W-003"
)
NO_GUID = ElementRef(global_id=None, express_id=7, ifc_type="IfcPropertySet")


def make_finding(**overrides: object) -> Finding:
    data: dict[str, object] = {
        "check_id": "a3f1c2d4e5f60718",
        "requirement_id": "REQ-001",
        "rule_id": "ids:External walls carry a fire rating",
        "rule_version": "9f8e7d6c",
        "facet_index": 0,
        "severity": "error",
        "category": "property_missing",
        "elements": [W2],
        "observed": "Pset_WallCommon.FireRating is absent",
        "expected": "Pset_WallCommon.FireRating shall be provided",
        "method": "ids",
    }
    data.update(overrides)
    return Finding.model_validate(data)


def expected_id(check_id: str, rule_version: str, facet_index: int, *element_keys: str) -> str:
    material = "|".join([check_id, rule_version, str(facet_index), *sorted(element_keys)])
    return hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]


def test_id_is_derived_from_content_per_c03_formula() -> None:
    finding = make_finding()
    assert finding.id == expected_id("a3f1c2d4e5f60718", "9f8e7d6c", 0, W2.global_id or "")
    assert len(finding.id) == 16


def test_id_is_stable_across_constructions_and_json_round_trip() -> None:
    first = make_finding()
    second = make_finding()
    assert first.id == second.id
    restored = Finding.model_validate_json(first.model_dump_json())
    assert restored == first
    assert restored.id == first.id


def test_id_changes_when_rule_version_changes() -> None:
    assert make_finding().id != make_finding(rule_version="00000001").id


def test_id_changes_when_check_or_facet_or_elements_change() -> None:
    base = make_finding()
    assert base.id != make_finding(check_id="ffffffffffffffff").id
    assert base.id != make_finding(facet_index=1).id
    assert base.id != make_finding(elements=[W1]).id
    assert base.id != make_finding(elements=[W1, W2]).id


def test_id_and_element_order_are_independent_of_insertion_order() -> None:
    forward = make_finding(elements=[W1, W2, W3])
    backward = make_finding(elements=[W3, W2, W1])
    assert forward.id == backward.id
    assert forward.elements == backward.elements
    assert [element.name for element in forward.elements] == ["W-003", "W-002", "W-001"]
    assert forward.model_dump_json() == backward.model_dump_json()


def test_elements_without_global_id_are_keyed_by_express_id() -> None:
    finding = make_finding(elements=[NO_GUID])
    assert finding.id == expected_id("a3f1c2d4e5f60718", "9f8e7d6c", 0, "#7")


def test_supplied_id_must_match_derived_id() -> None:
    finding = make_finding()
    assert make_finding(id=finding.id) == finding
    with pytest.raises(ValidationError, match="content-addressed"):
        make_finding(id="0123456789abcdef")


def test_method_llm_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_finding(method="llm")


@pytest.mark.parametrize("method", ["ids", "native"])
def test_method_accepts_only_deterministic_engines(method: str) -> None:
    assert make_finding(method=method).method == method


def test_finding_has_no_timestamp_or_run_reference() -> None:
    assert "created_at" not in Finding.model_fields
    assert "run_id" not in Finding.model_fields
    with pytest.raises(ValidationError):
        make_finding(created_at="2026-10-27T00:00:00Z")


def test_finding_requires_at_least_one_element() -> None:
    with pytest.raises(ValidationError):
        make_finding(elements=[])


def test_finding_is_immutable() -> None:
    finding = make_finding()
    with pytest.raises(ValidationError):
        finding.observed = "tampered"  # type: ignore[misc]


def test_category_is_snake_case_identifier() -> None:
    assert make_finding(category="prohibited_entity").category == "prohibited_entity"
    with pytest.raises(ValidationError):
        make_finding(category="Prohibited Entity")


def test_sort_findings_is_canonical_regardless_of_insertion_order() -> None:
    a = make_finding(check_id="aaaaaaaaaaaaaaaa", facet_index=1, elements=[W1])
    b = make_finding(check_id="aaaaaaaaaaaaaaaa", facet_index=0, elements=[W3])
    c = make_finding(check_id="aaaaaaaaaaaaaaaa", facet_index=0, elements=[W2])
    d = make_finding(check_id="0000000000000000", facet_index=5, elements=[W1])
    # Keys: W3 "0b…" < W2 "1h…" < W1 "2O…"; check_id first, then facet_index, then first element.
    expected = [d, b, c, a]
    assert sort_findings([a, b, c, d]) == expected
    assert sort_findings([c, a, d, b]) == expected


def test_findings_to_json_is_byte_identical_for_permuted_input() -> None:
    a = make_finding(elements=[W1])
    b = make_finding(elements=[W2])
    c = make_finding(check_id="0000000000000000", elements=[W3])
    first = findings_to_json([a, b, c])
    second = findings_to_json([c, b, a])
    assert first == second
    assert first.endswith("\n")
    parsed = json.loads(first)
    assert [item["id"] for item in parsed] == [c.id, b.id, a.id]
    assert list(parsed[0].keys()) == sorted(parsed[0].keys())

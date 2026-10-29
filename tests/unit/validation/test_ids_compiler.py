"""IDS import: XSD validation, per-specification CheckSpecs and lossless re-hydration (FR-REQ-05).

The compiler is the only place an IDS document is turned into executable checks. Each
``<specification>`` becomes one immutable ``CheckSpec`` whose payload is the canonicalised
element, so the same specification yields the same check id however the file was formatted.
"""

from __future__ import annotations

import hashlib
import socket
import xml.etree.ElementTree as ET
from typing import Any

import pytest

from bim_intelligence.schemas import CheckSpec, content_hash
from bim_intelligence.validation import (
    CheckSpecIntegrityError,
    InvalidIdsError,
    compile_ids,
    hydrate_specification,
    ids_schema,
)
from fixtures.make_minimal_ifc import SPEC_CLASSIFICATION, SPEC_FIRE_RATING
from support.ids import (
    CLASSIFICATION_SPEC,
    ENTITY_WALL,
    FIRE_RATING_SPEC,
    FIXTURE_IDS_BYTES,
    IDS_NS,
    MALFORMED_XML,
    NOT_IDS_XML,
    SCHEMA_INVALID_IDS,
    ids_document,
    specification,
)


def test_valid_ids_compiles_to_one_check_per_specification() -> None:
    compiled = compile_ids(FIXTURE_IDS_BYTES)
    assert compiled.title == "BIM Intelligence minimal fixture"
    assert compiled.sha256 == hashlib.sha256(FIXTURE_IDS_BYTES).hexdigest()
    assert [spec.name for spec in compiled.specifications] == [
        SPEC_FIRE_RATING,
        SPEC_CLASSIFICATION,
    ]
    assert [spec.index for spec in compiled.specifications] == [0, 1]
    for spec in compiled.specifications:
        assert spec.check.kind == "ids"
        assert spec.check.rule_id == f"ids:{spec.name}"
        assert spec.check.params == {}
        assert spec.check.ids_specification is not None
        assert spec.check.rule_version == content_hash(spec.check.ids_specification)


def test_two_specifications_give_two_distinct_check_specs() -> None:
    checks = [spec.check for spec in compile_ids(FIXTURE_IDS_BYTES).specifications]
    assert len(checks) == 2
    assert len({check.id for check in checks}) == 2


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        (MALFORMED_XML, "well-formed"),
        (SCHEMA_INVALID_IDS, "IDS 1.0"),
        (NOT_IDS_XML, "IDS 1.0"),
        (b"", "empty"),
    ],
    ids=["malformed-xml", "xsd-invalid", "not-an-ids", "empty"],
)
def test_malformed_or_unsupported_ids_is_rejected(data: bytes, fragment: str) -> None:
    with pytest.raises(InvalidIdsError, match=fragment):
        compile_ids(data)


def test_rejection_messages_never_echo_storage_paths() -> None:
    with pytest.raises(InvalidIdsError) as excinfo:
        compile_ids(SCHEMA_INVALID_IDS)
    message = str(excinfo.value)
    assert "\\" not in message and "/tmp" not in message and ".ids file (" not in message


def test_specification_payload_is_canonical_and_formatting_independent() -> None:
    compact = compile_ids(ids_document(FIRE_RATING_SPEC)).specifications[0].check
    pretty_xml = ET.fromstring(ids_document(FIRE_RATING_SPEC))
    ET.indent(pretty_xml, space="    ")
    pretty = compile_ids(ET.tostring(pretty_xml, encoding="utf-8")).specifications[0].check
    assert compact == pretty
    assert compact.ids_specification is not None
    assert compact.ids_specification.startswith(f'<specification xmlns="{IDS_NS}"')
    assert "\n" not in compact.ids_specification


def test_fixture_specification_matches_in_memory_equivalent() -> None:
    """The committed IDS and the test helper describe the same two checks."""
    from_file = [spec.check.id for spec in compile_ids(FIXTURE_IDS_BYTES).specifications]
    from_helper = [
        spec.check.id
        for spec in compile_ids(ids_document(FIRE_RATING_SPEC, CLASSIFICATION_SPEC)).specifications
    ]
    assert from_file == from_helper


def test_identifier_attribute_is_preferred_for_rule_id() -> None:
    spec = specification("Walls classified", ENTITY_WALL, identifier="BEP-4.2")
    compiled = compile_ids(ids_document(spec)).specifications[0]
    assert compiled.identifier == "BEP-4.2"
    assert compiled.check.rule_id == "ids:BEP-4.2"


def test_hydrated_specification_reproduces_the_compiled_facets() -> None:
    compiled = compile_ids(FIXTURE_IDS_BYTES).specifications[0]
    spec = hydrate_specification(compiled.check)
    assert spec.name == SPEC_FIRE_RATING
    assert spec.get_usage() == "required"
    assert spec.ifcVersion == ["IFC4"]
    assert [type(facet).__name__ for facet in spec.applicability] == ["Entity", "Property"]
    assert [type(facet).__name__ for facet in spec.requirements] == ["Property"]


def test_hydration_refuses_a_check_whose_payload_was_altered() -> None:
    """Criteria of a confirmed check cannot be changed without changing its identity (C-02)."""
    original = compile_ids(FIXTURE_IDS_BYTES).specifications[0].check
    assert original.ids_specification is not None
    weakened_xml = original.ids_specification.replace("FireRating", "Name")
    # Keeping the old rule_version with new XML is the tampering case the runner must detect.
    tampered = CheckSpec(
        kind="ids",
        rule_id=original.rule_id,
        rule_version=original.rule_version,
        ids_specification=weakened_xml,
    )
    assert tampered.id != original.id
    with pytest.raises(CheckSpecIntegrityError, match="rule_version"):
        hydrate_specification(tampered)


def test_hydration_refuses_native_checks() -> None:
    native = CheckSpec(kind="native", rule_id="naming.pattern", rule_version="1.0.0")
    with pytest.raises(CheckSpecIntegrityError, match="ids"):
        hydrate_specification(native)


def test_schema_loading_and_validation_never_touch_the_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``ids.xsd`` imports W3C schemas by URL; they must resolve from bundled copies only."""

    def refuse(self: socket.socket, *args: Any, **kwargs: Any) -> None:
        raise AssertionError(f"network access attempted: {args}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    ids_schema.cache_clear()
    try:
        compiled = compile_ids(FIXTURE_IDS_BYTES)
        assert len(compiled.specifications) == 2
        assert hydrate_specification(compiled.specifications[0].check).name == SPEC_FIRE_RATING
        with pytest.raises(InvalidIdsError):
            compile_ids(SCHEMA_INVALID_IDS)
    finally:
        ids_schema.cache_clear()

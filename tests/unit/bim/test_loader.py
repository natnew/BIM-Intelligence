"""``open_ifc``: schema detection and structured failures (FR-ING-01, ARCHITECTURE §14)."""

from __future__ import annotations

from pathlib import Path

import ifcopenshell.api.project
import pytest

from bim_intelligence.bim import SUPPORTED_SCHEMAS, IfcLoadError, UnsupportedSchemaError, open_ifc
from fixtures.make_minimal_ifc import IFC_PATH
from fixtures.variants import write_ifc2x3

STEP_HEADER = (
    "ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION((''),'2;1');\n"
    "FILE_NAME('','',(''),(''),'','','');\nFILE_SCHEMA(('{schema}'));\nENDSEC;\nDATA;\n"
)
STEP_FOOTER = "ENDSEC;\nEND-ISO-10303-21;\n"


def test_fixture_opens_as_ifc4() -> None:
    model = open_ifc(IFC_PATH)
    assert model.schema == "IFC4"
    assert len(model.by_type("IfcWall")) == 3


def test_ifc2x3_is_supported(tmp_path: Path) -> None:
    assert open_ifc(write_ifc2x3(tmp_path)).schema == "IFC2X3"


def test_ifc4x3_opens_and_reports_its_schema_identifier(tmp_path: Path) -> None:
    model = ifcopenshell.api.project.create_file(version="IFC4X3")
    path = tmp_path / "x3.ifc"
    path.write_text(model.to_string(), encoding="utf-8")
    opened = open_ifc(path)
    assert opened.schema == "IFC4X3"
    assert opened.schema_identifier.startswith("IFC4X3")
    assert frozenset({"IFC2X3", "IFC4", "IFC4X3"}) == SUPPORTED_SCHEMAS


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("garbage.ifc", "this is not an IFC file\n"),
        ("empty.ifc", ""),
        ("json.ifc", '{"schema": "IFC4"}'),
    ],
)
def test_unparseable_input_is_an_ifc_load_error(tmp_path: Path, name: str, content: str) -> None:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IfcLoadError) as exc_info:
        open_ifc(path)
    assert not isinstance(exc_info.value, UnsupportedSchemaError)
    assert str(tmp_path) not in str(exc_info.value), "messages must not leak storage paths"


def test_unknown_schema_is_rejected_explicitly(tmp_path: Path) -> None:
    path = tmp_path / "future.ifc"
    path.write_text(STEP_HEADER.format(schema="IFC9X9") + STEP_FOOTER, encoding="utf-8")
    with pytest.raises(UnsupportedSchemaError, match="IFC9X9"):
        open_ifc(path)


def test_missing_file_is_an_ifc_load_error_without_the_path(tmp_path: Path) -> None:
    with pytest.raises(IfcLoadError) as exc_info:
        open_ifc(tmp_path / "absent.ifc")
    assert "absent" not in str(exc_info.value)


def test_unsupported_schema_error_is_a_load_error() -> None:
    assert issubclass(UnsupportedSchemaError, IfcLoadError)

"""IDS 1.0 import and per-specification compilation to ``CheckSpec`` (FR-REQ-05, ADR-015 §1).

Two directions, one source of truth:

* :func:`compile_ids` validates an uploaded document against IfcTester's bundled IDS 1.0 XSD
  and turns every ``<specification>`` into an immutable, content-addressed ``CheckSpec``. The
  payload is the element in XML Canonical Form (C14N 2.0) with whitespace-only text removed, so
  the same specification yields the same check id whatever the authoring tool's indentation.
* :func:`hydrate_specification` rebuilds an executable IfcTester ``Specification`` from that
  payload alone, through the same XSD, after confirming the payload still hashes to the check's
  ``rule_version``. The runner therefore executes exactly what was confirmed, never the document
  it came from and never a payload that has been edited since (C-02).

This module and :mod:`bim_intelligence.validation.ids_runner` are the only code that imports
``ifctester`` (AGENTS.md §3).
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import ifctester.ids
from xmlschema import XMLSchema, XMLSchemaValidationError

from bim_intelligence.schemas import CheckSpec, content_hash
from bim_intelligence.validation.errors import CheckSpecIntegrityError, InvalidIdsError

IDS_NAMESPACE = "http://standards.buildingsmart.org/IDS"
IDS_VERSION = "1.0"

_NS = {"ids": IDS_NAMESPACE}
_SPECIFICATION_TAG = f"{{{IDS_NAMESPACE}}}specification"
_WRAPPER_TITLE = "BIM Intelligence check"
# Serialise IDS elements with a default namespace rather than ``ns0:`` prefixes. This is the
# same process-wide registration ``ifctester.ids.Ids.to_xml`` performs.
ET.register_namespace("", IDS_NAMESPACE)


@lru_cache(maxsize=1)
def ids_schema() -> XMLSchema:
    """IfcTester's bundled IDS 1.0 XSD, loaded without touching the network.

    ``ids.xsd`` imports the W3C XML and XSD namespaces by URL. With xmlschema's defaults the
    first load tries those URLs before using its bundled copies, which is a silent outbound
    request (ARCHITECTURE §13 permits none) and a slow failure offline. ``allow="local"``
    restricts resource access to the file system; the bundled fallbacks satisfy the imports.
    """
    xsd = Path(ifctester.ids.__file__).with_name("ids.xsd")
    return XMLSchema(str(xsd), allow="local")


@dataclass(frozen=True)
class CompiledSpecification:
    """One ``<specification>`` of an imported IDS and the check compiled from it."""

    index: int
    name: str
    identifier: str | None
    description: str | None
    check: CheckSpec

    @property
    def title(self) -> str:
        return self.name or f"Specification {self.index + 1}"

    @property
    def statement(self) -> str:
        return self.description or self.title


@dataclass(frozen=True)
class CompiledIds:
    """A validated IDS document: its identity, title and the checks it defines, in order."""

    sha256: str
    title: str
    specifications: tuple[CompiledSpecification, ...]


def compile_ids(data: bytes) -> CompiledIds:
    """Validate ``data`` as IDS 1.0 and compile one ``CheckSpec`` per specification.

    Raises :class:`InvalidIdsError` for anything that is not a well-formed, schema-valid IDS
    document. The message describes the first violation without echoing storage paths.
    """
    if not data.strip():
        raise InvalidIdsError("The document is empty.")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise InvalidIdsError(f"The document is not well-formed XML: {exc}.") from exc
    _validate_against_schema(data)

    title = root.findtext("ids:info/ids:title", default="", namespaces=_NS).strip()
    specifications = tuple(
        _compile_specification(index, element)
        for index, element in enumerate(root.iterfind("ids:specifications/ids:specification", _NS))
    )
    if not specifications:
        raise InvalidIdsError(f"The IDS {IDS_VERSION} document declares no specifications.")
    return CompiledIds(
        sha256=hashlib.sha256(data).hexdigest(),
        title=title or "Untitled",
        specifications=specifications,
    )


def hydrate_specification(check: CheckSpec) -> ifctester.ids.Specification:
    """An executable IfcTester ``Specification`` built from ``check.ids_specification`` only."""
    if check.kind != "ids" or check.ids_specification is None:
        raise CheckSpecIntegrityError(
            f"Check {check.id} is of kind {check.kind!r}; only ids checks can be hydrated."
        )
    expected_version = content_hash(check.ids_specification)
    if check.rule_version != expected_version:
        raise CheckSpecIntegrityError(
            f"Check {check.id}: rule_version {check.rule_version!r} does not match the hash of "
            f"its specification payload ({expected_version!r}); the check was altered after it "
            "was confirmed."
        )
    document = (
        f'<ids xmlns="{IDS_NAMESPACE}"><info><title>{_WRAPPER_TITLE}</title></info>'
        f"<specifications>{check.ids_specification}</specifications></ids>"
    )
    try:
        decoded: Any = ids_schema().decode(
            document, strip_namespaces=True, namespaces={"": IDS_NAMESPACE}
        )
    except (XMLSchemaValidationError, ET.ParseError) as exc:
        raise CheckSpecIntegrityError(
            f"Check {check.id}: the stored specification no longer validates as IDS "
            f"{IDS_VERSION}: {_first_line(str(exc))}"
        ) from exc
    entries = decoded["specifications"]["specification"]
    entry = entries[0] if isinstance(entries, list) else entries
    specification: ifctester.ids.Specification = ifctester.ids.Specification().parse(entry)
    return specification


def canonical_specification_xml(element: ET.Element) -> str:
    """C14N 2.0 serialisation of a ``<specification>`` with indentation removed.

    Whitespace-only text and tail nodes carry no meaning in IDS (the schema has no mixed
    content), so stripping them makes the payload, and therefore ``CheckSpec.id``, independent
    of how the source file was formatted. Values inside ``<simpleValue>`` are untouched.
    """
    if element.tag != _SPECIFICATION_TAG:
        raise ValueError(f"Expected an IDS <specification> element, got {element.tag!r}.")
    copy = _without_insignificant_whitespace(element)
    return ET.canonicalize(ET.tostring(copy, encoding="unicode"))


def _compile_specification(index: int, element: ET.Element) -> CompiledSpecification:
    name = (element.get("name") or "").strip()
    identifier = (element.get("identifier") or "").strip() or None
    description = (element.get("description") or "").strip() or None
    xml = canonical_specification_xml(element)
    rule_id = f"ids:{identifier or name or f'specification-{index + 1}'}"
    check = CheckSpec(
        kind="ids", rule_id=rule_id, rule_version=content_hash(xml), ids_specification=xml
    )
    return CompiledSpecification(
        index=index, name=name, identifier=identifier, description=description, check=check
    )


def _validate_against_schema(data: bytes) -> None:
    try:
        ids_schema().validate(data.decode("utf-8"))
    except XMLSchemaValidationError as exc:
        raise InvalidIdsError(
            f"The document is not a valid IDS {IDS_VERSION} file: {_describe(exc)}"
        ) from exc
    except (ValueError, TypeError, ET.ParseError) as exc:
        raise InvalidIdsError(
            f"The document could not be read as IDS {IDS_VERSION}: {_first_line(str(exc))}"
        ) from exc


def _describe(exc: XMLSchemaValidationError) -> str:
    """One line naming the offending element and the reason; no source dumps, no paths."""
    reason: Any = exc.reason
    path: Any = exc.path
    text = _first_line(str(reason)) if reason else _first_line(str(exc))
    text = text.replace(f"{{{IDS_NAMESPACE}}}", "")
    return f"{text} (at {path})" if path else text


def _first_line(message: str) -> str:
    for line in message.splitlines():
        if line.strip():
            return line.strip().rstrip(".") + "."
    return "validation failed."


def _without_insignificant_whitespace(element: ET.Element) -> ET.Element:
    copy = ET.Element(element.tag, dict(sorted(element.attrib.items())))
    copy.text = element.text if element.text and element.text.strip() else None
    for child in element:
        copy.append(_without_insignificant_whitespace(child))
    return copy

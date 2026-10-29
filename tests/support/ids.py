"""IDS 1.0 documents built in memory for the validation tests.

The committed ``minimal.ids`` covers the two fixture specifications; the helpers here compose
further documents (prohibited, zero-applicability, malformed) from the same fragments so each
test states exactly how its IDS differs from the baseline. Nothing is written to the repository.
"""

from __future__ import annotations

from typing import cast

import httpx
from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX
from fixtures.make_minimal_ifc import IDS_PATH

IDS_NS = "http://standards.buildingsmart.org/IDS"
FIXTURE_IDS_BYTES = IDS_PATH.read_bytes()

ENTITY_WALL = "<entity><name><simpleValue>IFCWALL</simpleValue></name></entity>"
ENTITY_DOOR = "<entity><name><simpleValue>IFCDOOR</simpleValue></name></entity>"
PROPERTY_IS_EXTERNAL_TRUE = (
    '<property dataType="IFCBOOLEAN"><propertySet><simpleValue>Pset_WallCommon</simpleValue>'
    "</propertySet><baseName><simpleValue>IsExternal</simpleValue></baseName>"
    "<value><simpleValue>TRUE</simpleValue></value></property>"
)
PROPERTY_IS_EXTERNAL_FALSE = PROPERTY_IS_EXTERNAL_TRUE.replace(
    # ifctester 0.9.0 ``cast_to_value`` recognises only lower-case "true"/"false" for booleans;
    # any other string is cast with ``bool()`` and therefore reads as True.
    "<simpleValue>TRUE</simpleValue>",
    "<simpleValue>false</simpleValue>",
)
REQUIRE_FIRE_RATING = (
    '<property dataType="IFCLABEL" cardinality="required"><propertySet>'
    "<simpleValue>Pset_WallCommon</simpleValue></propertySet>"
    "<baseName><simpleValue>FireRating</simpleValue></baseName></property>"
)
REQUIRE_CLASSIFICATION = (
    '<classification cardinality="required"><system><simpleValue>Uniclass 2015</simpleValue>'
    "</system></classification>"
)


def specification(
    name: str,
    applicability: str,
    requirements: str = "",
    *,
    min_occurs: int | str = 1,
    max_occurs: int | str = "unbounded",
    ifc_version: str = "IFC4",
    description: str | None = None,
    identifier: str | None = None,
) -> str:
    attributes = f'name="{name}" ifcVersion="{ifc_version}"'
    if description is not None:
        attributes += f' description="{description}"'
    if identifier is not None:
        attributes += f' identifier="{identifier}"'
    return (
        f"<specification {attributes}>"
        f'<applicability minOccurs="{min_occurs}" maxOccurs="{max_occurs}">{applicability}'
        f"</applicability><requirements>{requirements}</requirements></specification>"
    )


def ids_document(*specifications: str, title: str = "Test IDS") -> bytes:
    body = "".join(specifications)
    return (
        f'<?xml version="1.0" encoding="UTF-8"?><ids xmlns="{IDS_NS}">'
        f"<info><title>{title}</title></info><specifications>{body}</specifications></ids>"
    ).encode()


FIRE_RATING_SPEC = specification(
    "External walls carry a fire rating",
    ENTITY_WALL + PROPERTY_IS_EXTERNAL_TRUE,
    REQUIRE_FIRE_RATING,
    description="Every external wall shall declare its fire rating.",
)
CLASSIFICATION_SPEC = specification(
    "Walls carry a classification reference",
    ENTITY_WALL,
    REQUIRE_CLASSIFICATION,
    description="Every wall shall carry a classification reference in the project system.",
)
# Required with nothing to apply to: the fixture has no doors (AC-07, not_applicable).
DOOR_SPEC = specification("Doors carry a fire rating", ENTITY_DOOR, REQUIRE_FIRE_RATING)
# Prohibited: no internal walls allowed; W-003 is internal (AC-07, prohibited_entity).
NO_INTERNAL_WALLS_SPEC = specification(
    "No internal walls",
    ENTITY_WALL + PROPERTY_IS_EXTERNAL_FALSE,
    min_occurs=0,
    max_occurs=0,
)
# Declares a schema the fixture is not written in (skipped, never silently passed).
IFC2X3_ONLY_SPEC = specification(
    "IFC2X3 walls carry a fire rating", ENTITY_WALL, REQUIRE_FIRE_RATING, ifc_version="IFC2X3"
)

MALFORMED_XML = b"<ids><specifications><specification"
# Well-formed XML that violates the IDS XSD (``info`` lacks the mandatory ``title``).
SCHEMA_INVALID_IDS = (
    f'<ids xmlns="{IDS_NS}"><info/><specifications>{FIRE_RATING_SPEC}</specifications></ids>'
).encode()
NOT_IDS_XML = b'<?xml version="1.0"?><note><to>Reader</to></note>'


def upload_ids(
    client: TestClient, session_id: str, data: bytes, filename: str = "requirements.ids"
) -> httpx.Response:
    response = client.post(
        f"{API_PREFIX}/sessions/{session_id}/documents",
        files={"file": (filename, data, "application/xml")},
    )
    return cast(httpx.Response, response)

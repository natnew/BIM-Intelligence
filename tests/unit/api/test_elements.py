"""Element lookup by GlobalId (AC-04, FR-ING-04)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX
from fixtures.make_minimal_ifc import GLOBAL_IDS
from fixtures.variants import duplicate_w002_as_w001, write_variant
from support.api import assert_problem, upload


def _element_url(session_id: str, global_id: str) -> str:
    return f"{API_PREFIX}/sessions/{session_id}/elements/{global_id}"


def test_known_global_id_returns_the_full_record(client: TestClient, loaded_session: str) -> None:
    response = client.get(_element_url(loaded_session, GLOBAL_IDS["W-001"]))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ref"] == {
        "global_id": GLOBAL_IDS["W-001"],
        "express_id": body["ref"]["express_id"],
        "ifc_type": "IfcWall",
        "name": "W-001",
        "storey": "L00",
    }
    assert body["container"]["global_id"] == GLOBAL_IDS["L00"]
    assert body["container"]["ifc_type"] == "IfcBuildingStorey"
    assert body["type_ref"] is None
    common = body["psets"]["Pset_WallCommon"]
    assert common["IsExternal"] == {"value": True, "inherited": False}
    assert common["FireRating"] == {"value": "REI 60", "inherited": False}
    assert body["classifications"] == [
        {
            "system": "Uniclass 2015",
            "identification": "Ss_25_10_30",
            "name": "Wall systems",
            "inherited": False,
        }
    ]


def test_storey_record_has_no_container(client: TestClient, loaded_session: str) -> None:
    body = client.get(_element_url(loaded_session, GLOBAL_IDS["L00"])).json()
    assert body["ref"]["ifc_type"] == "IfcBuildingStorey"
    assert body["container"] is None
    assert body["ref"]["storey"] is None


def test_unknown_global_id_is_404(client: TestClient, loaded_session: str) -> None:
    response = client.get(_element_url(loaded_session, "0000000000000000000000"))
    assert_problem(response, 404, "element-not-found")


def test_malformed_global_id_is_400(client: TestClient, loaded_session: str) -> None:
    response = client.get(_element_url(loaded_session, "W-001"))
    assert_problem(response, 400, "invalid-global-id")


def test_before_upload_is_404_model_not_found(client: TestClient, session_id: str) -> None:
    response = client.get(_element_url(session_id, GLOBAL_IDS["W-001"]))
    assert_problem(response, 404, "model-not-found")


def test_duplicate_global_id_is_409_and_names_both_express_ids(
    client: TestClient, session_id: str, tmp_path: Path
) -> None:
    path = write_variant(tmp_path, "dup.ifc", duplicate_w002_as_w001)
    assert upload(client, session_id, path.read_bytes()).status_code == 201
    response = client.get(_element_url(session_id, GLOBAL_IDS["W-001"]))
    body = assert_problem(response, 409, "ambiguous-global-id", detail_contains="2 elements")
    assert GLOBAL_IDS["W-001"] in str(body["detail"])
    # The other wall is still reachable.
    assert client.get(_element_url(session_id, GLOBAL_IDS["W-003"])).status_code == 200

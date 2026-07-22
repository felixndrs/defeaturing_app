from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from app.testing.bodies import base_box, with_hole


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def _make_project(client, write_step) -> str:
    original = write_step(with_hole(), "original.step")
    defeatured = write_step(base_box(), "defeatured.step")
    with original.open("rb") as fo, defeatured.open("rb") as fd:
        resp = client.post(
            "/projects",
            data={"name": "Hole part"},
            files={
                "original": ("original.step", fo, "application/step"),
                "defeatured": ("defeatured.step", fd, "application/step"),
            },
        )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_end_to_end_analysis_and_decision(client, write_step):
    project_id = _make_project(client, write_step)

    # Kick off analysis. With TestClient, BackgroundTasks run synchronously after
    # the response is returned, so the run is DONE by the time we poll.
    start = client.post("/analysis", json={"project_id": project_id})
    assert start.status_code == 202, start.text
    run_id = start.json()["id"]

    run = client.get(f"/analysis/{run_id}").json()
    assert run["status"] == "done", run.get("error")
    assert run["progress"] == 1.0

    holes = [f for f in run["features"] if f["type"] == "hole"]
    assert len(holes) == 1
    hole = holes[0]
    assert hole["parameters"]["diameter"] == pytest.approx(10.0, abs=0.2)

    # The null provider attaches an assessment to every feature.
    assert hole["assessment"] is not None
    assert run["llm_summary"]

    # Record a user decision and confirm it persists.
    patched = client.patch(
        f"/analysis/{run_id}/features/{hole['id']}",
        json={"user_decision": "reject", "user_comment": "keep the hole"},
    )
    assert patched.status_code == 200
    assert patched.json()["user_decision"] == "reject"

    reloaded = client.get(f"/analysis/{run_id}").json()
    reloaded_hole = next(f for f in reloaded["features"] if f["id"] == hole["id"])
    assert reloaded_hole["user_decision"] == "reject"
    assert reloaded_hole["user_comment"] == "keep the hole"


def test_geometry_endpoint_serves_glb(client, write_step):
    project_id = _make_project(client, write_step)
    project = client.get(f"/projects/{project_id}").json()
    model_id = project["original"]["id"]

    resp = client.get(f"/geometry/{model_id}.glb")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "model/gltf-binary"
    assert resp.content[:4] == b"glTF"  # GLB magic number


def test_analysis_for_unknown_project_is_404(client):
    assert client.post("/analysis", json={"project_id": "nope"}).status_code == 404

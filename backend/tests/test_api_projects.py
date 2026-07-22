from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from synthetic import make_box, make_box_with_fillet

DX, DY, DZ = 40.0, 30.0, 20.0


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert ".step" in body["supported_formats"]


def test_create_and_fetch_project(client, write_step):
    original = write_step(make_box_with_fillet(3.0, DX, DY, DZ), "original.step")
    defeatured = write_step(make_box(DX, DY, DZ), "defeatured.step")

    with original.open("rb") as fo, defeatured.open("rb") as fd:
        response = client.post(
            "/projects",
            data={"name": "Bracket v1"},
            files={
                "original": ("original.step", fo, "application/step"),
                "defeatured": ("defeatured.step", fd, "application/step"),
            },
        )
    assert response.status_code == 201, response.text
    created = response.json()

    assert created["name"] == "Bracket v1"
    # The defeatured box has fewer faces and more volume than the filleted one.
    assert created["original"]["face_count"] == 26
    assert created["defeatured"]["face_count"] == 6
    assert created["defeatured"]["volume"] > created["original"]["volume"]

    fetched = client.get(f"/projects/{created['id']}").json()
    assert fetched == created


def test_unknown_project_is_404(client):
    assert client.get("/projects/does-not-exist").status_code == 404


def test_unsupported_upload_is_rejected(client, tmp_path):
    bogus = tmp_path / "model.xyz"
    bogus.write_text("nope")
    with bogus.open("rb") as f1, bogus.open("rb") as f2:
        response = client.post(
            "/projects",
            data={"name": "bad"},
            files={
                "original": ("model.xyz", f1, "application/octet-stream"),
                "defeatured": ("model.xyz", f2, "application/octet-stream"),
            },
        )
    assert response.status_code == 415

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from app.testing.bodies import base_box, with_hole


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def _analyzed_run_id(client, write_step) -> str:
    original = write_step(with_hole(), "original.step")
    defeatured = write_step(base_box(), "defeatured.step")
    with original.open("rb") as fo, defeatured.open("rb") as fd:
        resp = client.post(
            "/projects",
            data={"name": "Report Test"},
            files={
                "original": ("original.step", fo, "application/step"),
                "defeatured": ("defeatured.step", fd, "application/step"),
            },
        )
    project_id = resp.json()["id"]
    start = client.post("/analysis", json={"project_id": project_id})
    return start.json()["id"]


def test_pdf_report_generated(client, write_step):
    run_id = _analyzed_run_id(client, write_step)
    resp = client.get(f"/report/{run_id}/pdf")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert len(resp.content) > 1000


def test_html_bundle_generated(client, write_step):
    run_id = _analyzed_run_id(client, write_step)
    resp = client.get(f"/report/{run_id}/bundle")
    assert resp.status_code == 200, resp.text
    assert resp.content[:2] == b"PK"  # ZIP magic number

    import io
    import zipfile

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert "index.html" in names
    assert "geometry/original.glb" in names
    assert "geometry/defeatured.glb" in names
    html = zf.read("index.html").decode("utf-8")
    assert "hole" in html


def test_report_for_unknown_run_is_404(client):
    assert client.get("/report/does-not-exist/pdf").status_code == 404

from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from app.testing.bodies import base_box, with_hole


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def _analyzed_run_id(client, write_step, name: str = "Report Test") -> str:
    original = write_step(with_hole(), "original.step")
    defeatured = write_step(base_box(), "defeatured.step")
    with original.open("rb") as fo, defeatured.open("rb") as fd:
        resp = client.post(
            "/projects",
            data={"name": name},
            files={
                "original": ("original.step", fo, "application/step"),
                "defeatured": ("defeatured.step", fd, "application/step"),
            },
        )
    project_id = resp.json()["id"]
    start = client.post("/analysis", json={"project_id": project_id})
    return start.json()["id"]


def _pdf_pages(content: bytes) -> list[str]:
    from pypdf import PdfReader

    return [page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages]


def test_pdf_report_generated(client, write_step):
    run_id = _analyzed_run_id(client, write_step)
    resp = client.get(f"/report/{run_id}/pdf")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert len(resp.content) > 1000


def test_pdf_filename_follows_naming_scheme(client, write_step):
    run_id = _analyzed_run_id(client, write_step, name="Gehäuse Träger")
    resp = client.get(f"/report/{run_id}/pdf")
    disposition = resp.headers["content-disposition"]
    # defeaturing_review_<slug>_<YYYY-MM-DD>.pdf, umlauts transliterated.
    assert "defeaturing_review_gehaeuse_traeger_" in disposition
    assert disposition.rstrip('"').endswith(".pdf")


def test_pdf_explains_risk_and_uses_german(client, write_step):
    run_id = _analyzed_run_id(client, write_step)
    text = "\n".join(_pdf_pages(client.get(f"/report/{run_id}/pdf").content))
    assert "Lesehilfe" in text
    assert "Simulation" in text  # the reading guide names what the risk is about
    assert "Bohrungen" in text  # feature types are translated, not raw enum values
    assert "Inhaltsverzeichnis" in text


def test_pdf_in_english(client, write_step):
    run_id = _analyzed_run_id(client, write_step)
    resp = client.get(f"/report/{run_id}/pdf", params={"lang": "en"})
    assert resp.status_code == 200
    text = "\n".join(_pdf_pages(resp.content))
    assert "How to read this report" in text
    assert "Holes" in text
    assert "Lesehilfe" not in text
    assert "_en.pdf" in resp.headers["content-disposition"]


def test_rejected_features_only_in_final_chapter(client, write_step):
    run_id = _analyzed_run_id(client, write_step)
    run = client.get(f"/analysis/{run_id}").json()
    feature = run["features"][0]
    client.patch(
        f"/analysis/{run_id}/features/{feature['id']}",
        json={"user_decision": "reject"},
    )

    pages = _pdf_pages(client.get(f"/report/{run_id}/pdf").content)
    chapter_page = next(
        i for i, page in enumerate(pages) if "Verworfene" in page and "Änderungen" in page
    )
    marker = feature["id"][3:9]
    # The discarded change is documented, but only from the final chapter on --
    # the body of the report describes the approved state.
    assert any(marker in page for page in pages[chapter_page:])
    assert not any(marker in page for page in pages[:chapter_page])


def test_html_bundle_generated(client, write_step):
    run_id = _analyzed_run_id(client, write_step)
    resp = client.get(f"/report/{run_id}/bundle")
    assert resp.status_code == 200, resp.text
    assert resp.content[:2] == b"PK"  # ZIP magic number
    assert "defeaturing_review_report_test_" in resp.headers["content-disposition"]

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert "index.html" in names
    assert "geometry/original.glb" in names
    assert "geometry/defeatured.glb" in names
    html = zf.read("index.html").decode("utf-8")
    assert "hole" in html


def test_html_bundle_carries_both_languages(client, write_step):
    run_id = _analyzed_run_id(client, write_step)
    zf = zipfile.ZipFile(io.BytesIO(client.get(f"/report/{run_id}/bundle").content))
    html = zf.read("index.html").decode("utf-8")

    payload = json.loads(html.split("const DATA = ", 1)[1].split(";\nlet LANG", 1)[0])
    assert payload["i18n"]["de"]["report.guide"] == "Lesehilfe"
    assert payload["i18n"]["en"]["report.guide"] == "How to read this report"
    assert payload["vocab"]["featureType"]["hole"]["en"] == ["Hole", "Holes"]
    # The offline page must be able to switch language without a model call.
    assert payload["summary"]["de"] and payload["summary"]["en"]
    assert all(f["assessment"]["rationale_en"] for f in payload["features"])


def test_report_for_unknown_run_is_404(client):
    assert client.get("/report/does-not-exist/pdf").status_code == 404

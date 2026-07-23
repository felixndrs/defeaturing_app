"""Interactive offline review bundle.

A single self-contained HTML file plus the two GLBs, zipped together. It embeds
the run's JSON (features, evidence, assessments) inline, so it can be reopened
without a server or a fresh analysis -- the Lastenheft requirement.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from ..domain.models import AnalysisRun, GeometryModel, Project
from ..storage import files

_TEMPLATE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<title>Defeaturing Review — {project_name}</title>
<style>
  body {{ margin:0; font-family: system-ui, sans-serif; background:#0b0f19; color:#e5e7eb; }}
  header {{ padding: 10px 16px; border-bottom: 1px solid #1f2937; }}
  #layout {{ display:flex; height: calc(100vh - 48px); }}
  #list {{ width: 280px; overflow-y:auto; border-right: 1px solid #1f2937; }}
  #list button {{ display:block; width:100%; text-align:left; padding:8px 12px; background:none;
                  border:none; color:#e5e7eb; cursor:pointer; font-size: 13px; }}
  #list button:hover, #list button.active {{ background:#1f2937; }}
  #detail {{ flex:1; padding:16px; overflow-y:auto; }}
  .risk-low {{ color:#34d399; }} .risk-medium {{ color:#fbbf24; }} .risk-high {{ color:#f87171; }}
  table {{ border-collapse: collapse; }}
  td, th {{ border: 1px solid #1f2937; padding: 4px 8px; font-size: 12px; }}
  h2 {{ margin-top: 0; }}
</style>
</head>
<body>
<header><b>{project_name}</b> — Defeaturing Review (offline, ohne Neuanalyse)</header>
<div id="layout">
  <div id="list"></div>
  <div id="detail">Feature auswählen…</div>
</div>
<script>
const DATA = {data_json};
const list = document.getElementById('list');
const detail = document.getElementById('detail');

DATA.features.forEach((f, i) => {{
  const b = document.createElement('button');
  b.textContent = `${{f.type}} — ${{f.id.slice(0,10)}}`;
  b.onclick = () => select(i, b);
  list.appendChild(b);
}});

function select(i, btn) {{
  document.querySelectorAll('#list button').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  const f = DATA.features[i];
  const a = f.assessment;
  detail.innerHTML = `
    <h2>${{f.type}}</h2>
    <p>Detektor: ${{f.detector}} · Konfidenz ${{Math.round(f.confidence*100)}}%</p>
    <table>${{Object.entries(f.parameters).map(([k,v]) => `<tr><td>${{k}}</td><td>${{v}}</td></tr>`).join('')}}</table>
    ${{a ? `<p class="risk-${{a.risk}}">Risiko: ${{a.risk}} (${{Math.round(a.confidence*100)}}%)</p><p>${{a.rationale}}</p>` : ''}}
    <p><b>Entscheidung:</b> ${{f.user_decision}} ${{f.user_comment ? '— ' + f.user_comment : ''}}</p>
  `;
}}
</script>
</body>
</html>
"""


def build_bundle(run: AnalysisRun, project: Project, original: GeometryModel, defeatured: GeometryModel) -> Path:
    out_path = files.bundle_path(run.id)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "project": {"id": project.id, "name": project.name},
        "run_id": run.id,
        "llm_summary": run.llm_summary,
        "statistics": json.loads(run.statistics.model_dump_json()),
        "features": json.loads(run.model_dump_json())["features"],
    }
    html = _TEMPLATE.format(project_name=project.name, data_json=json.dumps(data))

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html)
        for role, model in (("original", original), ("defeatured", defeatured)):
            glb = files.geometry_path(model.id)
            if glb.exists():
                zf.write(glb, f"geometry/{role}.glb")

    return out_path

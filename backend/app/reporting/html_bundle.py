"""Interactive offline review bundle.

A single self-contained HTML file plus the two GLBs, zipped together. It embeds
the run's JSON (features, evidence, assessments) inline, so it can be reopened
without a server or a fresh analysis -- the Lastenheft requirement.

Both UI languages travel with the bundle: the dictionary and the bilingual LLM
prose are baked into the JSON, so the language switch works with no network and
no model call.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from .. import i18n
from ..domain.models import AnalysisRun, GeometryModel, Project
from ..storage import files

# Keys the bundle's own UI needs. Kept explicit so the embedded dictionary stays
# small and it is obvious what the offline page can say.
_BUNDLE_KEYS = (
    "report.title", "report.project", "report.created", "report.run_id",
    "report.summary", "report.summary_missing", "report.statistics", "report.guide",
    "report.parameters", "report.evidence", "report.decision", "report.risk",
    "report.confidence", "report.detector", "report.rejected_chapter",
    "report.rejected_intro", "report.no_features",
    "stats.changes", "stats.reviewed", "stats.unknown", "stats.original_faces",
    "stats.defeatured_faces", "stats.paired_faces", "stats.volume_original",
    "stats.volume_defeatured", "stats.volume_delta",
    "guide.intro", "guide.risk_title", "guide.risk_intro",
    "guide.risk_low", "guide.risk_medium", "guide.risk_high",
    "guide.confidence_title", "guide.confidence_body",
    "guide.images_title", "guide.images_body",
    "guide.decision_title", "guide.decision_body",
    "guide.evidence_title", "guide.evidence_body",
    "bundle.subtitle", "bundle.select_hint", "bundle.overview", "bundle.changes",
)

_TEMPLATE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__</title>
<style>
  :root {
    --bg:#0b0f19; --panel:#111827; --edge:#1f2937; --ink:#e5e7eb;
    --muted:#9ca3af; --faint:#6b7280; --accent:#f59e0b;
    --low:#34d399; --medium:#fbbf24; --high:#f87171;
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font-size:14px;
         font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
  header { display:flex; align-items:center; gap:16px; padding:10px 16px;
           border-bottom:1px solid var(--edge); background:var(--panel); }
  header .title { font-weight:600; }
  header .sub { color:var(--faint); font-size:12px; }
  .spacer { margin-left:auto; }
  .langswitch { display:inline-flex; border:1px solid var(--edge); border-radius:7px;
                overflow:hidden; background:rgba(0,0,0,.3); }
  .langswitch button { padding:4px 10px; font-size:12px; font-weight:600; border:0;
                       background:none; color:var(--muted); cursor:pointer; }
  .langswitch button.active { background:var(--edge); color:var(--ink); }
  #layout { display:flex; height: calc(100vh - 49px); }
  #list { width:280px; flex:none; overflow-y:auto; border-right:1px solid var(--edge);
          background:var(--panel); }
  #list .group { position:sticky; top:0; background:var(--panel); padding:8px 12px 4px;
                 font-size:11px; font-weight:600; letter-spacing:.05em;
                 text-transform:uppercase; color:var(--faint); }
  #list button.item { display:flex; align-items:center; gap:8px; width:100%;
                      text-align:left; padding:7px 12px; background:none; border:0;
                      color:var(--ink); cursor:pointer; font-size:13px; }
  #list button.item:hover { background:var(--edge); }
  #list button.item.active { background:var(--edge); box-shadow: inset 0 0 0 1px rgba(245,158,11,.6); }
  .name { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .mark-accept { color:var(--low); } .mark-reject { color:var(--high); }
  .mark-undecided { color:var(--faint); }
  .badge { font-size:10px; padding:1px 6px; border-radius:5px; }
  .badge.low { background:rgba(6,78,59,.6); color:var(--low); }
  .badge.medium { background:rgba(120,53,15,.6); color:var(--medium); }
  .badge.high { background:rgba(127,29,29,.6); color:var(--high); }
  #detail { flex:1; padding:24px 28px; overflow-y:auto; max-width:900px; }
  h1 { font-size:20px; margin:0 0 4px; }
  h2 { font-size:16px; margin:0 0 4px; }
  .meta { color:var(--faint); font-size:12px; margin:0 0 18px; }
  .section { margin-top:22px; }
  .section > .label { font-size:11px; font-weight:600; letter-spacing:.05em;
                      text-transform:uppercase; color:var(--faint); margin-bottom:6px; }
  table { border-collapse:collapse; width:100%; max-width:520px; }
  td { border-bottom:1px solid var(--edge); padding:5px 8px; font-size:13px; }
  td:first-child { color:var(--muted); width:45%; }
  .risk-low { color:var(--low); } .risk-medium { color:var(--medium); } .risk-high { color:var(--high); }
  .card { background:rgba(0,0,0,.3); border:1px solid var(--edge); border-radius:8px;
          padding:10px 12px; }
  .card + .card { margin-top:8px; }
  .card .kind { font-size:12px; font-weight:600; }
  .card .desc { font-size:12px; color:var(--muted); }
  .card .vals { font-family:ui-monospace, SFMono-Regular, Menlo, monospace;
                font-size:11px; color:var(--faint); margin-top:4px; }
  details { margin-top:18px; border:1px solid var(--edge); border-radius:8px;
            background:var(--panel); }
  details > summary { cursor:pointer; padding:10px 12px; font-weight:600; font-size:13px; }
  details .body { padding:0 12px 12px; }
  details h3 { font-size:13px; margin:14px 0 4px; }
  details p { margin:0; color:var(--muted); font-size:13px; line-height:1.5; }
  .note { color:var(--muted); font-size:13px; line-height:1.55; }
  .rejected-note { border-left:3px solid var(--high); padding-left:10px; }
</style>
</head>
<body>
<header>
  <div>
    <div class="title" id="hdr-project"></div>
    <div class="sub" id="hdr-sub"></div>
  </div>
  <div class="spacer"></div>
  <div class="langswitch" id="langswitch">
    <button data-lang="de">DE</button><button data-lang="en">EN</button>
  </div>
</header>
<div id="layout">
  <div id="list"></div>
  <div id="detail"></div>
</div>
<script>
const DATA = __DATA__;
let LANG = 'de';
let selected = null;  // feature id, or null for the overview

const T = (key) => (DATA.i18n[LANG] && DATA.i18n[LANG][key]) || key;
const vocab = (map, key, fallback) => (DATA.vocab[map][key] || {})[LANG] || fallback || key;
const typeName = (key, plural) => {
  const entry = DATA.vocab.featureType[key];
  if (!entry) return key;
  return (entry[LANG] || entry.de)[plural ? 1 : 0];
};
// [label, description] per evidence kind; an unknown kind keeps the detector's
// own English sentence rather than losing it.
const evidenceText = (kind, fallback) => {
  const entry = DATA.vocab.evidence[kind];
  if (!entry) return [kind.replace(/_/g, ' '), fallback];
  return entry[LANG] || entry.de;
};
const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const pct = (v) => Math.round(v * 100) + '%';
// Same formatting rules as the app: mm on length parameters (the importer
// normalises the CAD unit), spelled-out booleans, no fake decimal places.
const LENGTH_KEYS = ['radius', 'diameter', 'depth', 'distance', 'width', 'length',
                     'thickness', 'height'];
const fmtValue = (key, v) => {
  if (typeof v === 'boolean') return LANG === 'de' ? (v ? 'ja' : 'nein') : (v ? 'yes' : 'no');
  if (typeof v === 'number') {
    const text = Number.isInteger(v) ? String(v) : String(parseFloat(v.toFixed(3)));
    return LENGTH_KEYS.includes(key) ? text + ' mm' : text;
  }
  if (Array.isArray(v)) return v.map((x) => fmtValue(key, x)).join(', ');
  return String(v);
};
// The LLM writes its prose in both languages; fall back to German when a run
// predates the bilingual assessment.
const prose = (de, en) => (LANG === 'en' ? (en || de) : de);

const kept = DATA.features.filter((f) => f.user_decision !== 'reject');
const rejected = DATA.features.filter((f) => f.user_decision === 'reject');

function renderHeader() {
  document.getElementById('hdr-project').textContent = DATA.project.name;
  document.getElementById('hdr-sub').textContent = T('bundle.subtitle');
  document.title = T('report.title') + ' \\u2014 ' + DATA.project.name;
  document.documentElement.lang = LANG;
  document.querySelectorAll('#langswitch button').forEach((b) =>
    b.classList.toggle('active', b.dataset.lang === LANG));
}

function renderList() {
  const list = document.getElementById('list');
  list.innerHTML = '';

  const overview = document.createElement('button');
  overview.className = 'item' + (selected === null ? ' active' : '');
  overview.innerHTML = `<span class="name">${esc(T('bundle.overview'))}</span>`;
  overview.onclick = () => { selected = null; render(); };
  list.appendChild(overview);

  const byType = {};
  kept.forEach((f) => (byType[f.type] = byType[f.type] || []).push(f));
  Object.keys(byType)
    .sort((a, b) => typeName(a, true).localeCompare(typeName(b, true)))
    .forEach((type) => addGroup(list, typeName(type, true), byType[type]));

  if (rejected.length) addGroup(list, T('report.rejected_chapter'), rejected);
}

function addGroup(list, title, items) {
  const head = document.createElement('div');
  head.className = 'group';
  head.textContent = `${title} (${items.length})`;
  list.appendChild(head);

  items.forEach((f) => {
    const b = document.createElement('button');
    b.className = 'item' + (f.id === selected ? ' active' : '');
    const mark = { accept: '\\u2713', reject: '\\u2715', undecided: '\\u2022' }[f.user_decision];
    const risk = f.assessment
      ? `<span class="badge ${f.assessment.risk}">${esc(vocab('risk', f.assessment.risk))}</span>`
      : '';
    b.innerHTML =
      `<span class="mark-${f.user_decision}">${mark}</span>` +
      `<span class="name">${esc(typeName(f.type))} ${esc(f.id.slice(3, 9))}</span>${risk}`;
    b.onclick = () => { selected = f.id; render(); };
    list.appendChild(b);
  });
}

function renderDetail() {
  const detail = document.getElementById('detail');
  if (selected === null) { detail.innerHTML = overviewHtml(); return; }
  const f = DATA.features.find((x) => x.id === selected);
  if (!f) { detail.innerHTML = `<p class="note">${esc(T('bundle.select_hint'))}</p>`; return; }
  const a = f.assessment;

  const params = Object.entries(f.parameters)
    .map(([k, v]) =>
      `<tr><td>${esc(vocab('parameter', k, k))}</td><td>${esc(fmtValue(k, v))}</td></tr>`)
    .join('');
  const evidence = f.evidence.map((e) => {
    const [label, description] = evidenceText(e.kind, e.description);
    const values = Object.entries(e.values)
      .map(([k, v]) => vocab('parameter', k, k.replace(/_/g, ' ')) + '=' + fmtValue(k, v))
      .join('  ');
    return `
    <div class="card">
      <div class="kind">${esc(label)}</div>
      <div class="desc">${esc(description)}</div>
      <div class="vals">${esc(values)}</div>
    </div>`;
  }).join('');

  detail.innerHTML = `
    ${f.user_decision === 'reject'
      ? `<p class="note rejected-note">${esc(T('report.rejected_intro'))}</p>` : ''}
    <h1>${esc(typeName(f.type))}</h1>
    <p class="meta">ID ${esc(f.id.slice(3, 9))} · ${esc(T('report.detector'))} ${esc(f.detector)}
       · ${esc(T('report.confidence'))} ${pct(f.confidence)}</p>
    ${params ? `<div class="section"><div class="label">${esc(T('report.parameters'))}</div>
       <table>${params}</table></div>` : ''}
    ${a ? `<div class="section"><div class="label">${esc(T('report.risk'))}</div>
       <p class="risk-${a.risk}" style="margin:0 0 6px"><b>${esc(vocab('risk', a.risk))}</b></p>
       <p class="note">${esc(prose(a.rationale, a.rationale_en))}</p></div>` : ''}
    ${evidence ? `<div class="section"><div class="label">${esc(T('report.evidence'))}</div>
       ${evidence}</div>` : ''}
    <div class="section"><div class="label">${esc(T('report.decision'))}</div>
      <p class="note"><b>${esc(vocab('decision', f.user_decision))}</b>${
        f.user_comment ? ' — ' + esc(f.user_comment) : ''}</p></div>
  `;
}

function overviewHtml() {
  const s = DATA.statistics;
  const decided = DATA.features.filter((f) => f.user_decision !== 'undecided').length;
  const deltaRel = s.volume_original ? (s.volume_defeatured - s.volume_original) / s.volume_original : 0;
  const rows = [
    [T('stats.changes'), DATA.features.length],
    [T('stats.reviewed'), decided + ' / ' + DATA.features.length],
    [T('stats.unknown'), s.unknown_count],
    [T('stats.original_faces'), s.original_face_count],
    [T('stats.defeatured_faces'), s.defeatured_face_count],
    [T('stats.paired_faces'), s.paired_face_count],
    [T('stats.volume_original'), s.volume_original.toFixed(1) + ' mm³'],
    [T('stats.volume_defeatured'), s.volume_defeatured.toFixed(1) + ' mm³'],
    [T('stats.volume_delta'), (deltaRel >= 0 ? '+' : '') + (deltaRel * 100).toFixed(2) + ' %'],
  ].map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('');

  const guideBlocks = [
    ['guide.risk_title', 'guide.risk_intro'],
    ['guide.confidence_title', 'guide.confidence_body'],
    ['guide.decision_title', 'guide.decision_body'],
    ['guide.evidence_title', 'guide.evidence_body'],
  ].map(([h, p]) => `<h3>${esc(T(h))}</h3><p>${esc(T(p))}</p>`).join('');
  const riskLevels = ['low', 'medium', 'high']
    .map((r) => `<p><span class="risk-${r}"><b>${esc(vocab('risk', r))}</b></span> — ${
      esc(T('guide.risk_' + r))}</p>`).join('');

  return `
    <h1>${esc(T('report.title'))}</h1>
    <p class="meta">${esc(T('report.project'))}: ${esc(DATA.project.name)} ·
       ${esc(T('report.created'))}: ${esc(DATA.created_at.slice(0, 10))} ·
       ${esc(T('report.run_id'))}: ${esc(DATA.run_id)}</p>
    <div class="section"><div class="label">${esc(T('report.summary'))}</div>
      <p class="note">${esc(prose(DATA.summary.de, DATA.summary.en) || T('report.summary_missing'))}</p></div>
    <div class="section"><div class="label">${esc(T('report.statistics'))}</div>
      <table>${rows}</table></div>
    <details>
      <summary>${esc(T('report.guide'))}</summary>
      <div class="body">
        <p>${esc(T('guide.intro'))}</p>
        ${guideBlocks}
        <div style="margin-top:10px">${riskLevels}</div>
      </div>
    </details>`;
}

function render() { renderHeader(); renderList(); renderDetail(); }

document.querySelectorAll('#langswitch button').forEach((b) => {
  b.onclick = () => { LANG = b.dataset.lang; render(); };
});
render();
</script>
</body>
</html>
"""


def bundle_filename(project: Project, run: AnalysisRun) -> str:
    """Mirrors the PDF naming so both downloads sort together in a folder."""
    return f"defeaturing_review_{i18n.slugify(project.name)}_{run.created_at:%Y-%m-%d}.zip"


def _vocabulary() -> dict:
    """Enum translations for both languages, embedded so the offline page can
    relabel itself without a server."""
    return {
        "featureType": i18n.FEATURE_TYPE,
        "risk": i18n.RISK,
        "decision": i18n.DECISION,
        "parameter": i18n.PARAMETER,
        "evidence": i18n.EVIDENCE,
    }


def build_bundle(run: AnalysisRun, project: Project, original: GeometryModel, defeatured: GeometryModel) -> Path:
    out_path = files.bundle_path(run.id)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "project": {"id": project.id, "name": project.name},
        "run_id": run.id,
        "created_at": run.created_at.isoformat(),
        "summary": {"de": run.llm_summary, "en": run.llm_summary_en},
        "statistics": json.loads(run.statistics.model_dump_json()),
        "features": json.loads(run.model_dump_json())["features"],
        "i18n": {lang: {key: i18n.t(key, lang) for key in _BUNDLE_KEYS} for lang in i18n.LANGUAGES},
        "vocab": _vocabulary(),
    }
    # `</script>` inside the payload would end the inline script early.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (
        _TEMPLATE
        .replace("__TITLE__", f"{i18n.t('report.title')} — {project.name}")
        .replace("__DATA__", payload)
    )

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html)
        for role, model in (("original", original), ("defeatured", defeatured)):
            glb = files.geometry_path(model.id)
            if glb.exists():
                zf.write(glb, f"geometry/{role}.glb")

    return out_path

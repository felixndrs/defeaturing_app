"""Engineering PDF report.

Structure follows the Lastenheft: project info, AI summary, statistics, table
of contents, grouping by feature type, one detail page per feature with images,
parameters, evidence, confidence, user decision and comment.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from ..domain.models import AnalysisRun, FeatureChange, Project
from ..storage import files

_STYLES = getSampleStyleSheet()
_H1 = ParagraphStyle("H1", parent=_STYLES["Heading1"], spaceAfter=6 * mm)
_H2 = ParagraphStyle("H2", parent=_STYLES["Heading2"], spaceBefore=4 * mm, spaceAfter=2 * mm)
_BODY = _STYLES["BodyText"]
_SMALL = ParagraphStyle("Small", parent=_STYLES["BodyText"], fontSize=8, textColor=colors.grey)
_TOC_LEVEL0 = ParagraphStyle("TOCLevel0", parent=_BODY, fontSize=10, leftIndent=6 * mm)

_RISK_COLOR = {"low": colors.HexColor("#059669"), "medium": colors.HexColor("#d97706"),
               "high": colors.HexColor("#dc2626")}
_RISK_DE = {"low": "niedrig", "medium": "mittel", "high": "hoch"}
_DECISION_DE = {"undecided": "Unentschieden", "accept": "Beibehalten", "reject": "Verworfen"}
# Parameter keys that carry a length unit -- the STEP importer normalises the
# CAD unit to mm (see step_importer.py), so this is a safe assumption.
_LENGTH_KEYS = {"radius", "diameter", "depth", "distance", "width", "length", "thickness", "height"}


def _footer(canvas: pdfcanvas.Canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Seite {doc.page}")
    canvas.restoreState()


class _ReportDocTemplate(SimpleDocTemplate):
    """Registers each feature-type heading as a table-of-contents entry."""

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "H1":
            self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))


def build_report(run: AnalysisRun, project: Project, render_images: bool = True) -> Path:
    out_path = files.report_path(run.id)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = _ReportDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
    )

    story: list = []
    story += _cover(project, run)
    story += _summary_and_stats(run)
    story += _toc()

    grouped: dict[str, list[FeatureChange]] = {}
    for f in run.features:
        grouped.setdefault(f.type.value, []).append(f)

    for ftype in sorted(grouped):
        story.append(PageBreak())
        story.append(Paragraph(f"Feature-Typ: {ftype}", _H1))
        for feature in grouped[ftype]:
            story += _feature_detail(run, feature, render_images)

    doc.multiBuild(story, onFirstPage=_footer, onLaterPages=_footer)
    return out_path


def _cover(project: Project, run: AnalysisRun) -> list:
    return [
        Paragraph("AI Defeaturing Review", _H1),
        Paragraph(f"Projekt: {project.name}", _BODY),
        Paragraph(f"Analyse-ID: {run.id}", _SMALL),
        Paragraph(f"Erstellt: {run.created_at:%Y-%m-%d %H:%M} UTC", _SMALL),
        Spacer(1, 6 * mm),
        Paragraph("KI-Zusammenfassung", _H2),
        Paragraph(run.llm_summary or "(keine Bewertung verfügbar)", _BODY),
    ]


def _summary_and_stats(run: AnalysisRun) -> list:
    s = run.statistics
    rows = [
        ["Original Flächen", str(s.original_face_count)],
        ["Defeatured Flächen", str(s.defeatured_face_count)],
        ["Übereinstimmende Flächen", str(s.paired_face_count)],
        ["Volumen Original", f"{s.volume_original:.1f} mm³"],
        ["Volumen Defeatured", f"{s.volume_defeatured:.1f} mm³"],
        ["Volumenänderung", f"{s.volume_delta_rel*100:+.2f} %"],
        ["Unklassifizierte Änderungen", str(s.unknown_count)],
    ]

    table = Table(rows, colWidths=[80 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    return [Paragraph("Statistik", _H2), table]


def _toc() -> list:
    toc = TableOfContents()
    toc.levelStyles = [_TOC_LEVEL0]
    return [Paragraph("Inhaltsverzeichnis", _H2), toc]


def _feature_detail(run: AnalysisRun, feature: FeatureChange, render_images: bool) -> list:
    story: list = [Paragraph(f"{feature.type.value} — {feature.id[3:9]}", _H2)]
    story.append(Paragraph(f"Detektor: {feature.detector} · Konfidenz: {feature.confidence:.0%}", _SMALL))

    if render_images:
        paths = files.artifact_dir(run.id) / "screenshots"
        images, captions = [], []
        for view, caption in (("original", "Original"), ("defeatured", "Defeatured"), ("overlay", "Overlay")):
            p = paths / f"{feature.id}_{view}.png"
            if p.exists():
                images.append(Image(str(p), width=55 * mm, height=41 * mm))
                captions.append(Paragraph(caption, _SMALL))
        if images:
            img_table = Table([images, captions], colWidths=[58 * mm] * len(images))
            img_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
            story.append(img_table)

    if feature.parameters:
        rows = [[str(k), _fmt_param(k, v)] for k, v in feature.parameters.items()]
        t = Table(rows, colWidths=[40 * mm, 60 * mm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ]))
        story.append(Paragraph("Parameter", _SMALL))
        story.append(t)

    if feature.assessment:
        a = feature.assessment
        risk_style = ParagraphStyle("Risk", parent=_BODY, textColor=_RISK_COLOR.get(a.risk.value, colors.black))
        story.append(Paragraph(f"Risiko: {_RISK_DE.get(a.risk.value, a.risk.value)}", risk_style))
        story.append(Paragraph(a.rationale, _BODY))

    for ev in feature.evidence:
        story.append(Paragraph(f"Evidenz: {ev.kind} — {ev.description}", _SMALL))

    decision = _DECISION_DE.get(feature.user_decision.value, feature.user_decision.value)
    story.append(Paragraph(
        f"Benutzerentscheidung: <b>{decision}</b>"
        + (f" — {feature.user_comment}" if feature.user_comment else ""),
        _BODY,
    ))
    story.append(Spacer(1, 4 * mm))
    return story


def _fmt_param(key: str, v) -> str:
    if isinstance(v, float):
        s = f"{v:.3g}"
    else:
        s = str(v)
    if key in _LENGTH_KEYS and isinstance(v, (int, float)):
        s += " mm"
    return s

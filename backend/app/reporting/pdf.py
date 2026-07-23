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

from ..domain.models import AnalysisRun, FeatureChange, Project
from ..storage import files

_STYLES = getSampleStyleSheet()
_H1 = ParagraphStyle("H1", parent=_STYLES["Heading1"], spaceAfter=6 * mm)
_H2 = ParagraphStyle("H2", parent=_STYLES["Heading2"], spaceBefore=4 * mm, spaceAfter=2 * mm)
_BODY = _STYLES["BodyText"]
_SMALL = ParagraphStyle("Small", parent=_STYLES["BodyText"], fontSize=8, textColor=colors.grey)

_RISK_COLOR = {"low": colors.HexColor("#059669"), "medium": colors.HexColor("#d97706"),
               "high": colors.HexColor("#dc2626")}


def _footer(canvas: pdfcanvas.Canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def build_report(run: AnalysisRun, project: Project, render_images: bool = True) -> Path:
    out_path = files.report_path(run.id)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
    )

    story: list = []
    story += _cover(project, run)
    story += _summary_and_stats(run)
    story += _toc(run)

    grouped: dict[str, list[FeatureChange]] = {}
    for f in run.features:
        grouped.setdefault(f.type.value, []).append(f)

    for ftype in sorted(grouped):
        story.append(PageBreak())
        story.append(Paragraph(f"Feature-Typ: {ftype}", _H1))
        for feature in grouped[ftype]:
            story += _feature_detail(run, feature, render_images)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
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
        ["Volumen Original", f"{s.volume_original:.1f}"],
        ["Volumen Defeatured", f"{s.volume_defeatured:.1f}"],
        ["Volumenänderung", f"{s.volume_delta_rel*100:+.2f} %"],
        ["Unklassifizierte Änderungen", str(s.unknown_count)],
    ]
    for ftype, count in sorted(s.feature_counts.items()):
        rows.append([f"Feature: {ftype}", str(count)])

    table = Table(rows, colWidths=[80 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    return [Paragraph("Statistik", _H2), table]


def _toc(run: AnalysisRun) -> list:
    grouped: dict[str, int] = {}
    for f in run.features:
        grouped[f.type.value] = grouped.get(f.type.value, 0) + 1
    rows = [[ftype, str(n)] for ftype, n in sorted(grouped.items())]
    table = Table([["Featuretyp", "Anzahl"]] + rows, colWidths=[100 * mm, 30 * mm])
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    return [Paragraph("Inhaltsverzeichnis (Gruppierung)", _H2), table]


def _feature_detail(run: AnalysisRun, feature: FeatureChange, render_images: bool) -> list:
    story: list = [Paragraph(f"{feature.type.value} — {feature.id[:12]}", _H2)]
    story.append(Paragraph(f"Detektor: {feature.detector} · Konfidenz: {feature.confidence:.0%}", _SMALL))

    if render_images:
        paths = files.artifact_dir(run.id) / "screenshots"
        images = []
        for view in ("original", "defeatured", "overlay"):
            p = paths / f"{feature.id}_{view}.png"
            if p.exists():
                images.append(Image(str(p), width=55 * mm, height=41 * mm))
        if images:
            img_table = Table([images], colWidths=[58 * mm] * len(images))
            img_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
            story.append(img_table)
            story.append(Paragraph("Original · Defeatured · Overlay", _SMALL))

    if feature.parameters:
        rows = [[str(k), _fmt(v)] for k, v in feature.parameters.items()]
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
        story.append(Paragraph(f"Risiko: {a.risk.value} (Konfidenz {a.confidence:.0%})", risk_style))
        story.append(Paragraph(a.rationale, _BODY))

    for ev in feature.evidence:
        story.append(Paragraph(f"Evidenz: {ev.kind} — {ev.description}", _SMALL))

    story.append(Paragraph(
        f"Benutzerentscheidung: <b>{feature.user_decision.value}</b>"
        + (f" — {feature.user_comment}" if feature.user_comment else ""),
        _BODY,
    ))
    story.append(Spacer(1, 4 * mm))
    return story


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.3g}"
    return str(v)

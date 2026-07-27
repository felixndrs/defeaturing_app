"""Engineering PDF report.

Structure: cover with the AI summary, table of contents, a reading guide that
explains what risk and confidence actually mean, key figures, then one chapter
per feature type with a detail block per feature. Changes the reviewer
discarded are kept out of those chapters and collected in a final chapter, so
the body of the report describes the approved state only.

Headings carry names, not numbers -- ids, detector and confidence sit in a small
subline underneath, where they can be looked up without dominating the page.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from .. import i18n
from ..domain.enums import UserDecision
from ..domain.models import AnalysisRun, FeatureChange, Project
from ..i18n import Lang
from ..storage import files

# Palette shared with the app: slate greys, amber accent, semantic risk colours.
_INK = colors.HexColor("#111827")
_MUTED = colors.HexColor("#6b7280")
_ACCENT = colors.HexColor("#b45309")
_RULE = colors.HexColor("#d1d5db")
_ZEBRA = colors.HexColor("#f8fafc")

_STYLES = getSampleStyleSheet()
_TITLE = ParagraphStyle(
    "Title2", parent=_STYLES["Title"], fontSize=24, leading=28, alignment=TA_LEFT,
    textColor=_INK, spaceAfter=2 * mm,
)
_SUBTITLE = ParagraphStyle(
    "Subtitle", parent=_STYLES["BodyText"], fontSize=13, leading=17, textColor=_MUTED,
)
# H1 doubles as the table-of-contents marker (see _ReportDocTemplate).
_H1 = ParagraphStyle(
    "H1", parent=_STYLES["Heading1"], fontSize=16, leading=20, textColor=_ACCENT,
    spaceBefore=0, spaceAfter=4 * mm,
)
_H2 = ParagraphStyle(
    "H2", parent=_STYLES["Heading2"], fontSize=12, leading=15, textColor=_INK,
    spaceBefore=5 * mm, spaceAfter=1 * mm,
)
_H3 = ParagraphStyle(
    "H3", parent=_STYLES["Heading3"], fontSize=10, leading=13, textColor=_INK,
    spaceBefore=3 * mm, spaceAfter=1 * mm,
)
_BODY = ParagraphStyle(
    "Body", parent=_STYLES["BodyText"], fontSize=9.5, leading=13.5, textColor=_INK,
)
_SMALL = ParagraphStyle(
    "Small", parent=_STYLES["BodyText"], fontSize=8, leading=11, textColor=_MUTED,
)
_CAPTION = ParagraphStyle("Caption", parent=_SMALL, alignment=1)
_TOC_LEVEL0 = ParagraphStyle("TOCLevel0", parent=_BODY, fontSize=10, leftIndent=4 * mm)

_RISK_HEX = {"low": "#047857", "medium": "#b45309", "high": "#b91c1c"}
# Parameter keys that carry a length unit -- the STEP importer normalises the
# CAD unit to mm (see step_importer.py), so this is a safe assumption.
_LENGTH_KEYS = {"radius", "diameter", "depth", "distance", "width", "length", "thickness", "height"}


def report_filename(project: Project, run: AnalysisRun, lang: Lang = "de") -> str:
    """`defeaturing_review_<projekt>_<JJJJ-MM-TT>.pdf` -- readable in a download
    folder without opening it, and sortable by date."""
    stem = f"defeaturing_review_{i18n.slugify(project.name)}_{run.created_at:%Y-%m-%d}"
    return f"{stem}_en.pdf" if lang == "en" else f"{stem}.pdf"


def _footer_factory(project: Project, lang: Lang):
    def _footer(canvas: pdfcanvas.Canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_MUTED)
        canvas.drawString(20 * mm, 12 * mm, f"{i18n.t('report.title', lang)} — {project.name}")
        canvas.drawRightString(
            A4[0] - 20 * mm, 12 * mm, f"{i18n.t('report.page', lang)} {doc.page}"
        )
        canvas.setStrokeColor(_RULE)
        canvas.setLineWidth(0.5)
        canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
        canvas.restoreState()

    return _footer


class _ReportDocTemplate(SimpleDocTemplate):
    """Registers every chapter heading as a table-of-contents entry."""

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "H1":
            self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))


def build_report(
    run: AnalysisRun, project: Project, render_images: bool = True, lang: Lang = "de"
) -> Path:
    out_path = files.report_path(run.id, lang)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = _ReportDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=22 * mm,
        title=f"{i18n.t('report.title', lang)} — {project.name}",
        author=i18n.t("report.title", lang),
    )

    kept = [f for f in run.features if f.user_decision is not UserDecision.REJECT]
    rejected = [f for f in run.features if f.user_decision is UserDecision.REJECT]

    story: list = []
    story += _cover(project, run, lang)
    story.append(PageBreak())
    story += _toc(lang)
    story.append(PageBreak())
    story += _reading_guide(lang)
    story.append(PageBreak())
    story += _statistics(run, lang)

    grouped: dict[str, list[FeatureChange]] = {}
    for f in kept:
        grouped.setdefault(f.type.value, []).append(f)

    if not kept:
        story.append(PageBreak())
        story.append(Paragraph(i18n.t("stats.changes", lang), _H1))
        story.append(Paragraph(i18n.t("report.no_features", lang), _BODY))

    for ftype in sorted(grouped, key=lambda k: i18n.feature_type(k, lang, plural=True)):
        story.append(PageBreak())
        story.append(Paragraph(i18n.feature_type(ftype, lang, plural=True), _H1))
        story.append(_rule())
        for n, feature in enumerate(grouped[ftype], start=1):
            title = f"{i18n.feature_type(ftype, lang)} {n}"
            story += _feature_detail(run, feature, lang, title, render_images)

    if rejected:
        story.append(PageBreak())
        story.append(Paragraph(i18n.t("report.rejected_chapter", lang), _H1))
        story.append(_rule())
        story.append(Paragraph(i18n.t("report.rejected_intro", lang), _BODY))
        counters: dict[str, int] = {}
        for feature in rejected:
            key = feature.type.value
            counters[key] = counters.get(key, 0) + 1
            title = f"{i18n.feature_type(key, lang)} {counters[key]}"
            story += _feature_detail(run, feature, lang, title, render_images)

    footer = _footer_factory(project, lang)
    doc.multiBuild(story, onFirstPage=footer, onLaterPages=footer)
    return out_path


def _rule() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.7, color=_RULE, spaceAfter=3 * mm)


def _cover(project: Project, run: AnalysisRun, lang: Lang) -> list:
    created = run.created_at if isinstance(run.created_at, datetime) else None
    summary = i18n.pick(run.llm_summary, run.llm_summary_en, lang)
    meta = [
        [Paragraph(i18n.t("report.project", lang), _SMALL), Paragraph(project.name, _BODY)],
        [Paragraph(i18n.t("report.created", lang), _SMALL),
         Paragraph(f"{created:%d.%m.%Y %H:%M} UTC" if created else "—", _BODY)],
        [Paragraph(i18n.t("report.run_id", lang), _SMALL), Paragraph(run.id, _SMALL)],
    ]
    meta_table = Table(meta, colWidths=[35 * mm, 125 * mm])
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
    ]))

    summary_box = Table(
        [[Paragraph(summary or i18n.t("report.summary_missing", lang), _BODY)]],
        colWidths=[160 * mm],
    )
    summary_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _ZEBRA),
        ("BOX", (0, 0), (-1, -1), 0.7, _RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    return [
        Paragraph(i18n.t("report.title", lang), _TITLE),
        Paragraph(project.name, _SUBTITLE),
        Spacer(1, 4 * mm),
        _rule(),
        meta_table,
        Spacer(1, 8 * mm),
        Paragraph(i18n.t("report.summary", lang), _H2),
        summary_box,
    ]


def _toc(lang: Lang) -> list:
    toc = TableOfContents()
    toc.levelStyles = [_TOC_LEVEL0]
    return [Paragraph(i18n.t("report.toc", lang), _TITLE), _rule(), toc]


def _reading_guide(lang: Lang) -> list:
    """Explains the report's own vocabulary -- risk, confidence, the three views,
    the decision -- so a reader who did not run the analysis can judge it."""
    risk_rows = [
        [
            Paragraph(
                f'<b><font color="{_RISK_HEX[level]}">{i18n.risk(level, lang)}</font></b>',
                _BODY,
            ),
            Paragraph(i18n.t(f"guide.risk_{level}", lang), _BODY),
        ]
        for level in ("low", "medium", "high")
    ]
    risk_table = Table(risk_rows, colWidths=[22 * mm, 138 * mm])
    risk_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, _RULE),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    story: list = [
        Paragraph(i18n.t("report.guide", lang), _H1),
        _rule(),
        Paragraph(i18n.t("guide.intro", lang), _BODY),
        Paragraph(i18n.t("guide.risk_title", lang), _H3),
        Paragraph(i18n.t("guide.risk_intro", lang), _BODY),
        Spacer(1, 2 * mm),
        risk_table,
    ]
    for key in ("confidence", "images", "decision", "evidence"):
        story.append(Paragraph(i18n.t(f"guide.{key}_title", lang), _H3))
        story.append(Paragraph(i18n.t(f"guide.{key}_body", lang), _BODY))
    return story


def _statistics(run: AnalysisRun, lang: Lang) -> list:
    s = run.statistics
    decided = sum(1 for f in run.features if f.user_decision is not UserDecision.UNDECIDED)
    rows = [
        (i18n.t("stats.changes", lang), str(len(run.features))),
        (i18n.t("stats.reviewed", lang), f"{decided} / {len(run.features)}"),
        (i18n.t("stats.unknown", lang), str(s.unknown_count)),
        (i18n.t("stats.original_faces", lang), str(s.original_face_count)),
        (i18n.t("stats.defeatured_faces", lang), str(s.defeatured_face_count)),
        (i18n.t("stats.paired_faces", lang), str(s.paired_face_count)),
        (i18n.t("stats.volume_original", lang), f"{s.volume_original:.1f} mm³"),
        (i18n.t("stats.volume_defeatured", lang), f"{s.volume_defeatured:.1f} mm³"),
        (i18n.t("stats.volume_delta", lang), f"{s.volume_delta_rel*100:+.2f} %"),
    ]
    table = Table(
        [[Paragraph(k, _BODY), Paragraph(v, _BODY)] for k, v in rows],
        colWidths=[100 * mm, 60 * mm],
    )
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, _RULE),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _ZEBRA]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [Paragraph(i18n.t("report.statistics", lang), _H1), _rule(), table]


def _feature_detail(
    run: AnalysisRun, feature: FeatureChange, lang: Lang, title: str, render_images: bool
) -> list:
    # Heading names the feature; the identifying numbers go into the subline so
    # they stay findable without shouting.
    head: list = [
        Paragraph(title, _H2),
        Paragraph(
            f"ID {feature.id[3:9]} · {i18n.t('report.detector', lang)} {feature.detector}"
            f" · {i18n.t('report.confidence', lang)} {feature.confidence:.0%}",
            _SMALL,
        ),
    ]
    story: list = [KeepTogether(head)]

    if render_images:
        story += _image_row(run, feature, lang)

    if feature.parameters:
        rows = [
            [Paragraph(i18n.parameter(k, lang), _SMALL), Paragraph(_fmt_param(k, v, lang), _SMALL)]
            for k, v in feature.parameters.items()
        ]
        t = Table(rows, colWidths=[45 * mm, 55 * mm], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, _RULE),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _ZEBRA]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(i18n.t("report.parameters", lang), _SMALL))
        story.append(t)

    if feature.assessment:
        a = feature.assessment
        colour = _RISK_HEX.get(a.risk.value, "#111827")
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"{i18n.t('report.risk', lang)}: "
            f'<b><font color="{colour}">{i18n.risk(a.risk.value, lang)}</font></b>',
            _BODY,
        ))
        story.append(Paragraph(i18n.pick(a.rationale, a.rationale_en, lang), _BODY))

    for ev in feature.evidence:
        story.append(Paragraph(
            f"{i18n.t('report.evidence', lang)}: {i18n.evidence_kind(ev.kind, lang)} — "
            f"{i18n.evidence_description(ev.kind, lang, ev.description)}",
            _SMALL,
        ))

    story.append(Paragraph(
        f"{i18n.t('report.decision', lang)}: "
        f"<b>{i18n.decision(feature.user_decision.value, lang)}</b>"
        + (f" — {feature.user_comment}" if feature.user_comment else ""),
        _BODY,
    ))
    story.append(Spacer(1, 6 * mm))
    return story


def _image_row(run: AnalysisRun, feature: FeatureChange, lang: Lang) -> list:
    paths = files.artifact_dir(run.id) / "screenshots"
    images, captions = [], []
    for view in ("original", "defeatured", "overlay"):
        p = paths / f"{feature.id}_{view}.png"
        if p.exists():
            images.append(Image(str(p), width=52 * mm, height=39 * mm))
            captions.append(Paragraph(i18n.t(f"report.view.{view}", lang), _CAPTION))
    if not images:
        return []
    img_table = Table([images, captions], colWidths=[54 * mm] * len(images), hAlign="LEFT")
    img_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING", (0, 1), (-1, 1), 1),
    ]))
    return [Spacer(1, 2 * mm), img_table]


def _fmt_param(key: str, v, lang: Lang = "de") -> str:
    if isinstance(v, bool):
        return ("ja" if v else "nein") if lang == "de" else ("yes" if v else "no")
    if isinstance(v, float):
        s = f"{v:.3g}"
    else:
        s = str(v)
    if key in _LENGTH_KEYS and isinstance(v, (int, float)):
        s += " mm"
    return s

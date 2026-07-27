"""Server-side UI language for the generated artefacts (PDF, HTML bundle).

The frontend has its own dictionary (frontend/src/i18n.ts); this module covers
everything the backend renders itself. Both sides share the same keys so a
term reads identically in the app and in the report.

Only *static* wording lives here. Prose written by the LLM (rationale, summary)
is generated in both languages at analysis time and stored on the model -- see
``Assessment.rationale_en`` -- because translating it after the fact would need
another model call and would not work at all in the offline bundle.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

Lang = Literal["de", "en"]
LANGUAGES: tuple[Lang, ...] = ("de", "en")
DEFAULT_LANG: Lang = "de"


def normalize_lang(value: str | None) -> Lang:
    """Map anything a caller passes (``?lang=EN``, ``de-DE``, ``None``) onto a
    supported language, falling back to German."""
    if not value:
        return DEFAULT_LANG
    head = value.strip().lower().split("-")[0]
    return head if head in LANGUAGES else DEFAULT_LANG  # type: ignore[return-value]


# --------------------------------------------------------------------------
# Enum vocabularies
# --------------------------------------------------------------------------

# Singular / plural per feature type. The plural form titles the chapter, the
# singular names an individual feature inside it.
FEATURE_TYPE: dict[str, dict[Lang, tuple[str, str]]] = {
    "fillet": {"de": ("Verrundung", "Verrundungen"), "en": ("Fillet", "Fillets")},
    "chamfer": {"de": ("Fase", "Fasen"), "en": ("Chamfer", "Chamfers")},
    "hole": {"de": ("Bohrung", "Bohrungen"), "en": ("Hole", "Holes")},
    "slot": {"de": ("Langloch", "Langlöcher"), "en": ("Slot", "Slots")},
    "pocket": {"de": ("Tasche", "Taschen"), "en": ("Pocket", "Pockets")},
    "boss": {"de": ("Aufsatz", "Aufsätze"), "en": ("Boss", "Bosses")},
    "rib": {"de": ("Rippe", "Rippen"), "en": ("Rib", "Ribs")},
    "simplified_face": {
        "de": ("Vereinfachte Fläche", "Vereinfachte Flächen"),
        "en": ("Simplified face", "Simplified faces"),
    },
    "merged_face": {
        "de": ("Zusammengefasste Fläche", "Zusammengefasste Flächen"),
        "en": ("Merged face", "Merged faces"),
    },
    "unknown": {
        "de": ("Unklassifizierte Änderung", "Unklassifizierte Änderungen"),
        "en": ("Unclassified change", "Unclassified changes"),
    },
}

RISK: dict[str, dict[Lang, str]] = {
    "low": {"de": "niedrig", "en": "low"},
    "medium": {"de": "mittel", "en": "medium"},
    "high": {"de": "hoch", "en": "high"},
}

DECISION: dict[str, dict[Lang, str]] = {
    "undecided": {"de": "Unentschieden", "en": "Undecided"},
    "accept": {"de": "Beibehalten", "en": "Keep"},
    "reject": {"de": "Verworfen", "en": "Discarded"},
}

# Parameter keys the detectors emit. Anything missing falls back to the raw key,
# so a new detector never breaks the report.
PARAMETER: dict[str, dict[Lang, str]] = {
    "radius": {"de": "Radius", "en": "Radius"},
    "diameter": {"de": "Durchmesser", "en": "Diameter"},
    "depth": {"de": "Tiefe", "en": "Depth"},
    "distance": {"de": "Abstand", "en": "Distance"},
    "width": {"de": "Breite", "en": "Width"},
    "length": {"de": "Länge", "en": "Length"},
    "thickness": {"de": "Wandstärke", "en": "Thickness"},
    "height": {"de": "Höhe", "en": "Height"},
    "angle": {"de": "Winkel", "en": "Angle"},
    "area": {"de": "Fläche", "en": "Area"},
    "volume": {"de": "Volumen", "en": "Volume"},
    "patch_count": {"de": "Teilflächen", "en": "Patch count"},
    "face_count": {"de": "Flächenanzahl", "en": "Face count"},
    "closed": {"de": "geschlossen", "en": "Closed"},
    "through": {"de": "durchgehend", "en": "Through"},
    "axis": {"de": "Achse", "en": "Axis"},
    "additive": {"de": "aufbauend", "en": "Additive"},
    "lateral_area": {"de": "Mantelfläche", "en": "Lateral area"},
    "u_closed": {"de": "umlaufend geschlossen", "en": "Closed around"},
    "face_area": {"de": "Flächeninhalt", "en": "Face area"},
    "short_edge": {"de": "kurze Kante", "en": "Short edge"},
    "leg_distance": {"de": "Schenkelabstand", "en": "Leg distance"},
    "end_count": {"de": "Anzahl Rundungen", "en": "Rounded ends"},
    "wall_count": {"de": "Anzahl Wände", "en": "Wall count"},
    "footprint": {"de": "Grundfläche", "en": "Footprint"},
    "volume_delta": {"de": "Volumendifferenz", "en": "Volume delta"},
}

# Evidence kinds, with the detector's explanation translated alongside the
# label -- the description is a fixed sentence per kind, so it belongs in the
# dictionary rather than being written out in English by the detector.
EVIDENCE: dict[str, dict[Lang, tuple[str, str]]] = {
    "tangent_blend": {
        "de": ("Tangentialer Übergang",
               "Teilzylindrische bzw. torusförmige Fläche, tangential zu ihren Nachbarn — "
               "eine verrundete Kante."),
        "en": ("Tangent blend",
               "Partial cylindrical/toroidal patch tangent to its neighbours: a rounded edge."),
    },
    "planar_bevel": {
        "de": ("Ebene Anschrägung", "Eine einzelne ebene Fläche ersetzt eine scharfe Kante — eine Fase."),
        "en": ("Planar bevel", "A single planar face replacing a sharp edge -- a chamfer."),
    },
    "closed_cylinder": {
        "de": ("Geschlossene Zylinderfläche",
               "Die entfernte Fläche ist eine vollständig umlaufende Zylinderwand (360°) — "
               "das Kennzeichen einer Bohrung."),
        "en": ("Closed cylinder",
               "Removed face is a full cylindrical wall (360 deg), the signature of a hole."),
    },
    "depth_from_area": {
        "de": ("Tiefe aus Mantelfläche", "Durchgangslänge aus Mantelfläche geteilt durch Umfang."),
        "en": ("Depth from area", "Through length derived from lateral area / circumference."),
    },
    "planar_cavity": {
        "de": ("Ebene Vertiefung",
               "Ein ebener Boden, umschlossen von ebenen Wänden, in den Körper eingebracht."),
        "en": ("Planar cavity", "A planar floor enclosed by planar walls, cut into the body."),
    },
    "obround_walls": {
        "de": ("Langlochkontur", "Zwei gerundete Enden und ebene Seitenwände bilden ein Langloch."),
        "en": ("Obround walls", "Two rounded ends plus planar side walls form a slot."),
    },
    "additive_cylinder": {
        "de": ("Aufbauender Zylinder",
               "Das entfernte Material bildet eine umlaufende Zylinderwand, die aus dem "
               "Körper herausragt."),
        "en": ("Additive cylinder",
               "Removed material forms a full cylindrical wall protruding from the body."),
    },
    "thin_additive_wall": {
        "de": ("Dünne aufbauende Wand",
               "Dünner ebener Vorsprung: deutlich länger und höher als dick."),
        "en": ("Thin additive wall",
               "Thin planar protrusion: much longer and taller than it is thick."),
    },
    "unclassified_change": {
        "de": ("Unklassifizierte Änderung",
               "Geometrieänderung, die zu keinem bekannten Feature-Muster passt."),
        "en": ("Unclassified change", "Geometry change that matched no known feature pattern."),
    },
}


# --------------------------------------------------------------------------
# Static strings
# --------------------------------------------------------------------------

_T: dict[str, dict[Lang, str]] = {
    "report.title": {"de": "Defeaturing-Review", "en": "Defeaturing Review"},
    "report.project": {"de": "Projekt", "en": "Project"},
    "report.run_id": {"de": "Analyse-ID", "en": "Analysis ID"},
    "report.created": {"de": "Erstellt", "en": "Created"},
    "report.summary": {"de": "KI-Zusammenfassung", "en": "AI summary"},
    "report.summary_missing": {
        "de": "(keine Bewertung verfügbar)",
        "en": "(no assessment available)",
    },
    "report.toc": {"de": "Inhaltsverzeichnis", "en": "Contents"},
    "report.statistics": {"de": "Kennzahlen", "en": "Key figures"},
    "report.guide": {"de": "Lesehilfe", "en": "How to read this report"},
    "report.parameters": {"de": "Parameter", "en": "Parameters"},
    "report.evidence": {"de": "Evidenz", "en": "Evidence"},
    "report.decision": {"de": "Entscheidung", "en": "Decision"},
    "report.risk": {"de": "Risiko", "en": "Risk"},
    "report.confidence": {"de": "Konfidenz", "en": "Confidence"},
    "report.detector": {"de": "Detektor", "en": "Detector"},
    "report.page": {"de": "Seite", "en": "Page"},
    "report.rejected_chapter": {
        "de": "Verworfene Änderungen",
        "en": "Discarded changes",
    },
    "report.rejected_intro": {
        "de": "Diese Änderungen wurden im Review verworfen. Sie sind hier nur zur "
        "Nachvollziehbarkeit dokumentiert und gehören nicht zum freigegebenen Stand.",
        "en": "These changes were discarded during the review. They are documented "
        "here for traceability only and are not part of the approved state.",
    },
    "report.no_features": {
        "de": "Es wurden keine Geometrieänderungen erkannt.",
        "en": "No geometry changes were detected.",
    },
    "report.view.original": {"de": "Original", "en": "Original"},
    "report.view.defeatured": {"de": "Vereinfacht", "en": "Defeatured"},
    "report.view.overlay": {"de": "Überlagerung", "en": "Overlay"},
    "stats.original_faces": {"de": "Flächen im Original", "en": "Faces in original"},
    "stats.defeatured_faces": {
        "de": "Flächen im vereinfachten Modell",
        "en": "Faces in defeatured model",
    },
    "stats.paired_faces": {"de": "Zugeordnete Flächen", "en": "Paired faces"},
    "stats.volume_original": {"de": "Volumen Original", "en": "Volume original"},
    "stats.volume_defeatured": {
        "de": "Volumen vereinfacht",
        "en": "Volume defeatured",
    },
    "stats.volume_delta": {"de": "Volumenänderung", "en": "Volume change"},
    "stats.unknown": {
        "de": "Unklassifizierte Änderungen",
        "en": "Unclassified changes",
    },
    "stats.reviewed": {"de": "Davon entschieden", "en": "Of these decided"},
    "stats.changes": {"de": "Erkannte Änderungen", "en": "Detected changes"},
    # Reading guide -----------------------------------------------------
    "guide.intro": {
        "de": "Dieser Bericht dokumentiert, welche Geometrie zwischen dem Originalmodell "
        "und dem vereinfachten Modell entfallen ist, und wie stark jede einzelne "
        "Vereinfachung das Ergebnis einer FE-Simulation verfälschen kann.",
        "en": "This report documents which geometry was removed between the original "
        "and the defeatured model, and how much each individual simplification "
        "may distort the result of an FE simulation.",
    },
    "guide.risk_title": {
        "de": "Risiko — Gefahr der Ergebnisverfälschung",
        "en": "Risk — danger of distorting the result",
    },
    "guide.risk_intro": {
        "de": "Das Risiko beschreibt, wie stark das Entfernen dieser Geometrie das "
        "Simulationsergebnis verfälschen kann — nicht, wie sicher die Erkennung ist.",
        "en": "Risk describes how much removing this geometry may distort the "
        "simulation result — not how certain the detection is.",
    },
    "guide.risk_low": {
        "de": "Vernachlässigbarer Einfluss auf Steifigkeit und Spannungsverteilung; "
        "die Vereinfachung kann in der Regel ohne Prüfung übernommen werden.",
        "en": "Negligible effect on stiffness and stress distribution; the "
        "simplification can normally be accepted without further checks.",
    },
    "guide.risk_medium": {
        "de": "Lokal spürbarer Einfluss. Unkritisch bei globalen Betrachtungen, "
        "relevant sobald in diesem Bereich Spannungen ausgewertet werden.",
        "en": "Locally noticeable effect. Uncritical for global results, but "
        "relevant as soon as stresses are evaluated in this region.",
    },
    "guide.risk_high": {
        "de": "Kann das Ergebnis deutlich verfälschen — etwa lasttragende Strukturen "
        "oder unklassifizierte Änderungen. Vor der Übernahme von Hand prüfen.",
        "en": "May distort the result significantly — e.g. load-bearing structures "
        "or unclassified changes. Review by hand before accepting.",
    },
    "guide.confidence_title": {
        "de": "Konfidenz — Sicherheit der Erkennung",
        "en": "Confidence — certainty of the detection",
    },
    "guide.confidence_body": {
        "de": "Die Konfidenz sagt aus, wie eindeutig die Geometrie dem genannten "
        "Feature-Typ zugeordnet werden konnte. Ein niedriger Wert bedeutet nicht, "
        "dass die Änderung kritisch ist, sondern dass die Einordnung unsicher ist.",
        "en": "Confidence states how unambiguously the geometry could be assigned to "
        "the named feature type. A low value does not mean the change is critical, "
        "only that its classification is uncertain.",
    },
    "guide.images_title": {"de": "Die drei Ansichten", "en": "The three views"},
    "guide.images_body": {
        "de": "Original zeigt das unveränderte Bauteil, Vereinfacht den bereinigten "
        "Stand, Überlagerung beide übereinander. Die betroffene Geometrie ist "
        "orange hervorgehoben; alle drei Bilder nutzen dieselbe Kameraposition.",
        "en": "Original shows the unchanged part, Defeatured the cleaned-up state, "
        "Overlay both on top of each other. The affected geometry is highlighted "
        "in orange; all three images share the same camera position.",
    },
    "guide.decision_title": {"de": "Entscheidung", "en": "Decision"},
    "guide.decision_body": {
        "de": "Beibehalten heißt: die Vereinfachung wird übernommen. Verworfen heißt: "
        "die Geometrie muss im Simulationsmodell erhalten bleiben — solche "
        "Änderungen stehen gesammelt im letzten Kapitel.",
        "en": "Keep means the simplification is accepted. Discarded means the geometry "
        "must be preserved in the simulation model — those changes are collected "
        "in the final chapter.",
    },
    "guide.evidence_title": {"de": "Evidenz", "en": "Evidence"},
    # Offline review bundle ---------------------------------------------
    "bundle.subtitle": {
        "de": "Defeaturing-Review · offline, ohne Neuanalyse",
        "en": "Defeaturing review · offline, no re-analysis",
    },
    "bundle.select_hint": {
        "de": "Änderung links auswählen.",
        "en": "Select a change on the left.",
    },
    "bundle.overview": {"de": "Übersicht", "en": "Overview"},
    "bundle.changes": {"de": "Änderungen", "en": "Changes"},
    "guide.evidence_body": {
        "de": "Jede Einstufung stützt sich ausschließlich auf gemessene Größen aus dem "
        "Geometrievergleich. Diese sind unter jedem Feature aufgeführt, damit die "
        "Bewertung nachvollziehbar bleibt.",
        "en": "Every assessment rests solely on measured quantities from the geometry "
        "comparison. They are listed under each feature so the rating stays "
        "traceable.",
    },
}


def t(key: str, lang: Lang = DEFAULT_LANG) -> str:
    entry = _T.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry[DEFAULT_LANG])


def feature_type(value: str, lang: Lang = DEFAULT_LANG, plural: bool = False) -> str:
    entry = FEATURE_TYPE.get(value)
    if entry is None:
        return value
    return entry.get(lang, entry[DEFAULT_LANG])[1 if plural else 0]


def risk(value: str, lang: Lang = DEFAULT_LANG) -> str:
    return RISK.get(value, {}).get(lang, value)


def decision(value: str, lang: Lang = DEFAULT_LANG) -> str:
    return DECISION.get(value, {}).get(lang, value)


def parameter(key: str, lang: Lang = DEFAULT_LANG) -> str:
    return PARAMETER.get(key, {}).get(lang, key.replace("_", " "))


def evidence_kind(value: str, lang: Lang = DEFAULT_LANG) -> str:
    entry = EVIDENCE.get(value)
    if entry is None:
        return value.replace("_", " ")
    return entry.get(lang, entry[DEFAULT_LANG])[0]


def evidence_description(value: str, lang: Lang, fallback: str) -> str:
    """Translated explanation of an evidence kind.

    Detectors write their sentence in English; a kind we do not know yet keeps
    that original text rather than losing it.
    """
    entry = EVIDENCE.get(value)
    if entry is None:
        return fallback
    return entry.get(lang, entry[DEFAULT_LANG])[1]


def pick(de: str, en: str, lang: Lang = DEFAULT_LANG) -> str:
    """Choose between the two stored variants of LLM prose.

    Falls back to the German text when the English one is missing -- runs from
    before the bilingual assessment, or a provider that only answered once.
    """
    return (en or de) if lang == "en" else de


def slugify(value: str) -> str:
    """Filename-safe ASCII slug, used for the report filename.

    Umlauts are transliterated rather than dropped, so "Gehäuse" stays readable
    as "gehaeuse" instead of collapsing to "gehuse".
    """
    folded = (
        value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
        .replace("ß", "ss")
    )
    ascii_only = unicodedata.normalize("NFKD", folded).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower()
    return slug or "projekt"

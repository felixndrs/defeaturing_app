// UI language for the app. The backend has a mirror of this dictionary
// (backend/app/i18n.py) for the PDF and the offline bundle, using the same keys
// so a term reads identically in the app and in the report.
//
// Prose written by the LLM (risk rationale, run summary) is not translated here:
// it is generated in both languages during the analysis and stored on the run --
// see `prose()`.

import { useCallback, useMemo } from "react";
import { create } from "zustand";

export type Lang = "de" | "en";

const STORAGE_KEY = "defeaturing.lang";

function initialLang(): Lang {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "de" || stored === "en") return stored;
  return navigator.language?.toLowerCase().startsWith("en") ? "en" : "de";
}

interface LangState {
  lang: Lang;
  setLang: (lang: Lang) => void;
}

export const useLangStore = create<LangState>((set) => ({
  lang: initialLang(),
  setLang(lang) {
    localStorage.setItem(STORAGE_KEY, lang);
    applyToDocument(lang);
    set({ lang });
  },
}));

/** Browser chrome outside React's tree: tab title and the html lang attribute. */
function applyToDocument(lang: Lang) {
  document.documentElement.lang = lang;
  document.title = lookup("app.title", lang);
}

// --------------------------------------------------------------------------
// Vocabularies
// --------------------------------------------------------------------------

type Pair = Record<Lang, string>;

const FEATURE_TYPE: Record<string, Record<Lang, [string, string]>> = {
  fillet: { de: ["Verrundung", "Verrundungen"], en: ["Fillet", "Fillets"] },
  chamfer: { de: ["Fase", "Fasen"], en: ["Chamfer", "Chamfers"] },
  hole: { de: ["Bohrung", "Bohrungen"], en: ["Hole", "Holes"] },
  slot: { de: ["Langloch", "Langlöcher"], en: ["Slot", "Slots"] },
  pocket: { de: ["Tasche", "Taschen"], en: ["Pocket", "Pockets"] },
  boss: { de: ["Aufsatz", "Aufsätze"], en: ["Boss", "Bosses"] },
  rib: { de: ["Rippe", "Rippen"], en: ["Rib", "Ribs"] },
  simplified_face: {
    de: ["Vereinfachte Fläche", "Vereinfachte Flächen"],
    en: ["Simplified face", "Simplified faces"],
  },
  merged_face: {
    de: ["Zusammengefasste Fläche", "Zusammengefasste Flächen"],
    en: ["Merged face", "Merged faces"],
  },
  unknown: {
    de: ["Unklassifizierte Änderung", "Unklassifizierte Änderungen"],
    en: ["Unclassified change", "Unclassified changes"],
  },
};

const RISK: Record<string, Pair> = {
  low: { de: "niedrig", en: "low" },
  medium: { de: "mittel", en: "medium" },
  high: { de: "hoch", en: "high" },
};

const DECISION: Record<string, Pair> = {
  undecided: { de: "Unentschieden", en: "Undecided" },
  accept: { de: "Beibehalten", en: "Keep" },
  reject: { de: "Verworfen", en: "Discarded" },
};

const PARAMETER: Record<string, Pair> = {
  radius: { de: "Radius", en: "Radius" },
  diameter: { de: "Durchmesser", en: "Diameter" },
  depth: { de: "Tiefe", en: "Depth" },
  distance: { de: "Abstand", en: "Distance" },
  width: { de: "Breite", en: "Width" },
  length: { de: "Länge", en: "Length" },
  thickness: { de: "Wandstärke", en: "Thickness" },
  height: { de: "Höhe", en: "Height" },
  angle: { de: "Winkel", en: "Angle" },
  area: { de: "Fläche", en: "Area" },
  volume: { de: "Volumen", en: "Volume" },
  patch_count: { de: "Teilflächen", en: "Patch count" },
  face_count: { de: "Flächenanzahl", en: "Face count" },
  closed: { de: "geschlossen", en: "Closed" },
  through: { de: "durchgehend", en: "Through" },
  axis: { de: "Achse", en: "Axis" },
  additive: { de: "aufbauend", en: "Additive" },
  lateral_area: { de: "Mantelfläche", en: "Lateral area" },
  u_closed: { de: "umlaufend geschlossen", en: "Closed around" },
  face_area: { de: "Flächeninhalt", en: "Face area" },
  short_edge: { de: "kurze Kante", en: "Short edge" },
  leg_distance: { de: "Schenkelabstand", en: "Leg distance" },
  end_count: { de: "Anzahl Rundungen", en: "Rounded ends" },
  wall_count: { de: "Anzahl Wände", en: "Wall count" },
  footprint: { de: "Grundfläche", en: "Footprint" },
  volume_delta: { de: "Volumendifferenz", en: "Volume delta" },
};

// Evidence kinds as [label, description]. Detectors emit their sentence in
// English; keeping the translation here means the app and the report say the
// same thing without the detector knowing about languages.
const EVIDENCE: Record<string, Record<Lang, [string, string]>> = {
  tangent_blend: {
    de: [
      "Tangentialer Übergang",
      "Teilzylindrische bzw. torusförmige Fläche, tangential zu ihren Nachbarn — eine verrundete Kante.",
    ],
    en: [
      "Tangent blend",
      "Partial cylindrical/toroidal patch tangent to its neighbours: a rounded edge.",
    ],
  },
  planar_bevel: {
    de: ["Ebene Anschrägung", "Eine einzelne ebene Fläche ersetzt eine scharfe Kante — eine Fase."],
    en: ["Planar bevel", "A single planar face replacing a sharp edge -- a chamfer."],
  },
  closed_cylinder: {
    de: [
      "Geschlossene Zylinderfläche",
      "Die entfernte Fläche ist eine vollständig umlaufende Zylinderwand (360°) — das Kennzeichen einer Bohrung.",
    ],
    en: [
      "Closed cylinder",
      "Removed face is a full cylindrical wall (360 deg), the signature of a hole.",
    ],
  },
  depth_from_area: {
    de: ["Tiefe aus Mantelfläche", "Durchgangslänge aus Mantelfläche geteilt durch Umfang."],
    en: ["Depth from area", "Through length derived from lateral area / circumference."],
  },
  planar_cavity: {
    de: [
      "Ebene Vertiefung",
      "Ein ebener Boden, umschlossen von ebenen Wänden, in den Körper eingebracht.",
    ],
    en: ["Planar cavity", "A planar floor enclosed by planar walls, cut into the body."],
  },
  obround_walls: {
    de: ["Langlochkontur", "Zwei gerundete Enden und ebene Seitenwände bilden ein Langloch."],
    en: ["Obround walls", "Two rounded ends plus planar side walls form a slot."],
  },
  additive_cylinder: {
    de: [
      "Aufbauender Zylinder",
      "Das entfernte Material bildet eine umlaufende Zylinderwand, die aus dem Körper herausragt.",
    ],
    en: [
      "Additive cylinder",
      "Removed material forms a full cylindrical wall protruding from the body.",
    ],
  },
  thin_additive_wall: {
    de: ["Dünne aufbauende Wand", "Dünner ebener Vorsprung: deutlich länger und höher als dick."],
    en: ["Thin additive wall", "Thin planar protrusion: much longer and taller than it is thick."],
  },
  unclassified_change: {
    de: [
      "Unklassifizierte Änderung",
      "Geometrieänderung, die zu keinem bekannten Feature-Muster passt.",
    ],
    en: ["Unclassified change", "Geometry change that matched no known feature pattern."],
  },
};

// Parameter keys carrying a length unit; the importer normalises to mm.
const LENGTH_KEYS = new Set([
  "radius", "diameter", "depth", "distance", "width", "length", "thickness", "height",
]);

// --------------------------------------------------------------------------
// Static strings
// --------------------------------------------------------------------------

const DICT: Record<string, Pair> = {
  "app.title": { de: "Defeaturing-Review", en: "Defeaturing Review" },
  "app.newProject": { de: "Neues Projekt", en: "New project" },
  "app.back": { de: "Zurück", en: "Back" },
  "app.analyzing": {
    de: "Analyse läuft… Modelle werden verglichen.",
    en: "Analysis running… comparing models.",
  },
  "app.error": { de: "Fehler", en: "Error" },
  "app.changes": { de: "Änderungen", en: "changes" },
  "app.unclassified": { de: "unklassifiziert", en: "unclassified" },
  "app.decided": { de: "entschieden", en: "decided" },
  "app.shortcuts": {
    de: "j/k navigieren · a/r entscheiden",
    en: "j/k to navigate · a/r to decide",
  },
  "app.summary": { de: "KI-Zusammenfassung", en: "AI summary" },
  "app.noSelection": { de: "Keine Änderung ausgewählt.", en: "No change selected." },
  "app.language": { de: "Sprache", en: "Language" },
  "app.cancel": { de: "Abbrechen", en: "Cancel" },

  "confirmNew.title": { de: "Neues Projekt starten?", en: "Start a new project?" },
  "confirmNew.saved": {
    de: "Alle Entscheidungen und Kommentare sind bereits gespeichert. Über diesen Link öffnest du das Review später wieder:",
    en: "All decisions and comments are already saved. This link reopens the review later:",
  },
  "confirmNew.copy": { de: "Link kopieren", en: "Copy link" },
  "confirmNew.copied": { de: "Kopiert", en: "Copied" },
  "confirmNew.report": {
    de: "Bericht jetzt herunterladen:",
    en: "Download the report now:",
  },
  "confirmNew.undecided": {
    de: "{n} von {total} Änderungen sind noch nicht entschieden.",
    en: "{n} of {total} changes are still undecided.",
  },
  "confirmNew.confirm": { de: "Neues Projekt", en: "New project" },

  "upload.subtitle": {
    de: "Original- und vereinfachtes STEP-Modell hochladen.",
    en: "Upload the original and the defeatured STEP model.",
  },
  "upload.projectName": { de: "Projektname", en: "Project name" },
  "upload.original": { de: "Original (STEP)", en: "Original (STEP)" },
  "upload.defeatured": { de: "Vereinfacht (STEP)", en: "Defeatured (STEP)" },
  "upload.start": { de: "Analyse starten", en: "Start analysis" },
  "upload.defaultName": { de: "Defeaturing-Review", en: "Defeaturing Review" },

  "report.section": { de: "Bericht", en: "Report" },
  "report.pdf": { de: "PDF", en: "PDF" },
  "report.bundle": { de: "HTML-Paket", en: "HTML package" },
  "report.building": { de: "wird erstellt…", en: "building…" },
  "report.failed": {
    de: "Erstellung fehlgeschlagen. Bitte erneut versuchen.",
    en: "Generation failed. Please try again.",
  },

  "detail.detectedBy": { de: "detektiert von", en: "detected by" },
  "detail.confidence": { de: "Konfidenz", en: "Confidence" },
  "detail.parameters": { de: "Parameter", en: "Parameters" },
  "detail.assessment": { de: "KI-Bewertung", en: "AI assessment" },
  "detail.risk": { de: "Risiko", en: "Risk" },
  "detail.riskHint": {
    de: "Risiko einer Verfälschung des Simulationsergebnisses",
    en: "Risk of distorting the simulation result",
  },
  "detail.evidence": { de: "Evidenzen", en: "Evidence" },
  "detail.comment": { de: "Kommentar", en: "Comment" },
  "detail.commentPlaceholder": {
    de: "Anmerkung zur Entscheidung…",
    en: "Note on this decision…",
  },
  "detail.keep": { de: "Beibehalten (a)", en: "Keep (a)" },
  "detail.discard": { de: "Verwerfen (r)", en: "Discard (r)" },

  "viewer.loading": { de: "Lade Original…", en: "Loading original…" },
  "viewer.original": { de: "ORIGINAL", en: "ORIGINAL" },
  "viewer.defeatured": { de: "VEREINFACHT", en: "DEFEATURED" },
  "viewer.center": { de: "Ansicht zentrieren", en: "Centre view" },
  "viewer.partColor": { de: "Bauteilfarbe", en: "Part colour" },
  "viewer.background": { de: "Hintergrund", en: "Background" },
  "viewer.color.steel": { de: "Stahl", en: "Steel" },
  "viewer.color.slate": { de: "Blaugrau", en: "Slate" },
  "viewer.color.brass": { de: "Messing", en: "Brass" },
  "viewer.color.graphite": { de: "Graphit", en: "Graphite" },
  "viewer.bg.white": { de: "Weiß", en: "White" },
  "viewer.bg.grey": { de: "Grau", en: "Grey" },
  "viewer.bg.dark": { de: "Dunkelgrau", en: "Dark grey" },
};

function lookup(key: string, lang: Lang): string {
  return DICT[key]?.[lang] ?? key;
}

applyToDocument(useLangStore.getState().lang);

export interface Translator {
  lang: Lang;
  t: (key: string) => string;
  featureType: (value: string, plural?: boolean) => string;
  risk: (value: string) => string;
  decision: (value: string) => string;
  parameter: (key: string) => string;
  evidenceKind: (value: string) => string;
  /** Translated explanation of an evidence kind; unknown kinds keep `fallback`. */
  evidenceDescription: (value: string, fallback: string) => string;
  /** Format a parameter value, appending mm to length-valued keys. */
  paramValue: (key: string, value: unknown) => string;
  /** Pick the right variant of LLM prose; falls back to German. */
  prose: (de: string, en?: string | null) => string;
}

export function useT(): Translator {
  const lang = useLangStore((s) => s.lang);
  return useMemo<Translator>(
    () => ({
      lang,
      t: (key) => lookup(key, lang),
      featureType: (value, plural = false) =>
        FEATURE_TYPE[value]?.[lang]?.[plural ? 1 : 0] ?? value,
      risk: (value) => RISK[value]?.[lang] ?? value,
      decision: (value) => DECISION[value]?.[lang] ?? value,
      parameter: (key) => PARAMETER[key]?.[lang] ?? key.replace(/_/g, " "),
      evidenceKind: (value) => EVIDENCE[value]?.[lang]?.[0] ?? value.replace(/_/g, " "),
      evidenceDescription: (value, fallback) => EVIDENCE[value]?.[lang]?.[1] ?? fallback,
      paramValue: (key, value) => formatValue(key, value, lang),
      prose: (de, en) => (lang === "en" ? en || de : de),
    }),
    [lang],
  );
}

/** Stable setter for the language toggle. */
export function useSetLang(): (lang: Lang) => void {
  const setLang = useLangStore((s) => s.setLang);
  return useCallback((lang: Lang) => setLang(lang), [setLang]);
}

function formatValue(key: string, value: unknown, lang: Lang): string {
  if (typeof value === "boolean") {
    return lang === "de" ? (value ? "ja" : "nein") : value ? "yes" : "no";
  }
  if (typeof value === "number") {
    // Round to 3 decimals, then drop the trailing zeros: "20.000" reads as a
    // measurement precision the analysis never claimed.
    const text = Number.isInteger(value) ? String(value) : String(parseFloat(value.toFixed(3)));
    return LENGTH_KEYS.has(key) ? `${text} mm` : text;
  }
  if (Array.isArray(value)) return value.map((v) => formatValue(key, v, lang)).join(", ");
  return String(value);
}

// Look of the 3D viewer: part colour and background, both user-selectable and
// remembered across sessions.
//
// Background is more than a canvas colour: grid, edge lines and the floor
// labels are drawn on top of it, so each background ships the ink colours that
// stay legible against it. Picking them per background is what keeps the dark
// option from swallowing the edge lines.

import { create } from "zustand";

export interface PartColor {
  key: string;
  hex: string;
}

export interface Background {
  key: string;
  /** Canvas clear colour. */
  bg: string;
  /** Swatch shown in the menu -- the background colour itself. */
  swatch: string;
  gridCell: string;
  gridSection: string;
  edge: string;
  label: string;
}

export const PART_COLORS: PartColor[] = [
  { key: "steel", hex: "#9aa3b0" },
  { key: "slate", hex: "#7f9bc4" },
  { key: "brass", hex: "#c9a227" },
  { key: "graphite", hex: "#5c636f" },
];

export const BACKGROUNDS: Background[] = [
  {
    key: "white",
    bg: "#ffffff",
    swatch: "#ffffff",
    gridCell: "#e5e8ed",
    gridSection: "#c9ced7",
    edge: "#5b6472",
    label: "#94a3b8",
  },
  {
    key: "grey",
    bg: "#e7eaef",
    swatch: "#e7eaef",
    gridCell: "#c7ccd4",
    gridSection: "#a3aab5",
    edge: "#3f4756",
    label: "#64748b",
  },
  {
    key: "dark",
    bg: "#2b3038",
    swatch: "#2b3038",
    gridCell: "#3a414c",
    gridSection: "#4b5462",
    edge: "#c3cad6",
    label: "#7c8697",
  },
];

const STORAGE_KEY = "defeaturing.viewer";

interface ViewerTheme {
  partColor: string;
  background: string;
  setPartColor: (key: string) => void;
  setBackground: (key: string) => void;
}

function restore(): { partColor: string; background: string } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const saved = raw ? JSON.parse(raw) : {};
    return {
      partColor: PART_COLORS.some((c) => c.key === saved.partColor)
        ? saved.partColor
        : PART_COLORS[0].key,
      background: BACKGROUNDS.some((b) => b.key === saved.background)
        ? saved.background
        : BACKGROUNDS[1].key,
    };
  } catch {
    return { partColor: PART_COLORS[0].key, background: BACKGROUNDS[1].key };
  }
}

export const useViewerTheme = create<ViewerTheme>((set, get) => ({
  ...restore(),
  setPartColor(key) {
    set({ partColor: key });
    persist(get());
  },
  setBackground(key) {
    set({ background: key });
    persist(get());
  },
}));

function persist(state: ViewerTheme) {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ partColor: state.partColor, background: state.background }),
  );
}

export function partColorOf(key: string): string {
  return (PART_COLORS.find((c) => c.key === key) ?? PART_COLORS[0]).hex;
}

export function backgroundOf(key: string): Background {
  return BACKGROUNDS.find((b) => b.key === key) ?? BACKGROUNDS[1];
}

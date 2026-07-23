import { create } from "zustand";
import * as api from "./api";
import type { AnalysisRun, FeatureChange, ProjectDetail, UserDecision } from "./types";

type Phase = "upload" | "analyzing" | "review" | "error";

interface ReviewState {
  phase: Phase;
  error: string;
  project: ProjectDetail | null;
  run: AnalysisRun | null;
  selectedFeatureId: string | null;

  uploadAndAnalyze: (name: string, original: File, defeatured: File) => Promise<void>;
  loadRun: (runId: string) => Promise<void>;
  selectFeature: (id: string | null) => void;
  decide: (id: string, decision: UserDecision) => Promise<void>;
  comment: (id: string, comment: string) => Promise<void>;
  reset: () => void;
}

export const useReview = create<ReviewState>((set, get) => ({
  phase: "upload",
  error: "",
  project: null,
  run: null,
  selectedFeatureId: null,

  async uploadAndAnalyze(name, original, defeatured) {
    try {
      set({ phase: "analyzing", error: "" });
      const project = await api.createProject(name, original, defeatured);
      set({ project });
      const { id: runId } = await api.startAnalysis(project.id);

      // Poll until the background analysis finishes.
      for (;;) {
        const run = await api.getRun(runId);
        if (run.status === "done") {
          set({ run, phase: "review", selectedFeatureId: run.features[0]?.id ?? null });
          return;
        }
        if (run.status === "failed") {
          set({ phase: "error", error: run.error || "Analysis failed" });
          return;
        }
        await new Promise((r) => setTimeout(r, 500));
      }
    } catch (e) {
      set({ phase: "error", error: String(e) });
    }
  },

  async loadRun(runId) {
    // Deep-link into an existing review (?run=...): the project was analysed
    // once and can be reopened without re-uploading the models.
    try {
      set({ phase: "analyzing", error: "" });
      const run = await api.getRun(runId);
      const project = await api.getProject(run.project_id);
      if (run.status === "done") {
        set({ run, project, phase: "review", selectedFeatureId: run.features[0]?.id ?? null });
      } else {
        set({ phase: "error", error: `Run status: ${run.status}` });
      }
    } catch (e) {
      set({ phase: "error", error: String(e) });
    }
  },

  selectFeature(id) {
    set({ selectedFeatureId: id });
  },

  async decide(id, decision) {
    const { run } = get();
    if (!run) return;
    const updated = await api.patchFeature(run.id, id, { user_decision: decision });
    replaceFeature(set, get, updated);
  },

  async comment(id, comment) {
    const { run } = get();
    if (!run) return;
    const updated = await api.patchFeature(run.id, id, { user_comment: comment });
    replaceFeature(set, get, updated);
  },

  reset() {
    set({ phase: "upload", error: "", project: null, run: null, selectedFeatureId: null });
  },
}));

// Derives the selected feature from primitive slices (run, selectedFeatureId),
// so components re-render on selection change. A store method returning this
// value (e.g. `selectedFeature: () => ...`) would NOT do that: zustand only
// re-renders when the *selected slice* changes by reference, and a method
// reference is stable across the store's lifetime even though what it
// computes changes -- the classic "selector returns a function" trap.
export function useSelectedFeature(): FeatureChange | null {
  const run = useReview((s) => s.run);
  const selectedFeatureId = useReview((s) => s.selectedFeatureId);
  return run?.features.find((f) => f.id === selectedFeatureId) ?? null;
}

function replaceFeature(
  set: (partial: Partial<ReviewState>) => void,
  get: () => ReviewState,
  updated: FeatureChange,
) {
  const { run } = get();
  if (!run) return;
  set({
    run: {
      ...run,
      features: run.features.map((f) => (f.id === updated.id ? updated : f)),
    },
  });
}

import { useEffect, useMemo } from "react";
import { useReview } from "./store";
import { UploadForm } from "./components/UploadForm";
import { FeatureList } from "./components/FeatureList";
import { FeatureDetail } from "./components/FeatureDetail";
import { Viewer } from "./components/Viewer";

export default function App() {
  const phase = useReview((s) => s.phase);
  const error = useReview((s) => s.error);
  const reset = useReview((s) => s.reset);
  const loadRun = useReview((s) => s.loadRun);

  // Deep-link support: ?run=<id> reopens an existing review without re-uploading.
  useEffect(() => {
    const runId = new URLSearchParams(window.location.search).get("run");
    if (runId) loadRun(runId);
  }, [loadRun]);

  if (phase === "upload") return <UploadForm />;
  if (phase === "analyzing")
    return <Centered>Analyse läuft… Modelle werden verglichen.</Centered>;
  if (phase === "error")
    return (
      <Centered>
        <div className="text-rose-400">Fehler: {error}</div>
        <button onClick={reset} className="mt-3 rounded bg-edge px-3 py-1.5 text-sm">
          Zurück
        </button>
      </Centered>
    );
  return <Review />;
}

function Review() {
  const run = useReview((s) => s.run)!;
  const project = useReview((s) => s.project)!;
  const feature = useReview((s) => s.selectedFeature)();
  const select = useReview((s) => s.selectFeature);
  const decide = useReview((s) => s.decide);
  const reset = useReview((s) => s.reset);

  const gap = useMemo(
    () => Math.max(20, Math.cbrt(run.statistics.volume_original || 1000) * 2.4),
    [run],
  );

  // Keyboard navigation: j/k move, a/r decide. The real productivity lever when
  // there are hundreds of features.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) return;
      const feats = run.features;
      const idx = feats.findIndex((f) => f.id === feature?.id);
      if (e.key === "j" && idx < feats.length - 1) select(feats[idx + 1].id);
      else if (e.key === "k" && idx > 0) select(feats[idx - 1].id);
      else if (e.key === "a" && feature) decide(feature.id, "accept");
      else if (e.key === "r" && feature) decide(feature.id, "reject");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [run, feature, select, decide]);

  const decided = run.features.filter((f) => f.user_decision !== "undecided").length;

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-4 border-b border-edge px-4 py-2">
        <div className="font-semibold text-gray-100">{project.name}</div>
        <div className="text-xs text-gray-400">
          {run.features.length} Änderungen · {run.statistics.unknown_count} unklassifiziert ·{" "}
          {decided}/{run.features.length} entschieden
        </div>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-gray-500">j/k navigieren · a/r entscheiden</span>
          <button onClick={reset} className="rounded bg-edge px-3 py-1 text-sm">
            Neues Projekt
          </button>
        </div>
      </header>

      {run.llm_summary && (
        <div className="border-b border-edge bg-black/20 px-4 py-2 text-xs text-gray-300">
          <span className="font-semibold text-gray-400">KI-Zusammenfassung: </span>
          {run.llm_summary}
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <aside className="w-64 shrink-0 border-r border-edge bg-panel">
          <FeatureList />
        </aside>
        <main className="min-w-0 flex-1">
          {project.original && project.defeatured && (
            <Viewer
              originalId={project.original.id}
              defeaturedId={project.defeatured.id}
              feature={feature}
              gap={gap}
            />
          )}
        </main>
        <aside className="w-80 shrink-0 border-l border-edge bg-panel">
          {feature ? (
            <FeatureDetail feature={feature} />
          ) : (
            <div className="p-4 text-sm text-gray-500">Kein Feature ausgewählt.</div>
          )}
        </aside>
      </div>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-gray-300">{children}</div>
  );
}

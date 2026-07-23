import { useMemo } from "react";
import { useReview } from "../store";
import type { FeatureChange } from "../types";

const DECISION_MARK: Record<string, string> = {
  accept: "✓",
  reject: "✕",
  undecided: "•",
};
const DECISION_CLASS: Record<string, string> = {
  accept: "text-emerald-400",
  reject: "text-rose-400",
  undecided: "text-gray-500",
};
const RISK_CLASS: Record<string, string> = {
  low: "bg-emerald-900/60 text-emerald-300",
  medium: "bg-amber-900/60 text-amber-300",
  high: "bg-rose-900/60 text-rose-300",
};

export function FeatureList() {
  const run = useReview((s) => s.run);
  const selectedId = useReview((s) => s.selectedFeatureId);
  const select = useReview((s) => s.selectFeature);

  const groups = useMemo(() => {
    const byType: Record<string, FeatureChange[]> = {};
    for (const f of run?.features ?? []) (byType[f.type] ??= []).push(f);
    return Object.entries(byType).sort((a, b) => a[0].localeCompare(b[0]));
  }, [run]);

  if (!run) return null;

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {groups.map(([type, items]) => (
        <div key={type}>
          <div className="sticky top-0 bg-panel px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-gray-400">
            {type} <span className="text-gray-600">({items.length})</span>
          </div>
          {items.map((f) => (
            <button
              key={f.id}
              onClick={() => select(f.id)}
              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-edge ${
                f.id === selectedId ? "bg-edge ring-1 ring-inset ring-amber-500/60" : ""
              }`}
            >
              <span className={DECISION_CLASS[f.user_decision]}>
                {DECISION_MARK[f.user_decision]}
              </span>
              <span className="flex-1 truncate text-gray-200">
                {f.type}-{f.id.slice(3, 9)}
              </span>
              {f.assessment && (
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] ${RISK_CLASS[f.assessment.risk]}`}
                >
                  {f.assessment.risk}
                </span>
              )}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

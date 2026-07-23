import { useEffect, useState } from "react";
import { useReview } from "../store";
import type { FeatureChange } from "../types";

const RISK_CLASS: Record<string, string> = {
  low: "text-emerald-300",
  medium: "text-amber-300",
  high: "text-rose-300",
};

function fmt(v: unknown): string {
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(3);
  if (Array.isArray(v)) return v.map(fmt).join(", ");
  return String(v);
}

export function FeatureDetail({ feature }: { feature: FeatureChange }) {
  const decide = useReview((s) => s.decide);
  const comment = useReview((s) => s.comment);
  const [draft, setDraft] = useState(feature.user_comment);

  useEffect(() => setDraft(feature.user_comment), [feature.id, feature.user_comment]);

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4 text-sm">
      <h2 className="text-lg font-semibold capitalize text-gray-100">{feature.type}</h2>
      <div className="mt-1 text-xs text-gray-500">
        detektiert von {feature.detector} · Konfidenz {(feature.confidence * 100).toFixed(0)}%
      </div>

      <Section title="Parameter">
        <dl className="grid grid-cols-2 gap-x-3 gap-y-1">
          {Object.entries(feature.parameters).map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-gray-400">{k}</dt>
              <dd className="text-gray-200">{fmt(v)}</dd>
            </div>
          ))}
        </dl>
      </Section>

      {feature.assessment && (
        <Section title="KI-Bewertung">
          <div className="mb-1">
            Risiko:{" "}
            <span className={`font-semibold ${RISK_CLASS[feature.assessment.risk]}`}>
              {feature.assessment.risk}
            </span>{" "}
            <span className="text-gray-500">
              ({(feature.assessment.confidence * 100).toFixed(0)}%, {feature.assessment.provider})
            </span>
          </div>
          <p className="text-gray-300">{feature.assessment.rationale}</p>
        </Section>
      )}

      <Section title={`Evidenzen (${feature.evidence.length})`}>
        <ul className="space-y-2">
          {feature.evidence.map((e) => (
            <li key={e.id} className="rounded bg-black/30 p-2">
              <div className="text-xs font-medium text-gray-300">{e.kind}</div>
              <div className="text-xs text-gray-400">{e.description}</div>
              <div className="mt-1 font-mono text-[11px] text-gray-500">
                {Object.entries(e.values)
                  .map(([k, v]) => `${k}=${fmt(v)}`)
                  .join("  ")}
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Kommentar">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => draft !== feature.user_comment && comment(feature.id, draft)}
          rows={3}
          className="w-full rounded border border-edge bg-black/40 p-2 text-gray-200 outline-none focus:border-amber-500"
          placeholder="Anmerkung zur Entscheidung…"
        />
      </Section>

      <div className="mt-auto flex gap-2 pt-3">
        <DecisionButton
          active={feature.user_decision === "accept"}
          onClick={() => decide(feature.id, "accept")}
          className="bg-emerald-700 hover:bg-emerald-600"
        >
          Beibehalten (a)
        </DecisionButton>
        <DecisionButton
          active={feature.user_decision === "reject"}
          onClick={() => decide(feature.id, "reject")}
          className="bg-rose-700 hover:bg-rose-600"
        >
          Verwerfen (r)
        </DecisionButton>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-4">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {title}
      </div>
      {children}
    </div>
  );
}

function DecisionButton({
  active,
  onClick,
  className,
  children,
}: {
  active: boolean;
  onClick: () => void;
  className: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 rounded px-3 py-2 text-sm font-medium text-white transition ${className} ${
        active ? "ring-2 ring-white/70" : "opacity-80"
      }`}
    >
      {children}
    </button>
  );
}

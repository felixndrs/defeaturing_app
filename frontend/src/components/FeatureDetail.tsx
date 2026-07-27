import { useEffect, useState } from "react";
import { useT } from "../i18n";
import { useReview } from "../store";
import type { FeatureChange } from "../types";

const RISK_CLASS: Record<string, string> = {
  low: "text-emerald-300",
  medium: "text-amber-300",
  high: "text-rose-300",
};

export function FeatureDetail({ feature }: { feature: FeatureChange }) {
  const decide = useReview((s) => s.decide);
  const comment = useReview((s) => s.comment);
  const [draft, setDraft] = useState(feature.user_comment);
  const { t, featureType, risk, parameter, evidenceKind, evidenceDescription, paramValue, prose } =
    useT();

  useEffect(() => setDraft(feature.user_comment), [feature.id, feature.user_comment]);

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4 text-sm">
      <h2 className="text-lg font-semibold text-gray-100">{featureType(feature.type)}</h2>
      <div className="mt-1 text-xs text-gray-500">
        {t("detail.detectedBy")} {feature.detector} · {t("detail.confidence")}{" "}
        {(feature.confidence * 100).toFixed(0)}%
      </div>

      <Section title={t("detail.parameters")}>
        <dl className="grid grid-cols-2 gap-x-3 gap-y-1">
          {Object.entries(feature.parameters).map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-gray-400">{parameter(k)}</dt>
              <dd className="text-gray-200">{paramValue(k, v)}</dd>
            </div>
          ))}
        </dl>
      </Section>

      {feature.assessment && (
        <Section title={t("detail.assessment")}>
          <div>
            {t("detail.risk")}:{" "}
            <span className={`font-semibold ${RISK_CLASS[feature.assessment.risk]}`}>
              {risk(feature.assessment.risk)}
            </span>
          </div>
          {/* Spells out which risk is meant -- the reading the report uses too. */}
          <div className="mb-1.5 text-[11px] text-gray-500">{t("detail.riskHint")}</div>
          <p className="text-gray-300">
            {prose(feature.assessment.rationale, feature.assessment.rationale_en)}
          </p>
        </Section>
      )}

      <Section title={`${t("detail.evidence")} (${feature.evidence.length})`}>
        <ul className="space-y-2">
          {feature.evidence.map((e) => (
            <li key={e.id} className="rounded bg-black/30 p-2">
              <div className="text-xs font-medium text-gray-300">{evidenceKind(e.kind)}</div>
              <div className="text-xs text-gray-400">
                {evidenceDescription(e.kind, e.description)}
              </div>
              <div className="mt-1 font-mono text-[11px] text-gray-500">
                {Object.entries(e.values)
                  .map(([k, v]) => `${parameter(k)}=${paramValue(k, v)}`)
                  .join("  ")}
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={t("detail.comment")}>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => draft !== feature.user_comment && comment(feature.id, draft)}
          rows={3}
          className="w-full rounded border border-edge bg-black/40 p-2 text-gray-200 outline-none focus:border-amber-500"
          placeholder={t("detail.commentPlaceholder")}
        />
      </Section>

      <div className="mt-auto flex gap-2 pt-3">
        <DecisionButton
          active={feature.user_decision === "accept"}
          onClick={() => decide(feature.id, "accept")}
          className="bg-emerald-700 hover:bg-emerald-600"
        >
          {t("detail.keep")}
        </DecisionButton>
        <DecisionButton
          active={feature.user_decision === "reject"}
          onClick={() => decide(feature.id, "reject")}
          className="bg-rose-700 hover:bg-rose-600"
        >
          {t("detail.discard")}
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

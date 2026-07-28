import { useState } from "react";
import { downloadReport, reportBundleUrl, reportPdfUrl } from "../api";
import { useT } from "../i18n";

type Kind = "pdf" | "bundle";

/**
 * PDF / HTML download buttons with a busy state.
 *
 * The PDF is rendered on demand -- one offscreen screenshot per feature -- so it
 * can take several seconds. The button shows a spinner for as long as that runs
 * and reports a failure inline instead of silently doing nothing.
 */
export function ReportActions({ runId, projectName }: { runId: string; projectName: string }) {
  const { t } = useT();
  return (
    <div className="border-b border-edge px-3 py-2">
      <ReportDownloadButtons runId={runId} projectName={projectName} label={t("report.section")} />
    </div>
  );
}

/**
 * The two download buttons with their busy/failure state, without any chrome --
 * used both in the sidebar and in the "new project" confirmation, so leaving
 * the review always offers the same way to take the result along.
 */
export function ReportDownloadButtons({
  runId,
  projectName,
  label,
}: {
  runId: string;
  projectName: string;
  label?: string;
}) {
  const { t, lang } = useT();
  const [busy, setBusy] = useState<Kind | null>(null);
  const [failed, setFailed] = useState(false);

  async function run(kind: Kind) {
    if (busy) return;
    setBusy(kind);
    setFailed(false);
    const slug = projectName.trim().replace(/\s+/g, "_") || "review";
    try {
      if (kind === "pdf") {
        await downloadReport(reportPdfUrl(runId, lang), `defeaturing_review_${slug}.pdf`);
      } else {
        await downloadReport(reportBundleUrl(runId), `defeaturing_review_${slug}.zip`);
      }
    } catch {
      setFailed(true);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <div className="flex items-center gap-2">
        {label && (
          <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            {label}
          </span>
        )}
        <div className="ml-auto flex gap-1.5">
          <ReportButton busy={busy === "pdf"} disabled={busy !== null} onClick={() => run("pdf")}>
            {t("report.pdf")}
          </ReportButton>
          <ReportButton
            busy={busy === "bundle"}
            disabled={busy !== null}
            onClick={() => run("bundle")}
          >
            {t("report.bundle")}
          </ReportButton>
        </div>
      </div>
      {busy && (
        <div className="mt-1.5 text-right text-[11px] text-gray-500">
          {t(busy === "pdf" ? "report.pdf" : "report.bundle")} {t("report.building")}
        </div>
      )}
      {failed && <div className="mt-1.5 text-[11px] text-rose-400">{t("report.failed")}</div>}
    </div>
  );
}

function ReportButton({
  busy,
  disabled,
  onClick,
  children,
}: {
  busy: boolean;
  disabled: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex items-center gap-1.5 rounded-md bg-edge px-2.5 py-1 text-xs text-gray-200 transition hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {busy && <Spinner />}
      {children}
    </button>
  );
}

function Spinner() {
  return (
    <svg className="h-3 w-3 animate-spin text-amber-400" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2.5" />
      <path
        d="M8 1.5a6.5 6.5 0 0 1 6.5 6.5"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

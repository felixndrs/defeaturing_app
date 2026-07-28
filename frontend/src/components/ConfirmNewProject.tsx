import { useEffect, useState } from "react";
import { useT } from "../i18n";
import { ReportDownloadButtons } from "./ReportActions";

/**
 * Asked before a review is left for a fresh upload.
 *
 * Nothing is actually lost -- every decision is PATCHed to the backend as it is
 * made -- but the way *back* is the `?run=<id>` deep link, which the review
 * screen never shows anywhere. So this dialog is less a "save?" prompt than the
 * one place that hands the link over, plus the report downloads, before the
 * screen is cleared.
 */
export function ConfirmNewProject({
  runId,
  projectName,
  undecided,
  total,
  onCancel,
  onConfirm,
}: {
  runId: string;
  projectName: string;
  undecided: number;
  total: number;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const { t } = useT();
  const [copied, setCopied] = useState(false);
  const link = `${window.location.origin}${window.location.pathname}?run=${runId}`;

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard denied (no https, no permission): the link stays selectable
      // in the input next to the button, which is the fallback anyway.
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-lg rounded-lg border border-edge bg-panel p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-sm font-semibold text-gray-100">{t("confirmNew.title")}</h2>

        {undecided > 0 && (
          <p className="mt-2 text-xs text-amber-400">
            {t("confirmNew.undecided")
              .replace("{n}", String(undecided))
              .replace("{total}", String(total))}
          </p>
        )}

        <p className="mt-3 text-xs text-gray-400">{t("confirmNew.saved")}</p>
        <div className="mt-2 flex gap-2">
          <input
            readOnly
            value={link}
            onFocus={(e) => e.currentTarget.select()}
            className="min-w-0 flex-1 rounded-md border border-edge bg-black/30 px-2 py-1 text-xs text-gray-300"
          />
          <button
            onClick={copy}
            className="shrink-0 rounded-md bg-edge px-2.5 py-1 text-xs text-gray-200 transition hover:bg-gray-700"
          >
            {copied ? t("confirmNew.copied") : t("confirmNew.copy")}
          </button>
        </div>

        <p className="mt-4 text-xs text-gray-400">{t("confirmNew.report")}</p>
        <div className="mt-2">
          <ReportDownloadButtons runId={runId} projectName={projectName} />
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-md border border-edge px-3 py-1.5 text-sm text-gray-300 transition hover:bg-edge"
          >
            {t("app.cancel")}
          </button>
          <button
            onClick={onConfirm}
            className="rounded-md bg-amber-500 px-3 py-1.5 text-sm font-medium text-gray-900 transition hover:bg-amber-400"
          >
            {t("confirmNew.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}

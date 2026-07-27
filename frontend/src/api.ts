import type { AnalysisRun, FeatureChange, ProjectDetail, UserDecision } from "./types";

// All requests go through the Vite dev proxy (/api -> backend). In a production
// build, VITE_API_BASE can point at the backend origin directly.
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function createProject(
  name: string,
  original: File,
  defeatured: File,
): Promise<ProjectDetail> {
  const form = new FormData();
  form.append("name", name);
  form.append("original", original);
  form.append("defeatured", defeatured);
  return json(await fetch(`${BASE}/projects`, { method: "POST", body: form }));
}

export async function startAnalysis(projectId: string): Promise<{ id: string }> {
  return json(
    await fetch(`${BASE}/analysis`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ project_id: projectId }),
    }),
  );
}

export async function getRun(runId: string): Promise<AnalysisRun> {
  return json(await fetch(`${BASE}/analysis/${runId}`));
}

export async function getProject(projectId: string): Promise<ProjectDetail> {
  return json(await fetch(`${BASE}/projects/${projectId}`));
}

export async function patchFeature(
  runId: string,
  featureId: string,
  update: { user_decision?: UserDecision; user_comment?: string },
): Promise<FeatureChange> {
  return json(
    await fetch(`${BASE}/analysis/${runId}/features/${featureId}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(update),
    }),
  );
}

export function geometryUrl(modelId: string): string {
  return `${BASE}/geometry/${modelId}.glb`;
}

export function reportPdfUrl(runId: string, lang: string): string {
  return `${BASE}/report/${runId}/pdf?lang=${lang}`;
}

export function reportBundleUrl(runId: string): string {
  return `${BASE}/report/${runId}/bundle`;
}

/**
 * Fetch a generated report and hand it to the browser as a download.
 *
 * A plain `<a download>` cannot show progress: the PDF takes seconds to build
 * (one offscreen render per feature) and the click would look like it did
 * nothing. Fetching it ourselves lets the caller show a spinner and surface a
 * failure instead of navigating away to an error page.
 */
export async function downloadReport(url: string, fallbackName: string): Promise<void> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  try {
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filenameFrom(res.headers.get("content-disposition")) ?? fallbackName;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    // Revoking immediately can cancel the download in some browsers; one turn
    // of the event loop is enough for the click to have been picked up.
    setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000);
  }
}

function filenameFrom(header: string | null): string | null {
  if (!header) return null;
  const encoded = /filename\*=utf-8''([^;]+)/i.exec(header);
  if (encoded) return decodeURIComponent(encoded[1]);
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1] : null;
}

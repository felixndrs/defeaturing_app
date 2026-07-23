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

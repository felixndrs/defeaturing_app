// Mirrors the backend domain model (app/domain/models.py). Kept minimal to what
// the UI needs; the backend remains the source of truth.

export type Vec3 = [number, number, number];

export interface BBox {
  min: Vec3;
  max: Vec3;
}

export interface ModelSummary {
  id: string;
  role: "original" | "defeatured";
  source_file: string;
  source_format: string;
  solid_count: number;
  face_count: number;
  edge_count: number;
  volume: number;
  area: number;
}

export interface ProjectDetail {
  id: string;
  name: string;
  original: ModelSummary | null;
  defeatured: ModelSummary | null;
}

export interface Evidence {
  id: string;
  kind: string;
  description: string;
  values: Record<string, unknown>;
  source_stage: string;
}

export interface Assessment {
  rationale: string;
  risk: "low" | "medium" | "high";
  confidence: number;
  cited_evidence_ids: string[];
  provider: string;
  model?: string | null;
}

export interface GeometryRefs {
  original_face_ids: string[];
  defeatured_face_ids: string[];
}

export type UserDecision = "undecided" | "accept" | "reject";

export interface FeatureChange {
  id: string;
  type: string;
  status: string;
  detector: string;
  parameters: Record<string, unknown>;
  evidence: Evidence[];
  confidence: number;
  geometry_refs: GeometryRefs;
  bbox: BBox | null;
  centroid: Vec3 | null;
  assessment: Assessment | null;
  user_decision: UserDecision;
  user_comment: string;
}

export interface RunStatistics {
  original_face_count: number;
  defeatured_face_count: number;
  paired_face_count: number;
  unpaired_original_face_count: number;
  unpaired_defeatured_face_count: number;
  volume_original: number;
  volume_defeatured: number;
  feature_counts: Record<string, number>;
  unknown_count: number;
}

export interface AnalysisRun {
  id: string;
  project_id: string;
  status: "pending" | "running" | "done" | "failed";
  progress: number;
  stages: { name: string; status: string; duration_s: number | null }[];
  features: FeatureChange[];
  statistics: RunStatistics;
  llm_summary: string;
  error: string;
}

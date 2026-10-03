// The only file that knows backend URLs.
import type { DatasetInfo, Draft, EvalReport, FindingDetail, FindingRow, Graph, Health, Liability, MatchDetail, MatchRow, RunInfo, Summary } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers: { "content-type": "application/json", ...init?.headers } });
  } catch {
    throw new ApiError(0, "offline", "Cannot reach the LedgerLens server. Check that the backend is running.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.error?.code ?? "error", body?.error?.message ?? `Request failed (${response.status})`);
  }
  return response.json();
}

const post = <T,>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });

function query(params: Record<string, string | number | undefined | null>): string {
  const pairs = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return pairs.length ? "?" + pairs.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&") : "";
}

export const api = {
  health: () => request<Health>("/api/health"),
  loadDemo: () => post<DatasetInfo>("/api/demo/load"),
  latest: (period?: string) => request<{ run: RunInfo | null; dataset: DatasetInfo | null }>(`/api/runs/latest${query({ period })}`),
  startRun: (dataset_id: string, period: string) => post<{ run_id: string; status: string }>("/api/runs", { dataset_id, period }),
  run: (runId: string) => request<RunInfo>(`/api/runs/${runId}`),
  eventsUrl: (runId: string) => `${API_URL}/api/runs/${runId}/events`,
  summary: (runId: string) => request<Summary>(`/api/runs/${runId}/summary`),
  findings: (runId: string, filters: Record<string, string | number | undefined> = {}) =>
    request<{ items: FindingRow[]; total: number }>(`/api/runs/${runId}/findings${query(filters)}`),
  finding: (id: string) => request<FindingDetail>(`/api/findings/${id}`),
  matches: (runId: string, filters: Record<string, string | number | undefined> = {}) =>
    request<{ items: MatchRow[]; total: number }>(`/api/runs/${runId}/matches${query(filters)}`),
  match: (id: string) => request<MatchDetail>(`/api/matches/${id}`),
  draft: (findingId: string) => post<Draft>(`/api/findings/${findingId}/draft`),
  editDraft: (draftId: string, body: string) => request<Draft>(`/api/drafts/${draftId}`, { method: "PATCH", body: JSON.stringify({ body }) }),
  approve: (draftId: string) => post<{ draft: Draft; finding: FindingRow; summary: Summary }>(`/api/drafts/${draftId}/approve`),
  dismiss: (findingId: string, note: string) => post<{ finding: FindingRow; summary: Summary }>(`/api/findings/${findingId}/dismiss`, { note }),
  liability: (runId: string) => request<Liability>(`/api/runs/${runId}/liability`),
  graph: (runId: string) => request<Graph>(`/api/runs/${runId}/graph`),
  evalReport: () => request<EvalReport>("/api/eval"),
};

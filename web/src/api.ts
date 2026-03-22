import type { AnalyzeRequest, AnalyzeResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8787";

export async function analyze(request: AnalyzeRequest): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Analysis failed");
  }
  return res.json();
}

export async function getRecent(): Promise<AnalyzeResponse[]> {
  const res = await fetch(`${API_BASE}/api/recent`);
  if (!res.ok) return [];
  return res.json();
}

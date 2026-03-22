import type { AnalyzeRequest, AnalyzeResponse, SearchRequest, SearchResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function search(request: SearchRequest): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Search failed");
  }
  return res.json();
}

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

export async function geocode(query: string): Promise<{ lat: number; lng: number; name: string }> {
  const res = await fetch(`${API_BASE}/api/geocode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "場所が見つかりませんでした");
  }
  return res.json();
}

export async function reverseGeocode(lat: number, lng: number): Promise<string> {
  const res = await fetch(`${API_BASE}/api/reverse-geocode?lat=${lat}&lng=${lng}`);
  if (!res.ok) return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  const data = await res.json();
  return data.name;
}

export async function getRecent(): Promise<AnalyzeResponse[]> {
  const res = await fetch(`${API_BASE}/api/recent`);
  if (!res.ok) return [];
  return res.json();
}

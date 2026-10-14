import type { AnalyzeResponse, AppConfig, Place } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function readError(res: Response): Promise<string> {
  let data: Record<string, unknown> = {};
  try {
    data = await res.json();
  } catch {
  }
  if (res.status === 429) {
    const wait = data.retry_after ? ` Try again in ${data.retry_after}s.` : "";
    return String(data.detail || "Rate limit exceeded.") + wait;
  }
  if (typeof data.detail === "string") return data.detail;
  const parts: string[] = [];
  for (const [key, val] of Object.entries(data)) {
    if (key === "detail") continue;
    if (Array.isArray(val)) parts.push(`${key}: ${val.join(" ")}`);
    else if (typeof val === "string") parts.push(`${key}: ${val}`);
  }
  if (parts.length) return parts.join(" ");
  return `Request failed (${res.status})`;
}

export async function fetchAppConfig(): Promise<AppConfig> {
  const res = await fetch(`${API_BASE}/config/`);
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as AppConfig;
}

export async function geocode(q: string): Promise<Place[]> {
  const url = `${API_BASE}/geocode/?q=${encodeURIComponent(q)}`;
  const res = await fetch(url);
  if (!res.ok) {
    if (res.status === 429) return [];
    throw new Error(await readError(res));
  }
  const data = await res.json();
  return data.results as Place[];
}

export async function analyzeRoutes(payload: {
  origin: string | Place;
  destination: string | Place;
  departure_at: string;
  load_lbs: number;
}): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/routes/analyze/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as AnalyzeResponse;
}

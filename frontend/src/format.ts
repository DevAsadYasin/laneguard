import type { Checkpoint, RiskLevel, RouteResult } from "./types";
import { RISK_COLORS } from "./riskColors";

const LABEL_MAP: Record<string, string> = {
  hgv_recommended: "Recommended lane",
  hgv_shortest: "Shortest legal",
  hgv_avoid_tollways: "Avoid tollways",
  hgv_alternative: "Alt. truck route",
  recommended: "Recommended",
  shortest: "Shortest",
  avoid_tollways: "Avoid tollways",
  alternative: "Alternative",
};

export function formatRouteLabel(raw?: string): string {
  if (!raw) return "Route";
  const key = raw.replace(/^route-\d+$/i, "").trim() || raw;
  if (LABEL_MAP[key]) return LABEL_MAP[key];
  if (LABEL_MAP[raw]) return LABEL_MAP[raw];
  return raw
    .replace(/^hgv_/i, "")
    .replace(/^route-/i, "Route ")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (h <= 0) return `${m}m`;
  return `${h}h ${m}m`;
}

export function formatEta(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function formatRain(inHr: number): string {
  if (inHr < 0.005) return "dry";
  return `${inHr.toFixed(2)} in/hr`;
}

export function formatSnow(inHr: number): string {
  if (inHr < 0.05) return "none";
  return `${inHr.toFixed(1)} in/hr`;
}

export function worstCheckpoint(route: RouteResult): Checkpoint | null {
  if (!route.checkpoints.length) return null;
  return route.checkpoints.reduce((a, b) => (b.risk.score > a.risk.score ? b : a));
}

export function riskTone(level: RiskLevel): string {
  return RISK_COLORS[level];
}

export function weatherOutlook(route: RouteResult): string {
  const worst = worstCheckpoint(route);
  if (!worst) return "No checkpoints";
  const { no_travel_miles, severe_miles, high_miles, avg_risk } = route.summary;
  if (no_travel_miles > 0) {
    return `No-travel conditions on ${no_travel_miles.toFixed(0)} mi`;
  }
  if (severe_miles > 0) {
    return `Severe weather on ${severe_miles.toFixed(0)} mi · peak ${worst.risk.level}`;
  }
  if (high_miles > 0) {
    return `High risk on ${high_miles.toFixed(0)} mi · peak ${worst.risk.level}`;
  }
  if (avg_risk < 0.5) {
    return `Calm corridor · peak ${worst.risk.level} (wind ${worst.weather.wind_mph} mph)`;
  }
  return `Peak ${worst.risk.level} · avg risk ${avg_risk.toFixed(2)}`;
}

export function departurePlusHours(departureIso: string, hour: number): string {
  try {
    const d = new Date(departureIso);
    d.setHours(d.getHours() + hour);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return `+${hour}h`;
  }
}

export function routeArrival(route: RouteResult): string {
  const last = route.checkpoints[route.checkpoints.length - 1];
  return last ? formatEta(last.eta) : "—";
}

export function peakRiskLabel(route: RouteResult): RiskLevel {
  const worst = worstCheckpoint(route);
  return (worst?.risk.level as RiskLevel) || "Low";
}

export function maxWindMph(route: RouteResult): number {
  if (!route.checkpoints.length) return 0;
  return Math.max(...route.checkpoints.map((c) => c.weather.wind_mph));
}

export function riskChipClass(level: RiskLevel): string {
  return `risk-chip risk-chip-${level.toLowerCase().replace(/\s+/g, "-")}`;
}

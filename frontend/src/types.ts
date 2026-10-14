export type RiskLevel = "Low" | "Moderate" | "High" | "Severe" | "No Travel";

export interface Place {
  label: string;
  lat: number;
  lng: number;
}

export interface Checkpoint {
  lat: number;
  lng: number;
  mile: number;
  eta: string;
  eta_offset_seconds: number;
  weather: {
    wind_mph: number;
    rain_in_hr: number;
    snow_in_hr: number;
    matched_time: string | null;
    forecast_unavailable: boolean;
  };
  risk: {
    level: RiskLevel;
    score: number;
    components: Record<string, string>;
    warning?: string;
  };
}

export interface RouteSummary {
  id: string;
  no_travel_miles: number;
  severe_miles: number;
  high_miles: number;
  avg_risk: number;
  travel_time_seconds: number;
  distance_miles: number;
  sample_interval_miles: number;
}

export interface RouteResult {
  id: string;
  label?: string;
  geometry: { lat: number; lng: number }[];
  checkpoints: Checkpoint[];
  summary: RouteSummary & { label?: string };
}

export interface HeatPoint {
  lat: number;
  lng: number;
  intensity: number;
}

export interface AnalyzeResponse {
  origin: Place;
  destination: Place;
  departure_at: string;
  load_lbs: number;
  sample_interval_miles: number;
  routing_profile: string;
  routes: RouteResult[];
  recommended_route_id: string;
  recommendation_order: string[];
  heatmap_by_hour: HeatPoint[][];
  heatmap_hours: number;
  departure_max_hours_ahead?: number;
  weather_forecast_days?: number;
}

export interface AppConfig {
  departure_max_hours_ahead: number;
  departure_past_grace_minutes: number;
  heatmap_hours: number;
  weather_forecast_days: number;
  departure_guidance: string;
}

import { Fragment, useEffect, useMemo } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import type { AnalyzeResponse, RiskLevel } from "../types";
import { RISK_COLORS, ROUTE_PALETTE } from "../riskColors";
import {
  departurePlusHours,
  formatDuration,
  formatEta,
  formatRain,
  formatRouteLabel,
  formatSnow,
  maxWindMph,
  peakRiskLabel,
  routeArrival,
  weatherOutlook,
} from "../format";
import { HeatLayer } from "./HeatLayer";
import "leaflet/dist/leaflet.css";

interface Props {
  data: AnalyzeResponse;
  selectedRouteId: string;
  onSelectRoute: (id: string) => void;
  heatHour: number;
  showHeatmap: boolean;
}

function FitBounds({ data }: { data: AnalyzeResponse }) {
  const map = useMap();
  useEffect(() => {
    const pts = data.routes.flatMap((r) => r.geometry);
    if (!pts.length) return;
    const bounds = pts.map((p) => [p.lat, p.lng] as [number, number]);
    map.fitBounds(bounds, { padding: [48, 48] });
  }, [data, map]);
  return null;
}

function midPoint(geometry: { lat: number; lng: number }[]) {
  if (!geometry.length) return { lat: 0, lng: 0 };
  return geometry[Math.floor(geometry.length / 2)];
}

function endpointIcon(label: string, kind: "origin" | "dest") {
  const bg = kind === "origin" ? "#3d8bfd" : "#f0a202";
  return L.divIcon({
    className: "endpoint-icon",
    html: `<div style="background:${bg};color:#0b0f14;font:700 11px/1 'IBM Plex Sans',sans-serif;padding:4px 7px;border-radius:4px;border:1px solid #fff;white-space:nowrap">${label}</div>`,
    iconSize: [40, 20],
    iconAnchor: [20, 10],
  });
}

export function RouteMap({
  data,
  selectedRouteId,
  onSelectRoute,
  heatHour,
  showHeatmap,
}: Props) {
  const heatPoints = useMemo(
    () => data.heatmap_by_hour[Math.min(heatHour, data.heatmap_by_hour.length - 1)] ?? [],
    [data, heatHour],
  );

  const selected = data.routes.find((r) => r.id === selectedRouteId) ?? data.routes[0];
  const center = data.origin;

  return (
    <div className="map-shell">
      <MapContainer
        center={[center.lat, center.lng]}
        zoom={6}
        className="map-canvas"
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <FitBounds data={data} />
        <HeatLayer points={heatPoints} visible={showHeatmap} />

        <Marker
          position={[data.origin.lat, data.origin.lng]}
          icon={endpointIcon("A", "origin")}
        >
          <Popup>
            <div className="map-popup">
              <strong>Origin</strong>
              <div>{data.origin.label}</div>
            </div>
          </Popup>
        </Marker>
        <Marker
          position={[data.destination.lat, data.destination.lng]}
          icon={endpointIcon("B", "dest")}
        >
          <Popup>
            <div className="map-popup">
              <strong>Destination</strong>
              <div>{data.destination.label}</div>
            </div>
          </Popup>
        </Marker>

        {data.routes.map((route, idx) => {
          const isSelected = route.id === selectedRouteId;
          const recommended = route.id === data.recommended_route_id;
          const color = ROUTE_PALETTE[idx % ROUTE_PALETTE.length];
          const mid = midPoint(route.geometry);
          return (
            <Fragment key={route.id}>
              <Polyline
                positions={route.geometry.map((p) => [p.lat, p.lng] as [number, number])}
                pathOptions={{
                  color,
                  weight: isSelected ? 7 : recommended ? 5 : 3.5,
                  opacity: isSelected ? 0.98 : recommended ? 0.75 : 0.4,
                  dashArray: recommended || isSelected ? undefined : "7 9",
                }}
                eventHandlers={{ click: () => onSelectRoute(route.id) }}
              />
              <CircleMarker
                center={[mid.lat, mid.lng]}
                radius={isSelected ? 9 : 6}
                pathOptions={{
                  color: "#fff",
                  weight: 2,
                  fillColor: color,
                  fillOpacity: 0.95,
                }}
                eventHandlers={{ click: () => onSelectRoute(route.id) }}
              >
                <Popup>
                  <div className="map-popup">
                    <strong>
                      {formatRouteLabel(route.label || route.id)}
                      {recommended ? " · Best" : ""}
                    </strong>
                    <div>
                      {route.summary.distance_miles.toFixed(0)} mi ·{" "}
                      {formatDuration(route.summary.travel_time_seconds)}
                    </div>
                    <div className="popup-outlook">{weatherOutlook(route)}</div>
                    <div className="popup-grid">
                      <span>No travel</span>
                      <span>{route.summary.no_travel_miles.toFixed(0)} mi</span>
                      <span>Severe</span>
                      <span>{route.summary.severe_miles.toFixed(0)} mi</span>
                      <span>High</span>
                      <span>{route.summary.high_miles.toFixed(0)} mi</span>
                      <span>Avg risk</span>
                      <span>{route.summary.avg_risk.toFixed(2)}</span>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            </Fragment>
          );
        })}

        {!showHeatmap &&
          selected?.checkpoints.map((cp, i) => (
            <CircleMarker
              key={`sel-cp-${i}`}
              center={[cp.lat, cp.lng]}
              radius={i === 0 || i === selected.checkpoints.length - 1 ? 7 : 5}
              pathOptions={{
                color: "#0b0f14",
                weight: 1.5,
                fillColor: RISK_COLORS[cp.risk.level as RiskLevel],
                fillOpacity: 0.95,
              }}
            >
              <Popup>
                <div className="map-popup">
                  <strong>
                    Mile {cp.mile.toFixed(0)} ·{" "}
                    <span style={{ color: RISK_COLORS[cp.risk.level as RiskLevel] }}>
                      {cp.risk.level}
                    </span>
                  </strong>
                  <div>ETA {formatEta(cp.eta)}</div>
                  <div className="popup-grid">
                    <span>Wind</span>
                    <span>{cp.weather.wind_mph.toFixed(0)} mph</span>
                    <span>Rain</span>
                    <span>{formatRain(cp.weather.rain_in_hr)}</span>
                    <span>Snow</span>
                    <span>{formatSnow(cp.weather.snow_in_hr)}</span>
                  </div>
                  {cp.weather.forecast_unavailable && (
                    <div className="popup-warn">Forecast unavailable at this ETA</div>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>

      <div className="map-summaries">
        {data.routes.map((route, idx) => {
          const recommended = route.id === data.recommended_route_id;
          const isSelected = route.id === selectedRouteId;
          const peak = peakRiskLabel(route);
          return (
            <button
              key={route.id}
              type="button"
              className={`map-summary-card ${isSelected ? "selected" : ""} ${recommended ? "recommended" : ""}`}
              style={{ borderColor: ROUTE_PALETTE[idx % ROUTE_PALETTE.length] }}
              onClick={() => onSelectRoute(route.id)}
            >
              <div className="card-title">
                <span>{formatRouteLabel(route.label || route.id)}</span>
                {recommended && <em>Best</em>}
              </div>
              <div className="card-metrics">
                <span>{route.summary.distance_miles.toFixed(0)} mi</span>
                <span>{formatDuration(route.summary.travel_time_seconds)}</span>
                <span>peak {peak}</span>
              </div>
              <div className="card-metrics card-metrics-2">
                <span>Arrive {routeArrival(route)}</span>
                <span>Wind {maxWindMph(route).toFixed(0)} mph</span>
              </div>
              <div className="card-risk">{weatherOutlook(route)}</div>
            </button>
          );
        })}
      </div>

      {showHeatmap && (
        <div className="map-heat-chip">
          Heatmap · departure +{heatHour}h
          <span>{departurePlusHours(data.departure_at, heatHour)}</span>
        </div>
      )}

      <div className="map-legend-chip">
        {(Object.keys(RISK_COLORS) as RiskLevel[]).map((level) => (
          <span key={level}>
            <i style={{ background: RISK_COLORS[level] }} />
            {level}
          </span>
        ))}
      </div>
    </div>
  );
}

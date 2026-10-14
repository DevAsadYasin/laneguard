import type { AnalyzeResponse, Checkpoint, RiskLevel, RouteResult } from "../types";
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
  riskChipClass,
  routeArrival,
  weatherOutlook,
  worstCheckpoint,
} from "../format";

interface Props {
  data: AnalyzeResponse;
  selectedRouteId: string;
  expandedRouteId: string;
  onSelectRoute: (id: string) => void;
  heatHour: number;
  onHeatHour: (h: number) => void;
  showHeatmap: boolean;
  onToggleHeatmap: (v: boolean) => void;
}

function CheckpointRows({ checkpoints }: { checkpoints: Checkpoint[] }) {
  return (
    <ul className="cp-expand-list">
      {checkpoints.map((cp, i) => (
        <li key={i} className={`cp-row risk-${cp.risk.score}`}>
          <span
            className="risk-dot"
            style={{ background: RISK_COLORS[cp.risk.level as RiskLevel] }}
          />
          <div className="cp-body">
            <div className="cp-top">
              <strong>
                Mile {cp.mile.toFixed(0)} · {cp.risk.level}
              </strong>
              <span className="cp-eta">{formatEta(cp.eta)}</span>
            </div>
            <div className="cp-weather">
              <span>Wind {cp.weather.wind_mph.toFixed(0)} mph</span>
              <span>Rain {formatRain(cp.weather.rain_in_hr)}</span>
              <span>Snow {formatSnow(cp.weather.snow_in_hr)}</span>
            </div>
            {cp.weather.forecast_unavailable && (
              <div className="cp-warn">Forecast gap at this ETA</div>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

function RouteCard({
  route,
  idx,
  recommended,
  expanded,
  onToggle,
}: {
  route: RouteResult;
  idx: number;
  recommended: boolean;
  expanded: boolean;
  onToggle: () => void;
}) {
  const peak = peakRiskLabel(route);
  const worst = worstCheckpoint(route);
  const color = ROUTE_PALETTE[idx % ROUTE_PALETTE.length];

  return (
    <article
      className={`route-card ${expanded ? "expanded" : ""} ${recommended ? "is-rec" : ""}`}
      style={{ ["--card-accent" as string]: color }}
    >
      <button type="button" className="route-card-summary" onClick={onToggle}>
        <div className="route-card-head">
          <span className="route-swatch" style={{ background: color }} />
          <div className="route-card-titles">
            <strong>{formatRouteLabel(route.label || route.id)}</strong>
            <span className="route-card-sub">{weatherOutlook(route)}</span>
          </div>
          <div className="route-card-head-right">
            {recommended && <span className="badge">Best</span>}
            <span className="expand-chevron" aria-hidden>
              {expanded ? "▾" : "▸"}
            </span>
          </div>
        </div>

        <div className="stat-grid">
          <div className="stat">
            <span className="stat-label">Distance</span>
            <strong>{route.summary.distance_miles.toFixed(0)} mi</strong>
          </div>
          <div className="stat">
            <span className="stat-label">Drive time</span>
            <strong>{formatDuration(route.summary.travel_time_seconds)}</strong>
          </div>
          <div className="stat">
            <span className="stat-label">Arrive</span>
            <strong className="stat-arrive">{routeArrival(route)}</strong>
          </div>
          <div className="stat">
            <span className="stat-label">Peak risk</span>
            <strong>
              <span className={riskChipClass(peak)}>{peak}</span>
            </strong>
          </div>
        </div>

        <div className="route-chip-row">
          <span className="mini-chip">
            No travel <b>{route.summary.no_travel_miles.toFixed(0)} mi</b>
          </span>
          <span className="mini-chip">
            Severe <b>{route.summary.severe_miles.toFixed(0)} mi</b>
          </span>
          <span className="mini-chip">
            High <b>{route.summary.high_miles.toFixed(0)} mi</b>
          </span>
          <span className="mini-chip">
            Avg <b>{route.summary.avg_risk.toFixed(2)}</b>
          </span>
          <span className="mini-chip">
            Max wind <b>{maxWindMph(route).toFixed(0)} mph</b>
          </span>
          <span className="mini-chip">
            Samples <b>every {route.summary.sample_interval_miles} mi</b>
          </span>
        </div>

        <div className="route-card-hint">
          {expanded ? "Hide checkpoint weather" : "Show full weather & checkpoints"}
        </div>
      </button>

      {expanded && (
        <div className="route-card-details">
          <div className="detail-block">
            <h4>Why this lane</h4>
            <p>{weatherOutlook(route)}</p>
            <div className="detail-kv">
              <span>Risk miles</span>
              <span>
                NT {route.summary.no_travel_miles.toFixed(1)} · Sev{" "}
                {route.summary.severe_miles.toFixed(1)} · Hi{" "}
                {route.summary.high_miles.toFixed(1)}
              </span>
              <span>Average risk</span>
              <span>{route.summary.avg_risk.toFixed(2)} / 4</span>
              <span>Checkpoints</span>
              <span>{route.checkpoints.length} along the corridor</span>
            </div>
          </div>

          {worst && (
            <div className="detail-block">
              <h4>Peak weather stop</h4>
              <div className="peak-weather">
                <span
                  className="risk-dot lg"
                  style={{ background: RISK_COLORS[worst.risk.level as RiskLevel] }}
                />
                <div>
                  <strong>
                    Mile {worst.mile.toFixed(0)} · {worst.risk.level}
                  </strong>
                  <div className="cp-eta">{formatEta(worst.eta)}</div>
                  <div className="cp-weather">
                    <span>Wind {worst.weather.wind_mph.toFixed(0)} mph</span>
                    <span>Rain {formatRain(worst.weather.rain_in_hr)}</span>
                    <span>Snow {formatSnow(worst.weather.snow_in_hr)}</span>
                  </div>
                  {worst.risk.components && (
                    <div className="component-row">
                      Wind {worst.risk.components.wind} · Rain {worst.risk.components.rain} ·
                      Snow {worst.risk.components.snow}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          <div className="detail-block">
            <h4>Checkpoint weather</h4>
            <p className="checkpoint-sub">
              ETA-based Open-Meteo samples · also on the map pins
            </p>
            <CheckpointRows checkpoints={route.checkpoints} />
          </div>
        </div>
      )}
    </article>
  );
}

export function ResultsPanel({
  data,
  expandedRouteId,
  onSelectRoute,
  heatHour,
  onHeatHour,
  showHeatmap,
  onToggleHeatmap,
}: Props) {
  const recommended = data.routes.find((r) => r.id === data.recommended_route_id);
  const heatMax = data.heatmap_hours ?? 48;

  return (
    <aside className="results">
      <div className="results-head">
        <h2>Lane comparison</h2>
        <p>
          Checkpoints every <strong>{data.sample_interval_miles} mi</strong> ·{" "}
          {data.routing_profile}
        </p>
        <p className="results-head-hint">Tap a card to expand weather checkpoints</p>
      </div>

      {recommended && (
        <div className="rec-banner">
          <div className="rec-banner-label">Safest pick</div>
          <strong>{formatRouteLabel(recommended.label || recommended.id)}</strong>
          <p>{weatherOutlook(recommended)}</p>
          <p className="rec-banner-why">
            Ranked by No Travel → Severe → High → avg risk → travel time
          </p>
        </div>
      )}

      <div className="route-card-list">
        {data.routes.map((route, idx) => (
          <RouteCard
            key={route.id}
            route={route}
            idx={idx}
            recommended={route.id === data.recommended_route_id}
            expanded={route.id === expandedRouteId}
            onToggle={() => onSelectRoute(route.id)}
          />
        ))}
      </div>

      <div className="heat-controls">
        <label className="toggle">
          <input
            type="checkbox"
            checked={showHeatmap}
            onChange={(e) => onToggleHeatmap(e.target.checked)}
          />
          Corridor weather heatmap
        </label>
        <label className="field">
          <span>
            {showHeatmap
              ? `Forecast at departure +${heatHour}h · ${departurePlusHours(data.departure_at, heatHour)}`
              : "Enable heatmap to scrub 0–48h along the corridor"}
          </span>
          <input
            type="range"
            min={0}
            max={heatMax}
            value={Math.min(heatHour, heatMax)}
            onChange={(e) => onHeatHour(Number(e.target.value))}
            disabled={!showHeatmap}
          />
        </label>
        <div className="heat-scale">
          <span>Calm</span>
          <span className="heat-bar" />
          <span>Intense</span>
        </div>
      </div>

      <div className="legend">
        <span className="legend-title">Risk</span>
        {(Object.keys(RISK_COLORS) as RiskLevel[]).map((level) => (
          <span key={level}>
            <i style={{ background: RISK_COLORS[level] }} />
            {level}
          </span>
        ))}
      </div>
    </aside>
  );
}

import { useState } from "react";
import { analyzeRoutes } from "./api";
import { TripForm, type TripFormValues } from "./components/TripForm";
import { RouteMap } from "./components/RouteMap";
import { ResultsPanel } from "./components/ResultsPanel";
import { AnalyzingOverlay } from "./components/AnalyzingOverlay";
import type { AnalyzeResponse } from "./types";
import "./App.css";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState("");
  const [expandedRouteId, setExpandedRouteId] = useState("");
  const [heatHour, setHeatHour] = useState(0);
  const [showHeatmap, setShowHeatmap] = useState(false);

  function handleSelectRoute(id: string) {
    setSelectedRouteId(id);
    setExpandedRouteId((prev) => (prev === id ? "" : id));
  }

  function handleMapSelectRoute(id: string) {
    setSelectedRouteId(id);
    setExpandedRouteId(id);
  }

  async function handleSubmit(values: TripFormValues) {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeRoutes(values);
      setData(result);
      setSelectedRouteId(result.recommended_route_id);
      setExpandedRouteId(result.recommended_route_id);
      setHeatHour(0);
      setShowHeatmap(false);
    } catch (err) {
      setData(null);
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`app ${data ? "has-results" : ""} ${loading ? "is-loading" : ""}`}>
      <div className="sidebar">
        <TripForm loading={loading} onSubmit={handleSubmit} />
        {loading && (
          <div className="sidebar-loading" aria-live="polite">
            <span className="sidebar-loading-dot" />
            Finding your safest path…
          </div>
        )}
        {error && <div className="error">{error}</div>}
        {data && !loading && (
          <ResultsPanel
            data={data}
            selectedRouteId={selectedRouteId}
            expandedRouteId={expandedRouteId}
            onSelectRoute={handleSelectRoute}
            heatHour={heatHour}
            onHeatHour={setHeatHour}
            showHeatmap={showHeatmap}
            onToggleHeatmap={setShowHeatmap}
          />
        )}
      </div>
      <main className="main">
        {loading ? (
          <AnalyzingOverlay active={loading} />
        ) : data ? (
          <RouteMap
            data={data}
            selectedRouteId={selectedRouteId}
            onSelectRoute={handleMapSelectRoute}
            heatHour={heatHour}
            showHeatmap={showHeatmap}
          />
        ) : (
          <div className="empty-map">
            <div className="empty-copy">
              <h2>Pick a lane before the weather picks you</h2>
              <p>
                Enter origin, destination, departure, and load weight to compare three
                routes with ETA-based weather risk.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

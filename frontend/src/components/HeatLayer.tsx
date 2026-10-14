import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";
import type { HeatPoint } from "../types";

declare module "leaflet" {
  function heatLayer(
    latlngs: [number, number, number][],
    options?: Record<string, unknown>,
  ): L.Layer;
}

interface Props {
  points: HeatPoint[];
  visible: boolean;
}

export function HeatLayer({ points, visible }: Props) {
  const map = useMap();

  useEffect(() => {
    if (!visible) return;
    const latlngs: [number, number, number][] = points.map((p) => [
      p.lat,
      p.lng,
      Math.max(0.05, p.intensity),
    ]);
    const layer = L.heatLayer(latlngs, {
      radius: 28,
      blur: 22,
      maxZoom: 10,
      max: 1,
      gradient: {
        0.2: "#74c0fc",
        0.4: "#ffd43b",
        0.65: "#ff922b",
        0.85: "#fa5252",
        1.0: "#862e9c",
      },
    });
    layer.addTo(map);
    return () => {
      map.removeLayer(layer);
    };
  }, [map, points, visible]);

  return null;
}

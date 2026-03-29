"use client";
import { Source, Layer } from "react-map-gl/maplibre";

interface Props {
  data: GeoJSON.FeatureCollection;
}

export default function DangerLayer({ data }: Props) {
  return (
    <Source id="danger-zones" type="geojson" data={data}>
      {/* Filled polygons — severity-based color */}
      <Layer
        id="danger-fill"
        type="fill"
        paint={{
          "fill-color": [
            "match",
            ["get", "severity"],
            "no-damage",    "#22c55e",
            "minor-damage", "#eab308",
            "major-damage", "#f97316",
            "destroyed",    "#ef4444",
            "#ffffff",
          ],
          "fill-opacity": 0.45,
        }}
      />
      {/* Subtle white outline */}
      <Layer
        id="danger-outline"
        type="line"
        paint={{
          "line-color": "#ffffff",
          "line-width": 1,
          "line-opacity": 0.4,
        }}
      />
    </Source>
  );
}

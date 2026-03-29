"use client";
import { Source, Layer } from "react-map-gl/maplibre";

interface Props {
  data: GeoJSON.FeatureCollection;
}

export default function DangerLayer({ data }: Props) {
  return (
    <Source id="danger-zones" type="geojson" data={data}>
      {/* Filled polygons — severity-based color with pulsing opacity */}
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
          "fill-opacity": [
            "match",
            ["get", "severity"],
            "destroyed",    0.55,
            "major-damage", 0.5,
            "minor-damage", 0.4,
            "no-damage",    0.3,
            0.35,
          ],
        }}
      />

      {/* Colored outline matching severity */}
      <Layer
        id="danger-outline"
        type="line"
        paint={{
          "line-color": [
            "match",
            ["get", "severity"],
            "no-damage",    "#22c55e",
            "minor-damage", "#eab308",
            "major-damage", "#f97316",
            "destroyed",    "#ef4444",
            "#ffffff",
          ],
          "line-width": [
            "match",
            ["get", "severity"],
            "destroyed",    3,
            "major-damage", 2.5,
            "minor-damage", 2,
            "no-damage",    1.5,
            1.5,
          ],
          "line-opacity": 0.85,
        }}
      />

      {/* Glow effect for destroyed / major-damage */}
      <Layer
        id="danger-glow"
        type="line"
        filter={["in", ["get", "severity"], ["literal", ["destroyed", "major-damage"]]]}
        paint={{
          "line-color": [
            "match",
            ["get", "severity"],
            "destroyed",    "#ef4444",
            "major-damage", "#f97316",
            "#ffffff",
          ],
          "line-width": 8,
          "line-opacity": 0.2,
          "line-blur": 6,
        }}
      />
    </Source>
  );
}

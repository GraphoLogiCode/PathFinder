"use client";
import { Source, Layer } from "react-map-gl/maplibre";

interface Props {
  data: GeoJSON.Feature;
}

export default function RouteLayer({ data }: Props) {
  return (
    <Source id="safe-route" type="geojson" data={data}>
      {/* Shadow under route for depth */}
      <Layer
        id="route-shadow"
        type="line"
        layout={{ "line-cap": "round", "line-join": "round" }}
        paint={{
          "line-color": "#000000",
          "line-width": 10,
          "line-opacity": 0.25,
          "line-blur": 3,
        }}
      />
      {/* Main teal route line */}
      <Layer
        id="route-line"
        type="line"
        layout={{ "line-cap": "round", "line-join": "round" }}
        paint={{
          "line-color": "#00a896",
          "line-width": 4,
          "line-opacity": 0.92,
        }}
      />
      {/* Animated dashes on top */}
      <Layer
        id="route-dashes"
        type="line"
        layout={{ "line-cap": "butt", "line-join": "round" }}
        paint={{
          "line-color": "#00d4b8",
          "line-width": 2,
          "line-opacity": 0.6,
          "line-dasharray": [0, 3, 3, 0],
        }}
      />
    </Source>
  );
}

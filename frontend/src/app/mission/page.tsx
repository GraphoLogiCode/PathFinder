"use client";
import { useState, useCallback } from "react";
import MapView from "@/components/MapView";
import Sidebar from "@/components/Sidebar";
import ImageUpload from "@/components/ImageUpload";
import DangerLayer from "@/components/DangerLayer";
import RouteLayer from "@/components/RouteLayer";
import { Marker } from "react-map-gl/maplibre";

export default function MissionPage() {
  const [dangerZones, setDangerZones] = useState<GeoJSON.FeatureCollection | null>(null);
  const [route, setRoute] = useState<GeoJSON.Feature | null>(null);
  const [start, setStart] = useState<[number, number] | null>(null);
  const [end, setEnd] = useState<[number, number] | null>(null);
  const [detections, setDetections] = useState<any[]>([]);
  const [isDetecting, setIsDetecting] = useState(false);
  const [mapCenter, setMapCenter] = useState<[number, number]>([-90.88, 14.47]);

  const [ripple, setRipple] = useState<{ x: number; y: number; id: number } | null>(null);

  const handleMapClick = useCallback(
    (lng: number, lat: number, x?: number, y?: number) => {
      if (!start) setStart([lng, lat]);
      else if (!end) setEnd([lng, lat]);

      if (x !== undefined && y !== undefined) {
        setRipple({ x, y, id: Date.now() });
      }
    },
    [start, end]
  );

  const handleClear = () => {
    setStart(null);
    setEnd(null);
    setRoute(null);
    setDangerZones(null);
    setDetections([]);
  };

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        background: "var(--bg-deep)",
        overflow: "hidden",
        fontFamily: "var(--font-sans)",
      }}
    >
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside
        style={{
          width: 300,
          flexShrink: 0,
          borderRight: "1px solid var(--border-subtle)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Sidebar
          detectionCount={detections.length}
          start={start}
          end={end}
          hasRoute={!!route}
          dangerZones={dangerZones}
          detections={detections}
          route={route}
          onRouteCalculated={setRoute}
          onClearMarkers={handleClear}
        />
      </aside>

      {/* ── Map ─────────────────────────────────────────────────────────── */}
      <main style={{ flex: 1, position: "relative" }}>
        <MapView
          onMapClick={handleMapClick}
          onMoveEnd={(lng, lat) => setMapCenter([lng, lat])}
        >
          {dangerZones && <DangerLayer data={dangerZones} />}
          {route && <RouteLayer data={route} />}
          {start && (
            <Marker longitude={start[0]} latitude={start[1]} color="#22c55e" className="animate-marker-drop" />
          )}
          {end && (
            <Marker longitude={end[0]} latitude={end[1]} color="#ef4444" className="animate-marker-drop" style={{ animationDelay: "0.1s" }} />
          )}
        </MapView>

        {/* Depth gradient blending */}
        <div className="map-gradient-overlay" />

        {/* Map Click Ripple */}
        {ripple && (
          <div
            key={ripple.id}
            style={{
              position: "absolute",
              left: ripple.x - 20,
              top: ripple.y - 20,
              width: 40,
              height: 40,
              borderRadius: "50%",
              border: "2px solid var(--accent)",
              pointerEvents: "none",
              zIndex: 10,
              animation: "map-ripple 0.6s ease-out forwards",
            }}
          />
        )}

        {/* ── Intelligence Column (Upload & Analysis) ──────────────────────── */}
        <div style={{ position: "absolute", top: 20, right: 20, width: 260, display: "flex", flexDirection: "column", gap: 16, zIndex: 10 }}>
          <ImageUpload
            onDetections={setDetections}
            onDangerZones={setDangerZones}
            onUploadStateChange={setIsDetecting}
            mapCenter={mapCenter}
          />
          
          <div className="glass-panel animate-fade-up" style={{ padding: "16px 18px", borderRadius: 4 }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 14 }}>
              AI Analysis
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* Status Row */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Status</span>
                <span style={{ fontSize: 11, color: isDetecting ? "var(--accent-hi)" : detections.length > 0 ? "#22c55e" : "var(--text-faint)", fontWeight: 500, display: "flex", alignItems: "center", gap: 6 }}>
                  {isDetecting && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent-hi)", animation: "pulse-ring 2s infinite" }} />}
                  {isDetecting ? "Analyzing image..." : detections.length > 0 ? "Analysis complete" : "Waiting for image"}
                </span>
              </div>
              
              {/* Detections Row */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Detections</span>
                <span style={{ fontSize: 11, color: "var(--text-primary)", fontFamily: "var(--font-mono, monospace)" }}>
                  {isDetecting ? "--" : `${detections.length} zones detected`}
                </span>
              </div>
              
              {/* Confidence Row */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Confidence</span>
                <span style={{ fontSize: 11, color: "var(--text-primary)", fontFamily: "var(--font-mono, monospace)" }}>
                  {isDetecting ? "--" : detections.length > 0 ? `Avg: ${Math.round(detections.reduce((sum: number, d: any) => sum + (d.confidence ?? 0), 0) / detections.length * 100)}%` : "Not available"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Click-to-set instruction tooltip ──────────────────────────── */}
        <div
          style={{
            position: "absolute",
            bottom: 40,
            left: "50%",
            background: "rgba(23, 26, 29, 0.85)",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
            borderRadius: 20,
            padding: "10px 20px",
            fontSize: 13,
            fontWeight: 500,
            color: "var(--text-primary)",
            pointerEvents: "none",
            whiteSpace: "nowrap",
            zIndex: 20,
            transition: "all 0.3s ease",
            opacity: (!start || !end) ? 1 : 0,
            transform: (!start || !end) ? "translateX(-50%) translateY(0)" : "translateX(-50%) translateY(10px)",
          }}
        >
          {!start ? (
            <span>Click on map to set <span style={{ color: "#22c55e", fontWeight: 600 }}>starting point</span></span>
          ) : !end ? (
            <span>Now select <span style={{ color: "#ef4444", fontWeight: 600 }}>destination</span></span>
          ) : (
            <span>Ready to generate safest route</span>
          )}
        </div>
      </main>
    </div>
  );
}
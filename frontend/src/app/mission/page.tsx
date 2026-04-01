"use client";
import { useState, useCallback, useMemo, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import MapView from "@/components/MapView";
import Sidebar from "@/components/Sidebar";
import ImageUpload from "@/components/ImageUpload";
import DangerLayer from "@/components/DangerLayer";
import RouteLayer from "@/components/RouteLayer";
import AnalysisPanel from "@/components/AnalysisPanel";
import RegionSelect from "@/components/RegionSelect";
import { Marker } from "react-map-gl/maplibre";
import { detectDamage, geoReference } from "@/lib/api";
import type maplibregl from "maplibre-gl";

export default function MissionPage() {
  return (
    <Suspense fallback={<div style={{ background: "var(--bg-deep)", height: "100vh" }} />}>
      <MissionContent />
    </Suspense>
  );
}

function MissionContent() {
  const searchParams = useSearchParams();
  const urlLat = searchParams.get("lat");
  const urlLng = searchParams.get("lng");

  const initialCenter = useMemo<[number, number]>(() => {
    if (urlLat && urlLng) return [parseFloat(urlLng), parseFloat(urlLat)];
    return [-90.88, 14.47];
  }, [urlLat, urlLng]);

  const [dangerZones, setDangerZones] = useState<GeoJSON.FeatureCollection | null>(null);
  const [route, setRoute] = useState<GeoJSON.Feature | null>(null);
  const [start, setStart] = useState<[number, number] | null>(null);
  const [end, setEnd] = useState<[number, number] | null>(null);
  const [detections, setDetections] = useState<any[]>([]);
  const [isDetecting, setIsDetecting] = useState(false);
  const [mapCenter, setMapCenter] = useState<[number, number]>(initialCenter);
  const mapInstanceRef = useRef<maplibregl.Map | null>(null);
  const gpsFlyRef = useRef(false); // true when GPS flyTo is active — prevents competing flyToDangerZones
  const [routeSummary, setRouteSummary] = useState<any>(null);
  const [routeManeuvers, setRouteManeuvers] = useState<any[]>([]);
  const [ripple, setRipple] = useState<{ x: number; y: number; id: number } | null>(null);

  // Region selection
  const [isSelectingRegion, setIsSelectingRegion] = useState(false);
  const [isAnalyzingRegion, setIsAnalyzingRegion] = useState(false);

  // Per-severity rescue plan
  const [selectedSeverity, setSelectedSeverity] = useState<string | null>(null);
  const [showAnalysisPanel, setShowAnalysisPanel] = useState(false);

  const handleMapClick = useCallback(
    (lng: number, lat: number, x?: number, y?: number) => {
      if (isSelectingRegion) return;
      if (!start) setStart([lng, lat]);
      else if (!end) setEnd([lng, lat]);
      if (x !== undefined && y !== undefined) setRipple({ x, y, id: Date.now() });
    },
    [start, end, isSelectingRegion]
  );

  /* ── Fly map to bounding box of danger zones ──────────────────────────── */
  const flyToDangerZones = useCallback((geojson: GeoJSON.FeatureCollection) => {
    const map = mapInstanceRef.current;
    if (!map || !geojson.features.length) return;

    // Compute bounding box across all feature coordinates
    let minLng = Infinity, minLat = Infinity, maxLng = -Infinity, maxLat = -Infinity;
    for (const feature of geojson.features) {
      const geometry = feature.geometry;
      // Handle Polygon and MultiPolygon
      const coordSets =
        geometry.type === "MultiPolygon"
          ? (geometry as GeoJSON.MultiPolygon).coordinates.flat()
          : geometry.type === "Polygon"
          ? (geometry as GeoJSON.Polygon).coordinates
          : [];
      for (const ring of coordSets) {
        for (const [lng, lat] of ring) {
          if (lng < minLng) minLng = lng;
          if (lng > maxLng) maxLng = lng;
          if (lat < minLat) minLat = lat;
          if (lat > maxLat) maxLat = lat;
        }
      }
    }

    if (!isFinite(minLng)) return;

    map.fitBounds(
      [[minLng, minLat], [maxLng, maxLat]],
      { padding: 80, duration: 1400, maxZoom: 18 },
    );
  }, []);

  const handleClear = () => {
    setStart(null);
    setEnd(null);
    setRoute(null);
    setDangerZones(null);
    setDetections([]);
  };

  // Region detection feedback message
  const [regionMessage, setRegionMessage] = useState<string | null>(null);

  const handleRegionSelected = useCallback(
    async (bounds: {
      north: number; south: number; east: number; west: number;
      imageBlob: Blob; imageWidth: number; imageHeight: number;
    }) => {
      setIsSelectingRegion(false);
      setIsAnalyzingRegion(true);
      setRegionMessage(null);
      try {
        // Send the map canvas screenshot to /detect with source=region
        const file = new File([bounds.imageBlob], "region.png", { type: "image/png" });
        console.log("[Mission] Region analysis via canvas capture:", {
          blobSize: bounds.imageBlob.size,
          imageSize: `${bounds.imageWidth}x${bounds.imageHeight}`,
          bounds: { N: bounds.north.toFixed(5), S: bounds.south.toFixed(5), E: bounds.east.toFixed(5), W: bounds.west.toFixed(5) },
        });

        // Step 1: Run YOLO on the captured region screenshot
        const result = await detectDamage(file, "region");
        console.log("[Mission] Detection result:", {
          detections: result.detections?.length ?? 0,
          image_size: result.image_size,
        });
        setDetections(result.detections ?? []);

        // Step 2: Geo-reference using actual bounds from the map
        if (result.detections?.length > 0) {
          const anchorLat = (bounds.north + bounds.south) / 2;
          const anchorLng = (bounds.east + bounds.west) / 2;

          // Calculate GSD from the geographic extent vs pixel dimensions
          const latSpanM = Math.abs(bounds.north - bounds.south) * 111320;
          const lngSpanM = Math.abs(bounds.east - bounds.west) * 111320 * Math.cos(anchorLat * Math.PI / 180);
          const gsd = Math.max(latSpanM / result.image_size.height, lngSpanM / result.image_size.width);

          const geojson = await geoReference(
            result.detections,
            { lat: anchorLat, lng: anchorLng },
            gsd,
            [result.image_size.width / 2, result.image_size.height / 2],
          );
          setDangerZones(geojson);
          flyToDangerZones(geojson);
          setRegionMessage(`✅ Found ${result.detections.length} damage zone${result.detections.length > 1 ? "s" : ""}`);
        } else {
          setRegionMessage("ℹ️ No damage detected — try selecting over a disaster area");
        }
      } catch (err: any) {
        console.error("Region detection failed:", err);
        setRegionMessage(`❌ Detection failed: ${err.message}`);
      } finally {
        setIsAnalyzingRegion(false);
      }
    },
    [flyToDangerZones]
  );

  const handleGenerateRescuePlan = useCallback((severity: string) => {
    setSelectedSeverity(severity);
    setShowAnalysisPanel(true);
  }, []);

  const filteredDangerZones = useMemo(() => {
    if (!dangerZones || !selectedSeverity) return dangerZones;
    return {
      ...dangerZones,
      features: dangerZones.features.filter(
        (f: any) => f.properties?.severity === selectedSeverity
      ),
    };
  }, [dangerZones, selectedSeverity]);

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
          onResetStart={() => { setStart(null); setRoute(null); }}
          onResetEnd={() => { setEnd(null); setRoute(null); }}
          onAnalyzeRegion={() => { setIsSelectingRegion(!isSelectingRegion); setRegionMessage(null); }}
          isSelectingRegion={isSelectingRegion}
          isAnalyzingRegion={isAnalyzingRegion}
          onGenerateRescuePlan={handleGenerateRescuePlan}
          regionMessage={regionMessage}
        />
      </aside>

      {/* ── Map ─────────────────────────────────────────────────────────── */}
      <main style={{ flex: 1, position: "relative" }}>
        <MapView
          onMapClick={handleMapClick}
          onMoveEnd={(lng, lat) => setMapCenter([lng, lat])}
          onMapReady={(map) => { mapInstanceRef.current = map; }}
          initialCenter={initialCenter}
          initialZoom={urlLat ? 15 : 13}
        >
          {dangerZones && <DangerLayer data={dangerZones} />}
          {route && <RouteLayer data={route} />}

          {start && (
            <Marker longitude={start[0]} latitude={start[1]} anchor="bottom">
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div style={{ background: "#22c55e", color: "#000", fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 4, marginBottom: 4, whiteSpace: "nowrap", boxShadow: "0 2px 8px rgba(34,197,94,0.4)", letterSpacing: "0.05em" }}>START</div>
                <div style={{ width: 14, height: 14, borderRadius: "50%", background: "#22c55e", border: "3px solid #fff", boxShadow: "0 0 12px rgba(34,197,94,0.6), 0 2px 6px rgba(0,0,0,0.3)" }} />
              </div>
            </Marker>
          )}

          {end && (
            <Marker longitude={end[0]} latitude={end[1]} anchor="bottom">
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div style={{ background: "#ef4444", color: "#fff", fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 4, marginBottom: 4, whiteSpace: "nowrap", boxShadow: "0 2px 8px rgba(239,68,68,0.4)", letterSpacing: "0.05em" }}>DESTINATION</div>
                <div style={{ width: 14, height: 14, borderRadius: "50%", background: "#ef4444", border: "3px solid #fff", boxShadow: "0 0 12px rgba(239,68,68,0.6), 0 2px 6px rgba(0,0,0,0.3)" }} />
              </div>
            </Marker>
          )}
        </MapView>

        <div className="map-gradient-overlay" />

        {/* Region Select Overlay */}
        <RegionSelect active={isSelectingRegion} onRegionSelected={handleRegionSelected} />

        {/* Map Click Ripple */}
        {ripple && (
          <div key={ripple.id} style={{ position: "absolute", left: ripple.x - 20, top: ripple.y - 20, width: 40, height: 40, borderRadius: "50%", border: "2px solid var(--accent)", pointerEvents: "none", zIndex: 10, animation: "map-ripple 0.6s ease-out forwards" }} />
        )}

        {/* ── Intelligence Column (Upload & Analysis) ──────────────────── */}
        <div style={{ position: "absolute", top: 20, right: 20, width: 260, display: "flex", flexDirection: "column", gap: 16, zIndex: 10 }}>
          <ImageUpload
            onDetections={setDetections}
            onDangerZones={(zones) => {
              setDangerZones(zones);
              // Only fly to the bounding box if GPS didn't already position us.
              // ImageUpload calls onGpsDetected BEFORE onDangerZones when GPS
              // is available, so gpsFlyRef will be true in that case.
              if (zones?.features?.length && !gpsFlyRef.current) {
                flyToDangerZones(zones);
              }
              gpsFlyRef.current = false; // reset for next upload
            }}
            onGpsDetected={(lat, lng) => {
              // GPS is the most accurate anchor — fly directly to it.
              // Set flag so onDangerZones doesn't fire a competing animation.
              gpsFlyRef.current = true;
              const map = mapInstanceRef.current;
              if (map) {
                map.flyTo({ center: [lng, lat], zoom: 17, duration: 1400 });
              }
            }}
            onUploadStateChange={setIsDetecting}
            mapCenter={mapCenter}
          />

          <div className="glass-panel animate-fade-up" style={{ padding: "16px 18px", borderRadius: 4 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "#fff", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 16 }}>
              AI Analysis
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600 }}>Status</span>
                <span style={{ fontSize: 13, color: isDetecting || isAnalyzingRegion ? "var(--accent-hi)" : detections.length > 0 ? "#22c55e" : "rgba(255,255,255,0.5)", fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                  {(isDetecting || isAnalyzingRegion) && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent-hi)", animation: "pulse-ring 2s infinite" }} />}
                  {isDetecting ? "Analyzing image..." : isAnalyzingRegion ? "Analyzing region..." : detections.length > 0 ? "Analysis complete" : "Waiting for input"}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600 }}>Detections</span>
                <span style={{ fontSize: 13, color: "#fff", fontFamily: "var(--font-mono, monospace)", fontWeight: 500 }}>
                  {(isDetecting || isAnalyzingRegion) ? "--" : `${detections.length} zones`}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600 }}>Confidence</span>
                <span style={{ fontSize: 13, color: "#fff", fontFamily: "var(--font-mono, monospace)", fontWeight: 500 }}>
                  {(isDetecting || isAnalyzingRegion) ? "--" : detections.length > 0 ? `Avg ${Math.round(detections.reduce((s: number, d: any) => s + (d.confidence ?? 0), 0) / detections.length * 100)}%` : "N/A"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── AI Rescue Plan Panel ──────────────────────────────────── */}
        <AnalysisPanel
          dangerZones={filteredDangerZones}
          routeSummary={routeSummary}
          maneuvers={routeManeuvers}
          routeGeometry={route?.geometry}
          start={start}
          end={end}
          selectedSeverity={selectedSeverity}
          autoTrigger={showAnalysisPanel}
          onTriggered={() => setShowAnalysisPanel(false)}
        />

        {/* ── Instruction tooltip ───────────────────────────────────── */}
        <div
          style={{
            position: "absolute",
            bottom: 40,
            left: "50%",
            background: "rgba(23, 26, 29, 0.85)",
            backdropFilter: "blur(12px)",
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
            opacity: isSelectingRegion ? 0 : (!start || !end) ? 1 : 0,
            transform: "translateX(-50%)",
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
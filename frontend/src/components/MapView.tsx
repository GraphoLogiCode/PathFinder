"use client";
import { useRef, useCallback, useState } from "react";
import Map, { MapRef } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { SATELLITE_STYLE, STREET_STYLE } from "@/lib/mapStyle";

interface Props {
  onMapClick?: (lng: number, lat: number, x?: number, y?: number) => void;
  onMoveEnd?: (lng: number, lat: number) => void;
  initialCenter?: [number, number]; // [lng, lat]
  initialZoom?: number;
  children?: React.ReactNode;
}

/* ── Icon SVGs ───────────────────────────────────────────────────────────── */
const ZoomInIcon = () => (
  <svg width="22" height="22" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <circle cx="7" cy="7" r="5" />
    <line x1="7" y1="4" x2="7" y2="10" />
    <line x1="4" y1="7" x2="10" y2="7" />
    <line x1="11" y1="11" x2="15" y2="15" />
  </svg>
);

const ZoomOutIcon = () => (
  <svg width="22" height="22" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <circle cx="7" cy="7" r="5" />
    <line x1="4" y1="7" x2="10" y2="7" />
    <line x1="11" y1="11" x2="15" y2="15" />
  </svg>
);

const LocateIcon = () => (
  <svg width="22" height="22" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <circle cx="8" cy="8" r="3" />
    <line x1="8" y1="1" x2="8" y2="4" />
    <line x1="8" y1="12" x2="8" y2="15" />
    <line x1="1" y1="8" x2="4" y2="8" />
    <line x1="12" y1="8" x2="15" y2="8" />
  </svg>
);

const CompassIcon = () => (
  <svg width="22" height="22" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="8" cy="8" r="6.5" />
    <polygon points="8,3 10,8 8,7 6,8" fill="currentColor" stroke="none" />
    <polygon points="8,13 6,8 8,9 10,8" fill="none" />
  </svg>
);

const SatelliteIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="4"/>
    <path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>
    <path d="M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M19.07 4.93l-2.83 2.83M7.76 16.24l-2.83 2.83"/>
  </svg>
);

const MapIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
    <line x1="8" y1="2" x2="8" y2="18"/>
    <line x1="16" y1="6" x2="16" y2="22"/>
  </svg>
);

export default function MapView({ onMapClick, onMoveEnd, initialCenter, initialZoom, children }: Props) {
  const mapRef = useRef<MapRef>(null);
  const [isSatellite, setIsSatellite] = useState(true);
  const hasClickedMap = useRef(false);

  const handleClick = useCallback(
    (e: any) => { 
      onMapClick?.(e.lngLat.lng, e.lngLat.lat, e.point.x, e.point.y); 
      if (!hasClickedMap.current && mapRef.current) {
         hasClickedMap.current = true;
         mapRef.current.getMap().flyTo({ zoom: mapRef.current.getMap().getZoom() + 1, duration: 800 });
      }
    },
    [onMapClick]
  );

  const zoomIn = () => mapRef.current?.getMap().zoomIn();
  const zoomOut = () => mapRef.current?.getMap().zoomOut();
  const geolocate = () => {
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      mapRef.current?.getMap().flyTo({
        center: [coords.longitude, coords.latitude],
        zoom: 14,
        duration: 1200,
      });
    });
  };
  const resetNorth = () => mapRef.current?.getMap().resetNorthPitch({ duration: 600 });

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <Map
        ref={mapRef}
        initialViewState={{ longitude: initialCenter?.[0] ?? -90.88, latitude: initialCenter?.[1] ?? 14.47, zoom: initialZoom ?? 13 }}
        mapStyle={isSatellite ? SATELLITE_STYLE : STREET_STYLE}
        onClick={handleClick}
        onMoveEnd={(e) => onMoveEnd?.(e.viewState.longitude, e.viewState.latitude)}
        onLoad={() => {
          if (mapRef.current) {
            (window as any).__pathfinderMap = mapRef.current.getMap();
          }
        }}
        style={{ width: "100%", height: "100%" }}
      >
        {children}
      </Map>

      {/* ── Vignette: focus gradient around map edges ──────────────────── */}
      <div className="map-vignette" />

      {/* ── Left-side vertical icon controls ──────────────────────────────── */}
      <div
        className="glass-panel animate-fade-in"
        style={{ position: "absolute", left: 24, top: 24, display: "flex", flexDirection: "row", gap: 8, padding: "8px 12px", borderRadius: 8, background: "rgba(10, 15, 25, 0.85)", border: "1px solid rgba(255, 255, 255, 0.08)", boxShadow: "0 4px 12px rgba(0,0,0,0.5)" }}
      >
        {[
          { icon: <ZoomInIcon />,  label: "Zoom in",    action: zoomIn },
          { icon: <ZoomOutIcon />, label: "Zoom out",   action: zoomOut },
          { icon: <LocateIcon />,  label: "My location", action: geolocate },
          { icon: <CompassIcon />, label: "Reset north", action: resetNorth },
        ].map(({ icon, label, action }) => (
          <button
            key={label}
            title={label}
            aria-label={label}
            onClick={action}
            className="map-icon-btn"
            style={{ color: "#f4f4f5", background: "rgba(255, 255, 255, 0.08)", border: "1px solid rgba(255, 255, 255, 0.15)" }}
          >
            {icon}
          </button>
        ))}
      </div>

      {/* ── Map / Satellite toggle ──────────────────────────────────────── */}
      <button
        onClick={() => setIsSatellite((v) => !v)}
        title={isSatellite ? "Switch to street map" : "Switch to satellite"}
        style={{
          position: "absolute",
          bottom: 20,
          left: 16,
          zIndex: 10,
          display: "flex",
          alignItems: "center",
          gap: 7,
          padding: "8px 16px",
          borderRadius: 20, /* Pill shape */
          border: isSatellite
            ? "1px solid rgba(0, 168, 150, 0.5)"
            : "1px solid var(--border-subtle)",
          background: isSatellite ? "rgba(0, 168, 150, 0.15)" : "var(--bg-card)",
          color: isSatellite ? "var(--accent-hi)" : "var(--text-primary)",
          fontSize: 12,
          fontWeight: 600,
          fontFamily: "var(--font-sans)",
          letterSpacing: "0.05em",
          textTransform: "uppercase",
          cursor: "pointer",
          transition: "border-color 0.2s ease, color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease",
          boxShadow: isSatellite ? "0 0 12px rgba(0,168,150,0.2)" : "none",
        }}
        onMouseEnter={e => {
          e.currentTarget.style.transform = "translateY(-1px)";
          e.currentTarget.style.boxShadow = "0 4px 18px rgba(0,168,150,0.3)";
        }}
        onMouseLeave={e => {
          e.currentTarget.style.transform = "translateY(0)";
          e.currentTarget.style.boxShadow = isSatellite ? "0 0 12px rgba(0,168,150,0.2)" : "none";
        }}
      >
        {isSatellite ? <MapIcon /> : <SatelliteIcon />}
        {isSatellite ? "Street Map" : "Satellite"}
      </button>
    </div>
  );
}
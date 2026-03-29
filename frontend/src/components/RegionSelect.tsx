"use client";
import { useState, useCallback, useRef } from "react";

interface Props {
  active: boolean;
  onRegionSelected: (bounds: { north: number; south: number; east: number; west: number }) => void;
}

/**
 * Overlay on top of the map that lets the user drag a rectangle to select a region.
 * When active, intercepts mouse events and draws a selection box.
 */
export default function RegionSelect({ active, onRegionSelected }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const [startPt, setStartPt] = useState<{ x: number; y: number } | null>(null);
  const [endPt, setEndPt] = useState<{ x: number; y: number } | null>(null);

  const getMapCoords = useCallback(
    (clientX: number, clientY: number) => {
      // Convert screen coords to lat/lng via the map canvas
      const mapCanvas = document.querySelector(".maplibregl-canvas") as HTMLCanvasElement | null;
      if (!mapCanvas) return null;

      const rect = mapCanvas.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;

      // Access the map instance through the global __mapRef (set in MapView)
      const map = (window as any).__pathfinderMap;
      if (!map) return null;

      const lngLat = map.unproject([x, y]);
      return { lat: lngLat.lat, lng: lngLat.lng };
    },
    []
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!active) return;
      e.preventDefault();
      e.stopPropagation();

      const container = containerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      setStartPt({ x: e.clientX - rect.left, y: e.clientY - rect.top });
      setEndPt({ x: e.clientX - rect.left, y: e.clientY - rect.top });
      setDragging(true);
    },
    [active]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging || !active) return;
      e.preventDefault();
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      setEndPt({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    },
    [dragging, active]
  );

  const handleMouseUp = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging || !active || !startPt) return;
      e.preventDefault();
      setDragging(false);

      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const finalEnd = { x: e.clientX - rect.left, y: e.clientY - rect.top };

      // Convert corners to lat/lng
      const startCoord = getMapCoords(rect.left + startPt.x, rect.top + startPt.y);
      const endCoord = getMapCoords(rect.left + finalEnd.x, rect.top + finalEnd.y);

      if (startCoord && endCoord) {
        const bounds = {
          north: Math.max(startCoord.lat, endCoord.lat),
          south: Math.min(startCoord.lat, endCoord.lat),
          east: Math.max(startCoord.lng, endCoord.lng),
          west: Math.min(startCoord.lng, endCoord.lng),
        };

        // Only trigger if the region is large enough (not just a click)
        const latSpan = bounds.north - bounds.south;
        const lngSpan = bounds.east - bounds.west;
        if (latSpan > 0.0005 && lngSpan > 0.0005) {
          onRegionSelected(bounds);
        }
      }

      setStartPt(null);
      setEndPt(null);
    },
    [dragging, active, startPt, getMapCoords, onRegionSelected]
  );

  if (!active) return null;

  // Calculate rectangle display
  const boxStyle: React.CSSProperties = {};
  if (startPt && endPt && dragging) {
    const left = Math.min(startPt.x, endPt.x);
    const top = Math.min(startPt.y, endPt.y);
    const width = Math.abs(endPt.x - startPt.x);
    const height = Math.abs(endPt.y - startPt.y);
    Object.assign(boxStyle, {
      position: "absolute" as const,
      left,
      top,
      width,
      height,
      border: "2px solid rgba(0, 168, 150, 0.8)",
      background: "rgba(0, 168, 150, 0.12)",
      borderRadius: 2,
      pointerEvents: "none" as const,
      boxShadow: "0 0 20px rgba(0, 168, 150, 0.3)",
    });
  }

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 15,
        cursor: "crosshair",
      }}
    >
      {/* Selection rectangle */}
      {startPt && endPt && dragging && <div style={boxStyle} />}

      {/* Instruction overlay */}
      {!dragging && (
        <div
          style={{
            position: "absolute",
            top: 16,
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(0, 0, 0, 0.8)",
            backdropFilter: "blur(12px)",
            padding: "10px 20px",
            borderRadius: 8,
            border: "1px solid rgba(0, 168, 150, 0.3)",
            color: "rgba(255,255,255,0.9)",
            fontSize: 14,
            fontWeight: 600,
            whiteSpace: "nowrap",
            pointerEvents: "none",
            boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
          }}
        >
          🎯 Drag to select analysis region
        </div>
      )}
    </div>
  );
}

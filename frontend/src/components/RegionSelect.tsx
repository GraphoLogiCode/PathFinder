"use client";
import { useState, useCallback, useRef } from "react";

interface Props {
  active: boolean;
  onRegionSelected: (bounds: {
    north: number; south: number; east: number; west: number;
    imageBlob: Blob;
    imageWidth: number;
    imageHeight: number;
  }) => void;
}

/**
 * Overlay on the map that lets the user drag a rectangle to select a region.
 * Captures the selected area from the map canvas and returns it as a Blob
 * along with the geo-bounds.
 */
export default function RegionSelect({ active, onRegionSelected }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const [startPt, setStartPt] = useState<{ x: number; y: number } | null>(null);
  const [endPt, setEndPt] = useState<{ x: number; y: number } | null>(null);

  const getMapCoords = useCallback(
    (clientX: number, clientY: number) => {
      const map = (window as any).__pathfinderMap;
      if (!map) return null;
      const canvas = map.getCanvas();
      const rect = canvas.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;
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

        const latSpan = bounds.north - bounds.south;
        const lngSpan = bounds.east - bounds.west;
        if (latSpan > 0.0003 && lngSpan > 0.0003) {
          const map = (window as any).__pathfinderMap;
          if (map) {
            // Force the map to re-render so the WebGL canvas has valid pixels
            map.triggerRepaint();

            // Capture the saved start/end points before the async callback
            const savedStartPt = { ...startPt };
            const savedFinalEnd = { ...finalEnd };
            const savedContainer = container;

            requestAnimationFrame(() => {
              const canvas = map.getCanvas() as HTMLCanvasElement;
              const canvasRect = canvas.getBoundingClientRect();
              const containerRect = savedContainer.getBoundingClientRect();

              // Convert container-relative coords to canvas-relative coords
              const offsetX = containerRect.left - canvasRect.left;
              const offsetY = containerRect.top - canvasRect.top;
              const sx = Math.min(savedStartPt.x, savedFinalEnd.x) + offsetX;
              const sy = Math.min(savedStartPt.y, savedFinalEnd.y) + offsetY;
              const sw = Math.abs(savedFinalEnd.x - savedStartPt.x);
              const sh = Math.abs(savedFinalEnd.y - savedStartPt.y);

              // Enforce minimum region size for meaningful YOLO inference
              if (sw < 200 || sh < 200) {
                console.warn("[RegionSelect] Region too small:", sw, "x", sh, "px");
                return;
              }

              console.log("[RegionSelect] Capturing region:", {
                crop: { sx, sy, sw, sh },
                canvasSize: { w: canvas.width, h: canvas.height },
              });

              const MODEL_SIZE = 1024;
              const dpr = window.devicePixelRatio || 1;

              // Crop and scale to 1024x1024 in one step
              const outputCanvas = document.createElement("canvas");
              outputCanvas.width = MODEL_SIZE;
              outputCanvas.height = MODEL_SIZE;
              const ctx = outputCanvas.getContext("2d");
              if (!ctx) return;

              ctx.imageSmoothingEnabled = true;
              ctx.imageSmoothingQuality = "high";
              ctx.drawImage(
                canvas,
                sx * dpr, sy * dpr, sw * dpr, sh * dpr,
                0, 0, MODEL_SIZE, MODEL_SIZE
              );

              // Verify the capture isn't blank
              const sample = ctx.getImageData(MODEL_SIZE / 2, MODEL_SIZE / 2, 1, 1).data;
              const isBlank = sample[0] === 0 && sample[1] === 0 && sample[2] === 0 && sample[3] === 0;

              const doCapture = () => {
                outputCanvas.toBlob((blob) => {
                  if (blob) {
                    console.log("[RegionSelect] Captured:", blob.size, "bytes,", MODEL_SIZE, "x", MODEL_SIZE);
                    onRegionSelected({ ...bounds, imageBlob: blob, imageWidth: MODEL_SIZE, imageHeight: MODEL_SIZE });
                  } else {
                    console.error("[RegionSelect] toBlob returned null");
                  }
                }, "image/png");
              };

              if (isBlank) {
                console.warn("[RegionSelect] Blank capture — retrying in 300ms");
                setTimeout(() => {
                  ctx.drawImage(canvas, sx * dpr, sy * dpr, sw * dpr, sh * dpr, 0, 0, MODEL_SIZE, MODEL_SIZE);
                  doCapture();
                }, 300);
              } else {
                doCapture();
              }
            });
          } else {
            console.error("[RegionSelect] __pathfinderMap not set");
          }
        } else {
          console.warn("[RegionSelect] Region geo-span too small:", { latSpan, lngSpan });
        }
      }

      setStartPt(null);
      setEndPt(null);
    },
    [dragging, active, startPt, getMapCoords, onRegionSelected]
  );

  if (!active) return null;

  const boxStyle: React.CSSProperties = {};
  if (startPt && endPt && dragging) {
    const left = Math.min(startPt.x, endPt.x);
    const top = Math.min(startPt.y, endPt.y);
    const width = Math.abs(endPt.x - startPt.x);
    const height = Math.abs(endPt.y - startPt.y);
    Object.assign(boxStyle, {
      position: "absolute" as const,
      left, top, width, height,
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
      {startPt && endPt && dragging && <div style={boxStyle} />}
      {!dragging && (
        <div style={{
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
        }}>
          🎯 Drag to select analysis region
        </div>
      )}
    </div>
  );
}

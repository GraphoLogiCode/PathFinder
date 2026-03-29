"use client";
import { useState, useCallback } from "react";
import { detectDamage, geoReference } from "@/lib/api";

interface Props {
  onDetections: (detections: any[]) => void;
  onDangerZones: (zones: any) => void;
  onUploadStateChange?: (isUploading: boolean) => void;
  mapCenter?: [number, number]; // [lng, lat] from MapView — used as georef anchor
}

const UploadIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--accent)", marginBottom: 8 }}>
    <polyline points="16 16 12 12 8 16" />
    <line x1="12" y1="12" x2="12" y2="21" />
    <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
  </svg>
);

export default function ImageUpload({ onDetections, onDangerZones, onUploadStateChange, mapCenter }: Props) {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleUpload = useCallback(
    async (file: File) => {
      setUploading(true);
      onUploadStateChange?.(true);
      setError(null);
      setFileName(file.name);
      try {
        // Step 1: Detect damage (pixel-space polygon masks)
        const result = await detectDamage(file);
        onDetections(result.detections ?? []);

        // Step 2: Auto-georef — convert pixel masks → GeoJSON for map overlay
        if (result.detections?.length > 0 && mapCenter) {
          const geojson = await geoReference(
            result.detections,
            { lat: mapCenter[1], lng: mapCenter[0] },
            2.07, // Default GSD (m/px) — Hurricane Michael demo
            [result.image_size.width / 2, result.image_size.height / 2],
          );
          onDangerZones(geojson);
        }
      } catch (err: any) {
        setError(err.message ?? "Upload failed");
      } finally {
        setUploading(false);
        onUploadStateChange?.(false);
      }
    },
    [onDetections, onDangerZones, onUploadStateChange, mapCenter]
  );

  return (
    <div
      onClick={() => {
        if (uploading) return;
        const input = document.createElement("input");
        input.type = "file";
        input.accept = "image/*";
        input.onchange = (e) => {
          const file = (e.target as HTMLInputElement).files?.[0];
          if (file) handleUpload(file);
        };
        input.click();
      }}
      onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragActive(false);
        if (e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]);
      }}
      className="upload-card"
      style={{
        width: "100%",
        padding: "16px 18px",
        borderRadius: 3,
        border: `1px solid ${dragActive ? "var(--accent)" : uploading ? "var(--accent)" : "var(--border-subtle)"}`,
        background: "rgba(23, 26, 29, 0.75)",
        backdropFilter: "blur(20px) saturate(1.4)",
        WebkitBackdropFilter: "blur(20px) saturate(1.4)",
        cursor: uploading ? "default" : "pointer",
        transition: "border-color 0.2s",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        boxShadow: dragActive ? "0 0 0 1px var(--accent)" : "none",
      }}
    >
      {uploading ? (
        <>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              border: "2px solid var(--accent)",
              borderTopColor: "transparent",
              marginBottom: 10,
              animation: "spin 0.8s linear infinite",
            }}
          />
          <p style={{ fontSize: 15, color: "var(--accent)", fontFamily: "var(--font-sans)", letterSpacing: "0.02em", fontWeight: 600 }}>
            Analyzing damage…
          </p>
          {fileName && (
            <p style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", marginTop: 4, textAlign: "center", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 200, whiteSpace: "nowrap" }}>
              {fileName}
            </p>
          )}
        </>
      ) : error ? (
        <>
          <p style={{ fontSize: 14, color: "#ef4444", textAlign: "center", fontFamily: "var(--font-sans)", fontWeight: 600 }}>{error}</p>
          <p style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", marginTop: 4 }}>Click to retry</p>
        </>
      ) : (
        <>
          <div className="animate-icon-float">
            <UploadIcon />
          </div>
          <p style={{ fontSize: 15, fontWeight: 600, color: "#fff", fontFamily: "var(--font-sans)" }}>
            {dragActive ? "Release to analyze" : "Upload satellite image"}
          </p>
          <p style={{ fontSize: 13, color: "rgba(255,255,255,0.55)", marginTop: 4, fontFamily: "var(--font-sans)" }}>
            or click to browse
          </p>
        </>
      )}

      {/* ── Field Tool metadata ────────────────────────────────────────── */}
      <div style={{
        marginTop: 18,
        paddingTop: 12,
        borderTop: "1px solid var(--border-subtle)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        width: "100%",
        gap: 8,
      }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e", animation: "pulse-ring 2s infinite" }} />
        <span style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", letterSpacing: "0.04em", textTransform: "uppercase", fontWeight: 500 }}>Coverage: ~24 km² • 12 hrs ago</span>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .upload-card {
          transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease, border-color 0.2s ease;
        }
        .upload-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 0 20px rgba(0, 168, 150, 0.15);
          border-color: rgba(0, 168, 150, 0.3) !important;
        }
      `}</style>
    </div>
  );
}
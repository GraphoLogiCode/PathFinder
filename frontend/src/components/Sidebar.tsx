"use client";
import { useState } from "react";
import { calculateRoute, saveMission } from "@/lib/api";
import Link from "next/link";
import Logo from "@/components/Logo";

/* ── Thumbnail placeholders (Half-Earth category card images) ─────────── */
const DAMAGE_THUMB =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='72' height='56' viewBox='0 0 72 56'%3E%3Crect width='72' height='56' fill='%23162030'/%3E%3Ccircle cx='36' cy='28' r='16' fill='none' stroke='%2300a896' stroke-width='2'/%3E%3Cline x1='36' y1='12' x2='36' y2='44' stroke='%2300a896' stroke-width='2'/%3E%3Cline x1='20' y1='28' x2='52' y2='28' stroke='%2300a896' stroke-width='2'/%3E%3C/svg%3E";

const ROUTE_THUMB =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='72' height='56' viewBox='0 0 72 56'%3E%3Crect width='72' height='56' fill='%231a2a1f'/%3E%3Cpath d='M10 46 Q24 20 36 28 Q48 36 62 10' stroke='%2300a896' fill='none' stroke-width='2.5' stroke-linecap='round'/%3E%3Ccircle cx='10' cy='46' r='4' fill='%2322c55e'/%3E%3Ccircle cx='62' cy='10' r='4' fill='%23ef4444'/%3E%3C/svg%3E";

const TRANSPORT_THUMB =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='72' height='56' viewBox='0 0 72 56'%3E%3Crect width='72' height='56' fill='%231e2233'/%3E%3Ccircle cx='25' cy='32' r='6' fill='none' stroke='%2300a896' stroke-width='2'/%3E%3Ccircle cx='47' cy='32' r='6' fill='none' stroke='%2300a896' stroke-width='2'/%3E%3Cpath d='M19 32 L25 22 L47 22 L53 32' stroke='%2300a896' fill='none' stroke-width='2'/%3E%3C/svg%3E";

type TransportMode = "pedestrian" | "auto" | "bicycle";

interface Props {
  detectionCount: number;
  start: [number, number] | null;
  end: [number, number] | null;
  hasRoute: boolean;
  dangerZones: any;
  detections: any[];
  route: any;
  onRouteCalculated: (route: any) => void;
  onClearMarkers: () => void;
}

export default function Sidebar({
  detectionCount,
  start,
  end,
  hasRoute,
  dangerZones,
  detections,
  route,
  onRouteCalculated,
  onClearMarkers,
}: Props) {
  const [activeTab, setActiveTab] = useState<"layers" | "route">("layers");
  const [mode, setMode] = useState<TransportMode>("pedestrian");
  const [routing, setRouting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  const handleCalculateRoute = async () => {
    if (!start || !end) return;
    setRouting(true);
    setRouteError(null);
    try {
      const result = await calculateRoute(start, end, dangerZones, mode);
      onRouteCalculated(result.route);
    } catch (err: any) {
      setRouteError(err.message ?? "Routing failed");
    } finally {
      setRouting(false);
    }
  };

  return (
    <div
      className="sidebar-panel"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backdropFilter: "blur(20px) saturate(1.4)",
        WebkitBackdropFilter: "blur(20px) saturate(1.4)",
      }}
    >
      {/* ── Logo header ─────────────────────────────────────────────────── */}
      <div
        style={{
          padding: "16px 18px 0",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Logo size={26} className="text-zinc-100 hover:text-[var(--accent)] transition-colors cursor-pointer" />
            <Link
              href="/"
              style={{
                fontFamily: "var(--font-heading)",
                fontSize: 30, // text-3xl
                fontWeight: 600,
                color: "var(--text-primary)",
                textDecoration: "none",
                letterSpacing: "-0.025em",
              }}
            >
              PathFinder
            </Link>
          </div>
          <span
            style={{
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--text-faint)",
              padding: "2px 7px",
              border: "1px solid var(--border-subtle)",
              borderRadius: 2,
            }}
          >
            Mission
          </span>
        </div>

        {/* ── Tab bar (Half-Earth style) ─────────────────────────────────── */}
        <div style={{ display: "flex" }}>
          <button
            className={`sidebar-tab ${activeTab === "layers" ? "active" : ""}`}
            onClick={() => setActiveTab("layers")}
          >
            ◈ Map Layers
          </button>
          <button
            className={`sidebar-tab ${activeTab === "route" ? "active" : ""}`}
            onClick={() => setActiveTab("route")}
          >
            ◎ Route Setup
          </button>
        </div>
      </div>

      {/* ── Tab: Map Layers ──────────────────────────────────────────────── */}
      {activeTab === "layers" && (
        <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }} className="animate-fade-up">
          {/* Damage Scale card */}
          <div className="category-card" style={{ margin: "6px 0", borderRadius: 0, borderLeft: "none", borderRight: "none" }}>
            <img
              src={DAMAGE_THUMB}
              alt="Damage Scale"
              className="category-card-thumb"
            />
            <span className="category-card-title">Damage Scale</span>
            {detectionCount > 0 && (
              <div className="accent-badge">{detectionCount}</div>
            )}
          </div>

          {/* Damage legend (expandable under card) */}
          <div style={{ padding: "10px 18px 4px", borderBottom: "1px solid var(--border-subtle)" }}>
            {[
              { label: "No Damage",    color: "#22c55e" },
              { label: "Minor Damage", color: "#eab308" },
              { label: "Major Damage", color: "#f97316" },
              { label: "Destroyed",    color: "#ef4444" },
            ].map(({ label, color }) => (
              <div 
                key={label} 
                style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12, transition: "transform 0.2s, filter 0.2s" }}
                onMouseEnter={e => { e.currentTarget.style.transform = "scale(1.02) translateX(4px)"; e.currentTarget.style.filter = "brightness(1.15)"; }}
                onMouseLeave={e => { e.currentTarget.style.transform = "scale(1) translateX(0)"; e.currentTarget.style.filter = "brightness(1)"; }}
              >
                <div style={{ width: 12, height: 12, borderRadius: 2, background: color, flexShrink: 0, boxShadow: `0 0 8px ${color}` }} />
                <span style={{ fontSize: 13, color: "var(--text-muted)", transition: "color 0.2s" }}>{label}</span>
              </div>
            ))}
          </div>

          {/* Mission Status card */}
          <div className="category-card" style={{ margin: "6px 0", borderRadius: 0, borderLeft: "none", borderRight: "none" }}>
            <img
              src={ROUTE_THUMB}
              alt="MISSION CONTROL"
              className="category-card-thumb"
            />
            <span className="category-card-title">MISSION CONTROL</span>
          </div>

          {/* Status detail */}
          <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column", gap: 16 }}>
            {[
              { label: "START",       value: start ? `${start[1].toFixed(5)}, ${start[0].toFixed(5)}` : "Click on map", color: start ? "#22c55e" : "var(--text-faint)" },
              { label: "DESTINATION", value: end   ? `${end[1].toFixed(5)}, ${end[0].toFixed(5)}`     : "Click on map", color: end   ? "#ef4444" : "var(--text-faint)" },
              { label: "DETECTIONS",  value: `${detectionCount} detected`, color: "var(--text-primary)" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <span style={{ fontSize: 11, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</span>
                <span style={{ fontSize: 13, color, fontFamily: (label !== "DETECTIONS" && value !== "Click on map") ? "var(--font-mono, monospace)" : "var(--font-sans)" }}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Tab: Route Setup ─────────────────────────────────────────────── */}
      {activeTab === "route" && (
        <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }} className="animate-fade-up">
          {/* Transport Mode card */}
          <div className="category-card" style={{ margin: "6px 0", borderRadius: 0, borderLeft: "none", borderRight: "none" }}>
            <img
              src={TRANSPORT_THUMB}
              alt="Transport Mode"
              className="category-card-thumb"
            />
            <span className="category-card-title">Transport Mode</span>
          </div>

          {/* Mode selector */}
          <div style={{ padding: "12px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", gap: 8 }}>
              {([
                { id: "pedestrian", label: "Walk",  emoji: "🚶" },
                { id: "auto",       label: "Drive", emoji: "🚗" },
                { id: "bicycle",    label: "Bike",  emoji: "🚴" },
              ] as { id: TransportMode; label: string; emoji: string }[]).map(({ id, label, emoji }) => (
                <button
                  key={id}
                  onClick={() => setMode(id)}
                  className={`mode-btn${mode === id ? " active" : ""}`}
                >
                  <div>{emoji}</div>
                  <div style={{ marginTop: 3 }}>{label}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Waypoints */}
          <div style={{ padding: "12px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
            <p style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-faint)", marginBottom: 10 }}>
              Waypoints
            </p>
            {[
              { label: "Origin",      value: start ? `${start[1].toFixed(5)}, ${start[0].toFixed(5)}` : "Tap map to set", color: "#22c55e", dot: true },
              { label: "Destination", value: end   ? `${end[1].toFixed(5)}, ${end[0].toFixed(5)}`     : "Tap map to set", color: "#ef4444", dot: true },
            ].map(({ label, value, color, dot }) => (
              <div key={label} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                  {dot && <div style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />}
                  <span style={{ fontSize: 10, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
                </div>
                <p style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "monospace", paddingLeft: 14 }}>{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Footer actions ───────────────────────────────────────────────── */}
      <div style={{
        padding: "14px 14px",
        borderTop: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        background: "rgba(5, 10, 20, 0.4)",
      }}>
        {routeError && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
            <span className="alert-chip animate-alert-pulse">⚠ Route Error</span>
            <p style={{ fontSize: 11, color: "var(--alert-hi)", flex: 1 }}>{routeError}</p>
          </div>
        )}

        <button
          className="btn-teal btn-teal-sticky"
          onClick={handleCalculateRoute}
          disabled={!start || !end || routing}
          style={{ width: "100%" }}
        >
          {routing ? "Generating safest route…" : "Generate Safest Route"}
        </button>

        {hasRoute && (
          <button
            className="btn-ghost"
            onClick={() => {
              setSaving(true);
              saveMission({
                name: `Mission ${new Date().toLocaleTimeString()}`,
                start,
                end,
                detections,
                dangerZones,
                route,
              }).finally(() => setSaving(false));
            }}
            disabled={saving}
            style={{ width: "100%" }}
          >
            {saving ? "Saving…" : "💾 Save Mission"}
          </button>
        )}

        <button
          className="btn-ghost"
          disabled
          style={{ width: "100%", opacity: 0.6 }}
        >
          📄 Export PDF (Offline)
        </button>

        <button
          className="btn-ghost"
          onClick={onClearMarkers}
          style={{ width: "100%", color: "var(--text-faint)", fontSize: 12 }}
        >
          Clear All
        </button>
      </div>
    </div>
  );
}
"use client";
import { useState } from "react";
import { calculateRoute, saveMission } from "@/lib/api";
import Link from "next/link";
import Logo from "@/components/Logo";

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
  onResetStart: () => void;
  onResetEnd: () => void;
  onAnalyzeRegion: () => void;
  isSelectingRegion: boolean;
  isAnalyzingRegion: boolean;
  onGenerateRescuePlan: (severity: string) => void;
}

/* ── Damage level config ─────────────────────────────────────────────────── */
const DAMAGE_LEVELS = [
  { key: "no-damage", label: "No Damage", color: "#22c55e", icon: "🟢" },
  { key: "minor-damage", label: "Minor Damage", color: "#eab308", icon: "🟡" },
  { key: "major-damage", label: "Major Damage", color: "#f97316", icon: "🟠" },
  { key: "destroyed", label: "Destroyed", color: "#ef4444", icon: "🔴" },
];

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
  onResetStart,
  onResetEnd,
  onAnalyzeRegion,
  isSelectingRegion,
  isAnalyzingRegion,
  onGenerateRescuePlan,
}: Props) {
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

  /* ── Count detections per severity class ────────────────────────────────── */
  const severityCounts: Record<string, number> = {};
  if (dangerZones?.features) {
    for (const f of dangerZones.features) {
      const sev = f.properties?.severity ?? "unknown";
      severityCounts[sev] = (severityCounts[sev] || 0) + 1;
    }
  }
  const hasDamageData = Object.keys(severityCounts).length > 0;

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
      <div style={{ padding: "16px 18px 12px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Logo size={26} className="text-zinc-100 hover:text-[var(--accent)] transition-colors cursor-pointer" />
            <Link href="/" style={{ fontFamily: "var(--font-heading)", fontSize: 28, fontWeight: 600, color: "var(--text-primary)", textDecoration: "none", letterSpacing: "-0.025em" }}>
              PathFinder
            </Link>
          </div>
          <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.6)", padding: "3px 8px", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 3 }}>
            Mission
          </span>
        </div>
      </div>

      {/* ── Scrollable content ──────────────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: "auto", padding: "0" }}>

        {/* ── Section: Waypoints ──────────────────────────────────────────── */}
        <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
          <p style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(255,255,255,0.85)", marginBottom: 14 }}>
            📍 Waypoints
          </p>

          {/* Start */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: start ? "#22c55e" : "rgba(255,255,255,0.15)", border: start ? "none" : "1px dashed rgba(255,255,255,0.2)", boxShadow: start ? "0 0 8px rgba(34,197,94,0.4)" : "none" }} />
              <div>
                <p style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>Start</p>
                <p style={{ fontSize: 14, color: start ? "#22c55e" : "rgba(255,255,255,0.4)", fontFamily: start ? "monospace" : "var(--font-sans)", fontWeight: 500 }}>
                  {start ? `${start[1].toFixed(5)}, ${start[0].toFixed(5)}` : "Click map to set"}
                </p>
              </div>
            </div>
            {start && (
              <button onClick={onResetStart} style={{ background: "none", border: "none", color: "var(--text-faint)", cursor: "pointer", fontSize: 14, padding: "2px 6px", borderRadius: 4, transition: "color 0.2s" }}
                onMouseEnter={e => e.currentTarget.style.color = "#22c55e"}
                onMouseLeave={e => e.currentTarget.style.color = "var(--text-faint)"}
              >✕</button>
            )}
          </div>

          {/* End */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: end ? "#ef4444" : "rgba(255,255,255,0.15)", border: end ? "none" : "1px dashed rgba(255,255,255,0.2)", boxShadow: end ? "0 0 8px rgba(239,68,68,0.4)" : "none" }} />
              <div>
                <p style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>Destination</p>
                <p style={{ fontSize: 14, color: end ? "#ef4444" : "rgba(255,255,255,0.4)", fontFamily: end ? "monospace" : "var(--font-sans)", fontWeight: 500 }}>
                  {end ? `${end[1].toFixed(5)}, ${end[0].toFixed(5)}` : "Click map to set"}
                </p>
              </div>
            </div>
            {end && (
              <button onClick={onResetEnd} style={{ background: "none", border: "none", color: "var(--text-faint)", cursor: "pointer", fontSize: 14, padding: "2px 6px", borderRadius: 4, transition: "color 0.2s" }}
                onMouseEnter={e => e.currentTarget.style.color = "#ef4444"}
                onMouseLeave={e => e.currentTarget.style.color = "var(--text-faint)"}
              >✕</button>
            )}
          </div>

          {/* Reset all */}
          {(start || end) && (
            <button
              onClick={onClearMarkers}
              style={{
                width: "100%",
                padding: "6px 0",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 4,
                color: "rgba(255,255,255,0.6)",
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.2)"; e.currentTarget.style.color = "var(--text-muted)"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"; e.currentTarget.style.color = "var(--text-faint)"; }}
            >
              Reset All Points
            </button>
          )}
        </div>

        {/* ── Section: Transport Mode ────────────────────────────────────── */}
        <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
          <p style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(255,255,255,0.85)", marginBottom: 12 }}>
            🚶 Transport Mode
          </p>
          <div style={{ display: "flex", gap: 8 }}>
            {([
              { id: "pedestrian", label: "Walk", emoji: "🚶" },
              { id: "auto", label: "Drive", emoji: "🚗" },
              { id: "bicycle", label: "Bike", emoji: "🚴" },
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

        {/* ── Section: Region Analysis ────────────────────────────────────── */}
        <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
          <p style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(255,255,255,0.85)", marginBottom: 12 }}>
            🎯 Region Analysis
          </p>
          <button
            onClick={onAnalyzeRegion}
            disabled={isAnalyzingRegion}
            style={{
              width: "100%",
              padding: "10px 16px",
              borderRadius: 6,
              border: isSelectingRegion ? "2px solid var(--accent)" : "1px solid rgba(255,255,255,0.12)",
              background: isSelectingRegion
                ? "rgba(0, 168, 150, 0.15)"
                : isAnalyzingRegion
                ? "rgba(0, 168, 150, 0.1)"
                : "rgba(255,255,255,0.04)",
              color: isSelectingRegion ? "var(--accent)" : "rgba(255,255,255,0.8)",
              fontSize: 14,
              fontWeight: 600,
              cursor: isAnalyzingRegion ? "wait" : "pointer",
              transition: "all 0.2s ease",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
            }}
          >
            {isAnalyzingRegion ? (
              <>⏳ Analyzing with YOLO...</>
            ) : isSelectingRegion ? (
              <>✋ Click &amp; drag on map</>
            ) : (
              <>🛰️ Select Region to Analyze</>
            )}
          </button>
          <p style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", marginTop: 6, textAlign: "center" }}>
            Draw a box on the map to run AI damage detection
          </p>
        </div>

        {/* ── Section: Damage Warning Summary ────────────────────────────── */}
        <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
          <p style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(255,255,255,0.85)", marginBottom: 14 }}>
            ⚠️ Damage Analysis
          </p>

          {hasDamageData ? (
            <>
              {/* Warning level bars */}
              {DAMAGE_LEVELS.map(({ key, label, color, icon }) => {
                const count = severityCounts[key] || 0;
                const pct = detectionCount > 0 ? (count / detectionCount) * 100 : 0;
                return (
                  <div
                    key={key}
                    style={{ marginBottom: 12, transition: "transform 0.2s" }}
                    onMouseEnter={e => e.currentTarget.style.transform = "translateX(2px)"}
                    onMouseLeave={e => e.currentTarget.style.transform = "translateX(0)"}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontSize: 14 }}>{icon}</span>
                        <span style={{ fontSize: 14, fontWeight: 500, color: count > 0 ? color : "rgba(255,255,255,0.4)" }}>{label}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 14, fontWeight: 700, color: count > 0 ? color : "rgba(255,255,255,0.3)", fontFamily: "monospace" }}>
                          {count}
                        </span>
                        {count > 0 && (
                          <button
                            onClick={() => onGenerateRescuePlan(key)}
                            style={{
                              background: `${color}18`,
                              border: `1px solid ${color}40`,
                              borderRadius: 4,
                              color: color,
                              fontSize: 10,
                              fontWeight: 600,
                              padding: "3px 8px",
                              cursor: "pointer",
                              transition: "all 0.2s",
                              whiteSpace: "nowrap",
                            }}
                            onMouseEnter={e => { e.currentTarget.style.background = `${color}30`; }}
                            onMouseLeave={e => { e.currentTarget.style.background = `${color}18`; }}
                          >
                            Plan →
                          </button>
                        )}
                      </div>
                    </div>
                    {/* Progress bar */}
                    <div style={{ height: 6, borderRadius: 3, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
                      <div style={{
                        height: "100%",
                        width: `${pct}%`,
                        background: color,
                        borderRadius: 2,
                        boxShadow: count > 0 ? `0 0 8px ${color}40` : "none",
                        transition: "width 0.5s cubic-bezier(0.16, 1, 0.3, 1)",
                      }} />
                    </div>
                  </div>
                );
              })}

              {/* Total */}
              <div style={{
                marginTop: 12,
                padding: "8px 10px",
                background: "rgba(0, 168, 150, 0.08)",
                borderRadius: 4,
                border: "1px solid rgba(0, 168, 150, 0.15)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}>
                <span style={{ fontSize: 14, color: "rgba(255,255,255,0.8)", fontWeight: 600 }}>Total Detections</span>
                <span style={{ fontSize: 18, fontWeight: 700, color: "var(--accent)", fontFamily: "monospace" }}>{detectionCount}</span>
              </div>
            </>
          ) : (
            <div style={{ textAlign: "center", padding: "16px 0" }}>
              <p style={{ fontSize: 14, color: "rgba(255,255,255,0.5)", marginBottom: 6 }}>No damage data yet</p>
              <p style={{ fontSize: 12, color: "rgba(255,255,255,0.35)" }}>Upload a satellite image to analyze</p>
            </div>
          )}
        </div>

        {/* ── Section: Damage Scale Legend ────────────────────────────────── */}
        <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
          <p style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(255,255,255,0.85)", marginBottom: 12 }}>
            Damage Scale
          </p>
          {DAMAGE_LEVELS.map(({ label, color }) => (
            <div
              key={label}
              style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8, transition: "transform 0.2s, filter 0.2s" }}
              onMouseEnter={e => { e.currentTarget.style.transform = "translateX(4px)"; e.currentTarget.style.filter = "brightness(1.15)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "translateX(0)"; e.currentTarget.style.filter = "brightness(1)"; }}
            >
              <div style={{ width: 14, height: 14, borderRadius: 3, background: color, flexShrink: 0, boxShadow: `0 0 6px ${color}50` }} />
              <span style={{ fontSize: 14, color: "rgba(255,255,255,0.75)", fontWeight: 500 }}>{label}</span>
            </div>
          ))}
        </div>

      </div>

      {/* ── Footer actions ───────────────────────────────────────────────── */}
      <div style={{
        padding: "12px 14px",
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
          disabled={Boolean(!start || !end || routing)}
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
      </div>
    </div>
  );
}
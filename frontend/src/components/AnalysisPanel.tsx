"use client";
import { useState, useEffect } from "react";
import { analyzeArea } from "@/lib/api";

interface Props {
  dangerZones: any;
  routeSummary: any;
  maneuvers?: any[];
  routeGeometry?: any;
  start: [number, number] | null;
  end: [number, number] | null;
  selectedSeverity?: string | null;
  autoTrigger?: boolean;
  onTriggered?: () => void;
}

const SEVERITY_LABELS: Record<string, { label: string; color: string }> = {
  "no-damage": { label: "No Damage", color: "#22c55e" },
  "minor-damage": { label: "Minor Damage", color: "#eab308" },
  "major-damage": { label: "Major Damage", color: "#f97316" },
  "destroyed": { label: "Destroyed", color: "#ef4444" },
};

export default function AnalysisPanel({
  dangerZones,
  routeSummary,
  maneuvers,
  routeGeometry,
  start,
  end,
  selectedSeverity,
  autoTrigger,
  onTriggered,
}: Props) {
  const [plan, setPlan] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentSeverity, setCurrentSeverity] = useState<string | null>(null);

  const handleAnalyze = async (severity?: string | null) => {
    setLoading(true);
    setError(null);
    setCurrentSeverity(severity ?? null);
    try {
      const result = await analyzeArea({
        danger_zones: dangerZones,
        route_summary: routeSummary,
        maneuvers: maneuvers,
        route_geometry: routeGeometry,
        start: start ? { lat: start[1], lng: start[0] } : undefined,
        end: end ? { lat: end[1], lng: end[0] } : undefined,
        disaster_type: "hurricane",
        disaster_location: "Disaster Zone",
        severity_filter: severity ?? undefined,
      });
      setPlan(result.plan);
      setIsOpen(true);
    } catch (err: any) {
      console.error("Analysis failed:", err);
      setError(err.message || "Analysis failed");
    }
    setLoading(false);
  };

  // Auto-trigger when the parent requests it
  useEffect(() => {
    if (autoTrigger && dangerZones && selectedSeverity) {
      handleAnalyze(selectedSeverity);
      onTriggered?.();
    }
  }, [autoTrigger]);

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={() => handleAnalyze()}
        disabled={!dangerZones || loading}
        style={{
          width: "100%",
          padding: "10px 16px",
          borderRadius: 8,
          border: "none",
          background: !dangerZones
            ? "rgba(255,255,255,0.06)"
            : loading
            ? "rgba(59, 130, 246, 0.3)"
            : "rgba(59, 130, 246, 0.8)",
          color: !dangerZones ? "rgba(255,255,255,0.3)" : "#fff",
          fontSize: 13,
          fontWeight: 600,
          cursor: !dangerZones ? "not-allowed" : "pointer",
          transition: "all 0.2s ease",
          letterSpacing: "0.02em",
        }}
      >
        {loading ? "🤖 Generating Rescue Plan..." : "🤖 AI Rescue Plan"}
      </button>

      {error && (
        <div
          style={{
            padding: "8px 12px",
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: 6,
            fontSize: 11,
            color: "#f87171",
          }}
        >
          {error}
        </div>
      )}

      {/* Sliding Right Panel */}
      <div
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          width: 400,
          height: "100vh",
          background: "rgba(15, 17, 20, 0.97)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          borderLeft: "1px solid rgba(255,255,255,0.08)",
          boxShadow: "-8px 0 40px rgba(0,0,0,0.5)",
          zIndex: 100,
          transform: isOpen && plan ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.35s cubic-bezier(0.4, 0, 0.2, 1)",
          overflowY: "auto",
          padding: "28px 24px",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 24,
            paddingBottom: 16,
            borderBottom: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div>
            <h2
              style={{
                fontSize: 16,
                fontWeight: 700,
                color: "#fff",
                letterSpacing: "0.02em",
              }}
            >
              🤖 AI Rescue Plan
            </h2>
            {currentSeverity && SEVERITY_LABELS[currentSeverity] && (
              <span style={{
                display: "inline-block",
                marginTop: 6,
                fontSize: 11,
                fontWeight: 600,
                padding: "3px 10px",
                borderRadius: 10,
                background: `${SEVERITY_LABELS[currentSeverity].color}20`,
                color: SEVERITY_LABELS[currentSeverity].color,
                border: `1px solid ${SEVERITY_LABELS[currentSeverity].color}40`,
              }}>
                {SEVERITY_LABELS[currentSeverity].label} Zones
              </span>
            )}
          </div>
          <button
            onClick={() => setIsOpen(false)}
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 6,
              color: "rgba(255,255,255,0.6)",
              cursor: "pointer",
              width: 28,
              height: 28,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
            }}
          >
            ✕
          </button>
        </div>

        {plan && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Situation Summary */}
            {plan.situation_summary && (
              <section>
                <SectionTitle>Situation Overview</SectionTitle>
                <p
                  style={{
                    fontSize: 13,
                    color: "rgba(255,255,255,0.75)",
                    lineHeight: 1.6,
                    padding: "12px 14px",
                    background: "rgba(59, 130, 246, 0.08)",
                    border: "1px solid rgba(59, 130, 246, 0.15)",
                    borderRadius: 8,
                  }}
                >
                  {plan.situation_summary}
                </p>
              </section>
            )}

            {/* Risk Assessment */}
            {plan.risk_assessment?.length > 0 && (
              <section>
                <SectionTitle>Risk Zones</SectionTitle>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {plan.risk_assessment.map((risk: any, i: number) => (
                    <div
                      key={i}
                      style={{
                        background: "rgba(255,255,255,0.03)",
                        border: "1px solid rgba(255,255,255,0.06)",
                        borderRadius: 8,
                        padding: "12px 14px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: 6,
                        }}
                      >
                        <span
                          style={{
                            fontSize: 12,
                            fontWeight: 600,
                            color: "#fff",
                          }}
                        >
                          {risk.zone}
                        </span>
                        <SeverityBadge severity={risk.severity} />
                      </div>
                      <p
                        style={{
                          fontSize: 11,
                          color: "rgba(255,255,255,0.5)",
                          lineHeight: 1.5,
                        }}
                      >
                        {risk.recommendation}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Immediate Actions */}
            {plan.immediate_actions?.length > 0 && (
              <section>
                <SectionTitle>Immediate Actions</SectionTitle>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {plan.immediate_actions.map((action: any, i: number) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        gap: 12,
                        alignItems: "flex-start",
                      }}
                    >
                      <span
                        style={{
                          width: 22,
                          height: 22,
                          borderRadius: "50%",
                          background: "rgba(34, 197, 94, 0.2)",
                          border: "1px solid rgba(34, 197, 94, 0.4)",
                          color: "#22c55e",
                          fontSize: 11,
                          fontWeight: 700,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                          marginTop: 1,
                        }}
                      >
                        {action.priority}
                      </span>
                      <div>
                        <p
                          style={{
                            fontSize: 12,
                            color: "#fff",
                            fontWeight: 500,
                            marginBottom: 2,
                          }}
                        >
                          {action.action}
                        </p>
                        <p
                          style={{
                            fontSize: 10,
                            color: "rgba(255,255,255,0.4)",
                          }}
                        >
                          {action.responsible_team} · {action.time_window}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Resource Allocation */}
            {plan.resource_allocation?.length > 0 && (
              <section>
                <SectionTitle>Resources Needed</SectionTitle>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {plan.resource_allocation.map((res: any, i: number) => (
                    <div
                      key={i}
                      style={{
                        background: "rgba(255,255,255,0.03)",
                        border: "1px solid rgba(255,255,255,0.06)",
                        borderRadius: 8,
                        padding: "10px 14px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <div>
                        <p
                          style={{
                            fontSize: 12,
                            color: "#fff",
                            fontWeight: 500,
                            textTransform: "capitalize",
                          }}
                        >
                          {res.resource?.replace("_", " ")}
                        </p>
                        <p
                          style={{
                            fontSize: 10,
                            color: "rgba(255,255,255,0.4)",
                          }}
                        >
                          {res.deployment_location}
                        </p>
                      </div>
                      <PriorityBadge priority={res.priority} />
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Route Analysis */}
            {plan.route_analysis && (
              <section>
                <SectionTitle>Route Analysis</SectionTitle>
                <div
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    borderRadius: 8,
                    padding: "12px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                  }}
                >
                  {plan.route_analysis.primary_route_reasoning && (
                    <div>
                      <span
                        style={{
                          fontSize: 10,
                          color: "rgba(255,255,255,0.4)",
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                        }}
                      >
                        Primary Route
                      </span>
                      <p
                        style={{
                          fontSize: 12,
                          color: "rgba(255,255,255,0.7)",
                          lineHeight: 1.5,
                          marginTop: 2,
                        }}
                      >
                        {plan.route_analysis.primary_route_reasoning}
                      </p>
                    </div>
                  )}
                  {plan.route_analysis.alternative_considerations && (
                    <div>
                      <span
                        style={{
                          fontSize: 10,
                          color: "rgba(255,255,255,0.4)",
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                        }}
                      >
                        Alternatives
                      </span>
                      <p
                        style={{
                          fontSize: 12,
                          color: "rgba(255,255,255,0.7)",
                          lineHeight: 1.5,
                          marginTop: 2,
                        }}
                      >
                        {plan.route_analysis.alternative_considerations}
                      </p>
                    </div>
                  )}
                </div>
              </section>
            )}
          </div>
        )}
      </div>

      {/* Backdrop overlay */}
      {isOpen && plan && (
        <div
          onClick={() => setIsOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.3)",
            zIndex: 99,
          }}
        />
      )}
    </>
  );
}

/* ── Helper Components ─────────────────────────────────────────────── */

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3
      style={{
        fontSize: 11,
        fontWeight: 600,
        color: "rgba(255,255,255,0.45)",
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        marginBottom: 10,
      }}
    >
      {children}
    </h3>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    critical: { bg: "rgba(239, 68, 68, 0.15)", text: "#f87171" },
    high: { bg: "rgba(249, 115, 22, 0.15)", text: "#fb923c" },
    moderate: { bg: "rgba(234, 179, 8, 0.15)", text: "#facc15" },
    low: { bg: "rgba(34, 197, 94, 0.15)", text: "#4ade80" },
  };
  const c = colors[severity] || colors.moderate;
  return (
    <span
      style={{
        fontSize: 10,
        fontWeight: 600,
        padding: "2px 8px",
        borderRadius: 10,
        background: c.bg,
        color: c.text,
        textTransform: "capitalize",
      }}
    >
      {severity}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    immediate: { bg: "rgba(239, 68, 68, 0.15)", text: "#f87171" },
    within_6h: { bg: "rgba(249, 115, 22, 0.15)", text: "#fb923c" },
    within_24h: { bg: "rgba(234, 179, 8, 0.15)", text: "#facc15" },
  };
  const c = colors[priority] || colors.within_24h;
  return (
    <span
      style={{
        fontSize: 10,
        fontWeight: 600,
        padding: "2px 8px",
        borderRadius: 10,
        background: c.bg,
        color: c.text,
      }}
    >
      {priority?.replace("_", " ")}
    </span>
  );
}

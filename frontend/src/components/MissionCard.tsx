"use client";
import Link from "next/link";

export interface Mission {
  id: string;
  name?: string;
  start: [number, number];
  end: [number, number];
  mode: string;
  created_at?: string;
}

const THUMB_SVG = (i: number) =>
  `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='64' viewBox='0 0 80 64'%3E%3Crect width='80' height='64' fill='%230d1a2a'/%3E%3Ccircle cx='${20 + i * 8}' cy='${15 + i * 5}' r='5' fill='%2322c55e' opacity='0.7'/%3E%3Ccircle cx='${55 + i * 4}' cy='${45 - i * 5}' r='5' fill='%23ef4444' opacity='0.7'/%3E%3Cpath d='M${20 + i * 8} ${15 + i * 5} Q${38} ${32} ${55 + i * 4} ${45 - i * 5}' stroke='%2300a896' fill='none' stroke-width='2' stroke-dasharray='4 2'/%3E%3C/svg%3E`;

const modeLabel = (mode: string) => {
  if (mode === "pedestrian") return "🚶 Walk";
  if (mode === "auto") return "🚗 Drive";
  if (mode === "bicycle") return "🚴 Bike";
  return mode;
};

const formatDate = (iso?: string) => {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
};

interface Props {
  mission: Mission;
  index?: number;
}

export default function MissionCard({ mission, index = 0 }: Props) {
  return (
    <Link
      href={`/mission?id=${mission.id}`}
      style={{ textDecoration: "none" }}
    >
      <div
        className="category-card animate-fade-up"
        style={{
          borderRadius: 3,
          overflow: "hidden",
          transition: "transform 0.18s ease, box-shadow 0.18s ease",
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
          (e.currentTarget as HTMLElement).style.boxShadow = "0 8px 24px rgba(0,168,150,0.15)";
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
          (e.currentTarget as HTMLElement).style.boxShadow = "none";
        }}
      >
        {/* Thumbnail */}
        <img
          src={THUMB_SVG(index)}
          alt="Mission map thumbnail"
          style={{ width: 80, height: 64, flexShrink: 0, objectFit: "cover" }}
        />

        {/* Content */}
        <div style={{ flex: 1, padding: "8px 14px" }}>
          <p
            style={{
              fontFamily: "var(--font-heading)",
              fontSize: 15,
              fontWeight: 600,
              color: "var(--text-primary)",
              marginBottom: 4,
            }}
          >
            {mission.name ?? `Mission #${mission.id.slice(-4)}`}
          </p>
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 3 }}>
            {modeLabel(mission.mode)} · {formatDate(mission.created_at)}
          </p>
          <p style={{ fontSize: 10, color: "var(--text-faint)", fontFamily: "monospace" }}>
            {mission.start[1].toFixed(3)}, {mission.start[0].toFixed(3)} → {mission.end[1].toFixed(3)}, {mission.end[0].toFixed(3)}
          </p>
        </div>

        {/* Teal open indicator */}
        <div
          style={{
            width: 28,
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--accent)",
            fontSize: 16,
          }}
        >
          ›
        </div>
      </div>
    </Link>
  );
}
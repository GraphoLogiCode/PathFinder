"use client";
import Link from "next/link";
import Logo from "@/components/Logo";

/* ── Background: deep navy with subtle radial glow ─────────────────────── */
const BG_STYLE: React.CSSProperties = {
  minHeight: "100vh",
  background: `
    radial-gradient(ellipse 80% 60% at 50% 30%, rgba(0, 168, 150, 0.08) 0%, transparent 70%),
    radial-gradient(ellipse 60% 40% at 20% 80%, rgba(0, 80, 120, 0.12) 0%, transparent 60%),
    var(--bg-deep)
  `,
  fontFamily: "var(--font-sans)",
  color: "var(--text-primary)",
};

export default function DashboardPage() {
  return (
    <div style={{ ...BG_STYLE, position: "relative", overflow: "hidden" }}>
      <div className="bg-topo-animated" />
      <div className="bg-spotlight" />
      
      {/* ── Top nav bar ─────────────────────────────────────────────────── */}
      <header
        className="glass-panel"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 32px",
          height: 60,
          borderTop: "none",
          borderLeft: "none",
          borderRight: "none",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        {/* Logo group */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Logo size={26} className="text-zinc-100 hover:text-[var(--accent)] transition-colors" />
          <div>
            <h1
              style={{
                fontFamily: "var(--font-heading)",
                fontSize: 24, // text-2xl
                fontWeight: 600, // font-semibold
                color: "var(--text-primary)",
                lineHeight: 1,
                letterSpacing: "-0.025em", // tracking-tight
              }}
            >
              PathFinder
            </h1>
            <p style={{ fontSize: 10, color: "var(--text-faint)", letterSpacing: "0.06em", textTransform: "uppercase", marginTop: 2 }}>
              Disaster Navigation
            </p>
          </div>
        </div>

        {/* Nav link + CTA */}
        <div style={{ display: "flex", alignItems: "center" }} className="animate-fade-up">
          <Link href="/mission" style={{ textDecoration: "none" }}>
            <button className="btn-alert" style={{ padding: "8px 16px", fontSize: 13, display: "flex", alignItems: "center", gap: 6, borderRadius: 4 }}>
              <span style={{ fontSize: 16, lineHeight: 1 }}>+</span> New Mission
            </button>
          </Link>
        </div>
      </header>

      {/* ── Hero section ────────────────────────────────────────────────── */}
      <section
        style={{
          maxWidth: 780,
          margin: "0 auto",
          padding: "100px 32px 72px",
          textAlign: "center",
        }}
        className="animate-fade-up"
      >
        <h2
          className="animate-fade-up"
          style={{
            animationDelay: "0.05s",
            animationFillMode: "both",
            fontFamily: "var(--font-heading)",
            fontSize: "clamp(40px, 5vw, 64px)",
            fontWeight: 700,
            lineHeight: 1.05,
            color: "var(--text-primary)",
            letterSpacing: "-0.02em",
            marginBottom: 20,
          }}
        >
          Navigate danger zones.<br />
          Find safer <em style={{ color: "var(--accent)", fontStyle: "italic" }}>paths.</em>
        </h2>

        <p
          className="animate-fade-up"
          style={{
            fontSize: 16,
            color: "#E4E4E7",
            lineHeight: 1.6,
            maxWidth: 600,
            margin: "0 auto 32px",
            fontFamily: "var(--font-sans)",
            animationDelay: "0.1s",
            animationFillMode: "both",
          }}
        >
          Plan safer routes around hazard zones, blocked areas, and damaged infrastructure — in minutes.
        </p>

        <div className="animate-fade-up" style={{ animationDelay: "0.2s", animationFillMode: "both", maxWidth: 500, margin: "0 auto 16px" }}>
          <label style={{ display: "block", textAlign: "left", fontSize: 13, fontWeight: 700, color: "var(--text-faint)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
            Mission Location
          </label>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              window.location.href = "/mission";
            }}
            style={{ display: "flex", gap: 12 }}
          >
            <input
              type="text"
              required
              placeholder="Search mission location (city, region, or coordinates)"
              style={{
                flex: 1,
                padding: "16px 20px",
                fontSize: 16,
                background: "var(--bg-card)",
                border: "1px solid var(--border-subtle)",
                borderRadius: 4,
                color: "var(--text-primary)",
                fontFamily: "var(--font-sans)",
                outline: "none",
                transition: "border-color 0.2s, box-shadow 0.2s",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "var(--accent)";
                e.currentTarget.style.boxShadow = "0 0 0 1px var(--accent-dim)";
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "var(--border-subtle)";
                e.currentTarget.style.boxShadow = "none";
              }}
            />
            <button 
              type="submit" 
              className="btn-teal btn-teal-lg" 
              style={{ borderRadius: 6, padding: "0 28px", fontSize: 16, transition: "filter 0.2s" }}
              onMouseEnter={(e)=>e.currentTarget.style.filter="brightness(1.15)"}
              onMouseLeave={(e)=>e.currentTarget.style.filter="brightness(1)"}
            >
              Set Location
            </button>
          </form>
        </div>
      </section>

      <div
        className="animate-fade-up"
        style={{
          animationDelay: "0.4s",
          animationFillMode: "both",
          maxWidth: 960,
          margin: "0 auto 48px",
          display: "flex",
          justifyContent: "space-around",
          gap: 24,
        }}
      >
        {[
          { value: "Works Offline",   label: "Syncs when connected" },
          { value: "Hazard-Aware",    label: "Avoids danger zones" },
          { value: "Mission History", label: "Secure local log" },
        ].map(({ value, label }) => (
          <div key={label} className="capability-card">
            <p style={{ fontFamily: "var(--font-sans)", fontSize: 16, fontWeight: 700, color: "#A1A1AA", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 6 }}>
              {value}
            </p>
            <p style={{ fontSize: 14, color: "#71717A" }}>{label}</p>
          </div>
        ))}
      </div>

    </div>
  );
}
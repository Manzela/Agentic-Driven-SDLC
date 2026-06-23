/* site-chrome — the global app-shell: nav + footer (IA-03, IA-12, supporting-page-shell).
 * No-funnel nav (no pricing/demo/sign-in). Footer carries the verbatim governing
 * invariant as its single trust line (the canonical source, reused by 404 too). */

export const GOVERNING_INVARIANT =
  "Deterministic gates decide completeness from verifiable facts only; model self-assessment informs, never gates.";

export function SiteNav() {
  return (
    <header style={{ position: "sticky", top: 0, zIndex: 10, borderBottom: "var(--border-hairline)", background: "rgba(10,11,13,0.72)", backdropFilter: "blur(8px)" }}>
      <nav style={{ maxWidth: "var(--container-max)", margin: "0 auto", padding: "0 var(--space-8)", height: 64, display: "flex", alignItems: "center", justifyContent: "space-between" }} aria-label="Primary">
        <a href="/" style={{ textDecoration: "none", color: "var(--text)", lineHeight: 1.05 }}>
          <span style={{ display: "block", fontWeight: 600, fontSize: 15, letterSpacing: "-0.02em" }}>Autonomous Agent</span>
          <span style={{ display: "block", fontSize: 10.5, color: "var(--text-muted)", letterSpacing: "0.04em", textTransform: "uppercase" }}>Autonomous SDLC Platform</span>
        </a>
        <div style={{ display: "flex", gap: "var(--space-6)", alignItems: "center" }}>
          <a href="/how-it-works" style={navLink}>How it works</a>
          <a href="/proof" style={navLink}>Proof</a>
          <a href="/manifesto" style={navLink}>Manifesto</a>
          <a href="#get-notified" style={{ ...navLink, color: "var(--text)", border: "var(--border-hairline)", borderRadius: "var(--radius-sm)", padding: "7px 13px" }}>Get notified</a>
        </div>
      </nav>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer style={{ borderTop: "var(--border-hairline)", padding: "var(--space-16) 0", marginTop: "var(--space-16)" }}>
      <div style={{ maxWidth: "var(--container-max)", margin: "0 auto", padding: "0 var(--space-8)" }}>
        <p data-artifact style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text)", maxWidth: 760, lineHeight: 1.5, margin: 0 }}>
          {GOVERNING_INVARIANT}
        </p>
        <nav style={{ display: "flex", gap: "var(--space-6)", marginTop: "var(--space-6)", flexWrap: "wrap" }} aria-label="Footer">
          <a href="/how-it-works" style={navLink}>How it works</a>
          <a href="/proof" style={navLink}>Proof</a>
          <a href="/manifesto" style={navLink}>Manifesto</a>
          <a href="#get-notified" style={navLink}>Get notified</a>
        </nav>
      </div>
    </footer>
  );
}

const navLink: React.CSSProperties = { color: "var(--text-muted)", textDecoration: "none", fontSize: 14 };

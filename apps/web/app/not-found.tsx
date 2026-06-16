import { GOVERNING_INVARIANT } from "./components/site-chrome";

// Branded 404 (IA-08): preserves nav/footer via the shell, links to each
// canonical destination, carries the governing-invariant trust line, and reads
// as an error in 3s without alarm-red.
export default function NotFound() {
  return (
    <div style={{ maxWidth: "var(--container-max)", margin: "0 auto", padding: "var(--space-16) var(--space-8)" }}>
      <p style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-faint)", margin: 0 }}>404</p>
      <h1 style={{ fontSize: "clamp(28px,4vw,44px)", fontWeight: 600, letterSpacing: "-0.03em", margin: "12px 0 0" }}>
        That page isn&rsquo;t here.
      </h1>
      <p style={{ color: "var(--text-muted)", fontSize: 18, marginTop: "var(--space-4)", maxWidth: 560 }}>
        Here&rsquo;s the way back.
      </p>
      <div style={{ display: "flex", gap: "var(--space-6)", marginTop: "var(--space-6)", flexWrap: "wrap" }}>
        <a href="/" style={link}>Home</a>
        <a href="/how-it-works" style={link}>How it works</a>
        <a href="/proof" style={link}>Proof</a>
        <a href="/manifesto" style={link}>Manifesto</a>
      </div>
      <p data-artifact style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--text-muted)", marginTop: "var(--space-12)", maxWidth: 720 }}>
        {GOVERNING_INVARIANT}
      </p>
    </div>
  );
}

const link: React.CSSProperties = { color: "var(--text)", textDecoration: "none", borderBottom: "1px solid var(--border)" };

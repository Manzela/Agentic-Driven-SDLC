export default function Home() {
  return (
    <div style={{ maxWidth: "var(--container-max)", margin: "0 auto", padding: "var(--space-16) var(--space-8)" }}>
      <p
        style={{ color: "var(--text-muted)", fontSize: 18, margin: "0 0 18px" }}
        data-testid="antagonist-kicker"
      >
        An agent&rsquo;s self-report is not evidence.
      </p>
      <h1
        style={{
          fontSize: "clamp(40px, 7vw, 82px)",
          fontWeight: 600,
          letterSpacing: "-0.035em",
          lineHeight: 1.02,
          margin: 0,
        }}
      >
        Software delivery
        <br />
        that proves itself.
      </h1>
      <p style={{ color: "var(--text-muted)", fontSize: 19, marginTop: "var(--space-6)", maxWidth: 620 }}>
        Independent, evidence-backed verification &mdash; not the agent&rsquo;s
        word for it.
      </p>
    </div>
  );
}

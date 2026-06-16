export default function Home() {
  return (
    <main style={{ maxWidth: 1180, margin: "0 auto", padding: "120px 32px" }}>
      <p
        style={{ color: "#8A8F98", fontSize: 18, margin: "0 0 18px" }}
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
      <p style={{ color: "#8A8F98", fontSize: 19, marginTop: 22, maxWidth: 620 }}>
        Independent, evidence-backed verification &mdash; not the agent&rsquo;s
        word for it.
      </p>
      <p style={{ marginTop: 8, fontSize: 12, color: "#5A606B" }}>
        Autonomous Agent &middot; Autonomous SDLC Platform
      </p>
    </main>
  );
}

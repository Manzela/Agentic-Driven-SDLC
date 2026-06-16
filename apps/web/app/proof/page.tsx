import { GOVERNING_INVARIANT } from "../components/site-chrome";

export default function Proof() {
  return (
    <div style={{ maxWidth: "var(--container-max)", margin: "0 auto", padding: "var(--space-16) var(--space-8)" }}>
      <h1 style={{ fontSize: "clamp(28px,4vw,46px)", fontWeight: 600, letterSpacing: "-0.03em", margin: 0, maxWidth: 860 }}>
        Could an auditor prove your agent did what it claimed?
      </h1>

      <section style={{ marginTop: "var(--space-12)" }}>
        <h2 style={head}>The rule</h2>
        <p data-artifact style={{ fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--text)", maxWidth: 760 }}>{GOVERNING_INVARIANT}</p>
      </section>

      <section style={{ marginTop: "var(--space-12)" }}>
        <h2 style={head}>What proof looks like</h2>
        <div style={{ background: "var(--surface-2)", border: "var(--border-hairline)", borderRadius: "var(--radius-md)", padding: "var(--space-6)", maxWidth: 560 }}>
          {[["test_file", "tests/e2e/payment_retry.spec.ts"], ["test_name", "retry guard holds under timeout"], ["output_hash", "sha256:9f2c…a1e3"], ["collected_at", "2026-06-15T22:14:07Z"]].map(([k, v]) => (
            <div key={k} data-artifact style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--font-mono)", fontSize: 13, padding: "8px 0", borderBottom: "var(--border-hairline)" }}>
              <span style={{ color: "var(--text-faint)" }}>{k}</span><span style={{ color: "var(--proven)" }}>{v}</span>
            </div>
          ))}
        </div>
        <p style={{ color: "var(--text-faint)", fontSize: 12.5, marginTop: "var(--space-3)" }}>Illustrative / representative sample data.</p>
      </section>

      <section style={{ marginTop: "var(--space-12)" }}>
        <h2 style={head}>Why the verdict is independent</h2>
        <p style={{ color: "var(--text-muted)", fontSize: 16, maxWidth: 720 }}>
          The verifier has no write access to implementation and never grades its own output.
        </p>
      </section>

      <section style={{ marginTop: "var(--space-12)" }}>
        <h2 style={head}>Honest limits</h2>
        <p style={{ color: "var(--text-muted)", fontSize: 15, maxWidth: 720 }}>
          The hash-chained log is tamper-evident proof that execution happened as recorded (proof of execution) — distinct from proof that generated code is correct (proof of correctness), which is out of scope. Z3 checks the requirement logic model, not generated code.
        </p>
      </section>
    </div>
  );
}

const head: React.CSSProperties = { fontSize: 13, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: 500, margin: "0 0 12px" };

import { GOVERNING_INVARIANT } from "../components/site-chrome";

export default function Manifesto() {
  return (
    <article style={{ maxWidth: 760, margin: "0 auto", padding: "var(--space-16) var(--space-8)" }}>
      <h1 style={{ fontSize: "clamp(30px,4.4vw,52px)", fontWeight: 600, letterSpacing: "-0.03em", margin: 0 }}>
        The agent said done. It wasn&rsquo;t.
      </h1>

      <section style={{ marginTop: "var(--space-12)" }}>
        <h2 style={num}>1 &middot; The work nobody pays for</h2>
        <p style={p}>
          On a regulated delivery, you became the agent&rsquo;s missing parts &mdash; its memory, its verifier, its auditor. A suite went green, a PR merged, and a component that was never wired into a live path surfaced in production weeks later, owned by you. The proving was unpaid, invisible, and entirely yours.
        </p>
        <p style={p}>
          Every one of these problems is already solved &mdash; by Claude Code, Neon, Temporal, Langfuse, Playwright, Semgrep, and a dozen other proven Tier-1 tools. What no one has done is wire them all together, gate them correctly, and ship it as a product.
        </p>
      </section>

      <section style={{ marginTop: "var(--space-8)" }}>
        <h2 style={num}>2 &middot; The closed loop</h2>
        <p style={p}>
          The only thing that can halt or redirect a running agent is a deterministic Claude Code command hook (PreToolUse, PostToolUse, Stop, SubagentStop, PreCompact, SessionStart) &mdash; not a prompt, not CLAUDE.md &mdash; and command hooks fail closed. Four bounded subagents (initializer, implementer, verifier, research) do the work; the verifier never grades its own output.
        </p>
        <blockquote data-artifact style={{ fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--text)", borderLeft: "2px solid var(--proven)", paddingLeft: "var(--space-4)", margin: "var(--space-6) 0" }}>
          {GOVERNING_INVARIANT}
        </blockquote>
        <p style={p}>
          When work exceeds its bounds it routes to HANDOFF &mdash; terminal, and distinct from COMPLETE. We found and fixed our own HANDOFF infinite-block defect; a proof company audits itself.
        </p>
      </section>

      <section style={{ marginTop: "var(--space-8)" }}>
        <h2 style={num}>3 &middot; Why now</h2>
        <p style={p}>
          Deterministic per-edit enforcement only recently became possible &mdash; command-type hooks that fail closed. Already solved, never assembled. The product is the inevitable assembly of tools you already trust.
        </p>
      </section>
    </article>
  );
}

const num: React.CSSProperties = { fontSize: 13, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: 500, margin: "0 0 12px" };
const p: React.CSSProperties = { fontSize: 18, lineHeight: 1.6, color: "var(--text)", margin: "0 0 var(--space-4)" };

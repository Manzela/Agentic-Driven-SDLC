const STAGES: [string, string, string][] = [
  ["Intent", "Human brief → EARS-format requirement, validated by the SMT spec compiler + spec_validator.", "validated requirement"],
  ["Decompose", "The initializer subagent compiles the EARS spec into a default-unproven feature_list.json.", "coverage model"],
  ["Implement", "The implementer subagent builds one slice in a git worktree, under the ordered PreToolUse plan/scope gates.", "one atomic commit"],
  ["Verify", "The verifier subagent runs five layers, accepted only past the SubagentStop evidence gate.", "evidence record"],
  ["Prove", "A four-field Evidence_Record + a hash-chained audit log + the Z3 logic model.", "tamper-evident proof"],
  ["Gate", "The Stop hook holds the line locally; OPA/Conftest runs a zero-evidence policy at merge; a GitHub ruleset makes both required.", "fail-closed verdict"],
];

export default function HowItWorks() {
  return (
    <div style={{ maxWidth: "var(--container-max)", margin: "0 auto", padding: "var(--space-16) var(--space-8)" }}>
      <h1 style={{ fontSize: "clamp(32px,5vw,56px)", fontWeight: 600, letterSpacing: "-0.03em", margin: 0 }}>
        Six stages. One sequence. Nothing ships unproven.
      </h1>
      <p style={{ color: "var(--text-muted)", fontSize: 18, marginTop: "var(--space-4)", maxWidth: 640 }}>
        The same closed loop, at mechanism resolution. Strict invocation order:
        the ordered PreToolUse chain fires before each write; the Stop hook
        evaluates HANDOFF before the unproven-items gate.
      </p>
      <ol style={{ listStyle: "none", padding: 0, marginTop: "var(--space-12)" }}>
        {STAGES.map(([name, mech, artifact]) => (
          <li key={name} style={{ borderTop: "var(--border-hairline)", padding: "var(--space-6) 0", display: "grid", gridTemplateColumns: "160px 1fr", gap: "var(--space-6)" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 15, color: "var(--text)" }} data-artifact>{name}</span>
            <span>
              <span style={{ fontSize: 16, color: "var(--text)" }}>{mech}</span>
              <span style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--text-muted)", marginTop: 4 }} data-artifact>&rarr; {artifact}</span>
            </span>
          </li>
        ))}
      </ol>
      <p style={{ color: "var(--text-faint)", fontSize: 12.5, marginTop: "var(--space-6)", maxWidth: 720 }}>
        Claude Code hooks are command-type and fail closed; PostToolUse cannot undo an executed action; the hook roster is emerging/version-gated.
      </p>
    </div>
  );
}

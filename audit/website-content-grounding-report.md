# Website Content Grounding Report — autonomous-agent.dev

**Date:** 2026-06-15
**Question:** Is the website content/story (scrollytelling, modules, manifesto, LOOP centerpiece) a faithful, transparent, agentic-legible translation of the *real* product and the industry pain points it addresses?
**Sources:** market research `AI_SDLC_Market_Research.pdf` (16 categories · 95 pain points), the product spec `.kiro/specs/spec-to-evidence-control/` (PRD_MERGED, requirements, design), and the website spec `docs/website/autonomous-agent.dev/`.
**Method:** 8-agent grounding workflow (4 extractors → 1 synthesizer → 3 adversarial reviewers: accuracy, legibility/trust, coverage-completeness).

## Verdict

The site was **accurate and honest but systematically under-translated** the product's strongest mechanisms into legible named architecture. It never shipped an unverifiable count (the value-agnostic denylist correctly blocks even the real 34/34), and grounded the governing invariant, four-field evidence record, and hash-chained trace in real product facts. The grounding chain — **market pain point → real product mechanism → legible website claim** — held, but the most credibility-bearing mechanisms were named only generically, and one hard defect was present.

## What was fixed (applied 2026-06-15; counts unchanged 205/167/217; referential integrity PASS)

**🔴 Hard defect — LOOP-17 (INACCURATE):** the centerpiece's tool-per-node map listed **seven** nodes (inserted a "Spec" node) and placed **Gate before Verify** — contradicting the canonical six-stage loop everywhere else and asserting a logically impossible control flow. **Fixed:** reconciled to canonical `intent → decompose → implement → verify → prove → gate` (gate last), with spec-compilation folded into `decompose` (the real initializer subagent is "Spec Compiler + Coverage Builder").

**🟡 Legibility — named the machines** (previously zero mentions site-wide):
- The **six official Claude Code hooks** (PreToolUse/PostToolUse/Stop/SubagentStop/PreCompact/SessionStart) — now named across CONTENT-18, PAGE-01, PAGE-02, LOOP-17, CONTENT-11, with the honest limit co-required (command-type, fail-closed; PostToolUse cannot undo; roster emerging/version-gated).
- The **four bounded subagents** (initializer/implementer/verifier/research) — named; the verifier's no-write/never-grades-own-output principle surfaced on the homepage (HOME-06), not only /proof.
- The **gate chain** — a single canonical caption (Stop hook + OPA/Conftest + GitHub ruleset) single-sourced in CONTENT-13 and reused verbatim in HOME-05/LOOP-17/PAGE-01.
- **Worktrees + scope-sequencing**, **strict gate sequencing** (ordered PreToolUse chain; HANDOFF evaluated before the unproven-items gate), **B01–B19 signature mechanisms**, and the **security/control set** (OWASP ZAP, DeepEval, OpenFeature/flagd kill-switch, gitleaks, Hypothesis) — now required to be named (qualitatively).

**Accuracy corrections (from the red-team):**
- **Temporal** marked OPTIONAL/roadmap substrate (it is Phase-5/out-of-scope v1) — no longer implied to be "wired together" core.
- **No "millisecond"/"ms-latency" claim** — that is a market-research phrase, not a product-verified figure; replaced with "per-edit prevention before a write lands."
- **Honest limits surfaced:** proof-of-execution vs proof-of-correctness on /proof; Z3 checks the requirement logic model, not generated code; the HANDOFF infinite-block self-correction surfaced as a trust signal.

## Coverage note

Dominant defect type was **under-claim**, not over-reach. The reviewers found **no** case where the site claims a category the product defers/out-of-scopes (predictive routing, Temporal outer loop, Agent Teams, Pact, EU AI Act conformity, code-correctness proof). Near-misses ("zero context-management") are contained by existing claims-integrity controls and were clarified to durable-state offloading.

All remediations are claims-safe: qualitative naming, zero digits, no quantified-efficacy claims, no regulatory-conformity claims.

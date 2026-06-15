# autonomous-agent.dev — Website Specification

This folder is the **materialized, build-ready spec for the public marketing/manifesto website** at the
root domain `autonomous-agent.dev`.

| File | What it is | Count |
|---|---|--:|
| [`requirements.md`](requirements.md) | EARS requirements (ID, priority, EARS-pattern tag, user story, acceptance criteria, dependencies) | **205** |
| [`design.md`](design.md) | Design decisions, each traced to requirement IDs | **167** |
| [`tasks.md`](tasks.md) | Implementation tasks, each traced to requirement IDs, with an objective verification check | **217** |

## ⚠️ This is the *website* spec, not the *product* spec

Keep these two apart — conflating them would bias the product's own Agentic SDLC:

- **This folder** = a website *about* the product (a category-defining manifesto site).
- **The product** = the *Spec-to-Evidence Coverage Control System*, whose canonical spec lives at
  [`.kiro/specs/spec-to-evidence-control/`](../../../.kiro/specs/spec-to-evidence-control/)
  (`requirements.md` / `design.md` / `tasks.md` there describe the control plane itself).

## Provenance

Materialized **2026-06-15** from `docs/plans/based-on-the-attached-eventual-cat.md` — the 17-agent
spec+audit workflow artifact (PART B §B.1/B.2/B.3 indices), with every PART D/E/G correction folded
into the requirement text rather than left as "direction":

- **D1** — all cross-domain dependencies resolve to real requirement IDs (placeholder namespaces
  `TOKENS-*/MOTION-*/PROOF-*/CLAIMS-*/NAV-*` remapped). Verified: 0 dangling references.
- **D2** — single sources of truth declared (tokens→DS, motion→DS-08, routes→IA, gate copy→CONTENT-13,
  notify/`__pref`→PRIV, claims→`content/claims-registry.json`).
- **D3 / G.1** — no hardcoded `N/N verified` count anywhere (the corpus figure drifted 21→32→34);
  verification is stated qualitatively or bound to live harness output, enforced by a value-agnostic
  denylist.
- **D4** — token/contrast locks (`--proven #34E1A0` on `--canvas #0A0B0D` ≈12.5:1; `--text-faint`
  decorative/disabled only; canonical `--error`; display weights 300–600).
- **D5** — route set is the 6 content routes + `/privacy` + `/terms`; utility routes registered separately.
- **D7** — every acceptance criterion is objectively checkable; each requirement tagged with its EARS pattern.
- **PART E / G.3** — the 16 net-new requirements (LOOP-17, CONTENT-17/18/19, DS-19, PRIV-15/16,
  PAGE-17, PERF-17, A11Y-16, IA-17/18, SEO-16/17/18, TOOL-17) are included with design + tasks, so the
  100% traceability includes the fixes.

## Before building

Lock the 8 Phase-0 decisions in PART F of the source plan, then build the fail-closed CI gates first
(referential-integrity, value-agnostic claims lint, strict-CSP smoke-test, runtime motion-integrity,
AA contrast matrix) — the spec's own ethos applied to its website — then the LOOP centerpiece prototype.

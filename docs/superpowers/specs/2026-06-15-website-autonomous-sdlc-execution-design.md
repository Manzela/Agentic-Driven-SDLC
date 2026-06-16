# Execution Design — Autonomous SDLC for `autonomous-agent.dev`

**Date:** 2026-06-15
**Status:** Approved (design); pending spec-doc review → writing-plans
**Subject:** How to build the public website at `autonomous-agent.dev` to flawless completion by running it through the product's *own* methodology (the Spec-to-Evidence Coverage Control System).
**Spec under build:** [`docs/website/autonomous-agent.dev/`](../../website/autonomous-agent.dev/) (requirements/design/tasks)
**Methodology source:** [`.kiro/specs/spec-to-evidence-control/`](../../../.kiro/specs/spec-to-evidence-control/) (`PRD_MERGED`, requirements, design, tasks)

> This document is the *execution* design — the build harness and process. It does not restate the
> website's feature spec (that lives in `docs/website/autonomous-agent.dev/`). It is the answer to
> "how do we build all of it and be 100% confident it's flawlessly complete."

---

## 1. Goal & the meaning of "flawless"

Build the entire `autonomous-agent.dev` site and reach a state where **"done" is a machine fact, not a
judgement**: every in-scope requirement is `proven` by captured, re-derivable evidence, enforced by
deterministic fail-closed gates. We achieve this by **eating our own dog food** — the website is built
*on* the product's coverage-control methodology, making it the product's first real proving ground.

**Governing invariant (verbatim from the product spec, instantiated for the site):** deterministic gates
decide completeness, computed solely from verifiable facts captured against the real `apps/web` repo +
Vercel-preview state; model self-assessment and predictions only inform — they never gate. "Done" =
**0 `unproven` in-scope items** in `apps/web/feature_list.json`. A stuck run can never relabel itself
COMPLETE (it HANDOFFs instead).

## 2. Locked decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Confidence model | Dog-food: coverage model + fail-closed gates + independent verifier; 0-unproven = done |
| 2 | Code location | `apps/web/` in this repo (light monorepo with the Python control plane), path-filtered CI |
| 3 | Hosting | **Vercel** (App Router ISR, edge CSP/nonce, native OG `ImageResponse`, per-PR preview deploys) |
| 4 | Framework | **Next.js App Router** + TypeScript strict + Tailwind v4 (Style Dictionary tokens) — per spec TECH-01 |
| 5 | Scope | **209 items** = 205 materialized requirements + 3 Bucket-A + 1 SBOM/SCA |
| 6 | Orchestration | **Fully autonomous** gate-driven loop to 0-unproven; exactly 2 human gates |
| 7 | Autonomy trust | Adopt **all 5** actor-independence fixes (§5) — invariant is machine-checked, not conventional |
| 8 | Bootstrapping | Build a **website-scoped Phase-0 spine** in `apps/web` (self-contained; doesn't block on full product) |
| 9 | Completeness | Add SBOM/SCA (209th), `/security-review` (non-gating), explicit `SessionStart` restoration |

**Scope arithmetic:** 205 (DS 19, IA 18, HOME 15, LOOP 17, CONTENT 19, PAGE 17, TECH 16, TOOL 17, PERF 17,
A11Y 16, SEO 18, PRIV 16) + Bucket-A 3 (security-header matrix, privacy-safe RUM, whole-site
visual-regression gate) + 1 SBOM/SCA = **209**.

## 3. The fail-closed gate chain (instantiated for `apps/web`)

Grounded in the control-plane spec; verified against source by an adversarial review pass.

```
0  Spec-completion gate (non-LLM): website EARS → Z3 spec_validator (violation_count==0,
   vague NFRs rejected unless quantified), ≤7 passes / strict-decrease-or-HANDOFF → FREEZE feature_list.json
1  plan-approved.json            (HUMAN GATE #1; SHA-bound: feature_list_sha == sha256 of the frozen 209-item model)
2  PreToolUse hooks (ONLY true prevention, exit 2): resume-integrity → plan+SHA → scope-sequencing →
   checklist-approval → artifact-guard → status-guard → secret-guard
3  Implementer builds ONE slice in a git worktree (egress-denied); PostToolUse (ESLint/tsc/Semgrep/
   dead-code) = next-turn feedback only, CANNOT gate
4  Vercel preview deploy          (the live target the verifier checks against)
5  Independent verifier (no write to src) runs 5 layers → captures artifacts → SOLE actor flipping unproven→proven
6  SubagentStop (exit 2): reject unless 4-field Evidence_Record present+non-empty AND omission_declaration enumerates gaps
7  Stop hook (exit 2): block "done" while ANY of 209 items ≠ proven; HANDOFF triggers checked FIRST → exit 0
8  OPA/Conftest zero-evidence policy (required check): deny merge if any item unproven or proven-without-evidence
9  GitHub ruleset required checks: coverage-gate(OPA), formal-verification(Z3), secrets-scan(gitleaks),
   audit-chain-verify, zap-baseline, property-tests, SBOM/SCA dependency-CVE
10 Human PR review + production DNS go-live (HUMAN GATE #2) — reachable ONLY from genuine COMPLETE, never HANDOFF
```

Note (correction from review): SonarQube is a Phase-1 *tool* and SLSA is *signed provenance* — neither is
overstated as a registered required check beyond what the source supports; the named required checks are
coverage-gate, formal-verification, secrets-scan, audit-chain-verify, zap-baseline, property-tests, plus
the new SBOM/SCA check. ZAP baseline is a **CI check**, not a verifier-subagent layer.

## 4. Coverage model & evidence schema

**`apps/web/feature_list.json`** — canonical, version-controlled, append-only. 209 `CoverageItem`s, each:
`id`, `type` ∈ {functional, NFR, WIRING}, `priority` (P0–P3), `dependencies` (the spec's resolved
cross-domain deps), `acceptance_criteria` (the spec's ≥2 objective criteria), `in_scope` (default true),
`status` (default `unproven`). Validated against `schema/feature_list.schema.json` (draft-07) on every
PreToolUse write.

**ID remap (to perform):** the website spec's two-segment IDs (`DS-01`, `PRIV-15`) are materialized to the
methodology's canonical `^[A-Z]+-[A-Z]+-[0-9]{3}$` (e.g. `DS-01 → DS-TOK-001`, `PRIV-15 → PRIV-CSP-015`;
new families `REQ-SEC-*` security-header matrix, `REQ-RUM-*`, `REQ-VIS-*`, `REQ-SCA-*`), preserving
traceability to the source EARS IDs. Also fix `TECH-06`'s double-`**EARS:**` line before freeze.

**Evidence_Record** — exactly 4 required, non-empty fields, `additionalProperties:false`:
`test_file`, `test_name`, `output_hash` (`^sha256:[a-f0-9]{64}$`), `collected_at` (ISO-8601). The hash is
computed over the **actual captured artifact bytes** (Playwright trace / axe JSON / Lighthouse JSON /
header capture / visual-diff set), so a stale or fabricated hash is structurally impossible.

**Status transitions** (only): `unproven→proven` (verifier + complete evidence), `unproven→failed`,
`failed→unproven`. While ANY in_scope item is `unproven`, the site is incomplete. `in_scope=false` only
by a human-signed edit (an agent cannot self-exempt an item to fake COMPLETE).

## 5. The trust core — making a fully-autonomous loop actually honest

A red-team review found that, as initially specified, **a single autonomous session could self-declare
itself the verifier** (`actor_agent` is a self-declared field; SubagentStop only checked schema
completeness). That makes the invariant convention, not proof. The five adopted fixes close it:

1. **Harness-stamped actor identity.** `actor_agent` is set from the Claude Code subagent/session
   identity (or OTel span actor), *not* from a value the writing agent supplies. Reject any record where
   declared ≠ captured identity.
2. **Distinct-session assertion.** Store the implementer session/commit author on the slice; OPA + SubagentStop
   both reject a `proven` flip where `verifier_session == implementer_session` for the same item.
3. **Gate-side evidence re-derivation.** An un-bypassable gate (OPA coverage-gate / SubagentStop)
   recomputes the `sha256` from the cited `test_file`/`test_name` against the live Vercel preview and
   confirms it equals the submitted `output_hash` — verify, don't trust.
4. **Field-level write authority** in PreToolUse: `status` writable only by the verifier session and only
   within the allowed transition set; `in_scope` mutable only via a commit signed with the human-gate key.
5. **Formal + property coverage of actor separation.** Add a Z3 check + Hypothesis/fast-check property
   proving `proven ⇒ (verify_actor ∧ verify_actor ≠ impl_actor)` is UNSAT to violate (Property 24 made
   real, with a machine-checked line — it currently has none).

**Verifier contract:** `.claude/agents/verifier.md`, permission-scoped to `apps/web`; read-only on
`apps/web/src/**`; read/write only on `apps/web/tests/**` and the `status` field; cannot edit
`next.config`, `vercel.json`, CI workflows, the schema, or token sources; must emit a non-null
`omission_declaration`; cannot self-exempt items.

## 6. Build order (dependency tiers)

The loop is dependency-driven (pick highest-priority unblocked unproven items); the graph yields:

| Tier | Built & proven | Note |
|---|---|---|
| 0 — Spine | website-scoped control plane: `feature_list.json`, 6 hooks, `verifier.md`, OPA gate, schema, `evidence_collector`/`audit_log`, worktrees, CI, Vercel project | proven on one trivial slice first |
| 1 — Foundations | DS tokens (Style Dictionary + `DESIGN.md`), TECH app-shell, IA route manifest, PRIV CSP/header baseline | everything depends on these |
| 2 — Centerpiece | LOOP closed-loop + EvidenceTrace | per plan: riskiest/most visible, first |
| 3 — Narrative | HOME scrollytelling, PAGE supporting pages | |
| 4 — Cross-cutting NFRs | PERF, A11Y, SEO, TOOL/CI gates, SBOM/SCA, RUM, visual-regression | these gates also prove other items |

## 7. External dependencies & fallback-first (loop never blocks)

- **Rive `.riv` asset** → build the hand-coded SVG/CSS labeled loop first (it doubles as the
  spec-required reduced-motion/no-JS fallback, LOOP-08); the `.riv` enhancement is a separate item proven
  when the authored asset lands.
- **Final copy / manifesto prose** → loop proves the *system* (renders, voice-lint, claims-registry)
  against draft copy flagged `needs-human-approval`; words approved at go-live.
- **Legal text** (`/privacy`, `/terms`) → honest placeholder stub passes structural gates; real text
  injected before go-live.
- **DNS / Get-notified backend / analytics pick** → DNS *is* the go-live gate; Get-notified ships with a
  privacy-respecting backend + honeypot (PART F #6) or a stubbed state-machine wired at go-live.
- **OG images** are in-scope code (Next.js `ImageResponse`), not an external dependency.

## 8. Safety, bounds & human gates

- **Two human gates only:** ① plan-approval SHA-freeze; ② production DNS go-live (+ PR review), reachable
  only from a genuine COMPLETE.
- **Bounded autonomy:** kill-switch (flagd, ≤30s, no restart); execution bounds (25 turns/slice,
  1M-token/slice budget, retry 3, no-progress over N=3 slices → **HANDOFF exit 0**, never a relabeled
  COMPLETE); egress-denied builder sandbox; artifact-guard (tests/schema/CI/config); secret-guard;
  Neon outage → file-backed `feature_list.json`, still fail-closed (never fail-open).

## 9. Verification (evidence) taxonomy

Five verifier layers + cross-cutting gates:
- **structural** — `tsc` strict / ESLint / AST
- **semantic** — Vitest unit + integration
- **behavioral** — Playwright E2E incl. empty/loading/error/404/500 render assertions
- **security** — Semgrep/CodeQL SAST + security-header matrix (`curl -I`) + ZAP-baseline (CI) + **SBOM/SCA**
  dependency-CVE + `/security-review` (advisory, non-gating)
- **perf + a11y** — Lighthouse CWV budgets (LCP/CLS/INP) + axe-core **zero critical/serious**
- **cross-cutting** — whole-site visual-regression, claims-registry lint (value-agnostic `N/N` denylist),
  referential-integrity, runtime motion-integrity, AA contrast matrix.

## 10. Phase mapping (product → website)

- **Phase 0 (spine)** — Style Dictionary tokens + `feature_list.json` + Stop hook + verifier + worktrees +
  GitHub coverage-gate + Playwright; the website's own Phase-0 fail-closed gates (referential-integrity,
  claims lint, strict-CSP smoke-test, motion-integrity, contrast matrix) wired here.
- **Phase 1 (depth)** — Semgrep/CodeQL, SonarCloud quality gate (tool), full OPA `.rego`, PostToolUse,
  schema validation, WIRING/orphan checks.
- **Phase 2 (durable state)** — Neon Postgres traceability/evidence/run-state (per-PR branching matching
  Vercel previews), PreCompact checkpoints, SLSA provenance, flagd kill-switch; **explicit SessionStart
  restoration** (rehydrate the burn-down after compaction/crash on a long autonomous run).
- **Phase 3 (observability)** — OTel → Langfuse with `requirement.id` Baggage, hook-decision forwarding,
  reasoning-loop detector (informs HANDOFF; never gates). *Note: OTel GenAI conventions are experimental —
  pin versions per the spec's honest-limit.*
- **Phase 4 (PBTs)** — gate-invariant property tests as required CI (incl. the new actor-separation property).
- **Phases 5–6 (Temporal outer loop / predictive routing)** — DEFAULT OFF; advisory-only if ever used;
  never gate.

## 11. Honest limits (must be stated verbatim on the site)

Z3 proves the **gate/control logic model** (status transitions, unproven-blocks-COMPLETE,
prediction-can't-gate, cap→HANDOFF, evidence-schema, amendment monotonicity, actor separation). It does
**not** prove the rendered Next.js/TSX behaves — the site's actual rendered/visual/perf/a11y behavior is
proven exclusively by captured Playwright/axe/Lighthouse/header/ZAP evidence. The site must not claim
"formally verified code"; the value-agnostic `N/N verified` denylist lint enforces this.

## 12. Phase-0 decisions to lock before freeze (PART F)

Accent/contrast matrix; **hosting = Vercel** (locked); display typeface (Geist Sans default); mono family
(Geist Mono); `/writing` at launch (seed 1–2 vs stub); Get-notified backend + anti-abuse; gate-verdict
copy constant; claims-registry seed (qualitative/live-bound, no hardcoded count).

## 13. Top risks → mitigations

| Risk | Mitigation |
|---|---|
| Self-graded `proven` flip (the invariant hole) | The 5 fixes in §5 (machine-checked actor independence) |
| Flaky E2E / visual-diff | deterministic capture, retry budget, reasoning-loop detector → HANDOFF |
| Rive asset absence | fallback-first (SVG/CSS loop = LOOP-08 fallback) |
| Copy / legal external | draft + `needs-human-approval` marker, approved at go-live |
| Vercel preview nondeterminism | pin build, wait-for-stable before verifier runs |
| Spine over-build | 4 base roles only; file-backed Phase-0; Neon deferred to Phase-2 |
| Vulnerable transitive npm dep reaching COMPLETE | SBOM/SCA dependency-CVE required check (209th item) |

## 14. Open items for the implementation plan

- Materialize `feature_list.json` (209 items, remapped IDs) and freeze via SHA after the spec-completion gate.
- Decide Get-notified backend provider (PART F #6) and analytics platform (Plausible/Fathom/none).
- Confirm the website-scoped spine reuses vs. forks the product's `tools/`/hooks (it is scoped to
  `apps/web`, but mechanisms mirror the product's).

# Zero-Trust Evidence Gate — Dual-Enforcement Architecture

- **Date:** 2026-06-22
- **Status:** Decisions resolved (§9) — awaiting spec approval to write the Phase-A plan
- **Supersedes the enforcement model of:** `docs/superpowers/specs/2026-06-21-spine-canary-gate-first-thing-design.md` (the in-session hook spine remains, but is **demoted to best-effort steering**; it is no longer the binding gate).
- **Paradigm:** Stop *preventing the action via ephemeral runtime hooks*; instead *reject the outcome via durable, replayable provenance*. Treat every agent output as an **untrusted supply-chain artifact** (SLSA / in-toto model).

---

## 1. Root cause — why the in-session model cannot govern the fleet

Verified empirically this session (diagnostic in the transcript):

| Actor | Identical Edit `unproven→proven` | Hooks observed |
|---|---|---|
| **Main session** | **BLOCKED** ("status is verifier-owned (you are 'main')") | PreToolUse + PostToolUse fired |
| **Spawned subagent** | **SUCCEEDED** — wrote `proven` | **none** — no PreToolUse, no PostToolUse |
| **Headless `claude -p`** (any worktree) | n/a | **none** — project hooks never fire |

**`PreToolUse`/`PostToolUse` hooks fire only for the main interactive session — not for subagent tool calls, and not for headless `claude -p` processes.** This is by design (subagents are trusted extensions of the main session; headless project hooks require interactive trust). The consequence: the spine's in-session *prevention* gate governs **only the main loop**, never the verifier/implementer **actors** it was built to police. Any actor can self-grade `status=proven` directly, ungoverned. The actor-independence model, as a hook-prevention scheme, is structurally unenforceable.

**This is not a missing test — it is the wrong enforcement layer.**

---

## 2. The paradigm shift

> **Don't trust the write — verify the evidence.**

The gate never trusts the `status` field. `proven` is accepted **only** if backed by a durable, independently-re-derivable **Evidence_Record** whose provenance is **attested by a trust anchor the agent cannot impersonate**. Enforcement moves from "block the bad write in-session" (ephemeral, hook-dependent, unenforceable for subagents) to "reject the unproven claim at an unbypassable chokepoint" (durable, deterministic, replayable). This is the **zero-trust supply-chain** model — agent artifacts are treated exactly as untrusted build outputs are under SLSA, with cryptographic provenance attestation.

---

## 3. Architecture — Dual-Enforcement Zero-Trust, three pillars

```
            ┌───────────────────────── HARD SECURITY BOUNDARY ─────────────────────────┐
  UNTRUSTED │  Agent sandbox (claude -p)                                                 │ TRUSTED (TCB)
            │  - produces artifact bytes only                                            │
   artifact │  - NO access to signing identity, ledger, or attestation logic            │  Dispatcher
   ─────────┼──────────────────────────────────────────────────────────────────────────┼──────────────
            └──────────────────────────────────────────────────────────────────────────┘  - launches roles,
                                                                                             owns session ids
   (3) Process Isolation & Chain of Custody  ── the boundary that makes 1 & 2 trustworthy   - re-derives hash
                                                                                             - signs attestation
   (2) Autonomous Steering Gate (local, per-slice) ── refuse-advance + self-heal, bounded
   (1) Cryptographic Security Gate (CI / merge)    ── unbypassable source of truth
```

### Pillar 1 — Cryptographic Security Gate (CI / merge): the source of truth

The **only** binding gate. Enforced by the platform (branch-protection ruleset), so it cannot be skipped by a direct commit/push. It assumes the git payload is **hostile** and verifies, deterministically:

1. **Coverage policy** — `coverage_query.rego`: no merge while any in-scope item lacks a valid evidence record (zero-evidence-merge prohibition).
2. **Independent artifact re-derivation** — CI re-computes `output_hash` from the committed artifact and matches it (defense-in-depth; CI does **not** merely trust the signature).
3. **Attestation signature verification** — the Evidence_Record carries a **dispatcher signature** over `(artifact_hash, commit_sha, requirement_id, role, implementer_session_id, verifier_session_id)`. CI verifies it against the dispatcher's trust root. Production form: **Sigstore keyless** (OIDC → ephemeral cert, Rekor transparency log) so there is **no long-lived key** for any sandbox to steal.
4. **Actor-independence** — `verifier_session_id ≠ implementer_session_id`, both attested by the dispatcher (not read from the agent payload), cross-checked against the transparency/ledger record.
5. **Formal + SAST** — Z3 spec-completion (`spec_validator.py`), CodeQL.

A self-graded flip with no valid signed attestation **cannot merge** — regardless of who wrote it or whether any hook fired.

### Pillar 2 — Autonomous Steering Gate (local loop driver): minimize HITL

A pure CI gate **maximizes** HITL — a PR fails at merge, the agent's session is dead, a human reads logs and respawns. So the **same deterministic checks run locally at each slice boundary, pre-advance**, owned by the loop driver. This is the *automated* form of "Option 3", made co-equal:

- On a clean check → advance/commit.
- On a violation → **refuse to advance** (the `proven` claim is not accepted; nothing is committed), and **translate the exact policy/Rego failure into an action-directive self-heal prompt** fed into the same agent's context for autonomous correction. The action-directive steering already built (every block names the one sanctioned next step) becomes the self-heal generator.
- **Bounded** — self-heal is capped (N attempts) then **escalates to HANDOFF**, reusing the reentrancy/escalation discipline already built (`stop_hook_active` reentrancy, `block_streak → HANDOFF`). *Without this bound we recreate C-LOOP-04 (infinite self-correction) one layer up.*

This keeps the human out of the loop for correctable failures while preserving the CI gate as the backstop for anything the local gate misses or an actor tries to bypass.

### Pillar 3 — Process Isolation & Chain of Custody: the boundary that makes 1 & 2 real

Provenance metadata is worthless if the untrusted actor shares a filesystem with it. Therefore:

- **Actors run as separate `claude -p` processes inside a HARD kernel boundary.** Untrusted AI code with shell access requires a real isolation boundary — **not** a shared-kernel container (a container escape would reach the host *and* the dispatcher TCB / signing identity). Substrate: **Firecracker microVM** (KVM, own guest kernel — strongest) or **gVisor** (user-space kernel, lighter ops). The sandbox constrains filesystem to the agent's workspace and has **no access** to the signing identity, the ledger, or the attestation logic; the dispatcher communicates with it over a controlled channel (vsock / observed process output).
- **The dispatcher is the Trusted Computing Base (TCB)**, running **outside** the sandbox. It: launches each role (so it *owns* the role↔session mapping), observes the agent's artifact across the boundary (process output / workspace read), **independently re-derives** `output_hash`, supplies session ids from **its own** launch records (never the agent's payload), and **signs** the attestation.
- **The agent is an untrusted guest** whose only contribution is artifact bytes. It cannot forge provenance because it never holds the key, never writes the ledger, and the hash is computed by the dispatcher, not accepted from the agent.

---

## 4. Trust model & threat model (adversarial)

**TCB = the dispatcher + the signing identity + the CI policy.** Everything else (agents, workspace, git payload, feature_list.json, even the local audit chain) is **untrusted**.

| Threat | Mitigation |
|---|---|
| **Evidence forgery** — agent writes a fake evidence record / spoofed session id / hash of an empty file | Dispatcher re-derives the hash itself and supplies session ids from its own records; signs. Agent never produces the signed attestation. |
| **TOCTOU / artifact swap** — artifact changed after attestation | Signature atomically binds `(artifact_hash, commit_sha, role, session_ids)`; CI verifies the signed hash matches the artifact **at the committed SHA**. |
| **Key theft** — sandbox exfiltrates a signing key | No long-lived key: **Sigstore keyless** (ephemeral OIDC-bound cert) + transparency log. Sandbox has no OIDC identity for the signing workload. |
| **Ledger tampering** — agent rewrites `dispatch_ledger.json` | Ledger is **out-of-band** (dispatcher-side datastore CI queries directly) and/or entries are signed + recorded in a transparency log; the in-repo `audit_log.py` hash-chain remains as tamper-*evident* defense-in-depth but is **not** the root of trust. |
| **Dispatcher compromise** (root of trust) | Keep the TCB **minimal and auditable**; formally check its attestation logic; CI re-derives independently where it can so a single bug doesn't silently pass. |
| **Self-heal infinite loop** (re-introducing C-LOOP-04) | Bounded attempts → HANDOFF, reusing the escalation discipline. |
| **Bypass via direct push** | Branch ruleset makes Pillar 1 a *required* status check; no merge path skips it. |

---

## 5. Data flow (happy path + rejection)

1. Dispatcher launches `implementer` (session `i`) in a sandbox → produces code + artifact.
2. Dispatcher launches `verifier` (session `v ≠ i`) in a **fresh** sandbox → runs the checks, emits the artifact bytes proving the requirement.
3. Dispatcher (TCB) reads the artifact across the boundary, **re-derives** `output_hash`, builds the Evidence_Record with **its own** `{role, i, v, requirement_id, commit_sha}`, and **signs** it (keyless).
4. **Local gate (Pillar 2):** loop driver runs `coverage_gate` + signature check on the slice. Clean → write `proven` + commit the signed attestation. Violation → refuse-advance + action-directive self-heal prompt to the verifier; bounded → HANDOFF.
5. **CI gate (Pillar 1):** on PR, re-derives the hash, verifies the signature + transparency record, runs the rego policy + Z3 + CodeQL. Pass → mergeable. Fail → blocked (and, because the local gate already ran, this should be rare — the unbypassable backstop).

---

## 6. What's built vs. what's needed

**Built (reusable):**
- Evidence_Record + `validate_evidence_record` + `output_hash` re-derivation — `tools/evidence_collector.py`.
- Coverage gate + policies — `tools/coverage_gate.py`, `.github/policies/{coverage,coverage_query}.rego`, `.github/workflows/coverage-gate.yml`.
- Z3 spec-completion — `tools/spec_validator.py`.
- Commit-trailer provenance parser — `tools/traceability_writer.py`.
- **Tamper-evident hash chain** — `tools/audit_log.py` + `tools/audit_verify.py` (keep as defense-in-depth; not the root of trust).
- Loop driver skeleton — `tools/run_state_driver.py`; dispatch substrate — `plane-integration/dispatcher.py`, `the_loop.py`.
- The in-session hook spine (now **demoted to main-loop steering**).

**Needed (new):**
1. **Attestation + keyless signing** — dispatcher signs `(artifact_hash, commit_sha, role, session_ids)`; Sigstore/cosign integration; CI signature verification step.
2. **Out-of-band / signed dispatch ledger** — role↔session provenance CI can query independent of the repo.
3. **Agent sandbox** — hard kernel boundary (**Firecracker microVM** recommended; **gVisor** lighter alternative), key + ledger inaccessible to the agent; dispatcher observes artifacts across the boundary (vsock / process output).
4. **Local pre-advance gate + bounded self-heal** — loop driver runs the gate per slice, refuses-advance, generates action-directive self-heal prompts, escalates to HANDOFF.
5. **CI completeness** — add signature verification + actor-separation + independent re-derivation to the rego/CI path; register as a required check in the branch ruleset.
6. **Dispatcher TCB hardening** — minimize + audit the attestation logic.

---

## 7. Why this also fixes the verifiability problem that started this thread

The binding gate is now **pure deterministic logic** (re-derivation, signature verification, rego, Z3, ledger cross-check) plus standard CI — **none of it depends on hooks firing in subagents or headless sessions.** Therefore, unlike the live multi-turn hook canary (un-runnable in this sandbox), this architecture is **ordinary, fully testable software**: unit + integration tests for the gate, a signature-forgery red-team test, a ledger-tamper test, and a CI dry-run. The "outstanding gate before fleet launch" stops being un-observable and becomes verifiable in CI.

---

## 8. Scope & decomposition

This is larger than one implementation plan. Proposed phasing (each its own plan):

- **Phase A — Evidence-as-source-of-truth (no crypto yet):** local pre-advance gate + bounded self-heal + CI rego completeness + actor-separation from the (still-trusted) ledger. Closes the *enforcement-layer* gap; defers the crypto.
- **Phase B — Cryptographic chain of custody:** dispatcher signing (keyless), out-of-band/signed ledger, CI signature verification, TOCTOU binding.
- **Phase C — Process isolation / sandbox:** sandboxed agent processes, TCB boundary, dispatcher-observes-across-boundary.
- **Phase D — TCB hardening + red-team:** minimize/audit the dispatcher, forgery/tamper test suite, formal check of attestation logic.

Phase A delivers the reliability win immediately (a self-graded flip can't advance or merge) using only deterministic, testable logic; B–D progressively harden the chain of custody to survive a hostile filesystem.

---

## 9. Resolved decisions (2026-06-22)

1. **Phasing:** ✅ **Phase A first, then harden (B–D).** Build the deterministic enforcement now (a self-graded flip can't advance or merge — fully testable, no crypto dependency), launch a *guarded* fleet on it, and harden the cryptographic chain of custody (B–D) after. Accepted tradeoff: until Phase B lands, the dispatch ledger/provenance is trusted-but-not-yet-cryptographically-sealed.
2. **Signing:** ✅ **Sigstore keyless** (OIDC → ephemeral cert → Rekor transparency log). No long-lived key for any sandbox to steal; CI verifies against the transparency record.
3. **Sandbox substrate:** ✅ **Firecracker microVM** (hard KVM boundary; recommended) with **gVisor** as the lighter-ops alternative — over shared-kernel containers/jails, since the agent is untrusted code. Finalized concretely in Phase C.

**Next:** writing-plans for **Phase A** (local pre-advance gate + bounded self-heal + CI rego/actor-separation completeness — deterministic, testable, immediate reliability win).

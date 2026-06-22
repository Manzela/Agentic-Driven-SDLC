/eff# The First Thing Before Fleet Execution — a Fix-First + Negative-Control Live-Canary Gate

- **Date:** 2026-06-21
- **Status:** Decisions resolved (§7); claims independently re-verified (§3 note) — awaiting approval to proceed to the implementation plan
- **Branch of record:** `worktree-agentic-sdlc-optimization` (HEAD `3fbfe67`)
- **Decision driver:** Execution model = **autonomous fleet, spine-governed** (user-confirmed). The backlog will be executed *by* Claude Code agents that the steering spine is supposed to govern.
- **Evidence base:** 7-agent verification workflow `wf_7879c157-f3d` (6 parallel deep-readers + adversarial false-green critic), **then an independent first-hand re-check** (hooks executed with crafted stdin; official Claude Code hooks docs consulted for the harness contract). All claims cited to `file:line`/doc on disk as of 2026-06-21. The re-check confirmed 12/13 P0–P1 defects, **corrected D1's mechanism + fix and downgraded D12**, and added D14 — see §3 note.

---

## 1. The question and the one-line answer

> *"What should be the first thing to do before we begin executing the full plan and tasks in Plane, per `.kiro/specs/spec-to-evidence-control`?"*

**Make "the spine actually governs a live agent" a machine fact — not a self-report — before a single fleet agent runs.** Concretely: **fix the verified-broken controls first, then prove the spine with a *negative-control* live canary (a real `claude -p` session in which every gate is forced to emit at least one real block), then consolidate onto the branch the fleet runs from.** Only a green negative-control canary unblocks the fleet.

This *is* Phase 0 of the spec ("every spine component must be coded, wired, and **smoke-tested** before any Phase 1 task begins" — `tasks.md:5`). The first thing before executing the plan and the first task of the plan are the same move — but the smoke test must be the real gate, not the in-process simulation that exists today.

---

## 2. Why this is the first thing (and not backlog task #1)

The platform's entire thesis is **"done is a machine fact, not a self-report,"** enforced by a six-hook governance spine (SessionStart, PreToolUse, PostToolUse, SubagentStop, Stop, PreCompact). A forensic audit found that in the audited sessions the spine **was never wired**, so Claude Code fired the globally-installed `ralph-loop` plugin Stop hook instead — which re-injected an identical mega-prompt **49×** (root cause **C-LOOP-04**) and forced ~24 idle "standing by" turns.

If we launch an autonomous fleet now, every backlog task is executed under exactly the governance condition the project exists to eliminate. The governor must be **on and proven** first, or the fleet reproduces the failure at scale.

**The trap:** it *looks* done. There is a tracked `.claude/settings.json` wiring all six hooks, all six hook files exist, four actor definitions exist, and **243 spine unit tests pass in 0.4s**. That green is the *original blind spot reincarnated* — the audit's whole finding was that unit tests passed while the live wiring was absent or wrong. Trusting "243 green + settings.json present = ready" is itself the self-report the project distrusts.

---

## 3. Key finding: the spine is *wired-but-broken*

The investigation verified, on disk, that the wiring exists but multiple load-bearing controls are **non-functional in a real session**. These are not design opinions — each was reproduced by running the hook or reading the exact line.

> **Verification note (2026-06-21, independent re-check).** Every P0 claim below was re-derived first-hand (hooks run with crafted stdin; behavioral output read). Two corrections to the original investigation were found, both load-bearing:
> - **The actor-identity mechanism rests on a non-existent variable.** Per the official Claude Code hooks docs, **there is no `CLAUDE_AGENT_NAME` env var** (the documented hook vars are `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_EFFORT`, `CLAUDE_ENV_FILE`, `CLAUDE_CODE_REMOTE`). Subagent identity is delivered in the **hook stdin JSON** as `agent_type` (e.g. `"verifier"`, **no `.md` suffix**) and `agent_id`. So `actor_identity.resolve_identity` (which reads `os.environ["CLAUDE_AGENT_NAME"]`) resolves **`"main"` for every actor**, and the gate constant `"verifier.md"` is doubly wrong (wrong source *and* wrong format). This reframes D1's mechanism and **inverts the fix** (see D1, and Stage-0 item 1). The repo's `tests/spine/test_actor_identity.py` sets `CLAUDE_AGENT_NAME="implementer.md"` — it validates a **fiction** (see D14).
> - **The decision-channel contract is authoritative:** exit 2 ⇒ *"Claude Code ignores stdout… stderr text is fed back to Claude"*; the only valid Stop/SubagentStop decision value is `"block"` (omit to allow) — `"approve"` is ignored. This confirms D6 and **downgrades D12** from "self-grade bypass" to a conformance nit.

### 3.1 Blocking defects (P0 — a meaningful canary is impossible until these land)

| # | Defect (VERIFIED LIVE) | Evidence | Consequence |
|---|---|---|---|
| D1 | **Actor-identity is sourced from a non-existent variable.** `actor_identity.py:44` reads `os.environ["CLAUDE_AGENT_NAME"]`, which **Claude Code never sets** → every actor resolves to `"main"`. The gate constant `"verifier.md"` is also the wrong format (real `agent_type` is suffix-less `"verifier"`). Frontmatter `name: verifier` is *correct*. | `actor_identity.py:44` (reads missing env var); gate sites `subagent_stop_hook.py:30`, `pre_tool_use_hook.py:25`, `store.py:95`, `coverage.py:21` (`"verifier.md"`); official hooks docs (no `CLAUDE_AGENT_NAME`; `agent_type` in stdin) | **Every legitimate proven-flip is rejected** (`"main"` ≠ `"verifier.md"`) → guaranteed stall on the first real task; **and** actor-independence provides *zero* real separation (every actor is `"main"`). Canary may instead close its slice via the ungated D2 path. *Single weakest link.* **Fix is to read `agent_type` from stdin against a suffix-less role constant — NOT to rename the agent or append `.md`.** |
| D2 | **PreToolUse authority is inert.** It keys on a phantom `tool_input['field']` key that no real Edit/Write/Bash payload carries; falls through to allow at line 47. | `pre_tool_use_hook.py:37,41,47` — live run: implementer Edit `unproven→proven` → `{"decision":"allow","reason":"coverage-model write permitted"}` exit 0 | A non-verifier flips status via a normal Edit and it's **allowed**. The authority gate does nothing on real writes. |
| D3 | **Bash-write guard absent.** Hook reads only `file_path`; never inspects `tool_name`/Bash command. | `pre_tool_use_hook.py` (no command parsing); live run: `Bash: echo x > tests/spine/x.py` → `allow` | Protected paths (`tests/`, `schema/`, `.claude/`) are writable via Bash redirect by any agent. |
| D4 | **`human_signed` is forgeable.** Read from agent-controlled `tool_input`. | `pre_tool_use_hook.py:74` | An autonomous agent self-exempts an item from the `in_scope` gate by setting `human_signed:true` in its own payload. |
| D5 | **Stop has no reentrancy guard.** `stop_hook_active` is never read. | grep `stop_hook_active` → absent; live: `{stop_hook_active:true,…}` → exit 2 (still blocks) | The spine's **own** Stop hook reproduces C-LOOP-04 under forced continuation. |
| D6 | **Exit-2 reason goes to stdout, not stderr.** | `stop_hook.py:237`, `subagent_stop_hook.py:109` — stderr empty on exit 2 | Claude Code ignores stdout on exit 2 → the agent is **blocked blind**, no steering text reaches it. |
| D7 | **ralph-loop not disabled in live settings.** No `enabledPlugins` block; ralph enabled at user level. | live `.claude/settings.json` (no `enabledPlugins`); `~/.claude/settings.json` ralph=`true` | ralph's `stop-hook.sh` still fires in parallel with the governance Stop hook (C-LOOP-04 mechanic intact). |
| D8 | **No run_state populator; store defaults to `:memory:`.** `save_run_state` is called only in a demo `__main__` and a unit test. | `store.py:914`, `tests/spine/test_store.py:117`; `store.py:17-19` | The Stop completion gate runs on the streak-0 fallback or allows payload-less stops (`stop_hook.py:225-232`). "COMPLETE via Stop" means **"not gated,"** not "gate passed." |
| D9 | **No live-session canary infrastructure at all.** `prove_trivial_slice.py` and `test_spine_e2e.py` import hook modules in-process with **literal** session-ids; nothing spawns `claude -p`, reads a transcript, counts re-injections, detects ralph firing, or records hook-fired evidence. | `prove_trivial_slice.py:37-60` (zero subprocess); `tests/integration/test_spine_e2e.py:48-72` | The thing that would *prove* the failure is gone is the one artifact that does not exist. |

### 3.2 Secondary defects (P1 — must be covered by the canary or fixed alongside)

| # | Defect | Evidence | Consequence |
|---|---|---|---|
| D10 | **`proposed/01-settings.json` regresses PreCompact.** Its comment falsely says PreCompact is unbuilt; it omits the registration the live file has. Its `SPINE_REQUIRED_EVENTS` env targets A5 logic that doesn't exist live (inert). | `proposed/01-settings.json` (5 events, no PreCompact); live `pre_compact_hook.py` exists + is registered | Applying it **verbatim drops a working hook.** The hardened settings must be *corrected*, not copied. |
| D11 | **A5 SessionStart spine self-check is unbuilt.** The "make un-wiring loud" mechanism lives only in `proposed/05-session_start_hook.py`, never applied. | grep `SPINE_REQUIRED_EVENTS`/`registered_commands` in live hooks → absent | A future un-wiring stays **silent** — root cause C-HOOK-01 uncaught. |
| D12 | **SubagentStop accept path emits `decision:'approve'`** — not a valid Stop/SubagentStop decision value (only `"block"` or omit). **Corrected severity (was P1):** harmless, not a bypass — `"approve"` is ignored and exit 0 allows; self-grades are still blocked by exit 2 (lines 70–72). Conformance cleanup only (align to `tasks.md:226`). | `subagent_stop_hook.py:84`; official docs (valid value = `"block"`) | Code-conformance nit, **P2**. The real residue on this hook is D6 (its block reason is on stdout → ignored on exit 2). |
| D13 | **Steering content is the naive lineage.** No root `CLAUDE.md` anywhere; goal directive materialized nowhere agents read; live base-prompts hardcode thresholds (85% / 15 min / 7 / 1,000,000), leak which hook gates them, and emit bare-verdict block messages. | no `CLAUDE.md` (worktree or main); `implementer.md:44-50`, `verifier.md:3,63`; block strings in `pre_tool_use_hook.py:43-52` | **This is the user's stated concern directly:** vague blocks + leaked internals are the documented driver of the agent "fixing the hook" instead of being steered. |
| D14 | **The actor-identity tests validate a fiction.** `tests/spine/test_actor_identity.py` exercises `CLAUDE_AGENT_NAME="implementer.md"` — a variable Claude Code never sets and a format (`.md`) `agent_type` never uses. The 243-green suite is **green over a contract that does not exist** — the original blind spot, concretely. | `tests/spine/test_actor_identity.py:7`; official hooks docs | Unit-green contributes nothing to the real-session verdict; the identity tests must be rewritten to the `agent_type` stdin contract and re-run. Reinforces why Stage 1 must be a real `claude -p` run. |

### 3.3 What *is* sound (do not re-do)

- SubagentStop **decision logic** is correct and live: anti-spoof (`actor==CLAUDE_AGENT_NAME`), distinct sessions, and output-hash **re-derivation** all block correctly (`subagent_stop_hook.py:57-77`).
- Stop **HANDOFF-before-block ordering** (the infinite-block fix) is intact (`stop_hook.py:104-179`).
- The three non-gate hooks fail **open** by contract (SessionStart exit 0, PostToolUse exit 1, PreCompact exit 0).
- **Branch consolidation is mostly done:** `main` is a strict ancestor of `worktree-agentic-sdlc-optimization` (branch +27, main +0) and `main` already carries the same settings.json + 6 hooks + 4 agents. `spec-reconciliation` is the *old partial* spine (no settings.json, 3 hooks) — **not** the fleet branch.

---

## 4. Design: the three-stage first-thing gate

The principle: **apply the project's own doctrine to its own foundation.** "The spine is ready" must be established the same way the spine forces every task to establish "done" — by machine-checked evidence from a real run, with negative controls, not by assertion.

```
Stage 0  FIX-FIRST ──▶  Stage 1  NEGATIVE-CONTROL LIVE CANARY ──▶  Stage 2  CONSOLIDATE & GATE
(land the broken          (one real claude -p session; every          (single fleet branch;
 controls)                 gate forced to block at least once)         dispatcher refuses
                                                                       ungoverned cwd)
        │                            │                                         │
        └────── exit criterion: canary GREEN ⇒ fleet unblocked ───────────────┘
```

### Stage 0 — Fix-first (the blocking set)

Land these before the canary can mean anything. Most have a staged source in `audit/steering-audit/proposed/` that must be **reconciled** (not copied verbatim — see D10).

1. **Fix the actor-identity source + single-source the role constant (D1, D14).** Rewrite `actor_identity.resolve_identity` to read the documented **`agent_type`** field from the hook stdin JSON (default `"main"` for the root session), **not** the non-existent `CLAUDE_AGENT_NAME` env var. Define one suffix-less role constant (`VERIFIER_ROLE = "verifier"`) in a shared module imported by `pre_tool_use_hook.py`, `subagent_stop_hook.py`, `store.py`, `coverage.py` — drop the four `"verifier.md"` literals. **Do NOT rename the agent files or append `.md`** (frontmatter `name: verifier` is already correct). Rewrite `tests/spine/test_actor_identity.py` to the `agent_type` contract. Verify against a real spawned verifier subagent whose stdin carries `agent_type: "verifier"`.
2. **Correct + apply the hardened `settings.json` (D7, D10).** Six events **including PreCompact**, `${CLAUDE_PROJECT_DIR}`-relative command paths, per-hook timeouts, `enabledPlugins: {ralph-loop@claude-plugins-official: false}`. Fix the proposed file's false PreCompact-deferred premise first.
3. **Stop reentrancy + stderr channel (D5, D6).** Add the `stop_hook_active` short-circuit (exit 0, zero tokens on re-entry); move exit-2 reasons to **stderr** for Stop and SubagentStop.
4. **Real PreToolUse authority (D2, D3, D4).** JSON-delta predicate that detects `status` and `in_scope` flips in actual Edit/Write/MultiEdit/Bash payloads; Bash-command write-redirect detection for protected paths; resolve `human_signed` from an out-of-band `HUMAN_SIGNED` env / signature artifact.
5. **SubagentStop decision value (D12).** Emit block-or-omit (never the no-op `approve`); single-source the verifier role.
6. **A5 SessionStart spine self-check (D11).** Apply `proposed/05`: read the effective registration, detect missing-event / wrong-script / ralph-shadow, emit `GOVERNANCE SPINE PASS/FAIL` loudly.
7. **File-backed run_state populator (D8).** A thin loop driver that writes `iteration_count / no_progress_n / budget_exceeded / violation_count` to a **file-backed** store and pipes `run_state + feature_list` into the Stop event. Verify cross-process round-trip.
8. **Steering content (D13).** Materialize a root `CLAUDE.md` at the run cwd and/or SessionStart `additionalContext` carrying the goal directive + actor-independence doctrine; rewrite every block string to name **one imperative next action**; source thresholds from config in both hooks and prompts.

### Stage 1 — Negative-control live canary (the real gate)

A canary runner (`tools/run_spine_canary.py`, to be built) that spawns **one real bounded `claude -p` session** over a slice **designed to trip every gate**, then checks assertions against the **session's own transcript + a hook-fired evidence sink** — never in-process function returns.

**Canary setup (decided):** for the canary window, also remove/rename `ralph-loop` at the **user level** (`~/.claude/settings.json`) — belt-and-suspenders — so project-vs-user plugin precedence is not itself the variable under test; restore it afterward. The `ralph did not fire` assertion is then unambiguous. (The project-scoped disable from Stage 0 remains the real-fleet control; this only de-risks the canary's signal.)

**Validity precondition:** the canary is INVALID if any hook ran in-process. Assert a non-empty real `transcript.jsonl` exists. The 243 unit tests are necessary-not-sufficient and contribute **nothing** to the verdict.

**Assertions (all must hold):**

| Class | Assertion |
|---|---|
| **Registration** | Applied `settings.json` registers all **six** events with `${CLAUDE_PROJECT_DIR}` paths + timeouts; A5 self-check reports the spine fully wired and ralph **off** (positive assertion from the merged plugin set, not inferred from silence). |
| **Negative control — protected path** | implementer Edit **and** Bash-redirect to `tests/` / `.claude/settings.json` → **both exit 2**. |
| **Negative control — authority** | implementer real Edit flipping `status unproven→proven` → exit 2; `in_scope` flip with payload `human_signed:true` but no env → exit 2. |
| **Negative control — completion gate** | an in-scope item left unproven at Stop → `decision=='block'` (the gate actually bites at least once). |
| **Negative control — self-grade** | same-session proven-flip → SubagentStop **prevents the state change** (item stays unproven), verified at the harness level, not just a returned value. |
| **Anti-loop** | drive a Stop **block then forced continuation** → second Stop exits 0 emitting **zero tokens** (no identical re-injection); first block reason was on **stderr** (non-empty). |
| **Re-injection = 0** | counted by **normalized** near-duplicate similarity (strip digits/timestamps/whitespace; Jaccard ≥ 0.9), **and** ralph `stop-hook.sh` asserted **not executed** via hook-command telemetry. No idle "standing by" tail (≥2 consecutive no-tool-use turns). |
| **Hooks fired** | a hook-fired evidence sink records `{hook_event, command_path, session_id}`; all six events fired ≥1× in **both** the root session **and** a real spawned subagent; `CLAUDE_PROJECT_DIR` non-empty and the stdin `agent_type` field present (= `"verifier"`) in the subagent runtime. |
| **Positive path** | the slice reaches `proven` **only** via a real verifier subagent (resolved actor `"verifier"` from stdin `agent_type`, `verifier_session_id != implementer_session_id`, both traceable to the transcript) with an evidence block whose `output_hash` re-derives from a real artifact. |
| **Cwd-invariance** | re-run from a different cwd (repo root, a subdir) → SessionStart still fires against the correct project dir. |
| **Governance terminal** | `run_state.status ∈ {complete, handoff}`, `terminated_by=='governance_stop_hook'`, `watchdog_kill` and `manual_stop` both false; turn count well under `--max-turns`. |

### Stage 2 — Consolidate & gate the fleet

1. **Single fleet branch (decided): merge `worktree-agentic-sdlc-optimization → main` and run the fleet from `main`.** `main` is already a strict ancestor (branch +27, main +0), so the merge is fast-forward-clean and the Stage-0 fixes land on mainline. `spec-reconciliation` (the old partial spine) is retired as non-canonical. Gate the fleet on `git rev-parse --abbrev-ref HEAD == main`.
2. **Dispatcher preflight (fail-closed).** `dispatcher._exec_claude` refuses to spawn unless `(cwd/.claude/settings.json).exists()` **and** it disables ralph. No silent ungoverned no-op.
3. **Re-run the canary on the chosen fleet branch** to confirm the wiring traveled.

---

## 5. Exit criterion (the machine fact that unblocks the fleet)

> A **negative-control live canary** on the chosen fleet branch is GREEN: every blocking gate emitted ≥1 real block on its forced violation; re-injection = 0 across a real block-then-continue cycle with ralph proven absent; all six hooks fired in both root and subagent runtimes; the slice reached `proven` only via a real verifier; and termination was a governance `complete`/`handoff`. The canary ran as a real `claude -p` process (non-empty transcript) — no in-process simulation contributes to the verdict.

Until that exists, the fleet stays blocked. "243 green + settings.json present" explicitly does **not** satisfy this.

---

## 6. Scope boundaries

**In scope (the first thing):** Stages 0–2 above — the fix-first set, the canary runner + its evidence sink + run_state populator, branch consolidation, dispatcher preflight.

**Explicitly out of scope (deferred, not gating):**
- Building out the full board→agent fleet supervision (cron/systemd for `dispatcher.py --watch`, webhook endpoint) beyond the single proven-once dispatch and the preflight guard.
- Phase 1+ backlog execution itself.
- The optional Phase-5 durability models (`durable_orchestrator.py`, `event_bus.py`) — already self-described reference models, off the delivery path.
- P2 hardening surfaced by the audit but not gating a correct canary: status-enum near-miss messaging, repo-root depth validation, prompt-internal-leak reframing. These should be logged as follow-ups.

---

## 7. Resolved decisions (2026-06-21)

1. **Fleet branch:** ✅ **Merge `worktree-agentic-sdlc-optimization → main`, run the fleet from `main`.** Re-run the canary on `main` after merge to confirm the wiring traveled.
2. **Fix-first breadth:** ✅ **Full set** — all 8 Stage-0 items, **including** the steering-content layer (item 8 / D13). The "agent loops correcting the hook instead of being steered" concern is fixed as part of the first thing, not deferred.
3. **ralph isolation:** ✅ **Belt-and-suspenders** — disable `ralph-loop` at the user level for the canary window (restore after), in addition to the project-scoped disable.

---

## 8. Why not the lighter options

- **Static-wire (apply settings + lean on the 243 tests):** rejected — it is the original blind spot exactly. Green units coexist with all nine P0 defects, every one verified broken live.
- **Trivial happy-path canary:** rejected — a one-turn slice never trips a gate, so "no re-injection" is vacuously true, the reentrancy/stderr bugs never fire, and the slice can close through the D2 authority hole. Only **negative controls** turn the canary into a gate instead of a green light over an unwired spine.

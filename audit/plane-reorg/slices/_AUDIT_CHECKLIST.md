# Audit checklist (compact) — for Plane cross-reference

The board must address these. Cross-reference every backlog item against this list.

## Master defect
- **Pattern-1 — unregistered governance spine**: no `.claude/settings.json` on the run branch → none of the 6 designed hooks ever fired; the ralph-loop plugin Stop hook ran instead. 13 of 18 findings collapse to this.

## 18 verified findings
| id | sev | type | one-line |
|----|-----|------|----------|
| A-HOOK-01 | P0 | HOOK_MISFIRE | wrong Stop hook fired 64× (ralph-loop no-op); repo `stop_hook.py` never ran |
| A-INTENT-01 | P0 | INTENT_GAP | six-hook spine inert — no settings.json registration |
| A-IDLE-01 | P1 | IDLE_WASTE | loop hand-cranked by manual nudges; Stop gate never auto-continued |
| A-AMBIG-01 | P2 | AMBIGUITY | "1:1 aligned w/ latest spec" + mid-session spec rewrite → re-grounding; no SessionStart integrity hash |
| A-LOOP-01 | P2 | LOOP | 3-round teardown — no checkable success oracle for disable/teardown tasks |
| A-REDUN-01 | P2 | REDUNDANCY | verify-by-re-read churn; no PostToolUse forcing-function |
| B-INTENT-01 | P0 | INTENT_GAP | spine inert; settings.json not on run branch |
| B-INTENT-02 | P0 | INTENT_GAP | four agent base-prompts absent (`.claude/agents` only .gitkeep); impl+verify one actor |
| B-HOOK-01 | P1 | HOOK_MISFIRE | wrong Stop hook fired (plugin), not repo |
| B-IDLE-01 | P1 | IDLE_WASTE | 7.6-min human-gated stall; no autonomous forward path |
| B-AMBIG-01 | P2 | AMBIGUITY | task named a non-existent in-repo target; no hedge clause |
| B-REDUND-01 | P2 | REDUNDANCY | serial grep/ls to prove absence; no orientation-pass-first habit |
| B-OVERSPEC-01 | P2 | OVER_SPECIFIC | ANN101 lint detour edited shared pyproject.toml; lint treated as gate |
| C-HOOK-01 | P0 | HOOK_MISFIRE | wrong hook fired entire session |
| C-INTENT-02 | P0 | INTENT_GAP | lattice inert; 3 of 6 hooks don't exist; project-vs-product cwd split |
| C-LOOP-04 | P0 | LOOP | ralph Stop hook re-injected identical block 49×; no `stop_hook_active` reentrancy |
| C-IDLE-03 | P1 | IDLE_WASTE | 24 forced idle "standing by" turns while blocked on external inputs; no HANDOFF-on-blocker |
| C-REDUND-06 | P2 | REDUNDANCY | heavy redundant build/verify/style loops; no PostToolUse forcing-function |

## 10 remediation artifacts (staged in audit/steering-audit/proposed/)
- **01-settings.json** — register all 6 hooks (THE master fix; resolves Pattern-1 + the HOOK/INTENT findings)
- **02-stop-hook steering** — `stop_hook_active` reentrancy + HANDOFF-before-block + escalate-not-repeat (C-LOOP-04, C-IDLE-03, A-IDLE-01)
- **03-pretool steering** — refusals→steering + JSON-delta field authority (A-INTENT-01, field-authority)
- **04-subagentstop steering** — corrective evidence-gate steering
- **05-session_start_hook.py** — spine self-check canary + re-orient + resume integrity (A-INTENT-01 detection, A-AMBIG-01)
- **06-post_tool_use_hook.py** — forcing function: targeted checks → corrective next step (C-REDUND-06, A-REDUN-01)
- **07-agent base-prompts** — verifier/implementer/initializer/researcher actor-independence (B-INTENT-02)
- **08-goal directive** — bounded autonomy + `BLOCKED-ON:` sentinel + anti-idle (A-IDLE-01, C-IDLE-03)
- **09-CLAUDE.md** — durable invariants + 4 P2 doctrines (A-LOOP-01 success-oracle, B-AMBIG-01 hedge-on-named-targets, B-OVERSPEC-01 lint-is-advisory, B-REDUND-01 orientation-pass-first)
- **00-charter** — the tier-1 base-prompt engineering standard (CH-01 next-action-not-verdict, CH-06 kill-the-refire, CH-07 reentrancy, CH-08 HANDOFF-before-block)

## Named prerequisites (NOT yet authored — must exist for full execution)
- **loop driver / run_state populator** (external_blocker, no_progress_n, budget_exceeded, iteration_count)
- **tools/execution_bounds** (threshold + role registry)
- **PreCompact checkpoint hook** (produces resume_state_hash)
- **tools/spec_validator.py** + a **feature_list.json** instance (runtime coverage model)
- **disable/scope the ralph-loop plugin** so it can't shadow the governance Stop gate

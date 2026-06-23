# Phase-1 Verification Depth — Design Specification

- **Date:** 2026-06-23
- **Status:** Design approved (decisions locked via brainstorm + 4-lens adversarial red-team). Ready for `writing-plans`.
- **Scope:** `.kiro/specs/spec-to-evidence-control/tasks.md` tasks **18–26** plus their CI-wiring siblings (**21.4 / 40.4 / 14.2 amendment**) and the `execution_bounds` / ruleset / hook / docs deltas they imply. This is a **design**, not a plan: it states the target shape, the exact built-vs-missing delta against the live tree, the actor that owns each change, and an ordered TDD-sized decomposition. It does not re-implement what already exists.
- **Builds on:** `docs/superpowers/specs/2026-06-22-zero-trust-evidence-gate-design.md` (Phase A/A.5 — the deterministic evidence gate). This is the roadmap's **Phase 1 — Depth**.

> **Ground-truth note.** Every "live" claim below was verified against the working tree (orphan_detector.py, evidence_gate.py, loop_gate.py, pre_tool_use_hook.py, post_tool_use_hook.py, wiring_checker.py, coverage_gate.py, coverage_query.rego, the workflows, `.gitleaks.toml`, `execution_bounds.py`, and the spec `requirements.md`/`design.md`) by 9 parallel reader agents, then adversarially red-teamed by 4 diverse-lens skeptics (bypass / consistency / completeness / public-flip). Where a first draft asserted a behavior the code does not have, this revision corrects it and re-classifies the work.

---

## Reconciliation — locked decisions + 2026-06-23 ground-truth deltas

**Locked decisions (from the brainstorm — design AROUND these, do not relitigate):**

1. **Scope** = the **full** `.kiro` Phase 1 (tasks 18–26).
2. **Rollout** = **diff-aware / baseline**: blocking gates block ONLY findings the PR introduces + a path-allowlist exempting the existing control-plane `tools/` so day-one merges aren't all blocked.
3. **SAST tools** = **Semgrep** (OSS, gates now, custom WIRING rules, diff via `--baseline-commit`, runs CI AND locally) **+ CodeQL** (own workflow) **+ SonarCloud** — all gating.
4. **Visibility** = the repo is **PUBLIC** (flipped 2026-06-23), which makes CodeQL + SonarCloud free.
5. **Enforcement** = **dual**: every depth check runs BOTH in the local pre-advance gate (`loop_gate.gated_advance`, for autonomous self-heal) AND as required CI status checks (the unbypassable backstop). CodeQL is CI-only (too heavy per-slice); Semgrep + orphan run locally too.

**Resolved open questions (from the red-team):**

- **SonarCloud, not self-hosted SonarQube.** The public-repo free tier + New-Code reference-branch model assume hosted SonarCloud; the requirements.md term "SonarQube" is amended to SonarCloud (human-owned edit, §9).
- **Fork-PR posture = Semgrep-gates-forks.** Sonar/CodeQL are same-repo-only (they need secrets / SARIF write a fork PR cannot have); Semgrep-OSS is the binding SAST backstop for fork PRs (§3.6). Accepted trust posture: external PRs are gated by Semgrep + the post-merge nightly, not by CodeQL/Sonar pre-merge.
- **PostToolUse exit code = keep the live exit-0-with-`additionalContext`** behavior; amend the spec text ("exit 1" in 18.1/26.1) to match (§2.4).

**2026-06-23 ground-truth deltas since the red-team ran (fold into the plan):**

- **Repo is now PUBLIC** (was "will be flipped"). The §6 pre-public hygiene is therefore POST-public remediation — **partly done already via PR #31 (merged, `bc76611`)**: live infra fingerprints redacted (VM origin IP → `secrets.VM_HOST`; project UUID / CF account id / owner UUID / workspace slug removed as code defaults), and the over-broad `.gitleaks.toml` `docs/*.md` blanket replaced with precise value/path allowlists (`regexTarget="match"`). **Remaining §6 items:** the project UUID in 2 `audit/plane-xref/board-snapshot*.json` data dumps (deferred — data artifacts), **`main` branch protection** requiring the same gates (§3.5 precondition), and CodeQL/Sonar **`main` baseline seeding** (§3.8). Two non-code owner actions remain: lock OCI ingress to Cloudflare IP ranges, and confirm the `a411f976…` doc `SECRET_KEY` was never a live value.
- **SonarCloud is ALREADY WIRED** — the `SonarCloud Code Analysis` check passes on PRs today. Task 22 is therefore **PARTIAL (mostly done)**, not MISSING as the matrix below originally read; the remaining task-22 work is the New-Code definition + the 85%-coverage quality gate + the same-repo-only fork guard + the required-check registration, not the integration itself.

---

## 0. Threat model — what a hostile or sloppy actor must NOT be able to do

The gate is only as strong as its weakest evasion. The design closes all of these (each has a §-anchored fix and a required red-team assertion in §8):

| # | Evasion | Closed by |
|---|---|---|
| T1 | "Trace" a new untraceable function with a **fabricated** `REQ-NONEXIST-999` trailer | §3.1 validity cross-check (a ref counts only if the id exists in the model) |
| T2 | **Self-exempt** an entire file with one stray `orphan-exempt` substring in a docstring/comment | §3.2 line-anchored, reason-required, symbol-scoped marker + diff-aware on new markers |
| T3 | Add a new in-scope **backward orphan** that no changed `.py` textually references | §3.3 backward diff scoped to **model deltas**, not code references |
| T4 | Make `git merge-base` unreachable (shallow checkout) so the gate degrades to **full-repo pass** | §3.4 CI fails-closed on unreachable base; full-repo fallback is **local-only** |
| T5 | **Poison the baseline** by landing a finding on `main` first | §3.5 `main` branch-protection precondition (listed dependency, §9) |
| T6 | Shadow an AST dead-wiring finding with a benign same-qualname **Semgrep "clean"** | §2.1 de-dup is **union-of-concerns**, not winner-take-all |
| T7 | **Fork PR** with a new finding evades the gates that need secrets (Sonar/CodeQL) | §3.6 Semgrep-OSS is the fork backstop; secret-bearing gates not required for forks |
| T8 | Prove a WIRING item with a **unit-test** Evidence_Record | §2.3 gate denies proven WIRING unless `evidence_kind=='integration'` |
| T9 | Birth a new item **at `status:proven`** to skip the verifier | §2.2 insertion rule denies any non-`unproven` birth from a non-verifier |

---

## 1. Goal + architecture

**Goal.** Raise the merge bar from *"evidence is internally valid"* (Phase-0/A zero-trust gate) to *"the change introduces no new SAST finding, no new traceability orphan, no new dead wiring, and every WIRING proof is an integration proof"* — **without** blocking day-one merges on the pre-existing debt of the control-plane (`tools/`), and **without** any agent gaining the ability to self-grade, hardcode a threshold, or edit a human-owned artifact.

**Dual-layer enforcement (LOCKED #5).** Every depth check runs in two places that share one decision module:

| Layer | Where | Binding? | Posture on failure |
|---|---|---|---|
| **Local pre-advance gate** | `tools/loop_gate.gated_advance` (autonomous self-heal loop) | Advisory to the *run* (steers the agent); cannot let an unproven item merge | refuse-advance → bounded self-heal → `block_streak → HANDOFF` |
| **CI required status checks** | `.github/workflows/*.yml` registered in the ruleset | **Binding** — the unbypassable backstop | job exits non-zero → merge blocked |

This mirrors the zero-trust doctrine: **in-session hooks are best-effort steering; the binding gate is CI + the local pre-advance gate.** The `post_tool_use_hook` (task 18) is the *third*, softest surface — edit-time feedback only, **never** exit 2 (PostToolUse contract).

**Diff-aware / baseline (LOCKED #2).** Blocking gates block **only findings the PR introduces**, computed against a merge-base. A path-allowlist exempts the existing control-plane `tools/` so the gate is usable now. The *reporting* surface still shows exempted findings (enforcement-deferral ≠ reporting-silence). **Critically — diff-awareness is a softening, so every soft edge is itself a potential evasion (§0/T1–T7); the diff machinery is hardened in §3 before any gate is registered.**

**Repo is public (LOCKED #4).** CodeQL + SonarCloud are free for public repos. A pre-public hygiene step was a hard precondition; the flip happened early, so it is now post-flip remediation (§6, partly landed via PR #31).

**Pillars** (the local gate's decision shape):

```
Pillar 0  evidence-validity   (EXISTS) four-field + hash-rederive + actor-separation  [fail-CLOSED, trust core]
Pillar 1  diff-aware SAST      (NEW)    Semgrep HIGH/CRITICAL on PR-introduced findings [fail-OPEN local / closed CI]
Pillar 2  diff-aware orphans   (NEW)    forward+backward orphans the PR adds, tools/-exempt [fail-OPEN local / closed CI]
```

A slice advances only when **all** active pillars accept. Any rejection routes through the *existing* `block_streak → HANDOFF` escalation — **no new C-LOOP-04 is created** (LOCKED #5). The new fail-OPEN pillars are kept as **separate functions** so the fail-OPEN posture never leaks into `check_slice` (the proven-evidence trust core, which stays fail-CLOSED).

---

## 2. Component matrix (tasks 18–26)

Granularity is **per task**, citing the live tree. **Do not rebuild BUILT rows.**

| Task | Component | State | Exact delta (what is actually missing) |
|---|---|---|---|
| **18** | `.claude/hooks/post_tool_use_hook.py` | **PARTIAL — broken wiring leg** | Hook runs ruff + `semgrep` and **always exits non-block** (correct). **Three deltas:** (a) the wiring leg is **non-functional** — `_real_wiring` does `from tools.wiring_checker import check_wiring`, but `wiring_checker` exports **no `check_wiring`** (only `analyze`, `emit_wiring_items`); the bare `except Exception: return []` silently degrades wiring feedback to empty on every edit. Fix to call `analyze(...)` → `emit_wiring_items(...)`. (b) add the `mypy` runner (task 18.1 lists type-check; `_default_runners` wires only lint/sast/wiring). (c) optional `--baseline-commit` diff-aware filtering. **Exit-code reconciliation (§2.4):** spec text says "exit 1", the live hook exits 0 with `additionalContext`; keep exit-0, amend the text. None of these change the never-block contract. |
| **19** | `tools/wiring_checker.py` + WIRING ingestion + **failed-flip** | **PARTIAL** | `analyze()` + `emit_wiring_items()` complete. **Missing:** (a) the **19.3 ingestion path is BLOCKED by the live PreToolUse guard** (§2.2 — the premise "creating an unproven item is not a status change" is **false** against the live `_changed_coverage_fields`); (b) the **verifier `unproven → failed` flip** for unreachable WIRING symbols (criterion 8.2) is **unimplemented and unowned** (§2.3); (c) the de-dup contract with Semgrep (§2.1). |
| **20** | `tools/orphan_detector.py` + traceability-gate | **PARTIAL — matcher + exempt are evadable** | Detector is bidirectional with exit 0/1. **Missing/unsafe:** (a) the **forward matcher accepts any syntactic `REQ-XXX-NNN` token** with no cross-check against the model id set — fabricated-ID evasion (T1, §3.1); (b) the **`orphan-exempt` marker is a whole-file substring match** with no required reason — self-exempt-anywhere (T2, §3.2); (c) `--baseline-commit` diff-awareness with backward diff scoped to **model deltas** (§3.3); (d) a `tools/`-path allowlist; (e) the **`traceability-gate.yml` blocking caller does not exist** (task 40.4). |
| **21** | `.github/policies/coverage_query.rego` + `tools/coverage_gate.py` | **PARTIAL** | Four-field + actor-separation policy exists in both rego and Python twin; Property 22 PBT exists for the **twin**. **Residual:** (21.3) no `conftest test` runtime invocation of the rego — the rego is a **latent untested double**; (8.3) **`evidence_kind=='integration'` for proven WIRING is mandated but NOT gated** — a unit-test record proves a WIRING item today (T8, §2.3); (21.2/21.4) resolved in §5.1. **Do not rebuild the core policy.** |
| **22** | SonarCloud quality gate | **PARTIAL (mostly done — 2026-06-23 update)** | SonarCloud **is already wired and passing on PRs.** Residual: `sonar-project.properties` New-Code mode + the 85%-coverage quality gate, the **same-repo-only** fork guard (§3.6), and the required-check registration. The term "SonarQube" in requirements.md is amended to SonarCloud (§9). |
| **23** | CodeQL SAST | **MISSING** | No `.github/workflows/codeql.yml`. Needs Python CodeQL workflow, `fetch-depth: 0`, **same-repo-only SARIF upload** (§3.6), nightly `schedule` to seed the `main` baseline. CI-only (LOCKED #5). |
| **24** | `tools/semgrep_rules/wiring_dead_code.yml` | **MISSING** | No custom rules. Needs decorator-route / registered-callback **and job/scheduled-task** dead-code rules (all four 8.2 categories — §2.5) whose output matches `emit_wiring_items()`, plus the union-of-concerns de-dup contract (§2.1). |
| **25** | `.claude/hooks/pre_compact_hook.py` | **PARTIAL** | Checkpoints progress/feature_list/evidence. **Missing:** the `run_state.resume_state_hash` producer — it does not call `state_integrity.compute_state_hash()`, so SessionStart resume-integrity always lands on the no-baseline branch (Property 26 / COH-2 neutered). |
| **26** | `tests/integration/test_phase1_integration.py` | **MISSING** | Must exercise wiring → WIRING finding, the **verifier failed-flip** (§2.3), orphan forward+backward (exit non-zero), `conftest test` deny+pass, PostToolUse lint feedback, **and** the §8 red-team evasion suite (T1–T9). |

### 2.1 De-dup contract (19 ↔ 24) — union-of-concerns, not winner-take-all

Both sources key candidates by **symbol `qualname`**. The de-dup rule:

- A qualname flagged by **either** source is a finding. A Semgrep "clean" verdict **never** overrides an AST "orphan" verdict (closes **T6**).
- "Semgrep wins" means **only** that Semgrep's richer *metadata* (decorator/callback context) is preferred for the *reporting* of a shared qualname — a metadata-merge, not a verdict-override.
- De-dup happens **before** the write to `feature_list.json`. Task 24's rule output **must** conform to `emit_wiring_items()` shape so the merge is mechanical.
- The custom-rule author is bound by an explicit comment in `wiring_dead_code.yml`: *"A Semgrep clean result is advisory metadata; it cannot retract an AST orphan."*

### 2.2 WIRING ingestion (19.3) — the guard change this REQUIRES (corrected)

**The draft's premise is false against live code; re-classified from an assumed fact to a REQUIRED, currently-unbuilt hook change.** Verified live: for a **brand-new** item id, `_changed_coverage_fields` compares `after[id]` against an absent `before[id]` (`{}`), so `status:'unproven'` (≠ `None`) is reported as a *changed* `status` and `in_scope:true` as a *changed* `in_scope`. Result: an initializer/implementer `Write` that appends a new `unproven` WIRING item is **blocked** (R1 status-verifier-owned); even a verifier is blocked on R2 in_scope-human-owned unless `human_signed`. Empirically: initializer→block, implementer→block, main→block. Conversely a verifier seeding directly at `status:proven` is currently **allowed** — so the guard cannot distinguish "seed unproven" from "seed proven," and the fix must not open a hole where any new item is born proven.

**Concrete required guard change** (to `.claude/hooks/pre_tool_use_hook.py`, a PROTECTED artifact — owned by main/human, §10):

1. In `_changed_coverage_fields`, classify an item id **absent from `before`** as an **INSERTION**, distinct from an edge transition on an existing id.
2. **Insertion rule:** a new item is **permitted** for the initializer/implementer creation path **only** when its seeded `status == 'unproven'` (the only legal birth status). A new item born at any `status != 'unproven'` (notably `proven`) from **any non-verifier** actor is **denied** (closes **T9**); a `proven` birth from a verifier still requires the SubagentStop/CI hash-rederive evidence backstop.
3. `in_scope:true` on a **newly inserted** item is the creation default (not a scope-flip of an existing item) and is **permitted**; an `in_scope` value-change on an **existing** id still routes to a human-signed change (R2 unchanged).
4. Existing-id transition rules (R1/R2) are **unchanged**; the append-only ordering guard (`check_append_only`) is **unchanged**.

**Until this guard change lands, mark 19.3 BLOCKED — do not present its integration test as green.** Because the hook is protected, the implementer **describes** this change in its summary for main/human to apply; the change is re-tested against the full actor matrix (initializer/implementer/main/verifier × unproven/proven birth).

### 2.3 Verifier WIRING obligations — failed-flip (8.2) + integration-evidence (8.3)

Both are spec-mandated and both are **unowned/unenforced** in the live tree. Both are **verifier-owned** and governance-legal.

- **`unproven → failed` flip (8.2).** Each slice the **Verifier** reads `wiring_checker.emit_wiring_items()` output and performs `unproven → failed` for any WIRING item whose symbol is reported **unreachable** from a real execution path (a permitted edge; `failed` is not `proven`, so it does not violate verifier-only-proven). Implementer/initializer **create** WIRING items as `unproven` (§2.2); only the verifier flips them.
- **`evidence_kind=='integration'` for proven WIRING (8.3 / T8).** Add a depth obligation to **both** the rego and the `coverage_gate.py` twin: deny a `proven` WIRING-type item whose `evidence.evidence_kind != 'integration'`. A *type-conditional* extension of the four-field check (not a removal of the provenance/gate split for non-WIRING items). Add a Property-2 PBT leg: "a unit-test Evidence_Record cannot prove a WIRING item." The schema `allOf` should carry the same constraint so the file is schema-invalid at write time, with the gate as the binding backstop.

### 2.4 PostToolUse exit-code reconciliation

The spec text (18.1/26.1) says "exit 1"; the live `post_tool_use_hook.main` returns **0** and surfaces feedback via `additionalContext` (a bare `non_block` decision is invalid harness input). **Decision:** keep the live behavior — **exit 0 with non-empty `additionalContext`** — because (a) it matches the harness contract and (b) the never-block invariant is about *not exiting 2*. The §8 integration test asserts **exit 0 + non-empty `additionalContext` containing the finding**; the requirements/tasks text is amended (§9). No test asserts "exit 1".

### 2.5 The fourth 8.2 category — jobs

Criterion 8.2 names **four** reachability obligations: routes, handlers, jobs, callbacks. The draft covered routes/handlers/callbacks but dropped **jobs** (scheduled/cron/queue tasks registered out-of-band). Assign jobs explicitly: the task-24 Semgrep ruleset gains a **job/scheduled-task registration** rule (`@scheduler.task`, `celery.task`, queue-consumer registration, `cron`-style entry-points), conforming to `emit_wiring_items()`. Where a job is registered via a module-level entry-point the AST pass already seeds (`_seed_module_level_entrypoints`), the AST pass owns it; the Semgrep rule covers decorator/registration-table jobs the AST seeding does not reach. No 8.2 category is left without an owner.

---

## 3. Diff-aware mechanism (hardened)

The single source of truth for "what did this PR introduce" is the **merge-base**:

```
BASE = git merge-base origin/main HEAD     # pull_request
BASE = HEAD~1                              # push to main (no PR base)
```

`BASE` is **config-sourced**: new `execution_bounds` entries `ORPHAN_DETECTOR_BASELINE` (default `"origin/main"`), `SEMGREP_BASELINE_STRATEGY` (`"auto"|"explicit"|"off"`, default `"auto"`), and `ORPHAN_ALLOWLIST_PATTERN` (default `"tools/.*"`). **These are string values; `execution_bounds.py` currently exposes only an `_int` helper, so add a parallel `_str(name, default)` helper** — the thresholds-from-execution_bounds invariant covers non-numeric config too.

### 3.1 Forward-orphan **validity cross-check** (closes T1)

A unit's requirement reference counts as a real reference **only if the referenced id exists as an item id in `feature_list.json`** (intersect `_impl_unit_req_ids()` against the model's id set). A reference to an **unknown** id is itself an orphan signal (a *dangling ref*), reported as a distinct sub-class of forward orphan — not a pass. This lands **in step 2, before** diff-awareness is bolted on. `detect_orphans` gains a `known_ids: Set[str]` parameter (derived from the model passed in). Empty/missing model ⇒ the cross-check is skipped *only* in the explicitly pre-delivery local case (§7), never in CI.

### 3.2 `orphan-exempt` marker hardening (closes T2)

The marker becomes a **reviewed surface**, not a free self-allowlist:

1. **Reason required.** Match `#\s*orphan-exempt:\s*\S+` — a bare `# orphan-exempt` no longer exempts.
2. **Scoped to the unit it annotates**, not the whole file. This requires moving forward-orphan units from **file-level** (today `_scan_repo_impl_units` makes one unit per file with whole-source as `text`) to **function/class-level** units (line-range-scoped). The marker exempts only the function/class on whose line-range it sits.
3. **Diff-aware on the marker itself.** The gate **counts and reports** every exemption, and **fails** when a PR adds a **new** exempt marker **outside `tools/`** (a new self-exemption is a reviewed event). Pre-existing markers are untouched.

The heal prompt is reworded so it no longer advertises exemption as the path of least resistance (§4.1).

### 3.3 Backward-orphan diff scope — **model deltas, not code references** (closes T3)

The draft scoped the diff-aware backward pass to "req-IDs referenced in changed files," which silently re-introduces the exemption it forbids. **Corrected:**

- **Forward** diff-scope stays code-driven: scan only the **changed `.py` files** (now at function-level, §3.2) for forward orphans, minus the `tools/` allowlist.
- **Backward** diff-scope is **model-driven**: diff `feature_list.json` itself (`git show BASE:feature_list.json` vs working copy) and check backward orphans for every item the PR **adds or modifies** that is in-scope — regardless of whether any changed `.py` references it. **Backward orphans are never path-exempt.**

### 3.4 Merge-base reachability — fail-CLOSED in CI, full-repo fallback LOCAL-only (closes T4)

- **CI:** `fetch-depth: 0` is a **hard per-workflow precondition**. Each diff-aware job runs a **merge-base self-test** first: if `git merge-base origin/$BASE HEAD` is empty, the job **fails closed** with `"fetch-depth:0 required — merge-base unreachable"`. CI **never** silently falls back to full-repo.
- **CI Semgrep:** diff-aware against the true merge-base, **fail-CLOSED on any new finding**. Fail-OPEN is reserved strictly for a subprocess/tool **crash**, never for "baseline unreachable."
- **Local gate only:** when `origin/main` is unreachable on a fresh branch, fall back to full-repo + **log the degrade**, then to `HEAD~1`. This soft path lives **only** in the local layer.

### 3.5 Baseline-poisoning precondition (closes T5)

Diff-aware enforcement is **unsound** if a finding can be landed on the BASE without passing the gate. Mirror the out-of-band-baseline reasoning the coverage baseline already has: make **`main` branch-protection requiring the SAME required checks** an explicit, listed dependency (§9) and a §5 build-order precondition. Without main protection, do not register the diff-aware gates as binding.

### 3.6 Fork-PR soundness (closes T7)

After the public flip, a `pull_request` from a **fork** gets a **read-only** `GITHUB_TOKEN` and **no repo secrets**. Corrected rules:

- **Required contexts must be satisfiable by a fork PR using only the read-only token and no secrets, or must not be in the required set for fork PRs.**
- **Semgrep (OSS, no token) is the binding SAST backstop for forks** — diff-aware on every PR including forks.
- **Sonar / CodeQL / secrets-scan-SARIF steps are gated** on `if: github.event.pull_request.head.repo.full_name == github.repository` (same-repo only), **or** moved to a `workflow_run` pattern after review. Registered required **only for same-repo PRs**.
- A missing `SONAR_TOKEN` is the **normal fork steady-state** (skip the step), and **fail-closed only for same-repo PRs** where the secret is expected.

### 3.7 Summary table

| Gate | Diff-aware mechanism | tools/ allowlist | Fork PR | Base-unreachable |
|---|---|---|---|---|
| **Orphan** | `--baseline-commit <sha>`; forward = changed `.py` (function-level) minus allowlist; backward = **model deltas** (§3.3); validity cross-check (§3.1) | `--exempt-paths`/`.orphan-exempt.json`, default `tools/**` for **forward** only | OSS, runs on forks | **CI fail-closed** (§3.4); local full-repo+log |
| **Semgrep** | `--baseline-commit $(merge-base)`; sev ∈ {HIGH,CRITICAL}; new-code only | path-ignore `tools/**` (CI) + `allowlist_dirs` (local) | OSS, **binding fork backstop** | **CI fail-closed**; local fail-open |
| **CodeQL** | auto SARIF diff vs PR target; nightly seeds `main` baseline | `paths-ignore:[tools/**]` (documented expiry) | **same-repo only** | nightly baseline; first-PR guard (§3.8) |
| **SonarCloud** | cloud New-Code = ref branch `main` | `sonar.exclusions: tools/**` (documented expiry) | **same-repo only** | scheduled `main` scan seeds baseline |

### 3.8 CodeQL/Sonar empty-baseline window

Immediately post-flip, CodeQL/Sonar with no historical `main` analysis report **all pre-existing findings as new**. **Ordering constraint (§10 step 13):** after the flip, trigger the scheduled CodeQL + Sonar **main-branch** analysis and confirm it completes **before** registering `sast-codeql` / `coverage-gate-sonar` as required. Verify the first post-baseline PR shows zero "new" alerts from pre-existing code. Only then add the contexts to the required set. (SonarCloud is already analyzing PRs — confirm its New-Code baseline is `main`-anchored before making it *required*.)

---

## 4. Local dual-enforcement (loop_gate / evidence_gate depth checks)

`evidence_gate.py` stays the **single accept/reject module**; `loop_gate` orchestrates pillars and owns escalation.

### 4.1 New reject codes + heal prompts (`evidence_gate.py`)

Extend the existing `CODES` tuple and `_HEAL` map with `SAST_HIGH_CRITICAL`, `ORPHAN_DETECTED`, `ORPHAN_DANGLING_REF`. Heal prompts: SAST → fix each new HIGH/CRITICAL then re-run `semgrep --baseline-commit`; ORPHAN → forward = reference an EXISTING id (a fabricated/unknown id is itself a dangling-ref orphan), backward = route the missing proof to the VERIFIER (never self-grade), exemptions are reviewed and a NEW exemption outside `tools/` fails the gate; DANGLING_REF → correct the id or have the requirement SEEDED as an unproven item, do not invent a trailer. These are **module constants** referenced by the CI twin (`ci_evidence_check.py`) so codes cannot drift.

### 4.2 New depth-check functions (`evidence_gate.py`)

Both **fail-OPEN on tool error** but **reject on a genuine finding**, and **trivially accept on empty `changed_files`**. They are **distinct functions**; their fail-OPEN posture **never** leaks into `check_slice` (the trust core stays fail-CLOSED).

```python
def check_slice_semgrep(changed_files, baseline_commit) -> dict:
    # semgrep on changed_files; --baseline-commit when provided; HIGH/CRITICAL only.
    # finding → _reject("SAST_HIGH_CRITICAL"); clean → OK; subprocess/parse error → OK + warn.

def check_slice_orphans(changed_files, feature_list_path, known_ids,
                        baseline_commit=None, allowlist_dirs=("tools/",)) -> dict:
    # forward: function-level units over changed_files minus allowlist; validity-check
    #   against known_ids (unknown id → ORPHAN_DANGLING_REF).
    # backward: items the PR adds/modifies in feature_list.json with no artifact (model-delta).
    # either → _reject(...); tool/git error → OK + warn (fail-open, local).
```

### 4.3 `gated_advance` integration (no contract drift)

Extend the existing `gated_advance(*, root, evidence, artifact, ledger, max_self_heal=None)` with optional, backward-compatible kwargs — `changed_files`, `baseline_commit`, `feature_list_path`, `known_ids`. Pillar 0 runs first, then the two new pillars when `changed_files` is supplied. Reuse the **exact** escalation already in `tools/loop_gate.py`: `max_self_heal` defaults to `execution_bounds.BLOCK_STREAK_HANDOFF` (config-sourced); collect rejections across pillars; all-accept → advance; any-reject → tick a no-progress turn; at `block_streak >= max_self_heal` → `handoff`; else `self_heal` with the joined heal prompts. **No new no-progress window, no new cap, no new C-LOOP-04.**

### 4.4 Governance honored in the local layer

- **verifier-only flips.** A backward-orphan heals by routing the missing proof to the **verifier**; the gate never flips status. The `unproven→failed` WIRING flip (§2.3) is verifier-owned.
- **thresholds from execution_bounds.** The only config values (`BLOCK_STREAK_HANDOFF`, baseline strategy, allowlist pattern) are `execution_bounds` keys via `_int`/the new `_str`.
- **human-owned artifacts.** A SAST finding inside a test or `plan-approved.json` yields a *described* remediation in the summary, never an agent edit.
- **trust-core separation.** `check_slice_semgrep` / `check_slice_orphans` are fail-OPEN; `check_slice` stays fail-CLOSED. Never merge their posture.

---

## 5. Required-status-check topology + ruleset/doc updates

### 5.1 Resolve the coverage-gate / OPA-vs-twin reality (corrected)

Verified live: `coverage-gate.yml` co-hosts **neither Playwright nor SonarCloud** (SonarCloud runs as its own check), and its header documents that it runs the **Python twin** `coverage_gate.deny_merge` — *instead of* `conftest test`. So **the rego is not invoked in CI at all**.

**Decision for tasks 21.2 / 21.3 / 21.4:**

- **Keep the Python twin as the gating CI leg** (no OPA/Conftest runtime needed for the required `coverage-gate` check — the deliberate live design).
- **The rego is exercised by a NEW `conftest test` integration leg** (task 21.3 — `tests/integration/test_opa_conftest.py`), closing the latent-untested-double gap.
- **Re-scope task 21.4:** its "confirm the full **rego** is the invoked gating policy" wording is satisfied by acknowledging the twin is the gating leg and the rego is covered by the 21.3 conftest test (twin and rego kept logically identical). Surface this re-scope to human (§9).
- **Property 22 clarification (21.2):** the existing `test_invariants.py:193` PBT proves the **Python twin**, not Conftest-against-rego. Task 21.2's "Conftest policy denies" wording is satisfied only by making the 21.3 conftest leg property-driven, **or** by re-scoping 21.2 to the twin (surfaced, §9).

### 5.2 Target topology — independent contexts

| Context (job `name:`) | Tool | Diff-aware | Fork-safe | Register when |
|---|---|---|---|---|
| `formal-verification` | Z3 | — | yes | exists |
| `Property + spine test suite` | pytest | — | yes | exists |
| `coverage-gate` | **Python twin only** | full-repo | yes (no secret) | exists |
| `secrets-scan` | gitleaks | diff | SARIF upload same-repo-only | exists |
| `traceability-gate` | orphan_detector + commit-req-id | **diff (hardened §3)** | yes (no secret) | after task 20 + 40.4 |
| `sast-semgrep` | Semgrep custom + security-audit | diff | **yes — binding fork backstop** | after task 24 + CI workflow |
| `sast-codeql` | CodeQL | auto-diff | **same-repo only** | after task 23 + baseline seeded |
| `coverage-gate-sonar` | SonarCloud | new-code | **same-repo only** | after task 22 quality-gate + baseline confirmed |
| `zap-baseline` | ZAP | — | — | exists |

Use **distinct** names `sast-codeql` vs `sast-semgrep` (a shared `sast` name would overwrite one context in the required array).

### 5.3 Amend the canonical task-14.2 enumeration (required, not an aside)

Task 14.2 is the **single canonical** required-check list and currently omits `sast-codeql`/`sast-semgrep`. A required check absent from 14.2 is **not actually binding**. **Amend the task-14.2 enumeration** to add `sast-codeql`, `sast-semgrep` (and `coverage-gate-sonar` if a distinct context). This is a **tasks.md/requirements edit obligation**, surfaced for human application (§9) and tracked (§10 step 13).

### 5.4 Build-order + workflow shapes

- **Build-order rule.** A context is registered required **only after its tool exists and is green** (and, for CodeQL/Sonar, after the `main` baseline is seeded, §3.8). Workflow *files* may land early; *required-check registration* follows the tool.
- **`traceability-gate.yml` (task 40.4):** `on: pull_request:[main]` + `push:[main]`; `checkout fetch-depth:0` + **merge-base self-test (fail-closed, §3.4)**; run `orphan_detector.py --baseline-commit origin/main` (hardened §3.1–3.3); second step runs the REQ-6.2 commit-trailer assertion; **fail on either non-zero exit**.
- **Every NEW diff-aware workflow sets `fetch-depth: 0`.**
- **Docs.** Update `docs/github-ruleset.md`: separate `sast-semgrep`/`sast-codeql` rows, `traceability-gate` as independent, `coverage-gate` runs the **OPA Python twin only**, the fork-PR / same-repo split, and reference the amended canonical task-14.2 enumeration.

---

## 6. Post-public hygiene (LOCKED #4 — partly landed via PR #31)

The acceptance oracle is **"no real secret AND no over-broad mask AND no live infra fingerprint"** — not merely a clean gitleaks exit (A-LOOP-01).

**Done (PR #31, merged `bc76611`):** VM origin IP → `secrets.VM_HOST`; project UUID / CF account id / owner UUID / workspace slug removed as code defaults → `YOUR_*` placeholders; the over-broad `.gitleaks.toml` `docs/*.md` blanket removed and replaced with precise value/path allowlists (`regexTarget="match"`) covering the Plane upstream-default creds, the `dedup_key` content-hashes, and author-redacted example tokens; a doc-illustration `SECRET_KEY` scrubbed from `PLANE_BLUEPRINT.md`. Verified: tracked-file gitleaks scan = 0 findings; `git grep` for every sensitive fingerprint = 0 tracked files.

**Remaining:**

- [ ] Project UUID in 2 `audit/plane-xref/board-snapshot*.json` data dumps — **deferred** (rewriting dumps risks corrupting the audit trail; data artifact, not a code default).
- [ ] DNS-discoverable `plane.autonomous-agent.dev` hostname — **deferred** (subdomain of the public project domain; protection is CF Access, not obscurity).
- [ ] **`main` branch protection** requires the same gates (§3.5) — precondition before registering any diff-aware gate as binding.
- [ ] CodeQL/Sonar `main` baseline seeded (§3.8) before registering those contexts.
- [ ] **(owner action)** lock OCI security-list ingress to Cloudflare IP ranges — the real mitigation for the (now-redacted) origin IP.
- [ ] **(owner action)** confirm `a411f976…` was never a live `SECRET_KEY` (absent from every config → almost certainly a doc sample; if ever deployed, rotate).

This checklist lives in `docs/github-public-repo-checklist.md` (new).

---

## 7. Error handling / fail-closed posture

Posture is **layer-specific** — CI fails *closed* (binding); the local gate fails *open on tool errors* (must not wedge the autonomous run). The trust core (`check_slice`) stays fail-CLOSED in both.

| Condition | Local pre-advance gate | CI |
|---|---|---|
| `changed_files` empty / None | depth pillars **skip** (accept); Pillar 0 still runs | n/a (path-driven) |
| **Diff-base unreachable** | **full-repo fallback + log** (LOCAL-only soft path) | **FAIL-CLOSED**: merge-base self-test errors with "fetch-depth:0 required" (§3.4) |
| `semgrep`/`git`/tool subprocess **crash** | **fail-open** (accept) + logged warning | job **fails** (binding backstop) |
| Missing `SONAR_TOKEN` | n/a (CI-only) | **fork PR → skip** (normal); **same-repo PR → fail-closed**; context not required until secret exists (§3.6) |
| Fork PR, secret-bearing scan | n/a | scan **skipped/not-required** for forks; Semgrep-OSS is the binding fork SAST gate (§3.6) |
| CodeQL/Sonar no `main` baseline | n/a | nightly/scheduled run seeds it; contexts **not registered** until seeded (§3.8) |
| `feature_list.json` absent | orphan backward-check + validity cross-check skip (pre-delivery normal) | matches existing `ci_evidence_check` absent-input skip + `baseline_gate` override |
| Fabricated/unknown req-id reference | `ORPHAN_DANGLING_REF` reject (§3.1) | same — fail-closed |
| `evidence` absent/malformed (Pillar 0) | **fail-closed reject** (unchanged trust core) | unchanged |

**Invariant:** an *ambiguous CI state* resolves to **blocked**, never passed; an *ambiguous local tool crash* resolves to **advance + log**, never a wedge. **Merge-base unreachability is NOT ambiguous in CI** (the history is there) — it is a misconfiguration and fails closed.

---

## 8. Testing matrix

| Test | Maps to | Asserts |
|---|---|---|
| Property 11 (`tests/spine/test_orphan_detector.py`, extended + tagged) | task 20.2 | forward orphans flagged only in non-excluded, non-exempt **functions** (file→function-level, §3.2); a `tools/`-exempt or reason-bearing `# orphan-exempt:` function is not flagged; **bare `# orphan-exempt` (no reason) IS flagged**; backward orphans flagged for any in-scope item with no artifact; **either** condition independently sets `ok=false`; **validity cross-check** (unit citing only an unknown id → dangling-ref); **diff-aware mode flags only NEW orphans**. Carries the literal `# Feature: spec-to-evidence-control, Property 11: Orphan Detection` annotation. |
| Property 22 (`tests/property/test_invariants.py:193`) | task 21.2 (**twin only**) | deny ⇔ some in-scope item not `proven`-with-complete-evidence; out-of-scope ignored. Labeled as proving the **Python twin**. **No rebuild.** |
| **Property 2 — WIRING integration-evidence** (NEW) | criterion 8.3 / §2.3 | a `proven` WIRING item with `evidence_kind != 'integration'` is **denied** by both the twin and the rego; a unit-test record cannot prove a WIRING item. |
| Conftest integration (`tests/integration/test_opa_conftest.py` — NEW) | task 21.3 | `conftest test` against the **rego**: unproven fixture → deny; all-proven+complete → pass; proven-WIRING-with-unit-evidence → deny. |
| Phase-1 integration (`tests/integration/test_phase1_integration.py` — NEW) | task 26.1 | wiring → `type:"WIRING"` finding with symbol (via the **fixed** `_real_wiring`, §2); unreachable symbol → **verifier flips item to `failed`** (§2.3); orphan → exit non-zero + both types; conftest deny+pass; PostToolUse lint file → **exit 0 + non-empty `additionalContext`** (§2.4). |
| **Red-team evasion suite** (NEW — the acceptance oracle) | LOCKED #2/#5 + §0 | **T1** fabricated `REQ-NONEXIST-999` trailer → `ORPHAN_DANGLING_REF` blocks. **T2** docstring mentioning `orphan-exempt`, and a bare `# orphan-exempt` with no reason → **not exempt**; a NEW reason-bearing exempt marker outside `tools/` → fails. **T3** new in-scope item with no artifact, unreferenced by any changed `.py` → **backward orphan blocks** (model-delta). **T4** unreachable merge-base in CI → **fail-closed**. **T8** proven WIRING with unit-test evidence → denied. **T9** new item born `status:proven` from a non-verifier → PreToolUse blocks. Plus granularity: a **new unreferenced function in a file that already cites a req-ID** → forward orphan blocks. Plus baseline-vs-new: a pre-existing untouched orphan → does not block; a `tools/` forward orphan → exempt. |

---

## 9. External dependencies + assumptions

| Dependency | Owner | Assumption / failure mode |
|---|---|---|
| **`main` branch protection** requiring the same gates | human (repo settings) | **Diff-aware enforcement is unsound without it (§3.5).** A hard precondition. |
| `SONAR_TOKEN` GitHub secret | human (SonarCloud) | Already present (SonarCloud passes on PRs). **Fork PRs skip Sonar**; only same-repo PRs fail-closed if absent. |
| GitHub code-scanning enabled | human (repo settings) | Required for CodeQL SARIF; free on public repos; SARIF upload needs `security-events: write` → **same-repo PRs only**. |
| `conftest` (OPA) CLI in CI | CI image | Pin in `requirements-dev.txt` (currently unpinned) so the 21.3 rego test is version-stable. |
| `semgrep` binary | CI + local | `--config auto` (or pinned); **identical config** local and CI; OSS → runs on **fork PRs without secrets**. |
| `fetch-depth: 0` on every diff-aware job | CI workflow | Only `secrets-scan.yml` sets it today; each NEW gate must. Empty merge-base in CI → **fail-closed** (§3.4). |
| CodeQL/Sonar `main` baseline seeded | scheduled run | Register `sast-codeql`/`coverage-gate-sonar` **only after** the baseline run completes (§3.8). |
| Term reconciliation: "SonarQube"→SonarCloud; PostToolUse "exit 1"→exit-0; rego-vs-twin (21.4); 14.2 amendment | human (tasks.md/requirements.md) | Spec edits surfaced in the summary for human application. |
| Postgres (backward-orphan authority) | Phase-2 | Phase-1 is file-based (`feature_list.json`); a comment marks the eventual upgrade. |

**Assumptions.** History is confirmed clean of real secrets (PR #31). The repo is **public**; PR #31 landed the code-side §6 hygiene. `coverage_query.rego` + the Python twin stay logically identical (the 21.3 conftest leg proves it).

---

## 10. Decomposition into ordered implementation tasks (TDD-sized, with actor/ownership)

Ordered so each step has an objective oracle and nothing is registered as a required check before its tool exists and (for CodeQL/Sonar) its baseline is seeded. `*` = test-first.

**Ownership legend** (PROTECTED_PREFIXES = `tests/`, `schema/`, `.github/workflows/`, `.github/policies/`, `.claude/hooks/`, `.claude/settings.json` + the human-owned-tests/plan rule): **[I]** implementer-writable (`tools/**`, `docs/**`, `.gitleaks.toml`, `sonar-project.properties`). **[H]** protected/human-owned — the implementer **describes** the change; **main/human** (or verifier for tests) applies it. Every test step is **[H]**.

| # | Step | Owner | Task |
|---|---|---|---|
| 1 | `execution_bounds` keys: add `_str` helper + `ORPHAN_DETECTOR_BASELINE`, `SEMGREP_BASELINE_STRATEGY`, `ORPHAN_ALLOWLIST_PATTERN` | **[I]** | unblocks 2–4 |
| 2 | **Orphan hardening (pre-diff):** `*`Property-11 tests for validity cross-check (§3.1), reason-required + function-scoped exempt (§3.2) → implement matcher cross-check + AST function-level units + reason regex; **lands before diff-awareness** | tests **[H]**, `orphan_detector.py` **[I]** | 20 |
| 3 | **Orphan diff-awareness:** `*`diff-mode + model-delta-backward tests (§3.3) → `--baseline-commit` + `--exempt-paths`/`.orphan-exempt.json` + model-diff backward; local full-repo fallback + degrade log | tests **[H]**, `orphan_detector.py` **[I]** | 20 |
| 4 | `evidence_gate` depth funcs: `*`unit tests (finding→reject, clean→OK, tool-crash→fail-open, empty→accept, dangling-ref) → `check_slice_semgrep` + `check_slice_orphans` + new `CODES`/`_HEAL` | tests **[H]**, `evidence_gate.py` **[I]** | 20/24 local |
| 5 | `loop_gate` pillars: `*`tests (all-accept→advance; any-reject→self_heal; streak≥bound→handoff; reset-on-progress) → extend `gated_advance`, reuse `run_state_driver` + `BLOCK_STREAK_HANDOFF` | tests **[H]**, `loop_gate.py` **[I]** | LOCKED #5 |
| 6 | Semgrep custom rules: `*`fixtures → `wiring_dead_code.yml` (routes/handlers/callbacks **+ jobs**, §2.5), output conforming to `emit_wiring_items()`, union-of-concerns de-dup comment (§2.1) | tests **[H]**, `tools/semgrep_rules/**` **[I]** | 24 |
| 7 | **PreToolUse new-item-permit (§2.2):** `*`actor-matrix tests (initializer/implementer unproven-birth → allow; any non-verifier proven-birth → deny; existing-id transitions unchanged) → amend `_changed_coverage_fields` insertion rule | tests **[H]**, `pre_tool_use_hook.py` **[H]** | 19 |
| 8 | **WIRING ingestion + failed-flip (§2.3):** verifier `unproven→failed` for unreachable symbols; integration-test leg; pin initializer-creates-via-permit-path | tests **[H]**, agent prompts **[H]** | 19 / 8.2 |
| 9 | **WIRING integration-evidence gate (§2.3 / 8.3):** `*`Property-2 leg → add `evidence_kind=='integration'`-for-proven-WIRING to rego + `coverage_gate.py` twin (+ schema `allOf`) | tests **[H]**, rego/schema **[H]**, `coverage_gate.py` **[I]** | 21 / 8.3 |
| 10 | `post_tool_use_hook` deltas: fix `_real_wiring` to call `analyze`→`emit_wiring_items` (no `check_wiring`); add `mypy`; optional diff filter; assert **still exit-0 non-block** | tests **[H]**, `post_tool_use_hook.py` **[H]** | 18 |
| 11 | `pre_compact_hook` resume-hash: emit `run_state.resume_state_hash` via `state_integrity.compute_state_hash` | tests **[H]**, `pre_compact_hook.py` **[H]** | 25 |
| 12 | conftest leg (21.3): pass/fail + proven-WIRING-unit-evidence fixtures + `test_opa_conftest.py`; pin `conftest` in `requirements-dev.txt`; resolve 21.4 per §5.1 | tests/policies **[H]**, `requirements-dev.txt` **[I]** | 21 |
| 13 | CI workflows (files first, **each `fetch-depth:0` + merge-base self-test + fork-PR guards §3.4/§3.6**): `codeql.yml` (23), `semgrep.yml` (24 CI, fork-safe OSS), `traceability-gate.yml` (40.4), Sonar New-Code + quality-gate + `sonar-project.properties` (22, same-repo-only); `coverage-gate.yml` left OPA-twin-only (§5.1) | workflows **[H]**, `sonar-project.properties` **[I]** | 22/23/24/40.4 |
| 14 | Phase-1 integration + **red-team evasion suite** (§8 T1–T9, granularity, baseline-vs-new) | tests **[H]** | 26 |
| 15 | §6 remainder: `docs/github-public-repo-checklist.md`; confirm tracked tree clean-by-absence; (owner) OCI ingress lock + `a411f976` confirm | docs **[I]**, infra **[owner]** | LOCKED #4 |
| 16 | **Registration sequence (last):** ensure `main` protection (§3.5); seed/confirm CodeQL + Sonar `main` baseline (§3.8); **then** register `sast-codeql`, `sast-semgrep`, `traceability-gate` (+ `coverage-gate-sonar`) as required — only after each is green; **amend canonical task-14.2 list (§5.3)** + `docs/github-ruleset.md` | ruleset/14.2/docs **[H]** | 14.2 / 40.x |

Steps 1–12 are local/tool + protected-hook/test work, mergeable now (`tools/`-exempt so no day-one block); 13–14 add the CI surface; 15–16 are the registration sequence, gated on hygiene, main-protection, and baseline seeding. **The PreToolUse new-item permit (step 7) gates 19.3, the WIRING failed-flip (step 8), and ingestion — until step 7 lands, 19.3's integration test is not green.**

---

## Residual risks (accepted)

- **Function-level orphan units** require an AST refactor of `orphan_detector`'s file-level `_scan_repo_impl_units` (line-range attribution, decorators, nested defs). Accepted: the only way to close T2 + the granularity gap; gated behind step-2 tests.
- **Model-delta backward diff** assumes `feature_list.json` is committed on a delivery PR. For runtime-only models the backward pass correctly skips; a delivery PR adding items WITHOUT committing the file is mitigated by the existing `baseline_gate` "trusted baseline expecting a delivery turns skip into deny" override. Seam accepted for the file-based Phase-1 model.
- **CodeQL/Sonar use GitHub's own diff/new-code engines**, so their "introduced by this PR" can differ from Semgrep/orphan across force-push/rebase. Accepted: they are same-repo-only secondary gates; Semgrep-OSS is the consistent primary that also covers forks.
- **gitleaks FP set is a snapshot.** New machine-dumped artifacts could re-introduce FP-shaped content under a non-allowlisted path and noisily fail secrets-scan. Accepted: a noisy fail is the safe direction; the path/value allowlist is the documented, reviewable place to extend.
- **Semgrep ↔ AST disagreement** on dynamic dispatch / metaprogrammed registration. The union-of-concerns rule reduces false-negatives but cannot make either engine complete. Accepted: the verifier's manual failed-flip (8.2) + the CI backstop remain the safety net.
- **`fetch-depth:0`** increases CI checkout cost on a large history. Accepted as the price of sound diff-awareness; the merge-base self-test makes a misconfigured shallow checkout fail loudly.

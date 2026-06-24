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

- **SonarCloud, not self-hosted SonarQube.** The public-repo free tier + New-Code reference-branch model assume hosted SonarCloud; the **`tasks.md`** term "SonarQube" (task 22.1 / the co-tenancy note — *not* `requirements.md`, which never contained the term) is amended to SonarCloud (human-owned edit, §9).
- **Fork-PR posture = Semgrep-gates-forks.** Sonar/CodeQL are same-repo-only (they need secrets / SARIF write a fork PR cannot have); Semgrep-OSS is the binding SAST backstop for fork PRs (§3.6). Accepted trust posture: external PRs are gated by Semgrep + the post-merge nightly, not by CodeQL/Sonar pre-merge.
- **PostToolUse exit code = keep the live exit-0-with-`additionalContext`** behavior; amend the spec text ("exit 1" in 18.1/26.1) to match (§2.4).

**2026-06-23 ground-truth deltas since the red-team ran (fold into the plan):**

- **Repo is now PUBLIC** (was "will be flipped"). The §6 pre-public hygiene is therefore POST-public remediation — **partly done already via PR #31 (merged, `bc76611`)**: live infra fingerprints redacted (VM origin IP → `secrets.VM_HOST`; project UUID / CF account id / owner UUID / workspace slug removed as code defaults), and the over-broad `.gitleaks.toml` `docs/*.md` blanket replaced with precise value/path allowlists (`regexTarget="match"`). **Remaining §6 items:** the project UUID in 2 `audit/plane-xref/board-snapshot*.json` data dumps (deferred — data artifacts), **`main` branch protection** requiring the same gates (§3.5 precondition), and CodeQL/Sonar **`main` baseline seeding** (§3.8). Two non-code owner actions remain: lock OCI ingress to Cloudflare IP ranges, and confirm the `a411f976…` doc `SECRET_KEY` was never a live value.
- **SonarCloud runs server-side, but NOTHING in the repo wires it** — `grep -ri sonar .github/` returns zero hits; there is no `sonar-project.properties` and no workflow step. The `SonarCloud Code Analysis` check was *observed passing* on PRs #31/#32 (it runs via SonarCloud's app-side **Automatic Analysis**), but that is **out-of-band server state, unverifiable from the tree**, and it contradicts canonical task 22.1 (`tasks.md:467`) which still demands a repo-side scan step. **Treat task 22 as MISSING for planning** — the repo-side integration (`sonar-project.properties`, the scan step, New-Code definition, the 85% quality gate, the required-check registration) is all still to build. The app-side run is an *unverified bonus* a human must confirm in the PR-checks UI, never a reason to skip the work. (Original draft over-downgraded this to "PARTIAL/already-wired" on the strength of a runtime observation — corrected by the 2026-06-23 adversarial verification.)

---

### Adversarial verification (2026-06-23)

This spec was triple-checked: 9 ground-truth readers → draft → 4-lens red-team → synthesis, **then** a second independent **adversarial verification** (11 agents) that re-derived every load-bearing claim from the live tree (`file:line` quoted), **executed `pre_tool_use_hook.evaluate`** across the actor matrix, and hunted false-positives/negatives — cross-checked by the author's own direct tool-runs. Verdict: **accurate, minor fixes** (16/19 sampled claims confirmed; 3 corrected). Corrections folded into this revision: the verifier-proven-birth claim was **false** (new-item births are blocked for *all* actors; the real bug is the initializer cannot seed the model — §2.2); the WIRING schema-`allOf` is **already built**, so only the rego/twin legs remain (§2.3 / §10 step 9); SonarCloud is **unverifiable from the tree** (§2 task 22); the "SonarQube" term lives in `tasks.md`, not `requirements.md` (§9). New gaps added: the **production feed** for the local gate (§4.3 / step 14), the **WIRING ingester** write-path (step 8), the **de-dup owner** (step 10), the **prover `evidence_kind='integration'`** co-task (step 9), and the omitted **`audit-chain-verify` / `deepeval-gate`** required checks (§5.2).

A **third, independent pass (Gemini 3.5 Flash High**, prompted to re-derive every claim from the live tree) then surfaced four more gaps — each **verified by direct `grep`/file reads before folding in** (one of its six findings was rejected on the mechanism, one was already covered): a **deletion bypass** + the unbuilt `check_append_only` (**T10**), a born-`in_scope:false` **insertion bypass** (**T11**), a **`MultiEdit` coverage-guard** gap (**T12**), the required-check **context-name** mismatch (§5.2), and the **wiring-feedback output-shape** mismatch (§10 step 11).

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
| T8 | Prove a WIRING item with a **unit-test** Evidence_Record | **half-closed today:** `schema/feature_list.schema.json:130-152` allOf already blocks it at *write* time; §2.3 closes the remaining **rego + `coverage_gate.py` twin** legs (both still un-gated) |
| T9 | A new item **born `proven`** (or an existing-id proven-flip) bypasses the verifier | §2.2 insertion rule permits only `unproven` births; born-`proven` + existing-id flips stay verifier-only. **NB:** new-item births are *already blocked today* (for all actors, sans `human_signed`) — the rule must *re-open* legitimate `unproven` seeding **without** opening born-`proven` |
| T10 *(Gemini RT-02)* | **Delete** an in-scope `unproven` item from `feature_list.json` so the Stop gate has nothing left to block | §2.2 step-7 guard must handle **deletion** — the spec'd `check_append_only` (design.md:1482) is **NOT implemented** (verified absent); a non-verifier delete of an in-scope/`unproven` item must be denied |
| T11 *(Gemini RT-05)* | Insert a new item **born `in_scope:false`** so it evades every in-scope-only gate (in-scope-shrink applied to insertions) | §2.2 insertion rule: a new item born `in_scope:false` from a non-human is denied — births are `in_scope:true` or rejected |
| T12 *(Gemini RT-01, narrowed)* | Flip status/`in_scope` via a **`MultiEdit`** payload whose `edits[]` array the coverage-field diff doesn't parse, evading PreToolUse R1/R2 | §2.2 step-7: `_changed_coverage_fields` must parse `MultiEdit.edits[]` (today only Edit `old/new` + Write `content`). SubagentStop hash-rederivation is the existing backstop; R3 (protected-prefix) is **not** bypassed — `MultiEdit` carries top-level `file_path` |

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
| **21** | `.github/policies/coverage_query.rego` + `tools/coverage_gate.py` | **PARTIAL** | Four-field + actor-separation policy exists in both rego and Python twin; Property 22 PBT exists for the **twin**. **Residual:** (21.3) no `conftest test` runtime invocation of the rego — the rego is a **latent untested double**; (8.3) **`evidence_kind=='integration'` for proven WIRING is enforced at WRITE time by the schema allOf (`schema/feature_list.schema.json:130-152`, already built) but NOT by the merge gates** — the rego (`coverage_query.rego:31`) + `coverage_gate.py` twin (line 52) treat `evidence_kind` as provenance, so close those two legs ONLY (T8 half-closed, §2.3); (21.2/21.4) resolved in §5.1. **Do not rebuild the core policy or the schema allOf.** |
| **22** | SonarCloud quality gate | **MISSING from the repo** (app-side run unverifiable) | No `sonar-project.properties`, no sonar workflow/step (`grep -ri sonar .github/` → 0). A `SonarCloud Code Analysis` check was *observed passing* on PRs #31/#32 via SonarCloud's app-side Automatic Analysis — out-of-band, unfalsifiable from the tree, and canonical task 22.1 still demands a repo-side scan step. Build: the scan step/workflow + `sonar-project.properties` + New-Code (ref branch `main`) + 85% quality gate + same-repo-only fork guard (§3.6) + required-check registration. Amend the **`tasks.md`** "SonarQube"→SonarCloud term (§9). |
| **23** | CodeQL SAST | **MISSING** | No `.github/workflows/codeql.yml`. Needs Python CodeQL workflow, `fetch-depth: 0`, **same-repo-only SARIF upload** (§3.6), nightly `schedule` to seed the `main` baseline. CI-only (LOCKED #5). |
| **24** | `tools/semgrep_rules/wiring_dead_code.yml` | **MISSING** | No custom rules. Needs decorator-route / registered-callback **and job/scheduled-task** dead-code rules (all four 8.2 categories — §2.5) whose output matches `emit_wiring_items()`, plus the union-of-concerns de-dup contract (§2.1). |
| **25** | `.claude/hooks/pre_compact_hook.py` | **PARTIAL** | Checkpoints progress/feature_list/evidence. **Missing:** the `run_state.resume_state_hash` producer — it does not call `state_integrity.compute_state_hash()`, so SessionStart resume-integrity always lands on the no-baseline branch (Property 26 / COH-2 neutered). |
| **26** | `tests/integration/test_phase1_integration.py` | **MISSING** | Must exercise wiring → WIRING finding, the **verifier failed-flip** (§2.3), orphan forward+backward (exit non-zero), `conftest test` deny+pass, PostToolUse lint feedback, **and** the §8 red-team evasion suite (T1–T12). |

### 2.1 De-dup contract (19 ↔ 24) — union-of-concerns, not winner-take-all

Both sources key candidates by **symbol `qualname`**. The de-dup rule:

- A qualname flagged by **either** source is a finding. A Semgrep "clean" verdict **never** overrides an AST "orphan" verdict (closes **T6**).
- "Semgrep wins" means **only** that Semgrep's richer *metadata* (decorator/callback context) is preferred for the *reporting* of a shared qualname — a metadata-merge, not a verdict-override.
- De-dup happens **before** the write to `feature_list.json`. Task 24's rule output **must** conform to `emit_wiring_items()` shape so the merge is mechanical.
- The custom-rule author is bound by an explicit comment in `wiring_dead_code.yml`: *"A Semgrep clean result is advisory metadata; it cannot retract an AST orphan."*

### 2.2 WIRING ingestion (19.3) — the guard change this REQUIRES (corrected)

**The draft's premise is false against live code; re-classified from an assumed fact to a REQUIRED, currently-unbuilt hook change.** Verified live — by **executing `pre_tool_use_hook.evaluate` across the full actor × `human_signed` matrix**, not merely reading it: for a **brand-new** item id, `_changed_coverage_fields` compares `after[id]` against an absent `before[id]` (`{}`), so `status:'unproven'` (≠ `None`) is reported as a *changed* `status` and `in_scope:true` as a *changed* `in_scope`. The consequence is bigger than the draft thought:

- **Every new-item `Write` registers `changed={'status','in_scope'}` and is BLOCKED for ALL actors** unless `human_signed=True` — the **verifier is blocked too** (R2 in_scope-human-owned, `pre_tool_use_hook.py:230-236`), exactly like the initializer/implementer. The earlier "a verifier seeding at `status:proven` is currently *allowed*" claim is **FALSE** — a born-`proven` insertion is already blocked, by R2, not by any proven-specific rule. (T9 "born-proven skips the verifier" is therefore a property to **preserve**, not a live hole.)
- **The actual load-bearing defect is broader than WIRING-19.3:** because the new item's `status` reads as changed, R1 (status-verifier-owned) blocks the **initializer** — whose entire role is to seed the unproven coverage model — from seeding *at all*, even with `human_signed` (R2 satisfied, but R1 still fires on `status`). **Initializer/implementer cannot create any new item today.** That general seeding outage is the real bug; the draft framed it narrowly as a WIRING corner case.

The fix distinguishes a **new-id INSERTION** (a birth) from an **existing-id field MUTATION** (a flip): permit a legitimate `unproven` birth by initializer/implementer, while keeping a **born-`proven`** insertion and any **existing-id `status`/`in_scope` change** verifier/human-owned exactly as today.

**Concrete required guard change** (to `.claude/hooks/pre_tool_use_hook.py`, a PROTECTED artifact — owned by main/human, §10):

1. In `_changed_coverage_fields`, classify an item id **absent from `before`** as an **INSERTION**, distinct from an edge transition on an existing id.
2. **Insertion rule:** a new item is **permitted** for the initializer/implementer creation path **only** when its seeded `status == 'unproven'` (the only legal birth status). A new item born at any `status != 'unproven'` (notably `proven`) from **any non-verifier** actor is **denied** (closes **T9**); a `proven` birth from a verifier still requires the SubagentStop/CI hash-rederive evidence backstop.
3. `in_scope:true` on a **newly inserted** item is the creation default and is **permitted**; an `in_scope` value-change on an **existing** id still routes to a human-signed change (R2 unchanged). **A new item born `in_scope:false` from a non-human actor is DENIED** (Gemini RT-05) — a born-out-of-scope item evades every in-scope-only gate (the RT-02 in-scope-shrink class, applied to insertions). Insertions are `in_scope:true` or rejected.
4. Existing-id transition rules (R1/R2) are **unchanged**. **The guard must additionally handle DELETION and `MultiEdit` (Gemini RT-02/RT-01):** (a) `_changed_coverage_fields` iterates only `after`, so a **deleted** item is invisible — a non-verifier deletion of an in-scope or `unproven` item must be detected and **denied** (else the Stop gate passes on the now-absent item). The spec'd `check_append_only` (design.md:1482) is **NOT implemented in the live tree** (verified — `grep` finds no such guard), so this is **net-new work, not "unchanged."** (b) `_changed_coverage_fields` parses only Edit `old/new` + Write `content`, **not** `MultiEdit`'s `edits[]`, so a status/`in_scope` flip via `MultiEdit` evades R1/R2 at PreToolUse — the early gate must parse `edits[]` too (SubagentStop hash-rederivation is the existing backstop). The protected-prefix check (R3) reads top-level `file_path`, which `MultiEdit` *does* carry, so R3 is **not** bypassed.

**Until this guard change lands, mark 19.3 BLOCKED — do not present its integration test as green.** Because the hook is protected, the implementer **describes** this change in its summary for main/human to apply; the change is re-tested against the full actor matrix (initializer/implementer/main/verifier × unproven/proven birth).

### 2.3 Verifier WIRING obligations — failed-flip (8.2) + integration-evidence (8.3)

Both are spec-mandated and both are **unowned/unenforced** in the live tree. Both are **verifier-owned** and governance-legal.

- **`unproven → failed` flip (8.2).** Each slice the **Verifier** reads `wiring_checker.emit_wiring_items()` output and performs `unproven → failed` for any WIRING item whose symbol is reported **unreachable** from a real execution path (a permitted edge; `failed` is not `proven`, so it does not violate verifier-only-proven). Implementer/initializer **create** WIRING items as `unproven` (§2.2); only the verifier flips them.
- **`evidence_kind=='integration'` for proven WIRING (8.3 / T8).** The schema `allOf` **already** carries this constraint (`schema/feature_list.schema.json:130-152`, write-enforced via `feature_list_init.validate_against_schema`) — a unit-test Evidence_Record is **already rejected at write time**; do **not** rebuild it. The remaining gap is the **merge gates**: add the depth obligation to **both** the rego (`coverage_query.rego`) and the `coverage_gate.py` twin — deny a `proven` WIRING item whose `evidence.evidence_kind != 'integration'` (a *type-conditional* extension of the four-field check, not a removal of the provenance split for non-WIRING items). Add a Property-2 PBT leg over the twin + a conftest leg over the rego.
- **Prover must emit `evidence_kind='integration'` for WIRING (false-negative the draft missed).** The sole production prover, `tools/prove_trivial_slice.py:61`, stamps `evidence_kind='behavioral'` — **never** `'integration'`. So the moment the rego/twin gate (joining the existing schema allOf) requires `'integration'` for WIRING, the only prove-path can prove **no** WIRING item — every WIRING item becomes permanently unproveable. The verifier's WIRING-evidence path (or the prover, type-conditionally) MUST emit `evidence_kind='integration'` for `type:WIRING` items. This is a REQUIRED co-task of the gate (§10 step 9), not optional.

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

**WIRING-id non-determinism caveat.** WIRING ids are minted by ordinal per-analysis (`emit_wiring_items`), so the *same* symbol can map to a different id across analyses — a fresh-analysis id can read as "dangling" against the committed model. The validity cross-check MUST source `known_ids` from the **committed `feature_list.json`** (never a fresh analysis), and **exclude WIRING-prefixed ids from the dangling-ref subclass**, or `ORPHAN_DANGLING_REF` will fire non-deterministically on legitimately-minted WIRING references.

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

Immediately post-flip, CodeQL/Sonar with no historical `main` analysis report **all pre-existing findings as new**. **Ordering constraint (§10 step 18):** after the flip, trigger the scheduled CodeQL + Sonar **main-branch** analysis and confirm it completes **before** registering `sast-codeql` / `coverage-gate-sonar` as required. Verify the first post-baseline PR shows zero "new" alerts from pre-existing code. Only then add the contexts to the required set. (SonarCloud is already analyzing PRs — confirm its New-Code baseline is `main`-anchored before making it *required*.)

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

**The production feed (REQUIRED — without it the local layer is vaporware).** `changed_files` / `baseline_commit` / `known_ids` are kwargs, but **nothing in `tools/` or `.claude/hooks/` computes them today** (`grep -rE 'name-only|merge-base|changed_files' tools/ .claude/hooks/` → 0), and the only production caller of `gated_advance` (`tools/governed_pilot.py`) passes none of them — so in production the depth pillars **always receive empty `changed_files` and always skip**, silently no-op'ing the LOCAL half of LOCKED-#5 dual-enforcement (autonomous self-heal on SAST/orphan findings would be vaporware). A **named producer is REQUIRED** (§10 step 14): in the autonomous driver, compute `baseline_commit = git merge-base origin/main HEAD`, `changed_files = git diff --name-only <baseline_commit>`, and `known_ids` = the committed model's id-set, and thread them into `gated_advance`. Without it, §4.1–§4.3 are unreachable.

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
- **Voided tasks.md instructions (surface as amendment obligations, §9).** Because the Python twin is the gating leg and SonarCloud/Playwright run as their **own** checks (not co-tenants), the tasks.md instructions "add OPA/SonarQube/Playwright to `coverage-gate.yml`" (the task-14.1 co-tenancy note, tasks 15.1, 22.1) are partly **void** — list them explicitly so the canonical tasks don't silently disagree with the built topology. Add an explicit step (§10 step 18) to **re-confirm `coverage-gate` is STILL a required check after any policy change** (tasks.md:460-464, "do not assume continuity").

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
| `audit-chain-verify` | `audit_verify` | — | yes (no secret) | REQUIRED per canonical 14.2 (built in its own phase, task 40.3/52) — **must appear in the ruleset doc; do not drop** |
| `deepeval-gate` | DeepEval | — | needs eval key | REQUIRED per canonical 14.2 (Phase-3/4, task 55.1/40.6) — **must appear in the ruleset doc; do not drop** |

Use **distinct** names `sast-codeql` vs `sast-semgrep` (a shared `sast` name would overwrite one context in the required array).

**Context-name caveat (Gemini RT-04).** GitHub matches a required check by the job's **`name:` string**, not the short token. The live registered contexts are the **long** names per `docs/github-ruleset.md` — `Z3 formal-verification harness (34/34)`, `Property + spine test suite`, `Zero-evidence coverage gate (block merge on un-proven coverage)`, `gitleaks secrets diff-scan (block merge on detected secret)`, `zap-baseline`. **The short tokens in the table above are labels, not the registered contexts.** Therefore: each NEW Phase-1 workflow MUST set a stable `name:`, and the ruleset registers *that exact string*; the §5.4 `docs/github-ruleset.md` update and the §5.3 task-14.2 amendment must use the actual `name:` strings (registering a short token that no job emits silently fails to gate).

### 5.3 Amend the canonical task-14.2 enumeration (required, not an aside)

Task 14.2 is the **single canonical** required-check list and currently omits `sast-codeql`/`sast-semgrep`. A required check absent from 14.2 is **not actually binding**. **Amend the task-14.2 enumeration** to add `sast-codeql`, `sast-semgrep` (and `coverage-gate-sonar` if a distinct context). This is a **tasks.md/requirements edit obligation**, surfaced for human application (§9) and tracked (§10 step 18).

### 5.4 Build-order + workflow shapes

- **Build-order rule.** A context is registered required **only after its tool exists and is green** (and, for CodeQL/Sonar, after the `main` baseline is seeded, §3.8). Workflow *files* may land early; *required-check registration* follows the tool.
- **`traceability-gate.yml` (task 40.4):** `on: pull_request:[main]` + `push:[main]`; `checkout fetch-depth:0` + **merge-base self-test (fail-closed, §3.4)**; run `orphan_detector.py --baseline-commit origin/main` (hardened §3.1–3.3); second step runs the REQ-6.2 commit-trailer assertion; **fail on either non-zero exit**.
- **Every NEW diff-aware workflow sets `fetch-depth: 0`.**
- **Docs.** Update `docs/github-ruleset.md`: separate `sast-semgrep`/`sast-codeql` rows, `traceability-gate` as independent, `coverage-gate` runs the **OPA Python twin only**, the fork-PR / same-repo split, and reference the amended canonical task-14.2 enumeration. **The documented required set MUST match the full canonical 14.2 list — including `audit-chain-verify` and `deepeval-gate`; do NOT let the topology silently shrink** (§5.2).

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
| **pre_compact resume-hash round-trip** (25.2 case 3 — NEW) | task 25 / Property 26 | `pre_compact` writes `run_state.resume_state_hash` AND that value **equals `state_integrity.compute_state_hash`** over the same checkpointed state — the oracle SessionStart's `check_resume_integrity` reads back (without it the hash never matches, re-neutering the property). |
| **WIRING gate is proveable** (Property 2 leg — NEW) | §2.3 / step 9 | after the rego/twin WIRING gate lands, a WIRING item proven via the production prover path **succeeds** — i.e. the prover/verifier emits `evidence_kind='integration'`, so the gate does not make WIRING items permanently unproveable. |
| Phase-1 integration (`tests/integration/test_phase1_integration.py` — NEW) | task 26.1 | wiring → `type:"WIRING"` finding with symbol (via the **fixed** `_real_wiring`, §2); unreachable symbol → **verifier flips item to `failed`** (§2.3); orphan → exit non-zero + both types; conftest deny+pass; PostToolUse lint file → **exit 0 + non-empty `additionalContext`** (§2.4). |
| **Red-team evasion suite** (NEW — the acceptance oracle) | LOCKED #2/#5 + §0 | **T1** fabricated `REQ-NONEXIST-999` trailer → `ORPHAN_DANGLING_REF` blocks. **T2** docstring mentioning `orphan-exempt`, and a bare `# orphan-exempt` with no reason → **not exempt**; a NEW reason-bearing exempt marker outside `tools/` → fails. **T3** new in-scope item with no artifact, unreferenced by any changed `.py` → **backward orphan blocks** (model-delta). **T4** unreachable merge-base in CI → **fail-closed**. **T8** proven WIRING with unit-test evidence → denied. **T9** new item born `status:proven` from a non-verifier → PreToolUse blocks. **T10** non-verifier **deletes** an in-scope `unproven` item → PreToolUse blocks. **T11** insert an item born `in_scope:false` from a non-human → PreToolUse blocks. **T12** flip `status`/`in_scope` via a `MultiEdit` payload → R1/R2 fire (the `edits[]` array is parsed). Plus granularity: a **new unreferenced function in a file that already cites a req-ID** → forward orphan blocks. Plus baseline-vs-new: a pre-existing untouched orphan → does not block; a `tools/` forward orphan → exempt. |

---

## 9. External dependencies + assumptions

| Dependency | Owner | Assumption / failure mode |
|---|---|---|
| **`main` branch protection** requiring the same gates | human (repo settings) | **Diff-aware enforcement is unsound without it (§3.5).** A hard precondition. |
| `SONAR_TOKEN` GitHub secret | human (SonarCloud) | **Unverifiable from the tree** — no repo artifact references it. SonarCloud runs app-side (observed on PRs #31/#32); a human confirms via the PR-checks UI before the plan relies on it. **Fork PRs skip Sonar**; only same-repo PRs fail-closed if absent. |
| GitHub code-scanning enabled | human (repo settings) | Required for CodeQL SARIF; free on public repos; SARIF upload needs `security-events: write` → **same-repo PRs only**. |
| `conftest` (OPA) CLI in CI | CI image | Pin in `requirements-dev.txt` (currently unpinned) so the 21.3 rego test is version-stable. |
| `semgrep` binary | CI + local | `--config auto` (or pinned); **identical config** local and CI; OSS → runs on **fork PRs without secrets**. |
| `fetch-depth: 0` on every diff-aware job | CI workflow | Only `secrets-scan.yml` sets it today; each NEW gate must. Empty merge-base in CI → **fail-closed** (§3.4). |
| CodeQL/Sonar `main` baseline seeded | scheduled run | Register `sast-codeql`/`coverage-gate-sonar` **only after** the baseline run completes (§3.8). |
| Term reconciliation: "SonarQube"→SonarCloud (**`tasks.md` lines 463/466/467 only — NOT requirements.md, which never had the term**); PostToolUse "exit 1"→exit-0; rego-vs-twin (21.4); 14.2 amendment (+`sast-*`); void the "add to coverage-gate.yml" instructions in tasks 15.1/22.1 | human (`tasks.md`) | Spec edits surfaced in the summary for human application. |
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
| 7 | **PreToolUse new-item-permit (§2.2) — CORRECTED:** first **re-derive the actor matrix by EXECUTING `evaluate()`** (the draft's "verifier proven-birth allowed" was false; today *every* new-item write is blocked for all actors sans `human_signed`, and the **initializer cannot seed the model at all** — R1 fires on the new `status`). `*`tests: initializer/implementer **unproven-birth → allow** (the new permit); **born-`proven` (any actor) → deny**; **existing-id `status`/`in_scope` change → verifier/human-owned, unchanged** → amend `_changed_coverage_fields`/`evaluate` to split **new-id INSERTION** from **existing-id MUTATION**, **AND** (Gemini RT-01/02/05) parse `MultiEdit.edits[]` in `_changed_coverage_fields`, **deny non-verifier DELETION** of in-scope/`unproven` items (`check_append_only` is unbuilt — net-new), and **deny born-`in_scope:false`** from non-human actors | tests **[H]** (incl. delete / MultiEdit / born-out-of-scope cases), `pre_tool_use_hook.py` **[H]** | 19 + seeding/deletion/MultiEdit |
| 8 | **WIRING ingestion WRITE path + failed-flip (§2.2/§2.3) — EXPANDED:** (a) build the **ingester** — a path that reads `emit_wiring_items()` output and WRITES `type:WIRING` `unproven` items into `feature_list.json` via the step-7 permit (no such writer exists today; `emit_wiring_items` is consumed only by `_main` stdout + tests); (b) verifier `unproven→failed` for unreachable symbols. `*`integration test: a dead symbol → a WIRING item is created AND (if unreachable) flipped to `failed` | tests **[H]**, ingester **[I]**, agent prompts **[H]** | 19.3 / 8.1 / 8.2 |
| 9 | **WIRING integration-evidence gate (§2.3 / 8.3) — rego + twin ONLY:** `*`Property-2 leg → add `evidence_kind=='integration'`-for-proven-WIRING to the rego + `coverage_gate.py` twin. **The schema `allOf` already enforces this at write time (`feature_list.schema.json:130-152`) — do NOT rebuild it.** **REQUIRED co-task:** teach the prover (`prove_trivial_slice.py:61` stamps `'behavioral'`) / the verifier WIRING-evidence path to emit `evidence_kind='integration'` for `type:WIRING`, or every WIRING item becomes unproveable | tests **[H]**, rego **[H]**, `coverage_gate.py` + prover **[I]** | 21 / 8.3 |
| 10 | **WIRING de-dup / union-merge owner (§2.1 / T6) — NEW:** an owning function (+ `*`test) merging AST (`wiring_checker`) + Semgrep candidates by `qualname` with **union-of-concerns** (a Semgrep "clean" never retracts an AST orphan), run **before** the step-8 ingest write. Without an owner + test, T6 stays open despite §2.1 marking it closed | tests **[H]**, de-dup module **[I]** | 19/24 / T6 |
| 11 | **`post_tool_use_hook` deltas (§2.5) — CORRECTED:** fix `_real_wiring` (imports nonexistent `check_wiring`) to use `analyze`→`emit_wiring_items`, **but with caller-context** (analyze the changed file *plus* its repo callers, or only emit symbols dead across the full-repo index) — a bare changed-files-only call floods every defined symbol as a false "dead" finding; **(Gemini RT-06)** `emit_wiring_items` returns *ingestion CoverageItems* (`{id,type,wiring:{file,line}}`), the WRONG shape for `_normalize_findings` (which reads top-level `path/line/message` → it stringifies the whole dict) — the FEEDBACK path must map `wiring.file→path`, `wiring.line→line`, synthesize a readable message, distinct from step-8's ingestion path; add `mypy`; `*`schedule the **18.2 oracle** (a finding reaches `additionalContext`); assert **still exit-0 non-block** | tests **[H]**, `post_tool_use_hook.py` **[H]** | 18 |
| 12 | `pre_compact_hook` resume-hash: emit `run_state.resume_state_hash` via `state_integrity.compute_state_hash`; `*`**round-trip test (25.2 case 3): written hash == `state_integrity` recomputation over the same checkpointed state** (else SessionStart's resume-integrity never matches, re-neutering Property 26) | tests **[H]**, `pre_compact_hook.py` **[H]** | 25 |
| 13 | conftest leg (21.3): pass/fail + proven-WIRING-unit-evidence fixtures + `test_opa_conftest.py`; pin `conftest` in `requirements-dev.txt`; resolve 21.4 per §5.1 | tests/policies **[H]**, `requirements-dev.txt` **[I]** | 21 |
| 14 | **Production feed for the local gate (§4.3) — NEW:** in the autonomous driver (`governed_pilot.py` / its caller) compute `baseline_commit = git merge-base origin/main HEAD`, `changed_files = git diff --name-only`, `known_ids` = committed model id-set, and thread them into `gated_advance`; `*`test that depth pillars actually RUN (not skip) when a PR adds a finding. Without it the LOCKED-#5 local half no-ops | tests **[H]**, driver **[I]** | LOCKED #5 |
| 15 | CI workflows (files first, **each `fetch-depth:0` + merge-base self-test + fork-PR guards §3.4/§3.6**): `codeql.yml` (23), `semgrep.yml` (24 CI, fork-safe OSS), `traceability-gate.yml` (40.4), **the SonarCloud scan step + `sonar-project.properties` + New-Code + quality-gate (22 — repo-side integration is NET-NEW, not pre-existing; same-repo-only)**; `coverage-gate.yml` left OPA-twin-only (§5.1) | workflows **[H]**, `sonar-project.properties` **[I]** | 22/23/24/40.4 |
| 16 | Phase-1 integration + **red-team evasion suite** (§8 T1–T12 incl. delete-evasion / born-`in_scope:false` / `MultiEdit`-flip, granularity, baseline-vs-new) | tests **[H]** | 26 |
| 17 | §6 remainder: `docs/github-public-repo-checklist.md`; confirm tracked tree clean-by-absence; (owner) OCI ingress lock + `a411f976` confirm | docs **[I]**, infra **[owner]** | LOCKED #4 |
| 18 | **Registration sequence (last):** ensure `main` protection (§3.5); seed/confirm CodeQL + Sonar `main` baseline (§3.8); **then** register `sast-codeql`, `sast-semgrep`, `traceability-gate`, `coverage-gate-sonar` as required — only after each is green; re-confirm `coverage-gate` survives the policy change (§5.1); **amend canonical task-14.2 list (§5.3, +`sast-*`)** + update `docs/github-ruleset.md` to the FULL 14.2 set **including `audit-chain-verify` + `deepeval-gate`** (don't shrink it) | ruleset/14.2/docs **[H]** | 14.2 / 40.x |

Steps 1–14 are local/tool + protected-hook/test work, mergeable now (`tools/`-exempt so no day-one block); 15–16 add the CI surface; 17–18 are the registration sequence, gated on hygiene, main-protection, and baseline seeding. **Step 7 (the PreToolUse insertion-permit) is the linchpin: it un-blocks initializer/implementer model-seeding *generally* AND the step-8 WIRING ingest — until it lands, no new item (WIRING or otherwise) can be created and step-8's integration test is not green.** Step 9's prover-emits-`integration` co-task is equally load-bearing: without it the new WIRING gate makes every WIRING item unproveable. Step 14's production feed is what makes the LOCKED-#5 local enforcement real rather than a silent no-op.

---

## Residual risks (accepted)

- **Function-level orphan units** require an AST refactor of `orphan_detector`'s file-level `_scan_repo_impl_units` (line-range attribution, decorators, nested defs). Accepted: the only way to close T2 + the granularity gap; gated behind step-2 tests.
- **Model-delta backward diff** assumes `feature_list.json` is committed on a delivery PR. For runtime-only models the backward pass correctly skips; a delivery PR adding items WITHOUT committing the file is mitigated by the existing `baseline_gate` "trusted baseline expecting a delivery turns skip into deny" override. Seam accepted for the file-based Phase-1 model.
- **CodeQL/Sonar use GitHub's own diff/new-code engines**, so their "introduced by this PR" can differ from Semgrep/orphan across force-push/rebase. Accepted: they are same-repo-only secondary gates; Semgrep-OSS is the consistent primary that also covers forks.
- **gitleaks FP set is a snapshot.** New machine-dumped artifacts could re-introduce FP-shaped content under a non-allowlisted path and noisily fail secrets-scan. Accepted: a noisy fail is the safe direction; the path/value allowlist is the documented, reviewable place to extend.
- **Semgrep ↔ AST disagreement** on dynamic dispatch / metaprogrammed registration. The union-of-concerns rule reduces false-negatives but cannot make either engine complete. Accepted: the verifier's manual failed-flip (8.2) + the CI backstop remain the safety net.
- **`fetch-depth:0`** increases CI checkout cost on a large history. Accepted as the price of sound diff-awareness; the merge-base self-test makes a misconfigured shallow checkout fail loudly.
- **The local depth pillars are unreachable until step 14 wires the production feed.** Until the driver computes `changed_files`/`baseline_commit`, only the CI layer enforces the new depth checks — the "dual" in dual-enforcement is single. Accepted as *sequenced* (step 14), not silently assumed.
- **WIRING-id minting is per-analysis ordinal**, so the §3.1 validity cross-check sources `known_ids` from the committed model and exempts WIRING-prefixed ids from the dangling-ref subclass. Residual: a WIRING reference to a not-yet-committed id reads as dangling within the same PR; accepted — the ingester (step 8) commits the WIRING item before its references are gate-checked.

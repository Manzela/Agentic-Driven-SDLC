# Tech-debt: Cognitive-Complexity refactors (SonarCloud S3776 > 15)

**Status: tracked / DEFERRED by design.** Six `tools/` functions exceed SonarCloud's
Cognitive-Complexity threshold (S3776 default 15). This is the grounded plan to pay them down
when convenient — **not** urgent work.

## Why this is non-urgent (ground truth)

`sonar-project.properties:28` sets `sonar.exclusions=tools/**`. All six functions live under
`tools/`, which is **excluded from the blocking SonarCloud gate** (a documented controlled-debt
exemption — the file flags it "for EXPIRY once tools/ matures"). So these S3776 findings show on
the overall project measure but **do not block any PR**. Hence: defer, track here, and fold each
refactor into the next functional touch of its file (or do them as a batch right before lifting
the `tools/**` exclusion).

Baseline pinning tests confirmed green 2026-06-24 (92 + 17 + 17 passing across the suites below);
`conftest` is installed so the rego⇔python parity oracle really executes. Scores below are
SonarCloud-reported (no local complexipy/radon/lizard available); the *driver* is grounded in the
read control flow.

## Root cause (uniform)

Every function is a single flat scope interleaving 3–6 independently-testable responsibilities, so
S3776 sums the per-nesting-level penalty across all of them. The dominant shape is always the same:
a top-level guard/`try` wrapper + a loop whose body holds 2–4 nested sub-rules, OR two sequential
nested-loop passes, OR a long sequence of independent IO/branch blocks under one `try`. None is
algorithmically irreducible — it is co-located concern soup. **Fix is uniformly extract-method:**
lift each sub-rule / pass / IO block into a named `_`-prefixed pure helper (reusing each file's
existing helper convention), leaving the parent a thin orchestrator whose own score drops below 15.

## Definition of done (uniform, per function)

1. S3776 score < 15 for the function.
2. The named pinning test green **before and after** (pin-first → refactor → re-run; zero behaviour delta).
3. **No twin drift** — for `deny_merge`, the rego⇔python parity (`test_opa_conftest.py`) stays green and
   `.github/policies/coverage_query.rego` is **not** edited; for the orphan trio, the T1–T12 oracle
   (`test_phase1_integration.py`) stays green.

Each is its own behaviour-preserving commit. **Do not batch all six into one PR.**

## Sequenced plan (value ÷ risk)

### Order 1 — `tools/coverage_gate.py::deny_merge` (~25) · ~1.5h
Highest blast radius (dual-enforcement twin), fully pinned, no prereq. Extract per-rule helpers:
`_deny_reason_status(item)`, `_deny_reason_evidence(item)`, `_deny_reasons_actor_sep(item, ev)`,
`_deny_reason_wiring_kind(item, ev)`, plus `_validate_model_shape(feature_list)` for the early-return
guards. Parent = shape-check → in_scope filter → sorted loop calling the helpers → assemble.
**Pin:** `pytest tests/spine/test_coverage_gate.py tests/spine/test_coverage_gate_actor_sep.py tests/integration/test_opa_conftest.py -q` (last = the rego twin; must stay green).

### Order 2 — `tools/wiring_ingest.py::ingest_wiring_candidates` (~23) · ~1h
Isolated (no twin), low risk. Extract `_select_new_candidates(candidates, items)` (the qual-vs-id
de-dup loop) and `_validate_or_rollback(content, items, appended)` (keep validate + `items.remove`
rollback as **one** atomic unit). Parent = load → select → if none `return 0` → validate-or-rollback
→ atomic_write. **Pin:** `pytest tests/spine/test_wiring_dedup.py tests/integration/test_wiring_ingest.py -q`.

### Order 3 — `tools/orphan_detector.py::detect_orphans` (~23) + `::detect_orphans_diff` (~22) together · ~2.5h
They share the dangling-ref pattern — one PR, shared helpers: `_forward_pass(impl_units, known_ids)`,
`_backward_pass(requirements, referenced_ids)`, `_collect_dangling_refs(units, known_ids)` (reused by
both), `_scope_diff_inputs(...)` (the changed-files is-None/else block). **Pin:**
`pytest tests/spine/test_orphan_detector.py tests/spine/test_orphan_detector_diff.py tests/integration/test_phase1_integration.py -q` (T1–T12 oracle is load-bearing).

### Order 4 — `tools/evidence_gate.py::check_slice_orphans` (~19) · ~1.5h
Lowest score, closest to 15. Extract `_build_impl_units_from_changed(changed_files, repo_root)`,
`_load_model_and_requirements(feature_list_path, changed_files)`, `_verdict_from_report(report)`.
Keep all helper calls **inside** the outer fail-OPEN `try` (don't narrow the exception semantics).
**Pin:** `pytest tests/spine/test_evidence_gate_depth.py -q`.

### Order 5 — `tools/orphan_detector.py::main` (~27) · GATED, do LAST · ~3.5h
Highest score **and the only untested function** — `tests/integration/test_phase1_ci_workflows.py:122`
invokes the CLI with `--help` only (exits argparse before any logic). It owns the live
`traceability-gate` CI contract (exit 0=ok / 1=orphan + the JSON shape the gate parses), so a blind
refactor could silently change the gate's verdict.

- **5a (PREREQUISITE, separate commit): add `tests/spine/test_orphan_detector_cli.py`** pinning the
  CLI contract against the *current* `main()` — clean→exit 0 + `ok:true`; forward orphan→exit 1;
  missing `--feature-list` file→exit 1 + load error; malformed JSON→exit 1; `--baseline-commit` path
  takes the diff-aware branch; `--links` fold-in resolves a backward orphan. *(These are
  human/verifier-owned test artifacts — propose, then have a human/verifier author-or-approve before 5b.)*
- **5b (refactor):** extract `_build_arg_parser()`, `_load_model_or_error(path)`, `_fold_in_links(...)`,
  `_run_diff_aware(...)`. **Pin (now exists):** `pytest tests/spine/test_orphan_detector_cli.py -q`.

## Total

~13.5h across the epic. Open decision for a human: do these **now**, or **batch them right before
dropping the `tools/**` Sonar exclusion** (the exclusion is the reason there is zero gate pressure today).

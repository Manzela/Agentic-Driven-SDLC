# Implementation Plan: Spec-to-Evidence Coverage Control System

## Overview

Build the autonomous agentic software-delivery control plane on the Claude Code substrate in four required phases (0–3) plus Phase 4 (PBT suite), with two optional phases: Phase 5 (Temporal/Inngest durable outer loop) and Phase 6 (predictive routing). Phase 0 (spine) is the hard prerequisite for all subsequent phases: every spine component must be coded, wired, and smoke-tested before any Phase 1 task begins. Implementation language is Python throughout.

---

## Tasks

### Phase 0 — Spine

- [ ] 1. Repo scaffold and Python environment
  - Create directory tree: `.claude/hooks/`, `.claude/agents/`, `tools/`, `schema/`, `tests/unit/`, `tests/integration/`, `tests/property/`, `tests/smoke/`, `db/migrations/`, `.github/workflows/`, `.github/policies/`, `baselines/`
  - Create `pyproject.toml` (or `requirements.txt`) pinning `z3-solver`, `hypothesis`, `jsonschema`, `psycopg2-binary`, `semgrep`, `playwright`
  - Create `.vscode/settings.json` (or `.kiro/settings.json`) stub for hook wiring (populated in task 8)
  - Create `claude-progress.txt` placeholder and `.gitignore` entries
  - _Requirements: 11.1, 11.4_

  - [ ]* 1.1 Smoke-test scaffold: verify directory structure matches design component inventory
    - Assert all required directories exist; fail fast if any are missing
    - _Requirements: 7.1_

- [ ] 2. `feature_list.schema.json` — Coverage Model Schema
  - [ ] 2.1 Implement `schema/feature_list.schema.json`
    - Write JSON Schema (draft-07) with all required top-level fields: `schema_version`, `product_class`, `checklist_ref`, `items`
    - Define `CoverageItem` definition: `id` (pattern `^[A-Z]+-[A-Z]+-[0-9]{3}$`), `type` enum `{functional,NFR,WIRING}`, `priority`, `dependencies`, `acceptance_criteria` (minItems 1), `status` enum `{unproven,proven,failed}` default `unproven`, optional `evidence` ref
    - Define `EvidenceRecord` definition: all four required fields (`test_file`, `test_name`, `output_hash` with sha256 pattern, `collected_at` date-time), `additionalProperties: false`
    - _Requirements: 5.1, 5.3, 5.6_

  - [ ]* 2.2 Write property test for coverage item schema invariant
    - **Property 1: Coverage Item Schema Invariant**
    - **Validates: Requirements 5.1, 5.4**
    - Use `hypothesis` to generate arbitrary `feature_list.json`-shaped dicts; assert every generated valid item passes schema validation; assert any item with missing required field or wrong `type` enum fails
    - `# Feature: spec-to-evidence-control, Property 1: Coverage Item Schema Invariant`

  - [ ]* 2.3 Write property test for evidence schema enforcement (four-field gate)
    - **Property 2: Evidence Schema Enforcement (Four-Field Gate)**
    - **Validates: Requirements 5.3, 5.6**
    - Generate `EvidenceRecord` dicts with arbitrary field combinations; assert validation passes only when all four fields present and non-empty; assert any single missing/empty field causes validation failure
    - `# Feature: spec-to-evidence-control, Property 2: Evidence Schema Enforcement`

- [ ] 3. `evidence_collector.py` — Evidence_Record Builder
  - [ ] 3.1 Implement `tools/evidence_collector.py`
    - Write `collect(test_file, test_name, output_bytes) -> EvidenceRecord` function: compute `sha256:<hex>` from `output_bytes`, capture ISO-8601 `collected_at` from `datetime.utcnow()`
    - Write `validate_evidence_record(record: dict) -> bool` that checks all four fields present and non-empty; raise `ValueError` listing missing fields on failure
    - Write `store_to_feature_list(item_id, record, feature_list_path)` that atomically writes evidence and flips status to `proven` via JSON patch — blocked if any field missing
    - _Requirements: 5.3, 5.6, 9.3_

  - [ ]* 3.2 Write property test for evidence round-trip
    - **Property 19: Evidence Round-Trip (Store and Retrieve)**
    - **Validates: Requirements 16.2**
    - Generate arbitrary `(test_file, test_name, output_bytes)` triples; collect → validate → assert all four fields present and `output_hash` matches SHA-256 of input bytes
    - `# Feature: spec-to-evidence-control, Property 19: Evidence Round-Trip`

  - [ ]* 3.3 Write unit tests for `evidence_collector.py`
    - Test: `collect()` with empty bytes produces valid `sha256:` prefixed hash matching pattern `^sha256:[a-f0-9]{64}$`
    - Test: `collect()` with non-empty bytes produces a hash matching the same pattern and the `sha256:` prefix is always present
    - Test: `validate_evidence_record()` rejects records missing each of the four fields individually
    - Test: `store_to_feature_list()` rejects transition when evidence incomplete
    - _Requirements: 5.3, 5.6_

- [ ] 4. `spec_validator.py` — Z3-Backed EARS Validator
  - [ ] 4.1 Implement `tools/spec_validator.py`
    - Write EARS pattern encoder: map each pattern (Ubiquitous, Event-driven, State-driven, Unwanted, Optional) to Z3 Boolean formula using the SMT-lib translation rules in the design
    - Write `validate_spec(requirements: list[dict]) -> dict` returning `{contradictions, ambiguities, uncovered, violation_count}`
    - Implement consistency check (`check-sat` on full axiom set), completeness check (UNMAPPED detection), vacuity check, and independence check (prediction variables cannot influence gate decisions)
    - Implement vague-adjective scanner: reject any requirement containing `{fast,secure,scalable,optimized,efficient,reliable,performant}` without a numeric bound
    - Set Z3 solver timeout to DEFAULT 60 seconds; return `{violation_count: -1, error: "validator_timeout"}` on timeout
    - _Requirements: 1.2, 1.4, 4.1, 4.2, 4.3_

  - [ ]* 4.2 Write property test for spec validator structured output
    - **Property 14: Spec Validator Returns Structured Output**
    - **Validates: Requirements 4.1**
    - Generate arbitrary requirement lists; assert `validate_spec()` always returns a dict with exactly the four fields `{contradictions, ambiguities, uncovered, violation_count}`; assert authoring agent output is never consulted
    - `# Feature: spec-to-evidence-control, Property 14: Spec Validator Returns Structured Output`

  - [ ]* 4.3 Write property test for EARS pattern assignment uniqueness
    - **Property 16: EARS Pattern Assignment Uniqueness**
    - **Validates: Requirements 1.4**
    - Generate arbitrary requirement strings; assert each validated requirement carries exactly one EARS pattern tag; assert zero-pattern and multi-pattern cases are rejected
    - `# Feature: spec-to-evidence-control, Property 16: EARS Pattern Assignment Uniqueness`

  - [ ]* 4.4 Write property test for vague-adjective rejection
    - **Property 17: Vague-Adjective Rejection**
    - **Validates: Requirements 1.2**
    - Generate requirement strings that embed each vague adjective from the set `{fast,secure,scalable,optimized,efficient,reliable,performant}` in arbitrary positions without a numeric bound; assert all are rejected; assert strings with numeric bounds pass
    - `# Feature: spec-to-evidence-control, Property 17: Vague-Adjective Rejection`

  - [ ]* 4.5 Write unit tests for `spec_validator.py`
    - Reproduce all 29 formal-verification checks from `formal_verification_merged.py` as unit assertions
    - Test timeout path: mock Z3 solver to raise `TimeoutError`; assert return value has `violation_count == -1`
    - _Requirements: 4.1, 4.2_

- [ ] 5. `stop_hook.py` — Coverage Gate + Watchdog + Reentrancy Guard
  - [ ] 5.1 Implement `.claude/hooks/stop_hook.py`
    - Implement `load_feature_list()` and `load_run_state()` (reading from `feature_list.json` and `claude-progress.txt` / in-memory fallback before Postgres)
    - Implement `check_no_progress(run_state, feature_list) -> bool`: count items proven and commits produced across last N=3 slices; fire when both are zero
    - Implement `evaluate_stop(event) -> HookDecision`: Check 1 — any `unproven` items → exit 2 with enumerated IDs; Check 2 — no-progress fires → write HANDOFF, exit 2; Check 3 — iteration cap (DEFAULT 25) reached → write HANDOFF, exit 2; else → exit 0
    - Implement `with_reentrancy_guard(fn)`: set `stop_hook_active = True` before evaluation, release only on allow; skip evaluation if flag already set
    - Wrap entire hook in `try/except`; on unhandled exception exit 2 (fail closed) with structured error to stderr
    - _Requirements: 4.2, 4.3, 4.4, 10.2, 10.4, 14.1, 14.2_

  - [ ]* 5.2 Write property test for stop hook — unproven blocks termination
    - **Property 5: Stop Hook — Unproven Blocks Termination**
    - **Validates: Requirements 5.5, 10.2**
    - Generate feature lists with arbitrary mixes of `unproven`/`proven` items; assert hook blocks (exit 2) when any item is `unproven`; assert hook allows (exit 0) only when zero items are `unproven`
    - `# Feature: spec-to-evidence-control, Property 5: Stop Hook — Unproven Blocks Termination`

  - [ ]* 5.3 Write property test for no-progress → HANDOFF only
    - **Property 8: No-Progress → HANDOFF Only**
    - **Validates: Requirements 14.2, 21.1**
    - Generate run states with arbitrary `no_progress_n` values and slice histories using N=3 (DEFAULT, fixed — not arbitrary N); assert that when both conditions (zero proven, zero commits) hold for N=3 consecutive slices, `status` transitions to `handoff` never `complete`, AND the Stop hook exits 0 (allow termination), never exits 2 (which would force-continue — the infinite-block defect)
    - `# Feature: spec-to-evidence-control, Property 8: No-Progress → HANDOFF Only`

  - [ ]* 5.4 Write property test for cap and budget → HANDOFF only
    - **Property 9: Cap and Budget → HANDOFF Only**
    - **Validates: Requirements 14.1, 14.2, 21.1**
    - Generate run states at or beyond the iteration cap (DEFAULT 25) or cost budget; assert terminal status is always `handoff`; assert `complete` and `handoff` are never simultaneously true; assert the Stop hook returns exit 0 (allow termination) not exit 2 (which would force-continue) — Z3 CHECK-5b/5c verified
    - `# Feature: spec-to-evidence-control, Property 9: Cap and Budget → HANDOFF Only`

  - [ ]* 5.5 Write unit tests for `stop_hook.py`
    - Test reentrancy guard: call hook twice concurrently; assert second call returns allow immediately
    - Test: unhandled exception in body → exits 2 with error message
    - _Requirements: 10.4_

- [ ] 6. `pre_tool_use_hook.py` — Plan Gate + Scope Gate + Artifact Guard + Status Guard
  - [ ] 6.1 Implement `.claude/hooks/pre_tool_use_hook.py`
    - Implement `check_plan_approval(event) -> Optional[HookDecision]`: block any `Write`/`Edit`/`MultiEdit` call if `plan-approved.json` missing; also verify `feature_list_sha` in approval matches current `feature_list.json` SHA-256
    - Implement `check_scope_sequencing(event) -> Optional[HookDecision]`: block any `Bash` worktree-create or slice-assign call if any prior-slice item in `feature_list.json` is `unproven`
    - Implement `check_artifact_guard(event) -> Optional[HookDecision]`: block any tool targeting `feature_list.json` schema, `tests/`, CI config, or executing destructive Bash patterns (`rm -rf`, `DROP TABLE`, `git reset --hard`)
    - Implement `check_status_transition(event) -> Optional[HookDecision]`: for any write to `feature_list.json`, validate proposed transition is `unproven → proven` only; validate Evidence_Record completeness before allowing `proven` write
    - Chain all four checks; return first blocking decision; wrap in `try/except` with exit 2 on exception (fail closed)
    - _Requirements: 5.2, 5.3, 7.4, 7.5, 13.2, 13.3, 13.4, 18.1_

  - [ ]* 6.2 Write property test for plan approval gate
    - **Property 6: Plan Approval Gate**
    - **Validates: Requirements 7.4, 18.1**
    - Generate `(tool_name, plan_file_exists, sha_matches)` triples; assert hook blocks any Write/Edit/MultiEdit when `plan_file_exists=False` or `sha_matches=False`; assert hook allows only when both true
    - `# Feature: spec-to-evidence-control, Property 6: Plan Approval Gate`

  - [ ]* 6.3 Write property test for scope sequencing gate
    - **Property 7: Scope Sequencing Gate**
    - **Validates: Requirements 7.5**
    - Generate feature lists with arbitrary subsets of items marked `unproven`; assert worktree-create is blocked whenever any prior item is `unproven`; assert it is allowed only when all prior items are `proven`
    - `# Feature: spec-to-evidence-control, Property 7: Scope Sequencing Gate`

  - [ ]* 6.4 Write property test for identity mutation blockade
    - **Property 3: Identity-Mutation Blockade**
    - **Validates: Requirements 5.2, 13.3**
    - Generate tool calls that attempt to delete, reorder, or change `id`/`type`/`acceptance_criteria` of existing items; assert all are blocked; assert only `status: proven` writes are allowed
    - `# Feature: spec-to-evidence-control, Property 3: Identity-Mutation Blockade`

  - [ ]* 6.5 Write unit tests for `pre_tool_use_hook.py`
    - Test each of the four check functions independently with boundary inputs
    - Test: exception in any check → exits 2, never exits 0
    - _Requirements: 13.4, 13.5_

- [ ] 7. `session_start_hook.py` — State Loader
  - [ ] 7.1 Implement `.claude/hooks/session_start_hook.py`
    - Read `git status --porcelain` output and format as structured summary
    - Read `claude-progress.txt` (create with empty state if absent)
    - Read and parse `feature_list.json` (create minimal valid stub if absent); compute count of `unproven` vs `proven` items
    - Inject combined summary into Claude Code context via stdout (informational only — exit 0 always)
    - Wrap in `try/except`; on failure log warning to stderr and exit 0 (non-blocking)
    - _Requirements: 11.3_

  - [ ]* 7.2 Write unit tests for `session_start_hook.py`
    - Test: on first-run (no progress file, no feature_list.json) → exits 0 with stub summary
    - Test: with populated `feature_list.json` → summary includes correct unproven count
    - _Requirements: 11.3_

- [ ] 8. `subagent_stop_hook.py` — Evidence Schema Validator
  - [ ] 8.1 Implement `.claude/hooks/subagent_stop_hook.py`
    - Parse subagent result from stdin (JSON); locate `evidence` field(s) within result
    - Call `validate_evidence_record()` from `evidence_collector.py` on each evidence record
    - If any field missing or empty: exit 2 with enumerated missing fields (fail closed)
    - If all records valid: exit 0
    - Wrap in `try/except`; exit 2 on unhandled exception
    - _Requirements: 9.5_

  - [ ]* 8.2 Write unit tests for `subagent_stop_hook.py`
    - Test: subagent result with complete Evidence_Record → exits 0
    - Test: subagent result missing `output_hash` → exits 2 naming `output_hash`
    - Test: subagent result with zero evidence fields → exits 2
    - _Requirements: 9.5_

- [ ] 9. `settings.json` Hook Wiring
  - [ ] 9.1 Write `.claude/settings.json` (or `.kiro/settings.json`) with all hook registrations
    - Register `Stop`, `PreToolUse`, `PostToolUse` (matcher: `Write|Edit|MultiEdit`), `SubagentStop`, `SessionStart`, `PreCompact` — all as `"type": "command"`
    - Verify NO hook uses `"type": "http"` or `"type": "mcp"` (fail-closed requirement)
    - _Requirements: 13.4_

  - [ ]* 9.2 Smoke-test hook config: assert all hooks are command-type
    - Write `tests/smoke/test_hook_config.py`: parse `settings.json`; assert every registered hook has `"type": "command"`; assert no HTTP/MCP hooks present
    - _Requirements: 13.4_

- [ ] 10. Subagent definitions (`.claude/agents/`)
  - [ ] 10.1 Write `.claude/agents/initializer.md` — Spec Compiler + Coverage Model Builder
    - Define role, permissions (read/write spec artifacts + `feature_list.json` + baselines; no access to `tests/`, CI, or `src/`), and key behaviors
    - Include: run `spec_validator.py` after every elaboration pass; loop bounded to DEFAULT=7 passes; flag UNMAPPED items; write all items defaulting to `unproven`; enter plan mode; do NOT write `plan-approved.json`
    - Include HANDOFF conditions: no-progress (count doesn't decrease) → immediate HANDOFF; pass cap reached → HANDOFF
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 18.2_

  - [ ] 10.2 Write `.claude/agents/implementer.md` — Coding Subagent
    - Define role, permissions (write to implementation source in assigned worktree only; no write to `tests/`, `feature_list.json` schema, CI, or other worktrees), and key behaviors
    - Include: read `feature_list.json` for highest-priority `unproven` item; create dedicated git worktree; target ≤15 min / ≤1 feature; produce one atomic commit with requirement ID in trailer; do NOT run verification
    - _Requirements: 7.1, 7.2, 7.3, 6.2_

  - [ ] 10.3 Write `.claude/agents/verifier.md` — Independent Evaluator
    - Define role, permissions (read-only on `src/`; read/write on `tests/` and `feature_list.json` status field only; no write to implementation source), and key behaviors
    - Include: structural checks (lint, type check, AST), semantic checks (unit + integration tests), behavioral checks (Playwright CLI → capture trace/screenshot), security checks (Semgrep + CodeQL)
    - Include: performance/accessibility layer — k6/Lighthouse for `performance` NFR items (p95 latency, Core Web Vitals thresholds) and axe-core for `accessibility` NFR items (zero WCAG-A/AA violations on covered screens) as per REQ-VERIFY-007; UI-screen completeness checks (empty/loading/error states) as per REQ-VERIFY-008
    - Coverage tool: use `coverage.py` (`python -m pytest --cov --cov-report=json`) to generate per-file line coverage; read JSON report to check each touched file ≥ 85%
    - Assemble Evidence_Record via `evidence_collector.py`, flip `unproven → proven` only when all checks pass, coverage ≥ 85% on all touched files, and acting agent identity is `verifier.md` (not `implementer.md`)
    - _Requirements: 9.1, 9.2, 9.3, 9.6, 25.1, 25.2, 25.3_

  - [ ] 10.4 Write `.claude/agents/research.md` — Domain-Baseline Checklist Sourcer
    - Define role, permissions (read/write to `baselines/`; no access to `src/`, `tests/`, or CI), and key behaviors
    - Include: triggered by Initializer on new product class; query competitive analysis + standards + OSS refs; produce draft checklist named by product class under `baselines/`; present for human review; do NOT use checklist until approved; persist approved checklist as version-controlled artifact
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 11. Git worktree wiring scripts
  - [ ] 11.1 Write `tools/worktree_manager.py`
    - Implement `create_worktree(item_id: str) -> str`: run `git worktree add .worktrees/{item_id} -b slice/{item_id}`; return worktree path
    - Implement `remove_worktree(item_id: str)`: run `git worktree remove --force .worktrees/{item_id}` after merge/abandon
    - Implement `list_active_worktrees() -> list[str]`: parse `git worktree list --porcelain`
    - Enforce: one worktree per active slice; fail if worktree already exists for `item_id`
    - _Requirements: 7.2, 7.3_

  - [ ]* 11.2 Write integration tests for worktree wiring
    - Test: `create_worktree` → `git worktree list` shows exactly one entry for `item_id`
    - Test: `remove_worktree` → worktree no longer listed
    - Test: duplicate create for same `item_id` → raises error
    - _Requirements: 7.2_

- [ ] 12. `feature_list.json` initializer — empty coverage model
  - [ ] 12.1 Write `tools/feature_list_init.py`
    - Implement `initialize_feature_list(product_class, checklist_ref) -> dict`: produce a minimal valid `feature_list.json` with `schema_version: "1.0.0"`, empty `items: []`, and provided `product_class` / `checklist_ref`
    - Validate the produced file against `schema/feature_list.schema.json` before writing to disk
    - Write the validated file atomically (write to temp, then `os.replace`)
    - _Requirements: 5.1_

  - [ ]* 12.2 Write unit tests for `feature_list_init.py`
    - Test: initialized file passes schema validation
    - Test: file with missing `checklist_ref.sha` fails schema validation
    - _Requirements: 5.1_

- [ ] 13. Wire `formal_verification_merged.py` as CI check
  - [ ] 13.1 Create `.github/workflows/formal-verification.yml`
    - Trigger on `push` and `pull_request`
    - Install `z3-solver` via pip in a venv; run `python3 formal_verification_merged.py` (supersedes `formal_verification.py`)
    - Fail workflow if exit code is non-zero (any assertion failure)
    - Register as a required status check in GitHub repository ruleset
    - _Requirements: 4.1_

  - [ ]* 13.2 Smoke-test: verify `formal_verification_merged.py` currently exits 0
    - Run `python3 formal_verification_merged.py` in CI; assert exit 0 (all 29 checks pass)
    - _Requirements: 4.1_

- [ ] 14. GitHub Actions coverage gate (OPA/Conftest stub for Phase 0)
  - [ ] 14.1 Create `.github/workflows/coverage-gate.yml`
    - Trigger on `pull_request`
    - Install OPA/Conftest; run `conftest test feature_list.json --policy .github/policies/` 
    - For Phase 0: write a minimal `coverage_query.rego` stub that passes only when `feature_list.json` contains zero `unproven` items (full Postgres-backed policy deferred to Phase 1 task 20)
    - Register as a required status check in GitHub repository ruleset
    - _Requirements: 10.3_

  - [ ] 14.2 Configure GitHub repository ruleset
    - Document (in `docs/github-ruleset.md`) the required status checks: `formal-verification`, `coverage-gate`, plus human PR reviewer requirement
    - _Requirements: 10.3, 18.3_

- [ ] 15. Playwright CLI integration in CI
  - [ ] 15.1 Add Playwright step to `.github/workflows/coverage-gate.yml`
    - Install `playwright` and `playwright install chromium`
    - Run `playwright test tests/smoke/` (smoke suite to be populated by Verifier agent during slice verification)
    - Upload trace file as workflow artifact on failure
    - _Requirements: 9.1, 9.3_

- [ ] 16. Phase 0 Smoke Test — end-to-end spine
  - [ ] 16.1 Write `tests/smoke/test_spine_e2e.py`
    - Create a trivial `feature_list.json` with one `unproven` item and one `proven` item (with valid Evidence_Record)
    - Call `stop_hook.py` via subprocess with the `unproven`-containing file → assert exit 2
    - Call `stop_hook.py` with all-`proven` file → assert exit 0
    - Call `pre_tool_use_hook.py` with Write tool and no `plan-approved.json` → assert exit 2
    - Call `session_start_hook.py` → assert exit 0 and stdout contains git/progress/coverage summary
    - Call `subagent_stop_hook.py` with complete Evidence_Record → assert exit 0; with missing `output_hash` → assert exit 2
    - _Requirements: 5.5, 7.4, 9.5, 10.2, 11.3_

- [ ] 17. Phase 0 end-to-end integration test
  - [ ] 17.1 Write `tests/integration/test_phase0_integration.py`
    - Create a temp git repo with a `feature_list.json` containing one `unproven` and one fully-evidenced `proven` item
    - Call `stop_hook.py` via subprocess against the mixed file; assert exit 2 and stderr names the unproven item ID
    - Call `stop_hook.py` against an all-proven file; assert exit 0
    - Call `pre_tool_use_hook.py` with a `Write` event and no `plan-approved.json`; assert exit 2
    - Write a valid `plan-approved.json` with matching SHA; call hook again with `Write` event; assert exit 0
    - Call `pre_tool_use_hook.py` with a worktree-create event while a prior item is `unproven`; assert exit 2
    - Call `session_start_hook.py`; assert exit 0 and stdout JSON contains `git_status`, `unproven_count`, `proven_count`
    - Call `subagent_stop_hook.py` with a complete 4-field Evidence_Record; assert exit 0
    - Call `subagent_stop_hook.py` with `output_hash` missing; assert exit 2 and error names `output_hash`
    - Run `python3 formal_verification_merged.py`; assert exit 0 (all 29 checks pass)
    - _Requirements: 4.2, 5.5, 7.4, 7.5, 9.5, 10.2, 11.3, 13.5_

---

### Phase 1 — Verification Depth

- [ ] 18. `post_tool_use_hook.py` — Lint + SAST + Wiring Feedback
  - [ ] 18.1 Implement `.claude/hooks/post_tool_use_hook.py`
    - Triggered on `Write`, `Edit`, `MultiEdit` completion
    - Run lint (e.g., `ruff check`) on changed files; run type check (`mypy`); capture stdout/stderr
    - Run `semgrep --config auto` on changed files; filter for HIGH/CRITICAL findings
    - Run `python3 tools/wiring_checker.py` on changed files
    - Collect all findings; emit to stdout as structured feedback; exit 1 (non-blocking, next-turn feedback only — never exit 2)
    - Wrap in `try/except`; exit 1 on exception (non-blocking)
    - _Requirements: 9.4, 13.2_

  - [ ]* 18.2 Write unit tests for `post_tool_use_hook.py`
    - Test: clean file → exits 1 with empty findings list (still non-blocking)
    - Test: file with lint error → exits 1 with lint finding in output
    - Test: exception in body → exits 1 (never exits 2)
    - _Requirements: 9.4, 13.2_

- [ ] 19. `wiring_checker.py` — Call-Graph / Dead-Code Analysis
  - [ ] 19.1 Implement `tools/wiring_checker.py`
    - Accept a list of changed files as CLI args
    - Use Python AST (`ast` module) to build a call graph for each file: map function/method definitions to their call sites
    - Identify functions/methods that are never called from any real execution path (dead code)
    - For each dead-code finding, emit a WIRING coverage item candidate (JSON to stdout) with `type: "WIRING"` and the unreachable symbol name
    - Exit 0 even when findings exist (findings are returned to caller; blocking is done by `post_tool_use_hook.py`)
    - _Requirements: 8.1, 8.2_

  - [ ]* 19.2 Write unit tests for `wiring_checker.py`
    - Test: file with reachable route handler → no WIRING finding
    - Test: file with defined but never-called function → emits WIRING finding
    - _Requirements: 8.1_

- [ ] 20. `orphan_detector.py` — Bidirectional Orphan Check
  - [ ] 20.1 Implement `tools/orphan_detector.py`
    - Scan all source files for requirement ID references matching `[A-Z]+-[A-Z]+-[0-9]{3}` in comments, docstrings, and commit trailers
    - Read `feature_list.json` for all known requirement IDs
    - Report: (a) source files/functions with no requirement ref (forward orphans); (b) requirement IDs with no source file or verification artifact (backward orphans)
    - Exit non-zero and emit structured JSON report when any orphan is found
    - _Requirements: 6.3_

  - [ ]* 20.2 Write property test for orphan detection
    - **Property 11: Orphan Detection**
    - **Validates: Requirements 6.3**
    - Generate source-file/requirement pairs with arbitrary coverage; assert detector always flags (a) any impl unit with no req ref and (b) any req with no verification artifact; assert both conditions independently trigger failure
    - `# Feature: spec-to-evidence-control, Property 11: Orphan Detection`

- [ ] 21. `coverage_query.rego` — Full OPA Zero-Evidence Merge Policy
  - [ ] 21.1 Implement `.github/policies/coverage_query.rego` (full policy, replacing Phase 0 stub)
    - Write Rego policy: deny merge if any requirement ID in the approved set has zero rows in `evidence_records`
    - Accept `feature_list.json` as Conftest input; policy reads `items[_].status == "unproven"` and denies if any found
    - Add second rule: deny if any item has `status == "proven"` but `evidence` object is missing or has empty fields
    - Write fixture files under `tests/integration/opa/`: one passing fixture (all proven with evidence), one failing fixture (one unproven item)
    - _Requirements: 10.3_

  - [ ]* 21.2 Write property test for OPA zero-evidence policy at merge
    - **Property 22: OPA Zero-Evidence Policy at Merge**
    - **Validates: Requirements 10.3**
    - Generate `feature_list.json` variants with arbitrary proven/unproven distributions; assert Conftest policy denies merge whenever any item lacks evidence; assert policy allows only when every approved requirement has evidence
    - `# Feature: spec-to-evidence-control, Property 22: OPA Zero-Evidence Policy at Merge`

  - [ ]* 21.3 Write integration tests for OPA/Conftest policy
    - Run `conftest test` against passing and failing fixtures; assert correct pass/fail behavior
    - _Requirements: 10.3_

- [ ] 22. SonarQube AI Code Assurance quality gate in CI
  - [ ] 22.1 Add SonarQube scan step to `.github/workflows/coverage-gate.yml`
    - Add `sonarcloud-github-action` step (or equivalent) with project key configured
    - Configure quality gate: fail on any new HIGH/CRITICAL finding or coverage drop below 85%
    - _Requirements: 9.1, 9.6_

- [ ] 23. CodeQL SAST in GitHub Actions
  - [ ] 23.1 Create `.github/workflows/codeql.yml`
    - Use `github/codeql-action/analyze` for Python
    - Trigger on `push` and `pull_request`
    - Fail on HIGH/CRITICAL severity findings
    - _Requirements: 9.1, 17.1_

- [ ] 24. Semgrep custom rules for WIRING dead-code patterns
  - [ ] 24.1 Write `tools/semgrep_rules/wiring_dead_code.yml`
    - Define Semgrep rule to detect functions decorated with route/handler decorators (e.g., `@app.route`, `@router.get`) that are never imported or called from a non-test entry point
    - Define rule for callbacks registered in a dict/list but never invoked
    - Test rules against synthetic fixtures in `tests/fixtures/semgrep/`
    - _Requirements: 8.1, 8.2_

- [ ] 25. `pre_compact_hook.py` — PreCompact Checkpoint
  - [ ] 25.1 Implement `.claude/hooks/pre_compact_hook.py`
    - Before context compaction: append current progress summary (item IDs, status counts) to `claude-progress.txt`
    - Write a JSON snapshot of current `feature_list.json` evidence state to `claude-progress-evidence-snapshot.json`
    - Commit both files via `git add -f ... && git commit -m "chore: PreCompact checkpoint [skip ci]"` if anything has changed
    - Exit 0 always (non-blocking checkpoint)
    - _Requirements: 11.2_

  - [ ]* 25.2 Write unit tests for `pre_compact_hook.py`
    - Test: hook writes progress checkpoint and exits 0
    - Test: hook does not fail if git has no changes to commit
    - _Requirements: 11.2_

- [ ] 26. Phase 1 verification integration test
  - [ ] 26.1 Write `tests/integration/test_phase1_integration.py`
    - Create a Python source file with a defined-but-never-called function; run `wiring_checker.py` against it; assert JSON output contains a WIRING finding with `type: "WIRING"` and the symbol name
    - Create a source file with no requirement ID comment and a `feature_list.json` with one requirement; run `orphan_detector.py`; assert exit non-zero and report contains both orphan types
    - Write a `feature_list.json` with one `unproven` item; run `conftest test` against `.github/policies/coverage_query.rego`; assert policy denies
    - Write a `feature_list.json` with all `proven` items and complete evidence; run `conftest test`; assert policy passes
    - Run `post_tool_use_hook.py` against a file with a lint error; assert exit 1 (non-blocking) and stdout contains the error message
    - _Requirements: 8.1, 8.2, 9.4, 10.3, 13.2_

---

### Phase 2 — Durable State

- [ ] 27. Neon Postgres provisioning and connection management
  - [ ] 27.1 Write `tools/db_connection.py`
    - Implement `get_connection() -> psycopg2.Connection`: read `DATABASE_URL` from environment; support Neon serverless endpoint (SSL required); raise `ConfigError` if `DATABASE_URL` unset
    - Implement `health_check() -> bool`: run `SELECT 1`; return True/False; used as fallback-to-file trigger
    - Document in `docs/postgres-setup.md`: Neon project creation, per-PR branching setup, `DATABASE_URL` secret registration in GitHub Actions
    - _Requirements: 16.1_

- [ ] 28. Postgres schema migrations
  - [ ] 28.1 Write migration `db/migrations/001_requirements.sql`
    - `requirements` table with all columns and CHECK constraints as per design schema
    - _Requirements: 16.1_

  - [ ] 28.2 Write migration `db/migrations/002_coverage_items.sql`
    - `coverage_items` table with FK to `requirements`, status CHECK, default `unproven`
    - _Requirements: 16.1_

  - [ ] 28.3 Write migration `db/migrations/003_traceability_links.sql`
    - `traceability_links` table with FK to `requirements`, `link_type` and `direction` CHECK constraints
    - _Requirements: 6.1, 16.1_

  - [ ] 28.4 Write migration `db/migrations/004_evidence_records.sql`
    - `evidence_records` table with FK to `requirements`, `evidence_complete` CHECK constraint enforcing no empty fields
    - _Requirements: 5.3, 5.6, 16.1_

  - [ ] 28.5 Write migration `db/migrations/005_run_state.sql`
    - `run_state` table with `status` CHECK `{running,complete,handoff,blocked}`, `stop_hook_active` boolean, `no_progress_n` counter
    - _Requirements: 11.1, 16.1_

  - [ ] 28.6 Write migration `db/migrations/006_domain_baseline_checklists.sql`
    - `domain_baseline_checklists` table with `UNIQUE (product_class, version)`, `approved_at` nullable
    - _Requirements: 3.2, 16.1_

  - [ ] 28.7 Write migration `db/migrations/007_requirement_versions.sql`
    - `requirement_versions` table: `id SERIAL`, `requirement_id TEXT REFERENCES requirements(id)`, `version INTEGER NOT NULL`, `prior_text TEXT`, `new_text TEXT NOT NULL`, `author TEXT NOT NULL`, `rationale TEXT NOT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `UNIQUE (requirement_id, version)`
    - On amendment: insert version row AND reset `coverage_items.status` to `unproven` (trigger or app-level enforcement)
    - _Requirements: 22.1, 16.1_

  - [ ] 28.8 Write migration `db/migrations/008_gate_audit_log.sql`
    - `gate_audit_log` table: `seq BIGSERIAL PRIMARY KEY`, `event_name TEXT NOT NULL`, `tool_name TEXT`, `decision TEXT NOT NULL CHECK (decision IN ('allow','block'))`, `reason TEXT`, `requirement_id TEXT`, `actor_agent TEXT NOT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `prev_hash TEXT NOT NULL`, `entry_hash TEXT NOT NULL`
    - Hash chain: `entry_hash = sha256(canonical_row_json || prev_hash)`. First row's `prev_hash` = sha256("genesis")
    - _Requirements: 27.1, 27.2, 16.1_

  - [ ]* 28.9 Write integration tests for Postgres schema
    - Run all 8 migrations (001–008) on a test Neon branch; assert all tables created
    - Test `evidence_complete` CHECK rejects incomplete records
    - Test `requirement_versions` UNIQUE constraint rejects duplicate (requirement_id, version) pairs
    - Test `gate_audit_log` hash chain: insert two rows; verify `entry_hash` of row 2 = sha256(canonical_json(row2) || row1.entry_hash)
    - _Requirements: 5.6, 16.1, 22.1, 27.1_

- [ ] 29. Traceability link writer — commit trailer parser
  - [ ] 29.1 Write `tools/traceability_writer.py`
    - Implement `parse_commit_trailers(commit_sha: str) -> list[str]`: extract requirement IDs matching `[A-Z]+-[A-Z]+-[0-9]{3}` from `git log --format=%B -n1 {sha}`
    - Implement `write_traceability_link(req_id, link_type, target_ref, direction)`: insert into `traceability_links` table
    - Implement `assert_commit_has_req_id(commit_sha)`: raise `TraceabilityError` if no requirement ID found in trailer
    - _Requirements: 6.1, 6.2_

  - [ ]* 29.2 Write property test for commit trailer requirement ID
    - **Property 10: Commit Trailer Requirement ID**
    - **Validates: Requirements 6.2**
    - Generate arbitrary commit message strings; assert `parse_commit_trailers` returns non-empty list only when at least one ID matching `[A-Z]+-[A-Z]+-[0-9]{3}` is present; assert commits without IDs raise `TraceabilityError`
    - `# Feature: spec-to-evidence-control, Property 10: Commit Trailer Requirement ID`

- [ ] 30. Evidence storage integration — `evidence_collector.py` → `evidence_records` table
  - [ ] 30.1 Extend `tools/evidence_collector.py` with Postgres persistence
    - Add `store_to_postgres(record: EvidenceRecord, req_id: str, commit_sha: str)`: insert into `evidence_records` table via `db_connection.get_connection()`; fall back to `feature_list.json` update if DB unavailable
    - _Requirements: 16.2_

  - [ ]* 30.2 Write integration tests for evidence storage
    - Test: `store_to_postgres` with complete record → row appears in `evidence_records` with correct field values
    - Test: DB unavailable → falls back to `feature_list.json` without raising
    - _Requirements: 16.2_

- [ ] 31. Run state persistence — `run_state` table integration
  - [ ] 31.1 Write `tools/run_state_manager.py`
    - Implement `load_run_state(session_id) -> RunState`: read from `run_state` table; fall back to `claude-progress.txt` if DB unavailable
    - Implement `save_run_state(run_state: RunState)`: upsert into `run_state` table; also write `claude-progress.txt` as file-backed duplicate
    - Wire `load_run_state` / `save_run_state` into `stop_hook.py` replacing current file-only reads
    - _Requirements: 11.1_

- [ ] 32. SLSA provenance — `actions/attest-build-provenance`
  - [ ] 32.1 Create `.github/workflows/release.yml`
    - Trigger on `push` to `main` (or tag)
    - After build: call `actions/attest-build-provenance@v1` to sign artifact
    - Document `gh attestation verify` command in `docs/slsa-verification.md`
    - _Requirements: 17.3_

- [ ] 32a. `state_integrity.py` — Resumed-State Hash Checker (REQ-STATE-005)
  - [ ] 32a.1 Implement `tools/state_integrity.py`
    - On `SessionStart`, read current `feature_list.json` + `claude-progress.txt` and compute SHA-256 hash
    - Compare against `state_hash` stored in `run_state` Postgres table (or `claude-progress.txt` if DB unavailable)
    - If mismatch: exit 2 with message "Session resume blocked: state hash mismatch. Run operator reconciliation." (fail closed)
    - If match or first session: compute and store hash; proceed
    - Wire into `session_start_hook.py` by calling `state_integrity.check()` before context injection
    - _Requirements: 23.1_

  - [ ]* 32a.2 Write property test for resumed-state integrity (Property 26)
    - **Property 26: Resumed-State Integrity**
    - **Validates: Requirements 23.1** — Z3 CHECK-11a/11b
    - Generate (session_state_hash, durable_store_hash) pairs; assert `runProceeds=False` whenever hashes differ; assert `runProceeds=True` only when they match
    - `# Feature: spec-to-evidence-control, Property 26: Resumed-State Integrity`

- [ ] 32b. `audit_log.py` + `audit_verify.py` — Hash-Chained Gate-Decision Audit Log (REQ-AUDIT-001..003)
  - [ ] 32b.1 Implement `tools/audit_log.py`
    - Implement `append_gate_decision(event_name, tool_name, decision, reason, requirement_id, actor_agent)`: read last row's `entry_hash` from `gate_audit_log`; compute `entry_hash = sha256(canonical_json || prev_hash)`; insert row
    - First row: `prev_hash = sha256("genesis")`
    - Wire into all five hooks: each hook's decision return path calls `audit_log.append_gate_decision()` before returning
    - _Requirements: 27.1_

  - [ ] 32b.2 Implement `tools/audit_verify.py`
    - Implement `verify_chain(start_seq=1) -> VerifyResult`: read all rows ordered by `seq`; recompute each `entry_hash` from `(canonical_json(row), prev_row.entry_hash)`; return list of broken links
    - Trigger: run on every `SessionStart` (informational, non-blocking) and as a required CI check at merge (blocking on any broken link)
    - _Requirements: 27.2, 27.3_

  - [ ]* 32b.3 Write property test for audit log tamper detection (Property 28)
    - **Property 28: Audit-Log Tamper Detection**
    - **Validates: Requirements 27.1, 27.2**
    - Generate audit log sequences; mutate one entry's fields; assert `verify_chain()` fails with the mutated seq in broken links; assert unmodified chains always verify
    - `# Feature: spec-to-evidence-control, Property 28: Audit-Log Tamper Detection`

- [ ] 32c. Checklist-Approval Gate in PreToolUse Hook (REQ-SPEC-016 — items 9 and 5)
  - [ ] 32c.1 Add `check_checklist_approval(event)` to `pre_tool_use_hook.py`
    - Triggered when the Initializer agent attempts to use a domain-baseline checklist for discovery (tool call targeting `baselines/` read with discovery intent)
    - Read `domain_baseline_checklists` table; check `approved_at IS NOT NULL` for the checklist version being used
    - If `approved_at IS NULL` (DRAFT): exit 2 with "PreToolUse blocked: checklist is DRAFT. Present for human review before use."
    - Chain this as a fifth check function after existing four checks in `pre_tool_use_hook.py`
    - _Requirements: 24.1_

  - [ ]* 32c.2 Write property test for checklist-approval-before-use (Property 27)
    - **Property 27: Checklist-Approval Before Use**
    - **Validates: Requirements 24.1** — Z3 CHECK-12a/12b
    - Generate (checklist_state: DRAFT|APPROVED, usage_attempted: bool) pairs; assert discovery is blocked whenever checklist is DRAFT; assert it is allowed only when APPROVED
    - `# Feature: spec-to-evidence-control, Property 27: Checklist-Approval Before Use`

- [ ] 33. Phase 2 durable-state integration test
  - [ ] 33.1 Write `tests/integration/test_phase2_integration.py`
    - Against a test Neon branch: run all 8 migrations (001–008); assert all tables exist with correct columns and constraints
    - Insert a requirement record; insert a coverage item with `status='unproven'`; assert `evidence_complete` CHECK rejects an `evidence_records` row with empty `output_hash`
    - Insert a complete evidence record; assert it is retrievable by `requirement_id` and `commit_sha` with all four fields intact
    - Write a commit message containing a requirement ID; run `parse_commit_trailers`; assert the ID is returned
    - Write a commit message with no requirement ID; run `assert_commit_has_req_id`; assert `TraceabilityError` is raised
    - Call `load_run_state` with the DB unavailable; assert fallback reads from `claude-progress.txt` without raising
    - _Requirements: 6.1, 6.2, 6.3, 11.1, 16.1, 16.2, 16.3_

---

### Phase 3 — Observability

- [ ] 34. OTel setup and OTLP exporter configuration
  - [ ] 34.1 Write `tools/telemetry.py`
    - Configure `CLAUDE_CODE_ENABLE_TELEMETRY=1` and `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` in `.env.example` and CI workflow env
    - Implement `init_tracer(service_name: str)`: create `TracerProvider` with `OTLPSpanExporter` reading `OTLP_ENDPOINT` from environment; set export interval DEFAULT ≤5 seconds
    - Implement `get_tracer() -> Tracer`: return named tracer for `spec-to-evidence-control`
    - Pin OTel SDK version in `requirements.txt`
    - _Requirements: 12.1, 12.2_

  - [ ]* 34.2 Write unit tests for OTel setup
    - Test: `init_tracer` with missing `OTLP_ENDPOINT` → raises `ConfigError`
    - Test: tracer emits spans to mock OTLP exporter; assert export interval ≤5 seconds
    - _Requirements: 12.2_

- [ ] 35. W3C Baggage `BaggageSpanProcessor` for `requirement.id` propagation
  - [ ] 35.1 Implement `BaggageSpanProcessor` in `tools/telemetry.py`
    - Write `RequirementBaggageProcessor(SpanProcessor)`: on `on_start`, read active `requirement.id` from context; set `baggage.set_baggage("requirement.id", req_id)` on span; assert `requirement.id` is non-empty for any span with an active requirement
    - Register processor in `init_tracer()`
    - _Requirements: 6.4, 12.4_

  - [ ]* 35.2 Write property test for W3C Baggage requirement ID propagation
    - **Property 12: W3C Baggage Requirement ID Propagation**
    - **Validates: Requirements 6.4, 12.4**
    - Generate arbitrary spans under an active requirement context; assert every span's Baggage contains `requirement.id` with non-empty value; assert no requirement-processing span is emitted without this entry
    - `# Feature: spec-to-evidence-control, Property 12: W3C Baggage Requirement ID Propagation`

- [ ] 36. Hook decision event forwarding to OTLP
  - [ ] 36.1 Extend all five hooks to emit OTel gate-decision events
    - In each hook's decision return path, call `telemetry.get_tracer().start_as_current_span("hook.decision")` and set attributes: `hook.event`, `tool.name`, `decision` (allow/block), `reason`, `requirement.id`
    - Emit via the same OTLP endpoint as agent spans
    - _Requirements: 12.3_

- [ ] 37. Langfuse backend connection
  - [ ] 37.1 Configure Langfuse as the default OTLP backend
    - Set `OTLP_ENDPOINT` in `tools/telemetry.py` to read from environment variable `OTLP_ENDPOINT` (no hardcoded URLs)
    - Add `OTLP_ENDPOINT=https://cloud.langfuse.com/api/public/otel/v1/traces` as a commented example in `.env.example`
    - Add `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` to `.env.example` as required Langfuse auth variables
    - Write a `docs/observability-backends.md` file listing: Langfuse (MIT core, recommended default), SigNoz (MIT Expat core), Arize Phoenix (Elastic License 2.0 — source-available, NOT OSI, no hosted-service offering permitted) with the specific license note so backend choice is compliance-aware
    - _Requirements: 12.2, 12.5_

  - [ ]* 37.2 Write integration test for OTel export
    - Stand up a local OTLP collector (e.g., `opentelemetry-collector` via Docker); point `OTLP_ENDPOINT` at it
    - Call `init_tracer()` and emit one span with `requirement.id` Baggage; assert the collector receives the span and the Baggage attribute is present
    - _Requirements: 12.1, 12.4_

- [ ] 38. Phase 3 observability integration test
  - [ ] 38.1 Write `tests/integration/test_phase3_integration.py`
    - Call `init_tracer("spec-to-evidence-control")`; start a span under a mock `requirement.id` context; assert `RequirementBaggageProcessor` sets `requirement.id` on the span's Baggage
    - Simulate a `Stop` hook gate-decision (block); assert the hook emits a span with attributes `hook.event=Stop`, `decision=block`, `requirement.id` matching the active requirement
    - Assert that two gate evaluations with identical `feature_list.json` state but different mock prediction values produce the same span `decision` attribute value
    - Assert all hook spans are exported to the same OTLP endpoint as agent spans (verify via shared `TracerProvider`)
    - _Requirements: 12.3, 12.4, 13.6_

---

### Phase 4 — Property-Based Tests (Full Suite)

- [ ] 39. Complete PBT suite — all 29 correctness properties
  - [ ] 39.1 Write `tests/property/test_coverage_model.py`
    - Property 1: Coverage Item Schema Invariant (`test_coverage_item_schema_invariant`)
    - Property 2: Evidence Schema Enforcement (`test_evidence_schema_enforcement`)
    - Property 3: Identity-Mutation Blockade (`test_identity_mutation_blockade`)
    - Property 4: Completion Gate — Prediction Independence (`test_completion_gate_prediction_independence`)
    - Each test: `@settings(max_examples=100)`, tag comment `# Feature: spec-to-evidence-control, Property N: <text>`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 10.1, 13.6, 19.2_

  - [ ]* 39.2 Write property test for completion gate prediction independence
    - **Property 4: Completion Gate — Prediction Independence**
    - **Validates: Requirements 10.1, 13.6, 19.2**
    - Generate pairs of `(coverage_state, prediction_A, prediction_B)` where `prediction_A ≠ prediction_B` but coverage state is identical; assert gate decision is identical for both; assert no prediction variable appears in gate logic
    - `# Feature: spec-to-evidence-control, Property 4: Completion Gate — Prediction Independence`

  - [ ] 39.3 Write `tests/property/test_hooks.py`
    - Property 5: Stop Hook — Unproven Blocks Termination (`test_stop_hook_unproven_blocks`)
    - Property 6: Plan Approval Gate (`test_plan_approval_gate`)
    - Property 7: Scope Sequencing Gate (`test_scope_sequencing_gate`)
    - Property 8: No-Progress → HANDOFF Only (`test_no_progress_handoff`)
    - Property 9: Cap and Budget → HANDOFF Only (`test_cap_budget_handoff`)
    - Property 21: Hook Exit-Code Contract (`test_hook_exit_code_contract`)
    - _Requirements: 5.5, 7.4, 7.5, 10.2, 13.5, 14.1, 14.2, 18.1_

  - [ ]* 39.4 Write property test for hook exit-code contract
    - **Property 21: Hook Exit-Code Contract**
    - **Validates: Requirements 13.5**
    - Generate hook invocation scenarios with exit codes 0, 1, 2, and arbitrary non-zero; assert exit 0 → tool proceeds; exit 2 → tool blocked + stderr fed to agent; exit 1 → NOT blocked; other non-zero → non-blocking
    - `# Feature: spec-to-evidence-control, Property 21: Hook Exit-Code Contract`

  - [ ] 39.5 Write `tests/property/test_spec_validator.py`
    - Property 14: Spec Validator Returns Structured Output (`test_spec_validator_structured_output`)
    - Property 15: Spec-Completion Convergence Gate (`test_spec_completion_convergence`)
    - Property 16: EARS Pattern Assignment Uniqueness (`test_ears_pattern_uniqueness`)
    - Property 17: Vague-Adjective Rejection (`test_vague_adjective_rejection`)
    - _Requirements: 1.2, 1.4, 4.1, 4.3_

  - [ ]* 39.6 Write property test for spec-completion convergence gate
    - **Property 15: Spec-Completion Convergence Gate**
    - **Validates: Requirements 4.3**
    - Generate sequences of `violation_count` values across consecutive passes; assert system routes to HANDOFF whenever count does not strictly decrease between any two consecutive passes; assert continuation only on strict decrease
    - `# Feature: spec-to-evidence-control, Property 15: Spec-Completion Convergence Gate`

  - [ ] 39.7 Write `tests/property/test_traceability.py`
    - Property 10: Commit Trailer Requirement ID (`test_commit_trailer_req_id`)
    - Property 11: Orphan Detection (`test_orphan_detection`)
    - Property 12: W3C Baggage Requirement ID Propagation (`test_w3c_baggage_propagation`)
    - Property 13: UNMAPPED Blocks Advancement (`test_unmapped_blocks_advancement`)
    - Property 18: Checklist Version Link Fidelity (`test_checklist_version_link_fidelity`)
    - _Requirements: 2.2, 3.3, 6.2, 6.3, 6.4, 12.4_

  - [ ]* 39.8 Write property test for UNMAPPED blocks advancement
    - **Property 13: UNMAPPED Blocks Advancement**
    - **Validates: Requirements 2.2**
    - Generate domain-baseline checklist states with arbitrary items marked UNMAPPED; assert implementation-phase advancement is blocked whenever any item is UNMAPPED; assert unblocking requires the item to be covered by a mapped requirement
    - `# Feature: spec-to-evidence-control, Property 13: UNMAPPED Blocks Advancement`

  - [ ]* 39.9 Write property test for checklist version link fidelity
    - **Property 18: Checklist Version Link Fidelity**
    - **Validates: Requirements 3.3**
    - Generate checklist use events with arbitrary path/version/sha triples; assert the `checklist_ref` recorded in `feature_list.json` matches the actual git blob SHA at time of use; assert any mismatch causes validation failure
    - `# Feature: spec-to-evidence-control, Property 18: Checklist Version Link Fidelity`

  - [ ] 39.10 Write `tests/property/test_evidence.py`
    - Property 2: Evidence Schema Enforcement (if not already covered)
    - Property 19: Evidence Round-Trip (`test_evidence_round_trip`)
    - Property 20: Secret-Free Prompts, Spans, and URLs (`test_secret_free_output`)
    - Property 23: Line Coverage Threshold on Touched Files (`test_line_coverage_threshold`)
    - Property 24: Subagent Role Separation (`test_subagent_role_separation`)
    - _Requirements: 5.3, 5.6, 9.2, 9.6, 16.2, 17.5_

  - [ ]* 39.11 Write property test for secret-free prompts, spans, and URLs
    - **Property 20: Secret-Free Prompts, Spans, and URLs**
    - **Validates: Requirements 17.5**
    - Generate arbitrary prompt texts, span attribute dicts, and URLs; assert none matching known secret patterns (regex for API keys, tokens, passwords, connection strings) are emitted; assert any matching pattern is rejected before emission
    - `# Feature: spec-to-evidence-control, Property 20: Secret-Free Prompts, Spans, and URLs`

  - [ ]* 39.12 Write property test for line coverage threshold
    - **Property 23: Line Coverage Threshold on Touched Files**
    - **Validates: Requirements 9.6**
    - Generate slice results with arbitrary per-file coverage percentages; assert Verifier marks slice failed and does not emit `proven` status whenever any touched file has coverage < 85%; assert `proven` emitted only when all files ≥ 85%
    - `# Feature: spec-to-evidence-control, Property 23: Line Coverage Threshold on Touched Files`

  - [ ]* 39.13 Write property test for subagent role separation
    - **Property 24: Subagent Role Separation (Implementer Cannot Self-Verify)**
    - **Validates: Requirements 9.2**
    - Generate evidence chains with arbitrary `acting_agent` identities; assert any Evidence_Record where `acting_agent == "implementer.md"` is rejected; assert only evidence from `verifier.md` is accepted
    - `# Feature: spec-to-evidence-control, Property 24: Subagent Role Separation`

  - [ ] 39.14 Write `tests/property/test_completion_gate.py`
    - Property 4: Completion Gate — Prediction Independence
    - Property 5: Stop Hook — Unproven Blocks Termination
    - Property 22: OPA Zero-Evidence Policy at Merge
    - _Requirements: 10.1, 10.2, 10.3, 13.6, 19.2_

  - [ ] 39.15 Write `tests/property/test_amendment_and_integrity.py` — Properties 25–27
    - Property 25: Amendment Monotonicity (`test_amendment_monotonicity`) — amended-not-reproven requirement cannot be COMPLETE; Z3 CHECK-10a/10b
    - Property 26: Resumed-State Integrity (`test_resumed_state_integrity`) — hash mismatch blocks proceed; Z3 CHECK-11a/11b
    - Property 27: Checklist-Approval Before Use (`test_checklist_approval_before_use`) — DRAFT checklist cannot be used; Z3 CHECK-12a/12b
    - _Requirements: 22.1, 23.1, 24.1_

  - [ ]* 39.16 Write property test for research-claim authority labeling (Property 29)
    - **Property 29: Research-Claim Authority Labeling + Fact-Check**
    - **Validates: Requirements 24.2**
    - Generate Research_Sub_Agent output drafts with arbitrary claim lists; assert every external claim has a non-empty `source_url`; assert every source has a non-empty `authority_tier` from {primary, standard, peer-reviewed, blog, vendor, social}; assert any claim with only blog/vendor/social tier sources is flagged for human review
    - `# Feature: spec-to-evidence-control, Property 29: Research-Claim Authority Labeling`

- [ ] 40. Integrate `formal_verification_merged.py` as required CI check (Phase 4 hardening)
  - [ ] 40.1 Update `.github/workflows/formal-verification.yml`
    - Add `hypothesis` PBT run step: `python -m pytest tests/property/ -v`
    - Gate PR merge on this workflow in the GitHub repository ruleset
    - _Requirements: 4.1_

- [ ] 41. PBT CI workflow — run on every PR
  - [ ] 41.1 Create `.github/workflows/property-tests.yml`
    - Trigger on every `pull_request`
    - Install all test dependencies; run `python -m pytest tests/property/ --hypothesis-seed=0 -v`
    - Upload `hypothesis/` database as artifact for reproducibility
    - Register as required status check in GitHub repository ruleset
    - _Requirements: 4.1, 9.1_

- [ ] 42. Final PBT CI run and gate registration
  - [ ] 42.1 Run the full property-based test suite locally and fix any failures
    - Execute `python -m pytest tests/property/ --hypothesis-seed=0 -v` and resolve any property failures
    - For each failing property: identify the invariant violation, trace it to the relevant requirement, fix the implementation (not the test)
    - Confirm all 24 properties pass with `--hypothesis-seed=0` (deterministic seed for CI reproducibility)
    - _Requirements: 1.2, 1.4, 2.2, 3.3, 4.1, 4.3, 5.1, 5.2, 5.3, 5.5, 5.6, 6.2, 6.3, 6.4, 7.4, 7.5, 8.1, 9.2, 9.6, 10.1, 10.2, 10.3, 13.5, 13.6, 14.1, 14.2, 16.2, 17.5, 19.2_

---

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The hard phasing constraint is absolute: every Phase 0 task (1–17) must be complete before any Phase 1 task (18–26) begins
- Each task references specific requirements for traceability
- All hook implementations must use `"type": "command"` — never HTTP or MCP — to ensure fail-closed behavior
- The `stop_hook_active` reentrancy guard is critical to prevent cascade blocking; implement it in task 5 before testing
- Postgres is the durable source of truth (Phase 2), but all Phase 0–1 gates must work correctly with file-only fallback
- Property tests use `hypothesis` with `@settings(max_examples=100)` and the tag comment `# Feature: spec-to-evidence-control, Property N: <text>`
- The 24 correctness properties in Phase 4 are seeded throughout earlier phases (2, 3, 4, 5, 6, 8, 11) — the Phase 4 task consolidates and completes the full suite

---

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1"]
    },
    {
      "id": 1,
      "tasks": ["1.1", "2.1", "12.1"]
    },
    {
      "id": 2,
      "tasks": ["2.2", "2.3", "3.1", "12.2"]
    },
    {
      "id": 3,
      "tasks": ["3.2", "3.3", "4.1"]
    },
    {
      "id": 4,
      "tasks": ["4.2", "4.3", "4.4", "4.5", "5.1"]
    },
    {
      "id": 5,
      "tasks": ["5.2", "5.3", "5.4", "5.5", "6.1"]
    },
    {
      "id": 6,
      "tasks": ["6.2", "6.3", "6.4", "6.5", "7.1"]
    },
    {
      "id": 7,
      "tasks": ["7.2", "8.1"]
    },
    {
      "id": 8,
      "tasks": ["8.2", "9.1"]
    },
    {
      "id": 9,
      "tasks": ["9.2", "10.1", "10.2", "10.3", "10.4", "11.1"]
    },
    {
      "id": 10,
      "tasks": ["11.2", "13.1"]
    },
    {
      "id": 11,
      "tasks": ["13.2", "14.1", "15.1"]
    },
    {
      "id": 12,
      "tasks": ["14.2", "16.1"]
    },
    {
      "id": 13,
      "tasks": ["17.1"]
    },
    {
      "id": 14,
      "tasks": ["18.1", "19.1", "20.1"]
    },
    {
      "id": 15,
      "tasks": ["18.2", "19.2", "20.2", "21.1"]
    },
    {
      "id": 16,
      "tasks": ["21.2", "21.3", "22.1", "23.1", "24.1"]
    },
    {
      "id": 17,
      "tasks": ["25.1"]
    },
    {
      "id": 18,
      "tasks": ["25.2", "26.1"]
    },
    {
      "id": 19,
      "tasks": ["27.1"]
    },
    {
      "id": 20,
      "tasks": ["28.1", "28.2", "28.3", "28.4", "28.5", "28.6"]
    },
    {
      "id": 21,
      "tasks": ["28.7", "29.1"]
    },
    {
      "id": 22,
      "tasks": ["29.2", "30.1"]
    },
    {
      "id": 23,
      "tasks": ["30.2", "31.1"]
    },
    {
      "id": 24,
      "tasks": ["32.1"]
    },
    {
      "id": 25,
      "tasks": ["33.1"]
    },
    {
      "id": 26,
      "tasks": ["34.1"]
    },
    {
      "id": 27,
      "tasks": ["34.2", "35.1"]
    },
    {
      "id": 28,
      "tasks": ["35.2", "36.1"]
    },
    {
      "id": 29,
      "tasks": ["37.1", "37.2"]
    },
    {
      "id": 30,
      "tasks": ["38.1"]
    },
    {
      "id": 31,
      "tasks": ["39.1", "39.3", "39.5", "39.7", "39.10", "39.14"]
    },
    {
      "id": 32,
      "tasks": ["39.2", "39.4", "39.6", "39.8", "39.9", "39.11", "39.12", "39.13"]
    },
    {
      "id": 33,
      "tasks": ["40.1"]
    },
    {
      "id": 34,
      "tasks": ["41.1"]
    },
    {
      "id": 35,
      "tasks": ["42.1"]
    }
  ]
}
```

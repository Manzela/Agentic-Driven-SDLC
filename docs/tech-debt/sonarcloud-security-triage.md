# SonarCloud security triage (2026-06-24)

When the SonarCloud project was made **public** (to fix the failing `main` analysis), the
whole repo became analyzed — and `sonar.exclusions=tools/**` in `sonar-project.properties`
is **inert under Automatic Analysis** (the scanner only reads that file in *CI-based*
scanning). So `tools/` is fully analyzed, and SonarCloud reported **Security Rating E** from
**16 vulnerabilities** — mostly its new "agentic/LLM" rules (S8707/S2083 path-traversal,
S8705 shell-escape, S6680 loop-bounds) firing on control-plane CLIs.

A 6-investigator triage traced each finding's taint source. Outcome: **2 genuinely real**
(fixed), **4 false positives**, **10 low-impact-internal**.

## Fixed — the 2 genuinely real (PR #43)

| Finding | Why real | Fix |
|---|---|---|
| `tools/prove_trivial_slice.py:88` (S2083 BLOCKER) | the verifier prover wrote `status:proven` + an Evidence_Record to `Path(fl_path)` where `fl_path = sys.argv[2]` — a crafted argv could stamp the proven verdict the governance model trusts onto any file outside the repo | `_confine_to_root` (os.path.realpath + startswith-ROOT) on the write (:88) + the reads (:45, :83); traversal raises → fail-closed |
| `.github/workflows/secrets-scan.yml:48` (S7637) | `gitleaks/gitleaks-action@v2` — a mutable tag on a third-party action running with `GITHUB_TOKEN` + `security-events:write` | pinned to commit SHA `ff98106e4c7b2bc287b24eaf42907196329070c7` |

## False positives (4) — SonarCloud over-attributed taint

| Finding | Why it is NOT a vuln |
|---|---|
| `tools/run_state_driver.py:30` (S8707) | path is `Path(root) / "run_state.json"` — the basename is a **module constant**; `session_id` is written as record *content*, never a path segment; `root` is a trusted run dir |
| `tools/run_state_driver.py:68` (S2083 **BLOCKER**) | same path object as :30 — no user-controlled data flows into the path; the BLOCKER rating is over-attribution to the `root`/`session_id` params |
| `plane-integration/dispatcher.py:149` (S2083 **BLOCKER**) | `STATE = HERE / ".dispatcher_state.json"`, `HERE = Path(__file__).resolve().parent` — a **constant path**, zero user-controlled components |
| `tools/run_spine_canary.py:469` (S8705 **BLOCKER**) | `subprocess.run([...], shell=False)` — an **argv list**, no shell to escape; the only string arg is a **constant prompt** literal; gated behind the explicit `--live` flag |

## Low-impact-internal (10) — real pattern, not attacker-reachable in production

Read-only CLI reads in operator/internal tools with **no production untrusted caller** (each
is reached only via its own `__main__`/`sys.argv`, run by the trusted operator or CI; the
binding gates import the pure core in-process, never through argv):
`tools/prove_trivial_slice.py:45/:83` (✓ also fixed by the `_confine_to_root` above),
`tools/model_fingerprint.py:40` (read-only hash, defaults to a constant),
`tools/coverage_gate.py:260` (CLI parity shell — the CI merge gate imports `deny_merge`,
never this argv path), `tools/audit_verify.py:417`, `tools/deepeval_gate.py:329`,
`tools/kill_switch.py:211` (production input is a constant; argv override is `# pragma: no
cover` smoke). All fail closed on a bad path already.

Two non-`tools/` items:
- `plane-integration/agent_consumer.py:83` (S6680 CRITICAL) — **not** an unbounded-DoS: the
  loop iterates `range(offset, len(lines))` over lines **already read into memory**, so it
  cannot iterate more than the file has lines; the queue is appended only after a fail-closed
  **HMAC-SHA256** check (`webhook_handler`). Residual is memory pressure on an unbounded queue
  — optional hardening: cap the per-drain batch via `execution_bounds`.
- `pyproject.toml` (S8565, missing lock file) — the repo has **no** `[build-system]` /
  uv/poetry/pipenv project; installs are `pip -r requirements*.txt` with **exact `==` pins**.
  Not applicable as written. Optional: `pip-compile --generate-hashes` for transitive+hash
  integrity. Do **not** add a uv.lock/poetry.lock that doesn't match the build system.

## Disposition (to restore Security Rating A)

1. **Merge PR #43** — the 2 real fixes (removes the BLOCKER write-sink + the action pin).
2. **Make the `tools/**` exclusion effective** in SonarCloud (the documented controlled-debt
   intent) — **SonarCloud → Project → Administration → Analysis Scope → Source File
   Exclusions = `tools/**`** (or `api/settings/set?key=sonar.exclusions&value=tools/**`).
   Clears the ~12 `tools/` findings (the cog-complexity Maintainability ones too).
3. **Mark the 3 non-`tools/` items resolved** in the SonarCloud UI, citing this ledger:
   `dispatcher.py:149` → **False Positive**; `agent_consumer.py:83` → **Won't Fix / Accept**;
   `pyproject.toml` S8565 → **Won't Fix / Accept**.

Trade-off acknowledged: excluding `tools/**` also drops *security* analysis on the control
plane. The 2 real findings there are fixed; the rest are read-only operator tools with no
untrusted production caller. Re-evaluate when the `tools/**` exclusion's documented EXPIRY
(once `tools/` matures) is reached.

# GitHub Ruleset — `main` branch protection (the enforced Completion Gate)

This documents the **non-bypassable completion gate** the Spec-to-Evidence Control System
specifies (REQ-GATE-001..005, Requirement 10), as realized by GitHub branch protection on
`main`. The gate is **enforced**, not advisory: a PR can only merge to `main` when every
required status check below is green. This is the deterministic, fail-closed enforcement
layer — no self-report is accepted; the CI verdicts are the gate.

## Required status checks on `main` (live)

| Required check (context) | Workflow | Requirement it enforces |
|---|---|---|
| `Z3 formal-verification harness (34/34)` | `.github/workflows/ci.yml` | The 34 machine-checked invariants (completion/HANDOFF/exit-code) must hold |
| `Property + spine test suite` | `.github/workflows/ci.yml` | The Hypothesis property suite + spine unit tests (Properties 1–32) |
| `Zero-evidence coverage gate (block merge on un-proven coverage)` | `.github/workflows/coverage-gate.yml` | REQ-GATE-002 / Property 22 — no merge while any in-scope item is un-proven |
| `gitleaks secrets diff-scan (block merge on detected secret)` | `.github/workflows/secrets-scan.yml` | REQ-17.2 / Property 32 — secret in the diff blocks merge |
| `zap-baseline` | `.github/workflows/zap-baseline.yml` | REQ-SEC-008 — OWASP ZAP baseline DAST |

All checks are owned by GitHub Actions (`app_id 15368`).

## Current configuration

```json
{
  "required_status_checks": { "strict": false, "contexts": [ /* the 5 above */ ] },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
```

- `strict: false` — a PR need not be up to date with `main` before merging (avoids
  forced re-runs on every intervening merge).
- `enforce_admins: false` — admins may bypass in an emergency (e.g. to repair a broken
  required check). Set **`true`** for the fully non-bypassable gate REQ-GATE-005 intends.
- `required_pull_request_reviews: null` — no human review is *required* by the rule, which
  keeps autonomous merges unblocked. To enforce **REQ-18** (human-in-the-loop plan/PR
  approval), set e.g. `{ "required_approving_review_count": 1 }`.

## Strengthening to the full spec posture

```bash
gh api -X PUT repos/Manzela/Agentic-Driven-SDLC/branches/main/protection --input - <<'JSON'
{ "required_status_checks": { "strict": true, "contexts": [
    "Z3 formal-verification harness (34/34)", "Property + spine test suite",
    "Zero-evidence coverage gate (block merge on un-proven coverage)",
    "gitleaks secrets diff-scan (block merge on detected secret)", "zap-baseline" ] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 1 },
  "restrictions": null }
JSON
```

This makes the gate non-bypassable (`enforce_admins: true`), requires a human reviewer
(REQ-18), and requires branches to be current (`strict: true`).

## Single source of truth

The canonical required-checks list lives in `tasks.md` (the merge-gate enumeration). This
doc and the live ruleset MUST mirror it; if a check is added/renamed, update all three
(workflow job name → this table → the branch-protection `contexts`).

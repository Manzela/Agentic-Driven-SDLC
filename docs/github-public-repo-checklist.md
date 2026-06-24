# Public-repo hygiene checklist (post-PRIVATE→PUBLIC)

`Manzela/Agentic-Driven-SDLC` was flipped PRIVATE → PUBLIC (to get free CodeQL + SonarCloud).
This is the standing acceptance oracle and remediation ledger for that flip.

**Acceptance oracle:** *no real secret in the committed tree AND no over-broad gitleaks mask
AND no live infra fingerprint in tracked files.* Verified clean-by-absence by
`tests/integration/test_public_repo_hygiene.py` (gitleaks over tracked files = 0; redaction
landed; the one documented deferral is contained).

## 1. Code hygiene — LANDED (PR #31, merged)

- [x] VM origin IP redacted → `${{ secrets.VM_HOST }}` in the 4 deploy workflows
      (`deploy-plane.yml`, `deploy-tunnel.yml`, `deploy-plane-oci.yml`, `go-live.yml`).
      `VM_HOST` is set as a repo **secret**. (Test: `test_vm_host_redaction_landed`,
      `test_no_raw_public_ipv4_literal_in_workflows`.)
- [x] Project UUID / CF account id / owner UUID / workspace slug removed as code defaults in
      `plane-integration/*.py` + `tools/plane_config_audit.py` → `YOUR_*` placeholders.
- [x] `.gitleaks.toml` over-broad `docs/*.md` blanket removed; replaced with precise
      value/path allowlists + `regexTarget="match"`.
- [x] Git history verified clean of live secrets; the gitleaks hits were all FPs
      (Plane upstream-default creds, content-hash `dedup_key`s, author-redacted example
      tokens, and a doc-illustration `SECRET_KEY=a411f976…` that is **absent from every
      config** — not live).
- [x] gitleaks over **tracked** files = 0 (the only working-tree findings are untracked,
      gitignored `apps/web/.next/**` build-cache artifacts). (Test:
      `test_gitleaks_clean_on_tracked_files`.)

## 2. Remaining data artifacts — DEFERRED (documented, contained)

- [ ] Project UUID still present in 2 tracked data dumps:
      `audit/plane-xref/board-snapshot.json`, `audit/plane-xref/board-snapshot-1748.json`.
      These are historical board exports, not config. The deferral is **contained** — no
      other tracked file carries a bare UUID (Test:
      `test_deferred_board_snapshot_deferral_is_contained`). To close: redact the UUID in
      those two dumps or drop them from history.
- [ ] DNS-discoverable hostname `plane.autonomous-agent.dev` — public via DNS regardless;
      mitigated operationally (see §4), not a code-tree fingerprint.

## 3. CI / branch-protection preconditions — CROSS-TASK

- The Phase-1 SAST/traceability gates (`sast-codeql`, `sast-semgrep`, `traceability-gate`)
  are built (Task 15) but **not yet registered** as required checks; SonarCloud's exact
  context name must be read off a live run. Registration is **Task 18 (owner action)** —
  see `docs/github-ruleset.md`.
- CodeQL/Sonar are same-repo-only (a fork's read-only token can't write SARIF/use the
  SONAR_TOKEN); **Semgrep (OSS, no secrets) is the binding SAST check on fork PRs.**

## 4. OWNER ACTIONS — not autonomously resolvable (HANDOFF)

These require infrastructure access or a human attestation and are **out of the agent's
scope**:

- [ ] **Lock OCI security-list ingress to Cloudflare IP ranges.** Now that the origin VM IP
      was briefly public (a Cloudflare-Access-bypass recon vector), the real mitigation is to
      restrict the OCI security list so the origin only accepts traffic from Cloudflare's
      published IPv4/IPv6 ranges. (The IP redaction in §1 reduces discoverability but is not
      the mitigation.)
- [ ] **Confirm the `a411f976…` doc `SECRET_KEY` was never a live deployed value.** It appears
      only as a documentation illustration and is absent from every config; confirm it was
      never deployed, and if it ever was, rotate it.

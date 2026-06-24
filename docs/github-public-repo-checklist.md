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

- [x] **All 4 Phase-1 gates REGISTERED as required checks on `main`** (2026-06-24, via the
      narrow `PATCH .../branches/main/protection/required_status_checks` sub-resource so the
      existing 5 Phase-0 contexts + the PR-review/force-push/deletion posture were preserved):
      `sast-codeql`, `sast-semgrep`, `traceability-gate`, and **`SonarCloud Code Analysis`**
      (verbatim, app `sonarqubecloud`) — each verified against a live green run. `main` now
      requires **9 contexts**; `enforce_admins=false`, `strict=false`,
      `required_approving_review_count=1` unchanged.
- [x] **SonarCloud `main`-analysis ROOT CAUSE found + fixed.** The failure was NOT a branch
      config issue — the Compute-Engine log read *"…reach the maximum allowed lines limit
      (having 59,303 lines)"*: the SonarCloud project was **private** while the GitHub repo is
      public, so it counted against the free-tier private LOC cap (~50k) and the ~59k-line repo
      was rejected on every full scan, while diff-only PR scans passed (the exact private/public
      tell). Fixed by setting the SonarCloud project **public** (matches the public repo — no new
      code exposure; public projects are free + unlimited LOC). The baseline seeds on the next
      `main` scan (this merge).
- CodeQL/Sonar are same-repo-only (a fork's read-only token can't write SARIF/use the
  SONAR_TOKEN); **Semgrep (OSS, no secrets) is the binding SAST check on fork PRs.** Once
  required, fork PRs cannot satisfy the same-repo-only checks — acceptable for the current
  same-repo autonomous flow, a constraint only if external fork PRs are ever expected.

### Baselines (CodeQL / SonarCloud)

- [x] **CodeQL `main` baseline SEEDED** (automatic). The push-to-`main` trigger from the #32/#33
      merges produced 2 successful default-branch analyses (`code-scanning/analyses?ref=refs/heads/main`
      → ids @ `2a84fda`, `238eb97`, **0 alerts**, 43 rules, category `codeql-python`). GitHub
      default CodeQL setup is `not-configured` → no conflict with the advanced workflow. Nothing
      to do; a green default-branch analysis IS the New-Code baseline.
- [ ] **SonarCloud `main` baseline NOT seeded — owner action (see §4).** Every `main`-push
      analysis fails, so no successful baseline snapshot exists behind `sonar.newCode.referenceBranch=main`.

## 4. OWNER ACTIONS — not autonomously resolvable (HANDOFF)

These require infrastructure access or a human attestation and are **out of the agent's
scope**:

- [ ] **Lock OCI security-list ingress to Cloudflare IP ranges.** Now that the origin VM IP
      was briefly public (a Cloudflare-Access-bypass recon vector), restrict the OCI security
      list / NSG so the origin no longer accepts arbitrary inbound. **Genuinely owner-only:** no
      OCI IaC exists in-repo (zero `.tf`/terraform/security-list files — `deploy-plane-oci.yml`
      uses the instance Run-Command service only and relies on "the default route/security list";
      `PLANE_EDGE_DEPLOY.md:60` "set in the OCI Console — can't be done from CI"), the `oci` CLI
      is not installed, and no security-list/NSG OCID is recorded anywhere. Stronger-than-literal
      recommendation: the origin is a **Cloudflare Tunnel** (cloudflared dials *out*; "no inbound
      ports needed" — `PLANE_EDGE_DEPLOY.md:11,212-213`), so the best posture is **deny-all inbound
      except an SSH management CIDR** (keep that SSH rule or you lock yourself out — the tunnel is
      outbound-only and won't save an SSH lockout). As defense-in-depth (only needed if a service
      is ever a classic proxied origin, not a tunnel), allow TCP/443 from the **live Cloudflare
      CIDRs** (fetched 2026-06-24, etag `38f79d05…`; refresh against `api.cloudflare.com/client/v4/ips`):
      - IPv4: `173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22 141.101.64.0/18 108.162.192.0/18 190.93.240.0/20 188.114.96.0/20 197.234.240.0/22 198.41.128.0/17 162.158.0.0/15 104.16.0.0/13 104.24.0.0/14 172.64.0.0/13 131.0.72.0/22`
      - IPv6: `2400:cb00::/32 2606:4700::/32 2803:f800::/32 2405:b500::/32 2405:8100::/32 2a06:98c0::/29 2c0f:f248::/32`
      Verify: from a non-CF host `curl -m5 https://<origin-ip>` should time out; the app stays
      reachable only via the edge hostname. Durability: capture as `oci_core_security_list`
      Terraform in-repo so future audits diff it. **Runnable helper:**
      `plane-selfhost/oci-lock-ingress.sh` — dry-runs by default (set `SSH_MGMT_CIDR` +
      `INSTANCE_OCID`, review, then re-run with `APPLY=1`); backs up the current rules first
      and refuses to run without `SSH_MGMT_CIDR` (SSH-lockout guard).
- [x] **FIXED — SonarCloud `main`-branch analysis.** Diagnosed via the Compute-Engine API
      (`api/ce/activity?status=FAILED`): the failure was the **free-tier private LOC cap**, not a
      branch/New-Code misconfig — the project was private while the repo is public. Resolved by
      setting the SonarCloud project **public**; the `main` baseline seeds on the next scan and
      the `SonarCloud Code Analysis` required check is registered (§3). (`sonar-project.properties`
      is inert under Automatic Analysis — its `sonar.projectKey` uses a slash while SonarCloud's
      real key is the underscore form `Manzela_Agentic-Driven-SDLC`; cosmetic, left as-is.)
- [x] **CONFIRMED never live — the `a411f976…` doc `SECRET_KEY`.** Forensic verdict
      (`git rev-list --all` blob-grep of the full 64-hex value across all 241 commits / 41 refs):
      it appears in **exactly one path, ever** — `docs/plane/PLANE_BLUEPRINT.md` — as a captioned
      "fixed sample" inside an illustrative `plane.env` ini block; **no runtime config references
      it.** Live stacks use a different key (`docker-compose.yml` default `60gp0…`;
      `standalone-deploy.sh:297` generates `openssl rand -hex 32` per deploy; `plane.env.template`
      is a placeholder), and the real `plane.env`/`credentials.env` are **gitignored and never
      tracked**. Already scrubbed from the working tree by PR #31 (`1f860e2`); `grep -c a411f976
      docs/plane/PLANE_BLUEPRINT.md` = 0. **No rotation required.** Two residual owner notes (both
      optional): (a) the sample remains in *git history* of a now-public repo — a `filter-repo`
      purge is possible but disproportionate for a never-live sample; (b) the repo cannot prove a
      negative about the *untracked* live `plane.env` — if you cannot personally attest the literal
      was never hand-pasted onto the VM, a one-time SECRET_KEY rotation is a cheap precaution.

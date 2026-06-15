# Lens 3 — False-Negative Meta-Audit (working notes)

Grounding complete: read PART B (189 reqs + 151 design + 201 tasks), PART C (64 findings / 5 lenses),
PART D (D1-D7), PART E (deltas), PART F (Phase-0), and corpus PRD/requirements.md.

## What the original 5 lenses already cover (do NOT re-report)
- coverage-traceability: HOME dangling deps, shared-concern owners, /writing, Get-notified, global ID gate
- contradictions: contrast, font-weight, claims-count (21/21 vs 32/32), error-red token, legal routes,
  section IDs, GetNotified, OG/ISR, motion registry, reduced-motion scope, budgets, trailing-slash,
  hosting, coverage %, gate-verdict copy, loop-state enum
- ambiguity: claims-registry, accent hex, IA-02 EARS order, "legible/satisfying", INP-via-TBT,
  provisional budgets, axe critical/serious, motion semantic check, CLS vocab, Flesch, hash-chain,
  calm/skeleton, title length, CI-duration, EARS tags, legal routes
- missing-components: legal pages, favicon/manifest, CSP connect-src/report-to, notify PII event +
  sub-processor register + retention/DSR(prose), RSS/IA, reduced-data + browser matrix, print +
  forced-colors, uptime/synthetic + content-governance, already-subscribed, 410 lifecycle, i18n,
  motion kill-switch, security.txt/llms.txt/AI-crawler, OG variants
- tier1-standards: claims-count, motion ownership, decorative-loop detection, accent density,
  mono-inverse, frame-sampled red, stat-bar substitute, accent hex lock, error-red taxonomy
- D6 already adds: web-manifest, CSP allowlist, print, reduced-data+browser-matrix, motion kill-switch,
  /writing 301/410, i18n, security.txt + AI-crawler, route OG images, post-deploy uptime + periodic
  re-verify, PII-free notify event + sub-processor register

## NEW findings (under-covered SDLC vectors) — see StructuredOutput
NF-1 Legal/IP: no permission/trademark/attribution policy to NAME Tier-1 tools (LOOP-17/CONTENT-18) — P1
NF-2 License compliance of self-hosted deps (Geist OFL, JetBrains/Berkeley mono, Rive runtime, OG fonts) + NOTICE/SBOM — P1
NF-3 Stale proof number: corpus says 34/34 (req.md L9, PRD L4/130/133) but site D3/F8/§7 commit 32/32; corpus itself 32-vs-34 inconsistent — P0
NF-4 No SBOM / supply-chain provenance (SLSA) for the SITE's own build — product mandates it, site does not eat its dog food — P1
NF-5 No dependency pinning / lockfile-integrity / SRI for FIRST-PARTY bundles + build reproducibility — P1
NF-6 No site observability/RUM-error/alerting/incident runbook (RUM is perf-only PERF-15; no error telemetry SLO/alert) — P1
NF-7 No DR/backup/restore for captured emails + content repo; rollback is deploy-only (TOOL-13), no RPO/RTO — P2
NF-8 Data retention + DSAR are prose-only (PRIV-09); no enforced retention window / deletion path / erasure verification — P1
NF-9 Testing depth: no contract test for /api/notify, no E2E user-journey, no load/rate-limit test, no cross-browser/device matrix execution, no visual-a11y (contrast-in-render) — P1
NF-10 Analytics event schema undefined (no enumerated event taxonomy / property allowlist / PII-free schema gate) — P2
NF-11 Spec's own claims not all independently verifiable: "100% traceability", "2.2M tokens", "17-agent", Lighthouse>=95 self-published (PERF-13 ok) — claims-integrity applied to marketing copy ABOUT the build — P2
NF-12 No threat model / abuse-case catalog for the one write surface (/api/notify) beyond rate-limit+honeypot; no secrets-management/rotation policy for processor API keys — P2
NF-13 No accessibility-statement page / VPAT posture (regulated audience expects it); A11Y-13 forbids the number but no qualitative statement route — P3
NF-14 No content-integrity/SRI-equivalent for the .riv & evidence fixtures at runtime (TOOL-03 build-hash only; no runtime tamper check on the proof artifact the brand sells) — P3

# Design — autonomous-agent.dev (flagship website)

> **Scope:** Design decisions for the **public marketing/manifesto website** at `autonomous-agent.dev`.
> This is **NOT** the product design. The product's own design lives under
> [`.kiro/specs/spec-to-evidence-control/design.md`](../../../.kiro/specs/spec-to-evidence-control/design.md).

**Materialized:** 2026-06-15 from `docs/plans/based-on-the-attached-eventual-cat.md` (PART B §B.2),
with PART D/E/G corrections applied.

**Totals:** 167 design decisions. Each is ID'd (`D-<PREFIX>-NN`) and traced to the requirement IDs it serves.

**Single sources of truth (D2):** design tokens & contrast → DS; motion-intent registry → DS-08
(`lib/motion/registry.ts`); route + section manifest → IA (`lib/routes.ts`); gate-verdict copy →
CONTENT-13; Get-notified endpoint/state & `__pref` store → PRIV; claims → one
`content/claims-registry.json`. Owners declare; everyone else imports.

**Domain index:** DS · IA · HOME · LOOP · CONTENT · PAGE · TECH · TOOL · PERF · A11Y · SEO · PRIV

---

## Brand & Design System — DS

### D-DS-01 — Layered token architecture  (→ DS-01, DS-06, DS-07, DS-08, DS-10)
Adopt a three-tier token architecture: base scales → semantic tokens → primitives. Base palettes/scales are never consumed directly; UI binds only to semantic tokens, which primitives compose. DS is the single owner of the color, contrast, spacing, radius, elevation, and motion tokens. This isolates value changes to one tier and makes "every surface resolves from a named token" enforceable.

### D-DS-02 — Single source of truth: DESIGN.md + Style Dictionary  (→ DS-10, DS-01, DS-15)
DESIGN.md is the human contract; Style Dictionary JSON is the machine source. Both build deterministically into CSS custom properties and the Tailwind v4 `@theme`. A drift check compares committed generated output against a fresh build and fails CI on mismatch. DS owns tokens + contrast as the canonical source; no other domain may declare color/spacing/motion values.

### D-DS-03 — AA-corrected accent and contrast pairing matrix  (→ DS-02, DS-06)
Treat the contrast matrix as a tested artifact owned by DS. Locked values: --proven #34E1A0 on --canvas #0A0B0D ≈12.5:1 (AA pass); --text-faint #5A606B is decorative/disabled ONLY and is excluded from the AA text matrix; a canonical --error token is defined with AA ≥3:1 and reserved for real errors only. Each pairing's measured ratio is asserted in unit tests and via axe-core; a failing pair blocks launch.

### D-DS-04 — Self-hosted, subset, metric-matched font pipeline  (→ DS-04, DS-03, DS-05, DS-15)
Self-host Geist Sans (Inter Variable fallback) and Geist Mono as subset, preloaded WOFF2, served same-origin with zero third-party requests. Each `@font-face` uses `font-display: swap` plus a metric-matched fallback (`size-adjust`/`ascent-override`) so font-swap CLS is negligible. Display weights are capped at 300–600.

### D-DS-05 — Fluid modular type scale with role tokens  (→ DS-03, DS-18)
Define a modular scale exposed as role tokens (display, heading, body, label, caption) with fluid `clamp()` sizing, body resolving to 17–19px, tight negative tracking (-1.5px to -2px) on display roles, and consistent line-heights per role. Components reference roles, never raw sizes.

### D-DS-06 — Machine-artifact rendering layer  (→ DS-05, DS-12, DS-16)
Provide `<Mono>`/`<Artifact>` primitives plus an MDX component map so requirement IDs, evidence records, hashes, gate verdicts, code, and trace spans always render in Geist Mono / JetBrains Mono with tabular numerals on `[data-artifact]` nodes. Mono is permitted ONLY on `[data-artifact]` nodes; the MDX map routes artifact content through these primitives so prose can never borrow the mono face.

### D-DS-07 — Motion-as-information system  (→ DS-08, DS-09, DS-15)
Define motion tokens (durations, easings, named state semantics) in a single motion registry owned by DS-08. Every animation declares a `data-motion-intent` mapping to a registry entry; a runtime motion-integrity assertion rejects unmapped motion. Rive drives the hero loop; Framer Motion drives micro-interactions. Both honor the registry and the reduced-motion contract.

### D-DS-08 — prefers-reduced-motion static fallbacks  (→ DS-09, DS-17, DS-18)
Under `prefers-reduced-motion: reduce`, disable non-essential motion and render state-preserving static equivalents: the closed loop becomes a labeled static diagram, coverage shows its final filled state, and the gate shows its held verdict. Fallbacks are first-class, not afterthoughts, so reduced-motion users receive identical information.

### D-DS-09 — Component primitive library with a11y coverage  (→ DS-11, DS-13, DS-18)
Build the sanctioned primitives (soft-action buttons, cards/panels, status badges, navigation) with full default/hover/active/focus-visible/disabled states, keyboard operability, visible focus, non-color state cues, and correct semantic roles/landmarks/labels to WCAG 2.2 AA (target size, focus-not-obscured). These are the only building blocks for site UI.

### D-DS-10 — Code/trace/evidence block primitive  (→ DS-12, DS-05, DS-16)
A dedicated block primitive on `--surface-2` renders monospaced, line/column-aligned content with an optional requirement-ID gutter, hash-chain affordance, and accessible copy/scroll. When fed an evidence record or gate verdict it surfaces test_file, test_name, output_hash, collected_at, and verdict as labeled `[data-artifact]` data — and enforces the claims-integrity contract (no static quantified counts).

### D-DS-11 — Spacing, radius, elevation, container tokens  (→ DS-07, DS-18)
Editorial rhythm derives from a base-grid spacing scale plus radius, elevation/shadow, hairline-border, and container-width tokens (max ~1200–1280px). A no-raw-literal lint blocks spacing/radius values authored outside the token source, keeping layout geometry centralized and responsive-safe.

### D-DS-12 — Logo/wordmark and minimal iconography  (→ DS-14, DS-06, DS-04)
Define the 'Autonomous Agent' wordmark, the 'Autonomous SDLC Platform' descriptor lockup, color-on-dark/monochrome/single-accent variants with sizing and clear-space, and a single token-driven line-icon family. An exclusion rule blocks any icon implying an unverifiable claim or a decorative AI-glow. Accent appears in logo variants only where it denotes a verification signal.

### D-DS-13 — Claims-integrity guardrail at the component contract  (→ DS-16, DS-12, DS-08)
Enforce claims integrity in the component contract itself: badge/counter/hero-stat/verdict-chip components reject hardcoded quantified verification figures and require either qualitative copy or a harness-bound source (value + run-hash + collected_at). A CI check applies the value-agnostic denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` against rendered DOM and source. Claims live in a single `content/claims-registry.json`.

### D-DS-14 — Loading / empty / error / asset-fallback as token treatments  (→ DS-17, DS-09, DS-01)
Loading, empty, error, and asset-failure states are first-class token treatments: calm skeletons on `--surface`/`--surface-2`, no alarm-red decoration, and graceful degradation to static token-styled equivalents when Rive/font/trace assets fail. The canonical `--error` token is reserved for real errors only and never used for cosmetic fallback.

### D-DS-15 — Performance budgets and CWV protection  (→ DS-15, DS-04, DS-08, DS-10)
Document and CI-enforce budgets for the token + font + motion layer (LCP < 2.5s, CLS < 0.1, INP < 200ms on a mid-tier profile). Critical CSS is inlined, fonts preloaded and subset, and the hero animation is loaded so it neither blocks the main thread nor shifts layout. Budget regressions fail the build.

### D-DS-16 — Responsive system  (→ DS-18, DS-03, DS-07, DS-11)
Define breakpoints with fluid type, adaptive containers/spacing, an accessible collapsible navigation, and a hero/trace that degrades to a clean labeled diagram on small screens — guaranteeing no horizontal overflow from 320px upward. Composed entirely from the type, spacing, and primitive tokens above.

### D-DS-17 — Icon/manifest bundle generated from tokens  (→ DS-19, DS-14, DS-01)
Generate the full icon/manifest bundle from brand tokens using App-Router icon/manifest file conventions: an `icon`/`favicon` source produces favicon.ico and the 32px icon; an `apple-icon` (180px, opaque background) and 192/512 plus a maskable variant are emitted; a `manifest` route sets `theme_color` to `#0A0B0D` (from `--canvas`). Two `<meta name="theme-color">` tags cover light and dark schemes, and the document background is painted `--canvas` before first content so there is no white-flash. The single source for these values is the DS token set (no literals duplicated in the manifest).

---

## Information Architecture & Navigation — IA

### D-IA-01 — Single-source route + section manifest in lib/routes.ts  (→ IA-01, IA-03, IA-06, IA-07, IA-11, IA-12, IA-16)
This domain OWNS lib/routes.ts as the single source of truth for the route and section manifest. Content routes ({/, /how-it-works, /proof, /manifesto, /writing, /docs} plus legal /privacy, /terms) and major-section anchor ids are declared once here; nav, breadcrumbs, sitemap, and metadata all derive from this typed table rather than redeclaring paths, eliminating drift.

### D-IA-02 — No-funnel navigation model and content denylist lint  (→ IA-03, IA-12)
The nav/footer render only from the allowed-destination list; a CI content lint scans chrome markup against a denylist of funnel affordances (pricing/demo/contact-sales/sign-in/buy) and against the value-agnostic claims regex \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b. This keeps the manifesto tone enforceable rather than convention-based.

### D-IA-03 — Persistent sticky header with responsive disclosure + scroll state machine  (→ IA-04, IA-05, IA-14)
One header instance persists across SSG/ISR navigations. A breakpoint switch toggles inline destinations vs a focus-trapped disclosure panel; a small scroll state machine condenses the bar using a registered DS-08 motion token as a discrete informational state change, never a decorative loop.

### D-IA-04 — Anchor/section navigation with focus management and scroll-margin  (→ IA-06, IA-13)
Section ids and scroll-margin come from the manifest; activating an anchor updates the fragment and moves focus to the heading. Motion respects prefers-reduced-motion via the DS-09 reduced-motion contract, falling back to an instant jump.

### D-IA-05 — Breadcrumbs for nested routes with BreadcrumbList JSON-LD  (→ IA-07, IA-13, IA-16)
Nested routes (/writing/<slug>) render a breadcrumb derived from the manifest hierarchy, with the trailing crumb non-interactive and aria-current="page", plus BreadcrumbList JSON-LD for share/SEO; home renders none.

### D-IA-06 — Branded 404 and 500 routes via App Router boundaries  (→ IA-08, IA-09, IA-13)
not-found and global-error boundaries render branded pages that keep global nav, expose recovery links to canonical destinations, and scrub all stack traces, env detail, and internal identifiers from the 500 surface. Correct 404/500 HTTP status codes are asserted.

### D-IA-07 — Canonical-origin redirect layer (apex/www/http + alias table)  (→ IA-02, IA-10, IA-11)
A middleware redirect layer enforces the single https apex origin and URL hygiene (casing, trailing/duplicate slash → 308) and maps www/http/legacy aliases via a declared, version-controlled redirect table whose targets are validated against real manifest routes.

### D-IA-08 — Programmatic sitemap.xml + robots.txt with stub/error exclusion  (→ IA-11, IA-15, IA-16)
sitemap.xml is generated from the manifest's indexable content routes only; stub, error, and utility routes are excluded and marked noindex. robots.txt references the sitemap. Utility endpoints (sitemap.xml, robots.txt, rss/feed, OG-image, /.well-known/security.txt, web-manifest) are registered separately from content routes.

### D-IA-09 — Claims-integrity guardrail enforced in IA chrome  (→ IA-12, IA-16)
Header, footer, and metadata templates pull gate-verdict/trust copy from CONTENT-13 and any claim values from the single content/claims-registry.json (owned via CONTENT-06); a build-time check rejects any hardcoded "N/N verified" count using the denylist regex.

### D-IA-10 — Route/section accessibility and navigation-feedback contract  (→ IA-13, IA-04, IA-06, IA-14)
Every page emits banner/main/navigation/contentinfo landmarks and a visible-on-focus skip link as first focusable element; route-change completion moves focus to main/heading. An axe gate requires zero critical OR serious violations.

### D-IA-11 — Stub/empty-state strategy driven by content presence  (→ IA-15, IA-01)
Stub vs populated rendering is driven by content-presence flags from the manifest/content layer: empty /docs or /writing render an intent-stating stub with global nav and Get notified, never fabricated content or availability claims.

### D-IA-12 — Per-route metadata + social-share template  (→ IA-16, IA-02, IA-11)
A metadata template derives unique title/description/canonical/OG/Twitter per route from the manifest and page content, with self-referential canonical URLs and the claims denylist applied to all metadata values.

### D-IA-13 — Content-lifecycle redirect map for unpublished slugs  (→ IA-17)
Unpublishing a /writing slug writes a lifecycle entry to the version-controlled redirect table (301→/writing or 410), and the slug is excluded from sitemap and feed generation by the same content-presence logic that powers stub states — keeping discovery surfaces consistent with publication state.

### D-IA-14 — lib/routes.ts legal entries (/privacy, /terms)  (→ IA-18)
The manifest carries /privacy and /terms as indexable, inNav:false, isLegal:true entries co-owned by IA and PRIV; they are crawlable (in sitemap, no noindex) yet excluded from primary nav and from the exact-content-route equality test, while footer legal links resolve to them.

---

## Homepage Scrollytelling Narrative — HOME

### D-HOME-01 — Section-as-beat architecture with a single ordered scrollytelling driver  (→ HOME-02, HOME-10, HOME-12)
Model the page as eight ordered `section` beats whose ids and ordinals are imported from the IA-owned route/section manifest (IA-12) rather than re-declared, so deep-links, in-page nav, and analytics share one source of truth. A single ScrollNarrative driver owns active-beat and progress state; sections subscribe rather than each running their own scroll listener. Rationale: one driver yields deterministic active-beat resolution, avoids competing listeners, and makes the reduced-motion/static path a matter of the driver emitting resolved states.

### D-HOME-02 — Shared ClosedLoop centerpiece with a single state contract  (→ HOME-01, HOME-05, HOME-10, HOME-14)
Build one ClosedLoop component consuming a `stage` prop (intent, decompose, implement, verify, prove, gate) and a `mode` (motion | reduced | static). Both the Hero and Closed-loop-explained beats render the same component so the loop never forks visually. The static SVG labeled diagram is the default render and the permanent fallback; the animated layer mounts on top only when the asset loads. Rationale: a single state contract guarantees HOME-01's fallback and HOME-05's stage progression stay consistent and lets HOME-10/HOME-14 force resolved states without component-specific branches.

### D-HOME-03 — Fail-closed gate rendered as a satisfying accent-positive state, never alarm-red  (→ HOME-05, HOME-14)
The gate-holds-the-line beat glows the single reserved accent (--proven #34E1A0 on --canvas #0A0B0D, ≈12.5:1 contrast) and dims the unproven item to --text-faint (decorative/disabled-only). The canonical --error token is explicitly excluded from the gate verdict in all states. Gate-verdict copy is imported from CONTENT-13. Rationale: framing rejection as the feature requires the rejection to read as system-correct, not as an alarm; centralizing the copy and forbidding --error here keeps the brand claim honest and testable.

### D-HOME-04 — Fragmented-stack consolidation as a deterministic scroll-bound state machine  (→ HOME-03, HOME-14, HOME-15)
The ProblemGrid maps scroll progress to a finite set of discrete consolidation steps via a pure progress->state function (no time or randomness), so any progress value reproduces an identical state and reverse-scroll replays steps in reverse. Each step carries a `data-motion-state` from the DS-08 registry and the component exposes `data-motion-integrity` for the runtime assertion. Rationale: determinism is what makes HOME-15's robustness and HOME-14's no-decoration rule objectively checkable, and clean pin-release prevents CLS.

### D-HOME-05 — Replace-table and The-leap as scroll-revealed micro-interactions over a static baseline  (→ HOME-04, HOME-07, HOME-10, HOME-14)
Author both beats as fully-formed static DOM first (a real two-column table for the six role->substitute pairs; two lists for removes/guarantees), then layer scroll-tied reveal/recede/resolve purely as presentation. Row and list copy come from the content layer (CONTENT-06). Receded state uses muted/--text-faint, resolved uses --proven/--accent. Rationale: building static-first satisfies HOME-10's "no content trapped in animation" by construction and keeps accent usage within the ≤3–5% budget.

### D-HOME-06 — Proof beat: live monospaced evidence record with pending->proven animation and a claims-integrity firewall  (→ HOME-06, HOME-13)
The EvidenceTrace renders the four-field schema (test_file, test_name, output_hash, collected_at) inside `[data-artifact]` nodes — the only nodes permitted to use monospace — and the record is explicitly labeled illustrative sample data. A shared claims firewall runs the value-agnostic denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` over all homepage copy and metadata at build/test time; all claims resolve through content/claims-registry.json (CONTENT-06). Illumination to accent fires only when all four fields are present. Rationale: confines mono to artifacts, prevents any hardcoded "N/N verified" count from shipping, and ties proof visuals to real completeness.

### D-HOME-07 — Reduced-motion and resolved-state-by-default strategy  (→ HOME-10, HOME-12, HOME-14)
The motion registry (DS-08) is the single switch: under prefers-reduced-motion the ScrollNarrative driver disables pinning/scrubbing and emits each beat's final resolved state, so consolidation result, gate-holds, proven illumination, and all table rows render resolved by default. No content path depends on an in-between frame. Rationale: centralizing the reduced-motion decision in the driver/registry makes the final-state assertions uniform across beats and prevents per-component drift.

### D-HOME-08 — Responsive scrollytelling: pin on desktop, stacked reveals on touch/mobile  (→ HOME-11, HOME-03, HOME-05)
Above the DS-defined desktop breakpoint, scroll-bound beats pin and scrub; below it (or on touch-primary devices) they switch to stacked in-view reveals, the loop scales to a labeled diagram, and multi-column beats reflow to single column. Touch handlers never preventDefault native scroll/momentum and never induce horizontal overflow. Rationale: keeps the narrative legible and native-feeling on mobile while reusing the same content and state contracts, with the breakpoint owned by DS.

### D-HOME-09 — Performance & loading: SSR/ISR copy first, lazy per-section motion, reserved layout boxes  (→ HOME-12, HOME-01, HOME-13, HOME-15)
Serve the full narrative copy and static fallbacks as static/ISR HTML; mount per-section state machines and motion assets lazily on viewport approach via IntersectionObserver. Every deferred visual element gets reserved dimensions (aspect-ratio/min-height) so arrival yields CLS ≤ 0.1. Deferred-asset failure degrades that section to static without blocking siblings or surfacing raw errors. Rationale: static-first guarantees crawlability (HOME-13) and instant readability (HOME-01) while reserved boxes and lazy mounts protect CWV and the scroll budget (HOME-15).

### D-HOME-10 — Scroll-state robustness: deterministic progress->state with debounced settling and fragment resolution  (→ HOME-15, HOME-03, HOME-05)
The driver computes section state as a pure function of clamped scroll progress and exposes `data-motion-integrity` so a runtime assertion can confirm rendered state matches mapped progress under rapid scroll, reversal, and anchor jumps. Fragment navigation into a pinned/scrub range seeks the section to the corresponding progress state with the pin intact. Scroll updates are throttled/debounced (e.g., rAF-coalesced) to stay within the performance budget. Rationale: a single pure mapping plus an integrity probe is what makes "no stuck/skipped/out-of-order" objectively testable.

### D-HOME-11 — Soft-close and notify affordance with full submission-state coverage and no funnel  (→ HOME-09, HOME-08)
The Soft-close offers only soft actions: links to `/manifesto` and `/how-it-works` (routes from IA-03) plus an optional Get-notified control delegated to the PRIV-owned notify component, which renders distinct submitting/success/error/already-subscribed states. No pricing, demo, booking, logo-wall, or sibling-product links appear in Soft-close or Who-its-for. Rationale: ownership of notify by PRIV centralizes consent/state handling, and forbidding funnel elements keeps the manifesto tone and avoids unverifiable customer claims.

### D-HOME-12 — Content layer & claims-integrity governance for all homepage copy  (→ HOME-08, HOME-13, HOME-06, HOME-04, HOME-07)
All homepage strings — beat copy, replace-table rows, leap lists, audience framing, metadata — are sourced from the content layer with claims resolved through content/claims-registry.json (CONTENT-06); HOME components import copy and never inline marketing claims. The claims firewall (denylist regex, evidence-gating of customer/logo claims) runs over rendered output in CI. Rationale: one content/claims source of truth makes the no-aggregate-count and editorial-framing requirements enforceable across every beat at once.

---

## Rive Closed-Loop Centerpiece + Evidence Trace — LOOP

### D-LOOP-01 — Single Rive state machine as the loop's source of truth  (→ LOOP-01, LOOP-02, LOOP-03)
One Rive state machine owns all stage progression, gate behavior, and evidence-proving transitions; named inputs/triggers are the host's only write surface. No CSS-timed or Framer Motion animation touches the loop. Rationale: a single deterministic source makes the three acceptance goals (LOOP-03) testable at captured frames and lets the runtime motion-integrity assertion (D7) prove every animation maps to a state.

### D-LOOP-02 — Canonical loop geometry, ordering, and cadence  (→ LOOP-01, LOOP-11)
Fix the six-node geometry (intent → decompose → implement → verify → prove → gate → origin) with an unambiguous traversal direction and an 8–14s cadence input, defined once and reused across breakpoints. Rationale: a canonical geometry keeps the legibility contract (six labels, distinct positions, AA contrast) stable when the layout reflows for LOOP-11.

### D-LOOP-03 — Live requirement tokens coupled to a deterministic fixture  (→ LOOP-04, LOOP-13)
Requirement tokens are bound to a committed fixture modeled on the real evidence schema; tokens render only on [data-artifact] mono nodes and flip pending → proven from fixture state, never from a computed aggregate. Rationale: deterministic fixture data makes prove transitions reproducible for visual-regression and keeps the centerpiece artifact-driven, not claim-driven.

### D-LOOP-04 — EvidenceTrace panel: tamper-evident, hash-chained, four-field records  (→ LOOP-05, LOOP-12, LOOP-13)
The trace is an append-only DOM list; each record exposes test_file, test_name, output_hash, collected_at as navigable text, and each link references the prior record's hash to form a visible chain. Rationale: rendering records as real DOM text (not canvas) satisfies both the tamper-evident reading and the accessibility requirement in one structure.

### D-LOOP-05 — Lockstep prove-event bus coupling loop to trace  (→ LOOP-04, LOOP-05)
A small event bus emits a prove event when a token completes its evidence record; the trace subscribes and appends in lockstep, lighting the ID and output_hash to --proven. Rationale: a single ordered channel guarantees no record precedes its token and none is dropped, which is the LOOP-05 lockstep AC.

### D-LOOP-06 — Fail-closed gate choreography: satisfying, accent-as-correct, never alarming  (→ LOOP-06, LOOP-07, LOOP-09)
The gate sub-machine runs named beats approach → evaluate → hold/close (accent glow) → settle; held items dim to --text-faint/--pending and the verdict/reason copy is read from CONTENT-13. Accent (--proven) signals a correct hold; alarm-red is barred from the choreography and reserved for genuine runtime errors. Rationale: encoding the rejection as ordered named states with sourced copy makes "satisfying not alarming" assertable (accent at hold-frame, no red across the frame-sequence).

### D-LOOP-07 — Static fallback as the SSR default + error boundary  (→ LOOP-08, LOOP-11, LOOP-12, LOOP-16)
The fully-labeled static diagram (six stages, gate holding, ≥1 proven + ≥1 held token, representative records) is server-rendered as the default; the animated canvas hydrates over it only when motion is permitted and the runtime loads. An error boundary and loading/budget failures collapse back to this same static node. Rationale: making the fallback the default (not a degraded path) guarantees information parity with zero client JS and a single tested surface for reduced-motion, small-screen, and failure cases.

### D-LOOP-08 — One-accent semantic color layer enforced by token + audit test  (→ LOOP-09, LOOP-13)
All color resolves from DS tokens: --proven (#34E1A0 on --canvas #0A0B0D, ≈12.5:1) for verified/correct, --pending for awaiting, --text-faint for held; display weights 300–600. A binding audit test fails on any inline hex, extra saturated hue, or stray alarm-red, and runs the value-agnostic count denylist regex. Rationale: enforcing the palette and the no-headline-number rule in one audit makes the color and claims discipline a build gate, not a convention.

### D-LOOP-09 — Optional synchronized interaction model with auto-resume  (→ LOOP-10, LOOP-12)
Pointer/keyboard focus drives named Rive inputs deterministically and cross-highlights the matching evidence record both ways; a bounded idle timer auto-resumes cinematic playback. Rationale: routing interaction through the same named inputs keeps the deterministic state model intact and reuses the LOOP-12 stage↔record correspondence for highlighting.

### D-LOOP-10 — Performance, visibility-gating, loading/empty states  (→ LOOP-14, LOOP-15, LOOP-16)
Code-split the Rive runtime/asset and load after first paint into a pre-reserved box (CLS = 0); gate playback on IntersectionObserver + Page Visibility; show a calm labeled skeleton (neutral --pending) and an evidence awaiting state while loading, collapsing to the static fallback on budget overrun or failure. Rationale: keeping animation off the critical path and tying playback to visibility meets CWV targets while never leaving an indefinite spinner.

### D-LOOP-11 — Per-state tool layer with reduced-motion static mapping  (→ LOOP-17)
The Rive artboard carries a `tool` layer keyed per state so each stage's named tool surfaces only while that state is active (no concurrent logo parade); the reduced-motion path renders a static node → tool map listing the full stage-to-tool correspondence as DOM text. The static map follows the canonical loop order — intent, decompose, implement, verify, prove, gate (gate last, with no separate Spec node): Intent maps to the human brief; Decompose maps to the Claude Code initializer subagent spinning up git worktrees; Implement maps to the Claude Code implementer subagent wired to the official PreToolUse and PostToolUse hooks; Verify maps to Playwright, Semgrep, CodeQL, Hypothesis, k6, Lighthouse, and axe-core alongside an independent verifier subagent; Prove maps to the four-field Evidence_Record, the hash-chained audit log, and a Z3 logic model; and Gate (last) maps to the Stop hook plus OPA/Conftest policy and the GitHub ruleset. Where Claude Code hooks are named on the Implement and Gate nodes, the static map states the honest limit qualitatively: the official hook roster is emerging and version-gated, hooks fire only on command-type actions and must fail closed, and a PostToolUse hook observes after the fact and cannot undo an action already taken. Temporal, if present in the substrate copy, is labeled an optional orchestration substrate rather than a required node. Rationale: binding tool reveal to state (rather than a static row of logos) makes the mapping verifiable by per-state visual-regression and preserves the motion-bound-to-state discipline, with the static map guaranteeing parity under reduced motion and pinning the canonical six-stage order so the gate always reads last.

---

## Content, Copy & Claims Integrity — CONTENT

### D-CONTENT-01 — Voice Spec as the single content contract  (→ CONTENT-01, CONTENT-02, CONTENT-04, CONTENT-09, CONTENT-13)
Author one machine-readable Voice Spec (voice-spec.json) holding the deny and allow lexicons plus structural rules (no exclamation, no emoji, noun-phrase bullets). Every copy lint imports this one file rather than re-declaring word lists, so the anti-hype contract has a single source of truth and changes propagate to hero, leap bullets, CTAs, and terminology consistently.

### D-CONTENT-02 — Hero headline/subhead candidate matrix  (→ CONTENT-02)
Store ranked headline/subhead candidates in a committed matrix with corpus tags and a length budget. The hero binds to the top-ranked pair; tests assert the rendered strings are members of the matrix and that line-box counts respect 3-lines@360px / 1-line@1024px. Rationale: prevents ad-hoc copy edits and keeps the integrator-and-proof thesis canonical.

### D-CONTENT-03 — ReplaceTable bound to six canonical rows  (→ CONTENT-03)
Drive the 'What it replaces' module from a frozen six-row data file; the component maps rows to JSX and wraps machine-artifact substrings in <Mono data-artifact>. Set-equality test guards against drift. Rationale: the six rows are corpus-load-bearing and must not be silently edited.

### D-CONTENT-04 — TheLeap two-group bullet module  (→ CONTENT-04)
Render eliminations and guarantees from two fixed string arrays; a noun-phrase shape check and a digit scan run in CI. Rationale: keeps the leap quantifier-free and scannable, enforced mechanically not editorially.

### D-CONTENT-05 — Corpus-to-module mapping registry  (→ CONTENT-05, CONTENT-11)
Maintain corpus-map.json keyed by module id -> corpus element id(s), covering 16 domains, 7 gaps, 19 capability blocks (B01-B19), invariant, evidence schema, verifier. A build assertion enforces referential integrity both ways (no orphan element, no dangling citation) and injects non-rendered source annotations. Rationale: makes groundedness auditable.

### D-CONTENT-06 — Claims ledger as single source consumed by every gate  (→ CONTENT-06, CONTENT-12, CONTENT-14, CONTENT-18, CONTENT-19)
content/claims-registry.json is the one claims source every lint gate reads. Each entry: id, claim_text, corpus_citation, verifiability_status, optional harness binding (value + run_hash + collected_at). The Z3 claim is published QUALITATIVELY ("machine-checked formal verification of the requirement-logic model with Z3, self-counting and gating CI — not a proof of the generated code") or bound to live harness output; never a hardcoded N/N. A value-agnostic denylist regex \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b blocks 21/21, 32/32, 34/34, 100/100 equally. Rationale: the count drifted 21->32->34, so no literal tally is trustworthy.

### D-CONTENT-07 — Machine-artifact rendering schema and <Mono> primitives  (→ CONTENT-07, CONTENT-13, CONTENT-15)
Provide a <Mono data-artifact> primitive and an <EvidenceRecord> component exposing exactly test_file, test_name, output_hash, collected_at. The monospace DS token is scoped to [data-artifact] only; a lint asserts mono never bleeds into prose and prose family never appears on artifacts. Rationale: keeps evidence visually distinct from opinion and prevents model self-assessment masquerading as evidence.

### D-CONTENT-08 — Readability budget and inline-glossary enforcement  (→ CONTENT-08, CONTENT-13)
A build-time analyzer computes median sentence length per block and paragraph-sentence counts against numeric thresholds (<=22 words; manifesto <=5 sentences). A glossary registry lists jargon; a first-use scanner requires an inline definition or glossary link per page. Rationale: objective, numeric, page-scoped enforcement instead of subjective readability review.

### D-CONTENT-09 — Soft-CTA allowlist component and microcopy  (→ CONTENT-09, CONTENT-10)
A <SoftCTA> component accepts only allowlisted labels; a route-wide scanner flags any CTA outside the set and any banned funnel term. 'Get notified' microcopy lives in the catalog and defers to the PRIV domain for the notify action. Rationale: structurally impossible to ship a hard-conversion CTA.

### D-CONTENT-10 — Microcopy/state catalog for non-happy paths  (→ CONTENT-10, CONTENT-15)
A states catalog enumerates error/loading/empty/fallback microcopy per interactive component, with pending-state strings drawn from an approved fail-closed framing list. Coverage and Voice Spec lints run in CI. Rationale: edge-state copy is part of the manifesto, not an afterthought.

### D-CONTENT-11 — Manifesto MDX structure with verbatim invariant  (→ CONTENT-11, CONTENT-05)
Author /manifesto as numbered MDX sections (thesis, fragmented stack, human-as-infrastructure, closed loop, proof wedge) with the governing invariant stored as a shared constant and asserted byte-for-byte. §1 also hosts the integrator thesis and the no-lock-in block. Rationale: single canonical invariant string, reused not retyped.

### D-CONTENT-12 — Per-page metadata derived from on-page claims  (→ CONTENT-12)
Generate metadata (title, description, OG/Twitter, JSON-LD) from each page's ledger-registered claims via a build step; lints run the Voice Spec and verification-tally denylist over metadata too. Rationale: closes the off-page claim escape hatch.

### D-CONTENT-13 — Terminology/style sheet and consistency linter; owns gate-verdict copy  (→ CONTENT-13, CONTENT-07)
A terminology.json owns brand usage, casing of governed concepts, machine-artifact token format, AND the canonical gate-verdict copy (CONTENT-13 single source of truth). The canonical gate caption it carries reads "Stop hook holds locally; OPA/Conftest zero-evidence policy at merge; GitHub ruleset makes both required," stated qualitatively with the honest hook limit (command-type, fail closed, version-gated roster; the Stop hold is a local guard that a PostToolUse hook cannot retroactively undo). A consistency linter rejects disallowed synonyms/casing across routes; verdict strings render only from this file. Rationale: prevents category-diluting drift and centralizes verdict wording, pinning the gate caption to the canonical layered phrasing.

### D-CONTENT-14 — Who-it's-for audience module with anti-fabrication rule  (→ CONTENT-14, CONTENT-06)
The module renders audience/role/industry framing from data with a build assertion of zero logo <img>, zero testimonial/named-adopter strings, and any numeric social proof gated through the claims ledger. Rationale: honest positioning without fabricated proof.

### D-CONTENT-15 — Text-equivalent layer for motion and machine artifacts  (→ CONTENT-15, CONTENT-07)
Co-locate caption/summary/alt text with each motion and evidence component; the Rive centerpiece carries the four-state caption, evidence panels carry text summaries, reduced-motion fallbacks carry equivalent captions. Presence lints run per route. Rationale: accessibility and state parity are enforced, not optional.

### D-CONTENT-16 — Fail-closed pre-publish content gate (eat-our-own-dog-food)  (→ CONTENT-16, CONTENT-01, CONTENT-06, CONTENT-08, CONTENT-09, CONTENT-13, CONTENT-15)
Compose all content checks into one CI gate with no override flag; any sub-check failure exits non-zero with page+location reporting. The gate mirrors the product's fail-closed governing invariant. Rationale: the site must demonstrate the same deterministic, override-proof gating it markets.

### D-CONTENT-17 — Integrator-thesis copy deck + displacement denylist  (→ CONTENT-17)
The integrator thesis lives once in the copy deck and is injected into hero and manifesto §1; a displacement-phrase denylist (replaces/kills/better-than competitor patterns) runs alongside the Voice Spec lint. Rationale: keeps the honest "wire proven tools together" position and blocks competitor-displacement slips.

### D-CONTENT-18 — <PoweredBy> module from committed stack manifest  (→ CONTENT-18)
<PoweredBy> reads the committed stack manifest and renders each tool as a mono [data-artifact] entry showing the tool name, its B-block ID, and a one-line pain-point tie; a membership assertion confirms every listed tool exists in the manifest, and DOM/numeric scans confirm no logo <img> and no stat strings. Each entry is backed by a qualitative, citation-backed record in content/claims-registry.json carrying a verifiability_status of design-intent (or, for the Claude Code hooks, emerging/version-gated), with every claim cited to the product spec at .kiro/specs/spec-to-evidence-control/requirements.md and .kiro/specs/spec-to-evidence-control/design.md. The registry covers the official Claude Code hooks; the initializer, implementer, verifier, and research subagents; the git-worktree plus scope-sequencing gate; reasoning-loop detection; requirement-ID propagation via W3C Baggage; the OpenFeature/flagd kill-switch; OWASP ZAP DAST; DeepEval eval-gating; and Hypothesis property tests. Rationale: a claims-integrity-safe substitute for the conventional logo-wall that keeps every Powered-by claim qualitative, grounded in the committed spec, and honest about the hooks' emerging, version-gated status.

### D-CONTENT-19 — No-lock-in block on /how-it-works + manifesto  (→ CONTENT-19)
A shared no-lock-in content block names feature_list.json, EvidenceRecord, and requirement-ID Baggage and states "opinionated defaults, not a cage"; it renders on /how-it-works and in the manifesto, with the claim registered in the claims ledger. Rationale: portability promise is stated once and verifiably grounded.

---

## Supporting Pages — PAGE

### D-PAGE-01 — Shared supporting-page shell  (→ PAGE-01, PAGE-03, PAGE-06, PAGE-10, PAGE-11, PAGE-13)
A single `(site)` route-group layout provides the shared shell: header, soft-action footer, and the single Get-notified capture slot. Centralizing the shell keeps onward navigation, token application, and non-functional budgets uniform across all supporting pages and removes per-page drift. Footer onward-nav links resolve against the IA route manifest rather than hardcoded paths.

### D-PAGE-02 — Six-stage loop explainer and B01-B19 taxonomy  (→ PAGE-01, PAGE-02, PAGE-12)
The /how-it-works page composes a six-stage ordered loop explainer and the 19-block capability taxonomy. Stages and blocks are data-driven from a typed manifest so counts and order are structurally guaranteed (six stages, exactly B01-B19). Block IDs and stage artifacts are the only mono text and carry `[data-artifact]`. Gate-stage framing copy is pulled from CONTENT-13, never inlined.

### D-PAGE-03 — /proof information spine  (→ PAGE-03, PAGE-08)
A fixed four-section spine (invariant → evidence schema → verifier principle → auditor test) renders in deterministic order from an ordered config. The evidence schema lists exactly the four canonical fields on `[data-artifact]` nodes. The verifier-principle section states the independent-verifier principle qualitatively — the agent that proves a change is not the agent that wrote it — and frames the gate via the canonical caption: the Stop hook holds locally, an OPA/Conftest zero-evidence policy holds at merge, and the GitHub ruleset makes both required, with the gate read as the last stage of the loop. No quantitative verification figure is composed here; mechanism is described qualitatively and any claim resolves to the claims registry.

### D-PAGE-04 — EvidenceTrace as accessible state machine  (→ PAGE-04, PAGE-05, PAGE-12, PAGE-15)
The sample audit-trace is an explicit finite state machine (loading/ready/error/static plus per-row unproven → evidence-attached → proven and a terminal gate evaluation). State is held in `data-state` attributes that drive both visuals and assertions. The gate-held visual binds to the `--proven` token (#34E1A0). Keyboard operability, no-JS server-rendered static trace, and reduced-motion parity are first-class branches, not afterthoughts.

### D-PAGE-05 — MDX manifesto with reading aids and allowlist  (→ PAGE-06, PAGE-07, PAGE-14)
The manifesto renders from MDX through a fixed brand-component allowlist (pull-quote, evidence chip, numbered-section heading, blueprint rule); anything outside the allowlist is rejected at build. Numbered headings auto-generate copyable anchors and feed a scroll-derived, non-decorative progress indicator with proper progress semantics. Display headings use weights constrained to 300–600.

### D-PAGE-06 — Optional /writing behind a build-time flag  (→ PAGE-09, PAGE-14, PAGE-16)
The /writing index and articles live behind a build-time feature flag. When enabled and populated, entries sort descending by date with title/date/reading-time; when enabled and empty, a deliberate purpose empty state renders. When disabled, the route is fully absent and its nav entry is removed (handled with the not-found system).

### D-PAGE-07 — /docs honest placeholder  (→ PAGE-10, PAGE-16)
/docs renders an explicit forthcoming-docs placeholder with `noindex`, zero fabricated/dead links, and only the soft Get-notified affordance. This keeps the route honest while reserving the URL.

### D-PAGE-08 — Single claims registry with build-time guard  (→ PAGE-03, PAGE-06, PAGE-08)
All quantitative claims are sourced from one typed `content/claims-registry.json` carrying corpus references — the single source of truth for claims. A build-time guard scans rendered supporting-page text with the value-agnostic denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` and fails the build on any match or on any claim absent from the registry. No "N/N verified" count is ever hardcoded.

### D-PAGE-09 — Motion-as-information system  (→ PAGE-01, PAGE-04, PAGE-07, PAGE-12)
A shared motion system reads its definitions from the single motion registry DS-08; every animation binds to a real `data-state` value (no decorative-only motion). Reduced-motion (DS-09) is enforced globally so state-derived labels persist with zero-duration transitions. No component defines ad-hoc keyframes outside DS-08.

### D-PAGE-10 — Soft conversion: single Get-notified  (→ PAGE-11, PAGE-16)
The site exposes exactly one conversion affordance — a Get-notified email capture — with full loading/success/error/validation state handling and no funnel, pricing, demo, or sales-contact controls anywhere. The component is reused from the shared shell so the single-affordance invariant is structurally enforced.

### D-PAGE-11 — Tier-1 non-functional baseline  (→ PAGE-05, PAGE-12, PAGE-13)
A shared non-functional baseline binds CWV thresholds (LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms), WCAG 2.2 AA (axe zero critical OR serious), responsive snapshots, JSON-LD structured data, and security headers (CSP, X-Content-Type-Options, Referrer-Policy, HSTS). All color/type resolve to DS tokens (DS-01/DS-07) including the canonical `--error` token; `--text-faint` is restricted to decorative/disabled use; fonts are self-hosted same-origin.

### D-PAGE-12 — Branded not-found and link integrity  (→ PAGE-09, PAGE-10, PAGE-16)
A branded 404/error boundary provides soft navigation back to live IA routes, and a build-time internal-link validator fails on dead links and on nav entries for absent feature-flagged routes. This unifies feature-flag absence, dead-link prevention, and graceful error handling.

### D-PAGE-13 — Print stylesheet, token-mapped  (→ PAGE-17)
A dedicated `@media print` stylesheet for /manifesto and /proof maps the dark theme onto a token-driven light print theme (light surface + dark ink tokens meeting AA contrast), expands every `[data-artifact]` hash to its full value (overriding any on-screen truncation), and hides decorative canvas/motion via `display:none`. All print colors come from DS tokens — no print-only hardcoded hex — so the print theme stays in lockstep with the design system.

---

## Tech Stack & Front-end Architecture — TECH

### D-TECH-01 — App Router project shape with route group and colocated segment files  (→ TECH-01, TECH-08, TECH-10, TECH-09)
Use Next.js App Router with one `app/(site)/` route group, a single root `layout.tsx` for shared chrome, and one `page.tsx` per content route. The route set is owned by `lib/routes.ts` (the IA single source of truth) — segments are derived from and validated against it rather than declared ad hoc. Colocating `error.tsx`/`loading.tsx`/`not-found.tsx` per segment makes failure, loading, and empty handling structural rather than optional, which is what lets TECH-09/TECH-10 be enforced by a directory-shape test instead of code review.

### D-TECH-02 — Strict TypeScript with first-class machine-artifact and state-machine contracts  (→ TECH-02, TECH-04, TECH-13)
Enable `strict`, `noUncheckedIndexedAccess`, and `exactOptionalPropertyTypes`, and centralize domain types (`EvidenceRecord`, `RequirementId`, `LoopState` with a `gate` sub-state union, `MdxFrontmatter`) in a single `lib/types` module. Deriving runtime validators (Zod) from the same shapes gives one definition for both compile-time and build-time checks, so MDX frontmatter (TECH-04) and claims data (TECH-13) validate against the exact types the UI consumes. The build runs `tsc --noEmit`, making "any type error fails the build" a literal CI outcome.

### D-TECH-03 — Tailwind v4 themed solely from Style-Dictionary tokens  (→ TECH-03, TECH-06, TECH-14)
Style Dictionary compiles `design/tokens/*.json` (the DS single source of truth) into CSS custom properties; Tailwind v4's `@theme` references only those `var(--…)` values, never literals. The semantic palette (`--canvas`/`--surface`/`--surface-2`/`--border`/`--text`/`--text-muted`/`--text-faint`/`--proven`/`--pending` + canonical `--error`) and the Sans/Mono font tokens are the only color and type surface. Enforcing accent = `--proven` only and mono on `[data-artifact]` at the token layer means brand and artifact-typography rules are checkable statically rather than by inspection.

### D-TECH-04 — Build-time MDX pipeline with allow-listed components and typed frontmatter  (→ TECH-04, TECH-08, TECH-13)
Compile MDX from `content/` at build time with a fixed component allow-list (numbered sections, blueprint rules, pull-quotes, `<EvidenceRecord>`, `<RequirementId>`) and Zod-validated frontmatter. Compiling at build (not request) time keeps content routes SSG/ISR (TECH-08) and lets claim references inside prose resolve against `content/claims-registry.json` (TECH-13) before anything ships. An unlisted component or invalid frontmatter aborts the build with a file-named error.

### D-TECH-05 — Rive integration boundary: lazy, SSR-disabled, intersection-gated, CLS-safe  (→ TECH-05, TECH-06, TECH-07, TECH-09, TECH-15)
Isolate Rive in one `components/loop/ClosedLoop.tsx`, imported via `next/dynamic({ ssr: false })`, gated by an IntersectionObserver near the hero, and mounted in a fixed-aspect reserved container that holds the static labeled diagram until the `.riv` resolves. One boundary is the single place that must satisfy SSR-exclusion (TECH-05), motion-as-state (TECH-06), reduced-motion fallback (TECH-07), error containment (TECH-09), and the scoped `wasm-unsafe-eval` CSP allowance (TECH-15) — concentrating those constraints makes them auditable.

### D-TECH-06 — Motion-as-information contract: Rive vs Framer Motion split with a registry  (→ TECH-06, TECH-07, TECH-16)
Split responsibilities: Rive owns the hero closed-loop state machine and secondary product-state visuals; Framer Motion owns informational micro-interactions only. Every animation references an id in `lib/motion/registry.ts` — the DS-08 motion-intent registry that TECH imports rather than redefines — mapping it to a product-state enum. Anything not in the registry is not animated, which turns "motion must communicate state" into a build-enforceable rule (TECH-16) and a reduced-motion fallback contract (TECH-07).

### D-TECH-07 — Reduced-motion and accessibility fallback strategy  (→ TECH-07, TECH-09, TECH-10, TECH-11, TECH-16)
A shared reduced-motion/theme context drives one fallback strategy across the centerpiece, evidence-trace, and micro-interactions: under `prefers-reduced-motion: reduce` the Rive timeline never autoplays, Framer Motion elements render at their final informational state, and the static labeled diagram (with text equivalents for every machine artifact) is shown. The same static diagram doubles as the small-screen degradation (TECH-11) and the error/loading fallback (TECH-09/TECH-10), so one artifact serves accessibility, responsiveness, and resilience.

### D-TECH-08 — Rendering strategy: SSG by default, ISR for MDX, dynamic forbidden  (→ TECH-08, TECH-10, TECH-16)
Marketing routes are SSG; MDX content routes (`/manifesto`, `/writing`, `/writing/[slug]`) use ISR with a bounded `revalidate`. No segment opts into per-request dynamic rendering. Validating the build manifest against `lib/routes.ts` makes "dynamic is forbidden on marketing routes" a CI gate (TECH-16) rather than a convention, and bounded ISR keeps content fresh without request-time cost.

### D-TECH-09 — Error/loading/empty-state system with segment boundaries  (→ TECH-09, TECH-10, TECH-05)
Every route group gets `error.tsx` and `loading.tsx`; the Rive centerpiece and any client data-dependent region get dedicated React error boundaries rendering the on-brand static fallback styled from `--error`/`--surface`. Skeletons match final dimensions (no shift) and zero-item collections render intentional empty states. Containing failures at the boundary keeps a thrown component or failed `.riv` from crashing the rest of the page, and reuses the TECH-05/TECH-07 static diagram as the fallback.

### D-TECH-10 — Responsive layout and centerpiece degradation across 320px → ultra-wide  (→ TECH-11, TECH-03, TECH-07)
Layout spans a 320px floor to ultra-wide with a ~1200–1280px max content container built on token-driven spacing/type (TECH-03). Below a defined centerpiece breakpoint, the full Rive animation degrades to the simplified labeled diagram (the same TECH-07 fallback), prioritizing stage and artifact legibility over fidelity. Reusing the reduced-motion diagram for small screens avoids a second, divergent low-end rendering path.

### D-TECH-11 — Minimal, intentional state management with audited client boundaries  (→ TECH-12, TECH-02, TECH-01)
Default to server/segment state; introduce `'use client'` only for genuine interactivity (Rive state, scroll progress, reduced-motion/theme, form input), each an allow-listed module. Shared client state uses React context or a minimal documented store — no global app-wide state framework. An allow-list scan over `'use client'` files plus a dependency check makes the minimalism enforceable rather than aspirational, complementing the typed module boundaries from TECH-01/TECH-02.

### D-TECH-12 — Claims-integrity architecture: registry-backed, build-validated  (→ TECH-13, TECH-04, TECH-16)
Every quantitative/verification claim is data in a single `content/claims-registry.json` (the CONTENT-06 claims source), rendered through a `<Claim>` component that resolves a source entry. The build fails on any unresolved claim, and a value-agnostic denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` runs as a CI gate (TECH-16) so no hardcoded "N/N verified" count of any value can ship. Keeping claims out of JSX and behind one registry makes integrity a data-validation problem, not a copy-review problem.

### D-TECH-13 — Self-hosted variable fonts with zero-CLS swap and guaranteed mono artifacts  (→ TECH-14, TECH-03, TECH-15)
Self-host the display/body and mono families via `next/font/local`, exposing CSS-variable tokens the Tailwind theme consumes (TECH-03), with size-adjusted metric-compatible fallbacks and `font-display: swap`, and display weights across 300–600. Self-hosting keeps fonts inside the `'self'` CSP scope (TECH-15) and removes external font requests; mono-metric fallbacks ensure `[data-artifact]` nodes are mono even before the web font loads, holding CLS at ≈ 0.

### D-TECH-14 — Hardened delivery: CSP scoped for Rive WASM + self-hosted fonts  (→ TECH-15, TECH-05, TECH-08, TECH-14)
Emit strict security headers (CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `frame-ancestors 'none'`) via middleware/edge config. The CSP grants `wasm-unsafe-eval` only as needed for Rive WASM (TECH-05) and restricts font/style sources to `'self'` (TECH-14), with no wildcard script/style sources. Because rendering is static/ISR (TECH-08), headers can be applied uniformly at the edge, and the "narrowest sufficient allowance" principle is verifiable by parsing the emitted policy.

### D-TECH-15 — Fail-closed CI verification harness for performance, a11y, and motion integrity  (→ TECH-16, TECH-06, TECH-07, TECH-11, TECH-13)
A required CI harness runs Lighthouse (perf/SEO/best-practices ≥ 95, LCP < 2.5s, CLS ≈ 0, bounded JS bundle), axe-core (zero critical, AA contrast for `--proven`-on-`--canvas` and all text tokens, keyboard operability), a motion-integrity check against `lib/motion/registry.ts`, reduced-motion fallback rendering (TECH-07), responsive checks (TECH-11), and the claims denylist regex (TECH-13). Every gate exits non-zero on failure and blocks merge, so quality budgets are enforced fail-closed rather than monitored.

---

## Tooling, Pipeline & CI/CD — TOOL

### D-TOOL-01 — DS-governed Style Dictionary single-source token pipeline  (→ TOOL-01, TOOL-02, TOOL-10, TOOL-16)
DESIGN.md is the canonical token contract; design/tokens/*.json (owned by DS) is its machine derivation, and Style Dictionary is the only compiler from that source to CSS custom properties, the Tailwind v4 @theme layer, and the typed TS token map. Rationale: a single source of truth (D2) means consumers never hardcode values; determinism makes the token-drift gate trustworthy and lets the DESIGN.md↔source governance check catch silent rot. Canonical --error token and display weights 300–600 are fixed here (D4).

### D-TOOL-02 — Motion/Rive asset governance with mandatory fallback  (→ TOOL-03, TOOL-06, TOOL-07, TOOL-11)
Every .riv is validated against the DS-08 motion registry (state-machine name, inputs, content hash) and loaded lazily off the main thread; a committed static labeled-diagram is the mandatory fallback for prefers-reduced-motion and load failure. Rationale: motion is a single-source registry (D2 motion=DS-08), so animation behavior is verifiable and degrades safely without depending on WebGL.

### D-TOOL-03 — MDX content pipeline with value-agnostic claims-integrity linter  (→ TOOL-04, TOOL-15)
MDX frontmatter is validated against a typed (Zod) schema; a remark claims-integrity linter detects quantitative verification claims via the value-agnostic regex \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b and requires an evidence reference resolvable in content/claims-registry.json (the single claims source, D2). Rationale: NEVER hardcode a verified count (D3/G.1) — the denylist regex catches any fabricated count, decoupling enforcement from the current true value.

### D-TOOL-04 — Deterministic quality gates: lint / format / typecheck / unit+coverage  (→ TOOL-05, TOOL-08, TOOL-16)
ESLint (jsx-a11y, custom no-raw-token + mono-binding rules), Prettier, Stylelint, strict `tsc --noEmit`, and Vitest+Testing Library with a coverage gate and a motion-binding test run as deterministic checks. Rationale: every criterion is objectively checkable (D7); local hooks inform but CI is authoritative so mergeability is decided by reproducible outputs, not self-report.

### D-TOOL-05 — Visual-regression + axe + performance verification layer  (→ TOOL-06, TOOL-07, TOOL-11)
Playwright captures deterministic screenshots of the four named loop states and key routes across breakpoints against committed baselines; axe-core runs on every key route incl. empty/loading/error states; Lighthouse/CWV enforces score and LCP/CLS/INP budgets. Rationale: Rive asset budgets gate; JS/CSS budgets are Phase-0/1 provisional (non-gating until ratified) and CI-duration is a non-gating alert (D7 demotions).

### D-TOOL-06 — Fail-closed CI aggregation gate (the product invariant applied to the site)  (→ TOOL-09, TOOL-05, TOOL-12, TOOL-15)
A single required-status-check aggregation computes mergeability only from verifiable check outputs (tokens-drift, contrast, lint, typecheck, format, unit/coverage, visual, axe, Lighthouse/CWV, MDX/claims, link-check, traceability, security/header); any failure blocks merge and deploy with no manual-green override. Rationale: this mirrors the product's fail-closed verification invariant — no human or model self-report substitutes for a passing check.

### D-TOOL-07 — Traceability CI gate (this domain OWNS referential integrity)  (→ TOOL-09)
A traceability build step constructs the global requirement-ID set across all domains, then fails the build on (a) any task/design "Depends on"/"→" referencing a non-existent requirement ID, (b) any orphan design item mapping to no requirement, and (c) any orphan task mapping to no requirement. Rationale: D1 referential integrity — every dependsOn must resolve to a real requirement ID; placeholder namespaces (TOKENS-*, MOTION-*, PROOF-*, CLAIMS-*, NAV-*) are remapped to canonical IDs and the gate prevents their reintroduction. This gate is a required check inside D-TOOL-06.

### D-TOOL-08 — Deployment + preview environments on the apex domain  (→ TOOL-13, TOOL-14, TOOL-12)
Production builds SSG/ISR and deploys an immutable, content-addressable artifact to autonomous-agent.dev only, with health-gated promotion and atomic rollback; each PR gets an isolated, noindex (optionally auth'd) preview that runs visual/axe/Lighthouse/header checks and is torn down on close. Rationale: apex-only (D5 route set) keeps content off subdomains; immutability + rollback make promotion safe.

### D-TOOL-09 — Security, headers, CSP, supply chain & continuous verification  (→ TOOL-12, TOOL-16, TOOL-13, TOOL-17)
Strict CSP + HSTS/X-Content-Type-Options/Referrer-Policy/frame-ancestors/Permissions-Policy headers are asserted on built/preview artifacts; dependency-vuln and secret scanning gate deploy. External synthetic monitors probe /, /proof, and the OG-image endpoint, a scheduled job re-runs the privacy/security verification, and an incident runbook + immutable rollback cover recovery. The pipeline pins dependencies, runs SCA, and emits an SBOM per release. Rationale: G.5 supply chain — the site's own build mirrors the product's SLSA ethos (pinned deps + SCA + SBOM) and verification continues post-deploy.

---

## Performance — PERF

### D-PERF-01 — Core Web Vitals budget contract, machine-readable and fail-closed  (→ PERF-01, PERF-08, PERF-13)
Define a single versioned JSON budget contract (metric, threshold, gating-flag) as the canonical source for both the CI gate and the published-claim component. CWV thresholds (LCP < 2.5s, CLS < 0.1, INP < 200ms) are gating; JS/CSS budgets are flagged Phase-0/1 PROVISIONAL/non-gating until ratified. INP is sourced from a scripted Playwright interaction, never inferred from TBT, so the contract carries the measurement method per metric.

### D-PERF-02 — Self-hosted, subsetted font pipeline with zero-CLS fallback  (→ PERF-02, PERF-12)
Subset the brand typefaces to the glyph coverage actually used, restrict display weights to 300–600, emit self-hosted WOFF2, and pair each with a metric-matched system fallback so font-display: optional/swap never reflows. Preload only above-the-fold faces. Rationale: removing the third-party font origin and matching metrics is the cheapest path to font-swap CLS < 0.01.

### D-PERF-03 — Rive centerpiece: lazy, off-main-thread, layout-reserved  (→ PERF-03, PERF-09, PERF-14)
Wrap the centerpiece in a component that reserves its exact box via aspect-ratio, defers the Rive runtime + .riv behind an IntersectionObserver, and runs the animation off the main thread where supported. The same wrapper owns the static-poster fallback, so reduced-motion, reduced-data, and load-failure all collapse to one reserved-box code path with CLS ≤ 0.001.

### D-PERF-04 — Image strategy: modern formats, intrinsic dimensions, prioritized LCP  (→ PERF-04, PERF-12, PERF-16)
Serve AVIF/WebP with raster fallback, require intrinsic width/height or aspect-ratio on every image, lazy-load everything below the fold, and grant fetchpriority=high to at most the single LCP image. Rationale: intrinsic dimensions eliminate image-driven CLS; a single prioritized LCP image keeps the critical fetch wave lean.

### D-PERF-05 — Code-splitting and first-load JS budget enforced in CI  (→ PERF-05, PERF-08)
Push Rive, Framer Motion, the proof trace, and MDX-heavy modules behind dynamic imports so they never enter a route's initial bundle, and assert each route's first-load JS against a budget in CI. The JS budget is recorded but PROVISIONAL/non-gating until ratified; only its measurement is mandatory now.

### D-PERF-06 — Token-driven critical CSS with Tailwind v4 purge  (→ PERF-06)
Generate all CSS from the DS token source (tokens = DS, single source of truth) through Tailwind v4 with unused utilities purged, ship a per-route critical CSS slice, and forbid render-blocking third-party stylesheets. Rationale: a single token origin keeps style and design system in lockstep and bounds CSS growth.

### D-PERF-07 — SSG/ISR delivery with immutable asset caching  (→ PERF-07, PERF-12)
Statically generate every content route from the IA route manifest (route manifest = IA, single source of truth), reserve ISR for /writing only, and serve hashed assets with immutable cache headers from the CDN. Rationale: no per-request render on the critical path is the most reliable TTFB win.

### D-PERF-08 — Fail-closed performance gate as evidence-backed CI check  (→ PERF-08, PERF-01, PERF-13)
Run Lighthouse-CI plus the scripted INP Playwright check on every PR, block merge on any CWV breach or sub-95 score, and persist each result as an evidence record (metric, value, threshold, collected_at) that feeds the published-claim component. Budget breaches log but do not block while PROVISIONAL.

### D-PERF-09 — Reduced-motion fast path with no motion runtime downloaded  (→ PERF-09, PERF-03, PERF-11)
Branch at the server/edge on prefers-reduced-motion so the reduced path never emits the Rive runtime/.riv or non-essential Framer Motion code, rendering the static labeled-diagram loop instead. Rationale: deciding before hydration guarantees zero motion-runtime bytes rather than downloading then discarding.

### D-PERF-10 — Third-party script discipline and origin allowlist  (→ PERF-10, PERF-15)
All external and non-critical scripts load defer/async or post-hydration, and a CI check validates loaded origins against an allowlist while recording third-party transfer against a PROVISIONAL budget. Rationale: an allowlist makes unplanned third-party creep a reviewable diff, not a silent regression.

### D-PERF-11 — Compositor-only scroll motion at 60fps  (→ PERF-11, PERF-16)
Restrict scroll-driven animation to transform/opacity, schedule work in rAF gated by IntersectionObserver, and tear down observers when sections leave the viewport. Rationale: compositor-only properties keep the main thread free so scroll interactions stay within the INP budget.

### D-PERF-12 — Resource-priority waterfall  (→ PERF-12, PERF-02, PERF-04)
Author explicit hints: preconnect/dns-prefetch for required origins, preload for above-the-fold fonts and the LCP resource, and lazy/dynamic deprioritization for the Rive runtime, below-the-fold images, and non-critical scripts. Rationale: an intentional first request wave is what turns the other budgets into a fast LCP.

### D-PERF-13 — Self-referential claims integrity for published performance numbers  (→ PERF-13, PERF-08)
Render every published performance number through a PerfClaim component that reads a stored CI evidence record and shows monospaced value + threshold + collected_at, falling back to "pending" when no current record exists. Rationale: binding visible claims to CI evidence makes the manifesto's self-claims auditable.

### D-PERF-14 — Graceful loading / empty / error / slow-network states  (→ PERF-14, PERF-03, PERF-05)
Give every deferred asset (Rive, images, dynamic chunks) a reserved-space fallback — poster, skeleton, or graceful omission — and swallow load errors without console storms or main-thread blocking. Rationale: reserved-box fallbacks keep CLS ≤ 0.001 and the page usable under failure.

### D-PERF-15 — Privacy-respecting field RUM with lab-vs-field reconciliation  (→ PERF-15, PERF-01)
Ship a lightweight PII-free RUM beacon that reports LCP/CLS/INP/TTFB attributed to a route from the IA manifest, batched to minimize its own cost, and reconcile field percentiles against lab gate results. Rationale: field data catches device/network regressions the lab profile cannot reproduce.

### D-PERF-16 — Responsive asset and layout-stability strategy across breakpoints  (→ PERF-16, PERF-01, PERF-04)
Drive responsive sources via srcset/sizes and media/container queries so mobile never fetches desktop-only heavy media, and design breakpoint transitions to avoid reflow. Rationale: gating heavy media by viewport protects the mobile field profile that PERF-01 measures.

### D-PERF-17 — Reduced-data branch and browser-support matrix  (→ PERF-17)
Add a Save-Data/prefers-reduced-data branch — co-located with the reduced-motion branch in the centerpiece wrapper and edge logic — that skips the Rive runtime and heavy media in favor of the static loop, and publish a versioned browser-support-matrix document enumerating supported browsers and documented degradation per capability. Rationale: an explicit data-saver path plus a written support matrix turns "graceful degradation" into a testable, declared contract.

---

## Accessibility & Reduced Motion — A11Y

### D-A11Y-01 — Semantic landmark + heading shell as a layout primitive  (→ A11Y-01, A11Y-15)
A single layout primitive renders the banner/main/contentinfo landmarks and a nav landmark for primary navigation, and provides a heading-level context provider so nested sections request the next level rather than hardcoding tags. This guarantees one h1 and no skipped levels structurally, and gives route-change focus (A11Y-15) a stable `role=main` target. Rationale: structure enforced once at the shell prevents per-page drift.

### D-A11Y-02 — Skip link + roving focus + AA focus-ring tokens  (→ A11Y-02)
The shell emits a visually-hidden-until-focused "Skip to main content" link as the first focusable node, and a global `:focus-visible` ring driven by the DS-08/DS-09 focus tokens (≥3:1, non-color-only). Roving focus is managed via DOM order rather than `tabindex` reordering. Rationale: DOM-order tabbing plus a token-defined ring keeps focus order and visibility correct without per-component overrides.

### D-A11Y-03 — Contrast is consumed from DS-02, not re-declared  (→ A11Y-03)
A11Y consumes the contrast pairing matrix owned by DS-02 (T-DS-04) and the Style Dictionary contrast gate; it does not define thresholds or a second gate. Components only reference approved token pairings (e.g. `--proven` on `--canvas` ≈12.5:1). `--text-faint` is restricted to decorative/disabled use and never used to convey state. Rationale: single source of truth — tokens + contrast live in DS; A11Y verifies usage via axe-core at runtime.

### D-A11Y-04 — Reduced-motion-first ClosedLoop with static labeled SVG fallback  (→ A11Y-04, A11Y-12)
ClosedLoop is authored static-first: the default server render is a fully labeled SVG (six stages + closed gate), and the Rive/animated layer is only mounted client-side when the resolved `useReducedMotion` context is false AND capability checks pass. The same SVG doubles as the loading placeholder (A11Y-12). Rationale: static-first means no flash of motion and a meaningful no-JS/loading state.

### D-A11Y-05 — Global MotionConfig + resolved-state informational components  (→ A11Y-05, A11Y-16)
A site-wide Framer `MotionConfig` reads the resolved `useReducedMotion` context (OS query OR the in-page control) and forces `reducedMotion="always"` when set, backed by a CSS `@media (prefers-reduced-motion: reduce)` rule plus a `data-reduced-motion` attribute backstop so the in-page toggle works even without the media query. Informational components accept a `resolved` prop to mount at final state. Rationale: one context drives both CSS and JS so OS and in-page sources can never disagree.

### D-A11Y-06 — Non-color state encoding for verification artifacts  (→ A11Y-06)
A single `VerificationState` primitive maps each status (proven, pending, unproven/dim, gate-closed) to a color token plus a mandatory non-color cue: a glyph shape, a monospace state word, and/or a fill pattern. Components cannot render a state without going through the primitive. Rationale: centralizing the encoding makes "never color alone" structurally guaranteed and grayscale-safe.

### D-A11Y-07 — EvidenceTrace as semantic DOM with figure/figcaption loop equivalent  (→ A11Y-07, A11Y-12, A11Y-13)
EvidenceTrace renders as semantic DOM (ordered list / definition list), not canvas, and the ClosedLoop SVG is wrapped in `<figure>` with a `<figcaption>` text equivalent summarizing the six stages and fail-closed outcome. Until a trace's backing artifact resolves, the component renders neutral placeholder text — never a "proven" word (A11Y-13). Rationale: text-first DOM is readable by AT and avoids inert-canvas dead-ends.

### D-A11Y-08 — Dual-pass axe-core CI gate emitting evidence artifacts  (→ A11Y-08, A11Y-13)
CI runs axe-core over every route twice — default render and reduced-motion render — and fails closed on any critical OR serious violation. Each run writes a JSON evidence artifact (rules executed, per-route results, timestamps); a missing artifact fails the job. The same artifacts feed the claims-integrity lint (A11Y-13). Rationale: the gate proves itself rather than self-asserting a pass.

### D-A11Y-09 — Fluid type scale + reflow-safe monospace artifact handling  (→ A11Y-09, A11Y-14)
A fluid (clamp-based) type scale plus container-level wrapping/overflow handling for monospace machine artifacts ensures single-column reflow at 400% zoom with no page-level horizontal scroll; long artifacts scroll within their own container. Rationale: containing overflow locally satisfies 1.4.10 without truncating evidence text.

### D-A11Y-10 — Accessible interactive controls: forms, loop, trace  (→ A11Y-10, A11Y-11, A11Y-14)
Form and custom controls share an accessible-control pattern: programmatic name + role, `aria-describedby` error association, a polite live region for failures, and ≥24×24 CSS px hit targets (44×44 where practical). The same pattern backs the loop pause/play and trace controls. Rationale: one pattern gives naming, error announcement, and target size consistently.

### D-A11Y-11 — Motion-pause control, flash-safety, non-auto-advancing scroll  (→ A11Y-11, A11Y-04)
Auto-starting/>5s/auto-updating motion (loop, scrollytelling, trace stream) exposes a keyboard-operable pause/stop/hide control honoring SC 2.2.2 even when reduced-motion is unset; scrollytelling advances only on user scroll, never on a timer; animations stay within flash-safety thresholds. Rationale: explicit user control independent of OS settings.

### D-A11Y-12 — Loading/empty/error states with stable a11y tree and claims integrity  (→ A11Y-12, A11Y-13, A11Y-15)
Loading uses the static labeled diagram and system-font fallback (`font-display: swap`); failures keep the page operable and suppress any unbacked verification words. The route-change announcer (A11Y-15) shares this live-region infrastructure. Rationale: a stable accessibility tree across load/error states prevents misleading or empty announcements.

### D-A11Y-13 — In-page "Reduce motion" control wired to PRIV-03 __pref store  (→ A11Y-16)
A footer "Reduce motion" toggle writes to the shared PRIV-03 `__pref` store; an init script reads `__pref` before hydration and sets the `data-reduced-motion` attribute so the static render is chosen on first paint and persists across reload. The resolved `useReducedMotion` context returns `osQuery || prefControl`, so either source enables reduced motion. Rationale: persistence + pre-hydration read gives a single shared, flash-free preference independent of the OS.

---

## SEO, Metadata & Structured Data — SEO

### D-SEO-01 — Centralized metadata factory over the App Router Metadata API  (→ SEO-01, SEO-02, SEO-03, SEO-11)
A single `buildMetadata()` factory consumes a route descriptor (title, description, path, ogImage, robots overrides) and returns a Next.js Metadata object, used by every `generateMetadata`/static export. Centralizing emission guarantees uniform tag coverage (title/description/canonical/OG/Twitter) and makes the no-JS SSR parity invariant (SEO-11) enforceable from one place rather than per-route ad hoc code.

### D-SEO-02 — Single origin constant + canonicalization & environment policy  (→ SEO-02, SEO-08, SEO-11)
One `SITE_ORIGIN` constant feeds `metadataBase`, canonical derivation, sitemap, robots, and feed. Canonicalization normalizes to apex host, https, and a single trailing-slash convention; a `DEPLOY_ENV` switch flips preview builds to preview-origin canonicals + global noindex. A single origin source of truth eliminates host/scheme drift across surfaces and satisfies the D2 single-source-of-truth principle for routes (manifest = IA; SEO imports lib/routes.ts).

### D-SEO-03 — Token-driven OG image system via ImageResponse with static fallback  (→ SEO-04, SEO-03, SEO-13)
OG cards render with `ImageResponse` from design tokens (--canvas #0A0B0D, --text #F5F7FA, --proven #34E1A0 reserved for a verification glyph) using self-hosted Geist Sans/Mono, at a fixed 1200x630. A try/catch wraps generation and serves a pre-built static brand fallback on failure. All card text is routed through the claims scanner (SEO-13) before render so no count claim leaks into an image.

### D-SEO-04 — Site-wide JSON-LD provider for Organization + WebSite  (→ SEO-05, SEO-11, SEO-13)
A root-layout provider emits exactly one Organization and one WebSite `<script type="application/ld+json">` from a typed config object, with no SearchAction (no on-site search) and sameAs limited to owned profiles. Serialized JSON-LD strings pass through the claims denylist regex before emission, so structured data can never carry an unverifiable verification count.

### D-SEO-05 — Article + BreadcrumbList JSON-LD derived from front-matter  (→ SEO-06, SEO-12, SEO-10)
Per-article Article/BreadcrumbList nodes are derived from the validated front-matter object and the IA-declared hierarchy, with dateModified defaulting to datePublished and a build-time assertion that all required fields exist. Breadcrumb item URLs are built from `lib/routes.ts` so they always match real navigation.

### D-SEO-06 — Build-time sitemap from the IA route+content manifest  (→ SEO-07, SEO-02, SEO-14)
sitemap.xml is generated from the single IA route manifest (`lib/routes.ts`) joined with the content loader, emitting only canonical indexable content routes; utility routes, noindex stubs, drafts, and error pages are excluded by construction. Per-post lastmod comes from the post source mtime, not the global build time, and large /writing sets fall back to a sitemap index.

### D-SEO-07 — Environment-aware robots.txt with sitemap reference  (→ SEO-08, SEO-02, SEO-07)
robots.txt is generated from `SITE_ORIGIN` and `DEPLOY_ENV`: production allows content routes, disallows non-indexable internal paths, never blocks rendering assets, and emits an absolute Sitemap: directive; preview emits Disallow: /. AI-crawler user-agent rules (SEO-17) are appended from the same generator so the policy is explicit, not implicit.

### D-SEO-08 — RSS/Atom feed generation with autodiscovery and empty-state handling  (→ SEO-09, SEO-12, SEO-02)
A feed builder consumes the same front-matter source, emits newest-first items with permalink-based guids and absolute links, channel metadata, and a valid zero-item channel when empty. Autodiscovery `<link rel="alternate">` is injected into /writing and article heads via the metadata factory so discovery stays centralized.

### D-SEO-09 — Semantic HTML + heading-outline discipline with MDX slugging  (→ SEO-10, SEO-12)
Page shells enforce exactly one <h1>, a <main> landmark, and correct nav/header/footer/article usage; an MDX rehype slug plugin assigns stable heading ids. Monospace machine-artifact spans are styled, non-heading elements so they never enter the outline. A lint/test pass walks the rendered heading sequence to catch level skips.

### D-SEO-10 — Typed MDX front-matter schema as single source of truth  (→ SEO-12, SEO-06, SEO-09, SEO-07, SEO-13)
A Zod schema validates every MDX file's front-matter; the parsed object is the sole input to metadata, Article JSON-LD, sitemap, and feed. Validation failures fail the build naming file+field; draft:true propagates noindex + exclusion everywhere from this one decision point, satisfying D2 single-source-of-truth.

### D-SEO-11 — Claims-integrity scanner as a required SEO gate  (→ SEO-13, SEO-01, SEO-03, SEO-04, SEO-05)
A CI scanner collects every generated SEO string surface and matches them against the value-agnostic denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b`; any match fails the build. The only allow-list is a single `content/claims-registry.json`, each entry carrying a source reference. No verification count is ever hardcoded in metadata or structured data (D3/G.1).

### D-SEO-12 — Stub / empty / error-state SEO policy  (→ SEO-14, SEO-08, SEO-13)
Stub routes (e.g. /docs while empty), empty states, and error pages are marked noindex, excluded from sitemap, and emit no rich JSON-LD; error routes return correct status codes. The same front-matter pipeline lets a stub graduate to indexable content by adding real front-matter, with no special-case code.

### D-SEO-13 — Lang attribute & i18n non-goal posture  (→ SEO-16)
The root layout hardcodes `<html lang="en">`; no hreflang alternates and no non-"en" inLanguage are emitted anywhere. Internationalization is recorded as an explicit non-goal of the website spec — a deliberate posture note in the design, not a deferred TODO — so reviewers do not mistake single-locale scope for an omission.

### D-SEO-14 — Static well-known files + robots AI-UA rules + llms.txt  (→ SEO-17)
/.well-known/security.txt (RFC 9116, with Contact + future Expires), an llms.txt thesis/proof summary, and explicit AI-crawler User-agent rules (e.g. GPTBot, ClaudeBot, Google-Extended) in robots.txt are served as static/generated artifacts. Naming AI agents makes the machine-reading policy explicit rather than relying on default crawl behavior.

### D-SEO-15 — Per-route OG cards + explicit social-identity decision  (→ SEO-18)
The ImageResponse system produces a distinct card per top-level marketing route (/, /how-it-works, /proof, /manifesto) by binding each to its own title/eyebrow descriptor. The social-identity decision is encoded explicitly: when no owned profiles exist, twitter:site and Organization sameAs are omitted entirely (not stubbed), and the omission is documented as a decision so it is never re-opened as a TODO.

### D-SEO-16 — CI SEO verification harness emitting machine-readable evidence  (→ SEO-15, SEO-11, SEO-13)
A CI harness runs the full SEO invariant suite (title/description uniqueness+length, single canonical/origin, OG/Twitter completeness + image 200/dimensions, JSON-LD validity, sitemap well-formedness + route-parity against IA, robots validity, feed validity, single-H1/order, lang presence, no-JS parity) as a required status check, writing a machine-readable evidence artifact per run consistent with the product's evidence ethos.

---

## Privacy, Analytics, Security & Consent — PRIV

### D-PRIV-01 — Cookieless, PII-free analytics adapter behind one boundary  (→ PRIV-01, PRIV-03, PRIV-08, PRIV-11)
Route all measurement through a single analytics adapter boundary so that the cookieless, PII-free contract is enforced in exactly one place. The adapter strips to the enumerated aggregate fields, never reads or writes an identifier, and is the only module permitted to emit events — making opt-out (PRIV-03), signal-honoring (PRIV-08), and silent-failure (PRIV-11) single-point concerns rather than scattered call sites.

### D-PRIV-02 — Consent-policy module: cookieless ⇒ no wall; non-essential ⇒ opt-in  (→ PRIV-02, PRIV-03, PRIV-08)
A consent-policy module computes the effective consent state from (a) whether only essential/cookieless processing is active, (b) the `__pref` opt-out, and (c) GPC/DNT signals. Because baseline processing is cookieless, the policy returns "no wall"; it only requires prior opt-in if a future non-essential cookie/script is registered. This keeps the no-modal guarantee and the future opt-in path as one decision function.

### D-PRIV-03 — First-party `__pref` preference store with no tracking identifier  (→ PRIV-03, PRIV-08, PRIV-12)
The opt-out and honored-signal state persist in a strictly-necessary first-party store named `__pref`, holding only a consent flag and signal-reflection state — never a per-visitor or cross-site identifier. This domain OWNS `__pref` as the single source of truth for preferences; the accessible privacy UI (PRIV-12) reads and writes only through it.

### D-PRIV-04 — Security headers + strict CSP via edge middleware with per-request nonce  (→ PRIV-05, PRIV-06, PRIV-15)
A single edge/middleware layer sets all transport and document headers and injects a per-request nonce into the CSP. The CSP is strict by construction (nonce/hash + `strict-dynamic`, `object-src 'none'`, `base-uri 'none'`, Trusted Types) and never falls back to a host-allowlist script-src. The header set and the CSP both derive their dynamic source list from `security/allowlist.ts` (see D-PRIV-11).

### D-PRIV-05 — Same-origin, self-hosted assets to drive third-party surface toward zero  (→ PRIV-07, PRIV-06, PRIV-01)
Fonts, the Rive runtime, and the analytics client are self-hosted same-origin so the strict CSP needs no external host entries and SRI is required only for any unavoidable remote asset. This makes the near-zero third-party surface a structural property that the strict CSP and the cookieless analytics contract both depend on.

### D-PRIV-06 — Optional email capture: minimal, explicit-consent, single first-party endpoint  (→ PRIV-04, PRIV-09, PRIV-13)
The Get-notified flow uses a minimal, unbundled, explicit-consent component posting to ONE first-party Get-notified endpoint (owned by this domain). The endpoint is the single source of truth for capture; its single state enum models the submission lifecycle (idle → submitting → success → error). The Privacy page (PRIV-09) and hardened API (PRIV-13) both reference this one endpoint and its declared processor.

### D-PRIV-07 — Privacy page and footer trust note as claims-integrity-gated content  (→ PRIV-09, PRIV-10, PRIV-14)
The Privacy page and footer note are generated from declared, verifiable facts only. The footer note is filtered through the claims-integrity guardrail (value-agnostic denylist regex; every claim mapped to `content/claims-registry.json`), and the Privacy page is correspondence-checked against live behavior. Both are gated by the verification suite (PRIV-14) so unverifiable text cannot publish.

### D-PRIV-08 — Resilient, non-blocking failure and motion-as-information for privacy UI  (→ PRIV-11, PRIV-12)
Analytics failures are swallowed at the adapter boundary (no retry storm, no console noise, no CWV impact); email failures surface an accessible inline error that preserves input. Privacy-UI motion is informational with a static `prefers-reduced-motion` fallback, keeping resilience and accessibility as paired concerns of one UI layer.

### D-PRIV-09 — Automated privacy/security verification suite as a fail-closed deploy gate  (→ PRIV-14, PRIV-01, PRIV-05, PRIV-06, PRIV-08)
A verification suite asserts live behavior against every published claim (cookieless storage scan, header smoke-tests, CSP-directive assertions, GPC/DNT suppression, analytics-payload PII absence) and runs as a fail-closed deploy gate: any unverified claim blocks the deploy and blocks the claim from publication.

### D-PRIV-10 — Single allowlist feeds header injection + prod report-to  (→ PRIV-15, PRIV-06)
ONE `security/allowlist.ts` enumerates every `connect-src` (and any other dynamic source) and is the sole input to (a) CSP header construction at the edge and (b) the production `report-to`/reporting endpoint configuration. Because both consumers read the same module, the strict CSP cannot drift across environments and no host-allowlist script-src can creep in through environment-specific config.

### D-PRIV-11 — Sub-processor register JSON + retention/DSR policy  (→ PRIV-16, PRIV-09)
A machine-readable sub-processor register (JSON) lists each sub-processor with its purpose, retention period, and DSR-handling note. The register is the single source the Privacy page renders from, and the notify-success analytics event schema is defined to exclude email and any email-hash so the PII-free assertion (via PRIV-14) holds against a concrete payload contract.

---

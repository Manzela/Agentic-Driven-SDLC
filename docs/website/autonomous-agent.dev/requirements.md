# Requirements — autonomous-agent.dev (flagship website)

> **Scope:** This is the specification for the **public marketing/manifesto website** at the root
> domain `autonomous-agent.dev`. It is **NOT** the product spec. The product — the *Spec-to-Evidence
> Coverage Control System* — has its own separate, canonical spec under
> [`.kiro/specs/spec-to-evidence-control/`](../../../.kiro/specs/spec-to-evidence-control/). Keep the two
> apart: this folder describes a website *about* the product, so it can never bias or contaminate the
> product's own Agentic SDLC.

**Materialized:** 2026-06-15 from `docs/plans/based-on-the-attached-eventual-cat.md` (PART B §B.1),
with all corrections from PART D (D1–D7), PART E deltas, and PART G (G.1–G.5) applied.

**Totals:** 205 requirements across 12 domains. Internal requirement→design→task traceability target: 100%.

**Format:** Kiro-style EARS. Each requirement carries an ID, priority (P0–P3), an EARS-pattern tag, a
user story (with "so that"), the EARS statement, ≥2 objective acceptance criteria, and resolved
dependencies. No dependency references a placeholder namespace; no claim hardcodes any `N/N verified`
count (per D3/G.1 — the corpus figure drifted 21→32→34, so verification is published qualitatively or
bound to live harness output).

**Domain index:** DS · IA · HOME · LOOP · CONTENT · PAGE · TECH · TOOL · PERF · A11Y · SEO · PRIV

---

## Brand & Design System — DS

### DS-01 — Dark-theme color token set as single source of truth  ·  P0  ·  EARS: ubiquitous
**User story:** As a site visitor, I want every surface, text, and border to resolve from a named brand token, so that the manifesto site reads as one coherent, intentional dark theme rather than an accident of stray hex values.
**EARS:** The design system SHALL define a complete dark-theme color token set (--canvas #0A0B0D, --surface #121417, --surface-2 #181B1F, --border #1E2227, --text #F5F7FA, --text-muted #8A8F98, --text-faint #5A606B, --proven #34E1A0, --pending #E2B340, --signal aliased to --proven) as the single source of truth, and every rendered surface, text, and border on the site SHALL resolve its color from a named token rather than a hard-coded literal.
**Acceptance criteria:**
1. The token set is the single source of truth (DS owns tokens + contrast); the built CSS exposes each named custom property (`--canvas`, `--surface`, `--surface-2`, `--border`, `--text`, `--text-muted`, `--text-faint`, `--proven`, `--pending`, `--signal`) with exactly the listed values, and `--signal` computes to the same value as `--proven`.
2. A static scan of authored CSS/TSX/MDX finds zero color literals (`#`-hex, `rgb(`, `rgba(`, `hsl(`) outside the token source files; every `color`, `background`, and `border-color` declaration references a `var(--…)` token.
**Depends on:** none

### DS-02 — WCAG 2.2 AA contrast guarantee for token pairings  ·  P0  ·  EARS: state
**User story:** As a low-vision visitor, I want every meaningful text and UI pairing to meet AA contrast, so that I can read claims and proof on a dark canvas without strain.
**EARS:** WHERE a token pairing is used for text or meaningful non-text UI, the design system SHALL guarantee WCAG 2.2 AA contrast (>=4.5:1 normal text, >=3:1 large text and meaningful graphical objects/focus indicators) against its intended background token, and IF a proposed token fails its target ratio, THEN the system SHALL adopt an AA-corrected value before launch.
**Acceptance criteria:**
1. A machine-checkable contrast matrix (owned by DS) asserts measured ratios: --proven #34E1A0 on --canvas #0A0B0D computes to ≈12.5:1 (locked, AA pass); --text on --canvas ≥7:1; --text-muted on --canvas ≥4.5:1; the canonical --error token on its intended background ≥3:1 (used for real errors only).
2. --text-faint #5A606B is asserted to be applied ONLY to decorative or disabled nodes (test fails if --text-faint resolves on any node that is enabled body/heading/label text), and any token pairing that measures below its AA target fails the build with the offending pair named.
**Depends on:** DS-01

### DS-03 — Typographic system, scale, and weights  ·  P0  ·  EARS: ubiquitous
**User story:** As a reader, I want a deliberate grotesk type system with a clear modular scale, so that the manifesto has editorial authority and legible body copy.
**EARS:** The design system SHALL define a typographic system using a self-hosted display/body grotesk (Geist Sans, Inter Variable fallback) at display weights 300–600 with tight negative tracking (-1.5px to -2px on display sizes), plus a modular type scale, fluid responsive sizing, and consistent line-heights for display, heading, body (17-19px), label, and caption roles.
**Acceptance criteria:**
1. Role tokens exist for display, heading, body, label, and caption; computed body font-size resolves within 17–19px at the desktop breakpoint and display roles apply letter-spacing between -1.5px and -2px.
2. No rendered display/body grotesk text uses a font-weight outside the 300–600 range (assertion over computed `font-weight` on all grotesk nodes).
**Depends on:** DS-01

### DS-04 — Self-hosted, swap-safe brand fonts  ·  P0  ·  EARS: event
**User story:** As a privacy-conscious visitor, I want fonts served same-origin with no layout shift, so that no third party sees my request and the page does not jump while loading.
**EARS:** The design system SHALL self-host all brand fonts (display/body grotesk and the monospace family) as subset, preloaded WOFF2 files served same-origin with no third-party font requests, and WHEN a web font is still loading, the system SHALL apply font-display:swap with a metric-matched fallback so that cumulative layout shift from font swap is negligible.
**Acceptance criteria:**
1. Network capture on first load shows zero font requests to any third-party origin; every font file is WOFF2, served same-origin, and the primary faces appear in `<link rel="preload" as="font">`.
2. Each `@font-face` declares `font-display: swap` with a metric-matched fallback (`size-adjust`/`ascent-override` present), and measured CLS attributable to font swap is < 0.01.
**Depends on:** DS-01, DS-03

### DS-05 — Machine artifacts rendered in monospace only  ·  P0  ·  EARS: state
**User story:** As a reader evaluating evidence, I want every machine artifact rendered in mono with tabular numerals, so that IDs, hashes, and trace fields are unambiguous and never disguised as prose.
**EARS:** WHERE content is a machine artifact (requirement IDs e.g. REQ-014, evidence records with test_file / test_name / output_hash / collected_at, content hashes, gate verdicts, code, and execution-trace spans), the design system SHALL render it in the monospace family (Geist Mono / JetBrains Mono) with tabular numerals and SHALL never render such artifacts in the display/body grotesk.
**Acceptance criteria:**
1. Every node carrying `[data-artifact]` resolves to the monospace `font-family` with `font-variant-numeric: tabular-nums`; conversely, mono font-family appears ONLY on `[data-artifact]` nodes (test fails if mono is applied to non-artifact prose).
2. Sample requirement IDs, evidence-record fields (test_file, test_name, output_hash, collected_at), content hashes, and gate verdicts each render inside a `[data-artifact]` node and never in a display/body grotesk node.
**Depends on:** DS-01, DS-03

### DS-06 — Accent reserved for verification states only  ·  P0  ·  EARS: state
**User story:** As a visitor, I want the green accent to mean "proven" everywhere, so that color itself carries verifiable meaning and is never spent on decoration.
**EARS:** The design system SHALL reserve --proven/--signal as the single accent used ONLY for verification states and system-correct signals (proved requirements, satisfied gates, evidence confirmation, focus/active system indicators), and IF an element is purely decorative or marketing chrome, THEN the system SHALL NOT use the accent for it.
**Acceptance criteria:**
1. Across the first viewport of each content route, accent (`--proven`/`--signal`) pixels occupy ≤3–5% of first-viewport pixels (measured), and no purely decorative/marketing-chrome node resolves its color/background to the accent token.
2. An allowlist enumerates the only sanctioned accent contexts (proved requirements, satisfied gates, evidence confirmation, focus/active indicators); any accent usage outside the allowlist fails the review gate.
**Depends on:** DS-01

### DS-07 — Layout tokens (spacing, radius, elevation, container)  ·  P0  ·  EARS: ubiquitous
**User story:** As a builder, I want all layout composed from spacing/radius/elevation/container tokens, so that editorial rhythm is consistent and no component invents its own geometry.
**EARS:** The design system SHALL define spacing (base-grid scale), border-radius, elevation/shadow, hairline-border, and container-width tokens (max content width ~1200-1280px), and every component SHALL compose layout exclusively from these tokens.
**Acceptance criteria:**
1. Tokens exist for spacing scale, border-radius, elevation/shadow, hairline border, and container width; the main content container computes a max-width within 1200–1280px.
2. A scan finds zero raw spacing/radius literals (`px`/`rem` margins, paddings, gaps, radii) outside the token source; every such property references a token.
**Depends on:** DS-01

### DS-08 — Motion registry: every animation maps to a real state  ·  P0  ·  EARS: unwanted
**User story:** As a visitor, I want every animation to communicate a real product state, so that motion is information rather than ambient flourish.
**EARS:** The design system SHALL define motion tokens (duration scale, easing curves, and named state-transition semantics) as the single motion registry (DS-08), and SHALL require that every shipped animation map to a real product/UI state transition; IF a proposed motion does not communicate a verifiable state (proof pulsing, coverage filling, gate closing, evidence lighting up), THEN the system SHALL NOT ship it.
**Acceptance criteria:**
1. The motion registry (DS-08) enumerates duration tokens, easing curves, and named state-transition semantics; every shipped animation declares a registry entry naming the state it represents.
2. A runtime motion-integrity assertion fails if any animated element lacks a `data-motion-intent` mapping to a registry entry (i.e. no motion ships without a named verifiable state).
**Depends on:** DS-01

### DS-09 — Reduced-motion state-preserving fallbacks  ·  P0  ·  EARS: event
**User story:** As a motion-sensitive visitor, I want non-essential motion disabled while still seeing the final state, so that I get the same information without animation.
**EARS:** WHEN the user agent reports prefers-reduced-motion: reduce, the design system SHALL disable non-essential motion and present a legible static equivalent that conveys the same state information (e.g. the closed loop renders as a labeled static diagram; coverage indicators show final filled state; gate shows its held verdict).
**Acceptance criteria:**
1. Under emulated `prefers-reduced-motion: reduce`, no element exhibits ongoing animation (computed `animation`/`transition` durations are zero or paused), verified at runtime.
2. In the reduced-motion state, the hero loop renders as a labeled static diagram, coverage indicators show the final filled state, and the gate shows its held verdict (DOM/text assertions present for each).
**Depends on:** DS-08

### DS-10 — Single token source builds deterministically  ·  P0  ·  EARS: unwanted
**User story:** As a maintainer, I want one token source that builds deterministically into CSS vars and the Tailwind theme, so that the human contract and machine output can never silently drift.
**EARS:** The design system SHALL maintain a single token source of truth (DESIGN.md as the human contract plus Style Dictionary JSON as the machine source) that builds deterministically into CSS custom properties and the Tailwind v4 theme, and the system SHALL fail the build IF the generated CSS/Tailwind theme drifts from the token source.
**Acceptance criteria:**
1. Running the token build twice from a clean tree produces byte-identical CSS-var and Tailwind `@theme` output (deterministic).
2. A drift check fails the build (non-zero exit) when the committed generated CSS/Tailwind theme differs from a fresh build of the Style Dictionary source.
**Depends on:** DS-01

### DS-11 — Token-driven component primitive library  ·  P0  ·  EARS: ubiquitous
**User story:** As a builder, I want a documented set of token-driven primitives with all interaction states, so that the site is assembled only from sanctioned building blocks.
**EARS:** The design system SHALL provide a documented library of token-driven component primitives (button variants for soft actions, cards/panels, status badges, and navigation) with defined default, hover, active, focus-visible, and disabled states, and these primitives SHALL be the only sanctioned building blocks for site UI.
**Acceptance criteria:**
1. Button, card/panel, status-badge, and navigation primitives each expose default, hover, active, focus-visible, and disabled states, each verifiable in the component gallery.
2. Each primitive resolves all color/spacing/radius from tokens (no literals), and a focus-visible indicator is present and measurable on every interactive primitive.
**Depends on:** DS-01, DS-07

### DS-12 — Code/trace/evidence block primitive  ·  P0  ·  EARS: event
**User story:** As a reader, I want evidence records and gate verdicts surfaced as labeled monospaced data, so that proof is shown as structured artifact, not marketing copy.
**EARS:** The design system SHALL define a code/trace block primitive rendered on --surface-2 with the monospace family, line/column alignment, optional requirement-ID gutter and hash-chain affordance, and accessible copy/scroll behavior, and WHEN an evidence record or gate verdict is displayed it SHALL surface its fields (test_file, test_name, output_hash, collected_at, verdict) as labeled monospaced data.
**Acceptance criteria:**
1. The primitive renders on `--surface-2` in the monospace family within a `[data-artifact]` region, with a keyboard-accessible copy control and scrollable overflow.
2. When given an evidence record or gate verdict, the rendered output exposes labeled fields test_file, test_name, output_hash, collected_at, and verdict, each in a `[data-artifact]` node.
**Depends on:** DS-05, DS-07

### DS-13 — Accessibility: keyboard, focus, non-color state, semantics  ·  P0  ·  EARS: ubiquitous
**User story:** As a keyboard or assistive-tech user, I want every control operable with visible focus and non-color state cues, so that I can use the whole site to AA standard.
**EARS:** The design system SHALL guarantee that all interactive primitives are keyboard-operable with a visible focus indicator, that state is never conveyed by color alone, that semantic roles/landmarks/labels are present, and that the system honors WCAG 2.2 AA including target size and focus-not-obscured.
**Acceptance criteria:**
1. An axe-core run over each content route reports zero critical OR serious violations.
2. Every interactive primitive is reachable and operable by keyboard with a visible focus indicator; every status conveyed by the accent color is also conveyed by text/icon (not color alone), and interactive targets meet the AA target-size minimum.
**Depends on:** DS-11

### DS-14 — Wordmark, logo usage, and line-icon set  ·  P1  ·  EARS: unwanted
**User story:** As a brand steward, I want defined wordmark/logo usage and a minimal icon set, so that the brand is consistent and never implies an unverifiable claim.
**EARS:** The design system SHALL define the 'Autonomous Agent' wordmark and logo usage (sizing, clear-space, color-on-dark, monochrome and single-accent variants, favicon/app-icon, and the 'Autonomous SDLC Platform' category descriptor lockup) and a minimal, consistent line-icon set, and IF an icon would imply an unverifiable claim or decorative AI-glow, THEN the system SHALL exclude it.
**Acceptance criteria:**
1. Wordmark assets exist with documented sizing, clear-space, color-on-dark, monochrome, and single-accent variants plus the category-descriptor lockup, each rendered in the gallery.
2. The icon set is a single line-icon family resolving color from tokens; an explicit exclusion check confirms no icon implies an unverifiable claim or uses a decorative AI-glow effect.
**Depends on:** DS-01, DS-06

### DS-15 — Performance budgets and CWV protection  ·  P1  ·  EARS: state
**User story:** As a visitor on a mid-tier device, I want the token/font/motion layer to stay within performance budgets, so that the site loads fast and never shifts under me.
**EARS:** The design system SHALL operate within documented performance budgets such that critical CSS/font/token payloads and motion assets do not regress Core Web Vitals (LCP < 2.5s, CLS < 0.1, INP < 200ms) on a mid-tier device, and WHILE the hero animation loads it SHALL not block the main thread or cause layout shift.
**Acceptance criteria:**
1. A measured run on a mid-tier device profile reports LCP < 2.5s, CLS < 0.1, and INP < 200ms; the build fails if any budget is exceeded.
2. While the hero animation loads, measured long-task main-thread blocking and layout shift attributable to the hero are below threshold (CLS contribution < 0.01).
**Depends on:** DS-04, DS-08, DS-10

### DS-16 — No quantified verification claims until verifiable  ·  P0  ·  EARS: unwanted
**User story:** As a skeptical reader, I want the design system to refuse any hardcoded "N/N verified" figure, so that every verification claim shown is evidence-backed rather than self-graded.
**EARS:** The design system SHALL NOT provide visual treatments (badges, counters, hero stats, mono 'verdict' chips) that present a specific quantified verification claim (e.g. an 'N/N formally verified' figure) unless the figure is bound to live harness output (value + run-hash + collected_at); WHERE a verification state is shown it SHALL render only evidence-backed states, never a self-graded summary number, and verification status SHALL otherwise be stated qualitatively.
**Acceptance criteria:**
1. A value-agnostic denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` matches nowhere in rendered DOM text or source content; any verification count present must be bound to live harness output carrying value, run-hash, and collected_at.
2. No badge/counter/hero-stat/mono-verdict-chip component can render a quantified verification figure from a static literal (the component contract rejects a hardcoded count and requires a harness-bound source or qualitative copy).
**Depends on:** DS-12

### DS-17 — Calm loading, empty, and asset-fallback states  ·  P1  ·  EARS: state
**User story:** As a visitor on a slow link, I want calm skeletons and graceful asset fallbacks, so that loading or failed enhancements never produce alarm-red or broken UI.
**EARS:** WHILE a token-driven component or motion asset is loading, the design system SHALL present a calm skeleton/placeholder using --surface/--surface-2 tokens, and IF an enhancement asset (Rive runtime, font, trace data) fails to load, THEN the system SHALL fall back to the static token-styled equivalent without alarm-red decoration.
**Acceptance criteria:**
1. Loading skeletons resolve their background to `--surface`/`--surface-2` tokens only (no accent, no alarm-red), verified on a throttled load.
2. With the Rive runtime / a font / trace data forced to fail, the component renders its static token-styled equivalent and no `--error`/red token appears in the fallback (DOM assertion).
**Depends on:** DS-01, DS-09

### DS-18 — Responsive system with no horizontal overflow  ·  P1  ·  EARS: state
**User story:** As a mobile visitor, I want type, spacing, and nav to adapt and the hero to degrade to a clean diagram, so that the site is fully usable from 320px with no sideways scroll.
**EARS:** The design system SHALL define responsive breakpoints and behaviors such that typography scales fluidly, containers and spacing adapt, navigation collapses accessibly, and the hero/trace degrade to a clean labeled diagram on small screens, with no horizontal overflow from 320px up.
**Acceptance criteria:**
1. From a 320px-wide viewport upward, `document.scrollingElement.scrollWidth` does not exceed the viewport width on any content route (no horizontal overflow).
2. At the small breakpoint, navigation collapses into an accessible disclosure (keyboard-operable, labeled) and the hero/trace renders as a labeled static diagram (DOM/text assertion).
**Depends on:** DS-03, DS-07, DS-11

### DS-19 — Complete icon/manifest bundle with no white-flash  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor who pins or installs the site, I want a complete, correctly-themed icon and manifest bundle, so that the app icon and theme color are correct everywhere and the page never flashes white on load.
**EARS:** The site SHALL ship a complete icon/manifest bundle (favicon.ico, a 32px icon, an opaque apple-touch-icon at 180px, 192px and 512px icons plus a maskable variant, and a web app manifest with theme_color #0A0B0D) and SHALL declare a `<meta name="theme-color">` for both light and dark color schemes.
**Acceptance criteria:**
1. All required assets are present and valid: favicon.ico, the 32px icon, an apple-touch-icon at 180px with an opaque (non-transparent) background, 192px and 512px icons, a maskable icon variant, and a parseable web manifest whose `theme_color` equals `#0A0B0D` (derived from `--canvas`).
2. Two `<meta name="theme-color">` declarations exist scoped to `prefers-color-scheme: light` and `dark`, and on first paint the document background resolves to `--canvas #0A0B0D` with no white-flash (measured: no white frame before first content paint).
**Depends on:** DS-01, DS-14

---

## Information Architecture & Navigation — IA

### IA-01 — Canonical content routes resolve  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor, I want every advertised section of the site to load at a clean URL, so that I can navigate the manifesto without hitting dead ends.
**EARS:** The site SHALL expose exactly the following canonical content routes at the root domain autonomous-agent.dev: /, /how-it-works, /proof, /manifesto, /writing, /docs; and WHERE /writing or /docs is not launched with content, the site SHALL resolve the route to a designed stub page rather than a hard 404.
**Acceptance criteria:**
1. GET /, /how-it-works, /proof, /manifesto, /writing, /docs each return HTTP 200.
2. The exact-content-route test asserts the registered content-route set equals exactly {/, /how-it-works, /proof, /manifesto, /writing, /docs, /privacy, /terms}, with utility routes (sitemap.xml, robots.txt, rss/feed, OG-image, /.well-known/security.txt, web-manifest) registered separately and excluded.
3. With /writing or /docs flagged content-empty, GET returns 200 and the DOM contains the stub-state container, not the 404 marker.
**Depends on:** none

### IA-02 — Single canonical URL form  ·  P0  ·  EARS: event
**User story:** As a search engine and a visitor, I want each page reachable at exactly one canonical URL, so that links, indexing, and analytics never fragment across casing or slash variants.
**EARS:** WHEN a request arrives at a non-canonical casing, a trailing slash, or a duplicate slash, the site SHALL issue a 308 permanent redirect to the single canonical, lowercase, hyphen-delimited, extensionless URL on the https://autonomous-agent.dev origin.
**Acceptance criteria:**
1. GET /How-It-Works, /how-it-works/, and //how-it-works each return HTTP 308 with Location: https://autonomous-agent.dev/how-it-works.
2. Every canonical content route serves a self-referential <link rel="canonical"> equal to its https://autonomous-agent.dev lowercase extensionless URL.
**Depends on:** IA-10
**Priority:** P0

### IA-03 — No-funnel primary navigation  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor, I want a calm primary nav free of sales pressure, so that the site reads as a manifesto rather than a funnel.
**EARS:** The primary navigation SHALL present only the wordmark and the destinations How it works, Proof, Manifesto, and Writing, plus a single soft Get notified action, and SHALL NOT contain any pricing, demo, contact-sales, sign-in, or purchase affordance.
**Acceptance criteria:**
1. The <nav> banner contains exactly the wordmark, the four destination links, and one Get notified control — and nothing matching a pricing/demo/contact-sales/sign-in/buy denylist.
2. A CI content-lint over nav markup fails if any denied affordance string appears.
**Depends on:** none

### IA-04 — Responsive navigation disclosure  ·  P0  ·  EARS: state
**User story:** As a mobile visitor, I want the nav to collapse into an accessible menu, so that I can reach every destination on a small screen.
**EARS:** WHILE the viewport is at or above the desktop breakpoint, the navigation SHALL display all destinations inline in a single sticky bar; WHILE the viewport is below the desktop breakpoint, the navigation SHALL collapse non-wordmark destinations into an accessible disclosure menu that opens a focus-trapped panel.
**Acceptance criteria:**
1. At >=1024px all destination links are visible inline and the disclosure toggle is not rendered.
2. At <1024px the disclosure button exposes aria-expanded, and opening it traps focus within the panel (Tab from last item returns to first).
**Depends on:** IA-03

### IA-05 — Current-route and scroll state feedback  ·  P1  ·  EARS: event
**User story:** As a visitor, I want the nav to show where I am and stay legible while scrolling, so that I keep my bearings without decorative distraction.
**EARS:** WHEN a navigation destination corresponds to the current route, the navigation SHALL mark that item with aria-current="page" and a restrained visual treatment; and WHILE the user scrolls, the navigation SHALL change state only to preserve legibility as an informational state change, not a decorative loop.
**Acceptance criteria:**
1. On each content route, exactly one nav item carries aria-current="page" matching the active path.
2. The scroll-state transition uses a registered DS-08 motion token and is a discrete state change (no infinite/looping animation in the DOM/animation registry).
**Depends on:** IA-03, DS-08

### IA-06 — In-page anchor navigation  ·  P1  ·  EARS: event
**User story:** As a visitor on a long page, I want anchor links to jump to and focus the right section, so that I can deep-link and read with keyboard support.
**EARS:** Each major narrative section SHALL carry a stable semantic anchor id; WHEN a user activates an in-page anchor link, the page SHALL scroll to the target, update the URL fragment, and move keyboard focus to the section heading; and WHERE prefers-reduced-motion is set, the page SHALL jump without smooth-scroll animation.
**Acceptance criteria:**
1. Each major section element has a stable id and the activated anchor updates location.hash and sets focus to the target heading.
2. Under emulated prefers-reduced-motion: reduce, the navigation produces an instant jump (no smooth-scroll motion token applied).
**Depends on:** IA-13, DS-09

### IA-07 — Breadcrumbs for nested routes  ·  P1  ·  EARS: state
**User story:** As a visitor on an article, I want a breadcrumb trail, so that I can see and traverse my location in the hierarchy.
**EARS:** WHERE a page is below the top level of the IA (e.g. a /writing/<slug> article), the page SHALL render a breadcrumb trail from Home to the current page, marking the current page non-interactive with aria-current="page", and SHALL NOT render breadcrumbs on the home page.
**Acceptance criteria:**
1. On /writing/<slug>, an ordered breadcrumb renders Home > Writing > <title> with the final crumb non-interactive and aria-current="page".
2. On /, no breadcrumb element is present in the DOM.
**Depends on:** IA-13, IA-16

### IA-08 — Branded 404  ·  P0  ·  EARS: unwanted
**User story:** As a visitor who mistypes a URL, I want a branded not-found page with navigation, so that I can recover instead of seeing a raw error.
**EARS:** IF a request resolves to no known route or content, THEN the site SHALL return HTTP 404 with a branded not-found page that preserves the global navigation and offers links back to the canonical primary destinations.
**Acceptance criteria:**
1. GET /no-such-page returns HTTP 404 and the response contains the branded not-found marker plus the global <nav> banner.
2. The 404 page contains anchor links to each canonical primary destination.
**Depends on:** IA-13

### IA-09 — Branded 500  ·  P1  ·  EARS: unwanted
**User story:** As a visitor hitting a server fault, I want a clean branded error page, so that I am not exposed to internal details and can return home.
**EARS:** IF an unrecoverable server or rendering error occurs, THEN the site SHALL return HTTP 500 with a branded error page that contains no stack trace, environment detail, or internal identifier, and SHALL offer a path back to the home route.
**Acceptance criteria:**
1. A forced server error returns HTTP 500 and the rendered body matches no stack-trace/env-var/internal-id pattern.
2. The 500 page contains a link resolving to /.
**Depends on:** IA-13

### IA-10 — Single canonical origin redirect map  ·  P0  ·  EARS: event
**User story:** As an operator, I want one canonical origin enforced by a version-controlled redirect table, so that www, http, and legacy aliases all funnel to the apex https origin.
**EARS:** WHEN a request arrives at the www host, an http scheme, or a registered legacy/alias path, the site SHALL issue a 301/308 permanent redirect to the corresponding https://autonomous-agent.dev canonical URL, and the redirect map SHALL be a declared, version-controlled table.
**Acceptance criteria:**
1. Requests to http://autonomous-agent.dev/x and https://www.autonomous-agent.dev/x return 301/308 to https://autonomous-agent.dev/x.
2. Each entry in the version-controlled redirect table resolves to a real canonical route or registered utility endpoint (no dangling targets).
**Depends on:** none

### IA-11 — Sitemap and robots from manifest  ·  P1  ·  EARS: ubiquitous
**User story:** As a search engine, I want a sitemap and robots derived from the route manifest, so that only canonical indexable URLs are surfaced.
**EARS:** The site SHALL generate sitemap.xml from the route manifest containing only canonical indexable URLs and SHALL serve robots.txt that references the sitemap; and WHERE a route is a non-content stub or an error/utility page, the site SHALL exclude it and mark it noindex.
**Acceptance criteria:**
1. GET /sitemap.xml lists exactly the indexable content routes from the manifest and omits stub/error/utility routes.
2. GET /robots.txt returns 200 and contains a Sitemap: directive pointing at https://autonomous-agent.dev/sitemap.xml.
**Depends on:** IA-03, IA-16
**Priority:** P1

### IA-12 — Global footer secondary nav and claims guard  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor, I want a footer with full secondary nav, a soft email capture, and a restrained trust note, so that I can reach everything without being shown unverifiable claims.
**EARS:** The global footer SHALL provide secondary navigation to all canonical destinations, a single soft Get notified email capture, and a restrained qualitative trust/security note, and SHALL NOT display any "N/N verified" count or other quantitative claim that is not independently evidence-backed.
**Acceptance criteria:**
1. The <footer> contentinfo contains resolvable links to every canonical destination plus one Get notified capture, with verdict/trust copy sourced from CONTENT-13.
2. Footer text contains no substring matching the value-agnostic denylist \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b.
**Depends on:** IA-03, CONTENT-06

### IA-13 — Landmarks, skip link, route-change focus  ·  P0  ·  EARS: event
**User story:** As a keyboard or screen-reader user, I want landmark regions, a skip link, and focus moved on navigation, so that I can operate the site accessibly.
**EARS:** The site SHALL expose semantic landmark regions on every page and SHALL provide a visible-on-focus skip-to-content link as the first focusable element; and WHEN a route change completes, the site SHALL move focus to the main content region or page heading.
**Acceptance criteria:**
1. Every page exposes banner, main, navigation, and contentinfo landmarks, and the first Tab focuses a skip-to-content link that becomes visible on focus.
2. After a client route change, document.activeElement is the main region or page heading; axe reports zero critical or serious violations.
**Depends on:** none

### IA-14 — SSG/ISR transitions with loading state  ·  P1  ·  EARS: event
**User story:** As a visitor, I want route changes to render without a blank flash, so that navigation feels stable.
**EARS:** WHEN a user navigates between routes, the site SHALL render the destination via SSG/ISR with no full-page reload flash; and WHILE a route or async section is loading, the site SHALL present a defined loading state rather than a blank screen or layout jump.
**Acceptance criteria:**
1. A client-side navigation does not trigger a full document reload (no full navigation event), preserving the persistent header instance.
2. While a route segment is pending, a skeleton/route-level loading element is present in the DOM in place of a blank region.
**Depends on:** none

### IA-15 — Content-driven stub/empty states  ·  P2  ·  EARS: state
**User story:** As a visitor reaching an unlaunched section, I want an honest stub state, so that I understand the section's intent without being misled about availability.
**EARS:** WHERE /docs is a launch-time placeholder or /writing has no published entries, the site SHALL render a designed stub/empty state that states the section's intent, preserves global navigation, and offers the soft Get notified action, without fabricating content or implying availability.
**Acceptance criteria:**
1. With the section flagged empty, the route returns 200 and renders the stub container with intent copy, the global nav, and a Get notified control.
2. The stub DOM contains no article/list-item content nodes and no availability claim text.
**Depends on:** IA-01

### IA-16 — Per-route metadata and social cards  ·  P1  ·  EARS: ubiquitous
**User story:** As a sharer, I want each route to carry unique accurate metadata and social cards, so that links preview correctly without unverifiable claims.
**EARS:** Each canonical route SHALL define unique, accurate metadata — title, description, canonical URL, and Open Graph/Twitter card — derived from the route manifest and page content, and SHALL NOT include any unverifiable quantitative claim in share metadata.
**Acceptance criteria:**
1. Each canonical route emits a unique <title>, meta description, self-referential canonical URL, and og:/twitter: card tags.
2. No metadata value matches the claims denylist \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b.
**Depends on:** IA-02, IA-11

### IA-17 — Unpublished writing-slug lifecycle  ·  P2  ·  EARS: unwanted
**User story:** As an operator unpublishing an article, I want the old slug to redirect or gone and drop from discovery surfaces, so that stale URLs never index or 404.
**EARS:** IF a previously-public /writing slug is unpublished, THEN the site SHALL issue a 301 redirect to /writing (or return 410), drop the slug from sitemap.xml and the feed, and record a redirect-table entry.
**Acceptance criteria:**
1. GET the unpublished /writing/<slug> returns HTTP 301 to /writing or HTTP 410, and the slug is absent from /sitemap.xml and /rss feed.
2. The version-controlled redirect/lifecycle table contains an entry for the unpublished slug.
**Depends on:** IA-10, IA-11

### IA-18 — Legal routes in manifest  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor and a search engine, I want /privacy and /terms to exist as indexable legal pages outside primary nav, so that legal content is reachable and crawlable without cluttering the manifesto nav.
**EARS:** The route manifest SHALL include /privacy and /terms as indexable, inNav:false, isLegal:true entries that are excluded from the exact-content-route test, with ownership shared by IA and PRIV.
**Acceptance criteria:**
1. GET /privacy and GET /terms each return HTTP 200 and are indexable (no noindex, present in sitemap.xml).
2. Neither /privacy nor /terms appears in the primary nav, the footer legal links resolve to them, and the exact-content-route test still passes with these entries excluded.
**Depends on:** IA-03, IA-11, IA-12

---

## Homepage Scrollytelling Narrative — HOME

### HOME-01 — Hero with closed-loop centerpiece and permanent static fallback  ·  P0  ·  EARS: event
**User story:** As a first-time visitor, I want the hero to assert the product thesis instantly and stay legible even if motion never loads, so that I grasp "delivery that proves itself" without depending on an animation.
**EARS:** WHEN the homepage finishes its first contentful paint, the Hero section SHALL render the brand wordmark, a single oversized display headline asserting the product thesis (delivery that proves itself), a one-line subhead, the soft primary action (See how it works), and a mount-point for the closed-loop centerpiece; WHILE the centerpiece asset is still loading, the Hero SHALL render a legible static labeled diagram of the loop (intent -> decompose -> implement -> verify -> prove -> gate); IF the centerpiece asset fails to load or is unsupported, THEN the Hero SHALL retain the static labeled diagram as the permanent fallback and SHALL NOT show a broken-asset or error state.
**Acceptance criteria:**
1. In server-rendered HTML (JS disabled), the Hero DOM contains: a wordmark node, exactly one `h1` display headline, a subhead element, an anchor whose text is "See how it works" resolving to `/how-it-works` (route per IA-03), and a centerpiece mount-point element.
2. The static labeled loop diagram is present in the DOM at load and contains the six ordered stage labels in canonical order: intent, decompose, implement, verify, prove, gate (gate last); a build assertion verifies the order reads intent → decompose → implement → verify → prove → gate and that no stage places the gate before verify.
3. Simulating centerpiece load failure (asset 404 / unsupported) leaves the static diagram visible and produces no element with role="alert", no "error"/"failed" text, and no broken-image node.
4. The hero accent (--proven / --accent) occupies ≤3–5% of first-viewport pixels; all monospace text is confined to `[data-artifact]` nodes.
5. WHERE the hero copy enumerates the powering stack, it names Claude Code, Neon, Langfuse, Playwright, and Semgrep as the in-scope tools and references Temporal only as an OPTIONAL / roadmap (Phase-5) durable-execution substrate, never as a wired-in spine member.
**Depends on:** DS-01, DS-07, DS-08, IA-03, LOOP-05

### HOME-02 — Ordered named beat sequence with stable ids and ordinals  ·  P0  ·  EARS: event
**User story:** As a visitor or analytics consumer, I want each narrative beat to be an addressable, ordered section, so that deep-links, in-page nav, and progress tracking resolve to the correct beat without reordering the reading flow.
**EARS:** The Homepage SHALL present its narrative as an ordered sequence of named sections: (1) Hero+loop, (2) Fragmented-stack problem, (3) Human-as-infrastructure replace-table, (4) Closed-loop explained, (5) Proof model, (6) The leap, (7) Who it's for, (8) Soft close; WHEN the document is parsed, each section SHALL expose a stable id and an ordinal; WHERE a section is the active beat in the viewport, the Homepage SHALL expose that state programmatically without altering the reading order.
**Acceptance criteria:**
1. The server-rendered HTML contains exactly eight `section` elements, each with a non-empty stable `id` and a `data-beat-ordinal` whose values are the contiguous integers 1..8 in document order.
2. The eight section ids and ordinals match the route/section manifest owned by IA (IA-12); HOME imports the manifest and does not re-declare section names locally.
3. The active beat is exposed via a programmatic attribute (e.g., `data-active-beat` / `aria-current`) on exactly one section at a time; toggling active state does not change DOM order.
4. Each section id is reachable as a URL fragment and scroll-resolves to that section.
**Depends on:** IA-03, IA-12

### HOME-03 — Fragmented-stack consolidation as a deterministic scroll-bound state machine  ·  P0  ·  EARS: event
**User story:** As a visitor, I want the sprawling-tools grid to visibly collapse into one engine as I scroll, so that I feel the fragmentation-to-consolidation argument as a deterministic, reversible system state.
**EARS:** WHEN the Fragmented-stack section enters the viewport, it SHALL render a dense grid of tool/domain tiles drawn from the product corpus; WHILE the section is pinned and the user scrolls through its progress range, the grid SHALL animate as a deterministic, scroll-bound state machine that collapses the many tiles into a single consolidated engine element, each transition step mapped to a discrete scroll-progress value; IF the section uses scroll-pinning, THEN the pin SHALL release cleanly at the end of its progress range with no jump, overlap, or trapped scroll.
**Acceptance criteria:**
1. The tile set is rendered from the content corpus and is present as static DOM text (tile labels assertable with JS disabled).
2. Each consolidation step maps to a discrete scroll-progress value; replaying the same progress value yields the identical visual/DOM state (deterministic, no time/random dependence), verified via a runtime motion-integrity assertion exposed on `[data-motion-integrity]`.
3. At progress = 1.0 the grid has resolved to a single consolidated engine element that carries a visible label naming the real spine — "the gate-chain + coverage-model spine (Stop hook + OPA/Conftest + GitHub ruleset over a default-unproven feature_list.json)" — and on pin release, document flow resumes with measured CLS ≤ 0.1 and no overlapping/trapped-scroll condition.
4. Scrubbing progress backward reverses the state machine through the same discrete steps in reverse order.
5. The consolidated engine element's spine label is present as static DOM text and names the Stop hook, OPA/Conftest, the GitHub ruleset, and the default-unproven feature_list.json (string assertion).
**Depends on:** DS-08, DS-09

### HOME-04 — Human-as-infrastructure replace-table with static two-column baseline  ·  P0  ·  EARS: event
**User story:** As a visitor, I want each human role mapped to its machine substitute, revealing on scroll but readable as a plain table, so that I understand what the engine replaces regardless of motion support.
**EARS:** WHEN the Human-as-infrastructure section enters the viewport, it SHALL render the replace-table mapping each human role to its machine substitute (human-as-memory -> requirement-ID-tagged durable state; human-as-verifier -> fail-closed coverage model; human-as-scope-enforcer -> bounded task decomposition; human-as-auditor -> tamper-evident execution trace; human-as-integration-lead -> proactive domain-baseline discovery; human-as-tool-selector -> pre-integrated opinionated stack); WHILE the section is in view, each row SHALL reveal as an informational micro-interaction tied to scroll, transitioning the row from the human framing to the machine framing; the replace-table SHALL be fully readable as a static two-column table when motion is unavailable.
**Acceptance criteria:**
1. The server-rendered HTML contains a two-column table (or semantically equivalent role=table) with exactly the six role->substitute pairs above, all text assertable with JS disabled.
2. The six row copies are sourced from the content layer (CONTENT-06), not hardcoded in the component.
3. With reduced-motion or motion unavailable, all six rows render in their resolved (machine-framing visible) two-column form by default.
4. Scroll-driven reveal changes only presentation; no row's text content is reachable only mid-animation.
**Depends on:** DS-08, CONTENT-06

### HOME-05 — Closed-loop-explained beat with synchronized captions and gate-holds-the-line  ·  P0  ·  EARS: state
**User story:** As a visitor, I want the shared loop to advance stage-by-stage with captions and to show the gate rejecting an unproven item as a positive event, so that I read fail-closed as the feature, not a failure.
**EARS:** WHILE the Closed-loop-explained section is the active beat, the Homepage SHALL advance the shared loop centerpiece through its stages in canonical order (intent, decompose, implement, verify, prove, fail-closed gate — gate last) in lockstep with scroll progress and SHALL display a synchronized per-stage caption; WHEN scroll progress reaches the fail-closed-gate stage, the section SHALL present the gate holding the line on an unproven item as a system-correct event (gate glows the accent, the unproven item dims to faint/pending, copy frames the rejection as the feature) and SHALL render the canonical gate-stage caption verbatim from CONTENT-13; IF the centerpiece is in reduced-motion or static mode, THEN the section SHALL present the same six stages in canonical order and the gate-holds-the-line beat as a captioned static sequence.
**Acceptance criteria:**
1. The six stage captions exist in static DOM in canonical order (gate last) and are sourced from the content layer; the gate-verdict copy and the canonical gate-stage caption are imported verbatim from CONTENT-13 and not re-declared in HOME.
2. The gate-glow state uses the single reserved accent token (--proven / --accent from DS-01); the dimmed unproven item uses --text-faint (decorative/disabled-only) and never the canonical --error token.
3. With reduced-motion active, all six stages and the gate-holds beat render in their final/resolved captioned form (reduced-motion final-state assertion passes).
4. No alarm-red / --error styling appears on the gate verdict in any state.
5. The rendered gate-stage caption equals the canonical CONTENT-13 string ("The Stop hook holds the line locally; OPA/Conftest runs a zero-evidence policy at merge; a GitHub ruleset makes both required.") byte-for-byte (no inline literal in HOME).
**Depends on:** DS-01, DS-08, LOOP-05, CONTENT-13

### HOME-06 — Proof-model beat with live evidence record and no aggregate count  ·  P0  ·  EARS: event
**User story:** As a skeptical visitor, I want to see the governing invariant, a real four-field evidence record, and the auditor question, so that I trust proof comes from verifiable facts rather than a marketing tally.
**EARS:** WHEN the Proof-model section enters the viewport, it SHALL render (a) the governing invariant stated plainly (deterministic gates decide completeness from verifiable facts; model self-assessment informs, never gates), (b) a live monospaced evidence record showing the four-field schema (test_file, test_name, output_hash, collected_at) for a requirement, and (c) the north-star auditor question; WHILE a requirement transitions from pending to proven, the panel SHALL animate the proof as a real state change — the requirement ID and its evidence fields illuminate to the accent only once the evidence record is complete; the evidence record SHALL be presented as illustrative/representative sample data and SHALL NOT assert any specific aggregate verification count.
**Acceptance criteria:**
1. Static DOM contains the invariant text, the auditor question, and an evidence record exposing the four fields test_file, test_name, output_hash, collected_at.
2. The evidence record renders inside `[data-artifact]` nodes (the only place monospace is permitted) and is labeled/marked as illustrative sample data.
3. No homepage text matches the value-agnostic denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` (claims firewall, CONTENT-06).
4. The pending->proven illumination applies the accent only when the four evidence fields are all present; with reduced-motion the record renders in its resolved (proven, illuminated) final state.
5. The section states the independent-verifier principle in qualitative terms — "the verifier has no write access to implementation and never grades its own output" — present as static DOM text (string assertion).
**Depends on:** DS-01, PAGE-03, LOOP-05, CONTENT-06

### HOME-07 — The-leap beat: removes recede, guarantees resolve  ·  P1  ·  EARS: event
**User story:** As a visitor, I want what the engine removes to fade and what it guarantees to resolve to accent, so that I read the leap as a state change while still being able to read it as a plain list.
**EARS:** WHEN the The-leap section enters the viewport, it SHALL contrast what the engine removes (manual tool-selection, manual context-management, manual micro-steering, manual traceability) against what it guarantees (evidence-backed, coverage-verified, proof-traced output); WHILE the section is in view, the removed items SHALL recede toward muted/faint and the guaranteed outcomes SHALL resolve toward primary/accent; the section SHALL remain fully legible as a static two-part list when motion is unavailable.
**Acceptance criteria:**
1. Static DOM contains both lists: four "removes" items and three "guarantees" items, all text assertable with JS disabled.
2. List copy is sourced from the content layer (CONTENT-06).
3. Receded items use muted/--text-faint tokens; resolved items use --proven/--accent (DS-01); accent coverage stays ≤3–5% of viewport pixels.
4. With reduced-motion the section renders in its resolved two-part state by default.
**Depends on:** DS-01, DS-08, CONTENT-06

### HOME-08 — Who-its-for editorial audience framing with no funnel  ·  P1  ·  EARS: unwanted
**User story:** As a regulated-industry reader, I want the audience described editorially with no sales funnel, so that the page reads as a manifesto, not a pitch, and makes no unverifiable customer claims.
**EARS:** WHEN the Who-its-for section enters the viewport, it SHALL describe the audience as regulated and safety-critical software delivery (e.g., aerospace, medical, finance, defense) framed editorially; the section SHALL NOT render a customer logo-wall, pricing, demo CTA, or any lead-gen funnel element, and SHALL NOT reference subdomains or sibling products; WHERE named customers do not yet exist, the section SHALL use the audience/criteria framing and reserve any logo-wall pattern as a future, evidence-gated slot.
**Acceptance criteria:**
1. Static DOM contains the editorial audience copy (sourced from CONTENT-06) and the named domains aerospace, medical, finance, defense.
2. The section contains no pricing text, no "demo"/"book"/"contact sales" CTA, no `<form>` lead-gen element, no logo-wall image grid, and no link to any sibling-product subdomain.
3. Any customer/logo claim is gated behind the claims firewall and absent until evidence-backed; the value-agnostic verification-count denylist regex finds no match in the section.
4. The section contains one qualitative sentence tying the regulated audiences to the substrate they need — "tamper-evident proof of what an agent did, for which requirement, with what outcome — a hash-chained gate-decision audit log, SLSA provenance, and bidirectional requirement-to-evidence traceability." — present as static DOM text (string assertion).
5. The section makes no EU AI Act / regulatory-conformity claim; a denylist asserts zero occurrences of regulatory-conformity phrasing (e.g. 'EU AI Act compliant', 'AI Act conformity', 'regulation compliant') in the section.
**Depends on:** CONTENT-06, IA-03

### HOME-09 — Soft-close with manifesto link and fully-stated Get-notified affordance  ·  P1  ·  EARS: optional
**User story:** As a convinced visitor, I want a manifesto-tone close with only soft actions and an optional notify control that handles every state, so that I can engage without hitting a sales motion or a content gate.
**EARS:** WHEN the Soft-close section enters the viewport, it SHALL present a final manifesto-tone statement and soft actions only: Read the manifesto, See how it works, and an optional Get notified affordance; IF a Get notified affordance is present, THEN it SHALL be a single low-friction control whose submission, success, error, and already-subscribed states are all explicitly handled, and it SHALL NOT gate access to any site content; the Soft-close section SHALL NOT contain pricing, demo booking, or any hard sales motion.
**Acceptance criteria:**
1. Static DOM contains a "Read the manifesto" link to `/manifesto` and a "See how it works" link to `/how-it-works` (routes per IA-03), plus manifesto-tone closing copy from CONTENT-06.
2. The Get-notified control delegates to the PRIV-owned notify component and renders distinct, assertable states for submitting, success, error, and already-subscribed.
3. No site content is gated behind notify submission; the section contains no pricing/demo/booking element.
**Depends on:** IA-03, CONTENT-06, PRIV

### HOME-10 — Reduced-motion resolved-state-by-default  ·  P0  ·  EARS: state
**User story:** As a user who prefers reduced motion, I want every beat presented in its final resolved form with no information trapped in animation, so that the full narrative is reachable without any motion.
**EARS:** WHERE the user agent reports prefers-reduced-motion: reduce, the Homepage SHALL disable scroll-pinning, scrubbing, and all non-essential transitions and SHALL present every section as a static, fully-legible layout with all loop stages, table rows, and proof states shown resolved; the Homepage SHALL ensure no narrative content is reachable only via an animation in-between state; WHEN reduced motion is active, any motion-revealed state (proven illumination, gate-holds, consolidation result) SHALL render in its final/resolved state by default.
**Acceptance criteria:**
1. Under emulated prefers-reduced-motion: reduce, no scroll-pinning or scrubbing handlers are active and no non-essential transition runs.
2. All loop stages, all six replace-table rows, the gate-holds beat, the proven evidence illumination, and the grid-consolidation result are present in resolved form in the DOM (reduced-motion final-state assertions pass for each).
3. Every narrative text string assertable in motion mode is equally assertable in reduced-motion mode (no content gated by an in-between animation frame).
**Depends on:** DS-08, DS-09

### HOME-11 — Responsive/touch variant without scroll trapping  ·  P0  ·  EARS: state
**User story:** As a mobile/touch visitor, I want stacked in-view reveals and a scaled legible loop with no scroll hijacking, so that the narrative works on my device with native scrolling intact.
**EARS:** WHERE the viewport is below the desktop breakpoint or the device is touch-primary, the Homepage SHALL render a responsive variant that replaces scroll-pinning with stacked in-view reveals, scales the loop centerpiece to a legible labeled form, and reflows multi-column beats (replace-table, the leap) into single-column; WHILE on a touch device, the Homepage SHALL NOT trap scroll, hijack native momentum scrolling, or require horizontal scrolling; the mobile loop SHALL degrade to a clean labeled diagram when full playback is not viable.
**Acceptance criteria:**
1. Below the DS-defined desktop breakpoint, no scroll-pin is applied; beats use stacked in-view reveals and the page has no horizontal overflow (scrollWidth ≤ clientWidth).
2. The replace-table and The-leap reflow to single-column; the loop centerpiece renders as a scaled labeled diagram with the six stage labels present.
3. On a touch viewport, native scroll/momentum is not intercepted (no preventDefault on touchmove that blocks scroll) and no scroll-trap condition occurs.
**Depends on:** DS-01, DS-09

### HOME-12 — Progressive asset loading with reserved layout and static-first copy  ·  P0  ·  EARS: state
**User story:** As any visitor, I want all copy and fallbacks server-rendered immediately with motion lazy-loaded into reserved space, so that the page is readable instantly and asset arrival never shifts layout.
**EARS:** WHILE the centerpiece and deferred section assets are loading, the Homepage SHALL render all section copy and static fallbacks immediately from server-rendered HTML and SHALL lazy-load below-the-fold motion assets and per-section state machines on approach to the viewport; IF a deferred section asset fails to load, THEN that section SHALL fall back to its static representation without blocking the rest of the page or surfacing a raw error; the Homepage SHALL reserve layout space for all deferred visual elements so asset arrival causes no layout shift.
**Acceptance criteria:**
1. With JS disabled, every section's copy and static fallback are present in the response HTML.
2. Below-the-fold motion assets are not requested until the section approaches the viewport (verifiable via network request timing / IntersectionObserver wiring).
3. Each deferred visual element has reserved dimensions; cumulative layout shift across full load and scroll measures CLS ≤ 0.1.
4. Forcing a deferred asset to 404 leaves its section in static form, surfaces no raw error, and does not block sibling sections from rendering.
**Depends on:** DS-08, PAGE-03

### HOME-13 — Static/ISR HTML with SEO metadata and evidence-backed claims  ·  P1  ·  EARS: event
**User story:** As a search crawler or sharer, I want the homepage served as static/ISR HTML with complete, honest metadata, so that the full narrative is indexable without running scroll animations and no metadata makes unverifiable claims.
**EARS:** WHEN the Homepage is requested, it SHALL be served as static/ISR HTML containing the full narrative copy, a unique title and meta description, canonical URL at the root domain, Open Graph and Twitter card metadata with a representative preview image, and appropriate structured data (e.g., Organization/WebSite); the Homepage SHALL expose all narrative text to crawlers without requiring scroll-animation execution, and any structured-data or meta claims SHALL be evidence-backed and contain no unverifiable aggregate verification counts.
**Acceptance criteria:**
1. The response HTML contains a unique `<title>`, a `<meta name="description">`, `<link rel="canonical">` pointing to the root domain (`/`, per IA-03), Open Graph + Twitter card tags with an image, and JSON-LD Organization/WebSite structured data.
2. All eight beats' narrative text is present in the static HTML body (assertable with JS disabled).
3. No metadata, structured-data, or body string matches the verification-count denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b`; all claims trace to the content/claims registry (CONTENT-06).
**Depends on:** IA-03, PAGE-03, CONTENT-06

### HOME-14 — Every animation maps to a named state; no decoration  ·  P0  ·  EARS: unwanted
**User story:** As a brand steward, I want every animation tied to a defined product/system state and confined to the reserved accent for verification states, so that nothing ships as pure decoration and accent stays meaningful.
**EARS:** The Homepage SHALL ensure that every animation maps to a defined product/system state (consolidation, stage progression, pending->proven, gate-holds-the-line, role substitution) and SHALL NOT ship any animation whose sole purpose is decoration; WHERE an animated element represents a verification or system-correct state, the Homepage SHALL render it in the single reserved accent, all other animated states using neutral/muted tokens; IF a proposed motion cannot be tied to a named state, THEN it SHALL NOT be included.
**Acceptance criteria:**
1. A homepage motion inventory exists listing each animation with its named state from the motion registry (DS-08); every shipped animated element carries a `data-motion-state` whose value is one of the registered states.
2. No animated element lacks a registered state mapping (the build/test fails if an animation has no `data-motion-state` in DS-08's registry).
3. Accent (--proven/--accent, DS-01) is applied only to verification/system-correct states and occupies ≤3–5% of first-viewport pixels; all other animated states use neutral/muted tokens.
**Depends on:** DS-01, DS-08

### HOME-15 — Scroll-state robustness: deterministic settling and fragment resolution  ·  P1  ·  EARS: complex
**User story:** As a visitor scrolling fast, reversing, or jumping by anchor, I want each scroll-bound section to stay consistent with scroll position and settle to the correct beat, so that I never see stuck, skipped, or out-of-order states.
**EARS:** WHILE a visitor scrolls rapidly, reverses direction, or jumps via anchor/keyboard within a scroll-bound section, the Homepage SHALL keep each section's state machine consistent with the current scroll position and SHALL settle deterministically to the correct beat; IF the user navigates to a fragment that lands inside a pinned/scrub range, THEN the Homepage SHALL resolve that section to the corresponding progress state without breaking the pin or leaving a partial animation; the Homepage SHALL throttle/debounce scroll-driven updates so scroll handling does not exceed the performance budget.
**Acceptance criteria:**
1. For any scroll position, the section state equals the deterministic function of progress (verified by a runtime motion-integrity assertion on `[data-motion-integrity]` comparing rendered state to mapped progress) with no stuck/skipped/out-of-order state.
2. Navigating directly to a fragment inside a pinned/scrub range resolves that section to the corresponding progress state with the pin intact and no partial-animation residue.
3. Scroll-driven updates are throttled/debounced; the scroll handler stays within the defined performance budget (no dropped-frame budget breach under rapid scroll/reverse).
**Depends on:** DS-08, DS-09

---

## Rive Closed-Loop Centerpiece + Evidence Trace — LOOP

### LOOP-01 — Closed loop of six ordered, named stages  ·  P0  ·  EARS: event
**User story:** As a visitor, I want a single continuous closed loop of six named, ordered stages, so that I can read the autonomous SDLC as one self-returning cycle rather than a list of features.
**EARS:** WHEN the centerpiece mounts and motion is permitted, the ClosedLoop SHALL drive the active-stage indicator around the loop (intent → decompose → implement → verify → prove → gate, returning to origin) in canonical order at a pace that completes one full traversal in 8–14 seconds.
**Acceptance criteria:**
1. All six stage labels (intent, decompose, implement, verify, prove, gate) are present as DOM text at every captured frame, each in a distinct screen position, with the traversal direction unambiguous and the loop visibly returning to origin.
2. The active-stage indicator advances in canonical order and one full traversal measured from runtime telemetry falls within 8–14 seconds (inclusive) on the default playthrough.
**Depends on:** DS-08

### LOOP-02 — Single Rive state machine as source of truth  ·  P0  ·  EARS: ubiquitous
**User story:** As an engineer, I want the loop driven by one Rive state machine via named inputs, so that what is displayed is deterministic and host-controlled rather than ad-hoc CSS.
**EARS:** The ClosedLoop SHALL be driven by a single Rive state machine whose named states correspond to the loop stages and whose named inputs and triggers are the only mechanism by which the host application changes what is displayed.
**Acceptance criteria:**
1. The host changes displayed state exclusively through named Rive inputs/triggers; no time-based CSS animation or Framer Motion drives stage progression, gate behavior, or evidence-proving transitions (asserted by source audit and a runtime motion-integrity check).
2. Every named Rive state maps one-to-one to a declared loop stage in the state-machine contract; an unmapped state fails the contract test.
**Depends on:** DS-08

### LOOP-03 — Three concurrent acceptance goals per playthrough  ·  P0  ·  EARS: complex
**User story:** As a visitor, I want the centerpiece to be legible, satisfying-not-alarming, and artifact-driven on every default playthrough, so that the loop earns trust rather than performing it.
**EARS:** WHILE motion is permitted, the ClosedLoop SHALL concurrently satisfy three goals on every default playthrough — (1) legible in under 5 seconds, (2) the fail-closed gate rejection staged as satisfying not alarming, (3) requirement IDs and evidence traces rendered as live monospaced machine artifacts that light to the proven accent as proved; WHERE any goal cannot be met for a viewport or motion preference, the ClosedLoop SHALL degrade to the static fallback rather than ship a partial animation that violates a goal.
**Acceptance criteria:**
1. Legibility: at the captured frame all six stage labels are present as DOM text at or above a defined minimum px size, pass AA contrast against --canvas, and occupy distinct positions — verified within the deterministic capture window.
2. Satisfying-not-alarming: the proven accent is applied to the gate at the hold-frame AND no red hue appears anywhere across the full choreography frame-sequence within the deterministic window.
3. Artifact-driven: requirement IDs and evidence values render only on [data-artifact] nodes in the mono typeface and transition to --proven exactly when their evidence record is complete.
**Depends on:** LOOP-01, LOOP-06, DS-01, DS-08

### LOOP-04 — Requirement tokens traverse and turn proven  ·  P0  ·  EARS: event
**User story:** As a visitor, I want monospaced requirement tokens to travel the stages and light up when proved, so that proof is shown as a per-requirement event, not a claim.
**EARS:** WHEN a requirement token reaches the prove stage with a complete evidence record, the ClosedLoop SHALL transition that token's state from pending to proven and light it to the proven accent.
**Acceptance criteria:**
1. At least one monospaced requirement token (e.g. REQ-014) is visible traversing the stages; tokens render only on [data-artifact] nodes in the mono typeface, with no hand-drawn icons or marketing labels substituted for machine artifacts.
2. A token's computed color equals --proven only after its evidence record is complete; before completion its color is --pending; the transition is observable at the prove stage frame.
**Depends on:** DS-01, DS-07

### LOOP-05 — EvidenceTrace: hash-chained four-field records  ·  P0  ·  EARS: event
**User story:** As a visitor, I want a live append-only evidence stream with a tamper-evident schema, so that each proven requirement is backed by an inspectable record.
**EARS:** WHEN the loop proves a requirement token, the EvidenceTrace SHALL append the corresponding four-field evidence record (test_file, test_name, output_hash, collected_at) in lockstep as a hash-chained sequence and light its requirement ID and output_hash to the proven accent.
**Acceptance criteria:**
1. Each appended record exposes exactly the four fields test_file, test_name, output_hash, collected_at as readable DOM text on [data-artifact] nodes; each record's chain link references the prior record's hash (tamper-evident ordering verifiable in the DOM).
2. Append occurs in lockstep with the LOOP-04 prove event (no record appears before its token is proven; none is missing after), and the proven record's ID and output_hash compute to --proven.
**Depends on:** LOOP-04, DS-01

### LOOP-06 — Fail-closed gate holds unproven items, accent-as-correct  ·  P0  ·  EARS: unwanted
**User story:** As a visitor, I want the gate to hold back unproven work while glowing the proven accent, so that a correct rejection reads as the system working, not failing.
**EARS:** WHEN a requirement reaches the gate stage without a complete evidence record, the gate sub-machine SHALL transition to a holding/closed state in which the gate glows the proven accent and the unproven item is visibly held back (dimmed toward --text-faint/--pending) rather than error-flashed.
**Acceptance criteria:**
1. At the hold-frame the gate element's accent color equals --proven and the held item's color trends to --text-faint/--pending; the gate verdict copy is sourced from CONTENT-13 (not hardcoded in the component).
2. The gate SHALL NOT use alarm-red, shake, buzzer-like motion, or other failure-coded affordances for a correct rejection; alarm-red is reserved strictly for genuine runtime error states.
**Depends on:** DS-01, DS-08, CONTENT-13

### LOOP-07 — Multi-beat gate choreography with surfaced reason  ·  P0  ·  EARS: complex
**User story:** As a visitor, I want the rejection staged as ordered beats that explain why, so that the gate reads as intentional choreography rather than a glitch.
**EARS:** WHILE the gate evaluates, the gate sub-machine SHALL stage an ordered multi-beat sequence — approach, evaluate, hold/close with accent glow, settle — each driven by a named state, and SHALL briefly surface the reason the item is held (e.g. a monospaced 'no evidence' / 'unproven' marker sourced from CONTENT-13).
**Acceptance criteria:**
1. Each of the four beats corresponds to a distinct named Rive state observable in order within the deterministic window; the verdict/reason copy is read from CONTENT-13 and rendered on a [data-artifact] node in the mono typeface.
2. The held item's reason marker is present as DOM text during the evaluate beat and dismissed by the settle beat; no red hue appears across the sequence.
**Depends on:** LOOP-06, DS-08, CONTENT-13

### LOOP-08 — Static fully-labeled SSR fallback  ·  P0  ·  EARS: unwanted
**User story:** As a visitor on reduced-motion or a failed runtime, I want a static fully-labeled diagram, so that I get the same information without animation or client JS.
**EARS:** IF the user agent reports prefers-reduced-motion: reduce OR the Rive runtime fails to load, THEN the ClosedLoop and EvidenceTrace SHALL render a static fully-labeled diagram (all six stages, the gate in its holding state, at least one proven and one held token) plus a representative static evidence record set, server-rendered by default.
**Acceptance criteria:**
1. With JavaScript disabled and on first byte, the SSR output already contains all six stage labels, the gate in holding state, ≥1 proven and ≥1 held token, and ≥1 four-field evidence record as DOM text.
2. Under prefers-reduced-motion: reduce or a forced Rive load failure, no animated canvas mounts and the static diagram conveys the same information as the animated version.
**Depends on:** LOOP-01, DS-08

### LOOP-09 — One-accent semantic color layer  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor, I want a single disciplined accent semantics, so that color itself signals verification rather than decoration.
**EARS:** The ClosedLoop and EvidenceTrace SHALL use --proven (#34E1A0 on --canvas #0A0B0D, ≈12.5:1) exclusively for verified/evidence/system-correct signals, --pending for awaiting-evidence states, and --text-faint for held/unproven items, introducing no additional saturated hue.
**Acceptance criteria:**
1. A token-binding audit asserts every accent/pending/faint color in the centerpiece resolves to --proven, --pending, or --text-faint from DS (no inline hex, no extra saturated hue); display weights stay within 300–600.
2. --proven on --canvas measures ≈12.5:1 contrast; alarm-red is absent from all states except a genuine runtime error state.
**Depends on:** DS-01, DS-07

### LOOP-10 — Optional synchronized interaction with auto-resume  ·  P1  ·  EARS: optional
**User story:** As a visitor, I want to pause, focus a stage or token, and see the matching evidence highlight, so that I can inspect the loop on my own terms.
**EARS:** WHERE interaction is enabled and motion is permitted, the ClosedLoop SHALL let the visitor pause/resume and focus a stage or token via pointer and keyboard by driving named Rive inputs deterministically; WHEN a stage or token is focused, the EvidenceTrace SHALL highlight the corresponding record (and vice versa); and the loop SHALL auto-resume cinematic playback after a bounded idle period.
**Acceptance criteria:**
1. Focusing a stage/token (pointer or keyboard) highlights exactly the corresponding evidence record and the reverse holds; the two surfaces stay synchronized in the DOM.
2. After a bounded idle interval with no interaction, cinematic playback auto-resumes from a coherent state.
**Depends on:** LOOP-12

### LOOP-11 — Responsive layout with labeled small-screen reflow  ·  P0  ·  EARS: state
**User story:** As a visitor on any device, I want the loop and evidence panel to adapt without losing labels or gate semantics, so that the centerpiece stays legible everywhere.
**EARS:** WHILE on a large viewport the ClosedLoop and EvidenceTrace SHALL present loop and evidence panel side-by-side, and WHILE on a small viewport the ClosedLoop SHALL reflow to a vertically stackable, simplified-but-labeled loop with the trace below, preserving all six labels and the gate's holding semantics; IF the viewport is too small to animate legibly, THEN it SHALL fall back to the static labeled diagram.
**Acceptance criteria:**
1. At a defined large breakpoint the loop and evidence panel render side-by-side; at a defined small breakpoint they stack with all six stage labels and the gate holding semantics still present as DOM text.
2. Below the legibility threshold the static diagram (LOOP-08) renders instead of an illegible animation, verified by capture at the small breakpoint.
**Depends on:** LOOP-08, IA-03

### LOOP-12 — Accessible text equivalent and ARIA semantics  ·  P0  ·  EARS: ubiquitous
**User story:** As a screen-reader user, I want an ordered text equivalent of the loop and navigable evidence records, so that I get the full meaning without seeing the animation.
**EARS:** The ClosedLoop SHALL expose to assistive technology an ordered text equivalent (the six stages, the gate's fail-closed behavior, ≥1 proven and ≥1 held requirement) via appropriate roles/names/descriptions, and the EvidenceTrace SHALL expose its records as readable navigable text; WHILE animation plays, the ClosedLoop SHALL NOT convey any information by motion alone that is not also available as text or static state.
**Acceptance criteria:**
1. An accessibility-tree snapshot exposes the six ordered stages, the fail-closed gate behavior, and ≥1 proven and ≥1 held token as named/described nodes; evidence records are navigable text, not canvas-only.
2. An axe-core run on the centerpiece reports zero violations, and every motion-conveyed state has a text or static-state equivalent (no information-by-motion-alone).
**Depends on:** IA-03

### LOOP-13 — Fixture-backed artifacts, no unbacked aggregate count  ·  P0  ·  EARS: unwanted
**User story:** As a visitor, I want artifacts drawn from a committed illustrative fixture modeled on the real schema and never an unbacked "N/N verified" headline, so that the centerpiece shows the mechanism instead of an unverifiable claim.
**EARS:** The ClosedLoop and EvidenceTrace SHALL render only artifacts drawn from a committed fixture modeled on the product's real evidence schema and SHALL NOT display any aggregate verified/formally-verified count; WHERE a numeric proof statistic would otherwise appear, the centerpiece SHALL instead show the per-requirement evidence mechanism (the four-field record and the gate verdict). WHERE the centerpiece characterizes what the proof establishes, it SHALL clarify qualitatively that the hash-chained log is tamper-evident proof that execution happened as recorded (proof of execution) — distinct from proof that generated code is correct (proof of correctness), which is out of scope — and that the Z3 logic model checks the requirement logic model, not generated code.
**Acceptance criteria:**
1. All rendered IDs, hashes, and records resolve to entries in the committed fixture; claims copy is sourced from content/claims-registry.json, with no count computed or hardcoded in the component.
2. The rendered output and source pass a value-agnostic denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` (zero matches); the centerpiece presents the four-field record + gate verdict in place of any headline number.
3. Where the centerpiece characterizes the proof, it states qualitatively that the hash-chained log is proof of execution (tamper-evident proof that execution happened as recorded), distinct from proof of correctness (out of scope), and that Z3 checks the requirement logic model rather than generated code; string/presence assertion.
**Depends on:** LOOP-05, CONTENT-06

### LOOP-14 — Lazy-load Rive, reserved box, off-critical-path  ·  P0  ·  EARS: unwanted
**User story:** As a visitor, I want the centerpiece to load without blocking paint or shifting layout, so that the page stays fast and stable.
**EARS:** The ClosedLoop SHALL lazy-load the Rive runtime and .riv asset without blocking first paint, reserve its layout box ahead of load, and keep animation work off the critical path so Core Web Vitals targets are met; IF the device is low-powered, on save-data/slow connection, or the asset exceeds its load-time budget, THEN the ClosedLoop SHALL present the static fallback instead of the animated canvas.
**Acceptance criteria:**
1. The Rive runtime/asset is code-split and loaded after first paint; the reserved layout box yields zero cumulative layout shift attributable to the centerpiece (CLS contribution = 0).
2. Under save-data, an emulated low-power/slow connection, or an exceeded asset budget, the static fallback (LOOP-08) renders and no canvas mounts.
**Depends on:** LOOP-08, DS-08

### LOOP-15 — Playback gated on visibility  ·  P1  ·  EARS: state
**User story:** As a visitor, I want the loop to play only when on-screen, so that it doesn't burn cycles off-view or autoplay before I scroll to it.
**EARS:** WHILE the centerpiece is scrolled out of view or the document is hidden, the ClosedLoop SHALL pause playback, resuming from a coherent state when it returns to view, and SHALL begin playback only when its container intersects the viewport.
**Acceptance criteria:**
1. Playback starts only after the container intersects the viewport; on initial load before scroll it does not autoplay.
2. When scrolled out of view or the tab is backgrounded, playback pauses and resumes from a coherent state on return (verified by telemetry/state inspection).
**Depends on:** LOOP-14

### LOOP-16 — Calm labeled skeleton and evidence awaiting state  ·  P1  ·  EARS: state
**User story:** As a visitor, I want a calm labeled loading state instead of a spinner, so that the structure is visible while assets load and never hangs indefinitely.
**EARS:** WHILE the Rive asset or evidence fixture is loading, the ClosedLoop SHALL display a calm on-brand skeleton already showing the loop's labeled structure in a neutral (not-yet-proven) state and the EvidenceTrace SHALL show a labeled empty/awaiting state; IF loading exceeds the budget or fails, THEN the centerpiece SHALL resolve to the static fallback (LOOP-08) with a representative static record set, never an indefinite spinner.
**Acceptance criteria:**
1. During loading the skeleton shows all six stage labels in a neutral (--pending) state and the evidence panel shows a labeled awaiting state — no blank panel, no spinner-only.
2. On exceeded budget or failure the centerpiece resolves to the LOOP-08 static fallback with a representative static record set within the defined budget (no indefinite spinner).
**Depends on:** LOOP-05, LOOP-08

### LOOP-17 — Stage reveals its named Tier-1 tool, motion-bound-to-state  ·  P0  ·  EARS: event
**User story:** As a visitor, I want each of the six canonical stages to surface the actual Tier-1 tool that runs it only while that stage is active, so that I see a verifiable stage-to-tool mapping in the correct order — with the gate last — rather than a logo parade.
**EARS:** WHEN a loop stage activates, the ClosedLoop SHALL reveal that stage's named Tier-1 tool across the canonical six stages in order — Intent → the human brief; Decompose → the Claude Code initializer subagent (Spec Compiler + Coverage Builder, with spec-compilation folded into decompose) over git worktrees; Implement → the Claude Code implementer subagent (one slice per worktree) with PreToolUse prevention and PostToolUse feedback; Verify → Playwright · Semgrep/CodeQL · Hypothesis · k6/Lighthouse · axe-core plus the independent verifier subagent (no write access, never grades its own output); Prove → the four-field Evidence_Record plus a hash-chained audit log plus the Z3 logic model (surfaced via Langfuse/OTel); Gate (last) → the Claude Code Stop hook · OPA/Conftest zero-evidence policy · GitHub ruleset — as motion bound to state (a tool surfaces only while its stage runs), not a logo parade; the runtime substrate SHALL be named as Neon and Langfuse/OTel, with Temporal marked OPTIONAL (durable-execution roadmap, not a wired-in spine member); and WHERE prefers-reduced-motion: reduce, the ClosedLoop SHALL show the static node → tool mapping for all six stages in canonical order. Where the gate-stage caption is shown it SHALL reuse the canonical gate-stage caption verbatim from CONTENT-13. Claude Code hooks are command-type and fail closed; PostToolUse cannot undo an executed action; the hook roster is emerging/version-gated.
**Acceptance criteria:**
1. A tool label is present and revealed only while its owning stage is the active state; visual-regression at each named state asserts the correct tool label appears, that the canonical six-stage order reads intent → decompose → implement → verify → prove → gate with the gate last, and that other stages' tool labels are not concurrently surfaced (no logo parade).
2. Under prefers-reduced-motion: reduce, the static node → tool mapping renders the complete six-stage-to-tool correspondence as DOM text in canonical order (gate last), and a reduced-motion assertion verifies the full mapping is present.
3. Temporal, wherever it appears in the substrate label, is marked OPTIONAL / roadmap and never presented as a wired-in spine member; Neon and Langfuse/OTel are named as the in-scope substrate.
4. The gate-stage caption text equals the canonical gate-stage caption imported from CONTENT-13 (no inline literal), and the hook honest-limit note (command-type, fail-closed, PostToolUse cannot undo an executed action, roster emerging/version-gated) is present as qualitative copy wherever Claude Code hooks are named.
**Depends on:** LOOP-01, DS-08, CONTENT-13

---

## Content, Copy & Claims Integrity — CONTENT

### CONTENT-01 — Voice-and-tone spec with allow/deny lexicon  ·  P0  ·  EARS: ubiquitous
**User story:** As a content author, I want a single documented Voice Spec with machine-checkable allow/deny lexicons, so that every copy block is anti-hype and evidence-first without subjective review.
**EARS:** The site copy SHALL conform to a single documented Voice Spec (declarative, evidence-first, anti-hype, peer-to-peer; no exclamation marks, no superlatives unless evidence-backed, no second-person sales imperatives outside CTAs, no emoji in body copy), and every copy block SHALL be checkable against the Voice Spec's allow/deny lexicon.
**Acceptance criteria:**
1. The copy-lint gate fails on any body string containing a denylist term ('revolutionary', 'game-changing', 'effortless', 'magic', 'seamless', 'unleash', 'supercharge', '10x', standalone 'AI-powered') and passes on text using only allowed evidence terms ('verifiable', 'fail-closed', 'evidence-backed', 'deterministic', 'proven', 'independent').
2. The copy-lint gate fails on any body-copy exclamation mark or emoji codepoint and reports the offending page and character offset.
**Depends on:** none

### CONTENT-02 — Hero headline/subhead from ranked candidate set  ·  P0  ·  EARS: event
**User story:** As a visitor, I want one primary headline and one subhead stating the integrator-and-proof thesis, so that the value is legible in one screen without hype.
**EARS:** WHEN the home hero renders, the site SHALL present exactly one headline (closed-loop-integrates-the-stack-and-proves-the-work thesis) and one subhead (the proof wedge: independent, evidence-backed verification) drawn from an approved ranked candidate set, the headline being a single line at widths >=1024px where length permits and never wrapping beyond three lines at 360px.
**Acceptance criteria:**
1. The rendered headline and subhead strings each match an entry in the committed candidate matrix (exact-match assertion in test), and exactly one of each renders.
2. At a 360px viewport the headline element wraps to at most three lines (measured line-box count), and at >=1024px to one line for candidates under the documented length budget.
**Depends on:** IA-03, DS-01

### CONTENT-03 — 'What it replaces' six canonical rows  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor, I want the six corpus-grounded role-to-substitute rows, so that I see precisely what the closed loop displaces.
**EARS:** The site SHALL render a 'What it replaces' module containing exactly the six role-to-substitute rows (human-as-memory -> requirement-ID-tagged durable state; human-as-verifier -> fail-closed coverage model; human-as-scope-enforcer -> bounded task decomposition; human-as-auditor -> tamper-evident execution trace; human-as-integration-lead -> proactive domain-baseline discovery; human-as-tool-selector -> pre-integrated opinionated stack), with machine artifacts rendered in the monospace family. The human-as-verifier and human-as-auditor substitute cells SHALL name "per-edit prevention before a write lands" via PreToolUse plus the Stop hook (qualitative; never any latency or timing figure), and the human-as-scope-enforcer substitute cell SHALL name git worktrees plus the scope-sequencing gate. Where Claude Code hooks are named, the module SHALL co-state the hook honest-limit: Claude Code hooks are command-type and fail closed; PostToolUse cannot undo an executed action; the hook roster is emerging/version-gated.
**Acceptance criteria:**
1. The module renders exactly six rows whose label pairs equal the six canonical strings (set-equality assertion); any extra, missing, or altered row fails the build.
2. Every machine-artifact token in the module (e.g. requirement IDs) carries a [data-artifact] attribute and resolves to the monospace token; non-artifact prose does not use mono.
3. The human-as-verifier and human-as-auditor substitute cells name "per-edit prevention before a write lands" via PreToolUse + the Stop hook (qualitative, no latency/timing figure), and the human-as-scope-enforcer cell names git worktrees + the scope-sequencing gate; string/presence assertion.
4. Wherever Claude Code hooks are named, the hook honest-limit note (command-type, fail-closed, PostToolUse cannot undo an executed action, roster emerging/version-gated) renders as qualitative copy.
**Depends on:** DS-07

### CONTENT-04 — 'The leap' two-group bullet module  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor, I want eliminations and guarantees as two grouped noun-phrase bullet sets, so that the leap is scannable and free of unproven numbers.
**EARS:** The site SHALL render 'The leap' as two grouped bullet sets — (a) eliminations: zero tool-selection, zero context-management, zero micro-steering, zero manual traceability; (b) guarantees: evidence-backed, coverage-verified, proof-traced — where each bullet is a noun phrase and contains no quantified claim. The module's source annotation SHALL clarify (non-rendered, or as qualitative supporting copy) that "zero context-management" means durable-state offloading (PreCompact/SessionStart + Postgres), NOT predictive context (which is roadmap), so the elimination is not read as an overclaim.
**Acceptance criteria:**
1. Each bullet matches a no-verb / noun-phrase shape check and the claims-ledger numeric scan finds zero digits in the module.
2. The two groups render exactly the four elimination bullets and three guarantee bullets from the canonical list (exact-match assertion).
3. The "zero context-management" bullet carries a source annotation (or qualitative supporting copy) scoping it to durable-state offloading (PreCompact/SessionStart + Postgres) and explicitly excluding predictive context (roadmap); a presence assertion confirms the scoping note and the numeric scan still finds zero digits.
**Depends on:** none

### CONTENT-05 — Corpus-to-module mapping registry  ·  P0  ·  EARS: complex
**User story:** As a content maintainer, I want every marketing module traced to a corpus element, so that no claim is ungrounded.
**EARS:** The content system SHALL maintain a corpus-to-module mapping that routes the 16 problem domains and 7 unresolved market gaps into the home problem section and manifesto spine, the 19 capability blocks (B01-B19) into the /how-it-works taxonomy, and the governing invariant, evidence schema, and independent verifier into /proof; and WHERE any module makes a substantive claim, the module SHALL carry a non-rendered source annotation citing its corpus element.
**Acceptance criteria:**
1. A build assertion confirms every module flagged as substantive has a non-rendered corpus citation resolving to a real corpus element ID.
2. The mapping covers all 16 domains, 7 gaps, and 19 capability blocks with no orphan corpus element and no module citing a nonexistent element (referential-integrity check passes).
**Depends on:** IA-12, CONTENT-11

### CONTENT-06 — Claims-integrity guardrail and claims ledger  ·  P0  ·  EARS: unwanted
**User story:** As the site owner, I want every factual claim registered in a single claims ledger with a corpus citation and verifiability status, so that no unverifiable assertion ever ships.
**EARS:** The content system SHALL register every published factual claim in one claims ledger (content/claims-registry.json) with a corpus citation and a verifiability status, and IF a claim is a quantified or comparative assertion that is not independently verifiable at publish time, THEN the build SHALL fail and the claim SHALL NOT ship; the site SHALL NOT publish any specific 'N/N verified' verification tally.
**Acceptance criteria:**
1. content/claims-registry.json is the single source consumed by every lint gate; each entry has corpus_citation and verifiability_status fields, and a missing or 'unverifiable' status on a quantified/comparative claim fails the build.
2. The value-agnostic denylist regex \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b blocks 21/21, 32/32, 34/34, and 100/100 equally across all routes.
**Depends on:** none

### CONTENT-07 — Machine-artifact rendering schema  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor, I want machine artifacts shown in a fixed monospace schema and never confused with model opinion, so that evidence reads as evidence.
**EARS:** The content system SHALL render all machine artifacts (requirement IDs, evidence records, output hashes, gate verdicts, trace spans) using the monospace token and a fixed display schema, and WHERE an evidence record is shown it SHALL expose the four corpus fields test_file, test_name, output_hash, collected_at and SHALL NOT present a model self-assessment as evidence.
**Acceptance criteria:**
1. The monospace token resolves only on [data-artifact] nodes; a lint asserts no prose node uses mono and no [data-artifact] node uses the prose family.
2. Every rendered evidence record exposes exactly the four fields test_file, test_name, output_hash, collected_at; absence of any field fails the build.
**Depends on:** DS-07

### CONTENT-08 — Readability budget and inline glossary  ·  P1  ·  EARS: state
**User story:** As a technical-professional reader, I want a numeric readability budget and inline definitions, so that prose stays scannable and jargon is never undefined.
**EARS:** WHILE any page is being built, the content system SHALL enforce a readability budget (body median sentence length <=22 words; manifesto paragraphs <=5 sentences; one idea per paragraph with a leading topic sentence), and WHERE corpus jargon (e.g. 'fail-closed', 'OPA', 'EARS') appears it SHALL be defined inline or in a glossary on first use per page.
**Acceptance criteria:**
1. The reading-level check computes median sentence length per body block and fails any page exceeding 22 words (numeric threshold) or any manifesto paragraph exceeding 5 sentences.
2. A glossary-presence check fails the build for any flagged jargon term whose first per-page occurrence lacks an inline definition or glossary link.
**Depends on:** none

### CONTENT-09 — Soft-CTA allowlist  ·  P0  ·  EARS: unwanted
**User story:** As a visitor, I want only honest soft CTAs and no sales pressure, so that the site stays a manifesto, not a funnel.
**EARS:** The site SHALL render only soft CTAs from the approved set ('See how it works', 'Read the manifesto', optional 'Get notified') and SHALL NOT render any pricing, demo, trial, sales-contact, or hard-conversion CTA nor reference sibling products; and WHERE 'Get notified' exists its microcopy SHALL state honestly what the visitor receives and SHALL NOT imply an uncommitted launch date.
**Acceptance criteria:**
1. A CTA-allowlist scan fails the build on any interactive CTA label outside the approved set across all routes.
2. The denylist scan finds zero occurrences of 'pricing', 'demo', 'free trial', 'contact sales', or any committed-date launch phrasing in CTA microcopy.
**Depends on:** PRIV-01

### CONTENT-10 — Microcopy and non-happy-path state catalog  ·  P1  ·  EARS: event
**User story:** As a visitor in an edge state, I want clear microcopy for errors, loading, and empty states, so that the system feels deliberate and never alarming.
**EARS:** The content system SHALL define microcopy for all interactive and non-happy-path states (labels, helper text, validation/submission errors, loading/skeleton, empty states, component error/fallback), and WHEN an unproven or pending state is described the copy SHALL frame it as the system correctly holding the line, never as visitor failure.
**Acceptance criteria:**
1. A catalog-coverage check asserts every defined state (error, loading, empty, fallback) for each interactive component has non-empty microcopy registered.
2. Pending/unproven-state strings pass the Voice Spec lint and contain no alarm lexicon ('error!', 'failed', 'oops') framed against the visitor (assertion against approved framing list).
**Depends on:** CONTENT-15

### CONTENT-11 — Manifesto MDX with verbatim invariant  ·  P1  ·  EARS: ubiquitous
**User story:** As a reader, I want the manifesto authored as numbered MDX sections quoting the governing invariant precisely, so that the argument is structured and the invariant is exact.
**EARS:** The /manifesto content SHALL be authored in MDX as numbered sections opening with the category thesis, proceeding through the fragmented-stack problem, human-as-infrastructure, the closed loop, and the proof wedge, and closing without a hard sell, and WHERE it states the governing invariant it SHALL quote it precisely: deterministic gates decide completeness from verifiable facts only; model self-assessment informs, never gates. WHERE the closed-loop section names the enforcement layer, it SHALL name it concretely — "The only thing that can halt or redirect a running agent is a deterministic Claude Code command hook (PreToolUse, PostToolUse, Stop, SubagentStop, PreCompact, SessionStart) — not a prompt, not CLAUDE.md — and command hooks fail closed." — and SHALL name the four bounded subagents (initializer, implementer, verifier, research). It SHALL also state the bounded-execution and self-correction note: iteration/token/no-progress caps route to HANDOFF (a terminal state distinct from COMPLETE), and the team found and fixed its own HANDOFF infinite-block defect (a self-audit trust signal). Claude Code hooks are command-type and fail closed; PostToolUse cannot undo an executed action; the hook roster is emerging/version-gated.
**Acceptance criteria:**
1. The MDX renders as sequentially numbered sections covering the five required spine elements (presence assertion per section id).
2. The verbatim governing-invariant string is present exactly once and matches the canonical text byte-for-byte (exact-match assertion).
3. The closed-loop section names the enforcement layer concretely — the deterministic Claude Code command hook (PreToolUse, PostToolUse, Stop, SubagentStop, PreCompact, SessionStart), stated as the only thing that can halt or redirect a running agent (not a prompt, not CLAUDE.md), with the fail-closed note — and names the four bounded subagents (initializer, implementer, verifier, research); string/presence assertion.
4. The bounded-execution and self-correction note is present: iteration/token/no-progress caps routing to HANDOFF (terminal, distinct from COMPLETE), and the self-audit reference to finding and fixing the HANDOFF infinite-block defect; the hook honest-limit note (command-type, fail-closed, PostToolUse cannot undo an executed action, roster emerging/version-gated) renders as qualitative copy.
**Depends on:** CONTENT-05

### CONTENT-12 — Per-page metadata derived from on-page claims  ·  P1  ·  EARS: state
**User story:** As a search/social consumer, I want metadata that mirrors ledger-registered on-page claims, so that no off-page assertion escapes the guardrail.
**EARS:** WHILE building each route, the content system SHALL produce per-page metadata copy (title, meta description, OG/Twitter title and description, JSON-LD text) conforming to the Voice Spec and claims guardrail, and WHERE metadata asserts a capability it SHALL be identical in substance to an on-page ledger-registered claim with no number or comparison absent from the ledger.
**Acceptance criteria:**
1. Every metadata field passes the Voice Spec lint and the value-agnostic verification-tally denylist.
2. A consistency check asserts each substantive metadata claim maps to a claims-registry entry; a metadata number/comparison absent from the ledger fails the build.
**Depends on:** CONTENT-06

### CONTENT-13 — Canonical terminology, style sheet, and gate-verdict copy  ·  P1  ·  EARS: ubiquitous
**User story:** As a content maintainer, I want a single canonical terminology/style sheet that also owns gate-verdict copy, so that casing, brand usage, and verdict wording never drift.
**EARS:** The content system SHALL maintain the canonical terminology and style sheet (brand 'Autonomous Agent'; category 'the Autonomous SDLC Platform'; casing of fail-closed, closed loop, evidence record, governing invariant; machine-artifact token format) and SHALL own the canonical gate-verdict copy, including the single canonical gate-stage caption string — "The Stop hook holds the line locally; OPA/Conftest runs a zero-evidence policy at merge; a GitHub ruleset makes both required." — and all pages SHALL use these consistently without diluting synonyms; HOME-05, LOOP-17, and PAGE-01 SHALL reuse the canonical gate-stage caption verbatim from this source of truth. This style sheet SHALL also record the canonical six-stage loop order — intent → decompose → implement → verify → prove → gate (gate last) — as the authoritative ordering referenced by loop-rendering requirements.
**Acceptance criteria:**
1. A terminology-consistency linter fails the build on any disallowed synonym or casing variant of a governed term across all routes.
2. All gate-verdict strings render from this single style sheet (single-source assertion); no route hardcodes a verdict string outside it.
3. The canonical gate-stage caption string "The Stop hook holds the line locally; OPA/Conftest runs a zero-evidence policy at merge; a GitHub ruleset makes both required." is defined exactly once here, and HOME-05, LOOP-17, and PAGE-01 are asserted to render it byte-for-byte from this source (no inline literal in those requirements' components).
4. The style sheet records the canonical six-stage order intent → decompose → implement → verify → prove → gate (gate last); a build assertion fails if any consuming requirement renders the gate before verify or reorders the six stages.
**Depends on:** DS-07

### CONTENT-14 — 'Who it's for' module with anti-fabrication rule  ·  P1  ·  EARS: unwanted
**User story:** As a visitor in a regulated context, I want audience-description framing and zero fabricated social proof, so that the site stays honest.
**EARS:** The site SHALL render a 'Who it's for' module describing regulated and safety-critical delivery contexts in role/industry terms and SHALL NOT display any customer logo, testimonial, named adopter, or social-proof statistic that does not exist; IF no verifiable customer evidence exists, THEN the module SHALL use audience-description framing only and the logo-wall pattern SHALL remain unbuilt or empty-stated.
**Acceptance criteria:**
1. The module contains zero <img> logo nodes and zero named-adopter or testimonial strings (DOM and string assertion).
2. Any numeric social-proof claim is blocked unless backed by a claims-registry entry with verifiable status.
**Depends on:** CONTENT-06

### CONTENT-15 — Text equivalents for motion and machine content  ·  P0  ·  EARS: complex
**User story:** As an assistive-tech user, I want text equivalents for the closed-loop animation and evidence panels, so that all state is available without motion.
**EARS:** The content system SHALL provide text equivalents for all non-text and motion content — the Rive closed-loop centerpiece SHALL have a caption narrating intent->verify->prove->fail-closed-gate, the evidence/audit-trace panel SHALL have a textual summary, and every meaningful image SHALL have alt text — and WHERE a reduced-motion static fallback replaces an animation, the fallback SHALL carry a caption communicating the same product state.
**Acceptance criteria:**
1. A presence check fails the build if the Rive centerpiece lacks the four-state caption or the evidence panel lacks a text summary.
2. Every meaningful image has non-empty alt text and every reduced-motion fallback exposes a caption (DOM assertion across routes).
**Depends on:** DS-08, DS-09

### CONTENT-16 — Fail-closed pre-publish content gate  ·  P0  ·  EARS: unwanted
**User story:** As the release owner, I want one fail-closed pre-publish gate composing every content check, so that nothing ships on a 'looks fine' override.
**EARS:** The content system SHALL enforce a fail-closed pre-publish content gate running the Voice Spec lint, reading-level budget, claims-ledger verification, terminology-consistency check, CTA-allowlist check, and text-equivalent presence check across all routes, and IF any check fails THEN the build SHALL fail and the offending claim/term/string SHALL be reported with page and location; the gate SHALL be computed from these verifiable checks only and SHALL NOT pass on a manual override.
**Acceptance criteria:**
1. Removing any single gated check, or introducing one violation per check, causes a non-zero build exit with a report naming page and location.
2. No code path lets the gate pass when any sub-check fails (no override flag); a forced-override attempt is asserted to still fail.
**Depends on:** CONTENT-01, CONTENT-06, CONTENT-08, CONTENT-09, CONTENT-13, CONTENT-15

### CONTENT-17 — Integrator thesis present, displacement language absent  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor, I want the hero and manifesto to carry the integrator thesis and avoid 'replaces the tools' framing, so that the position is honest about standing on proven Tier-1 tools.
**EARS:** The hero and manifesto SHALL carry the integrator thesis — "Every one of these problems is already solved — by Claude Code, Neon, Langfuse, Playwright, Semgrep, and a dozen other proven Tier-1 tools. What no one has done is wire them all together, gate them correctly, and ship it as a product." — framed as a design intent (the integrated product is not presented as production-proven), and SHALL contain no competitor-displacement or "replaces the tools" language. The in-scope wired-together stack named here SHALL be Claude Code, Neon, Langfuse, Playwright, and Semgrep; Temporal SHALL be named only as an OPTIONAL durable-execution substrate on the roadmap (Phase-5) and SHALL NOT be listed among the wired-together in-scope tools.
**Acceptance criteria:**
1. A copy-lint asserts the integrator thesis string is present in the hero copy deck and manifesto §1 (exact-match presence), with the in-scope stack listing Claude Code, Neon, Langfuse, Playwright, and Semgrep.
2. The displacement-phrase denylist (e.g. 'replaces the tools', 'replaces Claude Code', 'kills <tool>', 'better than <tool>') matches zero occurrences across all routes.
3. Temporal is referenced only as an OPTIONAL / roadmap (Phase-5) durable-execution substrate and is not enumerated among the wired-together in-scope tools; the framing presents the integrated product as a design intent, not a production-proven claim.
**Depends on:** CONTENT-01, CONTENT-11

### CONTENT-18 — 'Powered by' module as machine artifacts  ·  P1  ·  EARS: ubiquitous
**User story:** As a visitor, I want a 'Powered by' module listing the proven in-production stack as machine artifacts, so that I see credibility without fabricated logos or stats.
**EARS:** The site SHALL render a "Powered by — built on proven, in-production solutions" module presenting the stack as machine artifacts (no customer logos, no unverifiable stats) as the claims-integrity-safe substitute for a logo-wall, and each manifest entry SHALL render the tool name (mono `[data-artifact]`) together with its B-block ID and a one-line qualitative pain-point tie-in drawn from the claims registry. Where Claude Code hooks are named, the module SHALL co-state the hook honest-limit: Claude Code hooks are command-type and fail closed; PostToolUse cannot undo an executed action; the hook roster is emerging/version-gated.
**Acceptance criteria:**
1. The <PoweredBy> module renders each tool as a mono [data-artifact] entry sourced from the committed PRD stack manifest; every listed tool is asserted to be a member of that manifest.
2. The module contains zero logo <img> nodes and zero numeric stat strings (DOM and numeric-scan assertion).
3. Each manifest entry renders three parts: the tool name in a mono `[data-artifact]` node, its B-block ID, and a one-line qualitative pain-point tie-in sourced from the claims registry (assertion that all three are present per entry, with no numeric stat in the tie-in).
4. The required manifest membership names the six official Claude Code hooks (PreToolUse, PostToolUse, Stop, SubagentStop, PreCompact, SessionStart); the four subagents (initializer, implementer, verifier, research); OWASP ZAP; DeepEval; OpenFeature/flagd; gitleaks; and Hypothesis — each asserted present as a manifest member.
5. Wherever Claude Code hooks are named, the hook honest-limit note (command-type, fail-closed, PostToolUse cannot undo an executed action, roster emerging/version-gated) renders as qualitative copy; the module carries zero logos and zero numeric stats.
**Depends on:** CONTENT-06, DS-07

### CONTENT-19 — Vendor-neutral schema and no-lock-in promise  ·  P1  ·  EARS: ubiquitous
**User story:** As an evaluator wary of lock-in, I want the vendor-neutral schema and 'opinionated defaults, not a cage' promise stated, so that I trust the platform is portable.
**EARS:** The site SHALL state the vendor-neutral schema (feature_list.json + EvidenceRecord + requirement-ID Baggage) and the "opinionated defaults, not a cage" no-lock-in promise on /how-it-works and in the manifesto.
**Acceptance criteria:**
1. A copy-presence check asserts the no-lock-in block (naming feature_list.json, EvidenceRecord, requirement-ID Baggage) renders on /how-it-works and in the manifesto.
2. The no-lock-in claim resolves to a claims-registry entry with a corpus citation (claims-ledger citation check passes).
**Depends on:** CONTENT-06, IA-03

---

## Supporting Pages — PAGE

### PAGE-01 — Closed delivery loop on /how-it-works  ·  P0  ·  EARS: event
**User story:** As a prospective reader, I want the /how-it-works page to explain the delivery loop as an ordered, named sequence of stages, so that I understand how intent becomes proven, gated delivery.
**EARS:** The /how-it-works page SHALL present the closed delivery loop as an ordered, named sequence of stages in canonical order — intent, decompose, implement, verify, prove, fail-closed gate (gate last) — each with a one-paragraph plain-language explanation, the deterministic mechanism behind it (naming ≥1 concrete mechanism from the controlled vocabulary below), and the machine artifact it produces; WHEN a visitor reaches the gate stage, the page SHALL frame the fail-closed rejection as the system holding the line (succeeding), not as an error. The controlled mechanism vocabulary per stage is — intent → EARS → SMT spec compiler + spec_validator; decompose → the initializer subagent + a default-unproven feature_list.json (spec-compilation folds into decompose); implement → the implementer subagent + a git worktree + the ordered PreToolUse plan/scope gates; verify → the verifier subagent (five layers) + the SubagentStop evidence gate; prove → the four-field Evidence_Record + a hash-chained audit log + the Z3 logic model; gate → the Stop hook + OPA/Conftest + a GitHub ruleset. The page SHALL also name the STRICT SEQUENCING — the ordered PreToolUse gate chain, and that the Stop hook evaluates HANDOFF triggers BEFORE the unproven-items gate. Where the gate-stage caption is shown it SHALL reuse the canonical gate-stage caption verbatim from CONTENT-13. Claude Code hooks are command-type and fail closed; PostToolUse cannot undo an executed action; the hook roster is emerging/version-gated.
**Acceptance criteria:**
1. The page DOM contains exactly six ordered stage nodes whose accessible names match `intent`, `decompose`, `implement`, `verify`, `prove`, and a gate stage, in that canonical document order (gate last; a build assertion fails if any stage places the gate before verify).
2. Each stage node contains a non-empty plain-language paragraph, a mechanism description, and a machine-artifact reference rendered with monospace styling only on a `[data-artifact]` node.
3. A build assertion verifies that each of the six stages names ≥1 mechanism from its controlled-vocabulary set (intent → EARS/SMT spec compiler + spec_validator; decompose → initializer subagent + default-unproven feature_list.json; implement → implementer subagent + git worktree + ordered PreToolUse plan/scope gates; verify → verifier subagent (five layers) + SubagentStop evidence gate; prove → four-field Evidence_Record + hash-chained audit log + Z3 logic model; gate → Stop hook + OPA/Conftest + GitHub ruleset); the page also names the strict sequencing (the ordered PreToolUse gate chain, and that the Stop hook evaluates HANDOFF triggers before the unproven-items gate).
4. The gate-stage copy contains the canonical gate-stage caption sourced verbatim from CONTENT-13 (no inline literal) and contains no error/failure-toned wording asserted by text-equality against the approved CONTENT-13 verdict copy; wherever Claude Code hooks are named, the hook honest-limit note (command-type, fail-closed, PostToolUse cannot undo an executed action, roster emerging/version-gated) renders as qualitative copy.
5. axe-core reports zero critical OR serious violations for the rendered stage sequence.
**Depends on:** DS-08, CONTENT-13, PAGE-13

### PAGE-02 — Capability taxonomy B01-B19  ·  P1  ·  EARS: state
**User story:** As a reader, I want the 19 capability blocks grouped into clusters, so that I can grasp the platform's capability surface at a glance.
**EARS:** WHERE the capability taxonomy is present, the /how-it-works page SHALL render the 19 capability blocks (B01-B19) grouped into a small set of capability clusters (specify, cover, execute, verify, prove, observe), each block carrying a short label, a one-line description that names its signature mechanism, and its block ID as a monospace artifact. Each block's one-line description SHALL name its signature mechanism qualitatively — e.g. B09 = "fail-closed completion gate: Stop hook + OPA/Conftest + GitHub ruleset"; B12 = "mid-flight steering: PreToolUse prevention + PostToolUse feedback"; B13 = "anti-loopmaxxing: iteration/token/no-progress caps routing to HANDOFF"; B16 = "security/control: SAST + secrets + SLSA + DAST + kill-switch". Where Claude Code hooks are named, the taxonomy SHALL co-state the hook honest-limit: Claude Code hooks are command-type and fail closed; PostToolUse cannot undo an executed action; the hook roster is emerging/version-gated.
**Acceptance criteria:**
1. The page renders exactly 19 block nodes whose IDs text-match `B01` through `B19` with no gaps or duplicates.
2. Each block ID is the only monospace-rendered text in its block and sits on a `[data-artifact]` node; assert no other descendant uses the mono font.
3. Every block is assigned to exactly one of the named clusters; assert each block node has a non-empty cluster ancestor and no block is orphaned.
4. Each block's one-line description names its signature mechanism (build assertion that the description is non-empty and mechanism-bearing); B09, B12, B13, and B16 match their canonical signature-mechanism strings (fail-closed completion gate: Stop hook + OPA/Conftest + GitHub ruleset; mid-flight steering: PreToolUse prevention + PostToolUse feedback; anti-loopmaxxing: iteration/token/no-progress caps routing to HANDOFF; security/control: SAST + secrets + SLSA + DAST + kill-switch).
5. Wherever Claude Code hooks are named in a block description, the hook honest-limit note (command-type, fail-closed, PostToolUse cannot undo an executed action, roster emerging/version-gated) renders as qualitative copy.
**Depends on:** PAGE-01

### PAGE-03 — /proof information spine  ·  P0  ·  EARS: ubiquitous
**User story:** As a skeptical reader, I want the /proof page to lay out the governing invariant, evidence schema, verifier principle, and auditor test, so that I can evaluate the proof claim on its mechanism.
**EARS:** The /proof page SHALL present, in order, the governing invariant (deterministic gates decide completeness from verifiable facts only; model self-assessment informs but never gates), the four-field evidence schema (test_file, test_name, output_hash, collected_at), the independent-verifier principle (the verifier has no write access and never grades its own output), and the auditor test (the north-star question), each as a distinct titled section. The page SHALL clarify qualitatively that the hash-chained log is tamper-evident proof that execution happened as recorded (proof of execution) — distinct from proof that generated code is correct (proof of correctness), which is out of scope — and that the Z3 logic model checks the requirement logic model, not generated code.
**Acceptance criteria:**
1. The page DOM contains four distinct titled sections in the specified document order; assert by heading text and ordinal position.
2. The evidence-schema section lists exactly the four field names `test_file`, `test_name`, `output_hash`, `collected_at`, each on a `[data-artifact]` mono node and no other field present.
3. The page text contains no hardcoded verification count; the denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` matches zero times against rendered text.
4. The page states qualitatively that the hash-chained log is proof of execution (tamper-evident proof that execution happened as recorded), distinct from proof of correctness (that generated code is correct, which is out of scope), and that Z3 checks the requirement logic model rather than generated code; string/presence assertion.
**Depends on:** DS-01, CONTENT-06

### PAGE-04 — Interactive sample audit-trace  ·  P0  ·  EARS: event
**User story:** As a reader, I want to step through a hash-chained execution trace, so that I can see how a feature moves from unproven to proven and how the gate evaluates.
**EARS:** WHEN a visitor activates the sample audit-trace component, the component SHALL render a monospaced, requirement-ID-tagged, hash-chained execution trace for a fictional-but-realistic feature and SHALL allow the visitor to advance one step at a time through states unproven → evidence-attached → proven and to a final fail-closed gate evaluation; WHILE the trace is at the gate step with any item still unproven, the component SHALL show the gate holding (closed) in the `--proven` accent color and SHALL NOT mark the run COMPLETE.
**Acceptance criteria:**
1. Activating the component then advancing emits trace rows tagged with requirement IDs, each row's hash field rendered on a `[data-artifact]` mono node; assert hash N's input references hash N-1 (chain).
2. Stepping transitions a tracked item through accessible states `unproven`, `evidence-attached`, `proven` in that order, assertable via `aria`/`data-state` attributes.
3. At the gate step with ≥1 unproven item, the gate node's resolved color equals the `--proven` token value (#34E1A0) and the DOM contains no node with text `COMPLETE` for the run.
4. The component is keyboard-operable end to end (Tab/Enter/Space advance) with a visible focus ring; assert via keyboard-only driver.
**Depends on:** DS-08, PAGE-05, LOOP-05

### PAGE-05 — Audit-trace accessibility and no-JS fallback  ·  P0  ·  EARS: state
**User story:** As a keyboard or no-JS user, I want the audit-trace to be fully operable or render a complete static outcome, so that the proof is accessible without interaction.
**EARS:** The sample audit-trace component SHALL be fully keyboard-operable, and WHERE the user has set prefers-reduced-motion or has JavaScript disabled, the component SHALL render a complete static labeled trace showing the final proven/unproven/gate-held outcome without requiring step interaction.
**Acceptance criteria:**
1. With JavaScript disabled, the rendered DOM already contains the full labeled trace and a final gate-held outcome node; assert presence without any event dispatch.
2. Under `prefers-reduced-motion: reduce`, no element on the component has a non-zero CSS transition/animation duration; assert computed styles.
3. axe-core reports zero critical OR serious violations in both the interactive and static-fallback renderings.
**Depends on:** DS-09, PAGE-04

### PAGE-06 — /manifesto MDX essay  ·  P0  ·  EARS: ubiquitous
**User story:** As a reader, I want a long-form manifesto essay with a clear thesis and structure, so that I understand the worldview behind the platform.
**EARS:** The /manifesto page SHALL render a long-form editorial essay authored in MDX, structured as numbered sections with a clear thesis, the problem (the fragmented AI-tooling stack and human-as-infrastructure), the wedge (proof: autonomy and specs are owned, verification is not), the governing invariant, and a forward-looking close, using blueprint hairline rules and generous editorial typography.
**Acceptance criteria:**
1. The page renders ≥5 numbered section headings in ascending order; assert heading numbers are sequential with no gaps.
2. Display headings use a font-weight in the range 300–600 inclusive; assert computed `font-weight` on each display heading.
3. The page text contains no hardcoded verification count; the denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` matches zero times.
**Depends on:** DS-01, CONTENT-06, PAGE-14

### PAGE-07 — Manifesto reading aids  ·  P1  ·  EARS: state
**User story:** As a reader of a long essay, I want a reading-progress indicator and copyable section anchors, so that I can track position and link to sections.
**EARS:** WHILE a visitor scrolls the /manifesto essay, the page SHALL display a non-decorative reading-progress and section-position indicator derived from real scroll position, and each numbered section heading SHALL expose a copyable anchor link.
**Acceptance criteria:**
1. Scrolling the essay updates the progress indicator's value monotonically with scroll position; assert at 0%, 50%, and 100% scroll the reported value increases.
2. Each numbered section heading exposes an anchor control whose activation places a same-page URL with the section's `#id` on the clipboard or address bar; assert resolved href targets an existing element ID.
3. The progress indicator is keyboard-reachable or exposed via an `aria` live/progress role; assert non-decorative semantics (not `aria-hidden`).
**Depends on:** PAGE-06

### PAGE-08 — No unverifiable quantitative claims  ·  P0  ·  EARS: unwanted
**User story:** As a trust-sensitive reader, I want supporting pages to never publish unverifiable counts, so that every claim is accurate and corpus-backed.
**EARS:** The supporting pages SHALL NOT publish any specific count of formally verified requirements or any other quantitative claim that is not currently corrected and verifiable in the corpus; WHERE a quantitative verification figure would otherwise appear, the page SHALL instead describe the mechanism (deterministic gates, machine-checked assertions, evidence schema) in qualitative, accurate terms.
**Acceptance criteria:**
1. Across all supporting-page rendered text, the denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` matches zero times (value-agnostic).
2. Every quantitative claim that does appear resolves to a key present in `content/claims-registry.json`; assert no rendered claim string is absent from the registry.
3. The build fails (non-zero exit) if any supporting page introduces a claim not present in `content/claims-registry.json`.
**Depends on:** CONTENT-06

### PAGE-09 — /writing index  ·  P2  ·  EARS: optional
**User story:** As a reader, I want a dated index of writing when enabled, so that I can browse articles or understand the section's purpose when empty.
**EARS:** WHERE the /writing route is enabled, the page SHALL render an index of MDX articles ordered by date with title, date, and reading time; IF no articles are published, THEN the page SHALL render an intentional empty state describing the writing's purpose rather than a broken or blank list.
**Acceptance criteria:**
1. When ≥1 article exists, the index lists entries sorted descending by date; assert each entry exposes title, ISO date, and reading-time text and order is non-increasing by date.
2. When zero articles exist, the page renders a non-empty purpose-describing empty-state node and contains no broken/empty list element.
3. axe-core reports zero critical OR serious violations in both populated and empty states.
**Depends on:** IA-03, PAGE-14, PAGE-16

### PAGE-10 — /docs honest placeholder  ·  P1  ·  EARS: ubiquitous
**User story:** As a developer, I want the /docs page to honestly state docs are forthcoming, so that I am not misled by dead or fabricated links.
**EARS:** The /docs page SHALL render an explicit placeholder state communicating that developer documentation is forthcoming, WITHOUT presenting fabricated or dead documentation links, and SHALL offer a soft Get-notified affordance only.
**Acceptance criteria:**
1. The page contains a placeholder node whose text communicates docs are forthcoming; assert presence by text.
2. The page contains zero anchor elements pointing to non-existent/dead doc routes; assert every in-page href resolves to a live route or external 200, and no fabricated doc links exist.
3. The only conversion affordance present is the single Get-notified capture; assert no pricing, demo, or sales-contact controls in the DOM.
**Depends on:** IA-12, PAGE-16

### PAGE-11 — Soft onward navigation, no funnel  ·  P1  ·  EARS: ubiquitous
**User story:** As a reader, I want soft links between supporting pages and a single optional email capture, so that I can explore without a sales funnel.
**EARS:** Each supporting page SHALL provide soft onward navigation to the other supporting pages and to the manifesto, and the only conversion affordance available site-wide SHALL be an optional Get-notified email capture; the pages SHALL NOT contain pricing, demo-booking, or sales-contact actions.
**Acceptance criteria:**
1. Each supporting page exposes onward links resolving to other supporting routes and to /manifesto; assert each href targets a route in the IA route manifest.
2. Each page contains at most one Get-notified capture and zero pricing/demo/sales-contact controls; assert by control inventory.
3. All onward-nav controls are keyboard-operable with visible focus; assert via keyboard-only driver.
**Depends on:** IA-03, IA-12

### PAGE-12 — Motion as bound state, reduced-motion parity  ·  P0  ·  EARS: state
**User story:** As any visitor, I want animations to be bound to real product/UI state and to degrade gracefully, so that motion conveys information, never decoration.
**EARS:** WHERE any supporting page animates an element, that animation SHALL be a state machine bound to a real product or UI state (e.g. trace step proven, coverage filled, gate held), and WHEN prefers-reduced-motion is set, the element SHALL present the same state information without continuous or easing-based motion.
**Acceptance criteria:**
1. Every animated element exposes a `data-state` (or equivalent) attribute whose value drives the visual; assert no animation runs without a bound state attribute.
2. Under `prefers-reduced-motion: reduce`, all such elements have zero-duration transitions/animations yet retain the same `data-state`-derived label; assert computed styles and text parity.
3. Each animation's registry entry resolves to DS-08 (the single motion registry); assert no inline ad-hoc keyframes outside the DS-08 registry.
**Depends on:** DS-08, DS-09

### PAGE-13 — Tier-1 non-functional baseline  ·  P0  ·  EARS: ubiquitous
**User story:** As any visitor, I want supporting pages to meet performance, a11y, SEO, and security budgets, so that the site is fast, accessible, and trustworthy.
**EARS:** Each supporting page SHALL meet defined Core Web Vitals, WCAG 2.2 AA, responsive, structured-data, and security-header budgets, and SHALL apply the design-token system and self-hosted fonts consistently.
**Acceptance criteria:**
1. Lab Core Web Vitals meet thresholds: LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms; assert via Lighthouse CI run.
2. axe-core reports zero critical OR serious violations on every supporting page at mobile and desktop breakpoints.
3. Required security headers are present (CSP, X-Content-Type-Options, Referrer-Policy, HSTS) and a valid JSON-LD block parses on each page; assert response headers and schema validation.
4. All color and type values resolve to DS tokens (single source of truth) and fonts are served same-origin; assert no off-token hardcoded hex and no third-party font requests.
**Depends on:** DS-01, DS-07, PAGE-05, PAGE-12

### PAGE-14 — MDX brand-component allowlist  ·  P1  ·  EARS: unwanted
**User story:** As a content maintainer, I want MDX to render only allowlisted brand components, so that authored content cannot inject arbitrary or unsafe markup.
**EARS:** The supporting-pages content pipeline SHALL render manifesto and writing content from MDX through a fixed allowlist of brand components (pull-quote, inline evidence chip, numbered-section heading, blueprint rule), and SHALL reject or ignore any component or raw markup outside that allowlist.
**Acceptance criteria:**
1. MDX containing a non-allowlisted component or raw HTML element causes the build to fail or strips it; assert the rendered DOM contains zero non-allowlisted custom elements.
2. Each allowlisted component renders with its expected role/semantics; assert presence of pull-quote, evidence-chip, numbered-heading, and blueprint-rule nodes from a fixture.
3. Raw `<script>`/event-handler attributes in MDX never reach the DOM; assert zero inline scripts/handlers from authored content.
**Depends on:** PAGE-06

### PAGE-15 — Audit-trace explicit state set  ·  P1  ·  EARS: complex
**User story:** As a reader, I want the audit-trace to handle loading, ready, error, and static states, so that I always see a legible proof concept, never a broken widget.
**EARS:** The sample audit-trace component SHALL define and render explicit loading, ready, error, and reduced/static states; IF the sample trace data fails to load or is malformed, THEN the component SHALL render a legible fallback summary of the proof concept rather than an empty or broken widget.
**Acceptance criteria:**
1. Each of loading, ready, error, and static states renders a distinct identifiable node; assert by `data-state` value across forced conditions.
2. When trace data is forced to fail or be malformed, the component renders a non-empty fallback summary node and no empty/broken container; assert text presence and absence of unhandled error.
3. The error and fallback states pass axe-core with zero critical OR serious violations.
**Depends on:** PAGE-04, PAGE-05

### PAGE-16 — Branded not-found and feature-flag absence  ·  P1  ·  EARS: event
**User story:** As a visitor hitting a disabled or missing route, I want a branded not-found with soft navigation, so that I can return to live pages without dead ends.
**EARS:** WHEN a visitor requests a supporting route that is disabled or non-existent, the site SHALL serve a branded not-found/placeholder response with soft navigation back to live pages, and feature-flagged routes (writing, docs) SHALL either render their intended state or be fully absent with their nav entries removed.
**Acceptance criteria:**
1. Requesting a non-existent supporting route returns a branded 404 view containing soft-nav links that each resolve to a live route in the IA route manifest.
2. When a feature flag is off, the flagged route is fully absent (404) AND its nav entry is removed from the rendered navigation; assert no orphan nav link.
3. axe-core reports zero critical OR serious violations on the branded not-found view.
**Depends on:** IA-03, IA-12

### PAGE-17 — Print-friendly /manifesto and /proof  ·  P1  ·  EARS: state
**User story:** As a reader who prints or saves to PDF, I want /manifesto and /proof to render in a legible light theme with full hashes and no decorative motion, so that the printed artifact is readable and complete.
**EARS:** WHERE @media print, /manifesto and /proof SHALL switch to a legible light theme, expand truncated hashes to their full value, and hide decorative canvas/motion elements.
**Acceptance criteria:**
1. Under print emulation, the page background resolves to a light color and body text to a dark color meeting WCAG 2.2 AA contrast; assert computed colors in the print media context.
2. Under print emulation, every `[data-artifact]` hash node renders its full (non-truncated) value; assert printed hash text equals the source hash and contains no ellipsis/truncation marker.
3. Under print emulation, decorative canvas/motion elements are not displayed; assert `display:none` (or absent) for nodes marked decorative and zero animation duration.
**Depends on:** DS-01, DS-07, PAGE-06, PAGE-03

---

## Tech Stack & Front-end Architecture — TECH

### TECH-01 — App Router shape with route group and colocated segment files  ·  P0  ·  EARS: complex
**User story:** As a front-end engineer, I want every public route to live under one App Router route group with colocated failure/loading files, so that the site has a predictable, fail-safe structure.
**EARS:** The front-end application SHALL be built on Next.js App Router with all routes under a single `app/(site)/` route group, each content route (`/`, `/how-it-works`, `/proof`, `/manifesto`, `/writing`, `/docs`, plus `/privacy` and `/terms`) implemented as a `page.tsx` segment with shared chrome in a single root `layout.tsx`; WHERE a route segment can fail, render slowly, or return no content, the application SHALL colocate `error.tsx`, `loading.tsx`, and (where applicable) `not-found.tsx` with that segment.
**Acceptance criteria:**
1. A typed route manifest in `lib/routes.ts` (IA single source of truth) enumerates exactly `/`, `/how-it-works`, `/proof`, `/manifesto`, `/writing`, `/docs`, `/privacy`, `/terms`; a build-time test asserts each listed content route resolves to a `page.tsx` under `app/(site)/` and no `page.tsx` exists outside the manifest.
2. A test asserts every route-group directory containing a `page.tsx` also contains `error.tsx` and `loading.tsx`, and that dynamic collection segments contain `not-found.tsx`; the assertion runs in CI and fails the build on a missing file.
**Depends on:** IA-03, IA-12

### TECH-02 — Strict TypeScript with first-class machine-artifact contracts  ·  P0  ·  EARS: unwanted
**User story:** As a maintainer, I want strict typing with explicit machine-artifact shapes, so that no untyped data or type error can reach production.
**EARS:** The application SHALL compile under TypeScript `strict` with `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` enabled and SHALL define explicit types for the evidence-record shape (`{ test_file: string; test_name: string; output_hash: string; collected_at: string }`), requirement-ID strings, loop-state-machine state names (including a `gate` state with sub-states), and MDX frontmatter; IF any type error exists, THEN the production build SHALL fail.
**Acceptance criteria:**
1. `tsconfig.json` sets `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`; a deliberately-introduced type error causes `next build` (which runs `tsc --noEmit`) to exit non-zero in CI.
2. Exported typed shapes exist for `EvidenceRecord` (exact four fields above), a `RequirementId` branded/string-literal type, a `LoopState` union whose members are `intent | decompose | implement | verify | prove | gate` with `gate` carrying a typed sub-state union, and a Zod-derived `MdxFrontmatter` type; a type-level test (`tsd`/`expect-type`) asserts each shape compiles and rejects malformed values.
**Depends on:** none

### TECH-03 — Tailwind v4 themed solely from Style-Dictionary tokens  ·  P0  ·  EARS: complex
**User story:** As a designer-developer, I want Tailwind driven entirely by Style-Dictionary-emitted CSS variables, so that tokens are the single source of truth for color, type, and accent.
**EARS:** The application SHALL use Tailwind CSS v4 with its theme configured exclusively from CSS custom properties emitted by Style Dictionary from `design/tokens/*.json`, exposing semantic tokens `--canvas`, `--surface`, `--surface-2`, `--border`, `--text`, `--text-muted`, `--text-faint`, `--proven`, `--pending`, and a canonical `--error` token, plus Sans and Mono family tokens; WHERE a component renders a machine artifact (requirement ID, evidence record, hash, gate verdict), it SHALL apply the mono token, and WHERE a component needs the brand accent, it SHALL reference `--proven` only.
**Acceptance criteria:**
1. The Tailwind v4 theme block references only `var(--…)` custom properties; a test parses the generated CSS and asserts the presence of all ten semantic tokens (`--canvas`, `--surface`, `--surface-2`, `--border`, `--text`, `--text-muted`, `--text-faint`, `--proven`, `--pending`, `--error`) sourced from the Style Dictionary build output, and fails if any literal hex color appears in component styles.
2. A static check asserts every element matching `[data-artifact]` resolves to the mono font token, and a lint rule fails the build if any accent color other than `--proven` is referenced.
**Depends on:** DS-01, DS-07

### TECH-04 — Build-time MDX pipeline with allow-listed components and typed frontmatter  ·  P1  ·  EARS: unwanted
**User story:** As a content engineer, I want MDX compiled at build time with a fixed component allow-list and validated frontmatter, so that prose cannot inject arbitrary components or ship malformed metadata.
**EARS:** The application SHALL render `/manifesto` and `/writing/[slug]` content from MDX files in `content/`, compiled at build time with a fixed allow-list of MDX components (numbered sections, blueprint rules, pull-quotes, `<EvidenceRecord>`, `<RequirementId>`) and typed, schema-validated frontmatter; IF an MDX file references a component outside the allow-list or fails frontmatter validation, THEN the build SHALL fail.
**Acceptance criteria:**
1. The MDX compile config registers exactly the allow-listed components; a fixture MDX referencing an unlisted component causes the build to exit non-zero.
2. Frontmatter is validated against a Zod schema during build; a fixture with missing/invalid frontmatter fields fails validation and aborts the build with a typed error naming the offending file.
**Depends on:** none

### TECH-05 — Rive integration boundary: lazy, SSR-disabled, CLS-safe wrapper  ·  P0  ·  EARS: complex
**User story:** As a performance engineer, I want the Rive centerpiece isolated in one lazy client boundary with a reserved container, so that it never causes layout shift or SSR cost.
**EARS:** The application SHALL integrate the Rive centerpiece via `@rive-app/react-canvas` inside a single client-boundary wrapper (`components/loop/ClosedLoop.tsx`) dynamically imported with SSR disabled, lazy-loaded when the hero approaches the viewport, and rendered in a reserved fixed-aspect container; WHILE the `.riv` asset is loading, the wrapper SHALL show the static labeled-diagram fallback in the reserved space so that no cumulative layout shift occurs.
**Acceptance criteria:**
1. `ClosedLoop` is imported via `next/dynamic` with `{ ssr: false }` and gated by an IntersectionObserver; a test asserts the module is not present in the server-rendered HTML and is requested only after the hero intersects.
2. A measured CLS check (Lighthouse/web-vitals in CI) asserts CLS ≈ 0 (≤ 0.01) for the hero, and a unit test asserts the reserved container has a fixed aspect-ratio and renders the static fallback before the `.riv` resolves.
**Depends on:** PAGE-03, LOOP-05

### TECH-06 — Motion-as-information contract: Rive vs Framer Motion split  ·  P0  ·  EARS: unwanted
**User story:** As a product owner, I want every animation to map to a real product state via a registry, so that motion communicates information and never decorates.
**EARS:** The application SHALL restrict Rive to the hero closed-loop state machine and any secondary product-state visual, and SHALL restrict Framer Motion to informational micro-interactions whose animated state maps to a real product state registered in `lib/motion/registry.ts`; WHERE a motion does not communicate a registered product state, the application SHALL NOT animate it.
**EARS:** WHERE a motion does not map to a registered product state in `lib/motion/registry.ts`, the application SHALL NOT animate it.
**Acceptance criteria:**
1. A typed `motionRegistry` in `lib/motion/registry.ts` (the DS-08 motion-intent registry, imported by TECH) maps each animation id to a product-state enum value; a test asserts every Framer Motion usage references a registry id and fails the build on an unregistered animation.
2. A static check asserts Rive is instantiated only inside `components/loop/` (hero loop and secondary product-state visuals) and nowhere else.
**Depends on:** DS-08, DS-09

### TECH-07 — Reduced-motion and accessibility fallback strategy  ·  P0  ·  EARS: event
**User story:** As a motion-sensitive visitor, I want a static, fully-labeled fallback when I request reduced motion, so that I get the same information without animation.
**EARS:** WHEN the user agent reports `prefers-reduced-motion: reduce`, the application SHALL render the closed loop as a static fully-labeled diagram conveying the same intent→decompose→implement→verify→prove→gate sequence, SHALL freeze Framer Motion micro-interactions to their final informational state, and SHALL NOT autoplay the Rive timeline; the static fallback SHALL expose text equivalents for all machine artifacts.
**Acceptance criteria:**
1. A Playwright test with `prefers-reduced-motion: reduce` emulated asserts the Rive timeline never autoplays, all Framer Motion elements render at their final state, and the static labeled diagram is in the DOM with text equivalents for each loop stage.
2. The static fallback exposes every machine artifact (stage names, gate verdict) as selectable text; an automated DOM assertion confirms no artifact is image-only under reduced motion.
**Depends on:** DS-08, DS-09

### TECH-08 — Rendering strategy: SSG by default, ISR for MDX, dynamic forbidden  ·  P0  ·  EARS: unwanted
**User story:** As an SRE, I want marketing routes statically generated and MDX routes on bounded ISR, so that no marketing route opts into per-request rendering.
**EARS:** The application SHALL statically render (SSG) all marketing routes at build time and SHALL apply ISR only to MDX-backed content routes (`/manifesto`, `/writing`, `/writing/[slug]`) via a bounded revalidation window; WHERE a route has no per-request dynamic data, the application SHALL NOT opt into dynamic (per-request) rendering.
**Acceptance criteria:**
1. A test inspects the build manifest and asserts every route in `lib/routes.ts` is `static` or `ISR`, and that no segment exports `dynamic = 'force-dynamic'` or uses request-time APIs; a violating route fails the build.
2. MDX content routes export a finite numeric `revalidate`; a test asserts the value is set and bounded (> 0 and ≤ a configured maximum).
**Depends on:** IA-03

### TECH-09 — Error/loading/empty-state system with segment boundaries  ·  P0  ·  EARS: unwanted
**User story:** As a visitor, I want failures contained to on-brand fallbacks, so that a thrown component or failed asset never crashes the page.
**EARS:** The application SHALL wrap the Rive centerpiece and any client data-dependent region in React error boundaries that render the on-brand static fallback, and SHALL provide segment-level `error.tsx` for every route group; IF a client component throws or an asset fails to load, THEN the boundary SHALL contain the failure, render a legible fallback styled from `--error`/`--surface`, and report the error without crashing the rest of the page.
**Acceptance criteria:**
1. A test forces `ClosedLoop` to throw and asserts the surrounding error boundary renders the static labeled-diagram fallback while the rest of the page remains interactive.
2. A test asserts each route group has an `error.tsx` whose rendered output references the `--error` token and includes an error-reporting hook; a forced `.riv` load failure is shown to render the fallback and log the error.
**Depends on:** PAGE-03, LOOP-05

### TECH-10 — Route-level loading skeletons and intentional empty states  ·  P1  ·  EARS: state
**User story:** As a visitor, I want token-styled skeletons and purposeful empty states, so that loading and empty collections never look broken.
**EARS:** WHILE content is loading, the application SHALL show a route-level `loading.tsx` token-styled skeleton matching final layout dimensions; WHEN a collection (e.g. `/writing`) has zero published items, the application SHALL render an intentional empty state rather than a blank list.
**Acceptance criteria:**
1. A test asserts the `/writing` skeleton uses token classes and its bounding dimensions match the loaded layout within a tolerance, so no layout shift occurs on resolve.
2. A test renders `/writing` with an empty content set and asserts a purpose-written empty-state component (not a blank `<ul>`) is shown, with copy and a token-styled container.
**Depends on:** IA-12

### TECH-11 — Responsive layout and centerpiece degradation 320px → ultra-wide  ·  P0  ·  EARS: complex
**User story:** As a mobile visitor, I want the layout and centerpiece to stay legible from 320px up, so that stages and artifacts remain readable when the full animation would not.
**EARS:** The application SHALL implement a responsive layout from a 320px minimum width through ultra-wide using a max content container of ~1200–1280px, and SHALL degrade the Rive centerpiece to a clean labeled diagram below a defined breakpoint; WHERE viewport width is below the centerpiece breakpoint, the application SHALL prioritize legibility of stages and machine artifacts over animation fidelity.
**Acceptance criteria:**
1. Playwright tests at 320px, 768px, 1280px, and 1920px assert no horizontal overflow and that the content container width is clamped to the ~1200–1280px maximum.
2. A test at a width below the configured centerpiece breakpoint asserts the simplified labeled diagram (not the full Rive animation) is rendered with all stage labels legible.
**Depends on:** DS-01

### TECH-12 — Minimal, intentional state management with audited client boundaries  ·  P1  ·  EARS: optional
**User story:** As an architect, I want server-by-default state with narrowly-scoped client boundaries, so that interactivity stays minimal and no global state framework creeps in.
**EARS:** The application SHALL keep state on the server / in route segments by default and SHALL introduce client state only inside explicitly-marked `'use client'` boundaries for genuine interactivity; WHERE shared cross-component client state is required, the application SHALL use lightweight React context or a minimal store rather than a global app-wide state framework.
**Acceptance criteria:**
1. A static scan asserts `'use client'` appears only in files under an allow-listed set (Rive wrapper, scroll-progress, reduced-motion/theme context, form input) and fails the build on any other client-marked module.
2. A dependency check asserts no global state framework (e.g. Redux/MobX/Zustand-as-global-app-store) is in `package.json` dependencies; shared client state resolves to React context or a documented minimal store.
**Depends on:** none

### TECH-13 — Claims-integrity architecture: registry-backed, build-validated  ·  P0  ·  EARS: unwanted
**User story:** As an editor, I want every quantitative claim sourced from one validated registry with no hardcoded verification counts, so that the site never ships an unverifiable number.
**EARS:** The application SHALL treat every quantitative or verification claim rendered in the UI as data carrying a source reference resolved from a single `content/claims-registry.json`, validated at build; IF a claim is rendered without a resolvable source entry, THEN the build SHALL fail, and the application SHALL NOT hard-code any "N/N verified" count anywhere.
**Acceptance criteria:**
1. All rendered claims flow through a `<Claim>` component reading `content/claims-registry.json`; a build-time validator asserts every referenced claim id resolves to an entry with a source, and fails the build (non-zero exit) on any unresolved reference.
2. A CI scan applies the value-agnostic denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` across source, content, and rendered output and fails the build on any match, so no hardcoded "N/N verified" count can ship.
**Depends on:** CONTENT-06

### TECH-14 — Self-hosted variable fonts with zero-CLS swap and guaranteed mono  ·  P1  ·  EARS: state
**User story:** As a performance engineer, I want self-hosted display and mono fonts via next/font with metric-compatible fallbacks, so that fonts load without layout shift and artifacts always render mono.
**EARS:** The application SHALL self-host the display/body family (Geist Sans or Inter Variable) and the monospace family (Geist Mono / JetBrains Mono) via `next/font/local`, exposing them as CSS-variable font tokens with size-adjusted fallbacks and display weights spanning 300–600; WHILE web fonts are loading, the application SHALL avoid layout shift using `font-display: swap` with metric-compatible fallbacks, and machine artifacts SHALL always resolve to the mono family.
**Acceptance criteria:**
1. A test asserts fonts are declared via `next/font/local` (no external font-CDN requests at runtime), expose CSS-variable tokens consumed by the Tailwind theme, define size-adjusted/metric-compatible fallbacks, and that available display weights cover the 300–600 range.
2. A DOM test asserts every `[data-artifact]` node computes to the mono font family even before the web font resolves (fallback is mono-metric), and a web-vitals check confirms CLS attributable to font swap is ≈ 0.
**Depends on:** DS-01, DS-07

### TECH-15 — Hardened delivery: CSP scoped for Rive WASM + self-hosted fonts  ·  P0  ·  EARS: complex
**User story:** As a security engineer, I want strict security headers and a narrowly-scoped CSP, so that the Rive WASM and fonts run with the least privilege required and nothing broader.
**EARS:** The application SHALL emit security headers (strict Content-Security-Policy, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `frame-ancestors 'none'`) via middleware/edge config and SHALL serve Rive WASM and `.riv` assets under a CSP that permits `wasm-unsafe-eval` only as scoped as required; WHERE the CSP would block a required runtime (Rive WASM, self-hosted fonts), the policy SHALL grant the narrowest sufficient allowance and nothing broader.
**Acceptance criteria:**
1. An integration test fetches a page and asserts the response carries CSP, HSTS, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, and `frame-ancestors 'none'` headers with expected directive values.
2. A test parses the CSP and asserts `wasm-unsafe-eval` is present only where Rive requires it, that font/style sources are restricted to `'self'`, and that no wildcard (`*`) source appears in `script-src` or `style-src`.
**Depends on:** DS-07

### TECH-16 — Fail-closed CI verification harness for perf, a11y, and motion  ·  P0  ·  EARS: unwanted
**User story:** As a release manager, I want performance, accessibility, and motion-integrity gates enforced in CI, so that any regression blocks merge.
**EARS:** The application SHALL enforce, as required CI gates, performance budgets (Lighthouse performance/SEO/best-practices ≥ 95, LCP < 2.5s, CLS ≈ 0, bounded JS bundle), accessibility (axe-core zero critical, WCAG 2.2 AA contrast for `--proven` on `--canvas` and all text tokens, full keyboard operability), and motion integrity (every animation maps to a registered product state; reduced-motion fallbacks render); IF any budget is exceeded, THEN the merge SHALL be blocked.
**Acceptance criteria:**
1. CI runs Lighthouse (asserting performance/SEO/best-practices ≥ 95, LCP < 2.5s, CLS ≤ 0.01, JS bundle under a configured byte budget) and axe-core (zero critical violations, AA contrast computed for `--proven`-on-`--canvas` and each text token); any failure exits non-zero and blocks merge as a required check.
2. A motion-integrity check asserts every animation id resolves to an entry in `lib/motion/registry.ts` and that reduced-motion fallbacks render; the claims denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` is run as a required gate, and full keyboard operability is verified by an automated traversal test.
**Depends on:** DS-08, CONTENT-06

---

## Tooling, Pipeline & CI/CD — TOOL

### TOOL-01 — Single-source token pipeline (DS → CSS/Tailwind/TS)  ·  P0  ·  EARS: event
**User story:** As a maintainer, I want a single canonical token source compiled deterministically into all consumer formats, so that there is exactly one source of truth for design tokens and outputs never drift.
**EARS:** The token pipeline SHALL compile a single canonical token source (design/tokens/*.json governed by DESIGN.md, owned by DS) via Style Dictionary into (a) CSS custom properties on :root, (b) a Tailwind v4 @theme layer, and (c) a typed TypeScript token map. WHEN a token source file changes, the pipeline SHALL regenerate all three outputs deterministically from the same input. IF any generated output is committed in a state that does not match a fresh build of the source, THEN the CI token-drift gate SHALL fail the build.
**Acceptance criteria:**
1. Running the token build twice on identical input produces byte-identical CSS, Tailwind @theme, and TS outputs (deterministic).
2. The CI token-drift gate fails the build when a committed generated output diverges from a fresh build of design/tokens/*.json.
3. All three output artifacts derive solely from design/tokens/*.json; no consumer hardcodes a token value.
**Depends on:** DS-01, DS-07

### TOOL-02 — Contrast + accent-discipline gate  ·  P0  ·  EARS: event
**User story:** As an accessibility owner, I want contrast and palette discipline enforced at build time, so that color decisions are machine-verified rather than convention.
**EARS:** WHEN tokens are built, the pipeline SHALL compute contrast ratios for every documented foreground/background pairing and SHALL fail the build IF any text pairing falls below WCAG 2.2 AA (4.5:1 body, 3:1 large/UI). The pipeline SHALL assert that exactly one chromatic accent hue (--proven/--signal) plus the --pending warm tone are the only saturated colors in the palette.
**Acceptance criteria:**
1. The gate fails when any documented foreground/background text pairing measures below 4.5:1 (body) or 3:1 (large/UI).
2. The gate fails when more than the permitted saturated colors (--proven/--signal accent hue + --pending) appear in the resolved palette.
3. Contrast results are emitted as a machine-readable report artifact per build.
**Depends on:** DS-01, DS-07

### TOOL-03 — Motion/Rive asset governance  ·  P0  ·  EARS: event
**User story:** As a maintainer, I want every animation asset validated against a committed manifest with a reduced-motion fallback, so that motion behavior is verifiable and degrades safely.
**EARS:** The motion/Rive asset pipeline SHALL validate every public/rive/*.riv against the committed motion registry (DS-08) declaring its required state-machine name, inputs (e.g. requirement-proved triggers, gate-close state), and a content hash. WHEN a .riv is added or changed, the pipeline SHALL fail IF the file's state-machine/input names or hash do not match the registry. WHERE prefers-reduced-motion is set OR WebGL/Rive fails to load, the loader SHALL render the committed static labeled-diagram fallback instead of the animation.
**Acceptance criteria:**
1. The gate fails when a .riv state-machine name, input set, or content hash mismatches the DS-08 motion registry.
2. Under emulated prefers-reduced-motion the static labeled-diagram fallback renders and the .riv is not requested.
3. When Rive/WebGL load fails, the loader renders the static fallback (verified by a forced-failure test).
**Depends on:** DS-08, DS-09

### TOOL-04 — MDX frontmatter + claims-integrity linter  ·  P1  ·  EARS: event
**User story:** As a content owner, I want MDX frontmatter validated and quantitative verification claims forced to cite evidence, so that no unsourced claim ships.
**EARS:** The MDX pipeline SHALL validate every content/**/*.mdx file's frontmatter against a typed schema (title, slug, description, publishedAt, status, sources[]) and SHALL fail the build IF required fields are missing or malformed. WHEN MDX content contains a quantitative verification claim, the claims-integrity linter SHALL require an adjacent evidence reference (source URL or evidence id) from content/claims-registry.json and SHALL fail the build IF the claim is unsourced. The linter SHALL NOT hardcode any verified count and SHALL detect claims via the value-agnostic denylist regex \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b.
**Acceptance criteria:**
1. The build fails when any content/**/*.mdx is missing or malforms a required frontmatter field (title, slug, description, publishedAt, status, sources[]).
2. The claims linter flags any text matching \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b that lacks an adjacent evidence reference resolvable in content/claims-registry.json.
3. The linter contains no hardcoded "N/N verified" literal; the same regex catches an arbitrary fabricated count in a fixture test.
**Depends on:** CONTENT-06

### TOOL-05 — Deterministic lint/format/typecheck gates  ·  P0  ·  EARS: state
**User story:** As a maintainer, I want lint, format, and strict typecheck enforced deterministically with CI as the authority, so that mergeability is decided by verifiable checks.
**EARS:** The repository SHALL enforce ESLint (incl. jsx-a11y and a custom no-raw-token rule), Prettier formatting, Stylelint, and `tsc --noEmit` in strict mode as deterministic gates. WHEN a developer attempts to commit, a pre-commit hook SHALL run format+lint on staged files and block the commit IF they fail. The same checks SHALL run in CI on the full tree, and CI SHALL be the authoritative gate (local hooks inform but the CI result decides mergeability).
**Acceptance criteria:**
1. CI fails on any ESLint, Stylelint, Prettier, or `tsc --noEmit` strict-mode violation across the full tree.
2. The custom no-raw-token ESLint rule flags a raw token value used outside the generated token layer.
3. Merge is blocked by the CI result regardless of local pre-commit hook outcome.
**Depends on:** DS-01

### TOOL-06 — Visual-regression suite  ·  P0  ·  EARS: event
**User story:** As a maintainer, I want deterministic screenshots of loop states and route breakpoints compared to baselines, so that visual regressions fail the build with a diff artifact.
**EARS:** The visual-regression suite SHALL capture deterministic screenshots of the closed-loop at its named states (intent, proving, proved, gate-closed) and of each key route at mobile/tablet/desktop breakpoints, comparing against committed baselines with a bounded pixel-diff threshold. WHEN a captured frame differs beyond threshold, the visual gate SHALL fail and publish a diff artifact. WHILE prefers-reduced-motion is emulated, the suite SHALL assert the static fallback renders and is legible.
**Acceptance criteria:**
1. The gate fails and publishes a diff artifact when any captured frame exceeds the bounded pixel-diff threshold against its committed baseline.
2. Screenshots are captured for all four named loop states and for each key route at mobile/tablet/desktop.
3. Under emulated prefers-reduced-motion the suite asserts the static fallback is present and legible.
**Depends on:** PAGE-03, LOOP-05, DS-09

### TOOL-07 — Accessibility (axe) suite  ·  P0  ·  EARS: event
**User story:** As an accessibility owner, I want axe-core run against every key route and dynamic state, so that no serious/critical violation ships.
**EARS:** The test suite SHALL run axe-core against every key route (including empty, loading, and error states of dynamic components) and SHALL fail the build IF any serious/critical violation is found (target: zero). WHEN a page contains the closed-loop or evidence-trace, the suite SHALL assert a text-equivalent/aria description exists. WHERE interactive controls exist, the suite SHALL assert full keyboard operability and visible focus states.
**Acceptance criteria:**
1. The build fails when axe-core reports any serious or critical violation on any key route or dynamic state.
2. For pages with the closed-loop or evidence-trace, the suite asserts a text-equivalent/aria description is present.
3. The suite asserts keyboard operability and a visible focus indicator for every interactive control.
**Depends on:** PAGE-03, LOOP-05

### TOOL-08 — Unit/component test layer with motion-binding assertion  ·  P1  ·  EARS: complex
**User story:** As a maintainer, I want pure logic and component states unit-tested with every animation provably bound to a state, so that no animation exists without a documented state mapping.
**EARS:** The unit/component test layer SHALL test pure logic (token helpers, MDX utilities, evidence-trace formatting) and component rendering with Vitest + Testing Library. WHERE a component declares an animation, the test SHALL assert the animation is bound to a documented state input from the DS-08 motion registry (a state→visual mapping) and SHALL fail IF an animation has no associated state. The suite SHALL cover loading, empty, and error states for any data-driven component.
**Acceptance criteria:**
1. The suite fails when a component declares an animation not bound to a documented state input in the DS-08 motion registry.
2. Loading, empty, and error states are exercised for every data-driven component.
3. Token helpers, MDX utilities, and evidence-trace formatting have passing unit tests with assertions on output.
**Depends on:** DS-08

### TOOL-09 — Fail-closed CI aggregation gate  ·  P0  ·  EARS: unwanted
**User story:** As a maintainer, I want a fail-closed merge gate computed only from verifiable checks, so that no human or model self-report can substitute for a passing check.
**EARS:** CI SHALL run tokens-drift, contrast, lint, typecheck, format, unit/coverage, Playwright visual, axe, Lighthouse/CWV budget, MDX/claims-integrity, link-check, traceability, and security/header checks as required status checks. IF any required check fails, THEN the merge gate SHALL block (fail-closed) and SHALL NOT allow deploy. The gate decision SHALL be computed only from these verifiable check outputs; no human or model self-report SHALL substitute for a passing check.
**Acceptance criteria:**
1. The merge gate blocks and deploy is prevented when any single required status check fails.
2. The set of required checks includes tokens-drift, contrast, lint, typecheck, format, unit/coverage, visual, axe, Lighthouse/CWV, MDX/claims-integrity, link-check, traceability, and security/header.
3. The gate decision is derived solely from check outputs; there is no manual-override path that marks the gate green.
**Depends on:** none

### TOOL-10 — DESIGN.md ↔ token-source governance  ·  P1  ·  EARS: event
**User story:** As a design-system owner, I want DESIGN.md and the token source kept provably consistent, so that the design contract cannot silently rot.
**EARS:** DESIGN.md SHALL be the canonical specification of the token contract (names, values, semantics, accent discipline, typography, motion rules) and the token source files (DS) SHALL be derived from it. WHEN DESIGN.md or the token source changes, a governance check SHALL verify they remain consistent (same token names/values) and SHALL fail IF they diverge. The governance check SHALL be a required CI gate.
**Acceptance criteria:**
1. The governance check fails when a token name or value differs between DESIGN.md and design/tokens/*.json.
2. The check is registered as a required CI gate that blocks merge on divergence.
3. Adding a token to one side without the other is caught by a fixture test.
**Depends on:** DS-01, DS-07

### TOOL-11 — Lighthouse/CWV + asset budgets  ·  P1  ·  EARS: event
**User story:** As a performance owner, I want Lighthouse/CWV and asset budgets enforced on production builds, so that performance regressions are caught — with provisional budgets demoted until ratified.
**EARS:** CI SHALL run Lighthouse CI (or equivalent) against production-built key routes and SHALL fail IF performance, accessibility, best-practices, or SEO scores fall below committed thresholds (e.g. >=95) or IF LCP > 2.5s / CLS > 0.1 / INP budgets are exceeded. The pipeline SHALL enforce Rive asset size budgets and SHALL fail on regression beyond a documented delta; JS and CSS bundle budgets are Phase-0/1 PROVISIONAL and SHALL be non-gating until ratified.
**Acceptance criteria:**
1. The build fails when any production key route falls below the committed Lighthouse score thresholds or exceeds LCP 2.5s / CLS 0.1 / INP budgets.
2. The Rive asset size budget gate fails on regression beyond the documented delta.
3. JS/CSS bundle-budget results are reported as non-gating (warning only) while marked Phase-0/1 provisional.
**Depends on:** none

### TOOL-12 — Security headers, CSP & vulnerability/secret scanning  ·  P0  ·  EARS: unwanted
**User story:** As a security owner, I want strict headers plus dependency and secret scanning enforced, so that a high/critical vulnerability or a committed secret blocks deploy.
**EARS:** The deployment SHALL serve a strict Content-Security-Policy plus HSTS, X-Content-Type-Options, Referrer-Policy, frame-ancestors and Permissions-Policy headers, and CI SHALL verify these headers on a built/preview artifact. CI SHALL run dependency vulnerability scanning and secret scanning as required gates. IF a high/critical dependency vulnerability or a committed secret is detected, THEN the security gate SHALL fail and block deploy.
**Acceptance criteria:**
1. The header-assertion test fails when CSP, HSTS, X-Content-Type-Options, Referrer-Policy, frame-ancestors, or Permissions-Policy is missing/weakened on the built/preview artifact.
2. The security gate fails and blocks deploy on any high/critical dependency vulnerability.
3. The secret-scanning gate fails and blocks deploy when a committed secret is detected.
**Depends on:** none

### TOOL-13 — Apex deploy: SSG/ISR, immutable, atomic rollback  ·  P0  ·  EARS: event
**User story:** As a maintainer, I want immutable apex-domain deploys with atomic rollback and health-gated promotion, so that a bad deploy never replaces a healthy one.
**EARS:** The deployment pipeline SHALL build the Next.js App Router site as SSG/ISR and deploy it to the root domain autonomous-agent.dev only (no subdomain content). WHEN the main branch passes all required gates, the pipeline SHALL deploy an immutable, content-addressable build artifact and SHALL support one-click/atomic rollback to a prior build. IF the production deploy health-check fails, THEN the pipeline SHALL halt promotion and retain the previous live version.
**Acceptance criteria:**
1. Production deploys are immutable, content-addressable artifacts served only from autonomous-agent.dev (no subdomain content).
2. A failed post-deploy health-check halts promotion and the previous live version remains served.
3. An atomic rollback to a prior build is executable and verified by a rollback drill.
**Depends on:** IA-03

### TOOL-14 — Per-PR ephemeral preview environments  ·  P1  ·  EARS: event
**User story:** As a reviewer, I want each PR to get an access-controlled preview with gates run against it, so that changes are verified pre-merge and previews are not indexed or leaked.
**EARS:** WHEN a pull request is opened or updated, the pipeline SHALL build and deploy an isolated preview environment at a unique URL and SHALL run the visual-regression, axe, Lighthouse, and header checks against that preview. The pipeline SHALL post the preview URL and a summary of gate results to the PR. WHERE a preview is created, it SHALL be access-controlled (noindex, optional auth) and SHALL be torn down when the PR is closed/merged.
**Acceptance criteria:**
1. Opening/updating a PR produces a unique preview URL with visual, axe, Lighthouse, and header checks run against it and a summary posted to the PR.
2. Each preview serves a noindex directive (and optional auth) and is not crawlable.
3. Closing or merging the PR tears down its preview environment.
**Depends on:** IA-03

### TOOL-15 — Link-check + SEO/structured-data validation  ·  P1  ·  EARS: event
**User story:** As a content owner, I want internal links and SEO artifacts validated on built routes, so that broken links or missing metadata fail the build and no route references a sibling product.
**EARS:** CI SHALL validate internal links, generated sitemap.xml, robots.txt, canonical tags, Open Graph/Twitter metadata, and JSON-LD structured data on built routes, and SHALL fail IF any internal link is broken or required SEO artifact/metadata is missing or invalid. The validator SHALL confirm no production route references a subdomain or sibling product.
**Acceptance criteria:**
1. The build fails on any broken internal link in the built output.
2. The build fails when sitemap.xml, robots.txt, a canonical tag, OG/Twitter metadata, or JSON-LD is missing or invalid on a built route.
3. The validator fails when any production route references a subdomain or sibling product.
**Depends on:** IA-03, IA-12

### TOOL-16 — Self-hosted Geist font pipeline  ·  P1  ·  EARS: event
**User story:** As a performance owner, I want Geist Sans/Mono self-hosted, subset, and preloaded, so that fonts protect LCP/CLS and machine-artifact components are bound to the mono token.
**EARS:** The font pipeline SHALL self-host Geist Sans and Geist Mono (woff2, subset, with font-display: swap and size-adjust to minimize CLS) and SHALL expose them via the token typography layer (display weights 300–600). The build SHALL fail IF a font file is missing, references an external host, or a machine-artifact component is not bound to the mono token. WHEN fonts load, the critical font SHALL be preloaded to protect LCP.
**Acceptance criteria:**
1. The build fails when a font file is missing or references an external host (all Geist faces are served self-hosted woff2, subset).
2. The build fails when a machine-artifact component is not bound to the mono typography token.
3. The critical font is preloaded and exposed via the token typography layer with display weights in the 300–600 range.
**Depends on:** DS-01

### TOOL-17 — Synthetic uptime + scheduled re-verify, runbook & supply chain  ·  P1  ·  EARS: state
**User story:** As an operator, I want external synthetic uptime monitoring, periodic security re-verification, an incident runbook, and a pinned/SBOM-emitting supply chain, so that production is continuously verified and reproducible after deploy.
**EARS:** The deployment SHALL run external synthetic uptime monitoring on /, /proof, and the OG-image endpoint, plus a periodic re-run of the privacy/security verification, with an incident runbook and an immutable rollback. WHILE the site is in production, the CI/release pipeline SHALL pin all dependencies, run software-composition-analysis (SCA), and emit an SBOM on every release (mirroring the product's SLSA ethos).
**Acceptance criteria:**
1. External synthetic monitors probe /, /proof, and the OG-image endpoint on a defined interval and alert on failure.
2. A scheduled job re-runs the privacy/security header verification periodically and alerts on regression.
3. An incident runbook and an immutable/atomic rollback procedure are documented and a rollback drill is recorded.
4. The release pipeline pins all dependency versions, runs SCA, and emits a downloadable SBOM artifact attached to each release.
**Depends on:** TOOL-12, TOOL-13

---

## Performance — PERF

### PERF-01 — Core Web Vitals on mobile field profile  ·  P0  ·  EARS: event
**User story:** As a first-time visitor on a mid-tier phone, I want every primary page to load fast and stay stable, so that I can read the manifesto without jank or waiting.
**EARS:** WHEN any content route (/, /how-it-works, /proof, /manifesto) finishes loading on a Moto-G-class mobile profile (4x CPU throttle, Slow-4G), the site SHALL meet field-grade Core Web Vitals thresholds: LCP < 2.5s, CLS < 0.1, and INP < 200ms at the 75th percentile.
**Acceptance criteria:**
1. INP < 200ms is verified by a SCRIPTED Playwright interaction that dispatches a real user input on each route and measures the input-to-next-paint latency; Total Blocking Time is NOT accepted as a substitute.
2. LCP < 2.5s and CLS < 0.1 are asserted per route under the Moto-G-class throttle profile, with the run failing if any single route exceeds any threshold.
**Depends on:** IA-03, DS-01

### PERF-02 — Self-hosted subsetted fonts with zero-CLS fallback  ·  P0  ·  EARS: state
**User story:** As a visitor, I want text to appear immediately without reflowing when the brand fonts arrive, so that reading is never interrupted by a layout jump.
**EARS:** WHILE the display, body, and mono typefaces are in use, the site SHALL self-host subsetted WOFF2 fonts, preload only the fonts needed for above-the-fold content, and apply font-display: optional (or swap with a metric-compatible fallback) so that no font swap shifts layout.
**Acceptance criteria:**
1. Display weights are restricted to the 300–600 range and all fonts are served as self-hosted subsetted WOFF2 from the site origin (no third-party font CDN request).
2. Font-swap CLS contribution is measured at < 0.01 via a scripted load that compares pre-swap and post-swap layout boxes.
**Depends on:** DS-01, DS-07

### PERF-03 — Lazy, off-main-thread, layout-reserved Rive centerpiece  ·  P0  ·  EARS: event
**User story:** As a visitor, I want the animated centerpiece to load only when relevant and never push content around, so that the initial load is fast and stable.
**EARS:** WHEN the homepage loads, the site SHALL defer the Rive runtime and the .riv asset until the centerpiece is near the viewport, render the animation off the main thread where supported, and reserve its exact box so it never contributes to CLS.
**Acceptance criteria:**
1. The Rive runtime and .riv asset are not requested during initial load and are fetched only after an IntersectionObserver fires for the centerpiece region (verified via network timeline).
2. The centerpiece container reserves its final box (aspect-ratio or explicit dimensions) so its per-component CLS is measured at ≤ 0.001.
**Depends on:** DS-08, DS-09

### PERF-04 — Modern image formats with intrinsic dimensions  ·  P1  ·  EARS: state
**User story:** As a visitor on a metered connection, I want images served in efficient formats at the right size, so that I do not burn data or wait on oversized assets.
**EARS:** WHILE raster or vector imagery is rendered, the site SHALL serve modern formats (AVIF/WebP with fallback), declare intrinsic width/height (or aspect-ratio), lazy-load below-the-fold images, and eagerly prioritize only the single LCP image if one exists.
**Acceptance criteria:**
1. Every content image declares intrinsic width/height or aspect-ratio, contributing per-component CLS measured at ≤ 0.001.
2. At most one image carries fetchpriority=high (the LCP image); all below-the-fold images are loading=lazy, verified by static markup audit.
**Depends on:** PAGE-03, DS-01

### PERF-05 — Per-route first-load JS budget and code-splitting  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor, I want pages to ship only the code they need, so that interactivity arrives quickly even on slow hardware.
**EARS:** The site SHALL enforce a per-route first-load JavaScript budget and code-split heavy, route-specific, and below-the-fold modules (Rive, Framer Motion, interactive proof trace, MDX-heavy content) behind dynamic imports so they are excluded from the initial bundle.
**Acceptance criteria:**
1. Rive, Framer Motion, the proof trace, and MDX-heavy modules are absent from each route's initial bundle, confirmed by bundle-composition analysis.
2. A per-route first-load JS budget is declared and checked in CI; the budget is Phase-0/1 PROVISIONAL and non-gating until ratified, but the measured value is recorded on every run.
**Depends on:** LOOP-05, IA-03

### PERF-06 — Token-driven critical CSS with Tailwind v4 purge  ·  P1  ·  EARS: ubiquitous
**User story:** As a visitor, I want styles to render without blocking, so that the page paints quickly and consistently.
**EARS:** The site SHALL ship a per-route critical/initial CSS budget, generate styles from the design tokens (Tailwind v4) with unused utilities purged, and avoid render-blocking third-party stylesheets.
**Acceptance criteria:**
1. All shipped CSS derives from the DS token source (single source of truth: tokens = DS) with no third-party render-blocking stylesheet in the document head, verified by markup audit.
2. A per-route initial CSS budget is recorded each run; the budget is Phase-0/1 PROVISIONAL and non-gating until ratified.
**Depends on:** DS-01

### PERF-07 — SSG/ISR delivery with immutable asset caching  ·  P1  ·  EARS: ubiquitous
**User story:** As a visitor, I want HTML served from cache rather than rendered per request, so that time-to-first-byte stays low everywhere.
**EARS:** The site SHALL statically generate (SSG) all content routes at build time and use ISR only where content updates are expected (e.g. /writing), serving HTML from cache/CDN with no per-request server render on the critical path.
**Acceptance criteria:**
1. The content routes /, /how-it-works, /proof, /manifesto, /writing, /docs, /privacy, and /terms are emitted as static artifacts at build time (per the IA route manifest as single source of truth).
2. Only /writing is configured for ISR; all others are pure SSG, confirmed by build output inspection.
**Depends on:** IA-12, IA-03

### PERF-08 — Fail-closed performance CI gate  ·  P0  ·  EARS: unwanted
**User story:** As a maintainer, I want a regression-blocking gate, so that no merge can quietly degrade performance.
**EARS:** IF performance score < 95, OR IF any Core Web Vitals threshold is exceeded, OR IF any ratified budget is breached, THEN the CI gate SHALL fail and block merge.
**Acceptance criteria:**
1. Every pull request runs Lighthouse-CI (or equivalent) plus the scripted INP Playwright check, and merge is blocked on any CWV threshold breach (LCP < 2.5s, CLS < 0.1, INP < 200ms).
2. JS/CSS budget breaches are reported but treated as non-gating while Phase-0/1 PROVISIONAL; CWV thresholds and the performance score are gating from the start.
**Depends on:** PAGE-03, LOOP-05

### PERF-09 — Reduced-motion fast path  ·  P0  ·  EARS: state
**User story:** As a motion-sensitive visitor, I want the site to skip animation entirely, so that I get a calm, fast experience.
**EARS:** WHILE the visitor's prefers-reduced-motion is set to reduce, the site SHALL not download or initialize the Rive runtime/.riv, SHALL render the static labeled-diagram loop fallback instead, and SHALL disable non-essential Framer Motion animation.
**Acceptance criteria:**
1. Under emulated prefers-reduced-motion: reduce, the network timeline shows zero .riv and zero Rive-runtime fetches.
2. The reduced-motion path yields equal-or-better measured LCP, CLS, and INP than the animated path on the same route.
**Depends on:** DS-08, DS-09

### PERF-10 — Third-party script discipline and origin allowlist  ·  P1  ·  EARS: state
**User story:** As a visitor, I want non-critical scripts kept off the critical path, so that they never delay the main content.
**EARS:** WHILE any third-party or non-critical first-party script is included, the site SHALL load it deferred/async or post-hydration, off the critical path, and SHALL keep total third-party transfer and main-thread cost within a defined budget.
**Acceptance criteria:**
1. Every external script tag carries defer or async (or is injected post-hydration), verified by markup audit; no synchronous third-party script blocks parsing.
2. Loaded origins are checked against an allowlist in CI; total third-party transfer is recorded each run against a PROVISIONAL non-gating budget.
**Depends on:** IA-03

### PERF-11 — Compositor-only scroll motion  ·  P1  ·  EARS: state
**User story:** As a visitor, I want scroll-driven motion to stay smooth, so that scrolling never feels laggy.
**EARS:** WHILE the visitor scrolls through any animated section, the site SHALL drive motion using compositor-friendly properties (transform/opacity), throttle scroll work via rAF/IntersectionObserver, and keep interaction latency within the INP budget.
**Acceptance criteria:**
1. Scroll-driven animations mutate only transform and opacity (no layout-triggering properties), verified by code audit and a paint-flashing inspection.
2. During a scripted scroll-and-interact Playwright run, measured INP remains < 200ms.
**Depends on:** DS-08, DS-09

### PERF-12 — Resource-priority waterfall  ·  P1  ·  EARS: event
**User story:** As a visitor, I want the browser to fetch the right things first, so that meaningful content paints as early as possible.
**EARS:** WHEN the document is served, the site SHALL set correct resource-loading priorities — preconnect/dns-prefetch for required origins, preload of the LCP resource and above-the-fold fonts, and explicit deprioritization (lazy/dynamic) of the Rive runtime, below-the-fold images, and non-critical scripts.
**Acceptance criteria:**
1. The document head contains preload hints for exactly the above-the-fold fonts and the LCP resource, and no preload of the Rive runtime, verified by markup audit.
2. A scripted run confirms the LCP resource is requested in the first request wave while the Rive runtime is requested only after viewport proximity.
**Depends on:** DS-01, DS-07

### PERF-13 — Evidence-backed self-referential performance claims  ·  P1  ·  EARS: unwanted
**User story:** As a reader, I want any published performance number to be backed by real evidence, so that the site's claims about itself are trustworthy.
**EARS:** IF the site publishes any quantitative performance claim about itself (a Lighthouse score, an LCP figure, a bundle size) in visible content, THEN that claim SHALL be rendered as a monospaced machine artifact derived from a stored CI gate evidence record (metric, value, threshold, collected_at), and SHALL be suppressed or shown as pending IF no current verified evidence exists.
**Acceptance criteria:**
1. Each rendered performance claim resolves to an evidence record carrying metric, value, threshold, and collected_at; claims with no current record render as "pending" rather than a hardcoded number.
2. A test injects a stale/missing evidence record and asserts the claim is suppressed or marked pending, not displayed as fact.
**Depends on:** CONTENT-06, LOOP-05

### PERF-14 — Graceful states for failed/slow non-critical assets  ·  P1  ·  EARS: unwanted
**User story:** As a visitor on a flaky network, I want the page to stay usable when an asset fails, so that a missing animation or image never breaks the experience.
**EARS:** IF a non-critical asset (Rive .riv, an image, a deferred chunk) fails to load or is slow, THEN the site SHALL present a stable, reserved-space fallback (static diagram/poster, skeleton, or graceful omission) without layout shift, console-error storms, or a blocked main thread, and SHALL keep the page fully usable.
**Acceptance criteria:**
1. With the .riv request blocked, the centerpiece shows its static poster fallback in the reserved box with measured per-component CLS ≤ 0.001.
2. Simulated asset failures produce no uncaught console errors and the page remains interactive (scripted INP < 200ms after the failure).
**Depends on:** DS-08, LOOP-05

### PERF-15 — Privacy-respecting field RUM  ·  P2  ·  EARS: optional
**User story:** As a maintainer, I want real-user CWV data attributed by route, so that I can catch field regressions lab tests miss.
**EARS:** WHERE field telemetry is enabled, the site SHALL collect real-user Core Web Vitals (LCP, CLS, INP, TTFB) via a lightweight privacy-respecting RUM path and attribute regressions to a route, without that telemetry itself harming performance.
**Acceptance criteria:**
1. The RUM payload carries no PII and the RUM script's own main-thread cost is recorded against a PROVISIONAL budget on every run.
2. Collected samples are attributable to a specific route from the IA route manifest, verified by an end-to-end capture test.
**Depends on:** IA-12, IA-03

### PERF-16 — Responsive assets and cross-breakpoint stability  ·  P1  ·  EARS: state
**User story:** As a visitor on any device, I want correctly sized assets and stable layout at every breakpoint, so that mobile never downloads desktop media and resizing never shifts content.
**EARS:** WHILE the site is viewed at any breakpoint, the site SHALL serve responsively-sized assets, avoid loading desktop-only heavy media on mobile, and ensure breakpoint transitions and container queries produce no cumulative layout shift.
**Acceptance criteria:**
1. At the mobile breakpoint, desktop-only heavy media is not requested, verified by an emulated-viewport network timeline.
2. Crossing each defined breakpoint produces measured per-page CLS < 0.1, asserted by a scripted resize run.
**Depends on:** DS-01, PAGE-03

### PERF-17 — Save-Data / reduced-data degradation and support matrix  ·  P1  ·  EARS: state
**User story:** As a visitor who has opted into data saving (or uses an older browser), I want the site to skip heavy media and degrade predictably, so that I get a fast, documented experience instead of broken or bloated pages.
**EARS:** WHILE prefers-reduced-data or the Save-Data client hint is set, the site SHALL skip the Rive runtime and heavy media (rendering the static loop) and SHALL declare a browser-support matrix with documented degradation behavior.
**Acceptance criteria:**
1. Under an emulated Save-Data run, the network timeline shows zero .riv fetches and zero heavy-media fetches, with the static loop rendered in the reserved box.
2. A versioned browser-support matrix document enumerates supported browsers and the documented degradation behavior for each unsupported/limited capability, and is referenced from the codebase.
**Depends on:** DS-08, DS-09

---

## Accessibility & Reduced Motion — A11Y

### A11Y-01 — Landmark & heading structure  ·  P0  ·  EARS: ubiquitous
**User story:** As a screen-reader user, I want one clear landmark and heading structure per page, so that I can navigate and orient without ambiguity.
**EARS:** The site SHALL render exactly one banner, one main, and one contentinfo landmark per page, with all primary navigation inside a nav landmark; and WHERE a page contains sectioned content, the page SHALL maintain a heading hierarchy with no skipped levels (h1 → h2 → h3) and exactly one h1 per page.
**Acceptance criteria:**
1. Each route exposes exactly one `role=banner`, one `role=main`, one `role=contentinfo`, and primary nav within a `role=navigation` landmark (verified by axe-core landmark rules + DOM assertion).
2. Each route has exactly one `<h1>` and no skipped heading levels (assert via accessibility-tree heading-level walk; zero level gaps).
**Depends on:** IA-03, IA-12

### A11Y-02 — Keyboard focus order & skip link  ·  P0  ·  EARS: event
**User story:** As a keyboard-only user, I want a logical focus order and a skip link, so that I can reach main content without tabbing through everything.
**EARS:** WHEN a visitor navigates with the Tab key, the site SHALL move focus through interactive elements in DOM/reading order with a focus indicator meeting WCAG 2.2 AA visibility, and WHEN focus first enters the page, the site SHALL expose a "Skip to main content" link as the first focusable element that moves focus to the main landmark when activated.
**Acceptance criteria:**
1. Tab order matches DOM/reading order on every route (Playwright tab sweep records focus sequence; zero out-of-order jumps).
2. The first `Tab` press focuses a visible "Skip to main content" link whose activation moves focus into `role=main`; focus ring meets WCAG 2.2 AA visibility (non-color-only, ≥3:1 against adjacent colors).
**Depends on:** DS-08, DS-09

### A11Y-03 — WCAG 2.2 AA contrast (references token gate)  ·  P0  ·  EARS: complex
**User story:** As a low-vision visitor, I want all text and UI components to meet AA contrast, so that I can read and operate the site.
**EARS:** The site SHALL meet WCAG 2.2 AA contrast for all text and UI components (normal text ≥ 4.5:1, large text and graphical/UI-component boundaries ≥ 3:1) by consuming the design-token contrast pairing matrix owned by DS-02; and IF a proposed token pairing falls below its threshold, THEN the design-token contrast gate (owned by DS-02) SHALL fail and that pairing SHALL NOT ship.
**Acceptance criteria:**
1. Every rendered text/UI pairing on every route resolves to a pairing already passing the DS-02 contrast matrix; axe-core reports zero critical or serious color-contrast violations on default and reduced-motion render paths.
2. A11Y references (does not re-declare) the DS-02 / T-DS-04 contrast gate; no contrast threshold is independently asserted in A11Y. Canonical example `--proven #34E1A0` on `--canvas #0A0B0D` measures ≈12.5:1.
**Depends on:** DS-01, DS-02, DS-07

### A11Y-04 — Reduced-motion static closed-loop  ·  P0  ·  EARS: state
**User story:** As a motion-sensitive visitor, I want a static labeled diagram instead of animation, so that I can understand the loop without triggering discomfort.
**EARS:** WHILE the resolved reduced-motion preference is "reduce", the closed-loop centerpiece SHALL render a static, fully labeled diagram of the loop (intent → decompose → implement → verify → prove → fail-closed gate) showing the gate in its closed/holding state, and SHALL NOT autoplay the Rive state machine or any looping motion.
**Acceptance criteria:**
1. With reduced-motion active, the centerpiece renders a static SVG with all six stage labels and the gate in closed/holding state; no Rive state machine or looping animation is instantiated (assert no `requestAnimationFrame`/Rive playback and no motion classes).
2. The static diagram exposes the same six-stage semantics as the animated version (text equivalent present, see A11Y-07).
**Depends on:** PAGE-03, LOOP-05, DS-08

### A11Y-05 — Reduced-motion resolved-state for all motion  ·  P0  ·  EARS: state
**User story:** As a motion-sensitive visitor, I want every animated element to appear in its final state instantly, so that no movement is shown.
**EARS:** WHILE the resolved reduced-motion preference is "reduce", the evidence-trace panel, coverage-fill indicators, trace-reveal sequences, scrollytelling transitions, and all Framer Motion micro-interactions SHALL render in their final/resolved state immediately, with no fade, slide, stagger, pulse, or auto-advance.
**Acceptance criteria:**
1. With reduced-motion active, all listed components mount at final state; no transition/animation runs (assert computed `animation`/`transition` durations resolve to 0 or are absent via the global motion backstop).
2. No auto-advance or stagger timers are scheduled under reduced-motion (zero pending interval/timeout for motion).
**Depends on:** DS-08, DS-09, LOOP-05

### A11Y-06 — State not conveyed by color alone  ·  P0  ·  EARS: ubiquitous
**User story:** As a colorblind visitor, I want verification states paired with non-color cues, so that I can tell proven from pending without relying on color.
**EARS:** The site SHALL NOT use color as the only visual means of conveying a verification state, and WHERE a machine artifact or loop node communicates proven, pending, unproven/dim, or gate-closed status, the site SHALL pair the color with a redundant non-color cue (icon/glyph shape, text label, fill pattern, or monospace state word).
**Acceptance criteria:**
1. Every verification-state indicator (proven, pending, unproven/dim, gate-closed) carries at least one non-color cue (icon shape, text label, fill pattern, or monospace state word), verified by DOM audit across all states.
2. Rendering each state in grayscale leaves the state distinguishable (manual + snapshot check; zero states ambiguous without color).
**Depends on:** CONTENT-06

### A11Y-07 — Text equivalents for animated/visual proof  ·  P0  ·  EARS: ubiquitous
**User story:** As an assistive-tech user, I want text equivalents for animated proof content, so that I can perceive the loop and evidence without seeing the visuals.
**EARS:** The site SHALL provide an accessible text equivalent for all animated and visual proof content: the closed-loop centerpiece SHALL expose an accessible name/description summarizing the six stages and the fail-closed outcome, and the evidence-trace records SHALL be exposed to assistive tech as readable text, not as an inert canvas.
**Acceptance criteria:**
1. The centerpiece exposes an accessible name/description (or associated visible text alternative) naming all six stages and the fail-closed outcome (assert via accessibility tree).
2. Evidence-trace records are present as readable DOM text exposed to AT (figure/figcaption or semantic list), not canvas-only; screen-reader read-through yields the trace content.
**Depends on:** PAGE-03, LOOP-05, CONTENT-06

### A11Y-08 — Dual-pass axe-core CI gate  ·  P0  ·  EARS: unwanted
**User story:** As a maintainer, I want CI to block merges on serious a11y regressions, so that accessibility never silently degrades.
**EARS:** WHEN the accessibility CI job runs against every route in both the default and reduced-motion render paths, the build SHALL fail closed (non-zero exit, merge blocked) IF any axe-core violation of impact "critical" or "serious" is present, and the gate SHALL itself be evidence-backed (recording which rules ran and the result, never a self-asserted pass).
**Acceptance criteria:**
1. CI runs axe-core on every route in both default and reduced-motion render paths; the job exits non-zero and blocks merge on any critical OR serious violation (zero tolerance).
2. The gate emits a machine-readable evidence artifact listing rules executed and per-route results; absence of the artifact is itself a failure.
**Depends on:** none

### A11Y-09 — Reflow & zoom to 400% (1.4.10)  ·  P1  ·  EARS: event
**User story:** As a low-vision visitor, I want content to reflow when zoomed, so that I can read without two-dimensional scrolling.
**EARS:** WHEN content is zoomed to 200% (and up to 400% per WCAG 2.2 SC 1.4.10) or OS/browser text size is enlarged, the site SHALL reflow to a single readable column without two-dimensional scrolling and without clipping or overlapping text, including the monospace machine artifacts.
**Acceptance criteria:**
1. At 400% zoom / 320 CSS px equivalent width, no horizontal scrolling is required for vertical content and no text is clipped or overlapped (Playwright reflow check; zero horizontal-scroll regions).
2. Monospace machine artifacts wrap or scroll within their own container without forcing page-level two-dimensional scrolling.
**Depends on:** DS-07

### A11Y-10 — Accessible controls & form errors  ·  P1  ·  EARS: event
**User story:** As an assistive-tech user, I want named controls and announced errors, so that I can complete the Get-notified form without color-only feedback.
**EARS:** The site SHALL give every form control and custom interactive control a programmatic accessible name and role, and WHEN the Get-notified submission is invalid or fails, THEN the site SHALL surface an accessible text-based error associated with the field and announced to assistive tech, never conveyed by color alone.
**Acceptance criteria:**
1. Every form/custom control has a programmatic accessible name and role (axe-core zero critical or serious naming violations).
2. Invalid/failed submission surfaces a text error programmatically associated (`aria-describedby`) and announced via a live region; error is not color-only (state never conveyed by color alone).
**Depends on:** DS-09

### A11Y-11 — Pause/stop/hide motion (2.2.2)  ·  P1  ·  EARS: optional
**User story:** As any visitor, I want to pause or stop auto-playing motion, so that I can read without distraction regardless of OS settings.
**EARS:** WHERE the site presents motion that starts automatically, runs longer than 5 seconds, or auto-updates (the closed-loop animation, auto-advancing scrollytelling, the trace stream), the site SHALL provide a mechanism to pause, stop, or hide it, and the motion SHALL respect WCAG 2.2 SC 2.2.2 even when reduced-motion is not set.
**Acceptance criteria:**
1. Each auto-starting/>5s/auto-updating motion exposes a keyboard-operable pause/stop/hide control with an accessible name (verified per component).
2. Activating the control halts the motion and persists the static state until re-enabled, with reduced-motion not required (SC 2.2.2 satisfied).
**Depends on:** PAGE-03, LOOP-05

### A11Y-12 — Accessible loading/error placeholders  ·  P1  ·  EARS: state
**User story:** As an assistive-tech user, I want stable, non-misleading placeholders while assets load, so that nothing claims "proven" without its evidence.
**EARS:** WHILE the closed-loop, self-hosted fonts, or trace content are loading, the site SHALL present an accessible, non-empty placeholder (the static labeled diagram and system fonts), and IF any of these assets fail to load, THEN the site SHALL keep the page operable and announce nothing misleading (no "proven" state shown without its evidence text).
**Acceptance criteria:**
1. During loading, the accessibility tree contains the static labeled diagram and system-font text (non-empty placeholder); no empty/aria-busy-only region remains user-blocking.
2. On asset load failure, the page stays operable and no "proven"/verification claim is exposed without its backing evidence text (assert no orphaned state words).
**Depends on:** PAGE-03

### A11Y-13 — Claims integrity for a11y/coverage numbers  ·  P1  ·  EARS: unwanted
**User story:** As a visitor, I want stated accessibility/coverage figures to be artifact-backed, so that I can trust the claims.
**EARS:** The site SHALL NOT present any verification, coverage, or "accessible/compliant" status as a published claim unless backed by a verifiable artifact, and IF an accessibility or coverage figure cannot currently be substantiated, THEN the site SHALL omit the specific number rather than assert it.
**Acceptance criteria:**
1. A content lint flags any accessibility/coverage/compliance number lacking a linked verifiable artifact; build fails on an unbacked claim (zero unbacked figures shipped).
2. Where a figure is unsubstantiated, the rendered copy omits the number rather than asserting it (verified by lint + content review).
**Depends on:** CONTENT-06

### A11Y-14 — Responsive a11y: target size (2.5.8) & orientation  ·  P1  ·  EARS: ubiquitous
**User story:** As a touch/mobile user, I want adequately sized targets and orientation support, so that I can operate the site on any device.
**EARS:** The site SHALL preserve accessibility across responsive breakpoints: interactive targets SHALL meet a minimum size of 24×24 CSS px (WCAG 2.2 SC 2.5.8; 44×44 where practical), content SHALL support both portrait and landscape (SC 1.3.4), and the loop SHALL degrade to the labeled diagram on small screens.
**Acceptance criteria:**
1. Every interactive target measures ≥ 24×24 CSS px (SC 2.5.8) at all breakpoints (automated bounding-box audit; zero undersized targets), with 44×44 used where practical.
2. Content is operable in both portrait and landscape (SC 1.3.4) with no orientation lock; the loop renders as the labeled static diagram at small-screen breakpoints.
**Depends on:** DS-07, IA-12

### A11Y-15 — Route-change focus & announcement  ·  P2  ·  EARS: event
**User story:** As an assistive-tech user, I want focus and title to update on route change, so that I know the page changed.
**EARS:** WHEN a client-side route change completes (Next.js App Router navigation) or an in-page anchor is activated, the site SHALL move focus to a logical target (the main landmark or the relevant heading), update the document title to reflect the new page, and announce the page change to assistive technology.
**Acceptance criteria:**
1. On route change, focus moves to `role=main` or the target heading and `document.title` updates to the new page (assert focus target + title diff per navigation).
2. The page change is announced via a polite live region (screen-reader announcement observed; no duplicate or missing announcements).
**Depends on:** IA-03

### A11Y-16 — Persisted in-page "Reduce motion" control  ·  P1  ·  EARS: optional
**User story:** As a visitor on a device where OS reduced-motion is unset, I want an in-page control to reduce motion that sticks, so that I can opt out of animation independently of my OS.
**EARS:** WHERE the visitor uses the in-page "Reduce motion" control, the site SHALL persist the preference (independent of the OS `prefers-reduced-motion` query) and SHALL write the same `useReducedMotion` context consumed site-wide, sharing the PRIV-03 `__pref` store.
**Acceptance criteria:**
1. Toggling the footer "Reduce motion" control immediately switches motion components to their static/resolved render (same effect as OS reduced-motion), verified by post-toggle DOM/motion assertion.
2. The preference is written to the PRIV-03 `__pref` store and the resolved `useReducedMotion` context, persisting across reload (and OR-merging with the OS query so either source enables reduced motion).
**Depends on:** DS-08, DS-09

---

## SEO, Metadata & Structured Data — SEO

### SEO-01 — Route-specific title & description  ·  P0  ·  EARS: complex
**User story:** As a search engine crawler, I want a unique, route-specific document title and meta description on every public route, so that each page is indexed and presented distinctly in results.
**EARS:** The metadata system SHALL produce a unique, route-specific document <title> and meta description for every public content route (/, /how-it-works, /proof, /manifesto, /writing, /writing/[slug], /docs), generated at build time via the Next.js App Router Metadata API. WHERE a route does not declare its own title, the metadata system SHALL fall back to a defined title template ("%s — Autonomous Agent") with the root layout supplying the default. WHEN a route declares no description, THEN the metadata system SHALL emit the global brand description rather than omitting the tag.
**Acceptance criteria:**
1. For each content route the rendered HTML contains exactly one non-empty <title> element and exactly one <meta name="description"> with non-empty content.
2. The set of (title, description) pairs across all content routes contains no duplicate pair (uniqueness assertion over fetched HTML).
3. A route with no declared title yields a title matching the "%s — Autonomous Agent" template; a route with no declared description yields the global brand description string.
**Depends on:** IA-03

### SEO-02 — Single canonical per page  ·  P0  ·  EARS: complex
**User story:** As an SEO engineer, I want exactly one normalized canonical URL per page, so that link equity is never split across host/scheme/parameter variants.
**EARS:** The metadata system SHALL emit exactly one <link rel="canonical"> per page pointing at the absolute, normalized URL on the production origin https://autonomous-agent.dev. The metadata system SHALL derive canonical URLs from a single metadataBase origin constant and SHALL normalize host (apex, not www), scheme (https), and trailing slash to one chosen convention. WHEN a page is reachable via tracking or pagination query parameters, THEN the canonical SHALL point at the clean parameter-free URL (except where a query genuinely identifies distinct content). IF the deploy is a preview/non-production environment, THEN the metadata system SHALL emit canonicals to the preview origin and SHALL additionally emit <meta name="robots" content="noindex">.
**Acceptance criteria:**
1. Every page's HTML contains exactly one <link rel="canonical"> whose href is absolute, https-scheme, apex-host, and matches the single trailing-slash convention.
2. A request with appended tracking query params (e.g. ?utm_source=x) yields a canonical equal to the clean parameter-free URL.
3. In a simulated preview environment the canonical points at the preview origin AND a <meta name="robots" content="noindex"> is present.
**Depends on:** DS-01

### SEO-03 — Complete OpenGraph & Twitter card sets  ·  P0  ·  EARS: ubiquitous
**User story:** As a social platform unfurler, I want a complete Open Graph and Twitter Card tag set on every route, so that shared links render rich, correct previews.
**EARS:** The metadata system SHALL emit a complete Open Graph tag set (og:type, og:title, og:description, og:url, og:site_name, og:locale, og:image, og:image:width, og:image:height, og:image:alt) and a complete Twitter Card set (twitter:card=summary_large_image, twitter:title, twitter:description, twitter:image, twitter:image:alt) for every public route, referencing a per-route social image at 1200x630 (1.91:1) with descriptive alt text. WHERE a route is an article (/writing/[slug]), THEN the metadata system SHALL set og:type=article and emit article:published_time, article:modified_time, and article:author.
**Acceptance criteria:**
1. For each content route the HTML contains all required og:* and twitter:* tags with non-empty content; twitter:card equals "summary_large_image".
2. og:image:width=1200 and og:image:height=630 are asserted present, and og:image:alt / twitter:image:alt are non-empty.
3. For an /writing/[slug] route, og:type="article" and article:published_time, article:modified_time, article:author are present.
**Depends on:** DS-07

### SEO-04 — Token-driven OG image system  ·  P0  ·  EARS: complex
**User story:** As a brand owner, I want per-route Open Graph images generated from design tokens with a static fallback, so that every share renders an on-brand 1200x630 card and never a broken image.
**EARS:** The social-image system SHALL generate per-route 1200x630 Open Graph images using Next.js ImageResponse from the design tokens (--canvas #0A0B0D background, --text #F5F7FA, one accent --proven #34E1A0 reserved for verification glyphs, self-hosted Geist Sans + Geist Mono). WHERE a route is an article, THEN the system SHALL render the article title, an eyebrow/section label, and a monospace artifact motif into the card, applying the accent ONLY to a verification/proof glyph. WHEN OG image generation fails or a route lacks a specific image, THEN the system SHALL serve a static pre-built brand fallback image (1200x630).
**Acceptance criteria:**
1. The OG image endpoint for each route returns HTTP 200 with content-type image/* and decoded dimensions exactly 1200x630.
2. The generated card uses the token background #0A0B0D and text #F5F7FA; the accent #34E1A0 is applied only to the verification glyph element (asserted via render-template inspection / snapshot).
3. When image generation is forced to fail, the served bytes equal the static fallback asset (200, 1200x630), never a 404 or empty body.
**Depends on:** DS-07, DS-08

### SEO-05 — Site-wide Organization + WebSite JSON-LD  ·  P0  ·  EARS: complex
**User story:** As a knowledge-graph consumer, I want one Organization and one WebSite JSON-LD node site-wide, so that the entity is unambiguous and free of unverifiable claims.
**EARS:** The structured-data system SHALL emit a single Organization JSON-LD node (name "Autonomous Agent", url, logo, sameAs for owned brand profiles only) and a single WebSite JSON-LD node (name, url, inLanguage, publisher referencing the Organization) site-wide via the root layout, output as <script type="application/ld+json"> using the schema.org @context. WHERE no public on-site search exists, THEN the WebSite node SHALL NOT include a potentialAction/SearchAction it cannot honor. The structured-data system SHALL NOT include any sameAs link to a subdomain or sibling product, and SHALL NOT assert any award/claim/rating not backed by the claims registry.
**Acceptance criteria:**
1. Exactly one Organization node and exactly one WebSite node are present site-wide, both valid against schema.org and parseable as JSON-LD.
2. The WebSite node contains no potentialAction/SearchAction; the Organization sameAs (if present) contains only owned-profile URLs and no subdomain/sibling-product link.
3. No JSON-LD string matches the value-agnostic denylist regex \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b.
**Depends on:** CONTENT-06

### SEO-06 — Article + BreadcrumbList JSON-LD  ·  P1  ·  EARS: complex
**User story:** As a search engine, I want Article and BreadcrumbList JSON-LD on writing routes, so that articles surface rich results with correct breadcrumbs.
**EARS:** The structured-data system SHALL emit Article (or BlogPosting/TechArticle as appropriate) JSON-LD on each /writing/[slug] route with headline, description, image, datePublished, dateModified, author, publisher (referencing the Organization), mainEntityOfPage, and inLanguage, and SHALL emit BreadcrumbList JSON-LD on nested routes reflecting the real navigational hierarchy with absolute item URLs. WHEN an article's front-matter omits dateModified, THEN the system SHALL default dateModified to datePublished. IF a required Article field is missing at build, THEN the build SHALL fail rather than emit incomplete structured data.
**Acceptance criteria:**
1. Each /writing/[slug] emits a schema.org-valid Article node containing all required fields with publisher referencing the single Organization node.
2. BreadcrumbList items use absolute apex-https URLs that match the IA-declared hierarchy for the route.
3. An article fixture omitting dateModified yields dateModified === datePublished; an article fixture missing a required field fails the build with a file-scoped error.
**Depends on:** IA-12

### SEO-07 — Build-time sitemap.xml  ·  P0  ·  EARS: complex
**User story:** As a crawler, I want a build-time sitemap of every canonical indexable route, so that discovery is complete and excludes non-indexable URLs.
**EARS:** The sitemap system SHALL generate /sitemap.xml at build time listing every canonical, indexable content route with <loc> (absolute apex https URL), <lastmod> (ISO-8601 derived from content/build provenance), and SHALL exclude any noindex, draft, redirecting, non-canonical, utility, or error URL. WHERE the /writing index grows large, THEN the sitemap system SHALL support a sitemap index splitting entries across child sitemaps. WHEN a /writing post's source file changes, THEN that entry's lastmod SHALL reflect the post's true last-modified date, not the global build time.
**Acceptance criteria:**
1. sitemap.xml is well-formed XML; every <loc> is absolute, https, apex-host, and is a member of the IA content-route set; no noindex/draft/utility/error path appears.
2. Every <lastmod> parses as valid ISO-8601.
3. Editing a writing post's source file changes only that entry's <lastmod> to the post's mtime while unrelated entries are unchanged.
**Depends on:** IA-03

### SEO-08 — Build-time robots.txt  ·  P0  ·  EARS: complex
**User story:** As a crawler, I want an environment-aware robots.txt with a sitemap directive, so that I index production fully and never index preview origins.
**EARS:** The robots system SHALL generate /robots.txt at build time declaring User-agent rules and an absolute Sitemap: directive to https://autonomous-agent.dev/sitemap.xml. WHILE the deploy target is production, the robots system SHALL allow indexing of all public content routes and disallow only non-indexable paths. IF the deploy target is a preview/staging environment, THEN the robots system SHALL emit Disallow: / so non-production origins are never indexed. The robots system SHALL NOT block CSS/JS/font/image assets required for rendering.
**Acceptance criteria:**
1. Production robots.txt contains an absolute Sitemap: https://autonomous-agent.dev/sitemap.xml directive and does not Disallow any content route.
2. A simulated preview build emits Disallow: / for the catch-all user-agent.
3. No Disallow rule matches required rendering assets (CSS/JS/font/image paths).
**Depends on:** DS-01

### SEO-09 — RSS/Atom feed  ·  P1  ·  EARS: complex
**User story:** As a feed reader, I want an autodiscoverable RSS/Atom feed of writing posts, so that I can subscribe and receive new posts.
**EARS:** The feed system SHALL generate an RSS 2.0 (and/or Atom) feed at a stable path (e.g. /writing/feed.xml) listing published /writing posts newest-first with title, absolute link, description/summary, pubDate, guid (stable, permalink-based), and author, plus channel-level title, link, description, language, and lastBuildDate, and SHALL emit an autodiscovery <link rel="alternate" type="application/rss+xml"> in the <head> of /writing and article pages. WHEN no posts exist yet, THEN the feed system SHALL emit a valid empty-channel feed rather than 404. WHERE full-content syndication is enabled, THEN the system SHALL place rendered HTML in content:encoded and escape it correctly.
**Acceptance criteria:**
1. The feed validates as well-formed RSS/Atom XML with all required channel-level and item-level fields; items are ordered newest-first by pubDate.
2. /writing and article pages contain a <link rel="alternate" type="application/rss+xml"> in <head> pointing at the feed path.
3. With zero published posts the feed endpoint returns 200 with a valid zero-item channel (not 404).
**Depends on:** DS-01

### SEO-10 — Semantic structure & heading outline  ·  P0  ·  EARS: complex
**User story:** As an accessibility/SEO auditor, I want one h1 per route and a clean heading hierarchy with landmarks, so that the document outline is correct and machine artifacts do not pollute it.
**EARS:** The semantic-structure system SHALL render exactly one <h1> per route expressing the page's primary subject and SHALL produce a heading hierarchy with no skipped levels (h1 -> h2 -> h3). The system SHALL wrap primary content in a <main> landmark and use <nav>, <header>, <footer>, and <article> appropriately, and SHALL ensure machine artifacts rendered in monospace (requirement IDs, hashes, gate verdicts) do NOT substitute for or pollute the semantic heading outline. WHERE MDX content authors headings, THEN the system SHALL auto-assign stable id slugs for anchor linking without breaking the outline.
**Acceptance criteria:**
1. Each route's HTML contains exactly one <h1> with non-empty text and no heading-level skip (assertion over the parsed heading sequence).
2. Each route contains exactly one <main> landmark, and present <nav>/<header>/<footer>/<article> elements are valid landmarks.
3. Every MDX-authored heading has a stable, unique id slug; monospace artifact spans are not heading elements.
**Depends on:** IA-03

### SEO-11 — No-JS server-rendered metadata parity  ·  P0  ·  EARS: state
**User story:** As a crawler that does not execute JavaScript, I want all SEO tags present in the server-rendered HTML, so that metadata never depends on hydration.
**EARS:** WHILE serving any route via SSG/ISR, the metadata system SHALL emit all SEO-critical tags (title, description, canonical, robots, OpenGraph, Twitter, JSON-LD, lang) in the initial server-rendered HTML, such that a non-JS fetch returns complete head metadata; the metadata system SHALL NOT depend on client-side React hydration, Framer Motion, or Rive to populate any SEO tag. WHERE a route uses ISR revalidation, THEN metadata SHALL be regenerated with the page so stale metadata is never served beyond the revalidation window.
**Acceptance criteria:**
1. A raw (JS-disabled) HTTP fetch of each route returns HTML already containing title, description, canonical, robots, OG, Twitter, JSON-LD, and lang attribute.
2. The no-JS rendered metadata set is byte-equivalent (modulo formatting) to the hydrated DOM metadata set for the same route.
3. No SEO tag is injected by a client-only script (assertion: removing client bundles leaves the head metadata intact).
**Depends on:** DS-01

### SEO-12 — Typed MDX front-matter schema (single source)  ·  P1  ·  EARS: complex
**User story:** As a content engineer, I want one validated front-matter schema driving all per-route metadata, JSON-LD, sitemap, and feed, so that there is a single source of truth and invalid content fails the build.
**EARS:** The content-metadata system SHALL define a single typed front-matter schema (validated, e.g. Zod) for MDX carrying title, description, slug, datePublished, dateModified, author, tags, ogImage override, draft flag, and canonical override, and SHALL be the single source from which per-route metadata, Article JSON-LD, sitemap entries, and feed items are derived. IF a post's front-matter fails schema validation, THEN the build SHALL fail with a precise error naming the file and field. WHERE draft:true is set, THEN the system SHALL exclude the post from production sitemap, feed, and index listings and SHALL mark it noindex.
**Acceptance criteria:**
1. Metadata, Article JSON-LD, sitemap entries, and feed items for a post all derive from the same parsed front-matter object (no second source).
2. A fixture with an invalid/missing required field fails the build with an error naming the file path and the offending field.
3. A draft:true post is absent from production sitemap, feed, and index listings and its route carries <meta name="robots" content="noindex">.
**Depends on:** CONTENT-06

### SEO-13 — Claims-integrity guardrail  ·  P0  ·  EARS: unwanted
**User story:** As a trust owner, I want a build-time scanner that blocks unverifiable verification-count claims across all SEO surfaces, so that no "N/N verified" figure ships unless it is corpus-traceable.
**EARS:** IF any generated SEO surface (titles, meta descriptions, OG/Twitter copy, JSON-LD serialized strings, social-image text, feed item text) contains a verification-count or unverifiable superlative not present in the allow-listed claims registry, THEN the claims-integrity guardrail SHALL fail the build. The guardrail SHALL specifically block any string matching the value-agnostic denylist regex \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b regardless of the numeric values. WHERE a claim is corpus-traceable, THEN its registry entry SHALL carry a source reference so the published claim is itself evidence-backed.
**Acceptance criteria:**
1. The scanner runs in CI over every generated SEO surface listed above and fails the build on any match of the denylist regex \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b.
2. A fixture surface containing e.g. "12/12 formally verified" fails the build; the same surface with the claim removed passes (no hardcoded count is ever permitted in metadata/structured data).
3. The single content/claims-registry.json is the only allow-list source, and each entry carries a non-empty source reference field.
**Depends on:** CONTENT-06

### SEO-14 — Stub / empty / error-state SEO policy  ·  P1  ·  EARS: state
**User story:** As an SEO owner, I want stub, empty, and error pages marked noindex and excluded from the sitemap, so that thin/non-content pages never get indexed.
**EARS:** WHILE the /docs route (or any thin/stub or empty-state route) is a stub, the metadata system SHALL mark it <meta name="robots" content="noindex,follow"> and SHALL exclude it from sitemap.xml, and the structured-data system SHALL NOT emit Article, FAQ, HowTo, or Product JSON-LD for it. WHEN /docs ships real content, THEN the route SHALL drop noindex, enter the sitemap, and gain structured data via the same front-matter pipeline. IF a route renders an error (404/500) or empty state, THEN it SHALL return the correct status code and SHALL NOT be added to the sitemap.
**Acceptance criteria:**
1. While stub, /docs HTML carries <meta name="robots" content="noindex,follow">, is absent from sitemap.xml, and emits no Article/FAQ/HowTo/Product JSON-LD.
2. A simulated content-bearing /docs drops noindex, appears in sitemap.xml, and gains front-matter-derived structured data.
3. The 404 and 500 routes return status 404/500 respectively and are absent from sitemap.xml.
**Depends on:** IA-03

### SEO-15 — CI SEO verification harness  ·  P0  ·  EARS: unwanted
**User story:** As a release gate owner, I want a CI harness asserting all SEO invariants and blocking deploy on failure, so that SEO regressions cannot ship.
**EARS:** The SEO verification harness SHALL run in CI on every build and SHALL assert: uniqueness/length of titles+descriptions, exactly-one-canonical/origin-correctness, OG/Twitter completeness and image 200/dimensions, JSON-LD schema validity (Organization/WebSite/Article/BreadcrumbList), sitemap.xml well-formedness and route-parity against IA, robots.txt validity and sitemap reference, feed validity, single-H1/heading-order, lang-attribute presence, and no-JS metadata parity. IF any assertion fails, THEN the harness SHALL fail the build with a precise file/route-scoped message and SHALL block deploy as a required status check, storing machine-readable evidence of which checks ran and their pass/fail outcome.
**Acceptance criteria:**
1. The harness executes every listed assertion category and exits non-zero if any fails, surfacing a file/route-scoped message.
2. The harness is wired as a required status check so a failing run blocks deploy.
3. Each run writes a machine-readable evidence artifact (checks run, pass/fail per check, validated artifact reference).
**Depends on:** IA-03

### SEO-16 — English-only lang & i18n non-goal  ·  P2  ·  EARS: ubiquitous
**User story:** As a crawler and assistive-technology user, I want every route to declare English via <html lang="en"> with no hreflang, so that language is unambiguous and i18n is an explicit non-goal.
**EARS:** The site SHALL set <html lang="en"> on every route, SHALL declare English-only with no hreflang alternates, and SHALL document internationalization as an explicit non-goal of the website spec.
**Acceptance criteria:**
1. Every route's server-rendered <html> element has the attribute lang="en" (assertion over fetched HTML for each route).
2. No route emits any <link rel="alternate" hreflang="..."> tag and no JSON-LD inLanguage value other than "en".
3. The fragment/spec records i18n / multi-locale as an explicit non-goal (documented posture, not a TODO).
**Depends on:** IA-03

### SEO-17 — security.txt, AI-crawler policy & llms.txt  ·  P3  ·  EARS: ubiquitous
**User story:** As a security researcher and AI crawler, I want /.well-known/security.txt, an explicit AI-crawler policy in robots.txt, and an llms.txt thesis summary, so that disclosure contacts and machine-reading expectations are clear.
**EARS:** The site SHALL serve /.well-known/security.txt conforming to RFC 9116, SHALL declare an explicit AI-crawler policy in robots.txt naming AI user-agents, and SHALL serve an llms.txt summarizing the site's thesis and proof model.
**Acceptance criteria:**
1. /.well-known/security.txt returns 200 with RFC 9116 required fields (Contact and Expires) present and a valid future Expires timestamp.
2. robots.txt contains explicit User-agent rules naming at least one AI crawler user-agent (e.g. GPTBot, ClaudeBot, Google-Extended) with a defined Allow/Disallow directive.
3. /llms.txt returns 200 with non-empty content describing the thesis and proof model.
**Depends on:** DS-01

### SEO-18 — Distinct per-route OG images & explicit social identity  ·  P3  ·  EARS: ubiquitous
**User story:** As a sharer, I want each top-level marketing route to unfurl a distinct OG card, with the social-identity decision made explicitly, so that previews are route-specific and no placeholder TODO ships.
**EARS:** Each top-level marketing route (/, /how-it-works, /proof, /manifesto) SHALL produce a distinct route-specific OG image via ImageResponse, and the social-identity decision SHALL be explicit: twitter:site and Organization sameAs SHALL be omitted entirely when no owned profiles exist, recorded as a deliberate decision rather than a TODO.
**Acceptance criteria:**
1. The OG images for /, /how-it-works, /proof, and /manifesto are pairwise distinct (differing rendered title/eyebrow; byte/snapshot non-equality across the four).
2. Each of the four routes returns an OG image at 200 with dimensions 1200x630.
3. When no owned social profiles exist, twitter:site is absent and Organization sameAs is absent (not an empty/placeholder value), and the omission is documented as an explicit decision.
**Depends on:** DS-07, DS-08

---

## Privacy, Analytics, Security & Consent — PRIV

### PRIV-01 — Cookieless, PII-free analytics  ·  P0  ·  EARS: ubiquitous
**User story:** As a privacy-conscious visitor, I want analytics that never identify me, so that browsing the manifesto site never costs me my privacy.
**EARS:** The analytics layer SHALL operate as cookieless, privacy-first measurement that collects no personally identifying information, sets no cross-site or persistent first-party tracking identifier, and performs no fingerprinting. WHERE a visitor's data is recorded, the analytics layer SHALL store only aggregate, anonymized event counts (page, referrer, country, device-class) with no per-visitor identity.
**Acceptance criteria:**
1. Inspecting all responses and client storage after a full session shows no cookie, localStorage, IndexedDB, or cache entry holding a per-visitor or cross-site identifier, and no fingerprinting API (canvas, WebGL, audio, font enumeration) is invoked.
2. A captured analytics payload contains only the enumerated aggregate fields (page, referrer, country, device-class) and no IP, email, hash, user-agent string, or any per-visitor identity token.
**Depends on:** none

### PRIV-02 — No cookie wall; opt-in for future non-essential  ·  P0  ·  EARS: state
**User story:** As a visitor, I want no blocking consent modal when none is legally required, so that content is never gated behind a needless wall.
**EARS:** WHERE the analytics layer is genuinely cookieless and PII-free, the consent system SHALL NOT present a blocking cookie-consent modal or interstitial that gates content. WHEN any future feature would set a non-essential cookie or load a non-essential third-party script, THEN the consent system SHALL require prior opt-in consent before that cookie is set or that script loads.
**Acceptance criteria:**
1. On first load with cookieless analytics active, no modal, interstitial, or scrim that blocks page interaction is rendered, asserted by checking no blocking-overlay element is present in the initial DOM.
2. A test that registers a synthetic non-essential cookie/script feature confirms the resource is not set or loaded until an explicit affirmative opt-in is recorded in the preference store.
**Depends on:** PRIV-03

### PRIV-03 — Persistent opt-out + first-party preference store  ·  P0  ·  EARS: event
**User story:** As a visitor, I want a durable control to disable optional analytics, so that my choice is honored now and on return.
**EARS:** The consent system SHALL provide an accessible, persistent control to disable all optional analytics. WHEN a visitor opts out, THEN the analytics layer SHALL stop emitting all measurement events for the remainder of the session and on subsequent visits, and the System SHALL record the opt-out as a first-party, strictly-necessary preference only in the `__pref` preference store.
**Acceptance criteria:**
1. After activating the opt-out control, network capture shows zero further analytics events for the rest of the session and on a subsequent reload of the same origin.
2. The opt-out is persisted solely in the first-party `__pref` store as a strictly-necessary flag, asserted by inspecting `__pref` content for the consent value and the absence of any tracking identifier.
**Depends on:** DS-01

### PRIV-04 — Minimal, unbundled email capture  ·  P1  ·  EARS: state
**User story:** As a visitor, I want the optional notify form to collect only my email with clear purpose, so that I am never bundled into unrelated processing.
**EARS:** WHERE the optional 'Get notified' email capture is presented, the email-capture component SHALL collect only an email address, SHALL require an explicit affirmative action with an adjacent purpose statement, and SHALL NOT pre-tick consent or bundle it with unrelated processing. WHEN an email is submitted, THEN the System SHALL transmit it over HTTPS to the single declared Get-notified endpoint and SHALL confirm submission without exposing the address to client-side third parties.
**Acceptance criteria:**
1. The form exposes exactly one email input plus an adjacent purpose statement, with no pre-ticked consent box and no field for unrelated processing, asserted by DOM inspection.
2. On submit, the email is sent only to the single declared Get-notified endpoint over HTTPS with no copy in any third-party client-side request, asserted by network capture.
**Depends on:** IA-03

### PRIV-05 — Transport hardening + security headers  ·  P0  ·  EARS: event
**User story:** As a visitor, I want every response served securely with hardened headers, so that the connection and document are protected by default.
**EARS:** The edge/server SHALL serve every response over HTTPS and SHALL set the security headers: Strict-Transport-Security (with a long max-age and includeSubDomains), X-Content-Type-Options: nosniff, Referrer-Policy: strict-origin-when-cross-origin, X-Frame-Options: DENY (or CSP frame-ancestors 'none'), Permissions-Policy denying camera/microphone/geolocation by default, and Cross-Origin-Opener-Policy: same-origin. WHEN an HTTP request arrives, THEN the edge SHALL 308-redirect it to HTTPS.
**Acceptance criteria:**
1. A header smoke-test asserts every listed header is present with the required value on a sampled set of routes (HTML, asset, API).
2. A request to the `http://` origin returns a 308 redirect to the `https://` equivalent, asserted by following the response status and Location header.
**Depends on:** none

### PRIV-06 — Strict CSP defaults  ·  P0  ·  EARS: complex
**User story:** As the site operator, I want a strict default CSP, so that injected or unauthorized scripts cannot execute.
**EARS:** The System SHALL enforce a Content-Security-Policy that defaults to `default-src 'self'`, authorizes scripts only via per-response nonces/hashes with `strict-dynamic`, sets `object-src 'none'`, `base-uri 'none'`, and `frame-ancestors 'none'`, and enables Trusted Types. WHERE inline scripts or styles are unavoidable, the CSP SHALL authorize them via per-response nonces rather than `unsafe-inline`, and SHALL NOT use a host-allowlist script-src.
**Acceptance criteria:**
1. A header smoke-test asserts the CSP contains `object-src 'none'`, `base-uri 'none'`, `frame-ancestors 'none'`, `strict-dynamic`, a Trusted Types directive, and a per-response nonce or hash, with no `unsafe-inline` token.
2. The same test asserts script-src contains no host/domain allowlist entry (no scheme-or-host source expression), confirming an allowlist-only CSP is not in use.
**Depends on:** PRIV-15

### PRIV-07 — SRI + near-zero third-party surface  ·  P1  ·  EARS: state
**User story:** As the site operator, I want self-hosting and SRI for any external asset, so that the third-party attack surface is driven toward zero.
**EARS:** WHERE the site loads any script or style from a non-same-origin source, the System SHALL apply Subresource Integrity (SRI) hashes and `crossorigin` attributes. The System SHALL prefer self-hosting for fonts, the Rive runtime, and analytics so that the third-party surface is as close to zero as practical.
**Acceptance criteria:**
1. A build-time check asserts every non-same-origin `<script>`/`<link rel=stylesheet>` carries a valid `integrity` hash and a `crossorigin` attribute.
2. An asset-origin audit confirms fonts, the Rive runtime, and the analytics client are served same-origin, asserted by enumerating loaded resource origins.
**Depends on:** PRIV-06

### PRIV-08 — Honor GPC/DNT signals  ·  P1  ·  EARS: event
**User story:** As a visitor who sets a browser privacy signal, I want it honored automatically, so that I need not also opt out in-page.
**EARS:** WHEN the browser presents a Global Privacy Control (`Sec-GPC: 1`) or `DNT: 1` signal, THEN the analytics layer SHALL suppress all optional measurement for that visitor by default without requiring an explicit in-page opt-out, and the consent system SHALL reflect the honored state in any privacy UI.
**Acceptance criteria:**
1. A request carrying `Sec-GPC: 1` (and separately `DNT: 1`) results in zero optional analytics events, asserted by network capture under each signal.
2. The privacy UI reflects the honored-signal state, asserted by inspecting the rendered consent control showing analytics as suppressed by signal.
**Depends on:** PRIV-03

### PRIV-09 — Accurate Privacy page  ·  P0  ·  EARS: ubiquitous
**User story:** As a visitor or regulator, I want a privacy page that exactly matches actual behavior, so that the disclosures are trustworthy.
**EARS:** The System SHALL publish a Privacy page that accurately describes all data processing (cookieless analytics, optional email capture, any sub-processors), the lawful basis under GDPR, the categories under CCPA/CPRA, retention, and the contact route for data-subject requests. The System SHALL keep the published policy in exact correspondence with the site's actual data behavior.
**Acceptance criteria:**
1. The Privacy page renders sections for analytics, email capture, sub-processors, GDPR lawful basis, CCPA/CPRA categories, retention, and a DSR contact route, asserted by presence checks on each section.
2. A correspondence test cross-checks the page's declared processors and behaviors against the live route manifest and analytics payload schema, failing if any declared behavior is absent or any actual behavior is undisclosed.
**Depends on:** IA-12

### PRIV-10 — Claims-clean footer trust note  ·  P1  ·  EARS: ubiquitous
**User story:** As a visitor, I want a footer trust note stating only true, verifiable facts, so that the site never makes unprovable claims.
**EARS:** The footer SHALL present a light trust/security note, rendered in the monospace machine-artifact style, that states only verifiable, presently-true facts about the site's posture (cookieless analytics, hardened transport, no sale of personal data). The footer note SHALL NOT publish any unverifiable count or claim, in keeping with the claims-integrity guardrail.
**Acceptance criteria:**
1. The rendered footer note text matches `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` zero times, asserted by a value-agnostic denylist regex over the note's text content.
2. Every factual assertion in the footer note maps to an entry in `content/claims-registry.json`, asserted by reconciling note claims against the registry.
**Depends on:** CONTENT-06

### PRIV-11 — Resilient, non-blocking failure  ·  P1  ·  EARS: unwanted
**User story:** As a visitor, I want failures in analytics or the form to never break the page, so that my experience stays smooth.
**EARS:** IF the analytics endpoint is blocked, fails, or times out, THEN the System SHALL fail silently with no console error surfaced to the visitor, no retry storm, and no impact on page interactivity or Core Web Vitals. IF the email-capture submission fails, THEN the email-capture component SHALL show an inline, accessible error state and SHALL NOT lose the entered value.
**Acceptance criteria:**
1. With the analytics endpoint forced to fail/time out, no uncaught console error appears, no more than the configured single attempt is made, and interactivity is unaffected, asserted by console capture and request-count assertion.
2. With the email endpoint forced to fail, an accessible inline error is shown (role/aria asserted) and the input retains its entered value, asserted by DOM inspection.
**Depends on:** none

### PRIV-12 — Accessible privacy UI (WCAG 2.2 AA)  ·  P1  ·  EARS: state
**User story:** As a visitor using assistive tech, I want the privacy UI to be fully accessible, so that I can manage my choices regardless of ability.
**EARS:** The consent and privacy UI SHALL meet WCAG 2.2 AA: keyboard operable, visible focus, AA contrast, and respectful of `prefers-reduced-motion`. WHERE any privacy UI animates (e.g. a notice slide-in or toggle transition), the motion SHALL be informational and SHALL have a static, legible reduced-motion fallback.
**Acceptance criteria:**
1. The consent control is reachable and operable by keyboard alone with a visible focus indicator and AA contrast, asserted by an automated accessibility scan plus keyboard-traversal test.
2. Under `prefers-reduced-motion: reduce`, privacy-UI animations are replaced by a static legible state, asserted by computed-style/snapshot comparison.
**Depends on:** DS-08

### PRIV-13 — Hardened, privacy-respecting email API  ·  P1  ·  EARS: event
**User story:** As the site operator, I want the email API hardened against abuse without tracking, so that capture stays safe and private.
**EARS:** The email-capture API SHALL validate and normalize input server-side, rate-limit by IP/identifier, and reject malformed or disposable-abuse submissions, using a privacy-respecting anti-abuse mechanism (e.g. honeypot + a privacy-preserving challenge such as a proof-of-work or Cloudflare Turnstile) rather than a tracking-based CAPTCHA. WHEN abusive volume is detected, THEN the API SHALL throttle without exposing whether a given address already exists.
**Acceptance criteria:**
1. Submissions that are malformed, disposable-domain, or fail the honeypot/challenge are rejected server-side, asserted by API responses to crafted inputs.
2. Repeated submissions for an existing vs. new address return indistinguishable responses under throttling, asserted by comparing status/body/timing so existence is not disclosed.
**Depends on:** PRIV-04

### PRIV-14 — Automated privacy/security verification gate  ·  P0  ·  EARS: complex
**User story:** As the site operator, I want a suite that proves live behavior matches every published claim, so that no unverified claim ships.
**EARS:** The System SHALL include an automated privacy/security verification suite that asserts the live behavior matches every published privacy/security claim (cookieless, headers present, CSP enforced, GPC honored, no PII leaked to analytics). WHERE any published claim cannot be verified by the suite, the System SHALL block that claim from publication until it can be evidenced.
**Acceptance criteria:**
1. The suite runs header smoke-tests, CSP-directive assertions, GPC/DNT suppression checks, and an analytics-payload PII-absence inspection, and reports pass/fail per claim.
2. The deploy gate fails closed when any asserted claim is unverified, asserted by injecting a deliberately violated claim and confirming the gate blocks.
**Depends on:** PRIV-01, PRIV-05, PRIV-06, PRIV-08

### PRIV-15 — Strict CSP from a single allowlist source  ·  P0  ·  EARS: ubiquitous
**User story:** As the site operator, I want the strict CSP generated from one source-of-truth allowlist, so that there is no drift and no bypassable host-allowlist script-src.
**EARS:** The site SHALL enforce a strict CSP — hash/nonce + `strict-dynamic`, `object-src 'none'`, `base-uri 'none'`, Trusted Types — generated from ONE `security/allowlist.ts` that enumerates every `connect-src` and feeds both header injection and the production `report-to` endpoint, and SHALL NOT be an allowlist-only/host-allowlist script-src CSP.
**Acceptance criteria:**
1. A header smoke-test asserts the emitted CSP contains strict directives (`strict-dynamic`, nonce/hash, `object-src 'none'`, `base-uri 'none'`, Trusted Types) with no `unsafe-inline` and no host-allowlist `script-src` entry.
2. A cross-domain no-drift test confirms the CSP and `connect-src` list emitted across environments derive identically from `security/allowlist.ts` (no environment hardcodes a divergent source list), and a prod `report-to` directive is present.
**Depends on:** PRIV-06, DS-01

### PRIV-16 — PII-free notify event + sub-processor register  ·  P1  ·  EARS: state
**User story:** As a visitor, I want the notify-success event to carry no PII and a published sub-processor register, so that I can verify exactly who processes my data and for how long.
**EARS:** WHERE a notify submission succeeds, the notify-success analytics event SHALL be PII-free (asserted by PRIV-14); and the site SHALL publish a machine-readable sub-processor register feeding `/privacy`, with documented retention and DSR handling.
**Acceptance criteria:**
1. A captured notify-success event payload contains no email, no hash of an email, and no per-visitor identifier, asserted by payload inspection against a PII denylist.
2. The machine-readable sub-processor register (with retention and DSR fields per entry) renders on `/privacy`, asserted by reconciling the register file against the entries shown on the rendered Privacy page.
**Depends on:** PRIV-14, IA-12

---

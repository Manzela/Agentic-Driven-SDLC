# Implementation Plan — autonomous-agent.dev (flagship website)

> **Scope:** Build tasks for the **public marketing/manifesto website** at `autonomous-agent.dev`.
> This is **NOT** the product implementation plan. The product's own tasks live under
> [`.kiro/specs/spec-to-evidence-control/tasks.md`](../../../.kiro/specs/spec-to-evidence-control/tasks.md).

**Materialized:** 2026-06-15 from `docs/plans/based-on-the-attached-eventual-cat.md` (PART B §B.3),
with PART D/E/G corrections applied.

**Totals:** 217 tasks. Each is ID'd (`T-<PREFIX>-NN`), traced to the requirement IDs it satisfies, and
carries an objective verification check.

**Phase-0 gates to build first** (the spec's own fail-closed ethos applied to its website):
referential-integrity gate (T-TOOL), value-agnostic claims-registry lint (CONTENT-06/T-DS-14),
strict-CSP header smoke-test (PRIV-15), runtime motion-integrity assertion (D7), and the AA contrast
matrix (T-DS-04). Provisional JS/CSS/INP budgets are non-gating until ratified (D7). CI-duration is a
non-gating alert. Lock the 8 Phase-0 decisions (PART F) before build.

**Domain index:** DS · IA · HOME · LOOP · CONTENT · PAGE · TECH · TOOL · PERF · A11Y · SEO · PRIV

---

## Brand & Design System — DS

- [ ] **T-DS-01** — Scaffold Style Dictionary token source and build to CSS vars + Tailwind v4 @theme  (→ DS-10, DS-01)
  - Author the base→semantic→primitive token JSON and the Style Dictionary build emitting CSS custom properties and the Tailwind v4 `@theme`.
  - Verify a clean build twice produces byte-identical output and exposes every named token (`--canvas`…`--signal`) with `--signal === --proven`.

- [ ] **T-DS-02** — Author DESIGN.md token contract and add drift + consistency CI checks  (→ DS-10, DS-01)
  - Write DESIGN.md as the human contract mirroring the Style Dictionary source.
  - Verify a drift check fails CI (non-zero exit) when committed generated CSS/Tailwind differs from a fresh build.

- [ ] **T-DS-03** — Add no-raw-literal lint for color/space/radius outside token sources  (→ DS-01, DS-06, DS-07)
  - Add a lint rule rejecting hex/rgb/hsl color literals and raw spacing/radius `px`/`rem` values outside token source files.
  - Verify the lint flags a seeded literal and passes on token-only code (zero literals in authored CSS/TSX/MDX).

- [ ] **T-DS-04** — Build the AA contrast pairing matrix and wire axe-core + unit contrast checks  (→ DS-02, DS-06)
  - Encode the pairing matrix as a tested artifact; lock --proven on --canvas ≈12.5:1, define canonical --error ≥3:1, mark --text-faint decorative/disabled-only.
  - Verify unit contrast tests assert each measured ratio and axe-core reports zero critical OR serious violations; a sub-AA pair fails the build.

- [ ] **T-DS-05** — Self-host, subset, and preload Geist Sans + Geist Mono with metric-matched fallbacks  (→ DS-04, DS-15)
  - Subset to WOFF2, serve same-origin, preload primary faces, add `font-display: swap` with `size-adjust`/`ascent-override` fallbacks.
  - Verify network capture shows zero third-party font requests and font-swap CLS < 0.01.

- [ ] **T-DS-06** — Implement fluid modular type scale as role tokens with weight cap  (→ DS-03, DS-18)
  - Define display/heading/body/label/caption role tokens with `clamp()` sizing, body 17–19px, display tracking -1.5px to -2px.
  - Verify no grotesk node computes a `font-weight` outside 300–600 and body resolves within 17–19px at desktop.

- [ ] **T-DS-07** — Build the <Artifact>/<Mono> primitive and MDX component map for machine artifacts  (→ DS-05, DS-12, DS-16)
  - Implement `<Mono>`/`<Artifact>` on `[data-artifact]` with tabular numerals and an MDX map routing IDs/hashes/records/code to them.
  - Verify mono font-family appears only on `[data-artifact]` nodes and never on prose.

- [ ] **T-DS-08** — Define spacing, radius, elevation, and container tokens and apply editorial rhythm  (→ DS-07)
  - Add base-grid spacing, radius, elevation/shadow, hairline-border, and container-width (~1200–1280px) tokens.
  - Verify the main container max-width resolves within 1200–1280px and no raw spacing/radius literals remain.

- [ ] **T-DS-09** — Define motion tokens and the motion-intent registry; scope Rive vs Framer  (→ DS-08)
  - Author duration/easing/state-semantic tokens as the single motion registry (DS-08); assign Rive to hero, Framer to micro-interactions.
  - Verify a runtime motion-integrity assertion fails for any animated element lacking a `data-motion-intent` registry mapping.

- [ ] **T-DS-10** — Author state-preserving reduced-motion and asset-failure static fallbacks  (→ DS-09, DS-17, DS-18)
  - Implement reduced-motion static equivalents (labeled loop diagram, filled coverage, held gate verdict) and asset-failure fallbacks.
  - Verify under emulated `prefers-reduced-motion: reduce` no element animates and each static equivalent is present in the DOM.

- [ ] **T-DS-11** — Build button, card, badge, and nav primitives with full interaction states  (→ DS-11, DS-13)
  - Implement soft-action buttons, cards/panels, status badges, and navigation with default/hover/active/focus-visible/disabled states from tokens.
  - Verify every interactive primitive is keyboard-operable with a measurable visible focus indicator.

- [ ] **T-DS-12** — Build the code/trace/evidence block primitive on --surface-2  (→ DS-12, DS-16)
  - Render line/column-aligned mono content on `--surface-2` with requirement-ID gutter, hash-chain affordance, and accessible copy/scroll; surface evidence/verdict fields as labeled data.
  - Verify test_file, test_name, output_hash, collected_at, and verdict render as labeled `[data-artifact]` nodes and no static quantified count is accepted.

- [ ] **T-DS-13** — Enforce the one-accent / accent-means-proven discipline via allowlist + review gate  (→ DS-06)
  - Maintain an allowlist of sanctioned accent contexts and a review gate blocking accent on decorative/marketing chrome.
  - Verify first-viewport accent pixels measure ≤3–5% per content route and no decorative node resolves to the accent token.

- [ ] **T-DS-14** — Add the claims-integrity guard for quantified verification claims  (→ DS-16)
  - Wire the component contract to reject hardcoded counts (require qualitative copy or harness-bound value+run-hash+collected_at); centralize claims in `content/claims-registry.json`.
  - Verify the denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` matches nowhere in rendered DOM or source.

- [ ] **T-DS-15** — Produce wordmark, icon set, favicon/app icons, and OG image from tokens  (→ DS-14)
  - Generate the wordmark variants, descriptor lockup, token-driven line-icon family, and OG image from brand tokens.
  - Verify all variants render in the gallery and the icon-exclusion check finds no unverifiable-claim or AI-glow icon.

- [ ] **T-DS-16** — Wire accessibility verification across primitives and pages  (→ DS-13)
  - Integrate axe-core and keyboard/focus checks across primitives and content routes.
  - Verify axe-core reports zero critical OR serious violations and state is never conveyed by color alone.

- [ ] **T-DS-17** — Implement loading, empty, and error state treatments  (→ DS-17)
  - Build calm skeletons on `--surface`/`--surface-2` and static token-styled fallbacks for Rive/font/trace asset failures.
  - Verify a forced asset failure renders the static equivalent with no `--error`/red token present.

- [ ] **T-DS-18** — Implement responsive breakpoints, collapsible nav, and degrading hero/trace  (→ DS-18)
  - Add breakpoints with fluid type/spacing, an accessible collapsible nav, and a hero/trace that degrades to a labeled diagram.
  - Verify from a 320px viewport upward there is no horizontal overflow on any content route.

- [ ] **T-DS-19** — Establish CWV performance budgets and CI enforcement  (→ DS-15, DS-04, DS-08)
  - Document and enforce LCP < 2.5s, CLS < 0.1, INP < 200ms budgets for the token+font+motion layer on a mid-tier profile.
  - Verify the build fails when any budget is exceeded and hero-load CLS contribution stays < 0.01.

- [ ] **T-DS-20** — Build the component gallery / living style guide as the brand contract surface  (→ DS-08, DS-09, DS-13)
  - Render every primitive, token, motion-intent entry, and reduced-motion fallback in a living style guide.
  - Verify the gallery exercises each interaction state and passes the same axe-core zero-critical-or-serious gate.

- [ ] **T-DS-21** — Generate the icon/manifest bundle from tokens with no white-flash  (→ DS-19)
  - Emit favicon.ico, 32px icon, opaque apple-touch-180, 192/512 + maskable icons via App-Router conventions, and a manifest with `theme_color` `#0A0B0D` plus light+dark `<meta name="theme-color">`.
  - Verify all icon sizes are present, the manifest parses with the correct `theme_color`, and first paint shows the `--canvas` background with no white-flash.

---

## Information Architecture & Navigation — IA

- [ ] **T-IA-01** — Author the typed route + section manifest as IA single source of truth in lib/routes.ts  (→ IA-01, IA-03)
  - Declare content routes, legal routes, section anchor ids, and content-presence flags in one typed table.
  - Test asserts the content-route set equals exactly {/, /how-it-works, /proof, /manifesto, /writing, /docs, /privacy, /terms}.

- [ ] **T-IA-02** — Implement canonical-origin and URL-hygiene redirects  (→ IA-02, IA-10)
  - Add middleware for casing/trailing/duplicate-slash → 308 and www/http/legacy → apex via the redirect table.
  - Test asserts /How-It-Works/ → 308 to https://autonomous-agent.dev/how-it-works and http/www variants → 301/308 to apex.

- [ ] **T-IA-03** — Build the persistent primary header (desktop inline + responsive disclosure)  (→ IA-03, IA-04, IA-05, IA-13)
  - Render allowed destinations inline at desktop and a focus-trapped disclosure below the breakpoint with aria-current.
  - Test asserts inline links at >=1024px, focus trap and aria-expanded at <1024px, and exactly one aria-current="page".
  - Render the category descriptor lockup beneath the wordmark (so a deep-link arrival reads the category immediately), pin or drop the condense behavior so it is deterministic, and keep /writing out of nav while it is stubbed.
  - Test asserts the descriptor lockup renders under the wordmark on every route, the condense behavior is deterministic (no jitter), and no nav item targets /writing while stubbed.

- [ ] **T-IA-04** — Build the global footer with soft Get notified and qualitative trust note  (→ IA-03, IA-12)
  - Render secondary nav to all destinations, one Get notified capture, and CONTENT-13-sourced trust copy.
  - Test asserts all destination links resolve and footer text matches no \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b.
  - Make the footer's single trust line the verbatim governing invariant (sourced from the shared CONTENT-11 constant) and ensure the footer owns the single Get-notified instance.
  - Test asserts the footer trust line is a byte-for-byte match of the governing invariant constant and that exactly one Get-notified control exists across the rendered page (footer-owned).

- [ ] **T-IA-05** — Add the no-funnel + claims-integrity content lint to CI  (→ IA-03, IA-12, IA-16)
  - Lint chrome markup and metadata against the funnel-affordance denylist and the claims regex.
  - Test asserts the lint fails on a seeded "12/12 verified" string and on a seeded "Pricing" nav item.

- [ ] **T-IA-06** — Implement anchor/section navigation with focus management and scroll-margin  (→ IA-06, IA-13)
  - Apply manifest section ids + scroll-margin; on activation update fragment and focus the heading.
  - Test asserts location.hash + heading focus on click, and an instant jump under prefers-reduced-motion: reduce.

- [ ] **T-IA-07** — Build Breadcrumbs component with BreadcrumbList JSON-LD  (→ IA-07, IA-13, IA-16)
  - Render breadcrumbs on nested routes with non-interactive aria-current final crumb and JSON-LD.
  - Test asserts breadcrumb on /writing/<slug>, none on /, and valid BreadcrumbList in the DOM.

- [ ] **T-IA-08** — Build the branded 404 (not-found) route  (→ IA-08, IA-13)
  - Implement not-found boundary preserving global nav and recovery links.
  - Test asserts GET /no-such-page returns 404 with nav and links to all canonical primary destinations.
  - Carry the verbatim governing invariant as the 404's trust line, in manifesto voice tied to the evidence thesis, and keep the page legible-as-an-error without alarm-red.
  - Test asserts the 404 body contains the byte-for-byte governing invariant and uses no alarm-red (--error) styling while still reading as an error state.

- [ ] **T-IA-09** — Build the branded 500 (global-error) route  (→ IA-09, IA-13)
  - Implement global-error boundary with no stack trace/env/internal id and a home link.
  - Test asserts forced error returns 500, body matches no stack/env/id pattern, and a link resolves to /.
  - Render the 500 in manifesto voice that reads as an error state within seconds without alarm-red styling.
  - Test asserts the 500 body uses no alarm-red (--error) styling while still reading as an error state.

- [ ] **T-IA-10** — Generate sitemap.xml and robots.txt programmatically  (→ IA-11, IA-16)
  - Build sitemap from indexable manifest routes; serve robots referencing it; register utility endpoints separately.
  - Test asserts sitemap lists only indexable content routes and robots.txt contains the Sitemap: directive.

- [ ] **T-IA-11** — Implement /docs and empty-/writing content-driven stub/empty states  (→ IA-15, IA-01)
  - Drive stub vs populated rendering from content-presence flags with intent copy + Get notified.
  - Test asserts empty section returns 200 with stub container, global nav, no article nodes, no availability claim.
  - Default the content-presence flag OFF at launch so /writing is fully absent (no route, no nav entry, no orphan link), and give the /docs stub live onward links to existing manifest routes alongside its single Get-notified affordance.
  - Test asserts that with the default flag /writing yields no route and no nav entry and is unreferenced by any link, while the /docs stub exposes live onward links resolving to existing manifest routes.

- [ ] **T-IA-12** — Implement skip link, landmarks, route-change focus, and loading states  (→ IA-13, IA-14)
  - Add landmarks, first-focus skip link, route-change focus move, and route-level skeleton loading.
  - Test asserts all four landmarks, visible-on-focus skip link, post-navigation focus, and axe zero critical OR serious.

- [ ] **T-IA-13** — Define per-route metadata and social-share templates  (→ IA-16, IA-02)
  - Derive unique title/description/canonical/OG/Twitter per route from the manifest.
  - Test asserts uniqueness, self-referential canonical, card tags, and no claims-denylist match in metadata.

- [ ] **T-IA-14** — Add an end-to-end IA/navigation audit suite (Playwright + axe)  (→ IA-01, IA-02, IA-08, IA-10, IA-11, IA-13, IA-16)
  - Cross-route Playwright + axe suite covering routes, redirects, 404/500, sitemap, landmarks, metadata.
  - Test asserts HTTP status codes, redirect Location headers, and axe zero critical OR serious across all content routes.

- [ ] **T-IA-15** — Implement unpublished-slug content-lifecycle redirect map  (→ IA-17, IA-10, IA-11)
  - On unpublish, write a 301→/writing (or 410) lifecycle entry and exclude the slug from sitemap and feed.
  - Test asserts removed slug returns 301/410, is absent from /sitemap.xml and /rss, and has a redirect-table entry.

- [ ] **T-IA-16** — Register /privacy and /terms legal routes in the manifest  (→ IA-18, IA-03, IA-12)
  - Add indexable, inNav:false, isLegal:true entries; wire footer legal links; exclude from exact-content-route test.
  - Test asserts /privacy and /terms return 200, are indexable and not in primary nav, footer links resolve, and the content-route test still passes.

---

## Homepage Scrollytelling Narrative — HOME

- [ ] **T-HOME-01** — Scaffold homepage as eight ordered beat sections with SSR copy and stable ids  (→ HOME-02, HOME-12)
  - Render eight `section` elements importing ids/ordinals from the IA-12 route/section manifest; populate copy from the content layer (CONTENT-06)
  - Assert with JS disabled that the response HTML contains exactly eight sections with contiguous `data-beat-ordinal` 1..8 in document order and non-empty ids matching the manifest

- [ ] **T-HOME-02** — Build ScrollNarrative provider tracking active beat and scroll progress  (→ HOME-02, HOME-15)
  - Implement a single rAF-coalesced driver computing active beat and clamped progress as a pure function of scroll position; expose active beat via `data-active-beat`/`aria-current`
  - Assert exactly one section is active at a time and DOM order is unchanged when active state toggles

- [ ] **T-HOME-03** — Implement shared ClosedLoop component with stage prop and static SVG fallback  (→ HOME-01, HOME-05, HOME-10)
  - Build one component with `stage` and `mode` props; static labeled SVG (intent->decompose->implement->verify->prove->gate) is the default and permanent fallback, animated layer mounts on load
  - Assert the six stage labels exist in static DOM and that simulated asset failure leaves the SVG visible with no alert/error/broken-image node

- [ ] **T-HOME-04** — Build Hero beat with headline-as-LCP, soft action, and reserved loop box  (→ HOME-01, HOME-12, HOME-13)
  - Render wordmark, one `h1` display headline (weight 300–600 per DS-07), subhead, "See how it works" anchor to `/how-it-works` (IA-03), and a reserved-dimension centerpiece mount-point
  - Assert all hero nodes exist in SSR HTML and that accent coverage in the first viewport measures ≤3–5% of pixels
  - Render the antagonist kicker present-at-first-paint above the dominant thesis `h1`, with the powering-stack moved out of the hero body to supporting weight, and mount the centerpiece loop cinematic (not pre-mounted to its gate state)
  - Assert the kicker node precedes the thesis `h1` in document order at first paint and reads at subordinate weight to it; assert the powering-stack does not appear in the hero body; assert the hero contains no `--proven` token and the loop's initial state is not the gate state

- [ ] **T-HOME-05** — Implement ProblemGrid consolidation as a deterministic scroll-bound state machine (desktop)  (→ HOME-03, HOME-14, HOME-15)
  - Map progress to discrete consolidation steps via a pure progress->state function; tag each step with `data-motion-state` from the DS-08 registry; pin on desktop and release cleanly
  - Assert replaying a progress value reproduces identical state, reverse-scroll replays steps in reverse, and pin-release produces CLS ≤ 0.1 with no trapped scroll
  - Build the betrayal sub-beat inside this section (the green-suite-lies micro-sequence: a suite reads green, merges, then surfaces as never wired into a live execution path) as a single quiet artifact-reveal with no alarm-red, and render at least a dozen named real tool tiles whose human-legible lead label is the primary label with the engineering spine string subordinated to it as a static-DOM caption
  - Assert the betrayal micro-sequence renders with no `--error`/alarm-red styling in any of its states; assert at least twelve named tool tiles are present; assert the human-legible lead label is the primary (higher-weight) label and the spine string is a subordinated caption in static DOM; assert Temporal renders outside the consolidated engine at progress=1.0

- [ ] **T-HOME-06** — Build ReplaceTable with the six role->substitute pairs and scroll-revealed rows  (→ HOME-04, HOME-14)
  - Author a real two-column table with the six pairs sourced from CONTENT-06; layer scroll reveal as presentation only (human->machine framing transition)
  - Assert all six pairs are readable in static DOM with JS disabled and that reduced-motion shows all rows resolved
  - Author the substitution grammar so the machine artifact text visibly replaces the human-labor text in each row, and name the per-edit enforcement on both the verifier cell and the auditor cell
  - Assert the resolved framing reads as substitution (machine text occupying where the human text was); assert no `--proven` token styles any row; assert both the verifier cell and the auditor cell carry per-edit naming

- [ ] **T-HOME-07** — Wire Closed-loop-explained beat (climax: "The line is held"): scroll-stepped stages with synchronized captions and the gate-holds beat  (→ HOME-05, HOME-14)
  - Advance the shared ClosedLoop through six stages in lockstep with progress; render per-stage captions and import gate-verdict copy from CONTENT-13
  - Assert the gate glow uses --proven/--accent (DS-01), the unproven item uses --text-faint, and no --error styling appears in any gate state
  - Compress stages 1–5 at roughly 3:1 so the gate reads as the arrival, make the held-item fade to `--text-faint` the primary signal, scope `--proven` to the verdict chip only, route the held item to a HANDOFF affordance distinct from COMPLETE, and drive the LOOP-07 four-beat gate choreography (approach → evaluate → hold/close → settle) with a success oracle
  - Assert stages 1–5 occupy roughly a third of the scroll allotted to the gate (gate as arrival); assert the held-item fade is the dominant signal and `--proven` appears only on the verdict chip; assert HANDOFF is a distinct node from COMPLETE; assert (mandatory) the reduced-motion static fallback renders the gate cell at 2× emphasis; assert the four named beats fire in order and the success oracle passes

- [ ] **T-HOME-08** — Build EvidenceTrace proof beat with four-field schema and pending->proven illumination  (→ HOME-06, HOME-13)
  - Render the four fields (test_file, test_name, output_hash, collected_at) inside `[data-artifact]` mono nodes, labeled illustrative sample data; illuminate to accent only when all four fields present
  - Assert mono appears only on `[data-artifact]` nodes and reduced-motion renders the record in its resolved proven state
  - Lead the beat with the self-administered auditor question co-framed for self-interest (could an auditor — and could you, later — prove this code did what it claimed and was independently verified), drive illumination by evidence completeness rather than scroll position, and show a single record plus its framing anchor
  - Assert the auditor question appears before the comparison framing; assert illumination is bound to all-four-fields-present, not to scroll progress; assert exactly one evidence record renders, labeled illustrative, alongside one framing anchor

- [ ] **T-HOME-09** — Enforce claims-integrity firewall on all homepage copy and metadata  (→ HOME-06, HOME-13, HOME-08)
  - Add a CI check running the denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` over rendered HTML and metadata; gate customer/logo claims behind content/claims-registry.json (CONTENT-06)
  - Assert the regex finds zero matches across the full rendered homepage and metadata

- [ ] **T-HOME-10** — Build The-leap beat with recede/resolve state transitions  (→ HOME-07)
  - Render four "removes" and three "guarantees" items from CONTENT-06; recede removes to muted/--text-faint, resolve guarantees to --proven/--accent
  - Assert both lists are readable as a static two-part list with JS disabled and resolve by default under reduced-motion
  - Render the beat as a static resolved two-column ledger with explicit group headers (structural contrast, not color alone) and completed guarantee noun phrases, dropping any "zero" prefix from the guarantee labels
  - Assert the two columns carry distinct text group headers (legible without color); assert each guarantee reads as a completed noun phrase and no guarantee label begins with "zero"

- [ ] **T-HOME-11** — Build Who-its-for beat with editorial audience framing and no funnel  (→ HOME-08)
  - Render editorial audience copy (aerospace, medical, finance, defense) from CONTENT-06; reserve logo-wall as a future evidence-gated slot
  - Assert no pricing/demo/contact-sales CTA, no `<form>`, no logo grid, and no sibling-subdomain link exist in the section
  - Open with a pain-hook (the standard "looks done is unacceptable") before any domain name, and include a no-lock-in micro-line
  - Assert the pain-hook text precedes the first domain name in document order; assert the no-lock-in micro-line is present in the section

- [ ] **T-HOME-12** — Build Soft-close with manifesto link and full notify state coverage  (→ HOME-09)
  - Render "Read the manifesto" (`/manifesto`) and "See how it works" (`/how-it-works`) links (IA-03) plus the PRIV-owned Get-notified control with submitting/success/error/already-subscribed states
  - Assert each notify state is independently renderable and that no site content is gated behind notify submission
  - Anchor the closing line back to the Beat-1 antagonist (resolving the betrayal arc) and make "See how it works" the primary affordance
  - Assert the close copy references the Beat-1 antagonist framing; assert "See how it works" is rendered as the primary action over the manifesto and notify affordances

- [ ] **T-HOME-13** — Implement reduced-motion + resolved-state-by-default across all beats  (→ HOME-10, HOME-14)
  - Drive reduced-motion from the DS-08 registry switch: disable pin/scrub and emit final resolved states for consolidation, gate-holds, proven illumination, and all rows
  - Assert under emulated prefers-reduced-motion that every motion-revealed state is present resolved and every motion-mode text string is equally assertable

- [ ] **T-HOME-14** — Implement responsive/touch variant: stacked reveals, scaled loop, single-column reflow  (→ HOME-11)
  - Below the DS desktop breakpoint, replace pinning with stacked in-view reveals, scale the loop to a labeled diagram, reflow replace-table and The-leap to single column
  - Assert no horizontal overflow (scrollWidth ≤ clientWidth) and that touch handlers do not preventDefault native scroll/momentum

- [ ] **T-HOME-15** — Implement progressive asset loading with reserved boxes and per-section static fallback  (→ HOME-12, HOME-01)
  - Serve copy + static fallbacks as static/ISR HTML; lazy-mount per-section motion via IntersectionObserver on approach; reserve dimensions for every deferred element
  - Assert deferred assets are not requested until approach, a forced 404 degrades only its section, and full-load+scroll CLS ≤ 0.1

- [ ] **T-HOME-16** — Add homepage SEO metadata, structured data, and social cards  (→ HOME-13)
  - Emit unique title, meta description, canonical at root (`/`, IA-03), OG/Twitter tags with image, and JSON-LD Organization/WebSite; expose all beat text in static HTML
  - Assert all metadata tags exist in the response and that no metadata/body string matches the verification-count denylist regex

- [ ] **T-HOME-17** — Produce and enforce the homepage motion inventory (state-machine, not decoration)  (→ HOME-14)
  - Author a motion inventory mapping each animation to a named state in the DS-08 registry; require every animated element to carry a registered `data-motion-state`
  - Assert the build fails if any animated element has a `data-motion-state` absent from the DS-08 registry, and that accent stays ≤3–5% of first-viewport pixels

- [ ] **T-HOME-18** — Harden scroll-state robustness with deterministic scrub and fragment resolution tests  (→ HOME-15, HOME-03, HOME-05)
  - Expose `data-motion-integrity` for a runtime assertion comparing rendered state to mapped progress; implement fragment seek into pinned/scrub ranges with pin intact
  - Assert under rapid scroll/reverse/anchor-jump there are no stuck/skipped/out-of-order states and the scroll handler stays within the performance budget

- [ ] **T-HOME-19** — Capture visual-regression frames at canonical narrative states  (→ HOME-01, HOME-03, HOME-05, HOME-10, HOME-12)
  - Capture reference frames for hero/static-fallback, full consolidation, gate-holds, proven evidence, and reduced-motion resolved layout
  - Assert each canonical state renders deterministically and matches its reference frame within tolerance

- [ ] **T-HOME-20** — Run Tier-1 accessibility, performance, and CWV verification on the homepage  (→ HOME-01, HOME-02, HOME-10, HOME-11, HOME-13)
  - Run axe/contrast checks (verify --proven on --canvas ≈12.5:1), CWV (LCP/CLS thresholds), reduced-motion and keyboard/fragment-nav audits
  - Assert contrast, CLS ≤ 0.1, LCP budget, reduced-motion final-state assertions, and accessible-name checks all pass

---

## Rive Closed-Loop Centerpiece + Evidence Trace — LOOP

- [ ] **T-LOOP-01** — Author the Rive ClosedLoop artboard and state-machine contract  (→ LOOP-02, LOOP-01)
  - Model the six named states + transitions and named inputs/triggers as the only host write surface, with the canonical traversal and 8–14s cadence input.
  - Contract test asserts each named state maps one-to-one to a declared stage and an unmapped state fails.
  - Author one state machine carrying both playback modes (hero autonomous traversal and Beat-5 scroll-driven), keep the moving layer to geometry and accent only, and place all tool names on the stationary artifact panel outside the motion layer.
  - Assert a single state-machine source drives both playback modes; assert the motion layer's artboard contains no tool-name text nodes (tool names live only on the stationary panel).

- [ ] **T-LOOP-02** — Build ClosedLoop host wrapper with typed Rive bindings  (→ LOOP-02, LOOP-01, LOOP-09)
  - Wrap the runtime with typed input/trigger bindings; route all display changes through them, no CSS/Framer motion for progression.
  - Runtime motion-integrity assertion confirms every observed animation corresponds to a named state.
  - Render the host as a separated moving layer (geometry + accent) over a stationary copy/artifact panel that owns the tool/stage labels, and expose the hero-autonomous and scroll-driven cadences as two playback modes of the same single state machine.
  - Assert the moving layer and the stationary artifact panel are distinct DOM/render layers with no tool names inside the moving layer; assert both playback modes resolve to one state-machine instance (single source of truth).

- [ ] **T-LOOP-03** — Create the illustrative loop fixture and requirement-token rendering  (→ LOOP-04, LOOP-13)
  - Commit a fixture modeled on the real evidence schema and render tokens only on [data-artifact] mono nodes.
  - Test asserts token color is --pending before completion and --proven only after its fixture record is complete.

- [ ] **T-LOOP-04** — Build the EvidenceTrace panel with hash-chained four-field records  (→ LOOP-05, LOOP-13, LOOP-12)
  - Render an append-only DOM list exposing test_file, test_name, output_hash, collected_at with each record linking the prior hash.
  - Test verifies the four fields are present as text and chain order is tamper-evident in the DOM.

- [ ] **T-LOOP-05** — Couple loop prove-events to evidence-trace appends (lockstep bus)  (→ LOOP-04, LOOP-05)
  - Emit a prove event on token completion and subscribe the trace to append in lockstep, lighting ID + output_hash to --proven.
  - Test asserts no record precedes its token and none is missing after proving.

- [ ] **T-LOOP-06** — Implement the fail-closed gate choreography (satisfying, accent-as-correct)  (→ LOOP-06, LOOP-07, LOOP-09)
  - Drive named beats approach → evaluate → hold/close (accent) → settle, dim held items to --text-faint/--pending, read verdict/reason copy from CONTENT-13.
  - Frame-sequence test asserts --proven on the gate at hold-frame and zero red hue across the whole window.

- [ ] **T-LOOP-07** — Bind centerpiece colors to tokens and add the color/claims audit test  (→ LOOP-09, LOOP-13)
  - Resolve all color from DS tokens (--proven #34E1A0 / --pending / --text-faint, weights 300–600); pull claims from content/claims-registry.json.
  - Audit fails on inline hex, extra saturated hue, stray alarm-red, OR any match of `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b`.

- [ ] **T-LOOP-08** — Build the static SSR fallback diagram and error boundary  (→ LOOP-08, LOOP-11, LOOP-12, LOOP-16)
  - Server-render the fully-labeled diagram (six stages, gate holding, ≥1 proven + ≥1 held token, representative records) as the default; hydrate the canvas over it.
  - No-JS and forced-Rive-failure tests confirm the static node carries the same information with no canvas mounted.

- [ ] **T-LOOP-09** — Add accessible text-equivalent and ARIA semantics for the centerpiece  (→ LOOP-12)
  - Expose ordered stages, fail-closed gate behavior, and ≥1 proven + ≥1 held token via roles/names/descriptions; make records navigable text.
  - axe-core run reports zero violations and the a11y tree exposes the six ordered stages and gate behavior.

- [ ] **T-LOOP-10** — Implement optional synchronized interaction with auto-resume  (→ LOOP-10, LOOP-12)
  - Drive pause/resume and stage/token focus through named Rive inputs via pointer + keyboard, cross-highlighting the matching record both ways.
  - Test asserts bidirectional highlight sync and auto-resume after a bounded idle period.

- [ ] **T-LOOP-11** — Implement responsive layout and small-screen degradation  (→ LOOP-11, LOOP-08)
  - Side-by-side at the large breakpoint; stacked simplified-but-labeled loop + trace at the small breakpoint preserving all labels and gate semantics.
  - Capture below the legibility threshold confirms fallback to the static labeled diagram, not an illegible animation.

- [ ] **T-LOOP-12** — Code-split Rive, reserve layout, enforce asset and CWV budgets  (→ LOOP-14, LOOP-16)
  - Lazy-load the runtime/asset after first paint into a pre-reserved box; enforce an asset load-time budget and save-data/low-power detection.
  - Test asserts CLS contribution = 0 and that budget/save-data conditions render the static fallback with no canvas.

- [ ] **T-LOOP-13** — Gate playback on viewport intersection and page visibility  (→ LOOP-15, LOOP-14)
  - Start playback only on viewport intersection; pause when out of view or tab hidden; resume from a coherent state.
  - Test asserts no autoplay before scroll and correct pause/resume on visibility change.

- [ ] **T-LOOP-14** — Implement loading skeleton and evidence empty/awaiting state  (→ LOOP-16, LOOP-05)
  - Show a calm labeled skeleton (six labels, neutral --pending) and a labeled evidence awaiting state during load.
  - Test asserts no blank panel/spinner-only and resolution to the static fallback on budget overrun or failure.

- [ ] **T-LOOP-15** — Build the three-goals acceptance harness and visual-regression captures  (→ LOOP-03, LOOP-01, LOOP-06, LOOP-04, LOOP-05)
  - Capture deterministic frames and assert legibility (six labels ≥ min px, AA contrast, distinct positions), satisfying gate (accent at hold-frame, no red across the sequence), and artifact-driven proving.
  - Wire the captures into CI as the binding oracle for LOOP-03's three concurrent goals.

- [ ] **T-LOOP-16** — Implement the per-state tool layer and reduced-motion static map  (→ LOOP-17)
  - Add a Rive `tool` layer over the six canonical stages in their fixed order intent→decompose→implement→verify→prove→gate (gate is the last node; there is no seventh "Spec" node) so each stage surfaces its named tool label only while active, and annotate the Implement node with the PreToolUse/PostToolUse hooks and the Gate node with the Stop/SubagentStop hooks; build the reduced-motion static node → tool mapping as DOM text carrying the same six named tool labels.
  - Visual-regression at each named state asserts the six stages render in canonical order with gate last (no "Spec" node), that each stage's named tool label is present and shown alone (no concurrent parade), and that the six official Claude Code hook names (PreToolUse, PostToolUse, UserPromptSubmit, SubagentStop, Stop, SessionStart) appear on the Implement and Gate nodes; the reduced-motion test asserts the full static map is present and names each stage's tool label.

---

## Content, Copy & Claims Integrity — CONTENT

- [ ] **T-CONTENT-01** — Author the Voice Spec and machine-readable deny/allow lexicons  (→ CONTENT-01)
  - Write voice-spec.json with deny/allow word lists and structural rules; build the copy-lint that imports it.
  - Verify: lint fails on a fixture containing 'game-changing' and an exclamation mark, passes on an evidence-term fixture.

- [ ] **T-CONTENT-02** — Build the headline/subhead candidate matrix and hero binding  (→ CONTENT-02)
  - Create the ranked candidate matrix with corpus tags and length budget; bind the hero to the top pair.
  - Verify: test asserts rendered strings are matrix members and line-box counts pass at 360px (<=3) and 1024px (1).

- [ ] **T-CONTENT-03** — Implement ReplaceTable from the six canonical rows  (→ CONTENT-03)
  - Freeze the six-row data file and render rows with <Mono data-artifact> on machine artifacts.
  - Verify: set-equality test on the six label pairs; mono resolves only on [data-artifact] nodes.

- [ ] **T-CONTENT-04** — Implement TheLeap two-group bullet module  (→ CONTENT-04)
  - Render eliminations (4) and guarantees (3) from fixed arrays as noun-phrase bullets.
  - Verify: noun-phrase shape check passes and digit scan returns zero in the module.

- [ ] **T-CONTENT-05** — Build the corpus-to-module mapping registry and assertion  (→ CONTENT-05)
  - Author corpus-map.json covering 16 domains, 7 gaps, B01-B19, invariant, evidence schema, verifier; inject non-rendered citations.
  - Verify: referential-integrity assertion fails on an orphan element and on a dangling citation.

- [ ] **T-CONTENT-06** — Build the claims ledger and claims-integrity gate  (→ CONTENT-06)
  - Create content/claims-registry.json and the gate that reads it; implement the value-agnostic tally denylist regex and qualitative/harness-bound Z3 claim.
  - Verify: build fails on an unverifiable quantified claim; regex blocks 21/21, 32/32, 34/34, 100/100.

- [ ] **T-CONTENT-07** — Implement machine-artifact components and evidence schema  (→ CONTENT-07)
  - Build <Mono data-artifact> and <EvidenceRecord> exposing test_file, test_name, output_hash, collected_at; scope the mono token to [data-artifact].
  - Verify: lint fails if mono appears in prose or an evidence record omits any of the four fields.

- [ ] **T-CONTENT-08** — Implement readability budget check and inline glossary  (→ CONTENT-08)
  - Build the median-sentence-length analyzer and the jargon first-use glossary scanner.
  - Verify: a page with median >22 words fails; a flagged jargon term without inline definition fails.

- [ ] **T-CONTENT-09** — Implement <SoftCTA> allowlist and banned-CTA scan  (→ CONTENT-09)
  - Implement <SoftCTA> accepting only allowlisted labels; defer 'Get notified' action to PRIV.
  - Verify: scan fails on a 'Request a demo' CTA and finds zero funnel terms in approved fixtures.

- [ ] **T-CONTENT-10** — Author the microcopy/state catalog for non-happy paths  (→ CONTENT-10)
  - Populate the states catalog (error/loading/empty/fallback) with approved fail-closed framing.
  - Verify: coverage check confirms every interactive component state has microcopy; pending strings pass Voice Spec lint.

- [ ] **T-CONTENT-11** — Author the numbered manifesto MDX with verbatim invariant  (→ CONTENT-11)
  - Write /manifesto as numbered MDX sections; store the governing invariant as a shared constant.
  - Verify: section-presence test for the five spine elements; byte-for-byte invariant match.
  - Verify: a presence check that the enforcement layer is described — the six official Claude Code hooks are named (PreToolUse, PostToolUse, UserPromptSubmit, SubagentStop, Stop, SessionStart), command hooks are characterized as fail-closed with the honest limit stated (a hook can block a tool call but cannot by itself prove the work is correct) — and that the proof-of-execution versus proof-of-correctness distinction is drawn explicitly.
  - Lead §1 with the antagonist (self-report is not evidence) before any solution framing, and present the HANDOFF self-correction as a trust beat (not an error footnote).
  - Verify: the §1 antagonist framing precedes the first solution/mechanism statement; verify the HANDOFF passage is framed as a trust signal in body voice rather than as an error footnote.

- [ ] **T-CONTENT-12** — Generate per-page metadata from on-page claims  (→ CONTENT-12)
  - Build the metadata generation step deriving title/description/OG/JSON-LD from ledger claims.
  - Verify: metadata passes Voice Spec + tally denylist; a metadata number absent from the ledger fails the build.

- [ ] **T-CONTENT-13** — Author terminology/style sheet, consistency linter, and gate-verdict copy  (→ CONTENT-13)
  - Author terminology.json (brand/casing/token format + canonical gate-verdict copy) and the consistency linter.
  - Verify: linter fails on a disallowed synonym; all verdict strings resolve from the single style sheet.
  - Verify: the linter asserts the canonical six-stage order intent→decompose→implement→verify→prove→gate (gate last) and the single canonical gate caption ("Stop hook holds locally; OPA/Conftest zero-evidence policy at merge; GitHub ruleset makes both required") across HOME, LOOP, and PAGE surfaces, so a regression that places gate before verify — or that drifts the gate caption (as LOOP-17 could) — fails the build.
  - Author the green-rationing rule (the `--proven` token is permitted only at the gate verdict chip and the completed evidence record) and the canonical held-item/HANDOFF verdict-chip copy in the style sheet, and lint both.
  - Verify: the linter fails on a `--proven` token used outside the gate verdict chip or completed evidence record, and fails when the HANDOFF verdict-chip copy drifts from the single canonical string in the style sheet.

- [ ] **T-CONTENT-14** — Implement Who-it's-for module with anti-fabrication assertion  (→ CONTENT-14)
  - Render audience/role/industry framing from data; gate any numeric social proof through the ledger.
  - Verify: assertion confirms zero logo <img> and zero testimonial/named-adopter strings.

- [ ] **T-CONTENT-15** — Implement text equivalents for motion and machine artifacts  (→ CONTENT-15)
  - Add the four-state Rive caption, evidence-panel summaries, image alt text, and reduced-motion fallback captions.
  - Verify: presence lint fails if the centerpiece caption or evidence summary is missing on any route.

- [ ] **T-CONTENT-16** — Compose and wire the fail-closed pre-publish content gate  (→ CONTENT-16)
  - Compose all content checks into one no-override CI gate emitting page+location on failure.
  - Verify: removing any sub-check or injecting one violation exits non-zero; a forced override still fails.

- [ ] **T-CONTENT-17** — Add integrator thesis and displacement-phrase denylist  (→ CONTENT-17)
  - Place the integrator thesis in the copy deck and inject into hero + manifesto §1; add the displacement denylist to the lint.
  - Verify: copy-lint asserts thesis present in both locations and zero displacement-phrase matches site-wide.

- [ ] **T-CONTENT-18** — Implement the <PoweredBy> machine-artifact module  (→ CONTENT-18)
  - Build <PoweredBy> reading the committed PRD stack manifest, rendering each entry as a mono [data-artifact] node that shows the tool name, the B-block ID it serves, and a one-line pain-point tie.
  - Verify: every manifest entry exposes tool name + B-block ID + one-line pain-point tie as labeled [data-artifact] text; membership-by-name assertion passes for the six official Claude Code hooks (PreToolUse, PostToolUse, UserPromptSubmit, SubagentStop, Stop, SessionStart), the four subagents (initializer, implementer, verifier, and the gate/orchestrator subagent), OWASP ZAP, DeepEval, OpenFeature/flagd, gitleaks, and Hypothesis; DOM/numeric scan confirms zero logo <img> and zero numeric stat strings.
  - Place the module as the immediate sequel to the fragmented-stack collapse (the "what's in the box?" reveal) and gloss each B-block ID in human-legible terms alongside its retained code.
  - Verify: the module renders in document order immediately after the collapse section; verify each B-block ID carries a human-legible gloss string adjacent to the retained ID.

- [ ] **T-CONTENT-19** — Author the vendor-neutral / no-lock-in content block  (→ CONTENT-19)
  - Author the shared no-lock-in block (feature_list.json, EvidenceRecord, requirement-ID Baggage, "opinionated defaults, not a cage") on /how-it-works and the manifesto; register the claim in the ledger.
  - Verify: copy-presence check passes on both pages and the claim resolves to a claims-ledger entry with a corpus citation.
  - Include a concrete EvidenceRecord JSON glimpse with a human gloss (including a gloss of "W3C Baggage"), and render the full no-lock-in triple (feature_list.json, EvidenceRecord, requirement-ID Baggage) on both /how-it-works AND the manifesto.
  - Verify: a literal EvidenceRecord JSON snippet plus its adjacent human gloss is present (and "W3C Baggage" is glossed); verify all three triple elements appear on /how-it-works and on the manifesto.

---

## Supporting Pages — PAGE

- [ ] **T-PAGE-01** — Scaffold (site) route group and shared supporting-page shell  (→ PAGE-01, PAGE-11, PAGE-13)
  - Create the `(site)` route-group layout with header, soft-action footer, and a single Get-notified slot; resolve footer links against the IA route manifest.
  - Assert the shell renders identically across all supporting routes and exposes exactly one Get-notified control (DOM control inventory).
  - Keep print stylesheets out of the shell scope (declared per-route only) and let the footer own the single Get-notified instance for the whole shell.
  - Assert no print stylesheet is attached at the shell layer (any print styles are route-scoped) and that the shell exposes exactly one footer-owned Get-notified control.

- [ ] **T-PAGE-02** — Build typed claims registry with corpus references  (→ PAGE-03, PAGE-06, PAGE-08)
  - Define `content/claims-registry.json` as the single source of truth with typed claim keys and corpus references.
  - Assert every quantitative claim rendered on a supporting page resolves to a registry key (no orphan claims).

- [ ] **T-PAGE-03** — Add build-time unverifiable-claim guard  (→ PAGE-08)
  - Add a build step scanning rendered supporting-page text with the value-agnostic denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b`.
  - Assert the build exits non-zero when a seeded "N/N verified" string is present and exits zero when removed.

- [ ] **T-PAGE-04** — Implement six-stage loop explainer on /how-it-works  (→ PAGE-01, PAGE-12)
  - Render six ordered stages from a typed manifest with plain-language, mechanism, and `[data-artifact]` artifact; pull gate framing from CONTENT-13.
  - Assert exactly six ordered stage nodes and gate copy equals the CONTENT-13 verdict string (no error-toned wording).
  - Assert a build check that the stages appear in canonical order intent→decompose→implement→verify→prove→gate (gate last) and that each of the six stages names at least one controlled-vocabulary mechanism — intent: EARS→SMT spec compiler; decompose: initializer subagent + feature_list.json; implement: implementer subagent + worktree + PreToolUse gates; verify: verifier subagent + SubagentStop; prove: Evidence_Record + audit log + Z3; gate: Stop hook + OPA/Conftest + GitHub ruleset — and that the strict gate sequencing (gate evaluates last, after prove) is named.

- [ ] **T-PAGE-05** — Implement B01-B19 capability taxonomy  (→ PAGE-02)
  - Render 19 blocks grouped into named clusters with label, one-line description, and `[data-artifact]` mono block ID.
  - Assert IDs B01-B19 are complete and unique and mono styling appears only on `[data-artifact]` nodes.
  - Align the named clusters one-to-one onto the six canonical loop stages (intent→decompose→implement→verify→prove→gate), framed as the same loop at higher resolution rather than a flat catalog.
  - Assert the cluster set maps onto the six loop stages (each cluster labels its owning stage; gate stage owns its cluster last) with no cluster left unmapped.

- [ ] **T-PAGE-06** — Build /proof information spine  (→ PAGE-03, PAGE-08)
  - Render the four ordered titled sections and the exact four-field evidence schema on `[data-artifact]` nodes.
  - Assert section order by ordinal and that the denylist regex matches zero times.
  - Assert a presence check that the enforcement layer is named — the six official Claude Code hooks (PreToolUse, PostToolUse, UserPromptSubmit, SubagentStop, Stop, SessionStart), with command hooks framed as fail-closed and the honest limit stated (a hook can block a step but cannot by itself establish correctness) — and that the proof-of-execution versus proof-of-correctness distinction is present on the page.
  - Open the spine with the auditor test as the challenge, then answer it with invariant → schema → independent-verifier in that order.
  - Assert the auditor-test challenge node precedes the invariant/schema/verifier answer in document order.

- [ ] **T-PAGE-07** — Implement EvidenceTrace state machine and sample dataset  (→ PAGE-04, PAGE-12)
  - Build the hash-chained, requirement-ID-tagged trace with per-row unproven → evidence-attached → proven and a terminal gate evaluation bound to `data-state`.
  - Assert gate-held color equals the `--proven` token (#34E1A0) and no `COMPLETE` node exists while any item is unproven.
  - Render a bridge sentence above the trace (reframing gate-green as held-correct at first contact), style evidence-pending rows with the `--pending` token, and route the held item to a HANDOFF state distinct from COMPLETE.
  - Assert a bridge sentence node precedes the trace; assert evidence-pending rows carry `--pending`; assert HANDOFF is a distinct `data-state` from COMPLETE.

- [ ] **T-PAGE-08** — Make EvidenceTrace accessible, no-JS safe, and state-complete  (→ PAGE-05, PAGE-15)
  - Add keyboard operability, server-rendered static fallback, and explicit loading/ready/error/static states with a legible malformed-data fallback.
  - Assert no-JS render contains the full labeled trace and forced-error render shows a non-empty fallback with zero critical/serious axe violations.

- [ ] **T-PAGE-09** — Establish shared motion-as-information contract and reduced-motion harness  (→ PAGE-12, PAGE-13)
  - Wire all animations to read from the single motion registry DS-08 and bind to `data-state`; enforce DS-09 reduced-motion globally.
  - Assert no animation runs without a bound state and that reduced-motion yields zero-duration transitions with state labels preserved.

- [ ] **T-PAGE-10** — Build MDX pipeline and brand component allowlist  (→ PAGE-06, PAGE-14)
  - Configure MDX to render only the four allowlisted brand components and reject/strip anything else, including raw HTML and scripts.
  - Assert a fixture with a non-allowlisted component fails the build and that zero inline scripts/handlers reach the DOM.

- [ ] **T-PAGE-11** — Author and render /manifesto essay with reading aids  (→ PAGE-06, PAGE-07)
  - Author the numbered-section MDX essay with copyable anchors and a scroll-derived non-decorative progress indicator; constrain display weights to 300–600.
  - Assert sequential heading numbers, monotonic progress at 0/50/100% scroll, and anchors resolving to existing IDs.
  - Implement the reading aid as a named-section side-rail (IntersectionObserver-driven, listing the section names with the active section marked), not a percentage progress bar.
  - Assert the side-rail lists each numbered section by name and marks exactly one active section on scroll, with no percentage-progress element present.

- [ ] **T-PAGE-12** — Implement optional /writing index and articles behind a flag  (→ PAGE-09, PAGE-16)
  - Gate /writing behind a build-time flag; render date-sorted index when populated, deliberate empty state when empty, full absence when disabled.
  - Assert descending date order when populated and full route+nav absence when the flag is off.
  - Default the flag OFF at launch (route and nav entry both absent, no orphan link) and drop any reading-time label from the index, rendering a human-readable date (ISO in the `datetime` attribute).
  - Assert that with the default flag the /writing route and its nav entry are both absent and no link targets it; assert no reading-time string renders and each entry date is human-readable with ISO in `datetime`.

- [ ] **T-PAGE-13** — Build /docs honest placeholder stub  (→ PAGE-10, PAGE-16)
  - Render a forthcoming-docs placeholder with `noindex`, zero dead links, and only the soft Get-notified affordance.
  - Assert no anchors point to non-existent doc routes and no pricing/demo/sales controls exist.
  - Add live onward links (to /how-it-works, /proof, /manifesto, resolved against the IA route manifest) alongside the single Get-notified affordance so the stub is not a dead end.
  - Assert the stub renders live onward links each resolving to an existing manifest route, alongside exactly one Get-notified control.

- [ ] **T-PAGE-14** — Add branded 404, error boundary, and internal link checker  (→ PAGE-16)
  - Implement the branded not-found/error boundary with IA-resolved soft nav and a build-time internal-link validator.
  - Assert a non-existent route returns the branded 404 with live soft-nav links and the link checker fails on a seeded dead link.

- [ ] **T-PAGE-15** — Implement single Get-notified soft-conversion component  (→ PAGE-11)
  - Build one Get-notified capture with loading/success/error/validation states reused from the shell; no funnel or sales controls anywhere.
  - Assert at most one capture per page and zero pricing/demo/sales-contact controls site-wide.

- [ ] **T-PAGE-16** — Add contextual soft cross-navigation between supporting pages  (→ PAGE-11)
  - Add onward links between supporting pages and to /manifesto, resolved against the IA route manifest.
  - Assert every onward href targets a manifest route and all controls are keyboard-operable with visible focus.

- [ ] **T-PAGE-17** — Add per-page SEO metadata and JSON-LD structured data  (→ PAGE-13)
  - Add per-page titles/meta and a valid JSON-LD block to each supporting page.
  - Assert each page's JSON-LD parses and validates against its schema type.

- [ ] **T-PAGE-18** — Configure security headers and CSP for supporting pages  (→ PAGE-13)
  - Set CSP, X-Content-Type-Options, Referrer-Policy, and HSTS for the supporting routes.
  - Assert the required headers are present and the CSP blocks third-party font/script origins.

- [ ] **T-PAGE-19** — Set up CI gates: Lighthouse, axe-core, responsive snapshots, motion integrity  (→ PAGE-05, PAGE-12, PAGE-13)
  - Wire CI to run Lighthouse CWV, axe-core, responsive snapshots, and a motion-integrity check across supporting pages.
  - Assert CWV thresholds (LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms) and axe zero critical OR serious; CI fails on regression.

- [ ] **T-PAGE-20** — Self-host fonts and wire Style-Dictionary tokens into supporting pages  (→ PAGE-13)
  - Self-host fonts same-origin and consume DS tokens (DS-01/DS-07) including canonical `--error` and `--proven` #34E1A0; restrict `--text-faint` to decorative/disabled.
  - Assert zero third-party font requests and zero off-token hardcoded hex values in supporting-page styles.

- [ ] **T-PAGE-21** — Add print stylesheet for /manifesto and /proof  (→ PAGE-17)
  - Add a token-mapped `@media print` stylesheet that switches to a light theme, expands `[data-artifact]` hashes to full value, and hides decorative canvas/motion.
  - Run a print-emulation snapshot asserting a light background and full (non-truncated) hashes with decorative motion not displayed.

---

## Tech Stack & Front-end Architecture — TECH

- [ ] **T-TECH-01** — Scaffold Next.js App Router project with strict TS, route group, and module/path-alias boundaries  (→ TECH-01, TECH-02)
  - Create `app/(site)/` with root `layout.tsx`, derive segments from `lib/routes.ts`, and set strict `tsconfig.json` plus path aliases.
  - Add a CI test asserting every content route in `lib/routes.ts` resolves to a `page.tsx` under `app/(site)/` and that no stray `page.tsx` exists outside the manifest; build fails on mismatch.

- [ ] **T-TECH-02** — Define core domain types: EvidenceRecord, requirement IDs, LoopState (with gate sub-states), Zod schemas  (→ TECH-02, TECH-13)
  - Implement `lib/types` with `EvidenceRecord`, `RequirementId`, `LoopState` (members `intent|decompose|implement|verify|prove|gate`, gate carrying a typed sub-state union), `MdxFrontmatter`, each paired with a Zod validator.
  - Add a type-level test (`tsd`/`expect-type`) that compiles valid shapes and rejects malformed ones; verify `next build` fails when a deliberate type error is introduced.

- [ ] **T-TECH-03** — Wire Style Dictionary → Tailwind v4 token theme with one-accent and mono-artifact enforcement  (→ TECH-03, TECH-14)
  - Build CSS custom properties from `design/tokens/*.json` (incl. `--canvas`/`--surface`/`--surface-2`/`--border`/`--text`/`--text-muted`/`--text-faint`/`--proven`/`--pending`/`--error`) and configure Tailwind `@theme` to reference only `var(--…)`.
  - Add a CSS-parse test asserting all ten semantic tokens are present and sourced from the Style Dictionary output, that no literal hex appears in components, that `[data-artifact]` resolves to mono, and that the only accent referenced is `--proven`.

- [ ] **T-TECH-04** — Self-host Geist Sans + Geist Mono via next/font/local with size-adjusted fallbacks  (→ TECH-14, TECH-03)
  - Load both families via `next/font/local` with `font-display: swap`, metric-compatible fallbacks, weights 300–600, exposed as CSS-variable tokens consumed by the Tailwind theme.
  - Add a test asserting no runtime external font requests, that `[data-artifact]` computes to a mono family even pre-swap, and a web-vitals check confirming font-swap CLS ≈ 0.

- [ ] **T-TECH-05** — Build the `<Mono>`/`<RequirementId>`/`<EvidenceRecord>` machine-artifact components  (→ TECH-03, TECH-04)
  - Implement the three components emitting `data-artifact` nodes typed against `EvidenceRecord`/`RequirementId`, with mono token applied by construction.
  - Add a render test asserting each component marks its output `[data-artifact]`, resolves to mono, and type-checks against the domain shapes (invalid props fail compilation).

- [ ] **T-TECH-06** — Implement reduced-motion/theme context and the static labeled closed-loop diagram  (→ TECH-07, TECH-12)
  - Build a `'use client'` reduced-motion/theme context and a static fully-labeled `intent→decompose→implement→verify→prove→gate` diagram with text equivalents for every machine artifact.
  - Add a Playwright test under emulated `prefers-reduced-motion: reduce` asserting the static diagram renders with selectable artifact text and no animation autoplays.

- [ ] **T-TECH-07** — Build the Rive ClosedLoop wrapper: dynamic ssr:false, intersection-gated, CLS-safe, typed states  (→ TECH-05, TECH-06, TECH-09)
  - Implement `components/loop/ClosedLoop.tsx` via `next/dynamic({ ssr: false })`, IntersectionObserver-gated, in a fixed-aspect reserved container showing the static fallback until the `.riv` resolves; type the state machine against `LoopState`.
  - Add tests asserting the module is absent from server HTML, loads only after hero intersection, holds CLS ≤ 0.01, and renders the fallback (not a crash) when forced to throw.

- [ ] **T-TECH-08** — Create the motion registry and wire Framer Motion informational micro-interactions  (→ TECH-06, TECH-07)
  - Author/import `lib/motion/registry.ts` (the DS-08 motion-intent registry) mapping each animation id to a product-state enum, and route every Framer Motion usage through a registry id.
  - Add a static check that fails the build on any Framer Motion animation lacking a registry entry and asserts Rive is instantiated only under `components/loop/`.

- [ ] **T-TECH-09** — Build the build-time MDX pipeline with allow-listed components and typed frontmatter  (→ TECH-04, TECH-08)
  - Configure MDX compilation from `content/` with the fixed component allow-list and Zod-validated frontmatter, wired for SSG/ISR rendering.
  - Add fixtures: one referencing an unlisted component and one with invalid frontmatter; verify each aborts the build non-zero with a file-named error.

- [ ] **T-TECH-10** — Implement claims registry, `<Claim>` component, and the claims-integrity CI scan  (→ TECH-13, TECH-04, TECH-16)
  - Create `content/claims-registry.json` and a `<Claim>` component resolving claim ids to source entries; add a build validator failing on any unresolved reference.
  - Add a CI gate running the denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` across source, content, and rendered output; verify it fails the build on a planted match and that no hardcoded N/N count exists.

- [ ] **T-TECH-11** — Apply SSG/ISR rendering strategy, per-route metadata, and the dynamic-rendering guard  (→ TECH-08, TECH-10)
  - Configure marketing routes as SSG and MDX routes (`/manifesto`, `/writing`, `/writing/[slug]`) as ISR with a bounded `revalidate`; add per-route metadata.
  - Add a manifest test asserting every `lib/routes.ts` route is static or ISR, that no segment forces dynamic/per-request rendering, and that ISR `revalidate` values are set and bounded.

- [ ] **T-TECH-12** — Implement error/loading/empty states across segments, centerpiece, /writing, and /docs  (→ TECH-09, TECH-10)
  - Add `error.tsx`/`loading.tsx` per route group (styled from `--error`/`--surface`), a dedicated centerpiece error boundary, dimension-matched skeletons, and an intentional `/writing` empty state.
  - Add tests: a thrown `ClosedLoop` renders the fallback while the page stays interactive; an empty `/writing` renders the empty-state component; each group has an `error.tsx` referencing `--error`.

- [ ] **T-TECH-13** — Implement responsive layout, fluid type, and small-screen centerpiece degradation  (→ TECH-11, TECH-03)
  - Build a token-driven responsive layout (320px → ultra-wide, ~1200–1280px max container) and degrade the centerpiece to the simplified labeled diagram below the breakpoint.
  - Add Playwright tests at 320/768/1280/1920px asserting no horizontal overflow, clamped container width, and that the simplified diagram (not full Rive) renders below the breakpoint with legible labels.

- [ ] **T-TECH-14** — Establish minimal state management and audited client boundaries  (→ TECH-12)
  - Confine `'use client'` to an allow-listed set (Rive state, scroll progress, reduced-motion/theme, form input) and use React context or a minimal store for shared client state.
  - Add a scan failing the build on any non-allow-listed `'use client'` module and a dependency check asserting no global app-wide state framework is installed.

- [ ] **T-TECH-15** — Configure security headers and a CSP scoped for Rive WASM and self-hosted fonts  (→ TECH-15, TECH-05, TECH-14)
  - Emit CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, and `frame-ancestors 'none'` via middleware/edge config, granting `wasm-unsafe-eval` only where Rive needs it and font/style sources only `'self'`.
  - Add an integration test asserting all headers are present with expected directives and a CSP-parse test asserting no wildcard in `script-src`/`style-src` and scoped `wasm-unsafe-eval`.

- [ ] **T-TECH-16** — Stand up the fail-closed CI harness: Lighthouse, axe-core, motion-integrity, bundle, visual regression  (→ TECH-16, TECH-06, TECH-07, TECH-11, TECH-13)
  - Wire required CI checks for Lighthouse (perf/SEO/best-practices ≥ 95, LCP < 2.5s, CLS ≤ 0.01, JS bundle budget), axe-core (zero critical, AA contrast for `--proven`-on-`--canvas` and text tokens, keyboard traversal), motion-integrity against `lib/motion/registry.ts`, the claims denylist regex, and visual regression.
  - Verify each gate exits non-zero and blocks merge by planting a regression per gate (perf, a11y, unregistered animation, missing reduced-motion fallback, claims match) and confirming the build fails.

---

## Tooling, Pipeline & CI/CD — TOOL

- [ ] **T-TOOL-01** — Author DESIGN.md token contract and design/tokens/*.json source  (→ TOOL-10, TOOL-01)
  - Define token names/values/semantics, accent discipline, typography (display weights 300–600), and the canonical --error token in DESIGN.md and mirror them into design/tokens/*.json.
  - Verify the token source parses and every DESIGN.md token name appears in the JSON source.

- [ ] **T-TOOL-02** — Configure Style Dictionary to emit CSS vars, Tailwind v4 @theme, and typed TS  (→ TOOL-01)
  - Configure Style Dictionary platforms for :root CSS custom properties, a Tailwind @theme layer, and a typed TS token map from the single source.
  - Verify two consecutive builds produce byte-identical outputs (determinism check).

- [ ] **T-TOOL-03** — Implement token-drift + design:check governance gate  (→ TOOL-01, TOOL-10)
  - Add a CI step that rebuilds outputs from source and diffs against committed artifacts, plus a DESIGN.md↔source name/value consistency check.
  - Verify the gate fails on a deliberately desynced token fixture.

- [ ] **T-TOOL-04** — Add tokens:contrast WCAG AA + accent-discipline gate  (→ TOOL-02)
  - Compute contrast for every documented foreground/background pairing and assert only the permitted saturated colors exist.
  - Verify the gate fails on a sub-4.5:1 pairing fixture and on an extra saturated color.

- [ ] **T-TOOL-05** — Build self-hosted Geist Sans/Mono font pipeline with subsetting + preload  (→ TOOL-16)
  - Self-host subset woff2 with font-display: swap + size-adjust, expose via token typography layer, preload the critical face.
  - Verify the build fails when a font references an external host or a machine-artifact component is not bound to the mono token.

- [ ] **T-TOOL-06** — Configure ESLint (jsx-a11y, custom token + mono rules), Prettier, Stylelint, strict tsc  (→ TOOL-05, TOOL-01, TOOL-16)
  - Wire ESLint with jsx-a11y, no-raw-token, and mono-binding rules plus Prettier, Stylelint, and `tsc --noEmit` strict.
  - Verify the no-raw-token rule flags a raw token value used outside the generated layer.

- [ ] **T-TOOL-07** — Wire husky + lint-staged pre-commit hooks (informational, CI authoritative)  (→ TOOL-05)
  - Run format+lint on staged files at commit time while documenting that CI is the authoritative gate.
  - Verify a failing staged file blocks commit locally but the CI result governs mergeability.

- [ ] **T-TOOL-08** — Implement motion registry (DS-08) + rive:check validation and size budget  (→ TOOL-03)
  - Validate each .riv state-machine name/inputs/hash against the DS-08 motion registry and enforce the asset size budget.
  - Verify rive:check fails on a hash/input mismatch fixture.

- [ ] **T-TOOL-09** — Build ClosedLoop wrapper with lazy load and static reduced-motion/error fallback  (→ TOOL-03, TOOL-07)
  - Lazy-load the .riv off-thread and render the committed static labeled-diagram on prefers-reduced-motion or load failure.
  - Verify the static fallback renders under emulated reduced-motion and under a forced Rive load failure.

- [ ] **T-TOOL-10** — Set up Vitest + Testing Library with coverage gate and motion-binding test  (→ TOOL-08)
  - Add Vitest+Testing Library, a coverage gate, and a test asserting every declared animation maps to a DS-08 state input.
  - Verify the suite fails when an animation has no associated documented state.

- [ ] **T-TOOL-11** — Build MDX pipeline with Zod frontmatter schema and component allowlist  (→ TOOL-04)
  - Validate frontmatter (title, slug, description, publishedAt, status, sources[]) via Zod and restrict MDX to an allowlisted component set.
  - Verify the build fails on a missing/malformed required frontmatter field.

- [ ] **T-TOOL-12** — Implement remark-claims-integrity linter and EvidenceClaim component  (→ TOOL-04, TOOL-15)
  - Detect claims with \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b and require an evidence reference resolvable in content/claims-registry.json; render verified claims via EvidenceClaim.
  - Verify the linter flags a fabricated count fixture and contains no hardcoded "N/N verified" literal.

- [ ] **T-TOOL-13** — Author Playwright visual-regression suite for loop states and route breakpoints  (→ TOOL-06, TOOL-03)
  - Capture deterministic screenshots of intent/proving/proved/gate-closed and each key route at mobile/tablet/desktop against committed baselines.
  - Verify the gate fails and publishes a diff artifact when a frame exceeds the pixel-diff threshold.

- [ ] **T-TOOL-14** — Add reduced-motion project and axe-core accessibility suite  (→ TOOL-06, TOOL-07)
  - Run axe-core on every key route incl. empty/loading/error states and assert keyboard operability + visible focus and loop/evidence text-equivalents.
  - Verify the build fails on any seeded serious/critical axe violation.

- [ ] **T-TOOL-15** — Configure Lighthouse CI thresholds and asset size budgets  (→ TOOL-11)
  - Enforce Lighthouse score and LCP/CLS/INP budgets and the gating Rive asset budget; emit JS/CSS budgets as non-gating provisional warnings.
  - Verify the gate fails on a sub-threshold route and that JS/CSS overage only warns.

- [ ] **T-TOOL-16** — Define strict CSP + security headers and header-assertion test  (→ TOOL-12)
  - Configure CSP, HSTS, X-Content-Type-Options, Referrer-Policy, frame-ancestors, Permissions-Policy and assert them on a built/preview artifact.
  - Verify the test fails when any required header is missing or weakened.

- [ ] **T-TOOL-17** — Add dependency-audit and secret-scanning required gates  (→ TOOL-12)
  - Run dependency vulnerability scanning and secret scanning as required CI gates that block deploy.
  - Verify the gate fails on a seeded high/critical advisory and on a planted test secret.

- [ ] **T-TOOL-18** — Add link-check, sitemap/robots, canonical, SEO metadata, and JSON-LD validation  (→ TOOL-15)
  - Validate internal links, sitemap.xml, robots.txt, canonical tags, OG/Twitter metadata, and JSON-LD on built routes and assert no subdomain/sibling-product reference.
  - Verify the build fails on a broken internal link and on a route referencing a sibling product.

- [ ] **T-TOOL-19** — Implement traceability gate over the global requirement-ID set  (→ TOOL-09)
  - Build the global requirement-ID set across all domains, then fail on any unresolved dependsOn, orphan design item, or orphan task; ban placeholder namespaces (TOKENS-*/MOTION-*/PROOF-*/CLAIMS-*/NAV-*).
  - Verify the gate fails on a fixture with an unresolved dependsOn and on an orphan design/task fixture.

- [ ] **T-TOOL-20** — Assemble fail-closed CI workflow with required status checks and parallelism  (→ TOOL-09)
  - Compose all gates (incl. traceability) as required status checks computing mergeability only from check outputs, fail-closed, no manual green.
  - Verify a single failing required check blocks merge and prevents deploy.

- [ ] **T-TOOL-21** — Implement production deploy to apex with SSG/ISR, immutability, rollback, health-check  (→ TOOL-13)
  - Build SSG/ISR, deploy an immutable content-addressable artifact to autonomous-agent.dev with health-gated promotion and atomic rollback.
  - Verify a failed health-check halts promotion and retains the previous live version.

- [ ] **T-TOOL-22** — Provision synthetic monitoring, scheduled re-verify, runbook, and SBOM/SCA supply chain  (→ TOOL-17)
  - Configure external synthetic monitors on /, /proof, and the OG-image endpoint; schedule a privacy/security re-verify job; document the incident runbook and rollback drill; pin dependencies, run SCA, and emit an SBOM per release.
  - Verify monitors alert on a forced outage, an SBOM artifact is attached to a release, and the rollback drill is recorded.

---

## Performance — PERF

- [ ] **T-PERF-01** — Author the machine-readable performance budget contract  (→ PERF-01, PERF-08)
  - Define a versioned JSON contract listing each metric with threshold, gating-flag, and measurement method (INP via scripted Playwright, not TBT).
  - Verify the contract parses in CI and that CWV entries are gating while JS/CSS entries are flagged PROVISIONAL/non-gating.

- [ ] **T-PERF-02** — Self-host and subset the brand typefaces with metric-matched fallbacks  (→ PERF-02, PERF-12)
  - Subset to used glyphs, restrict display weights to 300–600, emit self-hosted WOFF2, and define metric-matched system fallbacks.
  - Run a scripted load and assert font-swap CLS contribution < 0.01 and no third-party font-origin request.

- [ ] **T-PERF-03** — Build the lazy, layout-reserved ClosedLoop Rive wrapper  (→ PERF-03, PERF-14)
  - Reserve the exact box via aspect-ratio and defer the runtime + .riv behind an IntersectionObserver, running off the main thread where supported.
  - Verify no .riv/runtime fetch before viewport proximity and per-component CLS ≤ 0.001.

- [ ] **T-PERF-04** — Implement the image pipeline with intrinsic dimensions and AVIF/WebP  (→ PERF-04, PERF-16)
  - Serve AVIF/WebP with raster fallback, require intrinsic width/height, lazy-load below-the-fold, and mark only the LCP image fetchpriority=high.
  - Audit markup to confirm exactly one high-priority image and per-component image CLS ≤ 0.001.

- [ ] **T-PERF-05** — Enforce first-load JS budget and code-split heavy modules  (→ PERF-05, PERF-08)
  - Move Rive, Framer Motion, the proof trace, and MDX-heavy modules behind dynamic imports out of each route's initial bundle.
  - Verify via bundle analysis that those modules are absent from initial bundles and record per-route first-load JS against the PROVISIONAL budget.

- [ ] **T-PERF-06** — Wire token-driven critical CSS with Tailwind v4 purge and CSS budget  (→ PERF-06)
  - Generate CSS from the DS token source through Tailwind v4 with purge, and ship a per-route critical CSS slice.
  - Confirm no render-blocking third-party stylesheet in the head and record initial CSS size against the PROVISIONAL budget.

- [ ] **T-PERF-07** — Configure SSG/ISR rendering and immutable asset cache headers  (→ PERF-07, PERF-12)
  - Statically generate all content routes from the IA route manifest and configure ISR for /writing only.
  - Inspect build output to confirm /, /how-it-works, /proof, /manifesto, /writing, /docs, /privacy, /terms are emitted and hashed assets carry immutable cache headers.

- [ ] **T-PERF-08** — Stand up the fail-closed performance gate with evidence records  (→ PERF-08, PERF-01, PERF-13)
  - Run Lighthouse-CI plus the scripted INP Playwright check on every PR and persist results as evidence records (metric, value, threshold, collected_at).
  - Verify merge is blocked on any CWV breach or score < 95 while budget breaches only warn.

- [ ] **T-PERF-09** — Implement the reduced-motion fast path with no motion-runtime download  (→ PERF-09, PERF-03)
  - Branch at server/edge on prefers-reduced-motion to emit the static labeled-diagram loop and omit the Rive runtime and non-essential Framer Motion code.
  - Run an emulated prefers-reduced-motion: reduce session and assert zero .riv/runtime fetches and equal-or-better CWV.

- [ ] **T-PERF-10** — Add third-party script discipline and origin-allowlist CI check  (→ PERF-10, PERF-15)
  - Ensure all external scripts load defer/async or post-hydration and add a CI step validating loaded origins against an allowlist.
  - Verify no synchronous third-party script blocks parsing and third-party transfer is recorded against the PROVISIONAL budget.

- [ ] **T-PERF-11** — Build compositor-only scroll motion with off-screen teardown  (→ PERF-11, PERF-16)
  - Drive scroll animation via transform/opacity in rAF gated by IntersectionObserver and tear down observers when sections leave the viewport.
  - Run a scripted scroll-and-interact Playwright session and assert measured INP < 200ms with no layout-triggering paints.

- [ ] **T-PERF-12** — Build the evidence-backed PerfClaim component for published numbers  (→ PERF-13, PERF-08)
  - Render each published metric through a component that reads a stored evidence record and shows monospaced value/threshold/collected_at.
  - Inject a stale/missing record in a test and assert the claim shows "pending" rather than a hardcoded number.

- [ ] **T-PERF-13** — Implement graceful loading/empty/error/slow-network states  (→ PERF-14, PERF-03, PERF-05)
  - Give every deferred asset a reserved-space poster/skeleton/omission fallback and catch load errors without console storms.
  - Block the .riv request and assert the static poster renders in the reserved box with CLS ≤ 0.001 and the page stays interactive.

- [ ] **T-PERF-14** — Tune the resource-priority waterfall and validate hints  (→ PERF-12, PERF-02, PERF-04)
  - Author preconnect/dns-prefetch, preload for above-the-fold fonts and the LCP resource, and lazy/dynamic deprioritization for the rest.
  - Verify via scripted run that the LCP resource lands in the first request wave and the Rive runtime only after viewport proximity.

- [ ] **T-PERF-15** — Add privacy-respecting field RUM with lab-vs-field reconciliation  (→ PERF-15, PERF-01)
  - Ship a PII-free batched RUM beacon reporting LCP/CLS/INP/TTFB attributed to an IA-manifest route.
  - Verify an end-to-end capture attributes samples to the correct route and record the RUM script's own main-thread cost.

- [ ] **T-PERF-16** — Verify responsive asset gating and cross-breakpoint CWV  (→ PERF-16, PERF-01, PERF-04)
  - Drive responsive sources via srcset/sizes and media/container queries so mobile skips desktop-only heavy media.
  - Run an emulated mobile network timeline asserting no desktop-only media fetch and a scripted resize run asserting per-page CLS < 0.1.

- [ ] **T-PERF-17** — Add the Save-Data reduced-data branch and browser-support matrix  (→ PERF-17)
  - Add a Save-Data/prefers-reduced-data branch in the centerpiece wrapper and edge logic that skips the Rive runtime and heavy media for the static loop, and write a versioned browser-support-matrix document with documented degradation per capability.
  - Run an emulated Save-Data session and assert zero .riv fetches occur and that the support-matrix document is present and referenced from the codebase.

---

## Accessibility & Reduced Motion — A11Y

- [ ] **T-A11Y-01** — Build semantic landmark shell + heading-level provider  (→ A11Y-01, A11Y-15)
  - Implement a layout primitive rendering one banner/main/contentinfo landmark plus a nav landmark, with a heading-level context that emits the next level for nested sections.
  - Assert via DOM + accessibility tree: exactly one h1, one of each landmark, and zero skipped heading levels on every route.

- [ ] **T-A11Y-02** — Implement skip link and global :focus-visible ring  (→ A11Y-02)
  - Emit a visually-hidden-until-focused "Skip to main content" link as the first focusable node; add a global `:focus-visible` ring from DS-08/DS-09 focus tokens.
  - Run a Playwright tab sweep: first Tab focuses the skip link, activation lands in `role=main`, focus ring measures ≥3:1 and tab order matches DOM order.

- [ ] **T-A11Y-03** — Consume DS-02 contrast matrix and gate (reference, do not re-declare)  (→ A11Y-03)
  - Wire components to approved DS-02 token pairings only; restrict `--text-faint` to decorative/disabled; rely on the DS-02 (T-DS-04) Style Dictionary contrast gate rather than adding a second gate.
  - Verify axe-core reports zero critical or serious color-contrast violations on default and reduced-motion paths; confirm `--proven` on `--canvas` resolves to the approved ≈12.5:1 pairing.

- [ ] **T-A11Y-04** — Build static labeled ClosedLoop SVG + reduced-motion/capability gate  (→ A11Y-04, A11Y-12)
  - Author ClosedLoop static-first as a labeled SVG (six stages + closed gate); mount the Rive/animated layer only when resolved `useReducedMotion` is false and capability checks pass; reuse the SVG as the loading placeholder.
  - Assert that under reduced-motion no Rive/RAF playback is instantiated and the static SVG exposes all six labels with the gate in closed state.

- [ ] **T-A11Y-05** — Wire global MotionConfig + reduced-motion CSS/attribute backstop  (→ A11Y-05, A11Y-16)
  - Add a site-wide `MotionConfig` reading the resolved context, plus a `@media (prefers-reduced-motion: reduce)` rule and a `data-reduced-motion` attribute backstop; expose a `resolved` prop on informational motion components.
  - Verify all listed components mount at final state with zero non-zero animation/transition durations and no pending motion timers when reduced-motion is active (via OS query or the in-page toggle).

- [ ] **T-A11Y-06** — Implement VerificationState non-color cue primitive  (→ A11Y-06)
  - Build a `VerificationState` primitive mapping each status to a color token plus a mandatory non-color cue (glyph/monospace word/fill pattern); route all state rendering through it.
  - Verify each state via DOM audit carries a non-color cue and remains distinguishable in a grayscale snapshot (zero ambiguous states).

- [ ] **T-A11Y-07** — Make EvidenceTrace semantic DOM + figure/figcaption loop equivalent  (→ A11Y-07, A11Y-13)
  - Render EvidenceTrace as a semantic list (not canvas) and wrap ClosedLoop in `<figure>`/`<figcaption>` summarizing the six stages and fail-closed outcome; suppress state words for unresolved artifacts.
  - Verify via accessibility tree that the loop has an accessible name/description covering all six stages and that trace records are readable text exposed to AT.

- [ ] **T-A11Y-08** — Stand up dual-pass axe-core CI gate with evidence artifacts  (→ A11Y-08)
  - Add a CI job running axe-core over every route in both default and reduced-motion render paths, failing closed on any critical OR serious violation and emitting a per-route JSON evidence artifact.
  - Verify the job exits non-zero on a seeded critical/serious violation and that a missing evidence artifact also fails the job.

- [ ] **T-A11Y-09** — Implement fluid type scale + reflow-safe artifact wrapping  (→ A11Y-09, A11Y-14)
  - Add a clamp-based fluid type scale and container-level wrapping/overflow for monospace machine artifacts.
  - Run a Playwright reflow check at 400% zoom / 320px-equivalent width: zero page-level horizontal scroll and no clipped/overlapping text, including artifacts.

- [ ] **T-A11Y-10** — Build accessible Get-notified form and custom-control ARIA  (→ A11Y-10, A11Y-14)
  - Give every form/custom control a programmatic name + role, associate errors via `aria-describedby`, announce failures through a polite live region, and ensure ≥24×24 CSS px hit targets.
  - Verify axe-core zero critical/serious naming violations and that an invalid submission surfaces a text error (not color-only) announced to AT.

- [ ] **T-A11Y-11** — Add loop pause/play control, flash-safety, and non-auto-advance guarantees  (→ A11Y-11)
  - Add a keyboard-operable pause/stop/hide control (accessible name) to each auto-starting/>5s/auto-updating motion; make scrollytelling advance only on user scroll; keep animations within flash-safety thresholds.
  - Verify SC 2.2.2 with reduced-motion unset: activating the control halts and persists the static state until re-enabled, and no auto-advance timer fires.

- [ ] **T-A11Y-12** — Implement accessible loading/empty/error states with font-display fallback  (→ A11Y-12, A11Y-13)
  - Render the static labeled diagram and system-font fallback (`font-display: swap`) during loading; on asset failure keep the page operable and suppress any unbacked verification words.
  - Verify the accessibility tree is non-empty during load and that no "proven"/verification claim appears without its backing evidence text on failure.

- [ ] **T-A11Y-13** — Add claims-integrity content lint for accessibility/coverage numbers  (→ A11Y-13)
  - Add a build-time lint flagging any accessibility/coverage/compliance number lacking a linked verifiable artifact, consuming the axe-core evidence artifacts where applicable.
  - Verify the build fails on a seeded unbacked figure and that unsubstantiated copy omits the number rather than asserting it.

- [ ] **T-A11Y-14** — Verify responsive a11y: target sizes, orientation, mobile nav, zoom  (→ A11Y-14)
  - Audit interactive target sizes (≥24×24, 44×44 where practical), portrait/landscape support (SC 1.3.4), mobile nav, and small-screen loop degradation to the static diagram.
  - Run an automated bounding-box audit reporting zero undersized targets and confirm no orientation lock across breakpoints.

- [ ] **T-A11Y-15** — Implement App Router route-change focus, title, and announcement  (→ A11Y-15)
  - On App Router navigation/in-page anchor, move focus to `role=main` or the target heading, update `document.title`, and announce via a polite live region.
  - Verify per navigation: focus target reached, title diff applied, and exactly one announcement (no missing/duplicate).

- [ ] **T-A11Y-16** — Wire footer "Reduce motion" toggle to PRIV-03 __pref store  (→ A11Y-16)
  - Add a footer "Reduce motion" toggle writing to the shared PRIV-03 `__pref` store and an pre-hydration init script that reads `__pref` to set `data-reduced-motion` on first paint; make `useReducedMotion` return `osQuery || prefControl`.
  - Verify toggling switches motion components to static render immediately and the preference persists across reload (and OR-merges with the OS query).

---

## SEO, Metadata & Structured Data — SEO

- [ ] **T-SEO-01** — Define single origin constant + metadataBase + environment policy  (→ SEO-02, SEO-08, SEO-11)
  - Add `SITE_ORIGIN` and `DEPLOY_ENV` constants and wire `metadataBase` from them in the root layout.
  - Assert canonical/sitemap/robots all import the same origin (no second origin literal exists in the codebase grep).

- [ ] **T-SEO-02** — Build centralized buildMetadata() factory + root layout defaults  (→ SEO-01, SEO-02, SEO-03, SEO-11)
  - Implement `buildMetadata()` returning title (with "%s — Autonomous Agent" template), description fallback, canonical, robots, OG, Twitter.
  - For every content route, assert exactly one non-empty <title> and <meta name="description">, and uniqueness of (title, description) pairs.

- [ ] **T-SEO-03** — Emit complete OpenGraph + Twitter card sets per route  (→ SEO-03)
  - Populate all og:* and twitter:* tags via the factory, including og:image:width/height and *:image:alt.
  - Assert twitter:card="summary_large_image" and og:image:width=1200/height=630 on each route's HTML.

- [ ] **T-SEO-04** — Implement token-driven OG image system + static fallback  (→ SEO-04, SEO-13)
  - Build the ImageResponse renderer from design tokens with Geist fonts and a try/catch static fallback at 1200x630.
  - Assert each OG endpoint returns 200, content-type image/*, dimensions 1200x630, and the forced-failure path serves the fallback bytes.

- [ ] **T-SEO-05** — Add site-wide Organization + WebSite JSON-LD provider  (→ SEO-05, SEO-13)
  - Emit exactly one Organization and one WebSite node from the root layout, no SearchAction, owned-only sameAs.
  - Validate both nodes against schema.org and assert no JSON-LD string matches the denylist regex \b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b.

- [ ] **T-SEO-06** — Define typed MDX front-matter schema + single content loader  (→ SEO-12, SEO-06, SEO-09, SEO-07)
  - Implement the Zod front-matter schema and a single loader feeding metadata, JSON-LD, sitemap, and feed.
  - Assert an invalid fixture fails the build naming file+field, and that all four surfaces read from the same parsed object.

- [ ] **T-SEO-07** — Emit Article + BreadcrumbList JSON-LD on /writing/[slug]  (→ SEO-06, SEO-10, SEO-12)
  - Derive Article + BreadcrumbList nodes from front-matter and `lib/routes.ts` hierarchy, defaulting dateModified to datePublished.
  - Validate Article schema on a slug route and assert BreadcrumbList item URLs are absolute and match the IA hierarchy.

- [ ] **T-SEO-08** — Generate sitemap.xml from route+content manifest with true lastmod  (→ SEO-07, SEO-02, SEO-14)
  - Generate sitemap.xml from the IA route manifest + content loader, excluding utility/noindex/draft/error URLs.
  - Assert XML well-formedness, all <loc> are IA content routes, and editing one post's source changes only its <lastmod>.

- [ ] **T-SEO-09** — Generate environment-aware robots.txt with sitemap reference  (→ SEO-08, SEO-02, SEO-07)
  - Generate robots.txt from `SITE_ORIGIN`/`DEPLOY_ENV` with an absolute Sitemap: directive; preview emits Disallow: /.
  - Assert production allows all content routes, never blocks rendering assets, and preview disallows /.

- [ ] **T-SEO-10** — Generate RSS feed + autodiscovery link + empty-state handling  (→ SEO-09, SEO-12, SEO-02)
  - Build the feed from the front-matter source with permalink guids and inject the autodiscovery <link> via the factory.
  - Assert valid RSS/Atom XML with newest-first ordering and a valid 200 zero-item channel when no posts exist.

- [ ] **T-SEO-11** — Enforce single-H1, heading order, landmarks, and MDX slugging  (→ SEO-10, SEO-12)
  - Add the rehype slug plugin and page-shell landmarks; ensure monospace artifacts are non-heading spans.
  - Assert exactly one <h1>, no heading-level skips, one <main>, and stable unique heading ids per route.

- [ ] **T-SEO-12** — Implement claims-integrity scanner + claims registry as a required gate  (→ SEO-13, SEO-01, SEO-03, SEO-04, SEO-05)
  - Build the CI scanner over all SEO string surfaces against the denylist regex with `content/claims-registry.json` as the sole allow-list.
  - Assert a "12/12 formally verified" fixture fails the build, the cleaned surface passes, and every registry entry has a source reference.

- [ ] **T-SEO-13** — Apply stub/empty/error-state SEO policy (/docs, 404, 500)  (→ SEO-14, SEO-08, SEO-07)
  - Mark /docs (stub) and empty states noindex,follow, exclude from sitemap, emit no rich JSON-LD; error routes return correct status.
  - Assert stub /docs is noindex + sitemap-absent, a content-bearing /docs is indexed + in sitemap, and 404/500 return correct codes.

- [ ] **T-SEO-14** — Add no-JS metadata parity + SSG/ISR rendering verification  (→ SEO-11, SEO-15)
  - Verify all SEO tags (incl. lang) are present in raw server HTML and not injected by client scripts.
  - Assert a JS-disabled fetch contains the full metadata set and it is equivalent to the hydrated DOM set.

- [ ] **T-SEO-15** — Build CI SEO verification harness emitting machine-readable evidence  (→ SEO-15, SEO-13)
  - Implement the full invariant suite as a required status check that blocks deploy on failure.
  - Assert the harness exits non-zero on any failure and writes a machine-readable evidence artifact per run.

- [ ] **T-SEO-16** — Set <html lang="en"> everywhere and forbid hreflang  (→ SEO-16)
  - Hardcode lang="en" in the root layout and document i18n as an explicit non-goal.
  - Assert every route's <html> has lang="en" and no hreflang tag / non-"en" inLanguage exists anywhere.

- [ ] **T-SEO-17** — Serve security.txt, AI-crawler robots rules, and llms.txt  (→ SEO-17)
  - Add /.well-known/security.txt (RFC 9116), llms.txt thesis/proof summary, and named AI user-agent rules in robots.txt.
  - Assert security.txt returns 200 with valid Contact + future Expires, robots names AI UAs, and /llms.txt returns 200 non-empty.

- [ ] **T-SEO-18** — Produce distinct per-route OG cards + explicit social-identity decision  (→ SEO-18)
  - Bind /, /how-it-works, /proof, /manifesto each to a distinct ImageResponse descriptor; omit twitter:site/sameAs when no owned profiles exist.
  - Assert the four cards are pairwise distinct at 200/1200x630 and that twitter:site and Organization sameAs are absent (documented decision, not TODO).

---

## Privacy, Analytics, Security & Consent — PRIV

- [ ] **T-PRIV-01** — Implement cookieless analytics adapter behind a single boundary  (→ PRIV-01, PRIV-03, PRIV-11)
  - Build one adapter module that is the sole emitter of events, restricting payloads to the enumerated aggregate fields and reading/writing no identifier.
  - Verify by capturing a session's storage and a sample payload: assert no identifier in any store and only aggregate fields in the payload.

- [ ] **T-PRIV-02** — Build consent-policy module and dismissible privacy notice (no cookie wall)  (→ PRIV-02, PRIV-03, PRIV-08)
  - Implement a policy function computing effective consent from cookieless baseline, `__pref` opt-out, and GPC/DNT signals; render a non-blocking notice only.
  - Verify by asserting no blocking-overlay element exists in the initial DOM and that a registered synthetic non-essential resource stays unloaded until opt-in.

- [ ] **T-PRIV-03** — Add accessible analytics opt-out control + first-party `__pref` preference store  (→ PRIV-03, PRIV-08, PRIV-12)
  - Wire an accessible toggle that writes a strictly-necessary flag to the `__pref` store and gates the analytics adapter.
  - Verify by opting out, then asserting zero events for the session and on reload, and inspecting `__pref` for the flag with no tracking identifier.

- [ ] **T-PRIV-04** — Configure transport hardening and security response headers  (→ PRIV-05)
  - Set HSTS, X-Content-Type-Options, Referrer-Policy, X-Frame-Options/frame-ancestors, Permissions-Policy, and COOP at the edge; 308-redirect HTTP→HTTPS.
  - Verify with a header smoke-test across HTML/asset/API routes and a status/Location assertion on the HTTP request.

- [ ] **T-PRIV-05** — Ship strict nonce-based CSP compatible with Rive and self-hosted fonts  (→ PRIV-06, PRIV-15)
  - Inject a per-request nonce and emit `strict-dynamic`, `object-src 'none'`, `base-uri 'none'`, Trusted Types, with no `unsafe-inline`.
  - Verify with a header smoke-test asserting strict directives present and that script-src has no host-allowlist entry.

- [ ] **T-PRIV-06** — Self-host fonts/Rive assets and enforce SRI/origin allowlist guard  (→ PRIV-07, PRIV-06)
  - Self-host fonts, Rive runtime, and analytics client same-origin; add SRI + crossorigin to any unavoidable remote asset.
  - Verify with a build-time check on `integrity`/`crossorigin` and an asset-origin audit confirming same-origin delivery.

- [ ] **T-PRIV-07** — Build 'Get notified' email-capture UI with explicit, unbundled consent  (→ PRIV-04, PRIV-09)
  - Render a single email input with an adjacent purpose statement, no pre-ticked consent, and no unrelated fields, modeled by the single submission state enum.
  - Verify by DOM inspection for one input + purpose statement and absence of any pre-checked or unrelated-processing control.

- [ ] **T-PRIV-08** — Implement hardened first-party email-capture API route (single Get-notified endpoint)  (→ PRIV-04, PRIV-13, PRIV-05)
  - Implement one server endpoint that validates/normalizes, rate-limits, applies honeypot + privacy-preserving challenge, and posts only over HTTPS.
  - Verify that malformed/disposable/honeypot-fail inputs are rejected and that existing-vs-new address responses are indistinguishable under throttling.

- [ ] **T-PRIV-09** — Honor GPC/DNT browser privacy signals end-to-end  (→ PRIV-08)
  - Detect `Sec-GPC: 1` and `DNT: 1` at the adapter/policy boundary and suppress optional measurement, reflecting the state in the privacy UI.
  - Verify by sending each signal and asserting zero optional events plus a UI state showing analytics suppressed by signal.

- [ ] **T-PRIV-10** — Author accurate Privacy Policy page with GDPR + CCPA/CPRA sections  (→ PRIV-09)
  - Render sections for analytics, email capture, sub-processors, GDPR lawful basis, CCPA/CPRA categories, retention, and DSR contact.
  - Verify with a correspondence test cross-checking declared processors/behaviors against the live route manifest and analytics payload schema.

- [ ] **T-PRIV-11** — Build mono-styled footer trust/security note (claims-integrity-clean)  (→ PRIV-10, PRIV-09)
  - Render the monospace footer note from registry-backed verifiable facts only.
  - Verify the note matches the denylist regex `\b\d+\s*/\s*\d+\s+(formally\s+)?(verified|checked)\b` zero times and every claim maps to `content/claims-registry.json`.

- [ ] **T-PRIV-12** — Add resilient failure handling, error/loading/empty states, and reduced-motion fallbacks  (→ PRIV-11, PRIV-12)
  - Swallow analytics failures silently (no retry storm/console noise) and show an accessible inline email error that preserves input; add static reduced-motion fallbacks.
  - Verify by forcing endpoint failures and asserting no console error, single attempt, retained input value, and static state under `prefers-reduced-motion`.

- [ ] **T-PRIV-13** — Build the fail-closed privacy/security verification suite and wire it into the deploy gate  (→ PRIV-14, PRIV-01, PRIV-05, PRIV-06, PRIV-08, PRIV-15, PRIV-16)
  - Implement storage scan, header smoke-tests, CSP-directive assertions, GPC/DNT suppression checks, and analytics-payload PII-absence inspection as a deploy gate.
  - Verify by injecting a deliberately violated claim and confirming the gate fails closed and blocks the claim.

- [ ] **T-PRIV-14** — Generate strict CSP from a single `security/allowlist.ts` source (header + prod report-to)  (→ PRIV-15, PRIV-06)
  - Centralize every `connect-src` and dynamic source in `security/allowlist.ts`; feed both CSP header construction and the prod `report-to` endpoint from it.
  - Verify with a header smoke-test asserting strict directives, no `unsafe-inline`, no host-allowlist script-src, plus a cross-domain no-drift check that the source list derives identically everywhere.

- [ ] **T-PRIV-15** — Publish machine-readable sub-processor register feeding /privacy with PII-free notify event  (→ PRIV-16, PRIV-14, PRIV-09)
  - Define the sub-processor register JSON (purpose, retention, DSR per entry) rendered on `/privacy`, and define the notify-success event schema excluding email and email-hash.
  - Verify by inspecting a captured notify-success payload for no email/hash/identifier and reconciling the register file against the rendered Privacy page entries.

---

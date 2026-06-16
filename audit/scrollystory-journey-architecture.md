# Scrollystory & User-Journey Architecture — autonomous-agent.dev

**Date:** 2026-06-15
**Method:** 47-agent deep audit (run `wlebrhcm0`, 3.6M tokens): component inventory + Tier-1 storytelling benchmark → **one agent per component running the 9-question review battery** (26 components) → judge panel of 5 storytelling lenses → adversarial red-team (3 rounds, looped on P0s) → synthesis.
**Result:** 26 components reviewed — 1 P0 (`home-hero`), 21 P1, 4 P2; verdicts: 1 keep, 24 refine, 1 reframe. No component left unaddressed.
**Truth constraint:** every change stays faithful to `audit/website-content-grounding-report.md` and the claims-integrity firewall (no `N/N` counts; qualitative; real mechanisms named with honest limits).

---

## 1. The persona anchor (empathy is *constructed*, not asserted)

The lead engineer / staff architect who, on a regulated, safety-critical delivery (aerospace, medical, finance, defense), has **personally become the autonomous agent's missing parts** — its memory (re-introducing the same forgotten requirement after a context cut-off), its verifier (hand-checking whether code was actually *wired into live execution paths* vs. merely compiling green), its scope-enforcer, its auditor, its integration-lead, its tool-selector. Their pain is not "the agent is dumb" — it is that **the proving is unpaid, invisible, entirely theirs, and becomes personal liability when "looks done" reaches production.** The site makes them *relive one specific betrayal* (a green suite that lied, shipped, surfaced in prod weeks later) before it offers the gate as the answer.

## 2. The no-brainer mechanism — three felt-then-rationalized strokes

The red-team's load-bearing finding: the original story *asserted* dread instead of *constructing* it, so the gate read as friction. The fix is a three-stroke sequence whose ordering is load-bearing:

- **Stroke 0 — the constructed betrayal (Beat 2).** The visitor *watches* a green suite lie once: a component compiled, passed, merged, "never connected into a live execution path" (market research §1, verbatim), reaching production owned by them. Quiet, no alarm-red. The cost of no-block is now *felt*.
- **Stroke 1 — the watched gate-hold (Beat 5, first green).** The loop advances to its gate; an unproven item is *held*; its fade to `--text-faint` is the primary signal, a narrow `--proven` verdict chip reads "holding — verified," the held item routes visibly to **HANDOFF (distinct from COMPLETE)**. Relief is *inevitable* because the visitor already paid the cost in Beat 2.
- **Stroke 2 — the self-administered auditor question (Beat 6).** One breath: "Could an auditor prove your agent did what it claimed?" — co-framed for self-interest: "Could *you*, six months from now, prove which requirement this code satisfied — and that it was ever independently verified?" The visitor answers "no" for Devin/Cursor/their own CI, "yes, I just watched it" here. That asymmetry **is** the decision, self-administered.

**"Why has nobody done this?"** — seeded at Beat 3, detonated and *answered* at Beat 9 with a real cause, not a cleverness gap: **"already solved, never assembled — because the enabling primitive is new"** (deterministic per-edit enforcement only became possible recently: command-type hooks that fail closed). The collapse *shows seams* (Temporal stays outside the engine) so assembly looks honest, not magical.

## 3. The home scrollystory — 9 beats

| # | Beat | Emotional job | The simplification | Component |
|---|---|---|---|---|
| 1 | **The reveal, thesis-first** | Grasp "a product that proves its own work" in one read; enemy as kicker | Thesis you read in one breath + a calm machine proving it beside the words | home-hero / loop-centerpiece |
| 2 | **The day the green suite lied** (sub-beat) | Relive one betrayal so later relief is inevitable | "self-report is not evidence" becomes one concrete scar the visitor owns | home-betrayal |
| 3 | **The weight, then the collapse — with seams** | Feel the sprawl, then bodily relief as it becomes one engine (Temporal stays outside) | Fragmentation is one feeling resolved by one gesture; the seam keeps it believable | home-fragmented-stack / powered-by |
| 4 | **That is literally my job, gone** | Empathy peak: each unpaid role named so it stings, then *substituted* | The engine is defined by the human labor it removes (substitution grammar, not green) | home-replace-table |
| 5 | **The line is held** (first green) | Climax: "blocked" becomes the most reassuring moment | Thesis proven by watching; a block is a win; HANDOFF keeps it honest | home-closed-loop-explained |
| 6 | **Could you actually prove it?** | Convert watched relief into a verdict the visitor renders themselves | One question replaces a comparison table; it bites the builder's own future self | home-proof-model |
| 7 | **The leap** (static ledger) | Crystallize before/after; break the motion grammar | Four jobs you stop doing, three guarantees you gain — read instantly | home-the-leap |
| 8 | **Where "looks done" is unacceptable** | Highest-stakes reader feels seen; lock-in fear defused | Audience by the standard it's held to, not borrowed logos | home-who-its-for |
| 9 | **Already solved, never assembled** | Calm conviction + frictionless next step; answer "why nobody did this" | The product is the inevitable assembly of tools you already trust | home-soft-close / get-notified |

**Green is rationed:** `--proven` appears **only** at Beat 5 (gate verdict chip) and Beat 6 (completed evidence record). Beats 3, 4, 7, 8 use substitution / lateral separation / static resolution so the first green carries full meaning.

## 4. The user journey — 6 routes, each a different reader

1. **`/` (home, 9-beat scrollytell)** — the keynote: the whole argument in one descent.
2. **`/how-it-works`** — the convinced-but-skeptical builder: the six stages at mechanism resolution (controlled-vocabulary mechanisms + strict sequencing), B01–B19 as **six named clusters mapped onto the six loop stages** ("the same loop at higher resolution"), no-lock-in full triple.
3. **`/proof`** — the auditor-minded evaluator: invariant → evidence schema → independent-verifier → auditor test; honest limits out loud; interactive audit-trace with explicit states + HANDOFF-distinct-from-COMPLETE.
4. **`/manifesto`** — the worldview in prose: antagonist-first §1, enforcement layer named, governing invariant as the single pull-quote, HANDOFF self-correction as trust signal, named-section side-rail.
5. **`/writing` + `/docs`** — honestly stubbed; **default flag-OFF** (route + nav entry absent, no orphan link) until content justifies them.
6. **Global frame + edge states** — nav with category descriptor lockup (so deep-link arrivals know the category in 3s), footer carrying the **verbatim governing invariant** as its one trust line, defined `supporting-page-shell`, branded 404/500 (404 carries the invariant trust line; neither uses alarm-red but both read as errors in 3s).

## 5. Per-component verdicts & top fixes (from the 26-agent battery)

| Component | Verdict | Sev | Headline fix |
|---|---|---|---|
| home-hero | **reframe** | P0 | Lead with antagonist line, thesis as resolution; cut powering-stack from hero body; loop runs cinematic (not pre-mounted to gate) |
| home-fragmented-stack | refine | P1 | Real named tool tiles (≥12); human-legible lead label leads, engineering spine string subordinated; Temporal outside the engine |
| home-replace-table | refine | P1 | Substitution grammar (machine text replaces human text); outcome-first then mechanism; fix the weak "integration-lead" row |
| home-closed-loop-explained | refine | P1 | Rename to climax ("The line is held"); compress stages 1–5 (~3:1), gate gets ~40%; gate = arrival |
| home-proof-model | refine | P1 | Reverse to auditor-question-first; drop "governing invariant" as visitor copy; illumination driven by evidence completeness not scroll |
| home-the-leap | refine | P1 | Static two-column ledger with group headers (not color-alone); complete guarantee noun phrases; drop "zero" prefix |
| home-who-its-for | refine | P1 | Pain-hook before any domain name; outcome-before-mechanism; no-lock-in micro-line |
| home-soft-close | refine | P1 | Anchor close to Beat 1 antagonist; "See how it works" primary; resolve the betrayal arc |
| loop-centerpiece | refine | P1 | Separate motion layer (geometry + accent only) from a stationary copy/artifact panel; no tool names inside motion |
| loop-evidence-trace | refine | P1 | Homepage shows ONE record + framing anchor; append-list moves to /proof |
| powered-by | refine | P1 | Make it the immediate sequel to the collapse ("what's in the box?"); B-block IDs retained but glossed |
| integrator-thesis | refine | P1 | Primary delivery at fragmented-stack progress=1.0 (caption for a visual just experienced), not the hero shout |
| no-lock-in | refine | P1 | Concrete EvidenceRecord JSON glimpse + human gloss; gloss "W3C Baggage"; place after powered-by / after proof |
| howit-loop-explainer | refine | P1 | EARS = notation not tool; two-beat reveal; mechanism/artifact on demand |
| howit-capability-taxonomy | refine | P1 | Clusters align exactly to the six loop stages; framed as reveal/expansion, not a 19-block catalog |
| proof-spine | refine | P1 | Auditor test first (challenge), then invariant→schema→verifier as the answer |
| proof-audit-trace | refine | P1 | Bridge sentence above it; `--pending` on evidence-pending; gate-green reframed by copy at first contact |
| manifesto-spine | refine | P1 | §1 antagonist-first; HANDOFF as trust beat not error footnote |
| manifesto-reading-aids | refine | P2 | Named-section side-rail (IntersectionObserver), not a % progress bar |
| writing-index | refine | P2 | Drop reading-time; human-readable date (ISO in datetime attr) |
| docs-placeholder | **keep** | P2 | Add live onward links (per PAGE-11) alongside Get-notified |
| supporting-page-shell | refine | P1 | Remove print stylesheet from shell scope (per-route only); footer owns the single Get-notified instance |
| global-nav | refine | P1 | Category descriptor lockup under wordmark; pin/justify or drop the condense behavior; Writing out of nav while stubbed |
| global-footer | refine | P1 | Replace generic trust note with the verbatim governing invariant |
| get-notified | refine | P1 | Name the signal honestly ("when we open the platform, you'll hear first"); no date; one calm affordance |
| branded-error-states | refine | P2 | 404 carries the invariant trust line; upgrade stub copy to manifesto-voice tied to the evidence thesis |

## 6. The 8 open decisions — resolved to defaults (autonomous)

1. **Betrayal-beat placement** → **sub-beat within Fragmented-stack** (spec-safe; preserves HOME-02's contiguous 1..8 manifest). *Not* a 9th top-level section.
2. **Antagonist + soft-close copy** → **copy candidates routed through CONTENT-02's ranked matrix + claims-registry**, not pre-ratified canon. Thesis stays the dominant first-paint H1; the kicker is present-at-paint (DS layout sign-off folded into the design spec).
3. **CONTENT-17 integrator string** → **render verbatim** (blocking). Any trim (the "a dozen other" phrase) would be a formal CONTENT-17 amendment first; ship verbatim by default.
4. **Gate-close micro-choreography** → specify LOOP-07's four beats (approach, evaluate, hold/close, settle) with a measurable oracle, verdict-chip-green (not full-cell flood), HANDOFF-distinct affordance. Build detail.
5. **Betrayal tone** → **a single quiet artifact-reveal**, no alarm-red, framed as the visitor's own lived scar; success oracle = reads as recognition, not fear-mongering.
6. **Mobile parity** → vertical-stacked labeled loop with trace below, preserving the Beat-5 gate-hold and Beat-2 betrayal legibility; fall back to the static labeled diagram for those two beats if animation can't be legible.
7. **/writing & /docs at launch** → **flag-OFF** (route + nav entry absent). No orphan nav link.
8. **Dual-register loop cadence** → one Rive state machine, two playback modes (hero autonomous 8–14s; Beat-5 scroll-driven). Verify single-source-of-truth in the build.

## 7. Remediation map → spec edits

Applied to `docs/website/autonomous-agent.dev/{requirements,design,tasks}.md`, enrichment-only (no new requirement IDs unless a beat demands it), claims-safe:

- **HOME-01**: antagonist kicker present-at-paint above the dominant thesis H1; cut powering-stack from hero body (move to supporting weight); loop runs cinematic, no pre-mounted gate, no green.
- **HOME-02**: betrayal as a named sub-beat of the Fragmented-stack section (keep 8 top-level ordinals).
- **HOME-03**: ≥12 real named tool tiles; human-legible lead label primary + spine string subordinated; Temporal renders *outside* the consolidated engine at progress=1.0; enabling-primitive line.
- **HOME-04**: substitution grammar; outcome-first substitute copy; per-edit naming on verifier *and* auditor cells; no green.
- **HOME-05**: rename to climax; compress stages 1–5 ~3:1; gate as arrival; verdict-chip green + held-item fade primary; HANDOFF-distinct; mandatory 2× gate-cell emphasis in the static fallback.
- **HOME-06**: auditor-question-first + self-interest co-frame; drop "governing invariant" visitor label; illumination by evidence completeness not scroll; one record + framing anchor.
- **HOME-07**: static two-column ledger, group headers, completed guarantee phrases, drop "zero" prefix.
- **HOME-08**: pain-hook before domains; outcome-before-mechanism; no-lock-in micro-line.
- **HOME-09**: anchor to Beat-1 antagonist; "See how it works" primary; grounded "why nobody did this."
- **LOOP-01/02/17**: separate motion layer (geometry+accent) from stationary artifact panel; tool names out of the motion layer; dual cadence.
- **CONTENT-13**: gate caption already canonical; add the held-item/HANDOFF verdict-chip copy; green-rationing rule.
- **CONTENT-18**: powered-by is the collapse sequel; B-block IDs glossed.
- **CONTENT-19**: concrete EvidenceRecord JSON glimpse + gloss; placement after powered-by / after proof; full triple on /how-it-works AND manifesto.
- **PAGE-01/02**: clusters align to the six stages; reveal framing; EARS-as-notation fix.
- **PAGE-03/04**: auditor-test-first; bridge sentence; `--pending` on pending; HANDOFF-distinct.
- **PAGE-06/07/CONTENT-11**: manifesto §1 antagonist-first; named-section side-rail; HANDOFF as trust beat.
- **PAGE-09/10/16/IA-03/IA-15**: writing/docs flag-OFF default; drop reading-time; live onward links on docs stub.
- **IA-12 / supporting-page-shell**: footer carries verbatim governing invariant; shell defined; print styles per-route only; single Get-notified instance.
- **IA-08/09**: 404 carries the invariant trust line; both legible-as-errors without alarm-red.

## 8. Residual risks

- Regulated-persona dependence — mitigated by the Beat-6 self-interest co-frame so the unregulated builder is also bitten.
- The gate-close is the single point of failure for Stroke 1 — must be specified frame-by-frame with a measurable oracle and a mandatory static fallback.
- Betrayal-beat tone could tip into fear-mongering — single quiet artifact-reveal, grounded verbatim in §1, no alarm-red.

# Audit — Artifact Location for the `autonomous-agent.dev` Build Plan

**Date:** 2026-06-15
**Target:** `docs/plans/based-on-the-attached-eventual-cat.md` (the implementation plan)
**Question:** Where are the plan's `requirements.md` / `design.md` / `tasks.md` located?
**Method:** Codebase-only forensic pass. Fully answerable in-repo; no external references needed (Pass 2 N/A).

---

## TL;DR (the decisive answer)

There are **two distinct Kiro-style specs** in this repo, for **two different subjects**. The plan
conflates easily with the repo's existing spec, so the answer is split:

| You mean… | Subject | requirements.md | design.md | tasks.md | Status |
|---|---|---|---|---|---|
| **The three files that physically exist** | Spec-to-Evidence **Control System** (the *product*) | `.kiro/specs/spec-to-evidence-control/requirements.md` (438 ln) | `.kiro/specs/spec-to-evidence-control/design.md` (1125 ln) | `.kiro/specs/spec-to-evidence-control/tasks.md` (1083 ln) | ✅ Exist, canonical |
| **The plan's own spec** (what the plan is *about*) | The `autonomous-agent.dev` **website** | — | — | — | ❌ **Do not exist yet** — embedded inline + materialization-pending |

**Bottom line:** The website's `requirements.md` / `design.md` / `tasks.md` **are not files**. They live
**inline inside the plan itself** as PART B indices, and the plan explicitly states the standalone files
are generated *"on approval"* and **do not yet exist**. The only physical `requirements.md`/`design.md`/`tasks.md`
in the repo belong to a *different* spec (the control system), not the website the plan describes.

---

## Finding 1 — The plan is a *website* plan; the `.kiro` files are a *product* spec (different scope)

- The plan (`docs/plans/based-on-the-attached-eventual-cat.md:1`) is titled
  *"Autonomous Agent — `autonomous-agent.dev` flagship website build plan."* Its Context section
  (`:5-12`) says the goal is to build "the commercial front door" — a manifesto/marketing site — **not** the product.
- The repo's `.kiro` spec is about the **Spec-to-Evidence Coverage Control System** — "an autonomous
  agentic software-delivery control plane" (`.kiro/specs/spec-to-evidence-control/requirements.md:5`;
  `design.md:1`; `tasks.md:1`). That is the *product itself*, not its website.
- The plan even references the product corpus as *input grounding* (`:25-27` "PRD, requirements, design,
  market research, formal verification, audit") — confirming the `.kiro` files are **source material for**
  the website, not the website's own spec.

**So:** if the question is "where are the three artifacts of the *control system*," the answer is
`.kiro/specs/spec-to-evidence-control/`. If it's "where are the three artifacts of the *website the plan
describes*," see Finding 2 — they aren't materialized.

## Finding 2 — The website's R/D/T live *inline* in the plan as indices, not as files

The website spec is embedded in **PART B** of the plan, as three index sections (summaries, not full files):

| Artifact | Location in plan | Contents | Count |
|---|---|---|---|
| Website **requirements** | `:344` — **§B.1 Requirements index** | EARS one-liners across 12 domains | **189** |
| Website **design** | `:559` — **§B.2 Design index** | design decisions → requirement IDs | **151** |
| Website **tasks** | `:736` — **§B.3 Task index** | tasks → requirement IDs | **201** |

Domain breakdown table at `:329-342` (DS, IA, HOME, LOOP, CONTENT, PAGE, TECH, TOOL, PERF, A11Y, SEO, PRIV).
These are **indices** — one-liners with traceability IDs — not the full per-requirement acceptance criteria.

## Finding 3 — The standalone website files are *explicitly* not-yet-created (by design)

The plan is unambiguous that the physical `requirements.md`/`design.md`/`tasks.md` for the website do not exist:

- `:327` — "Full per-requirement acceptance criteria + full design/task detail live in the workflow
  artifact and **are materialized into `requirements.md` / `design.md` / `tasks.md` on approval**."
- `:1172` — "**On approval:** materialize the full per-requirement spec from the workflow artifact into
  `requirements.md` / `design.md` / `tasks.md`…"
- `:1182` — "Physical closure = materializing the corrected `requirements.md`/`design.md`/`tasks.md` …
  **I make no claim that the three spec files are fixed — they do not yet exist.**"
- `:1228` — "Artifact level — **materialization-pending (by design)**. The corrected requirement text is
  not yet physically rewritten into `requirements.md`/`design.md`/`tasks.md`…"

The plan **is** "the workflow artifact" it refers to. So today the website spec exists *only* as PART B
inside `docs/plans/based-on-the-attached-eventual-cat.md`.

## Finding 4 — Naming/disambiguation hazard

`.kiro/specs/spec-to-evidence-control/requirements.md` etc. are real, canonical, and recently reconciled
(see `audit/reconciliation-report.md`, `audit/verification-report.md`). A reader asked to "find
requirements.md" will hit these first and may wrongly assume they are the website's spec. They are **not** —
they are a different subject at a different layer. The website spec has no `.md` files of its own yet.

---

## Where things stand (prioritized)

- **P0 — Decision required, not a defect.** The website's `requirements.md`/`design.md`/`tasks.md` are
  intentionally un-materialized pending approval (`:1172`). To get physical website spec files, the plan
  must be approved and its "materialize on approval" step executed. *What:* generate the 3 files from
  PART B; *Where:* a new dir, suggest `.kiro/specs/autonomous-agent-website/` (parallel to the existing
  spec) or `docs/website/`; *Effort:* M (the index content exists; full ACs must be expanded from the
  workflow artifact). **This is a build step — cannot run in plan mode per `:1228`.**
- **P2 — Disambiguation.** If these two specs will coexist, add a one-line pointer in each so future
  readers don't conflate the website spec with the control-system spec. *Effort:* S.

## To enrich in pass 2

None required. Every claim above is cited to a line in `docs/plans/based-on-the-attached-eventual-cat.md`
or `.kiro/specs/spec-to-evidence-control/*.md`, both in-repo. No sibling-repo or external reference would
change the answer. The only open item is a **user decision** (approve materialization), not a missing fact.

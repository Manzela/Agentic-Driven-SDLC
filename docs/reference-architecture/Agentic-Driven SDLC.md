# Reference Architecture: Autonomous Agentic Software Delivery on Claude Code (Full Re-Issue)

## TL;DR
- The substrate choice is correct: Claude Code's native primitives (subagents, hooks, plan mode, CLAUDE.md, headless `claude -p`, checkpointing, worktrees, MCP) ARE the inner orchestrator; an external agent-reasoning framework (LangGraph/CrewAI/etc.) is redundant here. The two things Claude Code does NOT give you are a crash-safe outer loop and a fail-closed coverage gate — those are the pieces you build/add.
- The single most important reliability mechanism is the **Stop hook wired to a coverage validator**: hooks are shell commands the harness runs unconditionally, and a non-zero exit (exit 2) blocks the action — so a Stop hook that blocks while any `feature_list.json` item is unproven literally cannot be talked past by the model. Pair it with OPA/Conftest + a GitHub required status check at merge. Deterministic gates — not model self-assessment — are what reject incomplete delivery.
- Build the simplest spine first (spec → default-unproven coverage model → bounded slice in a worktree → independent verifier subagent → Stop-hook gate → git/Postgres evidence), add Temporal/Inngest ONLY when runs must survive multi-hour crashes, and do NOT build recursive agent swarms, elaborate memory graphs, or custom orchestration in v1.

## Key Findings
- **Hooks are the only deterministic enforcement layer.** Claude Code fires hooks (PreToolUse, PostToolUse, Stop, SubagentStop, PreCompact, SessionStart, UserPromptSubmit and more) as shell/HTTP commands; exit code 2 blocks. CLAUDE.md, prompts, and Skills are PROBABILISTIC (advisory). The "usually vs always" gap is where production fails — a PostToolUse hook runs the linter every time, no exceptions.
- **Agent Teams is real but experimental** (research preview shipped Feb 5, 2026 alongside Opus 4.6; requires Claude Code v2.1.32+, Opus 4.6, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`), with documented limitations (no session resumption of in-process teammates, task-status lag, slow shutdown, one team at a time, no nested teams, ~15x token cost). Do NOT depend on it for v1's safety-critical path; use hierarchical subagents.
- **The coverage model is a build-it-yourself thin artifact.** Anthropic's own long-running-agent harness uses a JSON feature list ("never remove or reorder items, only flip status incomplete→complete"), an initializer agent, a separate coding agent, git checkpoints, and — critically — a *separate evaluator agent* (GAN-style generator/evaluator), never letting an agent grade itself.
- **Off-the-shelf coverage of the verification stack is excellent:** Playwright + Playwright MCP (behavioral), Semgrep/CodeQL (SAST), SonarQube AI Code Assurance quality gates, Pact (contracts), OPA/Conftest (policy gate), GitHub repository rulesets + required status checks (merge gate), Dependabot/Snyk + Sigstore/SLSA `actions/attest-build-provenance` (supply chain). Managed Postgres (Neon/Supabase/Cloud SQL) handles traceability + run state. OpenTelemetry GenAI conventions + Langfuse/Phoenix handle observability.
- **Durable storage and observability are the previously under-weighted layers.** Claude Code has built-in OTel instrumentation (`CLAUDE_CODE_ENABLE_TELEMETRY=1`) emitting `claude_code.cost.usage` and `claude_code.token.usage` metrics plus span/trace export to any OTLP backend.

## Master Mapping Table

### 13 Gap Clusters

| # | Gap | Recommended managed building block | Key alternative | Claude Code primitive/integration | Enforcement |
|---|-----|-----------------------------------|-----------------|-----------------------------------|-------------|
| 1 | AI behavior gaps (missing features, unwired components, tests-pass-but-intent-unimplemented, self-eval overestimation) | Independent evaluator subagent + Playwright MCP behavioral proof + Semgrep dead-code/call-graph checks | CodeRabbit/Greptile review | SubagentStop hook validates evidence; separate evaluator agent (never self-grade) | DETERMINISTIC (hook + CI) |
| 2 | Fragility over long/multi-session work | File-based progress (claude-progress.txt) + git-as-state + Postgres run table; PreCompact hook checkpoints | Temporal/Inngest durable outer loop | SessionStart loads context; PreCompact hook; checkpointing/rewind | DETERMINISTIC (hook + durable engine) |
| 3 | Lack of machine-verifiable specs | GitHub Spec Kit (EARS acceptance criteria) or Kiro requirements-analysis (SMT) | OpenSpec / BMAD | Slash commands + Skills generate atomic specs with IDs | PROBABILISTIC (gen) → DETERMINISTIC (SMT check in Kiro) |
| 4 | Weak coverage & traceability | `feature_list.json` coverage model + Postgres traceability graph | StrictDoc/Doorstop | Initializer agent builds it; Stop hook validates it | DETERMINISTIC (Stop hook + OPA) |
| 5 | Poor execution-scope control | Claude Code plan mode + one-feature-at-a-time coding agent + git worktrees | — | Plan mode; subagents; worktrees for isolation | PROBABILISTIC (plan) + DETERMINISTIC (worktree isolation) |
| 6 | Weak gating & governance | OPA/Conftest + GitHub repository rulesets/required status checks | SonarQube quality gate | Stop hook (in-loop) + CI status checks (at merge) | DETERMINISTIC |
| 7 | Underused durable artifacts | git history as execution trail + Postgres authoritative store + spec/matrix files in repo | object storage for evidence | PreToolUse blocks edits to protected artifacts | DETERMINISTIC (hook) |
| 8 | Incomplete NFR + wiring treatment | NFRs as first-class coverage items + wiring checks (call-graph/integration tests) | — | Coverage model includes NFR + WIRING item types; verifier subagent | DETERMINISTIC (gate) |
| 9 | Org/role ambiguity | Fixed small role set as subagents (planner/implementer/verifier + security/QA) | Agent Teams (experimental) for peer coordination | `.claude/agents/*.md` definitions; Agent Teams when mature | PROBABILISTIC (roles) |
| 10 | Over-reliance on human micro-steering | Proactive-discovery initializer agent + domain baseline checklists | Kiro spec elaboration | Skills + CLAUDE.md baselines; plan mode review | PROBABILISTIC |
| 11 | Stack/framework uncertainty | Claude Code subagents+hooks as inner loop; Temporal/Inngest as outer loop only if needed | LangGraph/Pydantic AI/ADK | Native primitives; headless `claude -p` as durable step | n/a (architectural) |
| 12 | Observability gaps | OpenTelemetry GenAI + Langfuse (OSS) or W&B Weave | Arize Phoenix / Braintrust | `CLAUDE_CODE_ENABLE_TELEMETRY=1` OTLP export; hooks forward events | DETERMINISTIC (telemetry) |
| 13 | Defining "success" precisely | Coverage-and-evidence model: every requirement has machine-checkable acceptance criteria + captured evidence | — | Stop hook checks all items proven | DETERMINISTIC |

### 4 Pain-Point Clusters

| # | Pain point | Building block | Claude Code primitive | Enforcement |
|---|-----------|---------------|----------------------|-------------|
| 1 | Scope/detail omissions (unwired widgets, missing screens, sub-tier quality) | Proactive-discovery spec + coverage model with WIRING/UI items + Playwright behavioral proof | Initializer agent + Playwright MCP | DETERMINISTIC (gate on coverage) |
| 2 | Unrealistic demands on humans | Spec compiler auto-elaborates; coverage model tracks every item so humans don't have to | Skills + plan mode (human approves plan, not every micro-step) | PROBABILISTIC + human gate |
| 3 | Passive execution / no initiative | Initializer agent + domain baseline checklists infer competitive feature set | CLAUDE.md domain baselines + Skills | PROBABILISTIC |
| 4 | Execution drift & brittleness | Bounded slices + independent verifier + progress/stuck detection + 2-3 retry cap → human handoff | Stop/SubagentStop hooks + iteration caps (`--max-turns`) | DETERMINISTIC |

## Detailed Layer Sections (A–J)

### A. Spec compilation & proactive discovery
**Recommended:** GitHub Spec Kit as the spec scaffold (Specify → Plan → Tasks → Implement; constitution file; EARS acceptance criteria), augmented by a custom "initializer/proactive-discovery agent" that elaborates implied features from domain baseline checklists. **Key alternative:** Amazon Kiro, whose **requirements-analysis** step is uniquely valuable: it translates EARS requirements into SMT-lib formal logic and runs an automated-reasoning (SMT) solver to mathematically detect contradictions, ambiguities, and gaps before code. Across 35 internal Kiro projects with 1,400+ acceptance criteria, ~60% of first-draft requirements needed refinement, per AWS director of AI product management Mike Miller to The New Stack (May 15, 2026): "roughly 60% of first-draft requirements needed refinement before they could be reliably implemented." EARS (Easy Approach to Requirements Syntax — Ubiquitous/Event/State/Unwanted/Optional patterns, created by Alistair Mavin at Rolls-Royce in 2009) is the lingua franca all major SDD tools converge on.

Adoption signals: Spec Kit is a Python CLI with 90,000+ GitHub stars (v0.8.7, May 2026), supports 30+ agents including Claude Code; BMAD-METHOD ~48k stars; OpenSpec ~52k stars (June 2026). Martin Fowler's analysis warns these tools generate verbose, repetitive markdown and can be "a sledgehammer to crack a nut" on small tasks — so apply judgment.

**Claude Code integration:** Spec Kit installs slash commands / Skills; the initializer agent runs as a subagent that writes spec files into the repo. Enforcement is PROBABILISTIC (generation) until you add Kiro's SMT check or a schema-validation hook, which is DETERMINISTIC.

**Simplest sufficient choice + what to skip:** Spec Kit + EARS + a proactive-discovery initializer agent. Skip BMAD's 12-agent org-chart simulation for v1 — it's the most token-expensive (~$800–$2,000/developer/month on frontier models, ~230M tokens/week on large projects per Reenbit's field reports) and over-structured for most work.

#### A.1 — Concrete deterministic spec-completion loop (the unbiased "until-complete" mechanism)

This is the concrete realization of the "proactive-discovery initializer agent." The goal: drive Claude Code to elaborate the spec — translating EARS requirements into SMT-lib logic, detecting contradictions/ambiguities/gaps, and writing `features.json` — and keep going *until the spec is provably complete*, without either (a) the agent biasing its way to a premature "done" or (b) burning tokens in an endless loop. The resolution is a strict division of labor: **the agent writes; deterministic, non-LLM code judges; a bounded outer loop drives.** The recommended shape is layered (in-loop hook + crash-safe outer loop), because the two cost ~30 lines of shell over a hook-only design and close gaps neither covers alone.

**The judge is non-LLM code — this is what removes the bias.** A standalone validator (no model inside it) reads the spec artifacts and returns a hard verdict. The danger you flagged — an agent drifting toward "complete" to escape the cycle — exists only if the agent judges itself; so it doesn't judge at all. The validator is two complementary checks:
- **Logic check (Z3):** each EARS statement is translated to an SMT-lib formula; **Z3** — Microsoft Research's open-source SMT solver (`pip install z3-solver`, or `z3-solver` via WASM for Node/TS; no IDE, no vendor lock-in) — returns SAT / UNSAT / counterexample. UNSAT with the conflicting pair named = a contradiction (e.g., "WHILE maintenance mode the system SHALL reject writes" vs. "WHEN an admin saves THEN the system SHALL write immediately"). Unsatisfiable or vacuous conditions surface as requirements that can never fire. Z3 *proves*; it does not *opine* — there is no judgment for the agent to drift.
- **Coverage check (domain-baseline checklist):** Z3 cannot detect a requirement you never wrote — you can't prove the absence of something absent. A curated domain-baseline checklist (the proactive-discovery knowledge — e.g., a SaaS auth system MUST cover signup, login, logout, password-reset, session-expiry, lockout, MFA…) flags which baseline items have zero mapped requirements. This is the "no missing pieces left" half.

The validator's output is mechanical — `{ contradictions: [...], ambiguities: [...], uncovered: [...], violation_count: N }`. Zero violations = pass. **The agent gets no vote; only the exit code counts.** (Enforcement: DETERMINISTIC.)

**The inner guarantee is a `Stop` hook.** When the spec agent tries to end its turn, a `Stop` hook runs the validator. On `violation_count > 0` it blocks the stop and feeds the *specific* enumerated violations back into the session ("REQ-014 contradicts REQ-031 on auth state; REQ-022 has no acceptance criteria; 'password reset' has no requirements"), forcing another pass. Because the hook is shell code the harness runs unconditionally, the agent cannot talk its way past it. Guard with the `stop_hook_active` flag so the hook doesn't re-trigger itself once clean.

**The outer loop is the crash-safe wrapper and the token circuit-breaker — not a licence to loop forever.** A short shell `while` script (Temporal is overkill at the spec stage) re-invokes `claude -p` if a session dies and enforces the bound. Its exit condition is what balances your two fears — **convergence-or-escalate**, never "loop because the agent wants to":
- **Stop on success:** `violation_count == 0`.
- **Stop on no-progress:** if a pass does not *strictly reduce* `violation_count` versus the previous pass, the agent is stuck or thrashing → **halt and hand to a human** (do not retry into the void).
- **Stop on cap:** a hard ceiling (≈5–7 passes; `--max-turns` per invocation plus a loop counter) → graceful halt, hand the current spec + remaining violations to the human.

The two fears are handled by *different* mechanisms, so neither weakens the other: **bias/drift** is contained by the deterministic validator (nothing the agent claims is trusted), and **token burn** is contained by the convergence tripwire + hard cap (the validator is never relaxed to let the agent escape). This mirrors the loop-engineering "2–3 retries then human handoff" rule; a few more passes are reasonable here because spec refinement genuinely converges on enumerated defects — but the no-progress tripwire, not the raw number, is the real safety.

**Where Plan Mode sits.** Plan mode is an interactive, human-gated state, so it is the **human approval checkpoint, not the engine of the loop.** It runs at session start so you can supply context the agent could not infer, and — placed correctly — it presents the *already-validated, contradiction-free* spec + `features.json` for sign-off before any implementation. Its deterministic teeth are not "force plan mode" (a hook cannot make an unattended run interactive) but **"block code until the plan is approved":** a `PreToolUse` hook on `Write|Edit` exits 2 unless an approval marker (e.g., `plan-approved.json`, written when you approve) exists. Plan mode is the UI that produces the approval; the hook is what enforces that nothing proceeds without it. To default interactive sessions into plan mode at start, a `SessionStart` hook plus the default-mode setting can be used. (Enforcement: the plan-approval gate is DETERMINISTIC; plan mode itself is a human gate.)

**Sequence:** spec-completion loop runs to zero violations (or escalates) → plan mode presents the complete, SMT-validated spec + `features.json` for human approval and missing-context injection → approval writes the marker → the `PreToolUse` gate unlocks implementation tools. Completeness is proven *before* a human is asked to approve; code is blocked *until* they do.

**Simplest sufficient choice + what to skip:** the only custom piece is the validator (EARS→SMT-lib translation + Z3 + the domain checklist) — small, and the heart of the spec phase. The hook contract, `claude -p`, and plan mode are native Claude Code; do not wrap this in Temporal or an external orchestrator at the spec stage.

**Verify at build time / honest limits:** the exact `settings.json` key for default plan mode and the `SessionStart`/`PreToolUse` behaviors are version-gated — confirm against code.claude.com. Z3 only checks the logic you actually encode, so EARS→SMT-lib translation fidelity is where correctness is won or lost; budget for the translation step, and treat the checklist as living domain knowledge that must be maintained, since gap-detection is only as good as the baseline it checks against.

### B. Coverage model (default-unproven map)
**Recommended:** Build it yourself as a thin `feature_list.json` artifact — this is honestly not an off-the-shelf product, and that's fine. Follow Anthropic's harness pattern: JSON (resists model corruption better than markdown), every item carries an ID, type (functional / NFR / WIRING), priority, dependencies, acceptance criteria, and a status that starts `unproven` and can only flip to `proven` with attached evidence. Rule: never remove or reorder items, only flip status. Include NFRs and architectural WIRING (handlers/routes/jobs actually connected into execution paths) as first-class items, not afterthoughts.

**Claude Code integration:** the initializer agent generates it; a PreToolUse hook blocks edits to its schema; the Stop hook validates it. DETERMINISTIC at the gate.

**Skip:** elaborate requirement-graph databases before the flat JSON model works end to end.

### C. Traceability engine (bidirectional requirement↔design↔code↔test↔evidence↔commit↔owner)
**Recommended:** Managed Postgres (see I) holding a traceability graph, enriched with OpenTelemetry runtime spans linking requirement IDs to actual executed code paths. For a lighter, docs-as-code option, **StrictDoc** (explicit textX grammar, requirements-to-source traceability, ReqIF import/export, custom fields like PRIORITY/OWNER) or its predecessor **Doorstop** (one YAML file per requirement in git) are the right shape for agents — plain-text, git-native, CLI-driven, free. **Avoid** enterprise ALMs (Jama, Polarion): they are GUI-centric, license-heavy, and wrong-shaped for an agent that needs to read/write traceability as files and API calls.

**Claude Code integration:** agent writes trace links to Postgres/StrictDoc; commits carry requirement IDs; OTel spans tagged with requirement IDs. Enforcement DETERMINISTIC when the merge gate checks the matrix is complete.

**Skip:** a bespoke graph DB; Postgres + foreign keys is enough.

### D. Incremental execution control & WIRING verification
**Recommended:** Claude Code plan mode (human approves the plan, not each keystroke) + a two-agent initializer/coder harness + git worktrees for parallel isolation (each slice in its own worktree avoids collisions). For WIRING detection ("exists in code but never connected"), run static call-graph / dead-code analysis (Semgrep custom rules, language dead-code linters) plus integration tests that exercise real execution paths — and represent each wiring requirement as a coverage item the verifier must prove.

**Claude Code integration:** plan mode; subagents; `git worktrees`; WorktreeCreate/WorktreeRemove hooks exist. Bounded-slice discipline is PROBABILISTIC (prompt/plan) but the worktree isolation and the wiring gate are DETERMINISTIC.

**Skip:** custom orchestration — subagents suffice. Skip recursive agent swarms.

### E. Verification engine (structural + semantic + wiring + behavioral) with INDEPENDENT evaluators
**Recommended stack, all off-the-shelf:**
- **Behavioral/E2E:** Playwright + the official `@playwright/mcp` server (accessibility-tree driven; `claude mcp add playwright npx @playwright/mcp@latest`). Anthropic's own long-running harness used browser automation and found, per its "Effective harnesses for long-running agents" post, that "providing Claude with these kinds of testing tools dramatically improved performance, as the agent was able to identify and fix bugs that weren't obvious from the code alone" (note: that specific harness used the Puppeteer MCP server; `@playwright/mcp` is the recommended modern equivalent here). Use Playwright CLI in CI for token efficiency; MCP for exploratory self-QA.
- **Contracts:** Pact (code-first consumer-driven contract testing; the de-facto standard, maintained by the Pact Foundation across JS/Java/Python/Go/Ruby/.NET/Rust; pairs with Pact Broker/PactFlow). Lets agent-shipped services prove they won't break consumers/providers before deploy.
- **SAST:** Semgrep (fast, custom YAML rules, runs every PR) + GitHub CodeQL (deeper dataflow, GitHub-native, higher OWASP F1). These catch exactly the patterns AI code produces (SQL string concat, hardcoded secrets, unsafe deserialization).
- **Quality gate:** SonarQube with its **AI Code Assurance** quality gate ("Sonar way for AI Code"), which can block CI when AI-generated code fails thresholds.
- **Structured-output schema enforcement as first-class verification:** Pydantic (Python) / Zod (TypeScript) / BAML (cross-language Rust-compiled DSL with schema-aligned parsing) / Instructor (Pydantic-based, 11k+ stars, 3M+ downloads/month). For Claude specifically, structured output is via tool-use + JSON schema; always validate with Pydantic/Zod as a safety net.
- **Security review:** Claude Code's native `/security-review` command and Anthropic's `claude-code-security-review` GitHub Action (AI-powered security review analyzing diffs for vulnerabilities).
- **Alternatives:** CodeRabbit / Greptile for AI PR review.

**The non-negotiable rule:** use a *separate evaluator agent*, never self-grading. Anthropic's GAN-inspired generator/evaluator harness uses four grading criteria (design quality, originality, craft, functionality) and an evaluator that drives the browser via MCP independently; per Anthropic Labs' Prithvi Rajasekaran, "separating the agent doing the work from the agent judging it" is the key lever.

**Claude Code integration:** PostToolUse hooks run formatter/linter/Semgrep after each edit; SubagentStop hook validates the verifier's evidence; CI runs the full suite. DETERMINISTIC.

**Skip:** building your own test runner or SAST engine.

### F. Completion gates (fail-closed)
**Recommended — two complementary, both deterministic:**
1. **In-loop:** a Claude Code **Stop / SubagentStop hook** that runs the coverage validator and exits 2 (`{"decision":"block","reason":"..."}`) while any `feature_list.json` item is unproven, forcing the agent to keep working. This is the enforcement the model cannot skip.
2. **At-merge:** **OPA/Conftest** (Rego policy: zero unproven requirements) run as a required GitHub status check via **repository rulesets**. Conftest `deny` rules + non-zero exit block the merge.

**Why hooks beat prompts:** a CLAUDE.md instruction "don't finish until tests pass" is complied with *usually*; a Stop hook enforces it *always*. Guard against infinite loops with the `stop_hook_active` flag (exit 0 once the real condition clears).

**Skip:** trusting green tests or self-report as "done."

### G. Session continuity & memory/state (re-examined without bias)
**Recommended (default):** file-based `claude-progress.txt` + CLAUDE.md + git-as-state + Postgres. This is sufficient. Claude Code adds native memory (CLAUDE.md hierarchy), checkpointing/rewind, and compaction/auto-compact with PreCompact hooks (back up transcript/progress before context is trimmed). A dedicated memory service (Letta / Mem0 / Zep) is **over-engineering for v1** and only earns its keep if you later need cross-project semantic recall at scale.

**Claude Code integration:** SessionStart hook loads git status + progress; PreCompact hook checkpoints; rewind for recovery. DETERMINISTIC (hook-driven persistence).

**Skip:** a memory graph before traceability works.

### H. Orchestration layer (re-examined without LangGraph bias)
**Conclusion:** Claude Code subagents + hooks (and, when mature, Agent Teams) ARE the inner orchestrator. An external agent-reasoning framework (LangGraph, Pydantic AI, Google ADK, CrewAI, Mastra, Vercel AI SDK, Microsoft Agent Framework) is usually **redundant** on this substrate — they re-implement the loop Claude Code already provides. (LangChain's own docs note that "agent harnesses" like the Claude Agent SDK and coding CLIs are an alternative integration layer to LangGraph.) This matches the loop-engineering principle: deterministic code drives, the LLM only makes the decisions code can't.

**Add a durable OUTER loop ONLY for crash-safe multi-hour/multi-day runs:** **Temporal** (journal/replay durable execution; raised a $300M Series D at a $5B valuation led by Andreessen Horowitz, announced Feb 17, 2026; Temporal states it powers certain production workflows at OpenAI — note this is broader than "Codex" specifically; LLM calls are wrapped as Activities that journal-on-first-run and never re-execute on replay) or **Inngest** (simpler event-driven durability) invoking `claude -p` headless as a durable step/activity. There is a documented production pattern combining the Claude Agent SDK with Temporal (durable sleep, saga compensation, signals). As a16z framed it, "for long-running agents operating over extended horizons, the durability that Temporal provides is the difference between a compelling demo and a production system."

**Skip:** an external reasoning framework as your primary orchestrator. Adopt the outer loop only when you actually need crash recovery across hours.

### I. Durable storage
**Recommended:** managed Postgres for traceability + run state + evidence. Three good fits:
- **Neon** — serverless, copy-on-write **branching** (a branch from a 50 GB DB in <1s), scale-to-zero; Databricks announced intent to acquire Neon on May 14, 2025 (reported ~$1B). Per Databricks, "over 80 percent of the databases provisioned on Neon were created automatically by AI agents rather than by humans" — confirming it is purpose-built for agent workloads (fork-per-task). Best when agents spin up throwaway DBs per branch/PR.
- **Supabase** — full backend (auth, storage, realtime, edge functions) on Postgres; best when you also need app backend services.
- **GCP Cloud SQL** — for GCP ecosystem cohesion (Vertex AI, Cloud Run, GKE).
All support **pgvector** (and pgai/pgvectorscale) for semantic search if needed later — pgvectorscale has been benchmarked at ~28ms p95 at 50M vectors.

**Simplest sufficient choice:** Neon if you want per-PR DB branching; Supabase if you want a bundled backend; Cloud SQL for GCP cohesion. Skip a dedicated vector DB (Pinecone) for v1.

### J. Observability & evaluation (anti-loopmaxxing layer)
**Recommended:** Export Claude Code's built-in OpenTelemetry (set `CLAUDE_CODE_ENABLE_TELEMETRY=1`; it emits spans per model request/tool execution, plus `claude_code.cost.usage` and `claude_code.token.usage` metrics, over OTLP) into **Langfuse** (OSS, OTel-native; ClickHouse announced its $400M Series D — led by Dragoneer, ~$15B valuation — and its acquisition of Langfuse on Jan 16, 2026; per Orrick, Langfuse has "more than 2,000 paying customers, 26M+ SDK installs per month, and 6M+ Docker pulls, and is trusted by 19 of the Fortune 50 and 63 of the Fortune 500"; self-hosting/OSS licensing stated unchanged) — it has an official Claude Agent SDK integration via OpenInference. **Alternatives:** Arize Phoenix (built on OpenTelemetry/OpenInference but licensed **Elastic License 2.0, source-available, not OSI** — matters for procurement, as ELv2 forbids offering it as a hosted service); W&B Weave (Weights & Biases was acquired by CoreWeave, closed May 5, 2025, ~$1.7B; strong tracing/eval but **no native eval-gating-in-CI** — you'd build custom pipelines); **Braintrust** for eval-gated CI (native GitHub Action runs evals on every PR and blocks the merge when scores fall below defined thresholds).
**Offline eval harnesses:** promptfoo (OSS MIT, CI quality gates, now part of OpenAI per its repo header but "remains open source and MIT licensed"), Braintrust, DeepEval (Apache 2.0, "pytest for LLMs," `deepeval test run` in CI, 250+ contributors).

**Anti-loopmaxxing controls live here** — see dedicated section below.

**Skip:** a heavyweight commercial observability suite before you've instrumented the free OTel path.

## First-Class Section: HOOKS — the deterministic enforcement backbone

Hooks fire at fixed lifecycle points; Claude Code passes JSON on stdin and the handler signals via exit code (exit 2 = block) or JSON `{"decision":"block","reason":...}`. They are deterministic because **the harness runs them unconditionally as shell/HTTP commands — the model cannot choose to skip them**, unlike CLAUDE.md/prompts/Skills which are advisory. Real events (per Anthropic docs) include: SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PostToolUse and their failure variants, Stop, SubagentStart, SubagentStop, PreCompact, PostCompact, Notification, PermissionRequest, and more (the doc set lists roughly 30 events across the Claude Code CLI and Agent SDK; many are version-gated — e.g., SubagentStop since v1.0.41, PermissionRequest since v2.0.45, PostCompact/Elicitation since v2.1.76 — so verify against current docs).

Concrete hooks for THIS system:
- **Stop hook = coverage gate.** Runs the `feature_list.json` validator; exits 2 / returns `block` while any item is unproven, forcing continued work. Guard with `stop_hook_active` to avoid infinite hook loops; exit 0 once clean.
- **PostToolUse (matcher `Write|Edit|MultiEdit`) = run formatter + linter + Semgrep after each edit.** Multiple hooks run in parallel; can inject feedback ("3 type errors on lines 42, 78, 103") to help the model self-correct rather than just blocking.
- **PreToolUse = block edits to protected files** (tests, `feature_list.json` schema, CI config) and dangerous Bash (`rm -rf`, `DROP TABLE`); since v2.0.10 it can also rewrite tool input transparently.
- **PreCompact = checkpoint progress before context compaction** (back up transcript/progress file) — the most underused event and your defense against context loss.
- **SubagentStop = validate a subagent's evidence before accepting its result** (e.g., confirm the verifier actually attached passing browser-test output).
- **SessionStart = load context** (git status, progress file) so a resumed/relaunched session orients itself.

Hook handler types: command (shell), HTTP, and prompt (LLM-evaluated, good for nuanced Stop/SubagentStop checks). Tool-hook execution timeout is generous (10 minutes as of v2.1.3). For audit, forward every hook event to your observability endpoint.

## First-Class Section: AGENT TEAMS vs SUBAGENTS

**Subagents** = hierarchical delegation: the main session spawns workers, each in its own fresh context window, that do a scoped task and return only a summary; intermediate noise stays in the child. No lateral communication — if worker A learns something B needs, it routes A→main→B. GA, the primitive Anthropic recommends starting with, ~4–7x token cost vs a single session. Built-ins: Explore (Haiku, read-only), Plan, general-purpose. Custom subagents are markdown files with YAML frontmatter in `.claude/agents/`.

**Agent Teams** (experimental, research preview) = peer-to-peer: a team lead spawns independent teammates, each a full Claude Code session with its own context, that communicate directly via a mailbox/`SendMessage` system and a shared task list (`~/.claude/tasks/`). Requires v2.1.32+, Opus 4.6, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`; shipped Feb 5, 2026 alongside Opus 4.6. Anthropic validated the architecture at scale: per researcher Nicholas Carlini's engineering post "Building a C compiler with a team of parallel Claudes," "over nearly 2,000 Claude Code sessions and $20,000 in API costs, the agent team produced a 100,000-line compiler that can build Linux 6.9 on x86, ARM, and RISC-V" (~2B input tokens, ~140M output tokens). Documented limitations: no session resumption of in-process teammates, task-status lag blocking dependents, slow shutdown, one team at a time, no nested teams; ~15x token cost.

**Mapping to requirements:**
- **Cluster 9 (planner/implementer/verifier coordination):** subagents give you clean role separation today (planner subagent, implementer subagent, independent verifier subagent). Agent Teams would let a verifier *peer* watch an implementer in real time and flag drift mid-task (vs an after-the-fact verifier subagent) — directly attacking the execution-drift cluster — but only once mature.
- **Honest v1 stance:** depend on **subagents** for the safety-critical planner/implementer/verifier loop. Treat Agent Teams as an experiment for parallel research/review, behind a flag, not on the path that gates delivery. Re-evaluate when Anthropic removes the experimental label and fixes session resumption.

## First-Class Section: AWARENESS & MID-FLIGHT STEERING

This is the "nervous system" of the control loop: you cannot steer what you cannot see, and seeing is not the same as intervening. The section separates two modes that are frequently conflated, names the deterministic boundary between them, and places predictive "next-step" routing on the correct side of that boundary. The governing rule, repeated because it is load-bearing: **deterministic gates — hooks, CI, OPA — decide whether delivery is complete; awareness and prediction only inform, they never gate.**

### The split: passive awareness vs active steering
- **Passive awareness (the sensory layer, read-only).** A trace is being written as the agent acts; a human, a dashboard, or an LLM watcher *can* read it, but nothing is *required* to act. This is detection, not control. Awareness alone is monitoring.
- **Active steering (the motor layer, deterministic).** A process reads a signal mid-run and *synchronously halts or redirects* the agent. In Claude Code this is hooks, and only hooks — they run unconditionally and a non-zero exit changes what happens next, independent of what the model "intended." Steering without awareness is a black box that silently rejects work with no audit trail. Both are necessary; neither substitutes for the other.

A third, optional mode — **predictive routing** ("what context will the agent need next?") — is *not* a third gate. It is an acceleration aid layered on the sensory side. It may inject context or suggest a route; it must never emit a block/allow decision. (See "Predictive routing, correctly placed," below.)

### Detection: the awareness layer
- **OpenTelemetry is the substrate, and it is read-only.** Claude Code emits OTel spans/metrics/events when telemetry is enabled (`CLAUDE_CODE_ENABLE_TELEMETRY=1` plus an OTLP exporter), and export is mid-flight/streaming — each span ships as it closes, not batched at run-end — so a watcher sees the execution tree in real time. (Enforcement: this is observation, not intervention; it cannot stop anything.)
- **Honest status caveat:** the **OpenTelemetry GenAI semantic conventions are still experimental ("Status: Development") as of mid-2026** — the spec itself states the transition plan "will be updated to include stable version before the GenAI conventions are marked as stable." Pin your instrumentation version and opt in with `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`; keep your own business identifiers (`requirement.id`, `run_id`) stable regardless of semconv churn. Do **not** claim these attributes are stable — they are not. (A current benchmark, AgentTelemetry, OpenReview submission, finds vanilla OTel detects only ~43% of agent-specific faults precisely because planning/reasoning/memory phases lack span coverage — so treat OTel as necessary but not sufficient for agent awareness.)
- **Tag every span with the active requirement ID via W3C Baggage.** Set `requirement.id` once in OpenTelemetry Baggage at task start and use a `BaggageSpanProcessor` to promote it onto every child span automatically — this is the intended use of Baggage and makes the live trace filterable by requirement without per-span boilerplate. This is the single most valuable awareness practice here.
- **Forward gate decisions into the same trace.** Each hook should emit its outcome (event name, triggering tool, allow/block, reason, requirement ID) to the same OTLP endpoint as the agent spans, so one unified, time-ordered trace shows *both* what the agent did *and* every gate decision — the dual record needed for debugging and audit. Claude Code already emits hook-execution and permission-decision events into the telemetry stream.
- **Live backends (with honest licensing).** All three common choices are OTLP-native and stream live: **Langfuse** (MIT core, `ee/` enterprise; acquired by ClickHouse Jan 2026, licensing unchanged) — recommended default; **SigNoz** (MIT Expat core, `ee/` enterprise) if you want LLM + infra traces in one pane; **Arize Phoenix** — **note: Elastic License 2.0, source-available, NOT OSI open-source, and its terms prohibit offering it as a hosted/managed service**, which matters for procurement. Do not present the three as equivalently "open source."
- **Agent self-observation — calibrate the claim.** An LLM reading the trace to improve is a real *outer-loop* (between-run) practice — refine prompts/skills/datasets from traces + feedback. Live, *in-session* "the agent reads its own streaming trace and self-corrects within the same run" is emerging and hype-prone; do not depend on it for correctness. Use the deterministic motor layer for in-run control.

### Steering: the deterministic motor layer
Hooks are the only mechanism that deterministically intervenes inside a running session. Pick the right event for the job — and respect what each can and cannot do:
- **PreToolUse = the true pre-action gate (DETERMINISTIC, prevents).** Fires *before* a tool runs; exit 2 / `permissionDecision:deny` blocks it. This is the only place that can actually *stop* a destructive or policy-violating action (e.g., edits to protected files like tests or `feature_list.json` schema, `rm -rf`, `DROP TABLE`). Use command-type hooks for hard policy; HTTP/MCP hooks fail open.
- **PostToolUse = a next-turn forcing function (DETERMINISTIC feedback, CANNOT undo).** Fires *after* the tool already ran — the file is already written. Running lint/Semgrep/wiring-checks here and exiting 2 surfaces the specific errors to the agent so it *fixes them on the next turn*; it does **not** roll back the edit. (This is confirmed behavior, including a known Claude Code issue where exit 2 shows a "blocking error" yet the write persists.) Do not describe PostToolUse as "blocking" without this caveat; route any true prevention need to PreToolUse.
- **SubagentStop = evidence validation before acceptance (DETERMINISTIC).** Fires when a subagent finishes; block acceptance of its result if required evidence (test references, requirement citations, passing output) is absent, forcing it to continue.
- **Stop = the coverage gate (DETERMINISTIC).** Fires when the agent tries to end its turn; `decision:block` (reason required) forces it to keep working while any in-scope requirement is unproven. Guard with the `stop_hook_active` flag so the hook doesn't loop on itself, gate the block on a real failing check, and return clean once it clears. This is the in-loop twin of the OPA/CI merge gate from Section F.
- **Why not Temporal for this.** Temporal/Inngest operate at the supra-step **activity boundary** — they make a multi-hour run crash-safe and resumable, but a single agent invocation is one opaque activity to them, so they react to *step-level* outcomes (a verification step returned failed → retry/compensate) and are blind to token/tool-level events inside the run. They are complementary to hooks (durability), not a substitute (sub-step gating). Own the loop in hooks; wrap it in Temporal only when crash-durability across hours is the actual need.

### Predictive routing, correctly placed (read-only, never a gate)
The idea — use a fast LLM/SLM to predict the "semantic best next step" for each concluded event and inject just-in-time context (route the agent to the right file/data/keyword) to fight context exhaustion, reduce exploratory tool calls, and cut tokens — is legitimate and valuable. But a prediction can be wrong, so it is **probabilistic** and must stay strictly off the enforcement path:
- **It may** inject advisory `additionalContext` (e.g., via a `UserPromptSubmit`/`SessionStart` context-injection hook or an MCP "predict/retrieve" tool) and suggest routing.
- **It must never** emit a block/allow gate decision, and a gate must never read a prediction. A wrong-negative would wave incomplete delivery through; a wrong-positive would block correct delivery — either way the gate's guarantee is destroyed. Gate decisions are computed solely from verifiable facts (tests pass, coverage met, artifacts present), run against the *actual* repo state, never the predictor's belief about it.
- **Anti-bias / anti-drift guardrails:** keep the predictor read-only w.r.t. gates; tag predicted-routing spans with a distinct attribute so their influence is auditable; measure prediction acceptance/accuracy as a metric and disable routing on drift; treat retrieved/predicted content as untrusted input (separate "data" from "instructions") to avoid prompt-injection contamination; enforce the iteration/token caps below so a confidently-wrong predictor cannot drive a runaway loop.
- **Maturity, stated honestly:** the "PredictStream" project that motivated this idea is a **pre-product concept** as of mid-2026 — a "Coming Soon" page whose promised alpha has lapsed, with no public repository, package, or technical specification — so it is **not** a dependency you can adopt today. Do not present it as a shipping framework. Build the capability instead on battle-tested primitives that already do this job: **Speculative Actions** (arXiv:2510.04371; reports up to ~55% next-action prediction accuracy and ~20% latency reduction, with semantic guards and rollback when a guess is rejected — the safe blueprint), **semantic-router / the production vLLM Semantic Router**, just-in-time context retrieval (Anthropic context-engineering), and the **Claude memory tool + context editing** (Anthropic reports memory + context editing improved a long-horizon agent task by 39% over baseline and cut token use by 84% in a 100-turn evaluation). Prefer these shipping primitives over net-new prediction infrastructure.

### EARS requirements (awareness & mid-flight steering)
Authored in EARS syntax; each carries an ID and a deterministic/probabilistic label. "The system" = the spec-to-evidence control plane on Claude Code.

- **REQ-AMS-001 (Ubiquitous, DETERMINISTIC):** The system shall emit an OpenTelemetry span for every model call, tool invocation, and sub-agent task during a run.
- **REQ-AMS-002 (Ubiquitous, DETERMINISTIC):** The system shall propagate the active requirement ID into every span via W3C Trace Context Baggage so all child spans are filterable by `requirement.id`.
- **REQ-AMS-003 (State-driven, DETERMINISTIC):** WHILE a run is in progress, the system shall stream each span to the observability backend as it closes, rather than batching at run-end.
- **REQ-AMS-004 (Event-driven, DETERMINISTIC):** WHEN a hook makes a gate decision, the system shall emit that decision — event name, triggering tool, allow/block, reason, and requirement ID — to the same trace endpoint as the agent spans.
- **REQ-AMS-005 (Unwanted behaviour, DETERMINISTIC):** IF a tool action would edit a protected artifact or perform a destructive operation, THEN the system shall block it via a PreToolUse hook before it executes.
- **REQ-AMS-006 (Event-driven, DETERMINISTIC feedback):** WHEN a file edit completes, the system shall run lint, Semgrep, and wiring checks via a PostToolUse hook and, on failure, return the specific errors to the agent for correction on its next turn. (The system shall not rely on PostToolUse to reverse the edit.)
- **REQ-AMS-007 (Event-driven, DETERMINISTIC):** WHEN a sub-agent completes, the system shall validate its evidence via a SubagentStop hook and block acceptance of the result if required evidence is absent.
- **REQ-AMS-008 (Unwanted behaviour, DETERMINISTIC):** IF the agent attempts to end its turn WHILE any in-scope requirement is unproven, THEN the system shall block termination via a Stop hook (guarded by `stop_hook_active`) and return the unproven items.
- **REQ-AMS-009 (Ubiquitous, DETERMINISTIC):** The system shall compute every gate decision solely from verifiable facts (passing tests, coverage thresholds, artifact presence) evaluated against the actual repository state.
- **REQ-AMS-010 (State-driven, DETERMINISTIC):** WHILE a control loop is running, the system shall enforce a hard iteration cap and a token/cost budget and shall hand off to a human on breach.
- **REQ-AMS-011 (Unwanted behaviour, DETERMINISTIC):** IF the loop makes no measurable progress across consecutive iterations, THEN the system shall halt and hand off to a human rather than retry indefinitely.
- **REQ-AMS-012 (Optional feature, PROBABILISTIC, read-only):** WHERE predictive next-step routing is enabled, the system shall inject predictions only as advisory context and shall never permit a prediction to emit, or a gate to read, a block/allow decision.
- **REQ-AMS-013 (Optional feature, DETERMINISTIC audit):** WHERE predictive routing is enabled, the system shall tag predicted-routing spans distinctly and measure prediction acceptance/accuracy so its influence is auditable and routing can be disabled on drift.

### User stories
- *As an operator,* I want to watch a live trace of an in-progress run filtered by requirement ID, so I can see what the agent is doing and why before it finishes.
- *As a reviewer/auditor,* I want every gate decision co-located with the agent action that triggered it in one trace, so I can audit both what happened and which invariant was enforced.
- *As an engineer,* I want the agent blocked from declaring "done" while any requirement is unproven, so incomplete delivery cannot ship — regardless of what the model claims.
- *As a platform owner,* I want runaway loops to halt on iteration, budget, and no-progress limits and hand off to a human, so a hallucinating agent cannot burn the budget or accrue comprehension debt.
- *As a developer,* I want optional predictive routing to speed the agent toward the right context without ever being able to override a gate, so I get acceleration without sacrificing the enforcement guarantee.

### Simplest sufficient choice + what to skip
Enable OTel telemetry to Langfuse with `requirement.id` Baggage tagging and forward hook decisions into the same trace (awareness); wire PreToolUse (prevent), PostToolUse (fix-next-turn), SubagentStop (evidence), and Stop (coverage gate) as command-type hooks (steering); enforce iteration/budget/no-progress limits (loop safety). **Skip for v1:** predictive routing entirely until the deterministic spine is proven — add it later as a read-only acceleration aid using shipping primitives (memory tool, context editing, semantic-router), never as a gate. Skip Phoenix unless its ELv2 hosted-service restriction is acceptable to legal.

### Verify at build time / honest limits
The OTel GenAI conventions are experimental and attribute names can change; pin and opt in. The Claude Code hook event roster (~27–30 events as of mid-2026) and exact decision schemas are version-gated — confirm against code.claude.com. PostToolUse "blocking" is a next-turn forcing function, not an undo. AgentTelemetry and the predictive-routing papers cited are preprints/submissions; treat their headline numbers as directional, not field-proven. PredictStream is pre-product — do not wire a dependency to it.

## ANTI-LOOPMAXXING CONTROL SECTION

The philosophy ("loop engineering," crystallized by Google engineer Addy Osmani in June 2026, echoing Peter Steinberger of OpenClaw — "you should be designing loops that prompt your agents" — and Anthropic's Boris Cherny, who leads Claude Code — "I don't prompt Claude anymore… my job is to write loops") is to design the control system, not hand-prompt. The anti-pattern ("loopmaxxing") is open-ended `while(true)`, fuzzy goals, agents grading themselves, token explosion, comprehension debt, observability collapse. Controls, each mapped to a deterministic mechanism:

- **Deterministic exit conditions:** passing tests / clean compile / zero-exit; encoded in the Stop hook and CI. Never "the model says it's done."
- **Strict iteration caps:** `claude -p --max-turns N` in headless/CI runs caps agentic turns (a turn is consumed per tool call); `--max-budget-usd` caps spend (newer flag — verify against the current CLI reference). A circuit breaker for runaway loops.
- **Progress/stuck detection:** progress file + git-commit cadence; a watchdog (in the Temporal/Inngest outer loop or a Stop-hook counter) terminates runs making no measurable coverage progress.
- **Cost/token governance:** `CLAUDE_CODE_ENABLE_TELEMETRY=1` → OTel `claude_code.cost.usage` / `claude_code.token.usage` metrics (broken down by input/output/cacheRead/cacheCreation, model, query_source) with alerts; `/cost` (API users) / `/stats` (Pro/Max subscribers); per-invocation `total_cost_usd` from `claude -p --output-format json`. Note: from June 15, 2026, Agent SDK / `claude -p` usage on subscription plans draws from a separate monthly Agent SDK credit — factor this into cost design.
- **Separate-evaluator rule:** independent evaluator subagent only; never self-grade.
- **2–3 retry then human handoff:** cap retries per slice; on exhaustion, fail gracefully and hand off to a human (PR comment / AskUserQuestion / plan-mode pause) rather than looping.
- **Comprehension-debt mitigation:** trace-log agent reasoning and tool calls (OTel spans + hook event forwarding) and keep human-readable evidence (browser test reports, verifier critiques, commit messages) so a human can audit *why* the agent did what it did.

## End-to-End Reference Architecture (strict control loop)

1. **Intent** → terse product goal.
2. **Proactive-discovery spec** → Spec Kit + EARS + initializer agent elaborates implied/competitive features from domain baseline checklists; optional Kiro SMT requirements-analysis catches contradictions/gaps. (PROBABILISTIC gen → DETERMINISTIC SMT check.)
3. **Default-unproven coverage model** → initializer agent writes `feature_list.json` (functional + NFR + WIRING items, IDs, acceptance criteria, status=unproven). PreToolUse hook protects its schema.
4. **Bounded execution** → plan mode (human approves plan); coding subagent takes ONE highest-priority item in a dedicated **git worktree**; PostToolUse hooks format/lint/Semgrep after each edit.
5. **Independent verification** → separate evaluator subagent runs behavioral (Playwright MCP), wiring (call-graph/integration), semantic (review), security (Semgrep/CodeQL, `/security-review`); SubagentStop hook validates its evidence.
6. **Evidence capture** → reports + commits (with requirement IDs) + structured records to Postgres/object storage; optional Sigstore/SLSA attestation.
7. **Fail-closed completion gate** → **Stop hook** blocks run termination while any item unproven (in-loop); **OPA/Conftest + GitHub required status checks** block merge (at merge).
8. **Durable Postgres store** → traceability graph + run state + evidence (Neon/Supabase/Cloud SQL).
9. **OTel observability** → Claude Code telemetry → Langfuse/Phoenix; cost/token metrics + traces.
10. **Human handoff on stuck/budget** → iteration cap / retry cap / budget breach → graceful failure + handoff.
11. **(Optional) Durable outer loop** → Temporal/Inngest wraps the whole thing as crash-safe steps invoking `claude -p`, ONLY for multi-hour/day runs.

## MISSED Components (managed answers + Claude Code path + label)
- **Supply-chain/dependency security:** Dependabot + Snyk (SCA) + GitHub Advanced Security/Code Security; **Sigstore/SLSA provenance via `actions/attest-build-provenance`** (binds artifact digest to a SLSA build provenance predicate via in-toto, signed with a short-lived Sigstore cert; provides SLSA v1.0 Build Level 2 out of the box; verifiable with `gh attestation verify`). CI-enforced → DETERMINISTIC.
- **Sandboxing/isolation:** Claude Code native `/sandbox` (OS-level) for unattended runs; E2B (Firecracker microVMs, hardware-level isolation), Daytona (sub-90ms container cold-starts), Modal (GPU sandboxes), or devcontainers. Run agent execution sandboxed. DETERMINISTIC (isolation).
- **Structured-output/schema enforcement:** Pydantic/Zod/BAML/Instructor as first-class verification (see E). DETERMINISTIC (schema validation).
- **Human-in-the-loop approval surfaces:** plan mode, AskUserQuestion, GitHub PR review, feature-flag approval. Mixed.
- **Cost & token governance:** see anti-loopmaxxing. DETERMINISTIC (caps).
- **Prompt/spec version control & regression testing:** promptfoo in CI. DETERMINISTIC (gate).
- **Evidence storage & signed attestations:** object storage + Sigstore/in-toto/SLSA. DETERMINISTIC.
- **DAST/SAST in CI:** OWASP ZAP (DAST), CodeQL + Semgrep (SAST). DETERMINISTIC.
- **Feature-flagging/progressive delivery:** LaunchDarkly (mature commercial; handles ~20 trillion feature requests/day per CNCF, instant kill-switches/rollback) + OpenFeature (CNCF Incubating since Nov 2023, vendor-neutral flag standard, adopters include eBay/Google/Spotify/SAP) for safe rollout + instant rollback of agent-shipped changes. Decoupling deploy from release is essential for safely shipping agent-generated code. DETERMINISTIC (kill switch).

## Honest "Build-It-Yourself Gaps"
1. **The coverage model (`feature_list.json`) and its validator** — no off-the-shelf product fits; build the thin JSON artifact + Stop-hook validator + OPA policy. This is the heart of the system and it's custom.
2. **The proactive-discovery initializer agent + domain baseline checklists** — Spec Kit/Kiro scaffold specs but don't infer a *complete competitive* feature set from terse intent; that elaboration logic is yours (a subagent + curated checklists).
3. **WIRING verification glue** — detecting "exists but never connected" combines Semgrep custom rules + call-graph/dead-code tooling + integration tests, wired to coverage items; the integration is custom.
4. **The traceability link-writing** between requirement IDs ↔ commits ↔ OTel spans ↔ evidence — Postgres schema + the agent instructions to maintain it are yours.
5. **Eval-gating-in-CI if you choose Langfuse/Weave** (neither gates natively — Weave would require custom CI pipelines) — either adopt Braintrust/promptfoo/DeepEval or build the CI threshold check.

## Phased Adoption Roadmap
- **Phase 0 — Spine (build first, simplest reliable):** Spec Kit + EARS spec; `feature_list.json` coverage model; one initializer + one coder + one independent verifier subagent; git worktrees; Stop-hook coverage gate; git + a single Postgres table for run state; Playwright (CLI) behavioral proof; GitHub required status checks. **Do NOT build:** Agent Teams, durable outer loop, memory service, custom orchestration, recursive swarms.
- **Phase 1 — Verification depth:** add Semgrep + CodeQL + SonarQube AI quality gate + `/security-review`; Pact contracts; OPA/Conftest merge policy; PostToolUse lint/format/scan hooks; structured-output schema validation. **Skip:** elaborate memory graphs.
- **Phase 2 — Durable state:** formalize Postgres traceability graph (Neon/Supabase/Cloud SQL); PreCompact checkpoints; evidence storage + Sigstore/SLSA attestations.
- **Phase 3 — Durable outer loop (only if needed):** Temporal or Inngest wrapping `claude -p`, ONLY when runs must survive multi-hour/day crashes. **Don't add before you feel real crash pain.**
- **Phase 4 — Observability/eval + supply-chain + delivery safety:** OTel → Langfuse/Phoenix; promptfoo/Braintrust/DeepEval eval gates; Dependabot/Snyk; LaunchDarkly/OpenFeature progressive delivery + kill switches.
- **Phase 5 — Experimental (guarded):** pilot Agent Teams for parallel research/review behind a flag once Anthropic removes the experimental label and fixes session resumption.

## Recommendations
1. **Build Phase 0 now.** The spine — coverage model + Stop-hook gate + independent verifier + worktrees — solves the stated problem (reject incomplete delivery) with the least machinery. Benchmark that would change nothing: a run cannot terminate with any unproven item, and a human never has to manually catch a missing/unwired piece. If that holds, you're done for v1.
2. **Make every "done" deterministic.** No green-tests-or-self-report completion. Threshold to relax gates: only after the Stop hook + OPA gate have run clean on a meaningful run of consecutive real features with zero human-caught omissions.
3. **Use subagents, not Agent Teams, on the gating path** until the experimental label is gone and session resumption works. Re-evaluate per release notes.
4. **Defer the durable outer loop** until you actually experience crash loss on multi-hour runs. Adopt Temporal/Inngest then, not before.
5. **Adopt Kiro's SMT requirements-analysis** if spec contradictions/gaps are a recurring failure mode — it's the one place formal methods cheaply buy correctness upstream (AWS measured ~60% of first-draft requirements needing refinement).
6. **Instrument OTel from day one** (it's free and built in) so cost/stuck detection and comprehension-debt mitigation are in place before you need them.

## Caveats
- **Version-gated Claude Code features** (Agent Teams flags/limits, exact hook event roster, `--max-budget-usd`, the June 15 2026 Agent SDK credit change) must be verified against current official docs (code.claude.com / docs.claude.com) at build time.
- **Agent Teams is experimental** with real limitations; treat all peer-to-peer claims as preview-quality.
- **SDD tooling is fast-moving and can over-generate** verbose markdown (Fowler); apply the don't-overengineer lens.
- **Some adoption/maturity figures come from vendor or secondary sources** (GitHub star counts, funding, Braintrust's own comparisons, promptfoo's conflicting ~13k–21k star counts) and should be re-checked; the OpenTelemetry GenAI semantic conventions remain in "Development"/experimental status, so attribute names may change.
- **Note on the Anthropic harness:** its public long-running-agent demo used the Puppeteer MCP server, not Playwright MCP; the architecture transfers, but the specific tool differs from this report's recommendation.
- **The single most important principle:** deterministic gates — hooks (in-loop) + CI + OPA (at merge) — not model self-assessment — are what make the system reject incomplete delivery.
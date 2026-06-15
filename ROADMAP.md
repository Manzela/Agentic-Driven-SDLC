# Roadmap

Delivery is organized into a required spine (Phase 0) followed by phases that add depth, durability, observability, and orchestration. Two further phases are optional. The authoritative, task-level plan lives in `.kiro/specs/spec-to-evidence-control/tasks.md`; this document summarizes the phases.

## Phase 0 — Spine (next)

Establish the minimum deterministic control loop:

- [ ] Coverage model (`feature_list.json`) mapping every requirement to a tracked item
- [ ] Stop hook that refuses completion while any item is unproven
- [ ] Verifier subagent that collects and records evidence
- [ ] Git worktrees for isolated execution
- [ ] GitHub required status check
- [ ] Playwright (CLI) for end-to-end behavioral proof

## Phase 1 — Depth

- [ ] Static analysis (CodeQL, SonarQube) and policy-as-code (OPA/Conftest)
- [ ] Evidence schema validation
- [ ] PostToolUse enforcement hooks

## Phase 2 — Durability

- [ ] Postgres-backed coverage and evidence storage
- [ ] PreCompact checkpoints for session continuity
- [ ] Build provenance attestations (SLSA)

## Phase 3 — Observability

- [ ] OpenTelemetry tracing and Langfuse integration
- [ ] Requirement-ID propagation via W3C Baggage

## Phase 4 — Property-based test suite

- [ ] Full property-based test suite (all 30 correctness properties) wired as a required CI gate

## Optional phases (5–6)

- [ ] Phase 5 — Durable orchestration: durable workflow execution and crash recovery (Temporal/Inngest)
- [ ] Phase 6 — Predictive routing: advisory next-step routing that never gates a decision

Cross-cutting hardening folds into the required phases above rather than forming separate phases: sandboxed execution of untrusted code and secret scanning (Phase 1), and hash-chained audit-log integrity (Phase 2). Human handoff is a core terminal state enforced from Phase 0.

## Contributing

See `CONTRIBUTING.md`.

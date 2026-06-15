# Roadmap

Delivery is organized into a required spine (Phase 0) followed by phases that add depth, durability, observability, and orchestration. Two further phases are optional. The authoritative, task-level plan lives in `.kiro/specs/spec-to-evidence-control/tasks.md`; this document summarizes the phases.

## Phase 0 — Spine (next)

Establish the minimum deterministic control loop:

- [ ] Coverage model (`feature_list.json`) mapping every requirement to a tracked item
- [ ] Stop hook that refuses completion while any item is unproven
- [ ] Verifier subagent that collects and records evidence
- [ ] Git worktrees for isolated execution
- [ ] GitHub required status check
- [ ] Playwright MCP for end-to-end verification

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

## Phase 4 — Orchestration

- [ ] Durable workflow execution and crash recovery

## Optional phases

- [ ] Sandboxed execution and secret scanning
- [ ] Audit-log integrity through hash-chained records
- [ ] Escalation, human handoff, and predictive routing

## Contributing

See `CONTRIBUTING.md`.

# Spec-to-Evidence Coverage Control

A Claude Code control plane that gates autonomous software delivery on deterministic, verifiable evidence. Every requirement is compiled into a tracked coverage item, and no run may report completion until each item is backed by a recorded evidence artifact and the deterministic gates pass. The governing invariant is that completion is decided by deterministic gates, not by model self-assessment.

## Status

Pre-implementation. This repository currently contains:

- the reconciled specification (`.kiro/specs/spec-to-evidence-control/`),
- the formal-verification harness that machine-checks the specification's invariants (`verification/`),
- the forensic audit trail that produced the reconciled specification (`audit/`),
- reference and superseded material (`docs/`).

Implementation proceeds from the task plan in `.kiro/specs/spec-to-evidence-control/tasks.md`.

## Repository layout

```
.kiro/specs/spec-to-evidence-control/   Canonical specification (source of truth)
  requirements.md                        EARS requirements
  design.md                              Architecture, correctness properties, hook wiring, schemas
  tasks.md                               Phased implementation plan
verification/
  formal_verification_merged.py          Z3 SMT harness over the specification's invariants
audit/                                   Forensic audit and reconciliation record
docs/reference-architecture/             Background reference architecture
docs/superseded/                         Historical, non-authoritative material
```

## Formal verification

The harness encodes the specification's safety and liveness invariants as Z3 SMT assertions and checks each one against its expected satisfiability.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install z3-solver==4.16.0.0
python verification/formal_verification_merged.py
```

A passing run prints `Result: 34/34 checks passed` and exits 0; any failed assertion exits non-zero. The harness comprises 34 assertions across three groups — core consistency, scope-and-evidence, and amendment-and-gate — and is the authoritative count of its own assertions.

## Architecture

The control plane enforces its invariants through Claude Code hooks rather than model judgment. Six hooks participate: PreToolUse, PostToolUse, Stop, SubagentStop, PreCompact, and SessionStart. A coverage model tracks each requirement's status and evidence; a Stop-gate refuses completion while any item is unproven; an evidence schema requires a recorded artifact before an item is marked passed; and a resume-integrity gate blocks a run whose state hash does not match on resume.

See `.kiro/specs/spec-to-evidence-control/design.md` for the component inventory, correctness properties, hook-wiring table, and data schemas.

## Documentation

- `CONTRIBUTING.md` — development workflow and documentation standards
- `SECURITY.md` — security policy and reporting
- `ROADMAP.md` — phased delivery plan
- `CHANGELOG.md` — release history

Material under `docs/superseded/` is retained for provenance only and is not authoritative.

## License

Apache-2.0. See `LICENSE`.

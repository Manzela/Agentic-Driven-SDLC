# Contributing

## Getting Started

```bash
git clone <repository-url>
cd spec-to-evidence-control
python3 -m venv .venv && source .venv/bin/activate
pip install z3-solver==4.16.0.0
python verification/formal_verification_merged.py   # expect: Result: 34/34 checks passed, exit 0
```

## Specification-First Workflow

The specification under `.kiro/specs/spec-to-evidence-control/` is the source of truth. A change to behavior begins with the specification (`requirements.md`, `design.md`), is reflected in the formal-verification harness, and is then implemented per `tasks.md`.

Keep these four artifacts consistent. Any change that alters an invariant or a headline count in one artifact must be reflected in the others, including the harness's self-reported check count.

## Verification

Before submitting changes, run the formal-verification harness and confirm it exits 0. Once the Python package and test suite exist, also run `ruff check`, `mypy`, and `pytest`.

## Documentation Standards

All committed documentation is treated as public, production-grade technical writing:

- No emojis, marketing language, or decorative filler.
- Plain, precise prose; numbers and named technologies must be accurate.
- Active voice; terminology consistent with the specification.
- Code blocks and commands must be runnable as written.
- Comments explain what and why for a maintainer; they do not narrate a process.
- The changelog follows Keep a Changelog and Semantic Versioning.

## Code of Conduct

This project follows the Contributor Covenant. See `CODE_OF_CONDUCT.md`.

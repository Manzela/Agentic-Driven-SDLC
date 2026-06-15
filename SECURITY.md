# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. Do not open a public issue.
2. Email security@manzela.dev with a description and steps to reproduce.
3. Allow 48 hours for an initial response.

## Sensitive Content

This repository must never contain credentials, tokens, API keys, personal data, or proprietary identifiers. Secrets are supplied at runtime through environment variables; only `.env.template` is committed, never `.env`.

## Security Model

The control plane is fail-closed by design. Completion is decided by deterministic gates, not by model self-assessment:

- a run cannot report completion while any coverage item is unproven;
- an evidence record is required before an item is marked passed;
- a resume whose state hash does not match the prior run is blocked.

These invariants are machine-checked by the formal-verification harness in `verification/`.

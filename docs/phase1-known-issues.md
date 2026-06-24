# Phase-1 verification depth — known issues (whole-branch review)

A whole-branch adversarial review (6-dimension fan-out → adversarial verify → synthesize)
ran before this PR. It confirmed the Phase-1 **depth pillars** (orphan/SAST chains, the
coverage/WIRING merge gates, the born-proven/deletion/in_scope/MultiEdit guards for
Edit/Write/MultiEdit) are sound, and surfaced a set of cross-task findings. The **fixed**
ones are in this branch (see the "whole-branch review:" commit). The items below are
**surfaced and tracked** — they are either pre-existing trust-model scope (Phase B / RT-03)
or a design-completeness gap the 18-task plan did not include — and are disclosed here
rather than silently shipped.

## Pre-existing trust-model holes → Phase B (RT-03 crypto chain-of-custody)

These concern the CORE proven-flip authority model (the Phase-A spine), NOT the Phase-1
depth pillars this PR delivers. They predate Phase 1; the spec/plan defer the cryptographic
chain-of-custody that closes them to **Phase B (RT-03)**. They are recorded here so
registration of the new required checks (Task 18 owner action) is made with eyes open.

- **C1 — Bash program-exec write vector is not gated.** The PreToolUse gate's
  `_bash_write_targets` parses only `>`/`>>`/`tee`, so a non-verifier `python -c "open('feature_list.json','w')…"`
  or `python tools/<writer>.py` yields no targets and is allowed. A tool-interception gate
  fundamentally cannot statically analyze arbitrary program execution; the real defense is
  (a) the cryptographic evidence chain (Phase B) and (b) verifier-session isolation. A
  substring path-block would over-block legitimate *reads* (`cat feature_list.json`), so it
  is intentionally NOT added here.
- **C2 — verifier helper tools self-assert identity.** `prove_trivial_slice.py` (Phase A)
  and `wiring_ingest.mark_wiring_failed` (Task 8) write `status` directly with no runtime
  `actor_identity` resolution — their authority is the verifier *session* they run in (the
  same model as the existing prover). Closing this needs the Phase-B session-attestation /
  signed-evidence mechanism, not an in-process check (the functions hold no session context).
- **C3 — `ci_evidence_check` hash backstop is unreachable in the no-dispatch state.** It
  re-derives `output_hash` only when `dispatch_ledger.json` is present, which no workflow
  produces, so a fabricated `output_hash` on a `proven` item is not re-derived by any
  required check in the common state. `coverage_gate.deny_merge` (the binding gate) checks
  field presence, not hash correctness. Failing closed on *proven-without-ledger* would block
  legitimate no-dispatch merges; the correct fix is the Phase-B ledger/attestation always
  being produced. Until then, the out-of-band baseline gate (RT-01/RT-02) still denies
  model-omission / in-scope-shrink when a dispatch delivery is in flight.

## Design-completeness gap (Phase-1 plan did not include the orchestration)

- **WIRING coverage lifecycle has no production trigger (I2/I3).** The components are correct
  and tested — `wiring_checker.emit_wiring_items` → `wiring_dedup.merge` (now fixed to work on
  the real producer shape) → `wiring_ingest.ingest_wiring_candidates` → `coverage_gate` Rule 4
  / the schema `allOf`. But no hook/CLI/loop step calls the `emit → dedup → ingest` chain, so
  no `type:WIRING` item is ever *minted* in a live run, and the §8 "WIRING gate is proveable"
  leg has no prove-through test (the prover proves a functional item; surrogate tests fabricate
  a proven WIRING record). This makes nothing **unsafe** — the gates that fire are sound, and
  `post_tool_use` still surfaces wiring dead-code as advisory feedback — but the seeding pillar
  is inert end-to-end. Wiring it into the loop (analogous to how Task 14 wired the SAST/orphan
  depth feed into `gated_prove`) is a net-new orchestration step beyond the 18-task plan and is
  the recommended **follow-up task**.

## Disclosed deferrals (already documented elsewhere)

- **SonarCloud repo-side scan step** is config-only (`sonar-project.properties`); the scan/job
  + required-check registration are Task-18 owner actions (`docs/github-ruleset.md`,
  `docs/github-public-repo-checklist.md`). The phantom `src` source dir was removed.
- **Rego non-ASCII session-id parity fixture** is absent (the twins agree today; the Python
  side is locked by `test_evidence_gate_unicode.py`). A coverage-gap, not a live divergence.

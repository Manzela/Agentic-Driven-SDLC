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
depth pillars this PR delivers. They predate Phase 1; the cryptographic chain-of-custody that
fully closes them is deferred to **Phase B (RT-03)**. They are recorded here so registration
of the new required checks (Task 18 owner action) is made with eyes open. **C1 has since been
hardened (defense-in-depth) for the statically-parseable shell-write surface** after an
adversarial red-team — see its entry; only its undecidable residual (and C2/C3) still wait on
Phase B.

- **C1 — Bash shell-write vector (now hardened defense-in-depth; an undecidable residual
  remains for Phase B).** An adversarial red-team showed the *original* disclosure here
  understated this: `_bash_write_targets` parsed only `>`/`>>`/`tee`, so a non-verifier could
  write the coverage model **or any protected artifact (tests/hooks/CI/schema)** via a long
  tail of common, statically-parseable shell verbs — not just `python -c`. Confirmed
  empirically: `sed -i 's/unproven/proven/' feature_list.json` (a direct in-place status
  flip), `cp`/`mv`/`install`/`ln`/`rsync` to a protected dest, `dd of=`, `perl -i`,
  `truncate`, `patch`, `tar -x -C`, `ed`/`ex`, the `busybox` multiplexer, macOS `g`-prefixed
  coreutils, `timeout`/`flock`/`time` wrappers, the `>|` noclobber redirect, a leading `./`
  or absolute-under-repo path, and `$'…'` quoting — all yielded `[]` and **allowed** the
  write (the `./`-prefix and bare-dir gaps also defeated the R3 protected-artifact guard).

  **Closed in this change.** `_bash_write_targets` now recognizes those verbs/redirects and
  flags only the write *destination* (sources/reads stay allowed — verified zero false
  positives), and protected-path matching is normalized (`os.path.normpath` + relativize an
  absolute path under the repo root + bare-dir trailing slash, applied to both the Bash and
  Edit/Write guards). Two parser false-positives the red-team surfaced (`cp -t DIR src`
  reading the model out; `sed -i -f script.sed out` reading a script under a protected dir)
  were fixed. The full matrix is regression-locked in
  `tests/spine/test_pre_tool_use_authority.py` (`_REDTEAM_BLOCK` / `_REDTEAM_ALLOW`).

  **Residual → Phase B.** This is defense-in-depth, **not** a complete gate. Verb/wrapper
  recognition is a best-effort allowlist (three adversarial red-team rounds drove it to no
  known false positives and only the residual below). A target produced by stdin
  (`find … | xargs sed -i`), command substitution (`$(printf cp) … f`), a launcher taking a
  quoted command STRING (`bash -c`, `eval`, `su -c '…'`) or a command TEMPLATE (GNU
  `parallel`), arbitrary program execution (`python -c "open('feature_list.json','w')…"`, a
  compiler `-o`, any interpreter), interactive-editor scripting (`vim -c 'wq'`), or a
  cwd-relative path to a protected dir *outside* the repo root has **no static literal target**
  at the tool-call boundary and is still allowed (`_REDTEAM_RESIDUAL` asserts this explicitly).
  Closing the residual is the same RT-03 mechanism as C2/C3: a tool-interception gate
  fundamentally cannot analyze arbitrary program execution, so the real defense is the Phase-B
  cryptographic evidence chain (a raw write of `status:proven` produces no valid signed
  attestation, so the binding gate rejects it however the bytes reached disk) plus
  verifier-session isolation.
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

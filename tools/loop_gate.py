"""loop_gate.py — local PRE-ADVANCE gate: run the deterministic evidence gate
before a slice may advance; on reject, emit a BOUNDED action-directive self-heal
then escalate to HANDOFF. Reuses run_state_driver's block_streak as the self-heal
counter — so a recurring reject converts to HANDOFF rather than looping forever
(do NOT recreate C-LOOP-04).

PHASE A: the dispatch ledger is TRUSTED (cryptographic attestation is Phase B).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import evidence_gate, execution_bounds, run_state_driver  # noqa: E402

def _escalate(*, root, max_self_heal, code, reason, prompt, violation_count):
    """Single run_state tick + self_heal-or-handoff decision, shared by every reject
    path so the no-progress tick happens EXACTLY ONCE per gated_advance call (a double
    tick would corrupt block_streak and the no-progress window the Stop gate reads)."""
    rs = run_state_driver.tick(root, made_progress=False, violation_count=violation_count)
    if rs["block_streak"] >= max_self_heal:
        return {"action": "handoff", "code": code,
                "reason": f"{reason} (unresolved after {rs['block_streak']} self-heal "
                          f"attempts — escalating to HANDOFF, not Done)",
                "prompt": None, "run_state": rs}
    return {"action": "self_heal", "code": code, "reason": reason,
            "prompt": prompt, "run_state": rs}


def gated_advance(*, root, evidence, artifact, ledger, max_self_heal: int | None = None,
                  changed_files=None, baseline_commit=None,
                  feature_list_path=None, known_ids=None) -> dict:
    """Local pre-advance gate. Pillar 0 (evidence validity, fail-CLOSED trust core)
    runs first and IN ISOLATION: on reject it escalates WITHOUT running the depth
    pillars, so a fail-OPEN pillar's "accept" can never mask a rejected trust core.
    When Pillar 0 accepts AND ``changed_files`` is supplied, the fail-OPEN depth
    pillars (Semgrep §4.2, orphans §3.3) run; any reject self-heals with the rejected
    pillars' prompts joined. block_streak >= max_self_heal converts to HANDOFF
    (reusing run_state_driver's counter — do NOT recreate C-LOOP-04)."""
    # Threshold is CONFIG-SOURCED, never memorized (CLAUDE.md: "thresholds come from
    # execution_bounds, not memory"). Default to the SAME bound the authoritative Stop
    # hook escalates on (BLOCK_STREAK_HANDOFF) so the local pre-advance gate and the
    # Stop gate AGREE — a previously hardcoded 3 disagreed with the Stop hook's 5 and
    # ignored the SPINE_BLOCK_STREAK_HANDOFF override entirely.
    if max_self_heal is None:
        max_self_heal = execution_bounds.BLOCK_STREAK_HANDOFF

    # Pillar 0 — evidence validity (fail-CLOSED). A reject short-circuits BEFORE any
    # depth pillar runs: the trust core is authoritative and the fail-open pillars must
    # never get a vote once it has rejected (Pillar-0 isolation, §4.4 / Step 5).
    res = evidence_gate.check_slice(evidence=evidence, artifact=artifact, ledger=ledger)
    if not res["accepted"]:
        return _escalate(root=root, max_self_heal=max_self_heal, code=res["code"],
                         reason=res["reason"], prompt=evidence_gate.self_heal_prompt(res),
                         violation_count=1)

    # Pillar 0 accepted. Depth pillars (fail-OPEN) run ONLY when changed_files supplied
    # — without the producer feed (Task 14) they would receive empty lists and no-op.
    # A bare path STRING is a caller error — normalize to a one-element list so the
    # pillars iterate files, not characters (red-team F2).
    if isinstance(changed_files, str):
        changed_files = [changed_files]

    rejections = []
    if changed_files:
        res_semgrep = evidence_gate.check_slice_semgrep(
            changed_files=changed_files, baseline_commit=baseline_commit)
        if not res_semgrep["accepted"]:
            rejections.append(res_semgrep)
        # The orphan pillar REQUIRES a feature_list_path. Coercing None -> "" (the old
        # behavior) makes check_slice_orphans raise IsADirectoryError and silently
        # fail-OPEN forever — a dead pillar that LOOKS wired (red-team F1). Run it only
        # with a real path; absent one, the producer (Task 14) has not wired it yet, so
        # orphans is EXPLICITLY skipped rather than invisibly disabled.
        if feature_list_path:
            res_orphans = evidence_gate.check_slice_orphans(
                changed_files=changed_files, feature_list_path=feature_list_path,
                known_ids=known_ids or set(), baseline_commit=baseline_commit)
            if not res_orphans["accepted"]:
                rejections.append(res_orphans)

    if not rejections:
        rs = run_state_driver.tick(root, made_progress=True, violation_count=0)
        return {"action": "advance", "code": "OK", "reason": res["reason"],
                "prompt": None, "run_state": rs}

    # One or more depth pillars rejected. Join every rejected pillar's reason AND
    # heal-prompt so the agent sees ALL issues at once (§4.3); code is the first
    # rejected pillar's (Semgrep is checked before orphans).
    joined_reason = "; ".join(r["reason"] for r in rejections)
    bullets = "\n".join(f"  • {p}" for p in
                        (evidence_gate.self_heal_prompt(r) for r in rejections) if p)
    full_prompt = ("One or more depth checks rejected the advance:\n"
                   f"{bullets}\n\nAddress the issues above and attempt the advance again.")
    return _escalate(root=root, max_self_heal=max_self_heal, code=rejections[0]["code"],
                     reason=joined_reason, prompt=full_prompt, violation_count=len(rejections))

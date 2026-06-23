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

def gated_advance(*, root, evidence, artifact, ledger, max_self_heal: int | None = None) -> dict:
    # Threshold is CONFIG-SOURCED, never memorized (CLAUDE.md: "thresholds come from
    # execution_bounds, not memory"). Default to the SAME bound the authoritative Stop
    # hook escalates on (BLOCK_STREAK_HANDOFF) so the local pre-advance gate and the
    # Stop gate AGREE — a previously hardcoded 3 disagreed with the Stop hook's 5 and
    # ignored the SPINE_BLOCK_STREAK_HANDOFF override entirely.
    if max_self_heal is None:
        max_self_heal = execution_bounds.BLOCK_STREAK_HANDOFF
    res = evidence_gate.check_slice(evidence=evidence, artifact=artifact, ledger=ledger)
    if res["accepted"]:
        rs = run_state_driver.tick(root, made_progress=True, violation_count=0)
        return {"action": "advance", "code": "OK", "reason": res["reason"], "prompt": None, "run_state": rs}
    rs = run_state_driver.tick(root, made_progress=False, violation_count=1)
    if rs["block_streak"] >= max_self_heal:
        return {"action": "handoff", "code": res["code"],
                "reason": f"{res['reason']} (unresolved after {rs['block_streak']} self-heal "
                          f"attempts — escalating to HANDOFF, not Done)",
                "prompt": None, "run_state": rs}
    return {"action": "self_heal", "code": res["code"], "reason": res["reason"],
            "prompt": evidence_gate.self_heal_prompt(res), "run_state": rs}

"""governed_pilot.py — exercise the Phase A evidence gate on REAL slices end-to-end.

SCOPE (stated honestly — the pilot does not overclaim):
  * It validates the LOCAL enforcement decision: the deterministic evidence gate
    (tools/evidence_gate.check_slice via tools/loop_gate.gated_advance), driven through
    plane-integration/the_loop.gated_prove — the real, unmodified Phase-A code.
  * The Plane board write runs against a FAITHFUL-STRICT in-process plane_client that
    enforces the SAME authority + gate-order checks the real client does (check_actor /
    legal_edge), so the board-side scenarios have teeth (gate-ACCEPT can still be
    board-REJECTED). The LIVE board (network + real ASCP_VERIFIER_SECRET + server
    read-back) is exercised only once the rotated creds are re-applied to .env.
  * Forgery BREADTH is ALSO pinned by pytest (tests/spine/test_evidence_gate*.py,
    tests/spine/test_coverage_gate_actor_sep.py, tests/plane/test_the_loop_gated_prove.py).
    This pilot is the end-to-end smoke ORACLE, not a replacement for that suite.

ORACLE (A-LOOP-01 — name the verifiable end-state, then check it):
  ACCEPT    valid actor-separated hash-true evidence + legal board state -> advance + Done.
  FORGERY   self-grade (string / unicode-ß / whitespace near-dup), hash tamper, malformed
            hash, naive-timestamp backdate, missing evidence, ghost session, empty/non-string
            session -> NOT advance (the board never reaches Done).
  BOARD     gate-ACCEPT but wrong board state OR non-verifier OR missing secret -> NOT Done,
            AND no Evidence_Record is posted before the authority check (no orphaned evidence).
  ESCALATE  the same reject repeated to BLOCK_STREAK_HANDOFF (config-sourced) -> handoff;
            never a silent loop. The bound is read from execution_bounds, not memorized.
  COVERAGE  check_model: an in-scope item left unproven, and a malformed model, are rejected.
  TRUST     Phase A TRUSTS the dispatch ledger: a ledger of an attacker's OWN two ids PASSES.
            Documented boundary — closed cryptographically in Phase B (RT-03), not here.

Run:   python3 tools/governed_pilot.py
Exit:  0 iff the full oracle holds; non-zero otherwise (the failing scenario is printed).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "plane-integration"))

from tools import evidence_gate  # noqa: E402  (real gate, for the check_model coverage path)
from tools.execution_bounds import BLOCK_STREAK_HANDOFF  # noqa: E402  (config-sourced bound)

_LEGAL_DONE_PREDECESSORS = {"In-Verification", "Human-Review"}


def _mk_pc(*, strict: bool, board_state: str = "In-Verification", verifier_secret: bool = True):
    """A recording in-process plane_client.

    strict=False : board-side checks always pass (isolates the EVIDENCE-gate decision).
    strict=True  : check_actor + legal_edge enforce the same rules the real client does,
                   so a gate-ACCEPT can still be board-REJECTED (raises, like production).
    """
    pc = types.ModuleType("plane_client")
    pc.PBASE = "http://pilot.invalid/api/v1"
    pc.STATES = {}
    calls = []
    pc._calls = calls  # introspected by the runner

    def rec(name):
        def _f(*a, **k):
            calls.append({"fn": name, "args": [str(x) for x in a]})
            return {"ok": True, "fn": name}
        return _f

    pc.post_evidence = rec("post_evidence")
    pc.transition = rec("transition")
    pc.comment = rec("comment")
    pc.get_issue = lambda issue_id: {"state": board_state}
    pc.id2state = lambda s: s

    if strict:
        def check_actor(role, to_state):
            calls.append({"fn": "check_actor", "args": [str(role), str(to_state)]})
            if to_state == "Done" and (role != "verifier" or not verifier_secret):
                raise PermissionError(
                    f"role {role!r} cannot reach {to_state!r}"
                    + ("" if verifier_secret else " (ASCP_VERIFIER_SECRET absent)")
                )
        def legal_edge(cur, to):
            calls.append({"fn": "legal_edge", "args": [str(cur), str(to)]})
            return not (to == "Done" and cur not in _LEGAL_DONE_PREDECESSORS)
        pc.check_actor = check_actor
        pc.legal_edge = legal_edge
    else:
        pc.check_actor = lambda *a, **k: None
        pc.legal_edge = lambda *a, **k: True
    return pc


def _load_the_loop(pc):
    sys.modules["plane_client"] = pc
    sys.modules.pop("the_loop", None)
    spec = importlib.util.spec_from_file_location("the_loop", ROOT / "plane-integration/the_loop.py")
    tl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tl)
    return tl


def _sha(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


ARTIFACT = "PASS tests/spine/test_evidence_gate.py::test_self_grade_rejected 1 passed in 0.02s"
IMPL = "sess-implementer-7f3a"
VERI = "sess-verifier-9b21"


def _good_evidence(**over) -> dict:
    ev = {
        "test_file": "tests/spine/test_evidence_gate.py",
        "test_name": "test_self_grade_rejected",
        "output_hash": _sha(ARTIFACT),
        "collected_at": datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc).isoformat(),
        "implementer_session_id": IMPL,
        "verifier_session_id": VERI,
    }
    ev.update(over)
    return ev


def _fresh_root() -> str:
    return tempfile.mkdtemp(prefix="gpilot-")


def _run(pc, issue_id, evidence, artifact, ledger, root):
    """Run gated_prove; capture decision (or raised exception), board writes, and
    whether evidence was posted (to detect orphaned-evidence)."""
    tl = _load_the_loop(pc)
    pc._calls.clear()
    raised = None
    decision = None
    try:
        decision = tl.gated_prove(issue_id=issue_id, evidence=evidence, artifact=artifact,
                                  ledger=ledger, root=root)
    except Exception as exc:  # board-side reject (strict mock) propagates from _gate
        raised = f"{type(exc).__name__}: {exc}"
    board = list(pc._calls)
    done = any(c["fn"] == "transition" and any(a == "Done" for a in c["args"]) for c in board)
    evidence_posted = any(c["fn"] == "post_evidence" for c in board)
    action = decision["action"] if decision else "raised"
    code = decision.get("code") if decision else None
    return {"action": action, "code": code, "raised": raised, "done": done,
            "evidence_posted": evidence_posted, "board": board}


def main() -> int:
    results = []
    ok = True
    lenient = _mk_pc(strict=False)

    def check(scenario, expect, cond, extra):
        nonlocal ok
        ok &= cond
        results.append({"scenario": scenario, "expect": expect, "pass": cond, **extra})

    # ── ACCEPT (gate decision; lenient board) ───────────────────────────────────
    r = _run(lenient, "PILOT-001", _good_evidence(), ARTIFACT, {"sessions": [IMPL, VERI]}, _fresh_root())
    check("ACCEPT valid actor-separated evidence", "advance + Done",
          r["action"] == "advance" and r["done"], {"action": r["action"], "code": r["code"], "done": r["done"]})

    # ── FORGERIES (caught at the evidence gate; board never written) ─────────────
    forgeries = [
        ("FORGERY self-grade (identical string session)", "SAME_SESSION",
         _good_evidence(verifier_session_id=IMPL), ARTIFACT, {"sessions": [IMPL, VERI]}),
        ("FORGERY self-grade (whitespace/case near-dup)", "SAME_SESSION",
         _good_evidence(implementer_session_id="sess-x", verifier_session_id="  SESS-X  "),
         ARTIFACT, {"sessions": ["sess-x", "  SESS-X  "]}),
        ("FORGERY unicode self-grade (ß folds to ss)", "SESSION_MISSING",
         _good_evidence(implementer_session_id="ss", verifier_session_id="ß"),
         ARTIFACT, {"sessions": ["ss", "ß"]}),
        ("FORGERY output_hash does not re-derive", "HASH_MISMATCH",
         _good_evidence(), ARTIFACT + " <TAMPERED>", {"sessions": [IMPL, VERI]}),
        ("FORGERY malformed output_hash (uppercase hex)", "EVIDENCE_MALFORMED",
         _good_evidence(output_hash="sha256:" + "A" * 64), ARTIFACT, {"sessions": [IMPL, VERI]}),
        ("FORGERY naive (non-tz) collected_at backdate", "EVIDENCE_MALFORMED",
         _good_evidence(collected_at="2026-01-01T00:00:00"), ARTIFACT, {"sessions": [IMPL, VERI]}),
        ("FORGERY no Evidence_Record", "EVIDENCE_MISSING",
         None, ARTIFACT, {"sessions": [IMPL, VERI]}),
        ("FORGERY empty-string verifier session", "SESSION_MISSING",
         _good_evidence(verifier_session_id="   "), ARTIFACT, {"sessions": [IMPL, VERI]}),
        ("FORGERY non-string session id", "SESSION_MISSING",
         _good_evidence(verifier_session_id=12345), ARTIFACT, {"sessions": [IMPL, VERI]}),
        ("FORGERY session not in dispatch ledger", "SESSION_NOT_IN_LEDGER",
         _good_evidence(verifier_session_id="sess-ghost"), ARTIFACT, {"sessions": [IMPL]}),
    ]
    for name, want_code, ev, art, led in forgeries:
        r = _run(lenient, "PILOT-F", ev, art, led, _fresh_root())
        cond = r["action"] != "advance" and not r["done"] and not r["evidence_posted"] and r["code"] == want_code
        check(name, f"NOT advance / {want_code} / no evidence posted", cond,
              {"action": r["action"], "code": r["code"], "done": r["done"]})

    # ── BOARD-SIDE (strict mock: gate ACCEPTS, board enforcement still rejects) ───
    # b1: legal predecessor + verifier + secret -> Done.
    r = _run(_mk_pc(strict=True, board_state="In-Verification", verifier_secret=True),
             "PILOT-B1", _good_evidence(), ARTIFACT, {"sessions": [IMPL, VERI]}, _fresh_root())
    check("BOARD accept (In-Verification, verifier, secret)", "advance + Done",
          r["action"] == "advance" and r["done"], {"action": r["action"], "done": r["done"]})
    # b2: wrong board state -> legal_edge blocks Done; _gate raises BEFORE posting (no orphan).
    r = _run(_mk_pc(strict=True, board_state="Backlog", verifier_secret=True),
             "PILOT-B2", _good_evidence(), ARTIFACT, {"sessions": [IMPL, VERI]}, _fresh_root())
    check("BOARD reject: gate-accept but item in Backlog", "NOT Done / no orphaned evidence",
          not r["done"] and not r["evidence_posted"], {"action": r["action"], "raised": r["raised"], "evidence_posted": r["evidence_posted"]})
    # b3: verifier env missing the secret -> check_actor raises BEFORE posting.
    r = _run(_mk_pc(strict=True, board_state="In-Verification", verifier_secret=False),
             "PILOT-B3", _good_evidence(), ARTIFACT, {"sessions": [IMPL, VERI]}, _fresh_root())
    check("BOARD reject: verifier secret absent", "NOT Done / no orphaned evidence",
          not r["done"] and not r["evidence_posted"], {"action": r["action"], "raised": r["raised"], "evidence_posted": r["evidence_posted"]})

    # ── ESCALATION (config-sourced bound; never a memorized 3) ───────────────────
    esc_root = _fresh_root()
    ev = _good_evidence(verifier_session_id=IMPL)  # persistent self-grade
    actions, last = [], None
    for _ in range(BLOCK_STREAK_HANDOFF):
        last = _run(lenient, "PILOT-ESC", ev, ARTIFACT, {"sessions": [IMPL]}, esc_root)
        actions.append(last["action"])
    expect_actions = ["self_heal"] * (BLOCK_STREAK_HANDOFF - 1) + ["handoff"]
    handoff_comment = any(c["fn"] == "comment" for c in last["board"])
    check(f"ESCALATION reject x{BLOCK_STREAK_HANDOFF} (==BLOCK_STREAK_HANDOFF)",
          f"{BLOCK_STREAK_HANDOFF-1}x self_heal then handoff + HANDOFF comment",
          actions == expect_actions and not last["done"] and handoff_comment,
          {"actions": actions, "handoff_comment": handoff_comment})

    # ── COVERAGE (check_model multi-item path) ───────────────────────────────────
    led = {"sessions": [IMPL, VERI]}
    arts = {"A": ARTIFACT}
    proven_item = {"id": "A", "in_scope": True, "status": "proven", "evidence": _good_evidence()}
    unproven_item = {"id": "B", "in_scope": True, "status": "unproven"}
    cm_unproven = evidence_gate.check_model(model={"items": [proven_item, unproven_item]}, ledger=led, artifacts=arts)
    check("COVERAGE check_model rejects an in-scope UNPROVEN item", "accepted=False (B unproven)",
          not cm_unproven["accepted"] and any(x.get("id") == "B" for x in cm_unproven["rejections"]),
          {"rejections": [x.get("code") for x in cm_unproven["rejections"]]})
    cm_malformed = evidence_gate.check_model(model={"items": "not-a-list"}, ledger=led, artifacts=arts)
    check("COVERAGE check_model fails CLOSED on a malformed model", "accepted=False / MODEL_MALFORMED",
          not cm_malformed["accepted"] and cm_malformed["rejections"][0]["code"] == "MODEL_MALFORMED",
          {"code": cm_malformed["rejections"][0]["code"]})

    # ── TRUST BOUNDARY (Phase A trusts the ledger — documented, not a defect) ─────
    r = _run(lenient, "PILOT-TRUST", _good_evidence(implementer_session_id="atk-a", verifier_session_id="atk-b"),
             ARTIFACT, {"sessions": ["atk-a", "atk-b"]}, _fresh_root())
    check("TRUST forged ledger of attacker's own ids PASSES (Phase-A boundary -> Phase B)",
          "advance + Done (declared boundary; ledger is TRUSTED until Phase B signs it)",
          r["action"] == "advance" and r["done"], {"action": r["action"], "note": "RT-03 closes this with crypto"})

    report = {
        "oracle_held": ok,
        "config": {"BLOCK_STREAK_HANDOFF": BLOCK_STREAK_HANDOFF, "source": "tools/execution_bounds.py (env SPINE_BLOCK_STREAK_HANDOFF)"},
        "scope": "LOCAL gate decision + faithful-strict board mock; LIVE board write deferred to rotated .env creds",
        "slice": {"implementer": IMPL, "verifier": VERI, "artifact_sha": _sha(ARTIFACT)},
        "scenarios": results,
    }
    print(json.dumps(report, indent=2))
    n_pass = sum(1 for r in results if r["pass"])
    print(f"\nGOVERNED PILOT: {'PASS' if ok else 'FAIL'} — {n_pass}/{len(results)} scenarios. "
          + ("The gate reaches Done ONLY on real, actor-separated, hash-true evidence AND a legal "
             "board state/actor; every forgery class blocks with no orphaned evidence; recurring reject "
             "escalates to HANDOFF at the config-sourced bound; the trusted-ledger boundary is explicit."
             if ok else "See the failing scenario(s) above."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

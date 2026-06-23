#!/usr/bin/env python3
"""
the_loop — the mechanical PM interface the autonomous SDLC loop drives through.

The intelligence (compiling a spec, implementing a slice, verifying it) is performed
by Claude Code agents; THIS module is the deterministic glue between those agents and
the live Plane board, enforcing the .kiro completion-gate discipline:

  • status                          board summary by state
  • next                            the next AGENT-actionable work item (JSON); human-gated
                                    items are surfaced with awaiting:human, never served as work
  • advance <id> <state> <role>     move an item (plane_client enforces actor + gate order + read-back)
  • prove <id> <tf> <tn> <hash>     VALIDATE a 4-field Evidence_Record, then set Done (verifier only)
  • handoff <id> <reason> <role>    route to HANDOFF (cap/budget/no-progress) — never Done
  • block  <id> <reason> <role>     route to Blocked with a reason (auditable)
  • fail   <id> <reason>            route to Failed (verifier; verification failed)

Completion-gate invariant: Done is reachable only via prove() — verifier + a VALID
Evidence_Record + a legal predecessor (In-Verification/Human-Review). cap/budget/no-progress
=> handoff (terminal, distinct from Done). State UUIDs + gate order are enforced in plane_client.
"""
import sys, json, pathlib
import importlib.util as _ilu
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import plane_client as pc
from tools.evidence_collector import validate_evidence_record

PBASE = pc.PBASE

# states an AGENT can act on (human-gated states are surfaced separately, not served as work)
ACTIONABLE_ORDER = ["Agent-Triaged", "Spec-Compiling", "Plan-Approved",
                    "Agent-Executing", "In-Verification"]
# natural next state + acting role (advisory; plane_client enforces legality)
NEXT_STEP = {
    "Backlog": ("Agent-Triaged", "initializer"),
    "Agent-Triaged": ("Spec-Compiling", "initializer"),
    "Spec-Compiling": ("Spec-Verified", "initializer"),
    "Spec-Verified": ("Plan-Approved", "human"),
    "Plan-Approved": ("Agent-Executing", "implementer"),
    "Agent-Executing": ("In-Verification", "verifier"),
    "In-Verification": ("Human-Review", "verifier"),
    "Human-Review": ("Done", "verifier"),
}


def _all_items():
    return pc._paginate(f"{PBASE}/work-items/")


def status():
    from collections import Counter
    items = _all_items()
    by = Counter(pc.id2state(i.get("state")) or "?" for i in items)
    print(f"Board: {len(items)} work items")
    for st in list(pc.states()):
        if by.get(st):
            print(f"  {st:16s} {by[st]}")
    for k, v in by.items():
        if k not in pc.states():
            print(f"  {str(k):16s} {v}")


def next_item():
    items = _all_items()
    cand = []
    for i in items:
        st = pc.id2state(i.get("state")) or "?"
        if st in ACTIONABLE_ORDER:
            cand.append((ACTIONABLE_ORDER.index(st), i))
    if not cand:
        print(json.dumps({"actionable": None})); return
    cand.sort(key=lambda x: (x[0], x[1].get("sequence_id", 0)))
    _idx, it = cand[0]
    st = pc.id2state(it.get("state"))
    nxt, role = NEXT_STEP.get(st, (None, None))
    out = {"issue_id": it["id"], "name": it.get("name"), "state": st,
           "next_state": nxt, "next_role": role}
    if role == "human":
        out["awaiting"] = "human"   # do not auto-act; a human gate
    print(json.dumps(out, indent=1))


def advance(issue_id, to_state, role):
    pc.transition(issue_id, to_state, role)  # enforces actor + gate-order + read-back
    print(json.dumps({"advanced": issue_id, "to": to_state, "by": role, "ok": True}))


def _gate(issue_id, to_state, role):
    """Authority + actor-independence + gate-order — checked BEFORE any board write,
    so a rejected actor never orphans a comment/evidence record (review MAJOR #1)."""
    pc.check_actor(role, to_state)                       # raises PermissionError if not allowed
    cur = pc.id2state(pc.get_issue(issue_id).get("state"))
    if not pc.legal_edge(cur, to_state):
        raise PermissionError(f"illegal transition {cur!r} -> {to_state!r} (gate order)")
    return cur


def prove(issue_id, test_file, test_name, output_hash):
    record = {"test_file": test_file, "test_name": test_name,
              "output_hash": output_hash,
              "collected_at": datetime.now(timezone.utc).isoformat()}
    if not validate_evidence_record(record):  # REL-03: reject empty/garbage before Done
        print(json.dumps({"error": "invalid Evidence_Record",
                          "hint": "output_hash must be sha256:<64 lowercase hex>; all fields non-empty",
                          "record": record}))
        sys.exit(2)
    _gate(issue_id, "Done", "verifier")  # authority+state BEFORE posting (no orphaned evidence)
    pc.post_evidence(issue_id, test_file, test_name, output_hash, record["collected_at"], "verifier")
    pc.transition(issue_id, "Done", "verifier")  # re-validates + read-back in plane_client
    print(json.dumps({"proven": issue_id, "evidence": record, "state": "Done"}))


def _loop_gate():
    spec = _ilu.spec_from_file_location(
        "loop_gate", pathlib.Path(__file__).resolve().parents[1] / "tools/loop_gate.py"
    )
    m = _ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def gated_prove(*, issue_id, evidence, artifact, ledger, root):
    """Gate a proven transition: only set Done when the evidence gate ACCEPTS.

    On reject -> return the self-heal/HANDOFF decision; the board is NOT moved to Done.
    On handoff -> post a HANDOFF comment and transition to HANDOFF state.
    On self_heal -> no board change; caller feeds decision['prompt'] back to the verifier.

    This is the programmatic gate for the autonomous loop (the dispatcher calls it with
    the verifier-produced evidence + dispatch ledger); the `prove` CLI command above is
    the manual path with four-field validation. Both reach Done only through the gate.
    """
    decision = _loop_gate().gated_advance(
        root=root, evidence=evidence, artifact=artifact, ledger=ledger
    )
    if decision["action"] == "advance":
        pc.post_evidence(
            issue_id, evidence["test_file"], evidence["test_name"],
            evidence["output_hash"], evidence["collected_at"], "verifier",
        )
        pc.transition(issue_id, "Done", "verifier")
    elif decision["action"] == "handoff":
        pc.comment(issue_id, f"<p><b>HANDOFF</b> — evidence gate: {decision['reason']}</p>")
        pc.transition(issue_id, "HANDOFF", "verifier")
    # self_heal -> no board change; caller feeds decision['prompt'] back to the verifier
    return decision


def handoff(issue_id, reason, role="verifier"):
    _gate(issue_id, "HANDOFF", role)             # gate BEFORE the comment write
    pc.comment(issue_id, f"HANDOFF — reason: {reason} (a human picks this up; not Done)")  # escaped
    pc.transition(issue_id, "HANDOFF", role)
    print(json.dumps({"handoff": issue_id, "reason": reason}))


def block(issue_id, reason, role="implementer"):
    _gate(issue_id, "Blocked", role)
    pc.comment(issue_id, f"BLOCKED — reason: {reason}")  # escaped
    pc.transition(issue_id, "Blocked", role)
    print(json.dumps({"blocked": issue_id, "reason": reason}))


def fail(issue_id, reason, role="verifier"):
    _gate(issue_id, "Failed", role)
    pc.comment(issue_id, f"FAILED verification — reason: {reason}")  # escaped
    pc.transition(issue_id, "Failed", role)
    print(json.dumps({"failed": issue_id, "reason": reason}))


USAGE = ("usage: the_loop.py [status | next | advance <id> <state> <role> | "
         "prove <id> <tf> <tn> <hash> | handoff <id> <reason> <role> | "
         "block <id> <reason> <role> | fail <id> <reason>]")

def _main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
    elif cmd == "next":
        next_item()
    elif cmd == "advance":
        advance(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "prove":
        prove(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "handoff":
        handoff(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "verifier")
    elif cmd == "block":
        block(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "implementer")
    elif cmd == "fail":
        fail(sys.argv[2], sys.argv[3])
    else:
        print(USAGE)


if __name__ == "__main__":
    # Emit structured JSON on a gate/transport failure instead of a raw traceback (review MAJOR #1)
    try:
        _main()
    except (PermissionError, RuntimeError, KeyError, ValueError, IndexError) as e:
        print(json.dumps({"error": type(e).__name__, "detail": str(e)}))
        sys.exit(2)

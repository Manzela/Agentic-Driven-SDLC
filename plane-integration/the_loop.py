#!/usr/bin/env python3
"""
the_loop — the mechanical PM interface the autonomous SDLC loop drives through.

The intelligence (compiling a spec, implementing a slice, verifying it) is performed
by Claude Code agents; THIS module is the deterministic glue between those agents and
the live Plane board, enforcing the .kiro completion-gate discipline:

  • `status`                      board summary by state
  • `next`                        the next actionable work item (JSON) for an agent
  • `advance <id> <state> <role>` move an item, enforcing actor authority + gate order
  • `prove <id> <tf> <tn> <hash>` attach a 4-field Evidence_Record then set Done (verifier)
  • `handoff <id> <reason> <role>`route to HANDOFF (cap/budget/no-progress) — never Done

Completion-gate invariant (mirrors evaluate_stop): an item may only reach `Done` via
`prove` (verifier + complete Evidence_Record). cap/budget/no-progress => `handoff`,
which is a terminal state distinct from Done.
"""
import sys, json, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import plane_client as pc

PBASE = pc.PBASE

# priority order of states for "what should an agent pick up next"
ACTIONABLE_ORDER = ["Agent-Triaged", "Spec-Compiling", "Spec-Verified",
                    "Plan-Approved", "Agent-Executing", "In-Verification", "Human-Review"]
# the natural next state + acting role for a simple forward advance
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

def _items():
    return pc._api("GET", f"{PBASE}/work-items/?per_page=100")

def _all_items():
    out, url = [], f"{PBASE}/work-items/?per_page=100"
    while url:
        d = pc._api("GET", url)
        rs = d.get("results", d) if isinstance(d, dict) else d
        out += rs
        nxt = d.get("next_page_results") if isinstance(d, dict) else False
        cur = d.get("next_cursor") if isinstance(d, dict) else None
        url = (f"{PBASE}/work-items/?per_page=100&cursor={cur}") if (nxt and cur) else None
    return out

# state-uuid -> name
ID2STATE = {v: k for k, v in pc.STATES.items()}

def status():
    items = _all_items()
    from collections import Counter
    by = Counter(ID2STATE.get(i.get("state"), "?") for i in items)
    print(f"Board: {len(items)} work items")
    for name, _g, _m in []:
        pass
    for st in (list(pc.STATES) or []):
        if by.get(st):
            print(f"  {st:16s} {by[st]}")
    leftover = {k: v for k, v in by.items() if k not in pc.STATES}
    for k, v in leftover.items():
        print(f"  {k:16s} {v}")

def next_item():
    items = _all_items()
    cand = []
    for i in items:
        st = ID2STATE.get(i.get("state"), "?")
        if st in ACTIONABLE_ORDER:
            cand.append((ACTIONABLE_ORDER.index(st), i))
    if not cand:
        print(json.dumps({"actionable": None})); return
    cand.sort(key=lambda x: (x[0], x[1].get("sequence_id", 0)))
    st_idx, it = cand[0]
    st = ID2STATE.get(it.get("state"))
    nxt, role = NEXT_STEP.get(st, (None, None))
    print(json.dumps({"issue_id": it["id"], "name": it.get("name"), "state": st,
                      "next_state": nxt, "next_role": role}, indent=1))

def advance(issue_id, to_state, role):
    r = pc.transition(issue_id, to_state, role)
    print(json.dumps({"advanced": issue_id, "to": to_state, "by": role, "ok": True}))

def prove(issue_id, test_file, test_name, output_hash):
    collected = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    pc.post_evidence(issue_id, test_file, test_name, output_hash, collected, "verifier")
    pc.transition(issue_id, "Done", "verifier")
    print(json.dumps({"proven": issue_id, "evidence": {"test_file": test_file,
          "test_name": test_name, "output_hash": output_hash, "collected_at": collected}, "state": "Done"}))

def handoff(issue_id, reason, role="verifier"):
    pc.comment(issue_id, f"<p><b>HANDOFF</b> — reason: {reason} (a human picks this up; not Done)</p>")
    pc.transition(issue_id, "HANDOFF", role)
    print(json.dumps({"handoff": issue_id, "reason": reason}))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status": status()
    elif cmd == "next": next_item()
    elif cmd == "advance": advance(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "prove": prove(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "handoff": handoff(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "verifier")
    else: print("usage: the_loop.py [status|next|advance <id> <state> <role>|prove <id> <tf> <tn> <hash>|handoff <id> <reason> <role>]")

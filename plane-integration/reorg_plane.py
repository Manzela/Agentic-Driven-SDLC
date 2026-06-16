#!/usr/bin/env python3
"""
Reorganize the live ASCP Plane board to Tier-1 grade, from the research-synthesized
plan (audit/plane-reorg/reorg-plan.json):

  • 8 Modules  = the 8 epics E1-E8 (the WHAT / feature axis) — each epic's stories+tasks
  • 7 Cycles   = the platform phases 0-6 (the WHEN / sprint axis), one active at a time
                 (an item can be in only one cycle; assigned by a deterministic epic→phase map)

Idempotent: dedups cycles/modules by name; records ids in .reorg_state.json. Uses the
public REST API (cycles + modules + bulk issue assignment). Views + the onboarding Page
are provisioned separately via the Django ORM (not in the public API).
"""
import sys, json, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import plane_client as pc

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
PROV = json.loads((HERE / ".provision_state.json").read_text())
BACKLOG = json.loads((ROOT / "docs/plane/plane_backlog.json").read_text())
STATE_F = HERE / ".reorg_state.json"
ST = json.loads(STATE_F.read_text()) if STATE_F.exists() else {"cycles": {}, "modules": {}}
def save(): STATE_F.write_text(json.dumps(ST, indent=1))

ISSUES = PROV["issues"]           # logical key -> plane issue uuid
def epic_subtree(eid):
    """All plane issue ids under epic eid: the epic + its stories + their tasks."""
    ids = []
    ek = f"epic:{eid}"
    if ek in ISSUES: ids.append(ISSUES[ek])
    for s in BACKLOG["stories"]:
        if s.get("epic_id") != eid: continue
        sk = f"story:{s['key']}"
        if sk in ISSUES: ids.append(ISSUES[sk])
        for i, _t in enumerate(s.get("tasks", [])):
            tk = f"task:{s['key']}#{i}"
            if tk in ISSUES: ids.append(ISSUES[tk])
    return ids

# ---- the 8 epics (modules) ----
EPICS = [
    ("E1", "Core Plane Infrastructure & Self-Hosting"),
    ("E2", "Agentic Workspace & Governance Model"),
    ("E3", "Intent→Spec Compilation & Coverage Model"),
    ("E4", "Verification Engine & Evidence"),
    ("E5", "Completion & Quality-Gate Automation"),
    ("E6", "Agent Integration Layer — Plane ⇄ Agent"),
    ("E7", "Observability, Audit & Traceability"),
    ("E8", "Orchestration, Anti-Loopmaxxing & HITL"),
]
# ---- the 7 phase-cycles (sequential, non-overlapping; exactly one 'current') ----
CYCLES = [
    ("Phase 0 — Spine", "2026-06-16", "2026-06-29"),
    ("Phase 1 — Verification Depth", "2026-06-30", "2026-07-13"),
    ("Phase 2 — Durable State & Security", "2026-07-14", "2026-07-27"),
    ("Phase 3 — Observability & Proof", "2026-07-28", "2026-08-10"),
    ("Phase 4 — Property-Based Test Suite", "2026-08-11", "2026-08-24"),
    ("Phase 5 — Durable Orchestration (optional)", "2026-08-25", "2026-09-07"),
    ("Phase 6 — Predictive Routing (optional)", "2026-09-08", "2026-09-21"),
]
# deterministic epic -> phase-cycle index (the WHEN each epic's work primarily lands)
EPIC_PHASE = {"E1": 0, "E2": 0, "E3": 1, "E4": 1, "E5": 2, "E6": 2, "E7": 3, "E8": 5}

def _api(method, path, body=None):
    return pc._api(method, path, body)

def ensure_modules():
    existing = {m["name"]: m["id"] for m in (_api("GET", f"{pc.PBASE}/modules/").get("results", []) if isinstance(_api("GET", f"{pc.PBASE}/modules/"), dict) else _api("GET", f"{pc.PBASE}/modules/"))}
    for eid, title in EPICS:
        name = f"{eid} — {title}"
        mid = ST["modules"].get(eid) or existing.get(name)
        if not mid:
            r = _api("POST", f"{pc.PBASE}/modules/", {"name": name, "project_id": pc.PROJ,
                     "description": f"Epic {eid}: {title}", "external_id": f"module:{eid}", "external_source": "ascp-blueprint"})
            mid = r["id"]; print(f"  module + {name}")
        ST["modules"][eid] = mid; save()
        ids = epic_subtree(eid)
        if ids:
            _api("POST", f"{pc.PBASE}/modules/{mid}/module-issues/", {"issues": ids})
            print(f"    assigned {len(ids)} items to {eid}")

def ensure_cycles():
    listing = _api("GET", f"{pc.PBASE}/cycles/")
    existing = {c["name"]: c["id"] for c in (listing.get("results", []) if isinstance(listing, dict) else listing)}
    cyc_ids = []
    for name, start, end in CYCLES:
        cid = ST["cycles"].get(name) or existing.get(name)
        if not cid:
            r = _api("POST", f"{pc.PBASE}/cycles/", {"name": name, "project_id": pc.PROJ,
                     "start_date": f"{start}T00:00:00Z", "end_date": f"{end}T00:00:00Z",
                     "external_id": f"cycle:{name[:7]}", "external_source": "ascp-kiro"})
            cid = r["id"]; print(f"  cycle + {name}")
        ST["cycles"][name] = cid; save(); cyc_ids.append(cid)
    # assign each epic's subtree to its phase-cycle
    for eid, _t in EPICS:
        ph = EPIC_PHASE[eid]; cid = cyc_ids[ph]
        ids = epic_subtree(eid)
        if ids:
            _api("POST", f"{pc.PBASE}/cycles/{cid}/cycle-issues/", {"issues": ids})
            print(f"    {eid} ({len(ids)} items) -> {CYCLES[ph][0]}")

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"Reorg ASCP board ({pc.WS}/{pc.PROJ})")
    if only in ("all", "modules"): print("[modules]"); ensure_modules()
    if only in ("all", "cycles"): print("[cycles]"); ensure_cycles()
    print("DONE. modules:", len(ST["modules"]), "cycles:", len(ST["cycles"]))

if __name__ == "__main__":
    main()

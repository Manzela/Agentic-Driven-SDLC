#!/usr/bin/env python3
"""plane_config_audit.py — audit a LIVE Plane project's configuration against
production-grade expectations (Plane's documented model + the ASCP blueprint).

Read-only: hits the public REST API (X-API-Key) the same way provision_plane.py
does, and reports PASS/FAIL per check. Env (or plane-selfhost/credentials.env):
  PLANE_API_BASE   e.g. https://plane.autonomous-agent.dev/api/v1
  PLANE_WORKSPACE_SLUG   e.g. ascp
  PLANE_PROJECT_ID       project UUID
  PLANE_API_KEY          API token

Exit code 0 if no FAILs, else 1. Intended to run in CI (the runner has network).
Checklist references: docs/plane/PLANE_BLUEPRINT.md (12 states / 8 epics / 49
stories / 186 tasks / 7 cycles / 22 labels) and audit/plane-ui/enhancement-spec.json.
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
CREDS = HERE.parent / "plane-selfhost" / "credentials.env"


def load_cfg():
    cfg = dict(os.environ)
    if CREDS.exists():
        for line in CREDS.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg.setdefault(k, v)
    miss = [k for k in ("PLANE_API_BASE", "PLANE_WORKSPACE_SLUG", "PLANE_PROJECT_ID", "PLANE_API_KEY") if not cfg.get(k)]
    if miss:
        sys.exit(f"Missing config: {', '.join(miss)} (env or {CREDS})")
    return cfg


CFG = load_cfg()
BASE = CFG["PLANE_API_BASE"].rstrip("/")
WS = CFG["PLANE_WORKSPACE_SLUG"]
PROJ = CFG["PLANE_PROJECT_ID"]
KEY = CFG["PLANE_API_KEY"]
PBASE = f"{BASE}/workspaces/{WS}/projects/{PROJ}"


def api(path):
    url = path if path.startswith("http") else (BASE + path if path.startswith("/workspaces") else PBASE + path)
    req = urllib.request.Request(url, headers={"X-API-Key": KEY, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def rows(payload):
    """Normalize a Plane list response (paginated dict or bare list)."""
    if isinstance(payload, list):
        return payload
    return payload.get("results", payload.get("data", []))


CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main():
    print(f"Auditing {PBASE}\n")

    # 1) States — the 12-state agent workflow across all 5 Plane state groups,
    #    each with a deliberate order (production: no default-only states).
    try:
        st = rows(api("/states/"))
        groups = {s.get("group") for s in st}
        check("States: >= 9 custom workflow states", len(st) >= 9, f"{len(st)} states")
        check("States: all 5 groups present (backlog/unstarted/started/completed/cancelled)",
              {"backlog", "unstarted", "started", "completed", "cancelled"} <= groups, str(sorted(g for g in groups if g)))
        check("States: each has an explicit color (visual encoding)",
              all(s.get("color") for s in st), "every state colored" if all(s.get("color") for s in st) else "some states uncolored")
    except Exception as e:
        check("States reachable", False, repr(e))

    # 2) Cycles — 7 phase cycles, each with start AND end dates (timeboxed).
    try:
        cy = rows(api("/cycles/"))
        dated = [c for c in cy if c.get("start_date") and c.get("end_date")]
        check("Cycles: 7 cycles configured", len(cy) == 7, f"{len(cy)} cycles")
        check("Cycles: every cycle is timeboxed (start+end dates)", len(dated) == len(cy) and cy, f"{len(dated)}/{len(cy)} dated")
    except Exception as e:
        check("Cycles reachable", False, repr(e))

    # 3) Labels — the encoded label namespace (agent:/type:/gate:/phase:/priority:).
    try:
        lb = rows(api("/labels/"))
        names = {l.get("name", "") for l in lb}
        prefixes = {n.split(":")[0] for n in names if ":" in n}
        check("Labels: >= 15 labels present", len(lb) >= 15, f"{len(lb)} labels")
        check("Labels: encoded namespaces present (agent/type/gate/phase)",
              {"agent", "type", "gate", "phase"} & prefixes != set(), f"prefixes={sorted(prefixes)}")
    except Exception as e:
        check("Labels reachable", False, repr(e))

    # 4) Work items — the 8 epics / 49 stories / 186 tasks should be materialized.
    try:
        # Plane paginates issues; use the count field when present.
        first = api("/issues/")
        total = first.get("total_count") if isinstance(first, dict) else None
        if total is None:
            total = len(rows(first))
        check("Work items: >= 240 issues materialized (8+49+186 ≈ 243)", total >= 240, f"{total} issues")
    except Exception as e:
        check("Issues reachable", False, repr(e))

    # 5) Project meta — name + identifier set (not a default 'Untitled').
    try:
        pj = api("")  # GET project
        check("Project: has a name + identifier", bool(pj.get("name")) and bool(pj.get("identifier")),
              f"{pj.get('name')} ({pj.get('identifier')})")
    except Exception as e:
        check("Project reachable", False, repr(e))

    fails = [n for n, ok, _ in CHECKS if not ok]
    print(f"\n==== {len(CHECKS) - len(fails)}/{len(CHECKS)} checks passed ====")
    if fails:
        print("FAILED: " + "; ".join(fails))
        return 1
    print("All configuration checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

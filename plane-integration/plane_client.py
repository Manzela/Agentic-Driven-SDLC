#!/usr/bin/env python3
"""
plane_client — the agent→Plane write-back side of the bidirectional contract.

Agents (initializer / implementer / verifier) use this to move work items through
the 12-state agent workflow and to attach Evidence_Records as comments, exactly as
the .kiro completion-gate model prescribes (only the verifier may set Done;
cap/budget/no-progress route to HANDOFF, never Done). Pure stdlib; X-API-Key auth.
"""
import os, json, time, pathlib, urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
CREDS = HERE.parent / "plane-selfhost" / "credentials.env"
STATE_FILE = HERE / ".provision_state.json"

def _load_env(p):
    e = {}
    for ln in pathlib.Path(p).read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1); e[k] = v
    return e

CFG = _load_env(CREDS)
API_BASE = CFG["PLANE_API_BASE"].rstrip("/")
WS = CFG["PLANE_WORKSPACE_SLUG"]
PROJ = CFG["PLANE_PROJECT_ID"]
KEY = CFG["PLANE_API_KEY"]
PBASE = f"/workspaces/{WS}/projects/{PROJ}"

# state-name -> uuid map written by the provisioner
_PROV = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"states": {}, "issues": {}}
STATES = _PROV.get("states", {})

# which agent_role is permitted to write which state (mirrors the .kiro actor model)
TRANSITION_AUTH = {
    "Agent-Triaged": {"initializer", "human"},
    "Spec-Compiling": {"initializer"},
    "Spec-Verified": {"initializer"},
    "Plan-Approved": {"human"},                 # human-only gate
    "Agent-Executing": {"implementer"},
    "In-Verification": {"verifier"},
    "Human-Review": {"verifier", "human"},
    "Done": {"verifier"},                        # only the verifier proves Done
    "HANDOFF": {"initializer", "implementer", "verifier"},  # any loop on cap/budget/no-progress
    "Blocked": {"initializer", "implementer", "verifier"},
    "Failed": {"verifier"},
}

_last = [0.0]
def _api(method, path, body=None, retries=8):
    now = time.time()
    if now - _last[0] < 1.1: time.sleep(1.1 - (now - _last[0]))
    _last[0] = time.time()
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(f"{API_BASE}{path}", data=data, method=method,
              headers={"X-API-Key": KEY, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read(); return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(62); continue
            if 500 <= e.code < 600: time.sleep(min(2 ** attempt, 30)); continue
            raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:300]}")
    raise RuntimeError(f"{method} {path}: exhausted retries")

def transition(issue_id, to_state, actor_role):
    """Move an issue to a new agent-workflow state, enforcing the actor authority model."""
    allowed = TRANSITION_AUTH.get(to_state, set())
    if actor_role not in allowed:
        raise PermissionError(f"{actor_role} may not set state '{to_state}' (allowed: {sorted(allowed)})")
    suid = STATES.get(to_state)
    if not suid:
        raise KeyError(f"unknown state '{to_state}' (run provision_plane.py first)")
    return _api("PATCH", f"{PBASE}/work-items/{issue_id}/", {"state": suid})

def post_evidence(issue_id, test_file, test_name, output_hash, collected_at, actor_role="verifier"):
    """Attach an Evidence_Record (4-field) as a work-item comment — the proof trail."""
    html = ("<p><b>Evidence_Record</b> (actor: %s)</p><ul>"
            "<li><code>test_file</code>: %s</li><li><code>test_name</code>: %s</li>"
            "<li><code>output_hash</code>: %s</li><li><code>collected_at</code>: %s</li></ul>"
            % (actor_role, test_file, test_name, output_hash, collected_at))
    return _api("POST", f"{PBASE}/work-items/{issue_id}/comments/", {"comment_html": html})

def comment(issue_id, html):
    return _api("POST", f"{PBASE}/work-items/{issue_id}/comments/", {"comment_html": html})

def get_issue(issue_id):
    return _api("GET", f"{PBASE}/work-items/{issue_id}/")

if __name__ == "__main__":
    import sys
    print(json.dumps({"states": list(STATES), "issues": len(_PROV.get("issues", {}))}, indent=1))

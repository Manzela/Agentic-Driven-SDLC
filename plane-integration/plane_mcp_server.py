#!/usr/bin/env python3
"""
plane_mcp_server — a Model Context Protocol (MCP) stdio server that lets Claude Code (and
any MCP client) read AND write the live Plane board directly, both ways: list/get/create/
update work-items, drive the 12-state agent workflow with the actor-authority model
enforced, attach Evidence_Records, manage cycles/modules, and (escape hatch) call any
Plane REST endpoint for settings, etc.

This is the *agent -> board* half of the E6 bidirectional contract, exposed as tools the
model can invoke. (The *board -> agent* half — a webhook receiver that dispatches issues to
agents — is a separate daemon; see plane-integration/webhook_handler.py and the dispatcher.)

Design / security:
  • Pure stdlib. Speaks JSON-RPC 2.0 over newline-delimited stdin/stdout (MCP stdio
    transport). All diagnostics go to STDERR — STDOUT is the protocol channel only.
  • The API token is NEVER hardcoded and NEVER printed. It is loaded lazily from env
    (PLANE_API_KEY) or from a gitignored creds file (PLANE_CREDS_FILE, default
    ../plane-selfhost/credentials.env). plane_context redacts it.
  • Writes are real and immediate. plane_transition enforces TRANSITION_AUTH (only the
    verifier may set Done; cap/budget/no-progress route to HANDOFF) so the MCP surface
    cannot bypass the .kiro completion-gate actor model.
  • Rate-limited (>=1.1s between calls) with retry/backoff on 429/5xx, mirroring
    plane_client.py.

Run:  PLANE_CREDS_FILE=/abs/credentials.env python3 plane_mcp_server.py
Wire into Claude Code via .mcp.json (see plane-integration/README-mcp.md).
"""
import sys, os, json, time, pathlib, urllib.request, urllib.error

SERVER_NAME = "plane-ascp"
SERVER_VERSION = "1.0.0"
DEFAULT_PROTOCOL = "2024-11-05"   # echoed back to client unless it requests another

HERE = pathlib.Path(__file__).resolve().parent


def log(*a):
    """Diagnostics -> STDERR only (STDOUT is the JSON-RPC channel)."""
    print(*a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- credentials (lazy)
_CFG = None


def _load_env_file(p):
    e = {}
    for ln in pathlib.Path(p).read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            e[k] = v
    return e


def cfg():
    """Lazily resolve Plane connection config. Env overrides file; never raises at import."""
    global _CFG
    if _CFG is not None:
        return _CFG
    fromfile = {}
    creds_path = os.environ.get("PLANE_CREDS_FILE") or str(HERE.parent / "plane-selfhost" / "credentials.env")
    try:
        fromfile = _load_env_file(creds_path)
    except FileNotFoundError:
        log(f"[plane-mcp] no creds file at {creds_path}; relying on env vars")
    g = lambda k: os.environ.get(k) or fromfile.get(k)
    _CFG = {
        "api_base": (g("PLANE_API_BASE") or "http://localhost:8090/api/v1").rstrip("/"),
        "ws": g("PLANE_WORKSPACE_SLUG") or "ascp",
        "proj": g("PLANE_PROJECT_ID"),
        "key": g("PLANE_API_KEY"),
        "creds_path": creds_path,
    }
    if not _CFG["key"] or not _CFG["proj"]:
        log("[plane-mcp] WARNING: PLANE_API_KEY / PLANE_PROJECT_ID unresolved — calls will fail until set")
    return _CFG


def pbase():
    c = cfg()
    return f"/workspaces/{c['ws']}/projects/{c['proj']}"


# ---------------------------------------------------------------- REST (rate-limited)
_last = [0.0]


def api(method, path, body=None, retries=6):
    c = cfg()
    now = time.time()
    if now - _last[0] < 1.1:
        time.sleep(1.1 - (now - _last[0]))
    _last[0] = time.time()
    data = json.dumps(body).encode() if body is not None else None
    url = f"{c['api_base']}{path}"
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"X-API-Key": c["key"] or "", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else {"ok": True, "status": r.status}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(62)
                continue
            if 500 <= e.code < 600:
                time.sleep(min(2 ** attempt, 30))
                last_err = f"{e.code}: {e.read().decode()[:300]}"
                continue
            raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:400]}")
        except urllib.error.URLError as e:
            last_err = str(e)
            time.sleep(min(2 ** attempt, 10))
            continue
    raise RuntimeError(f"{method} {path}: exhausted retries ({last_err})")


def _results(obj):
    """Plane list endpoints sometimes wrap in {results:[...]}, sometimes return a bare list."""
    if isinstance(obj, dict) and "results" in obj:
        return obj["results"]
    return obj


_states_cache = [None]


def states_map():
    """name -> uuid for this project's 12 workflow states (cached)."""
    if _states_cache[0] is None:
        rows = _results(api("GET", f"{pbase()}/states/"))
        _states_cache[0] = {s["name"]: s["id"] for s in rows}
    return _states_cache[0]


def resolve_state(name_or_id):
    if not name_or_id:
        return None
    m = states_map()
    if name_or_id in m:
        return m[name_or_id]
    # assume it's already a uuid
    return name_or_id


# the .kiro actor-authority model (mirrors plane_client.TRANSITION_AUTH). The MCP surface
# MUST NOT let a caller bypass it: only the verifier proves Done; loops route to HANDOFF.
TRANSITION_AUTH = {
    "Agent-Triaged": {"initializer", "human"},
    "Spec-Compiling": {"initializer"},
    "Spec-Verified": {"initializer"},
    "Plan-Approved": {"human"},
    "Agent-Executing": {"implementer"},
    "In-Verification": {"verifier"},
    "Human-Review": {"verifier", "human"},
    "Done": {"verifier"},
    "HANDOFF": {"initializer", "implementer", "verifier"},
    "Blocked": {"initializer", "implementer", "verifier"},
    "Failed": {"verifier"},
}


# ---------------------------------------------------------------- tool implementations
def t_context(_):
    c = cfg()
    key = c.get("key") or ""
    return {
        "api_base": c["api_base"], "workspace": c["ws"], "project_id": c["proj"],
        "token": (key[:10] + "…redacted") if key else None,
        "creds_file": c["creds_path"],
        "states": list(states_map().keys()),
        "note": "agent->board MCP surface; writes are real. Transition authority enforced.",
    }


def t_list_states(_):
    return _results(api("GET", f"{pbase()}/states/"))


def t_list_issues(a):
    q = []
    if a.get("limit"):
        q.append(f"per_page={int(a['limit'])}")
    if a.get("cursor"):
        q.append(f"cursor={a['cursor']}")
    qs = ("?" + "&".join(q)) if q else ""
    rows = _results(api("GET", f"{pbase()}/work-items/{qs}"))
    want_state = a.get("state")
    search = (a.get("search") or "").lower()
    out = []
    sid = resolve_state(want_state) if want_state else None
    for it in rows:
        if sid and it.get("state") != sid:
            continue
        if search and search not in (it.get("name", "").lower()):
            continue
        out.append({"id": it.get("id"), "name": it.get("name"),
                    "state": it.get("state"), "priority": it.get("priority"),
                    "sequence_id": it.get("sequence_id")})
    return {"count": len(out), "items": out[: int(a.get("limit", 50))]}


def t_get_issue(a):
    return api("GET", f"{pbase()}/work-items/{a['issue_id']}/")


def t_create_issue(a):
    body = {"name": a["name"]}
    if a.get("description_html"):
        body["description_html"] = a["description_html"]
    if a.get("priority"):
        body["priority"] = a["priority"]
    if a.get("state"):
        body["state"] = resolve_state(a["state"])
    if a.get("assignee_ids"):
        body["assignees"] = a["assignee_ids"]
    return api("POST", f"{pbase()}/work-items/", body)


def t_update_issue(a):
    body = {}
    for k in ("name", "description_html", "priority"):
        if a.get(k) is not None:
            body[k] = a[k]
    if a.get("state"):
        body["state"] = resolve_state(a["state"])
    if not body:
        raise ValueError("no updatable fields provided")
    return api("PATCH", f"{pbase()}/work-items/{a['issue_id']}/", body)


def t_transition(a):
    to_state, role = a["to_state"], a["actor_role"]
    allowed = TRANSITION_AUTH.get(to_state)
    if allowed is None:
        raise ValueError(f"unknown target state '{to_state}'")
    if role not in allowed:
        raise PermissionError(f"actor '{role}' may not set '{to_state}' (allowed: {sorted(allowed)})")
    sid = resolve_state(to_state)
    if not sid:
        raise KeyError(f"state '{to_state}' not found on project")
    return api("PATCH", f"{pbase()}/work-items/{a['issue_id']}/", {"state": sid})


def t_add_comment(a):
    return api("POST", f"{pbase()}/work-items/{a['issue_id']}/comments/",
               {"comment_html": a["comment_html"]})


def t_post_evidence(a):
    role = a.get("actor_role", "verifier")
    html = ("<p><b>Evidence_Record</b> (actor: %s)</p><ul>"
            "<li><code>test_file</code>: %s</li><li><code>test_name</code>: %s</li>"
            "<li><code>output_hash</code>: %s</li><li><code>collected_at</code>: %s</li></ul>"
            % (role, a["test_file"], a["test_name"], a["output_hash"], a["collected_at"]))
    return api("POST", f"{pbase()}/work-items/{a['issue_id']}/comments/", {"comment_html": html})


def t_list_cycles(_):
    return _results(api("GET", f"{pbase()}/cycles/"))


def t_list_modules(_):
    return _results(api("GET", f"{pbase()}/modules/"))


def t_assign_cycle(a):
    return api("POST", f"{pbase()}/cycles/{a['cycle_id']}/cycle-issues/", {"issues": a["issue_ids"]})


def t_assign_module(a):
    return api("POST", f"{pbase()}/modules/{a['module_id']}/module-issues/", {"issues": a["issue_ids"]})


def t_request(a):
    """Escape hatch for full read/write coverage (settings, members, etc.). `path` is
    relative to the API base. Use {project} / {workspace} placeholders for convenience."""
    c = cfg()
    path = a["path"].replace("{project}", c["proj"] or "").replace("{workspace}", c["ws"])
    if not path.startswith("/"):
        path = "/" + path
    return api(a["method"].upper(), path, a.get("body"))


# name -> (handler, json-schema, description, is_write)
TOOLS = {
    "plane_context": (t_context, {"type": "object", "properties": {}},
                      "Show the connected workspace/project, redacted token, and the 12 state names.", False),
    "plane_list_states": (t_list_states, {"type": "object", "properties": {}},
                          "List the project's workflow states (name + id).", False),
    "plane_list_issues": (t_list_issues, {"type": "object", "properties": {
        "state": {"type": "string", "description": "filter by state name or id"},
        "search": {"type": "string", "description": "case-insensitive substring of the title"},
        "limit": {"type": "integer", "default": 50},
        "cursor": {"type": "string", "description": "pagination cursor"}}},
        "List work-items (optionally filtered by state/search).", False),
    "plane_get_issue": (t_get_issue, {"type": "object", "required": ["issue_id"], "properties": {
        "issue_id": {"type": "string"}}}, "Get one work-item by id.", False),
    "plane_create_issue": (t_create_issue, {"type": "object", "required": ["name"], "properties": {
        "name": {"type": "string"},
        "description_html": {"type": "string"},
        "priority": {"type": "string", "enum": ["urgent", "high", "medium", "low", "none"]},
        "state": {"type": "string", "description": "state name or id"},
        "assignee_ids": {"type": "array", "items": {"type": "string"}}}},
        "Create a new work-item.", True),
    "plane_update_issue": (t_update_issue, {"type": "object", "required": ["issue_id"], "properties": {
        "issue_id": {"type": "string"},
        "name": {"type": "string"},
        "description_html": {"type": "string"},
        "priority": {"type": "string", "enum": ["urgent", "high", "medium", "low", "none"]},
        "state": {"type": "string", "description": "state name or id"}}},
        "Update fields on a work-item (name/description/priority/state).", True),
    "plane_transition": (t_transition, {"type": "object", "required": ["issue_id", "to_state", "actor_role"],
        "properties": {
            "issue_id": {"type": "string"},
            "to_state": {"type": "string", "description": "target state name"},
            "actor_role": {"type": "string", "enum": ["initializer", "implementer", "verifier", "human"]}}},
        "Move a work-item through the 12-state agent workflow. ENFORCES actor authority "
        "(only verifier->Done; loops->HANDOFF).", True),
    "plane_add_comment": (t_add_comment, {"type": "object", "required": ["issue_id", "comment_html"],
        "properties": {"issue_id": {"type": "string"}, "comment_html": {"type": "string"}}},
        "Add an HTML comment to a work-item.", True),
    "plane_post_evidence": (t_post_evidence, {"type": "object",
        "required": ["issue_id", "test_file", "test_name", "output_hash", "collected_at"], "properties": {
            "issue_id": {"type": "string"}, "test_file": {"type": "string"},
            "test_name": {"type": "string"}, "output_hash": {"type": "string"},
            "collected_at": {"type": "string"}, "actor_role": {"type": "string", "default": "verifier"}}},
        "Attach a 4-field Evidence_Record (the proof trail) as a comment.", True),
    "plane_list_cycles": (t_list_cycles, {"type": "object", "properties": {}},
                          "List cycles (sprints/phases).", False),
    "plane_list_modules": (t_list_modules, {"type": "object", "properties": {}},
                           "List modules (epics/feature groups).", False),
    "plane_assign_cycle": (t_assign_cycle, {"type": "object", "required": ["cycle_id", "issue_ids"],
        "properties": {"cycle_id": {"type": "string"},
                       "issue_ids": {"type": "array", "items": {"type": "string"}}}},
        "Assign work-items to a cycle.", True),
    "plane_assign_module": (t_assign_module, {"type": "object", "required": ["module_id", "issue_ids"],
        "properties": {"module_id": {"type": "string"},
                       "issue_ids": {"type": "array", "items": {"type": "string"}}}},
        "Assign work-items to a module.", True),
    "plane_request": (t_request, {"type": "object", "required": ["method", "path"], "properties": {
        "method": {"type": "string", "enum": ["GET", "POST", "PATCH", "PUT", "DELETE"]},
        "path": {"type": "string", "description": "API path relative to base, e.g. "
                 "'/workspaces/{workspace}/projects/{project}/members/'. Supports {project}/{workspace}."},
        "body": {"type": "object"}}},
        "Escape hatch: call ANY Plane REST endpoint (settings, members, views, pages). "
        "Full read/write coverage. Use deliberately.", True),
}


# ---------------------------------------------------------------- JSON-RPC plumbing
def reply(mid, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": mid}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle(msg):
    method = msg.get("method")
    mid = msg.get("id")
    is_request = "id" in msg

    if method == "initialize":
        proto = (msg.get("params") or {}).get("protocolVersion") or DEFAULT_PROTOCOL
        return reply(mid, {
            "protocolVersion": proto,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })

    if method in ("notifications/initialized", "initialized"):
        return  # notification, no reply

    if method == "ping":
        return reply(mid, {})

    if method == "tools/list":
        tools = [{"name": n, "description": d, "inputSchema": s}
                 for n, (_h, s, d, _w) in TOOLS.items()]
        return reply(mid, {"tools": tools})

    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        entry = TOOLS.get(name)
        if not entry:
            return reply(mid, error={"code": -32602, "message": f"unknown tool '{name}'"})
        handler = entry[0]
        try:
            out = handler(args)
            text = json.dumps(out, indent=2, default=str)
            return reply(mid, {"content": [{"type": "text", "text": text}]})
        except Exception as e:  # surface as a tool error, not a protocol error
            log(f"[plane-mcp] tool '{name}' failed: {e}")
            return reply(mid, {"content": [{"type": "text", "text": f"ERROR: {type(e).__name__}: {e}"}],
                               "isError": True})

    if is_request:
        return reply(mid, error={"code": -32601, "message": f"method not found: {method}"})
    # else: unknown notification — ignore


def main():
    log(f"[plane-mcp] {SERVER_NAME} v{SERVER_VERSION} ready on stdio "
        f"(workspace={cfg()['ws']}, project={cfg()['proj']})")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            log(f"[plane-mcp] bad JSON: {e}")
            continue
        try:
            handle(msg)
        except Exception as e:
            log(f"[plane-mcp] handler crash: {e}")
            if "id" in msg:
                reply(msg["id"], error={"code": -32603, "message": f"internal error: {e}"})


if __name__ == "__main__":
    main()

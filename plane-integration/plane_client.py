#!/usr/bin/env python3
"""
plane_client — the agent→Plane write-back side of the bidirectional contract.

Agents (initializer / implementer / verifier) move work items through the 12-state
agent workflow and attach Evidence_Records, per the .kiro completion-gate model
(only the verifier may set Done; cap/budget/no-progress route to HANDOFF, never Done).

Hardened per the plane-integration audit:
  * Board config is ENV-driven (one board, any board): os.environ > plane-integration/.env >
    plane-selfhost/credentials.env (local-dev fallback), reconciling the PLANE_WS|PLANE_WORKSPACE_SLUG
    / PLANE_PROJ|PLANE_PROJECT_ID alias drift. [CFG-01/REL-04/REL-09]
  * _api sends a browser User-Agent + conditional CF-Access headers (remote board behind Cloudflare),
    honors Retry-After, keeps 429 off the bounded retry budget, retries transient URLError. [CFG-03/REL-07/COR-07]
  * State UUIDs are resolved LIVE from the targeted board (GET /states/), not a stale local file, so a
    cross-board misconfig fails loud. [CFG-02/COR-01]
  * transition() enforces actor authority AND gate ORDER (legal-edge check), and gates privileged roles
    (verifier/human) behind a role secret the implementer agent does not possess. [REL-02/SEC-03]
  * Evidence/comment HTML is escaped (no stored XSS against the human reviewer). [SEC-02]
"""
import os, json, time, random, pathlib, html, urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
CREDS = HERE.parent / "plane-selfhost" / "credentials.env"
DOTENV = HERE / ".env"


def _load_env_file(p):
    e = {}
    try:
        for ln in pathlib.Path(p).read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                e[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return e


_DOTENV = _load_env_file(DOTENV)
_CREDS = _load_env_file(CREDS)


def cfg(*names, required=True, default=None):
    """Resolve config: os.environ (any alias) > .env > credentials.env > default."""
    for src in (os.environ, _DOTENV, _CREDS):
        for n in names:
            if src.get(n):
                return src[n]
    if required and default is None:
        raise SystemExit(f"plane_client: missing required config {names[0]} "
                         f"(set it in env or plane-integration/.env — see REMOTE_ACCESS.md)")
    return default


API_BASE = cfg("PLANE_API_BASE").rstrip("/")
WS = cfg("PLANE_WS", "PLANE_WORKSPACE_SLUG")
PROJ = cfg("PLANE_PROJ", "PLANE_PROJECT_ID")
KEY = cfg("PLANE_API_KEY")
CF_ID = cfg("CF_ACCESS_CLIENT_ID", required=False, default="")
CF_SECRET = cfg("CF_ACCESS_CLIENT_SECRET", required=False, default="")
PBASE = f"/workspaces/{WS}/projects/{PROJ}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ascp-automation"

# ── State machine (the canonical 12-state model) ─────────────────────────────
FORWARD = {
    "Backlog": "Agent-Triaged", "Agent-Triaged": "Spec-Compiling",
    "Spec-Compiling": "Spec-Verified", "Spec-Verified": "Plan-Approved",
    "Plan-Approved": "Agent-Executing", "Agent-Executing": "In-Verification",
    "In-Verification": "Human-Review", "Human-Review": "Done",
}
UNIVERSAL = {"Blocked", "Failed", "HANDOFF"}     # reachable from any active state
TERMINAL = {"Done", "HANDOFF", "Failed"}          # no outbound edges
RECOVERY = {"Blocked": "Agent-Executing", "Failed": "Agent-Executing"}  # retry path
EXTRA_EDGES = {("In-Verification", "Done")}       # verifier may prove Done from In-Verification

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
PRIVILEGED = {"verifier", "human"}                # roles that require an out-of-band secret
ROLE_SECRET_ENV = {"verifier": "ASCP_VERIFIER_SECRET", "human": "ASCP_HUMAN_SECRET"}


# ── Pure logic (unit-testable, no I/O) ───────────────────────────────────────
def legal_edge(cur, to):
    """True iff cur -> to is a permitted transition in the gate graph."""
    if cur == to:
        return False
    if to in UNIVERSAL:
        return cur not in TERMINAL
    if cur in TERMINAL:
        return False
    if cur in RECOVERY and to == RECOVERY[cur]:
        return True
    if (cur, to) in EXTRA_EDGES:
        return True
    return FORWARD.get(cur) == to


def check_actor(role, to_state, env=None):
    """Authority + actor-independence. Raises PermissionError if not permitted.
    Privileged roles (verifier/human) must present a role secret in env — the
    implementer agent's environment must NOT contain it."""
    env = os.environ if env is None else env
    allowed = TRANSITION_AUTH.get(to_state, set())
    if role not in allowed:
        raise PermissionError(f"{role} may not set state '{to_state}' (allowed: {sorted(allowed)})")
    if role in PRIVILEGED and not env.get(ROLE_SECRET_ENV[role]):
        raise PermissionError(
            f"role '{role}' requires {ROLE_SECRET_ENV[role]} in the environment "
            f"(actor-independence: this secret must live only in the {role} runtime, "
            f"never in the implementer agent's env)")


# ── HTTP ─────────────────────────────────────────────────────────────────────
_last = [0.0]


def _api(method, path, body=None, retries=6):
    now = time.time()
    if now - _last[0] < 1.1:
        time.sleep(1.1 - (now - _last[0]))
    _last[0] = time.time()
    headers = {"X-API-Key": KEY, "Content-Type": "application/json", "User-Agent": UA}
    if CF_ID and CF_SECRET:
        headers["CF-Access-Client-Id"] = CF_ID
        headers["CF-Access-Client-Secret"] = CF_SECRET
    data = json.dumps(body).encode() if body is not None else None
    attempt = 0
    deadline = time.time() + 600  # wall-clock cap so 429s don't burn the retry budget (REL-07)
    while True:
        req = urllib.request.Request(f"{API_BASE}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code == 429:  # do NOT count against `retries`; honor Retry-After + jitter
                ra = e.headers.get("Retry-After")
                wait = float(ra) if (ra and ra.isdigit()) else 30
                if time.time() + wait > deadline:
                    raise RuntimeError(f"{method} {path}: 429 retry deadline exceeded")
                time.sleep(wait + random.uniform(0, 2)); continue
            if 500 <= e.code < 600 and attempt < retries:
                time.sleep(min(2 ** attempt, 30) + random.uniform(0, 1)); attempt += 1; continue
            raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:300]}")
        except urllib.error.URLError as e:  # transient DNS/conn blip (COR-07)
            if attempt < retries:
                time.sleep(min(2 ** attempt, 30) + random.uniform(0, 1)); attempt += 1; continue
            raise RuntimeError(f"{method} {path} -> connection failed: {e}")


def _paginate(path):
    out, cur = [], None
    for _ in range(80):
        sep = "&" if "?" in path else "?"
        d = _api("GET", path + f"{sep}per_page=100" + (f"&cursor={cur}" if cur else ""))
        if isinstance(d, list):
            out.extend(d); break
        out.extend(d.get("results", []))
        if not d.get("next_page_results"):
            break
        cur = d.get("next_cursor")
        if not cur:
            break
    return out


# ── Live state resolution (CFG-02/COR-01) ────────────────────────────────────
_STATES = None
_ID2STATE = None


def states():
    global _STATES, _ID2STATE
    if _STATES is None:
        rows = _paginate(f"{PBASE}/states/")
        _STATES = {r["name"]: r["id"] for r in rows}
        _ID2STATE = {r["id"]: r["name"] for r in rows}
    return _STATES


def id2state(state_uuid):
    states()
    return _ID2STATE.get(state_uuid)


def state_id(name):
    sid = states().get(name)
    if not sid:
        raise KeyError(f"state {name!r} not found on board {WS}/{PROJ} "
                      f"(have: {sorted(states())}) — wrong board?")
    return sid


def get_issue(issue_id):
    return _api("GET", f"{PBASE}/work-items/{issue_id}/")


def transition(issue_id, to_state, actor_role):
    """Move an issue, enforcing actor authority + actor-independence + gate ORDER."""
    check_actor(actor_role, to_state)                 # REL-02 authority + SEC-03 identity
    cur = id2state(get_issue(issue_id).get("state"))  # gate-order: read CURRENT state
    if cur is None:
        raise RuntimeError(f"cannot resolve current state of {issue_id} on this board")
    if not legal_edge(cur, to_state):
        raise PermissionError(
            f"illegal transition {cur!r} -> {to_state!r} for {issue_id} "
            f"(gate order; legal next: {FORWARD.get(cur)!r} or {sorted(UNIVERSAL)})")
    r = _api("PATCH", f"{PBASE}/work-items/{issue_id}/", {"state": state_id(to_state)})
    # read-back assert (CFG-08): confirm the board actually moved
    if isinstance(r, dict) and r.get("state") and id2state(r["state"]) != to_state:
        raise RuntimeError(f"transition not applied: board still at {id2state(r['state'])!r}")
    return r


def post_evidence(issue_id, test_file, test_name, output_hash, collected_at, actor_role="verifier"):
    """Attach an Evidence_Record (4-field) as a comment — all values HTML-escaped (SEC-02)."""
    e = html.escape
    body = ("<p><b>Evidence_Record</b> (actor: %s)</p><ul>"
            "<li><code>test_file</code>: %s</li><li><code>test_name</code>: %s</li>"
            "<li><code>output_hash</code>: %s</li><li><code>collected_at</code>: %s</li></ul>"
            % (e(str(actor_role)), e(str(test_file)), e(str(test_name)),
               e(str(output_hash)), e(str(collected_at))))
    return _api("POST", f"{PBASE}/work-items/{issue_id}/comments/", {"comment_html": body})


def comment(issue_id, html_body, escape=True):
    """Post a comment. By default the body is escaped; pass escape=False only for trusted markup."""
    payload = html.escape(html_body) if escape else html_body
    return _api("POST", f"{PBASE}/work-items/{issue_id}/comments/", {"comment_html": payload})


if __name__ == "__main__":
    print(json.dumps({"board": f"{API_BASE} {WS}/{PROJ}", "cf": bool(CF_ID),
                      "states": sorted(states())}, indent=1))

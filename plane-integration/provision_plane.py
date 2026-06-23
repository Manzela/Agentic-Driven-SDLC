#!/usr/bin/env python3
"""
Provision the Agentic SDLC Control Plane workspace in a live Plane instance from
the reconciled .kiro spec blueprint (docs/plane/plane_backlog.json).

Idempotent: keyed by external_id (external_source="ascp-kiro"); a local state file
(.provision_state.json) maps logical keys -> Plane UUIDs so re-runs skip existing
objects. Uses only the public REST API (X-API-Key) -- the same path the agents use.

Hierarchy:  Epic (8)  ->  Story (49)  ->  Task (186)   [subtasks rendered as a
checklist inside each task's description]. Custom-field values (agent_role,
requirement_id, evidence_status, coverage_type, ears_pattern, gate, ...) are
encoded into a structured metadata block in each issue's description AND mapped to
labels where a label exists, because the community edition's public API does not
expose custom-property creation.
"""
import os, sys, json, time, random, pathlib, urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
CREDS = ROOT / "plane-selfhost" / "credentials.env"
BACKLOG = ROOT / "docs" / "plane" / "plane_backlog.json"
STATE_FILE = HERE / ".provision_state.json"
EXTERNAL_SOURCE = "ascp-kiro"

# ---------- config ----------
def load_env(path):
    env = {}
    for line in pathlib.Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); env[k] = v
    return env

CFG = load_env(CREDS)
API_BASE = CFG["PLANE_API_BASE"].rstrip("/")
WS = CFG["PLANE_WORKSPACE_SLUG"]
PROJ = CFG["PLANE_PROJECT_ID"]
KEY = CFG["PLANE_API_KEY"]
PBASE = f"/workspaces/{WS}/projects/{PROJ}"
# Browser UA so a CF-fronted board doesn't 1010 (REL-05); CF-Access headers if present (remote board).
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ascp-automation"
CF_ID = os.environ.get("CF_ACCESS_CLIENT_ID", "")
CF_SECRET = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")

STATE_GROUP_COLOR = {
    "backlog": "#94a3b8", "unstarted": "#6366f1", "started": "#f59e0b",
    "completed": "#10b981", "cancelled": "#ef4444",
}
def label_color(name):
    p = name.split(":")[0]
    return {"agent": "#2563eb", "priority": "#f97316", "type": "#14b8a6",
            "gate": "#a855f7", "phase": "#64748b"}.get(p, "#ef4444")

PRIORITY_BY_LABEL = {"priority:blocking": "urgent", "priority:high": "high", "priority:normal": "medium"}

# ---------- http ----------
class ApiError(RuntimeError):
    def __init__(self, code, msg): self.code = code; super().__init__(msg)

_last_ts = [0.0]
def _throttle(min_interval=1.1):
    now = time.time()
    dt = now - _last_ts[0]
    if dt < min_interval:
        time.sleep(min_interval - dt)
    _last_ts[0] = time.time()

def _headers():
    h = {"X-API-Key": KEY, "Content-Type": "application/json", "User-Agent": UA}
    if CF_ID and CF_SECRET:
        h["CF-Access-Client-Id"] = CF_ID
        h["CF-Access-Client-Secret"] = CF_SECRET
    return h


def api(method, path, body=None, retries=8):
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    last = None
    attempt = 0
    deadline = time.time() + 600          # 429s wait against a wall-clock cap, not the retry budget (REL-07)
    while attempt < retries:
        _throttle()
        req = urllib.request.Request(url, data=data, method=method, headers=_headers())
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            txt = e.read().decode("utf-8", "replace")[:400]
            last = ApiError(e.code, f"{method} {path} -> {e.code}: {txt}")
            last.body = txt
            if e.code == 429:                 # honor Retry-After + jitter; do NOT consume `attempt`
                ra = e.headers.get("Retry-After")
                wait = float(ra) if (ra and str(ra).isdigit()) else 30
                if time.time() + wait > deadline:
                    raise last
                time.sleep(wait + random.uniform(0, 2)); continue
            if 500 <= e.code < 600:
                time.sleep(min(2 ** attempt, 30) + random.uniform(0, 1)); attempt += 1; continue
            raise last
        except urllib.error.URLError as e:
            last = ApiError(0, f"{method} {path} -> URLError {e}")
            time.sleep(min(2 ** attempt, 30) + random.uniform(0, 1)); attempt += 1; continue
    raise last

def paged(path):
    out, cursor = [], path
    seen = 0
    while cursor:
        d = api("GET", cursor)
        if isinstance(d, dict) and "results" in d:
            out += d["results"]
            nxt = d.get("next_cursor")
            # Plane cursor pagination: next page via ?cursor=
            if d.get("next_page_results") and nxt:
                cursor = f"{path}{'&' if '?' in path else '?'}cursor={nxt}"
            else:
                cursor = None
        elif isinstance(d, list):
            out += d; cursor = None
        else:
            cursor = None
    return out

# ---------- idempotency state ----------
ST = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"states": {}, "labels": {}, "issues": {}}
def save_state():
    STATE_FILE.write_text(json.dumps(ST, indent=1))

# ---------- description rendering ----------
def esc(s): return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def story_html(s):
    h = []
    if s.get("ears"):
        h.append("<p><b>EARS requirements</b></p><ul>")
        for e in s["ears"]:
            h.append(f"<li><b>[{esc(e.get('pattern'))}]</b> {esc(e.get('text'))}</li>")
        h.append("</ul>")
    if s.get("acceptance_criteria"):
        h.append("<p><b>Acceptance criteria</b></p><ul>")
        for a in s["acceptance_criteria"]: h.append(f"<li>{esc(a)}</li>")
        h.append("</ul>")
    meta = {"epic": s.get("epic_id"), "requirement_id": s.get("requirement_id"),
            "agent_role": s.get("agent_role"), "evidence_status": "unproven",
            "coverage_type": s.get("coverage_type"), "state": s.get("state"), "key": s.get("key")}
    h.append("<p><b>Control metadata</b></p><ul>")
    for k, v in meta.items():
        if v: h.append(f"<li><code>{esc(k)}</code>: {esc(str(v))}</li>")
    h.append("</ul>")
    return "".join(h)

def task_html(t, subtasks):
    h = [f"<p><b>Category:</b> {esc(t.get('category'))}</p>"]
    if subtasks:
        h.append("<p><b>Subtasks</b></p><ul>")
        for st in subtasks: h.append(f"<li>{esc(st)}</li>")
        h.append("</ul>")
    return "".join(h)

# ---------- provisioning steps ----------
def ensure_states(vocab):
    existing = {s["name"]: s["id"] for s in paged(f"{PBASE}/states/")}
    for name, group, meaning in vocab["states"]:
        if name in existing:
            ST["states"][name] = existing[name]; continue
        if name in ST["states"]: continue
        r = api("POST", f"{PBASE}/states/", {
            "name": name, "group": group, "color": STATE_GROUP_COLOR[group],
            "description": meaning, "external_id": f"state:{name}", "external_source": EXTERNAL_SOURCE})
        ST["states"][name] = r["id"]
        print(f"  state + {name} ({group})")
    save_state()

def ensure_labels(vocab):
    existing = {l["name"]: l["id"] for l in paged(f"{PBASE}/labels/")}
    for name in vocab["labels"]:
        if name in existing: ST["labels"][name] = existing[name]; continue
        if name in ST["labels"]: continue
        r = api("POST", f"{PBASE}/labels/", {
            "name": name, "color": label_color(name),
            "external_id": f"label:{name}", "external_source": EXTERNAL_SOURCE})
        ST["labels"][name] = r["id"]
        print(f"  label + {name}")
    save_state()

def label_ids(names):
    return [ST["labels"][n] for n in names if n in ST["labels"]]

def priority_of(labels):
    for l in labels:
        if l in PRIORITY_BY_LABEL: return PRIORITY_BY_LABEL[l]
    return "none"

def create_issue(key, name, html, state_uuid=None, labels=None, parent=None, priority="none"):
    if key in ST["issues"]:
        return ST["issues"][key]
    body = {"name": name[:250], "description_html": html or "<p></p>",
            "external_id": key, "external_source": EXTERNAL_SOURCE, "priority": priority}
    if state_uuid: body["state"] = state_uuid
    if labels: body["labels"] = labels
    if parent: body["parent"] = parent
    try:
        r = api("POST", f"{PBASE}/work-items/", body)
        iid = r["id"]
    except ApiError as e:
        if e.code == 409:  # external_id already exists server-side -> adopt it (idempotent)
            import re
            m = re.search(r'\{.*\}', getattr(e, "body", "") or str(e))
            iid = (json.loads(m.group(0)).get("id") if m else None)
            if not iid:
                raise
        else:
            raise
    ST["issues"][key] = iid
    save_state()
    return iid

def ensure_epics(epics, descmap):
    for e in epics:
        key = f"epic:{e['epic_id']}"
        name = f"[{e['epic_id']}] {e['title']}"
        html = descmap.get(e["epic_id"], f"<p>{esc(e['title'])}</p>")
        eid = create_issue(key, name, html, state_uuid=ST["states"].get("Agent-Triaged"),
                           labels=label_ids(["priority:high"]), priority="high")
        print(f"  epic  + {e['epic_id']} {e['title'][:50]}")
    save_state()

def ensure_stories(stories):
    for s in stories:
        key = f"story:{s['key']}"
        parent = ST["issues"].get(f"epic:{s['epic_id']}")
        labels = label_ids(s.get("labels", []))
        state_uuid = ST["states"].get(s.get("state")) or ST["states"].get("Agent-Triaged")
        sid = create_issue(key, f"{s['key']}: {s['title']}", story_html(s),
                          state_uuid=state_uuid, labels=labels, parent=parent,
                          priority=priority_of(s.get("labels", [])))
    save_state()
    print(f"  stories provisioned: {sum(1 for k in ST['issues'] if k.startswith('story:'))}")

CATEGORY_LABEL = {"Infrastructure": "phase:0", "API": "phase:1", "Orchestration": "phase:2"}
def ensure_tasks(stories):
    n = 0
    for s in stories:
        parent = ST["issues"].get(f"story:{s['key']}")
        if not parent: continue
        for i, t in enumerate(s.get("tasks", [])):
            key = f"task:{s['key']}#{i}"
            lbls = label_ids([CATEGORY_LABEL.get(t.get("category"), "phase:0")])
            create_issue(key, f"{s['key']}.{i+1} {t.get('title')}", task_html(t, t.get("subtasks", [])),
                        state_uuid=ST["states"].get("Backlog"), labels=lbls, parent=parent)
            n += 1
            if n % 25 == 0:
                save_state(); print(f"    ...{n} tasks")
    save_state()
    print(f"  tasks provisioned: {sum(1 for k in ST['issues'] if k.startswith('task:'))}")

def main():
    bl = json.loads(BACKLOG.read_text())
    vocab = bl["vocab"]; epics = bl["epics"]; stories = bl["stories"]
    # epic descriptions from blueprint markdown (first 1200 chars of each epic section)
    descmap = {}
    print(f"Provisioning ASCP -> {API_BASE} (ws={WS} proj={PROJ})")
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    if only in ("all", "states"): print("[states]");  ensure_states(vocab)
    if only in ("all", "labels"): print("[labels]");  ensure_labels(vocab)
    if only in ("all", "epics"):  print("[epics]");   ensure_epics(epics, descmap)
    if only in ("all", "stories"):print("[stories]"); ensure_stories(stories)
    if only in ("all", "tasks"):  print("[tasks]");   ensure_tasks(stories)
    print("DONE. issues:", len(ST["issues"]), "states:", len(ST["states"]), "labels:", len(ST["labels"]))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
webhook_handler — the Plane→agent ingest side of the bidirectional contract.

A self-contained HMAC-verifying webhook receiver (stdlib only). Plane POSTs work-item /
comment / cycle events here; we verify X-Plane-Signature (HMAC-SHA256), dedup on
X-Plane-Delivery, gate on genuine STATE TRANSITIONS, and route to an append-only
dispatch queue (.agent_queue.jsonl) that agent_consumer.py drains. This decouples
fast 200-OK receipt from slow agent runs.

Hardened per the plane-integration audit:
  * verify() is fail-CLOSED: no WEBHOOK_SECRET ⇒ reject; the server REFUSES to start
    without a secret unless ALLOW_INSECURE=1. Binds 127.0.0.1 by default. [SEC-01/REL-10]
  * delivery dedup evicts by RECENCY (insertion order), not lexical UUID. [REL-02/COR-02]
  * check-add-persist + enqueue are under a Lock; _save_seen is atomic; a corrupt
    seen-file is preserved (renamed), never silently wiped. [COR-05/SEC-06]
  * dispatch fires only on a real state TRANSITION (activity.field=='state'), de-duped
    per (issue_id,state); 'created' never auto-runs the verifier. [COR-03/REL-07]

Run:  WEBHOOK_SECRET=<secret> python3 webhook_handler.py    # binds 127.0.0.1:8099
"""
import os, json, hmac, hashlib, pathlib, time, threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
QUEUE = HERE / ".agent_queue.jsonl"
SEEN = HERE / ".webhook_deliveries.json"
DISPATCHED = HERE / ".webhook_dispatched.json"   # last (issue_id,state) dispatched, per-transition dedup
SEEN_CAP = 5000


def _load_dotenv(p):
    try:
        for ln in pathlib.Path(p).read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_load_dotenv(HERE / ".env")
SECRET = os.environ.get("WEBHOOK_SECRET", "")
PORT = int(os.environ.get("WEBHOOK_PORT", "8099"))
BIND = os.environ.get("WEBHOOK_BIND", "127.0.0.1")   # localhost by default (SEC-01)
ALLOW_INSECURE = os.environ.get("ALLOW_INSECURE") == "1"

# state -> agent_role that should act when an issue ENTERS this state
DISPATCH_ON_STATE = {
    "Agent-Triaged": "initializer",
    "Plan-Approved": "implementer",
    "Agent-Executing": "verifier",
    "In-Verification": "verifier",
}
# states where a freshly-CREATED item must NOT auto-dispatch (only a real transition into them)
NO_DISPATCH_ON_CREATE = {"Agent-Executing", "In-Verification"}

_lock = threading.Lock()


def _load_json(path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default
    except Exception:
        # corrupt — preserve for forensics, do NOT silently wipe (COR-05/SEC-06)
        try:
            path.rename(path.with_suffix(path.suffix + f".corrupt.{int(time.time())}"))
        except OSError:
            pass
        return default


def _atomic_write(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)   # atomic on POSIX


# _seen: OrderedDict[delivery_id] = ts, recency = insertion order (REL-02/COR-02).
# Tolerate the legacy ["uuid", ...] on-disk format (review MAJOR #2): a bare string
# becomes (uuid, 0.0) instead of crashing the unpack at import on an upgraded host.
_seen = OrderedDict(
    (tuple(x) if isinstance(x, (list, tuple)) and len(x) == 2 else (x, 0.0))
    for x in _load_json(SEEN, []))
_dispatched = _load_json(DISPATCHED, {})   # {issue_id: last_state_dispatched}


def _save_seen():
    while len(_seen) > SEEN_CAP:
        _seen.popitem(last=False)            # evict OLDEST by insertion (true recency)
    _atomic_write(SEEN, json.dumps(list(_seen.items())))


def verify(sig, raw):
    if not SECRET:
        return False                          # fail-CLOSED (SEC-01)
    if not sig:
        return False
    sig = sig.split("=", 1)[1] if sig.startswith("sha256=") else sig
    expected = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def enqueue(job):
    job["enqueued_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(QUEUE, "a") as f:
        f.write(json.dumps(job) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _is_state_transition(payload):
    """True iff this issue event is a genuine state CHANGE (not a benign edit)."""
    act = payload.get("activity") or {}
    field = act.get("field")
    if field is not None:                      # Plane sends per-field activity on updates
        return field == "state"
    return None                                # unknown — caller falls back to per-(issue,state) dedup


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, msg="OK"):
        self.send_response(code); self.send_header("Content-Type", "text/plain")
        self.end_headers(); self.wfile.write(msg.encode())

    def do_GET(self):
        return self._reply(200, "ok") if self.path == "/health" else self._reply(404, "not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length)
        sig = self.headers.get("X-Plane-Signature", "")
        delivery = self.headers.get("X-Plane-Delivery", "")
        event = self.headers.get("X-Plane-Event", "")
        if not verify(sig, raw):
            return self._reply(403, "invalid signature")
        with _lock:                            # atomic check-add-persist (COR-05)
            if delivery and delivery in _seen:
                return self._reply(200, "duplicate ignored")
            if delivery:
                _seen[delivery] = time.time(); _save_seen()
        try:
            payload = json.loads(raw or "{}")
        except Exception:
            return self._reply(400, "bad json")

        self._reply(200, "accepted")           # ack fast, then route
        try:
            self._route(event, payload, delivery)
        except Exception as e:                  # never lose the ack; record the failure
            enqueue({"kind": "route_error", "error": str(e)[:200], "delivery": delivery})

    def _route(self, event, payload, delivery):
        action = payload.get("action")
        data = payload.get("data", {}) or {}
        if event == "issue":
            issue_id = data.get("id")
            sv = data.get("state")
            state_name = sv.get("name") if isinstance(sv, dict) else sv
            role = DISPATCH_ON_STATE.get(state_name)
            if not (role and issue_id):
                return
            transition = _is_state_transition(payload)
            if transition is False:
                return                          # a non-state edit — ignore
            if action == "created" and state_name in NO_DISPATCH_ON_CREATE:
                return                          # don't auto-verify a freshly-created item
            with _lock:                         # per-(issue,state) transition dedup (COR-03)
                if _dispatched.get(issue_id) == state_name:
                    return
                _dispatched[issue_id] = state_name
                _atomic_write(DISPATCHED, json.dumps(_dispatched))
            enqueue({"kind": "agent_dispatch", "agent_role": role, "issue_id": issue_id,
                     "state": state_name, "action": action, "delivery": delivery,
                     "name": data.get("name")})
        elif event == "issue_comment":
            enqueue({"kind": "comment", "issue_id": data.get("issue"),
                     "action": action, "delivery": delivery})
        else:
            enqueue({"kind": "event", "event": event, "action": action, "delivery": delivery})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if not SECRET and not ALLOW_INSECURE:
        raise SystemExit("REFUSING TO START: WEBHOOK_SECRET not set (fail-closed). "
                         "Set WEBHOOK_SECRET, or ALLOW_INSECURE=1 for dev only.")
    if not SECRET:
        print("WARN: ALLOW_INSECURE=1 — signature verification DISABLED (dev only)")
    print(f"webhook_handler listening on {BIND}:{PORT}  (queue -> {QUEUE.name})")
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()

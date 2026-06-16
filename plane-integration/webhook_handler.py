#!/usr/bin/env python3
"""
webhook_handler — the Plane→agent ingest side of the bidirectional contract.

A self-contained HMAC-verifying webhook receiver (stdlib only). Plane POSTs work-item /
comment / cycle events here; we verify X-Plane-Signature (HMAC-SHA256), dedup on
X-Plane-Delivery, and route state-changes into an append-only dispatch queue
(.agent_queue.jsonl) that the loop driver (the_loop.py) consumes. This decouples
fast 200-OK webhook receipt from slow agent runs (resilience: REQ-LOOP, REQ-STATE).

Run:  WEBHOOK_SECRET=<secret> python3 webhook_handler.py   # listens on :8099
"""
import os, json, hmac, hashlib, pathlib, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
QUEUE = HERE / ".agent_queue.jsonl"
SEEN = HERE / ".webhook_deliveries.json"
SECRET = os.environ.get("WEBHOOK_SECRET", "")
PORT = int(os.environ.get("WEBHOOK_PORT", "8099"))

# state -> the agent_role that should act when an issue ENTERS this state
DISPATCH_ON_STATE = {
    "Agent-Triaged": "initializer",      # triaged -> compile spec
    "Plan-Approved": "implementer",      # human approved -> build the slice
    "Agent-Executing": "verifier",       # slice built -> verify (next turn)
    "In-Verification": "verifier",
}

def _load_seen():
    try: return set(json.loads(SEEN.read_text()))
    except Exception: return set()
def _save_seen(s):
    SEEN.write_text(json.dumps(sorted(s)[-5000:]))   # cap memory of deliveries

_seen = _load_seen()

def verify(sig, raw):
    # FAIL-CLOSED: an unsigned/misconfigured receiver must NOT accept arbitrary payloads
    # (those payloads enqueue agent_dispatch jobs the dispatcher will act on). When no
    # secret is configured we reject — UNLESS the operator explicitly opts into the
    # insecure dev path via ASCP_DEV_ALLOW_UNSIGNED=1.
    if not SECRET:
        return os.environ.get("ASCP_DEV_ALLOW_UNSIGNED") == "1"
    if not sig: return False
    expected = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)

def enqueue(job):
    job["enqueued_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(QUEUE, "a") as f:
        f.write(json.dumps(job) + "\n")

class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, msg="OK"):
        self.send_response(code); self.send_header("Content-Type", "text/plain")
        self.end_headers(); self.wfile.write(msg.encode())

    def do_GET(self):
        if self.path == "/health":
            return self._reply(200, "ok")
        return self._reply(404, "not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        sig = self.headers.get("X-Plane-Signature", "")
        delivery = self.headers.get("X-Plane-Delivery", "")
        event = self.headers.get("X-Plane-Event", "")
        if not verify(sig, raw):
            return self._reply(403, "invalid signature")
        if delivery and delivery in _seen:           # idempotent: drop duplicate delivery
            return self._reply(200, "duplicate ignored")
        if delivery:
            _seen.add(delivery); _save_seen(_seen)
        try:
            payload = json.loads(raw or "{}")
        except Exception:
            return self._reply(400, "bad json")

        action = payload.get("action")
        data = payload.get("data", {}) or {}
        # respond 200 FAST, then route
        self._reply(200, "accepted")

        if event == "issue":
            issue_id = data.get("id")
            state_name = (data.get("state") or {}).get("name") if isinstance(data.get("state"), dict) else data.get("state")
            role = DISPATCH_ON_STATE.get(state_name)
            if role and issue_id:
                enqueue({"kind": "agent_dispatch", "agent_role": role,
                         "issue_id": issue_id, "state": state_name,
                         "action": action, "delivery": delivery,
                         "name": data.get("name")})
        elif event == "issue_comment":
            enqueue({"kind": "comment", "issue_id": data.get("issue"),
                     "action": action, "delivery": delivery})
        # cycles/modules/projects: recorded but no dispatch
        else:
            enqueue({"kind": "event", "event": event, "action": action, "delivery": delivery})

    def log_message(self, *a):  # quiet default logging
        pass

if __name__ == "__main__":
    if not SECRET and os.environ.get("ASCP_DEV_ALLOW_UNSIGNED") == "1":
        print("WARN: WEBHOOK_SECRET not set and ASCP_DEV_ALLOW_UNSIGNED=1 — "
              "signatures NOT verified (dev only, INSECURE)")
    elif not SECRET:
        print("WARN: WEBHOOK_SECRET not set — receiver is FAIL-CLOSED (all POSTs rejected). "
              "Set WEBHOOK_SECRET, or ASCP_DEV_ALLOW_UNSIGNED=1 for insecure local dev.")
    print(f"webhook_handler listening on :{PORT}  (queue -> {QUEUE.name})")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

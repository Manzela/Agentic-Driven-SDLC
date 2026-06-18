#!/usr/bin/env python3
"""
agent_consumer — the missing reader of .agent_queue.jsonl (closes the Plane→agent loop).

webhook_handler.py enqueues `agent_dispatch` jobs; nothing read them (REL-01). This consumer
drains the queue with a COMMITTED OFFSET (.agent_queue.offset) so each job runs at-least-once
and survives restarts without reprocessing, RE-FETCHES authoritative board state before acting
(SEC-04 — never trust the webhook's payload state), and dispatches a Claude Code agent of the
named role via a configurable command.

Dispatch command (env ASCP_DISPATCH_CMD): a shell command run once per job with these env vars
set — ASCP_ROLE, ASCP_ISSUE_ID, ASCP_STATE, ASCP_ISSUE_NAME. Values are passed via the
environment (not string-interpolated) so a hostile issue name cannot inject shell. If unset,
the consumer logs what it WOULD dispatch (safe dry-run).

Run:  python3 agent_consumer.py drain     # process new jobs once, then exit
      python3 agent_consumer.py watch     # loop, polling every ASCP_POLL_SEC (default 5)
"""
import os, sys, json, time, pathlib, subprocess

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import plane_client as pc

HERE = pathlib.Path(__file__).resolve().parent
QUEUE = HERE / ".agent_queue.jsonl"
OFFSET = HERE / ".agent_queue.offset"
DISPATCH_CMD = os.environ.get("ASCP_DISPATCH_CMD", "")
POLL_SEC = int(os.environ.get("ASCP_POLL_SEC", "5"))


def _read_offset():
    try:
        return int(OFFSET.read_text().strip())
    except Exception:
        return 0


def _commit_offset(n):
    tmp = OFFSET.with_suffix(".tmp")
    tmp.write_text(str(n))
    os.replace(tmp, OFFSET)


def _dispatch(job):
    role, iid, name = job.get("agent_role"), job.get("issue_id"), job.get("name", "")
    want_state = job.get("state")
    # SEC-04: re-fetch authoritative state; skip if the item already moved on.
    try:
        live = pc.id2state(pc.get_issue(iid).get("state"))
    except Exception as e:
        print(f"  [skip] {iid}: cannot fetch live state ({str(e)[:80]})")
        return
    if live != want_state:
        print(f"  [stale] {iid}: webhook said {want_state!r} but board is {live!r} — not dispatching")
        return
    if not DISPATCH_CMD:
        print(f"  [would-dispatch] role={role} issue={iid} state={live} name={name!r}")
        return
    env = {**os.environ, "ASCP_ROLE": role or "", "ASCP_ISSUE_ID": iid or "",
           "ASCP_STATE": live or "", "ASCP_ISSUE_NAME": name or ""}
    print(f"  [dispatch] role={role} issue={iid} state={live}")
    subprocess.run(DISPATCH_CMD, shell=True, env=env, check=False)


def drain():
    if not QUEUE.exists():
        print("queue empty (no .agent_queue.jsonl)"); return 0
    lines = QUEUE.read_text().splitlines()
    start = _read_offset()
    n = 0
    for i in range(start, len(lines)):
        ln = lines[i].strip()
        if ln:
            try:
                job = json.loads(ln)
            except Exception:
                print(f"  [bad-line {i}] skipped"); _commit_offset(i + 1); continue
            if job.get("kind") == "agent_dispatch":
                _dispatch(job)
            else:
                print(f"  [non-dispatch] {job.get('kind')} (recorded, no action)")
            n += 1
        _commit_offset(i + 1)        # commit AFTER each job → exactly-once across restarts
    print(f"drained {n} job(s); offset now {len(lines)}")
    return n


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "drain"
    if cmd == "drain":
        drain()
    elif cmd == "watch":
        print(f"watching {QUEUE.name} every {POLL_SEC}s (Ctrl-C to stop)")
        while True:
            drain()
            time.sleep(POLL_SEC)
    else:
        print("usage: agent_consumer.py [drain|watch]")

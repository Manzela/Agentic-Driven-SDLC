#!/usr/bin/env python3
"""
agent_consumer — the reader of .agent_queue.jsonl (closes the Plane→agent loop).

webhook_handler.py enqueues `agent_dispatch` jobs; this consumer drains them with a COMMITTED
OFFSET (.agent_queue.offset). Guarantee is **at-least-once**: a job's offset is committed only
once the job is SETTLED — dispatched, or confirmed stale (board moved on). A transient board-fetch
failure leaves the offset at that job so it is retried next poll (never silently dropped). Dispatch
must therefore be idempotent. Each job RE-FETCHES authoritative board state before acting (SEC-04 —
never trust the webhook's payload state).

Dispatch (env ASCP_DISPATCH_CMD): a shell command run per job with ASCP_ROLE / ASCP_ISSUE_ID /
ASCP_STATE / ASCP_ISSUE_NAME in the env (passed via env, not interpolated → no shell injection from
a hostile issue name). The child env carries ONLY the role-secret for the dispatched role — never
another role's secret (actor-independence; review HIGH #3). If ASCP_DISPATCH_CMD is unset, the
consumer logs what it WOULD dispatch (safe dry-run).

Run:  python3 agent_consumer.py drain     # process settled jobs once, then exit
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
    """Return True if the job is SETTLED (offset may advance), False on a transient
    failure that must be retried (offset must NOT advance) — review HIGH #4."""
    role, iid, name = job.get("agent_role"), job.get("issue_id"), job.get("name", "")
    want_state = job.get("state")
    try:
        live = pc.id2state(pc.get_issue(iid).get("state"))   # SEC-04 authoritative re-fetch
    except Exception as e:
        print(f"  [retry] {iid}: board unreachable ({str(e)[:80]}) — leaving offset for retry")
        return False
    if live != want_state:
        print(f"  [stale] {iid}: webhook said {want_state!r} but board is {live!r} — dropping")
        return True                                          # intentional, settled drop
    if not DISPATCH_CMD:
        print(f"  [would-dispatch] role={role} issue={iid} state={live} name={name!r}")
        return True
    # per-role child env: strip ALL role secrets, then add back only this role's (review HIGH #3)
    env = {k: v for k, v in os.environ.items() if k not in pc.ROLE_SECRET_ENV.values()}
    senv = pc.ROLE_SECRET_ENV.get(role)
    if senv and os.environ.get(senv):
        env[senv] = os.environ[senv]
    env.update({"ASCP_ROLE": role or "", "ASCP_ISSUE_ID": iid or "",
                "ASCP_STATE": live or "", "ASCP_ISSUE_NAME": name or ""})
    print(f"  [dispatch] role={role} issue={iid} state={live}")
    subprocess.run(DISPATCH_CMD, shell=True, env=env, check=False)
    return True


def drain():
    if not QUEUE.exists():
        print("queue empty (no .agent_queue.jsonl)"); return 0
    raw = QUEUE.read_text()
    lines = raw.splitlines()
    # A trailing line without a newline is a partial/in-flight append — don't process/commit it yet.
    complete = len(lines) if raw.endswith("\n") else max(0, len(lines) - 1)   # review MODERATE #5
    n = 0
    for i in range(_read_offset(), complete):
        ln = lines[i].strip()
        if not ln:
            _commit_offset(i + 1); continue
        try:
            job = json.loads(ln)
        except Exception:
            print(f"  [bad-line {i}] skipped"); _commit_offset(i + 1); continue
        if job.get("kind") == "agent_dispatch":
            if not _dispatch(job):
                print("  transient failure — stopping; offset left at this job for retry")
                break                                        # do NOT commit past an unsettled job
        else:
            print(f"  [non-dispatch] {job.get('kind')} (recorded, no action)")
        n += 1
        _commit_offset(i + 1)                                # commit only AFTER the job is settled
    print(f"drained {n} job(s); offset now {_read_offset()} / {complete} complete")
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

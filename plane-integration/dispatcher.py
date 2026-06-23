#!/usr/bin/env python3
"""
dispatcher — the board→agent leg of the E6 bidirectional bridge (the half that was missing).

`webhook_handler.py` receives Plane events and appends `agent_dispatch` jobs to an
append-only queue (`.agent_queue.jsonl`). THIS module is the consumer: it tails that queue
and, for each dispatch job, invokes the mapped agent role (initializer / implementer /
verifier) to perform the .kiro completion-gate step, then lets the agent write back to the
board via `the_loop.py` / `plane_client.py`. This closes "the board drives agents":

    Plane event ──▶ webhook_handler (verify + enqueue) ──▶ .agent_queue.jsonl ──▶ dispatcher ──▶ agent ──▶ Plane

Design / safety (mirrors the spec's resilience + actor-authority posture):
  • At-least-once with dedup. Each job has a stable key (delivery|issue|state|kind);
    a processed key is never re-dispatched. A persisted cursor (`.dispatcher_state.json`)
    survives restarts. A failing job is retried up to MAX_ATTEMPTS, then quarantined
    (poison-pill protection) so one bad job can't wedge the queue.
  • Real agent execution is OFF by default. The default 'stage' invoker records intent and
    writes a Plane comment — wiring is exercised without spawning unbounded autonomous
    `claude` sessions. Set ASCP_AGENT_EXEC=1 to actually spawn `claude -p` (bounded by
    ASCP_AGENT_TIMEOUT, default 900s).
  • Every processed job appends a tamper-evident audit row via tools/audit_log.py — the
    runtime audit producer the gate path otherwise never invokes (decision ∈ allow|block).

Run:
  python3 dispatcher.py --once                  # drain the current queue and exit (cron/CI)
  python3 dispatcher.py --watch --interval 5     # daemon: poll the queue every 5s
Env:
  ASCP_AGENT_EXEC=1            actually spawn `claude -p` (default: stage/dry)
  ASCP_AGENT_TIMEOUT=900       per-agent subprocess timeout (s)
  ASCP_DISPATCHER_NO_PLANE=1   skip Plane write-back (tests / offline)
"""
import os, sys, json, time, pathlib, hashlib, subprocess, argparse

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
QUEUE = HERE / ".agent_queue.jsonl"
STATE = HERE / ".dispatcher_state.json"
AUDIT = HERE / ".dispatch_audit.jsonl"

# TRUSTED BASELINE — written by the dispatcher (TCB) to an out-of-band location
# that is NEVER part of the agent's PR payload or workspace. CI fetches it from
# this protected path; an agent controlling feature_list.json cannot tamper with it.
# Phase B will sign this file; Phase A.5 trusts it by delivery path alone.
BASELINE_PATH = HERE / "coverage_baseline.json"

VALID_ROLES = {"initializer", "implementer", "verifier"}
MAX_ATTEMPTS = 3


def _log(*a):
    print("[dispatcher]", *a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- trusted baseline writer
def _write_baseline_fail_closed(issue_ids: list, out_path=None) -> None:
    """Write the trusted coverage baseline for dispatched item ids (FAIL-CLOSED).

    The output is the TRUSTED baseline the merge gate checks the PR payload against.
    It MUST be delivered to CI out-of-band (protected artifact / protected branch /
    secret) — NEVER read from the PR payload alongside feature_list.json. An agent
    controlling feature_list.json cannot tamper with a file written here.
    Phase B signs this output; Phase A.5 trusts it by delivery path alone.

    FAIL-CLOSED: any write failure raises so that drain() surfaces the error rather
    than silently proceeding without a baseline. A silent skip would leave CI with no
    baseline file, causing the download-artifact step to fail silently (continue-on-error)
    and the gate to run without a baseline — permanently bypassing RT-01/RT-02. The spec
    mandates fail-CLOSED throughout; this function upholds that contract.

    Callers that need fail-safe behaviour (e.g. watch-mode) may catch the exception
    themselves and decide whether to abort or continue.
    """
    if not issue_ids:
        return
    path = pathlib.Path(out_path) if out_path is not None else BASELINE_PATH
    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    import baseline_writer  # noqa: PLC0415
    baseline_writer.write_baseline(required_in_scope=issue_ids, out_path=path)
    _log(f"trusted baseline written → {path} ({len(issue_ids)} item(s))")


# ---------------------------------------------------------------- audit producer
_audit = None  # AuditLog instance | False (fallback) | None (uninitialised)


def _audit_log():
    global _audit
    if _audit is not None:
        return _audit
    try:
        if str(ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(ROOT / "tools"))
        import audit_log
        _audit = audit_log.AuditLog(path=str(AUDIT))
    except Exception as e:  # never let audit wiring break dispatch
        _log(f"audit_log unavailable ({e}); using plain JSONL fallback")
        _audit = False
    return _audit


def audit(event, decision, reason, issue_id, actor="dispatcher"):
    """Append one gate-decision row. decision ∈ {'allow','block'} (REQ-AUDIT-001 contract)."""
    a = _audit_log()
    if a:
        try:
            a.append(event=event, tool=None, decision=decision, reason=reason,
                     requirement_id=issue_id, actor_agent=actor)
            return
        except Exception as e:
            _log(f"audit append failed ({e}); falling back to JSONL")
    with open(AUDIT, "a") as f:
        f.write(json.dumps({"event": event, "decision": decision, "reason": reason,
                            "issue_id": issue_id, "actor": actor,
                            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")


# ---------------------------------------------------------------- queue + cursor
def job_key(job):
    basis = "|".join(str(job.get(k, "")) for k in ("delivery", "issue_id", "state", "kind"))
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


def read_jobs():
    if not QUEUE.exists():
        return []
    jobs = []
    for line in QUEUE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            jobs.append(json.loads(line))
        except json.JSONDecodeError:
            _log("skipping malformed queue line")
    return jobs


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {"seen": [], "attempts": {}}


def save_state(st):
    st["seen"] = st.get("seen", [])[-10000:]
    STATE.write_text(json.dumps(st, indent=1))


# ---------------------------------------------------------------- Plane write-back
def _plane_comment(issue_id, html):
    if not issue_id or os.environ.get("ASCP_DISPATCHER_NO_PLANE") == "1":
        return False
    try:
        if str(HERE) not in sys.path:
            sys.path.insert(0, str(HERE))
        import plane_client as pc
        pc.comment(issue_id, html)
        return True
    except Exception as e:  # creds absent / board offline — never fail the dispatch on this
        _log(f"plane comment skipped: {e}")
        return False


def _governed_cwd_ok(root) -> bool:
    """True iff ``root`` is a governed spine checkout: ``.claude/settings.json``
    exists AND disables the ralph-loop plugin, so a dispatched agent runs under
    the governance spine rather than ungoverned / ralph-shadowed. Fail closed."""
    s = pathlib.Path(root) / ".claude" / "settings.json"
    if not s.is_file():
        return False
    try:
        d = json.loads(s.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return d.get("enabledPlugins", {}).get("ralph-loop@claude-plugins-official") is False


def _exec_claude(role, job):
    """Spawn a bounded headless agent run. OFF unless ASCP_AGENT_EXEC=1."""
    if not _governed_cwd_ok(ROOT):
        _log("REFUSED exec: cwd is not a governed spine checkout "
             "(.claude/settings.json missing or ralph-loop not disabled). Staying in stage mode.")
        return False
    prompt = (
        f"You are the {role} agent. Plane work-item {job.get('issue_id')} "
        f"('{job.get('name')}') entered state '{job.get('state')}'. Perform the {role} step "
        f"of the .kiro completion-gate workflow for this item, then record the outcome via "
        f"plane-integration/the_loop.py (advance / prove / handoff). Respect actor authority: "
        f"only the verifier may set Done; cap/budget/no-progress => handoff, never Done."
    )
    try:
        r = subprocess.run(
            ["claude", "-p", prompt], cwd=str(ROOT),
            timeout=int(os.environ.get("ASCP_AGENT_TIMEOUT", "900")),
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            _log(f"claude exec rc={r.returncode}: {r.stderr[:200]}")
        return r.returncode == 0
    except FileNotFoundError:
        _log("`claude` CLI not found — cannot EXEC; staying in stage mode for this job")
        return False
    except subprocess.TimeoutExpired:
        _log(f"claude exec timed out for issue {job.get('issue_id')}")
        return False
    except Exception as e:
        _log(f"claude exec failed: {e}")
        return False


def default_invoker(job):
    """Dispatch one job to its agent. Stage mode by default; real exec behind ASCP_AGENT_EXEC=1."""
    role = job.get("agent_role")
    issue_id = job.get("issue_id")
    exec_on = os.environ.get("ASCP_AGENT_EXEC") == "1"
    tag = "EXEC" if exec_on else "stage"
    posted = _plane_comment(
        issue_id,
        f"<p><b>Dispatcher</b> → <code>{role}</code> agent for state "
        f"<code>{job.get('state')}</code> [{tag}]</p>",
    )
    if exec_on:
        return {"mode": "exec", "role": role, "plane_comment": posted, "exec_ok": _exec_claude(role, job)}
    return {"mode": "stage", "role": role, "plane_comment": posted}


# ---------------------------------------------------------------- drain loop
def drain(invoker=default_invoker, max_attempts=MAX_ATTEMPTS, baseline_path=None):
    """Process all new agent_dispatch jobs once. Returns the number dispatched.

    After all jobs are processed, writes the trusted coverage baseline for every
    successfully dispatched issue id. The baseline is written to BASELINE_PATH (an
    out-of-band trusted location — NOT the agent workspace / PR payload). CI fetches
    it from there; an agent controlling feature_list.json cannot tamper with it.
    Phase B signs this file; Phase A.5 trusts it by delivery path alone.
    """
    st = load_state()
    seen = set(st.get("seen", []))
    attempts = dict(st.get("attempts", {}))
    dispatched = 0
    dispatched_ids: list = []

    for job in read_jobs():
        if job.get("kind") != "agent_dispatch":
            continue  # comments/other events are recorded by the receiver; not our concern
        key = job_key(job)
        if key in seen:
            continue
        role = job.get("agent_role")
        issue_id = job.get("issue_id")
        if role not in VALID_ROLES:
            audit("Dispatch", "block", f"unknown agent_role {role!r}", issue_id)
            seen.add(key)
            continue
        try:
            result = invoker(job)
            audit("Dispatch", "allow",
                  f"{role} <- issue {issue_id} ({result.get('mode')}; "
                  f"plane_comment={result.get('plane_comment')})", issue_id)
            seen.add(key)
            attempts.pop(key, None)
            dispatched += 1
            if issue_id:
                dispatched_ids.append(str(issue_id))
        except Exception as e:
            n = attempts.get(key, 0) + 1
            attempts[key] = n
            if n >= max_attempts:
                audit("Dispatch", "block", f"quarantined after {n} attempts: {e}", issue_id)
                seen.add(key)
                attempts.pop(key, None)
            else:
                audit("Dispatch", "block", f"retry {n}/{max_attempts}: {e}", issue_id)

    st["seen"] = list(seen)
    st["attempts"] = attempts
    save_state(st)

    # Write the trusted coverage baseline for all dispatched item ids (fail-closed).
    # A write failure raises so the caller sees the error rather than proceeding
    # silently without a baseline — which would leave CI permanently gateless.
    if dispatched_ids:
        _write_baseline_fail_closed(dispatched_ids, out_path=baseline_path)

    return dispatched


def watch(interval=5.0, invoker=default_invoker):
    _log(f"watching {QUEUE.name} every {interval}s "
         f"(exec={'ON' if os.environ.get('ASCP_AGENT_EXEC') == '1' else 'OFF/stage'})")
    while True:
        try:
            n = drain(invoker)
            if n:
                _log(f"dispatched {n} job(s)")
        except Exception as e:
            _log(f"drain error: {e}")
        time.sleep(interval)


def main(argv=None):
    ap = argparse.ArgumentParser(description="ASCP board→agent dispatcher (E6 consumer)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--once", action="store_true", help="drain the queue once and exit")
    g.add_argument("--watch", action="store_true", help="poll the queue forever")
    ap.add_argument("--interval", type=float, default=5.0, help="watch poll interval (s)")
    args = ap.parse_args(argv)
    if args.watch:
        watch(args.interval)
    else:
        n = drain()
        print(json.dumps({"dispatched": n, "queue": QUEUE.name}))


if __name__ == "__main__":
    main()

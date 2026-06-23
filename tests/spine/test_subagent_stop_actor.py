"""Actor-independence fixes #1/#2/#3 enforced at the SubagentStop gate."""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude/hooks/subagent_stop_hook.py"
_p = HOOK
_spec = importlib.util.spec_from_file_location("subagent_stop_hook", _p)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

OUTPUT = "playwright: home route renders — 1 passed"
HASH = "sha256:" + hashlib.sha256(OUTPUT.encode()).hexdigest()


def _record(vs="sess-v", is_="sess-i", actor="verifier", output_hash=HASH):
    return {
        "test_file": "apps/web/tests/e2e/home.spec.ts",
        "test_name": "home route renders",
        "output_hash": output_hash,
        "collected_at": "2026-06-15T22:14:07+00:00",
        "actor_agent": actor,
        "verifier_session_id": vs,
        "implementer_session_id": is_,
    }


def test_valid_distinct_session_accepted():
    # Accept now OMITS the "approve" literal: a valid record returns decision=None
    # (Stop/SubagentStop have no valid "approve" value — only "block" or omit).
    out = hook.evaluate(_record(), OUTPUT, "verifier", "[Gap] 500-state untested.")
    assert out["decision"] is None, out


def test_same_session_blocked():  # fix #2
    out = hook.evaluate(_record(vs="same", is_="same"), OUTPUT, "verifier", "[Gap] none")
    assert out["decision"] == "block" and "session" in out["reason"].lower()


def test_hash_mismatch_blocked():  # fix #3 re-derivation
    out = hook.evaluate(_record(output_hash="sha256:" + "0" * 64), OUTPUT, "verifier", "[Gap] none")
    assert out["decision"] == "block" and "hash" in out["reason"].lower()


def test_non_verifier_actor_blocked():  # fix #1
    out = hook.evaluate(_record(actor="implementer"), OUTPUT, "implementer", "[Gap] none")
    assert out["decision"] == "block"


def test_forged_actor_blocked():  # fix #1 — payload claims verifier, runtime says implementer
    out = hook.evaluate(_record(actor="verifier"), OUTPUT, "implementer", "[Gap] none")
    assert out["decision"] == "block"


def test_missing_omission_blocked():
    out = hook.evaluate(_record(), OUTPUT, "verifier", "")
    assert out["decision"] == "block"


# --- main() shell contract (D6/D12): STDERR block channel, omit-decision accept ---

def _run(event, cwd=ROOT):
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event),
                       capture_output=True, text=True, cwd=str(cwd),
                       env={**os.environ})
    return p.returncode, p.stdout, p.stderr


def _good_record(out="artifact-bytes"):
    h = "sha256:" + hashlib.sha256(out.encode()).hexdigest()
    # NOTE: collected_at is required by validate_evidence_record's four-field
    # contract (test_file, test_name, output_hash, collected_at). The plan's
    # verbatim fixture omitted it, which would reject the record and defeat the
    # accept-path assertion — added here so the accept path is truly exercised.
    return {"actor_agent": "verifier", "verifier_session_id": "v1",
            "implementer_session_id": "i1", "output_hash": h,
            "collected_at": "2026-06-15T22:14:07+00:00",
            "requirement_id": "R", "test_file": "t", "test_name": "n"}


def test_accept_omits_decision_and_exits_zero():
    out = "artifact-bytes"
    ev = {"session_id": "v1", "agent_type": "verifier",
          "tool_input": {"evidence": _good_record(out), "output": out,
                         "omission_declaration": "none X"}}
    rc, so, se = _run(ev)
    assert rc == 0
    assert '"approve"' not in so          # the no-op literal is gone


def test_self_grade_blocks_on_stderr():
    out = "artifact-bytes"
    rec = _good_record(out); rec["implementer_session_id"] = "v1"  # same as verifier
    ev = {"session_id": "v1", "agent_type": "verifier",
          "tool_input": {"evidence": rec, "output": out,
                         "omission_declaration": "none X"}}
    rc, so, se = _run(ev)
    assert rc == 2 and se.strip() != "" and so.strip() == ""


def test_no_evidence_ordinary_stop_allows():
    # An ordinary subagent finishing its turn submits no Evidence_Record — there
    # is nothing to gate, so main() allows the stop (exit 0, no block reason).
    ev = {"session_id": "i1", "agent_type": "implementer",
          "tool_input": {"output": "did some work"}}
    rc, so, se = _run(ev)
    assert rc == 0 and se.strip() == ""

"""Actor-independence fixes #1/#2/#3 enforced at the SubagentStop gate."""
import hashlib
import importlib.util
import pathlib

_p = pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/subagent_stop_hook.py"
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


def test_valid_distinct_session_approved():
    out = hook.evaluate(_record(), OUTPUT, "verifier", "[Gap] 500-state untested.")
    assert out["decision"] == "approve", out


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

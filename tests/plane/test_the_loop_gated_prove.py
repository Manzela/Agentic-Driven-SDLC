# tests/plane/test_the_loop_gated_prove.py
import hashlib
import importlib.util
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _make_stub():
    """Return a fresh plane_client stub with all methods gated_prove may call."""
    pc = types.ModuleType("plane_client")
    pc.PBASE = ""
    pc.STATES = {}
    pc.post_evidence = lambda *a, **k: None
    pc.comment = lambda *a, **k: None
    # _gate() runs on the advance path BEFORE post_evidence (no orphaned evidence):
    # it checks actor authority + gate-order against the board. Benign defaults let a
    # valid advance through; a test wanting a board-side REJECT overrides these.
    pc.check_actor = lambda *a, **k: None
    pc.get_issue = lambda *a, **k: {"state": "in-verification"}
    pc.id2state = lambda *a, **k: "In-Verification"
    pc.legal_edge = lambda *a, **k: True
    # Default: transitions must NOT happen unless a test explicitly allows them.
    pc.transition = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError(f"unexpected pc.transition call: {a!r} {k!r}")
    )
    return pc


def _load_the_loop(pc):
    """Import the_loop against the given plane_client stub."""
    sys.modules["plane_client"] = pc
    # Force a fresh import each time so stubs don't bleed across tests.
    key = "the_loop"
    sys.modules.pop(key, None)
    spec = importlib.util.spec_from_file_location(
        key, ROOT / "plane-integration/the_loop.py"
    )
    tl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tl)
    return tl


def _valid_evidence(artifact: str = "a", sessions: tuple = ("impl", "verf")) -> dict:
    """Build a well-formed evidence dict that passes all gate checks."""
    impl_id, verf_id = sessions
    return {
        "test_file": "t",
        "test_name": "n",
        "output_hash": "sha256:" + hashlib.sha256(artifact.encode()).hexdigest(),
        "collected_at": "2026-06-22T00:00:00+00:00",
        "implementer_session_id": impl_id,
        "verifier_session_id": verf_id,
    }


# ---------------------------------------------------------------------------
# 1. SELF-GRADE path: same implementer and verifier session → gate rejects.
# ---------------------------------------------------------------------------
def test_prove_blocks_self_grade(monkeypatch, tmp_path):
    """Self-grade (verifier==implementer) must produce self_heal, never Done."""
    pc = _make_stub()
    # Transition must NOT be called on a self-grade reject.
    pc.transition = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("must NOT transition on self-grade reject")
    )
    tl = _load_the_loop(pc)

    out = tl.gated_prove(
        issue_id="X",
        evidence={
            "test_file": "t",
            "test_name": "n",
            "output_hash": "sha256:" + hashlib.sha256(b"a").hexdigest(),
            "collected_at": "2026-06-22T00:00:00+00:00",
            "implementer_session_id": "i",
            "verifier_session_id": "i",          # same → SAME_SESSION
        },
        artifact="a",
        ledger={"sessions": ["i"]},
        root=tmp_path,
    )
    assert out["action"] == "self_heal"
    assert out["code"] == "SAME_SESSION"


# ---------------------------------------------------------------------------
# 2. ADVANCE path: valid evidence → pc.post_evidence + pc.transition('Done').
# ---------------------------------------------------------------------------
def test_prove_advance_sets_done(tmp_path):
    """Valid evidence must call post_evidence and transition to Done."""
    calls = []
    pc = _make_stub()
    pc.post_evidence = lambda *a, **k: calls.append(("post_evidence", a, k))
    pc.transition = lambda *a, **k: calls.append(("transition", a, k))

    tl = _load_the_loop(pc)

    artifact = "real output"
    evidence = _valid_evidence(artifact=artifact, sessions=("impl-1", "verf-1"))
    out = tl.gated_prove(
        issue_id="ITEM-1",
        evidence=evidence,
        artifact=artifact,
        ledger={"sessions": ["impl-1", "verf-1"]},
        root=tmp_path,
    )

    assert out["action"] == "advance", f"expected advance, got {out}"
    transition_calls = [c for c in calls if c[0] == "transition"]
    assert transition_calls, "pc.transition was never called on advance"
    # First positional arg after issue_id must be 'Done'
    assert transition_calls[0][1][1] == "Done", (
        f"transition target was {transition_calls[0][1][1]!r}, expected 'Done'"
    )
    post_calls = [c for c in calls if c[0] == "post_evidence"]
    assert post_calls, "pc.post_evidence was never called on advance"


# ---------------------------------------------------------------------------
# 3. HANDOFF path: repeated rejections exhaust max_self_heal → handoff.
# ---------------------------------------------------------------------------
def test_prove_handoff_after_max_self_heal(tmp_path):
    """After BLOCK_STREAK_HANDOFF consecutive rejects, action must be 'handoff'
    and pc.comment + pc.transition('HANDOFF') must both be called.

    The bound is read from execution_bounds (NOT a memorized 3) so this test tracks
    the SAME threshold the Stop hook escalates on — the config registry owns the value.
    """
    comment_calls = []
    transition_calls = []
    pc = _make_stub()
    pc.comment = lambda *a, **k: comment_calls.append((a, k))
    pc.transition = lambda *a, **k: transition_calls.append((a, k))

    tl = _load_the_loop(pc)

    # Bad evidence: self-grade → gate always rejects with SAME_SESSION.
    bad_evidence = {
        "test_file": "t",
        "test_name": "n",
        "output_hash": "sha256:" + hashlib.sha256(b"a").hexdigest(),
        "collected_at": "2026-06-22T00:00:00+00:00",
        "implementer_session_id": "i",
        "verifier_session_id": "i",
    }

    # Config-sourced bound: first (max_sh-1) calls are self_heal, the max_sh-th tips
    # into handoff. Imported here so a change to BLOCK_STREAK_HANDOFF can't silently
    # desync this test from loop_gate.gated_advance / the Stop hook.
    sys.path.insert(0, str(ROOT))
    from tools.execution_bounds import BLOCK_STREAK_HANDOFF
    max_sh = BLOCK_STREAK_HANDOFF
    out = None
    for _ in range(1, max_sh + 1):
        out = tl.gated_prove(
            issue_id="X",
            evidence=bad_evidence,
            artifact="a",
            ledger={"sessions": ["i"]},
            root=tmp_path,
        )
        if out["action"] == "handoff":
            break

    assert out is not None
    assert out["action"] == "handoff", (
        f"expected handoff after {max_sh} rejects, last action was {out['action']!r}"
    )
    assert comment_calls, "pc.comment was not called on handoff"
    assert transition_calls, "pc.transition was not called on handoff"
    assert transition_calls[-1][0][1] == "HANDOFF", (
        f"transition target was {transition_calls[-1][0][1]!r}, expected 'HANDOFF'"
    )


# ---------------------------------------------------------------------------
# 4. FORGERY guard: naive (no-tz) collected_at must be rejected by the gate.
# ---------------------------------------------------------------------------
def test_prove_rejects_naive_timestamp(tmp_path):
    """A naive (timezone-unaware) collected_at must fail gate validation,
    not silently pass as a forged backdated evidence record.
    """
    pc = _make_stub()
    pc.transition = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("must NOT transition on naive-tz evidence")
    )
    tl = _load_the_loop(pc)

    artifact = "payload"
    out = tl.gated_prove(
        issue_id="FORGE-1",
        evidence={
            "test_file": "t",
            "test_name": "n",
            "output_hash": "sha256:" + hashlib.sha256(artifact.encode()).hexdigest(),
            "collected_at": "2026-01-01T00:00:00",   # naive — no +00:00
            "implementer_session_id": "impl-x",
            "verifier_session_id": "verf-x",
        },
        artifact=artifact,
        ledger={"sessions": ["impl-x", "verf-x"]},
        root=tmp_path,
    )
    assert out["action"] in ("self_heal", "handoff"), (
        f"naive-tz forgery was accepted; got action={out['action']!r}"
    )
    assert out["code"] == "EVIDENCE_MALFORMED", (
        f"expected EVIDENCE_MALFORMED, got {out['code']!r}"
    )

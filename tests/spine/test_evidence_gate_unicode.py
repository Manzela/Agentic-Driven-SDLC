"""RT-04 fix: non-ASCII session ids cannot defeat actor-separation.

A non-ASCII id (e.g. 'ß') would casefold to 'ss' in Python but NOT in Rego's
lower() — a twin-drift. The ASCII gate collapses any non-ASCII id to "" so it is
treated as ABSENT in BOTH the Python gate and the Rego twin, closing both the
drift and the Unicode self-grade class.
"""
import hashlib
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("eg", ROOT / "tools/evidence_gate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_ART = "real-artifact"
_H = "sha256:" + hashlib.sha256(_ART.encode()).hexdigest()


def _ev(**over):
    rec = {
        "test_file": "t.py", "test_name": "t::case", "output_hash": _H,
        "collected_at": "2026-06-22T00:00:00+00:00",
        "implementer_session_id": "sess-impl", "verifier_session_id": "sess-veri",
    }
    rec.update(over)
    return rec


def test_non_ascii_verifier_id_is_absent_not_distinct():
    eg = _load()
    r = eg.check_slice(
        evidence=_ev(verifier_session_id="ß"),
        artifact=_ART,
        ledger={"sessions": ["sess-impl", "sess-veri", "ß"]},
    )
    assert r["accepted"] is False and r["code"] == "SESSION_MISSING"


def test_unicode_equivalent_self_grade_rejected():
    # 'SS' (ASCII -> 'ss') and 'ß' (non-ASCII -> '') must NOT pass as distinct.
    eg = _load()
    r = eg.check_slice(
        evidence=_ev(implementer_session_id="SS", verifier_session_id="ß"),
        artifact=_ART,
        ledger={"sessions": ["ss", "ß"]},
    )
    assert r["accepted"] is False


def test_norm_session_is_ascii_only_and_casefolds():
    eg = _load()
    assert eg._norm_session("ß") == ""              # non-ASCII -> absent
    assert eg._norm_session("  Sess-Impl  ") == "sess-impl"  # strip + casefold
    assert eg._norm_session(None) == ""             # non-string -> absent
    assert eg._norm_session("   ") == ""            # whitespace-only -> absent

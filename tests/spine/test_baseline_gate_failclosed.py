"""Phase A.5 hardening: a present-but-corrupted TRUSTED baseline fails CLOSED.

A genuinely absent baseline (None) is the pre-delivery state and ALLOWS; but a
baseline that is present yet malformed (a JSON list/string/number instead of an
object) is a corrupted trusted input and must DENY — never a silent allow that
would reopen RT-01/RT-02 on baseline corruption.
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("bg", ROOT / "tools/baseline_gate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_absent_baseline_none_allows():
    assert _load().baseline_gate(baseline=None, feature_list=None)["deny"] is False


def test_present_but_malformed_baseline_denies():
    bg = _load()
    for bad in (["A"], "A", 5, ("A",)):
        r = bg.baseline_gate(baseline=bad, feature_list={"items": []})
        assert r["deny"] is True, f"malformed baseline {bad!r} must fail closed"

"""Phase-C tests: webhook fail-closed + recency dedup (SEC-01/REL-02) and the
queue consumer's exactly-once offset (REL-01). Pure/local — no network, no server."""
import os
import sys
import json
import time
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plane-integration"))

# env BEFORE imports: a secret so verify() can be exercised; dummy board for plane_client.
os.environ["WEBHOOK_SECRET"] = "topsecret"
os.environ.setdefault("PLANE_API_BASE", "http://test.invalid/api/v1")
os.environ.setdefault("PLANE_WS", "t")
os.environ.setdefault("PLANE_PROJ", "p")
os.environ.setdefault("PLANE_API_KEY", "k")

import hmac, hashlib  # noqa: E402
import webhook_handler as wh  # noqa: E402
import agent_consumer as ac  # noqa: E402


def _sig(secret, raw):
    return hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def test_verify_valid_and_invalid():
    raw = b'{"x":1}'
    assert wh.verify(_sig("topsecret", raw), raw) is True
    assert wh.verify("sha256=" + _sig("topsecret", raw), raw) is True   # prefixed form
    assert wh.verify(_sig("wrong", raw), raw) is False
    assert wh.verify("", raw) is False


def test_verify_fail_closed_without_secret():
    saved = wh.SECRET
    try:
        wh.SECRET = ""                       # simulate unconfigured secret
        assert wh.verify(_sig("topsecret", b"x"), b"x") is False   # fail-CLOSED (SEC-01)
    finally:
        wh.SECRET = saved


def test_recency_eviction_not_lexical(tmp_path):
    # The old bug kept the lexically-largest 5000 UUIDs; the fix keeps the most-RECENT.
    wh.SEEN = tmp_path / "seen.json"
    wh.SEEN_CAP = 3
    wh._seen.clear()
    for d in ["zzz", "aaa", "mmm", "bbb", "ccc"]:   # insertion order = recency
        wh._seen[d] = time.time()
        wh._save_seen()
    assert list(wh._seen) == ["mmm", "bbb", "ccc"]   # oldest two (zzz,aaa) evicted by RECENCY
    # 'zzz' (lexically largest) was correctly evicted — the old code would have kept it.
    assert "zzz" not in wh._seen


def test_consumer_offset_exactly_once(tmp_path):
    ac.QUEUE = tmp_path / "q.jsonl"
    ac.OFFSET = tmp_path / "q.offset"
    ac.QUEUE.write_text(
        json.dumps({"kind": "event", "event": "cycle"}) + "\n" +
        json.dumps({"kind": "comment", "issue_id": "i1"}) + "\n"
    )
    assert ac.drain() == 2          # processes both non-dispatch jobs (no network)
    assert ac.drain() == 0          # offset committed → nothing reprocessed
    # append one more; only the new line is processed
    with open(ac.QUEUE, "a") as f:
        f.write(json.dumps({"kind": "event", "event": "module"}) + "\n")
    assert ac.drain() == 1
    assert ac._read_offset() == 3


def test_partial_trailing_line_not_committed(tmp_path):
    # a torn/in-flight append (no trailing newline) must NOT be processed or committed past
    ac.QUEUE = tmp_path / "q.jsonl"
    ac.OFFSET = tmp_path / "q.offset"
    ac.QUEUE.write_text(json.dumps({"kind": "event"}) + "\n" + '{"kind":"event","x"')  # truncated
    assert ac.drain() == 1                       # only the complete first line
    assert ac._read_offset() == 1
    with open(ac.QUEUE, "a") as f:               # complete the line
        f.write(':1}\n')
    assert ac.drain() == 1                        # now the (newly complete) second line
    assert ac._read_offset() == 2


def test_transient_fetch_failure_does_not_advance(tmp_path, monkeypatch):
    # at-least-once: an unfetchable dispatch job leaves the offset put (retried next poll)
    ac.QUEUE = tmp_path / "q.jsonl"
    ac.OFFSET = tmp_path / "q.offset"
    ac.QUEUE.write_text(json.dumps({"kind": "agent_dispatch", "agent_role": "verifier",
                                    "issue_id": "i1", "state": "In-Verification"}) + "\n")

    def _boom(_iid):
        raise RuntimeError("board unreachable")
    monkeypatch.setattr(ac.pc, "get_issue", _boom)
    assert ac.drain() == 0                        # not settled
    assert ac._read_offset() == 0       # offset NOT advanced (no silent drop)

    # board reachable but item moved on → settled drop (commit)
    monkeypatch.setattr(ac.pc, "get_issue", lambda _iid: {"state": "uuid"})
    monkeypatch.setattr(ac.pc, "id2state", lambda _s: "Done")  # != In-Verification → stale
    assert ac.drain() == 1
    assert ac._read_offset() == 1

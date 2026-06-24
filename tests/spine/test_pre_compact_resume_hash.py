"""Round-trip test for the pre_compact resume-hash producer (Property 26 / COH-2, task 25).

SessionStart's check_resume_integrity can only match a hash that pre_compact actually
wrote. The hook previously wrote NO run_state.resume_state_hash, so resume-integrity always
took the no-baseline branch and Property 26 was neutered. This test asserts:
  1. pre_compact writes run_state.resume_state_hash into the checkpoint payload, and
  2. that hash EQUALS a fresh state_integrity.compute_state_hash() over the same state, so
  3. check_resume_integrity(written_hash, ...) returns True (the round-trip closes).
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "pre_compact_hook", ROOT / ".claude/hooks/pre_compact_hook.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_FL = {"items": [{"id": "REQ-A-001", "type": "functional", "priority": 1,
                  "dependencies": [], "acceptance_criteria": ["x"],
                  "status": "unproven", "in_scope": True}]}
_PROGRESS = "Task 1 done\nTask 2 in progress\n"
_GIT = " M feature_list.json\n?? new.py\n"


def _setup(root: pathlib.Path):
    (root / "feature_list.json").write_text(json.dumps(_FL), encoding="utf-8")
    (root / "claude-progress.txt").write_text(_PROGRESS, encoding="utf-8")
    return {"repo_root": str(root), "git_status": _GIT}


def test_pre_compact_writes_resume_hash_and_equals_recomputation(tmp_path):
    from tools.state_integrity import compute_state_hash
    hook = _load()
    state = _setup(tmp_path)

    payload = hook.pre_compact(state)
    assert payload["ok"] is True
    written = payload["run_state"]["resume_state_hash"]

    expected = compute_state_hash(_GIT, _PROGRESS, _FL)
    assert written == expected
    assert isinstance(written, str) and len(written) == 64  # sha256 hex


def test_pre_compact_hash_round_trips_through_check_resume_integrity(tmp_path):
    """The written hash makes SessionStart's resume-integrity verdict True over the same
    durable state — the COH-2 round-trip the producer exists to guarantee."""
    from tools.state_integrity import check_resume_integrity
    hook = _load()
    payload = hook.pre_compact(_setup(tmp_path))
    written = payload["run_state"]["resume_state_hash"]
    assert check_resume_integrity(written, _GIT, _PROGRESS, _FL) is True
    # A drift in any durable input flips the verdict to False (the hash is load-bearing).
    assert check_resume_integrity(written, _GIT, _PROGRESS + "tampered\n", _FL) is False


def test_pre_compact_resume_hash_deterministic(tmp_path):
    hook = _load()
    state = _setup(tmp_path)
    h1 = hook.pre_compact(state)["run_state"]["resume_state_hash"]
    h2 = hook.pre_compact(state)["run_state"]["resume_state_hash"]
    assert h1 == h2


def test_pre_compact_still_nonblocking_and_hash_present_on_missing_state(tmp_path):
    """Even with NO durable artifacts on disk, the hook stays ok=True and still emits a
    well-formed (empty-state) resume hash — the checkpoint never blocks compaction."""
    hook = _load()
    payload = hook.pre_compact({"repo_root": str(tmp_path), "git_status": ""})
    assert payload["ok"] is True
    assert "resume_state_hash" in payload["run_state"]
    assert len(payload["run_state"]["resume_state_hash"]) == 64


def test_persist_resume_hash_writes_run_state_json(tmp_path):
    """pre_compact's delivery writes resume_state_hash into run_state.json, MERGING so
    existing loop-driver keys survive (red-team F3 delivery channel)."""
    hook = _load()
    (tmp_path / "run_state.json").write_text(json.dumps({"session_id": "s", "block_streak": 2}))
    result = hook.pre_compact(_setup(tmp_path))
    hook._persist_resume_hash(result)
    row = json.loads((tmp_path / "run_state.json").read_text())
    assert row["resume_state_hash"] == result["run_state"]["resume_state_hash"]
    assert row["session_id"] == "s" and row["block_streak"] == 2  # other keys preserved


def _load_session_start():
    spec = importlib.util.spec_from_file_location(
        "session_start_hook", ROOT / ".claude/hooks/session_start_hook.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_round_trip_holds_for_kiro_layout(tmp_path):
    """I4 (whole-branch review): the producer resolves durable files via root/.kiro/state
    candidates; the consumer must use the SAME resolution. With the model+progress under
    .kiro/ (not root), the producer hash must still verify on the consumer side — previously
    the consumer read root-only and resume_integrity_ok was permanently False here."""
    pre = _load()
    ss = _load_session_start()
    (tmp_path / ".kiro").mkdir()
    (tmp_path / ".kiro" / "feature_list.json").write_text(json.dumps(_FL))
    (tmp_path / ".kiro" / "claude-progress.txt").write_text(_PROGRESS)

    written = pre.pre_compact({"repo_root": str(tmp_path), "git_status": _GIT}
                              )["run_state"]["resume_state_hash"]
    # Consumer resolves via the SAME candidate list (root absent -> falls through to .kiro/).
    progress = ss._read_text(ss._first_existing(tmp_path, ss._PROGRESS_CANDIDATES))
    feature_list = ss._read_feature_list(ss._first_existing(tmp_path, ss._FEATURE_CANDIDATES))
    result = ss.session_start(feature_list=feature_list, progress=progress,
                              git_status=_GIT, durable_hash=written)
    assert result["resume_integrity_ok"] is True, result


def test_full_round_trip_pre_compact_to_session_start(tmp_path, monkeypatch):
    """END-TO-END (red-team F1/F2/F3): pre_compact persists the hash to run_state.json,
    and SessionStart's main reads it and verifies resume_integrity_ok=True over the SAME
    durable state — the producer↔consumer loop the task exists to close, now using ONE
    canonical hash with a real delivery channel (no event-supplied hash)."""
    pre = _load()
    ss = _load_session_start()
    _setup(tmp_path)  # writes feature_list.json + claude-progress.txt
    (tmp_path / "run_state.json").write_text(json.dumps({"session_id": "s"}))

    # Producer: checkpoint computes the hash over disk state (NO explicit git_status, so
    # the producer and consumer both derive it from the same repo) and persists it.
    pre._persist_resume_hash(pre.pre_compact({"repo_root": str(tmp_path)}))
    written = json.loads((tmp_path / "run_state.json").read_text())["resume_state_hash"]
    assert written  # delivered

    # Consumer: SessionStart resolves THIS root, reads the same files + the same git_status
    # source, reads durable_hash from run_state.json (event carries none), and verifies.
    monkeypatch.setattr(ss, "_project_root", lambda: tmp_path)
    monkeypatch.setattr(ss, "_read_git_status", lambda _root: pre._git_status(tmp_path, {}))
    durable = ss._read_run_state_hash(tmp_path)
    assert durable == written  # the consumer reads the delivered baseline
    result = ss.session_start(
        feature_list=ss._read_feature_list(tmp_path / "feature_list.json"),
        progress=ss._read_text(tmp_path / "claude-progress.txt"),
        git_status=pre._git_status(tmp_path, {}),
        durable_hash=durable,
    )
    assert result["resume_integrity_ok"] is True, result

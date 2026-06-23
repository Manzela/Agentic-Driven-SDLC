"""Task 14: the production feed makes the local depth pillars RUN on a real diff.

compute_depth_feed derives (baseline_commit, changed_files, known_ids) from git + the
committed model; threaded into gated_advance, the fail-OPEN depth pillars (Semgrep,
orphans) then actually run instead of no-opping on empty inputs. Fail-SOFT: a git error
yields empty changed_files (pillars skip), never a wedge.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import loop_gate, run_state_driver  # noqa: E402
from tools.depth_feed import compute_depth_feed  # noqa: E402

ART = "art"
HASH = "sha256:" + hashlib.sha256(ART.encode()).hexdigest()
LEDGER = {"sessions": ["i", "v"]}


def _ev(**o):
    r = {"test_file": "t", "test_name": "n", "output_hash": HASH,
         "collected_at": "2026-06-22T00:00:00+00:00",
         "implementer_session_id": "i", "verifier_session_id": "v"}
    r.update(o)
    return r


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def _init_repo(root: Path, baseline_model: dict):
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@t.test")
    _git(root, "config", "user.name", "tester")
    (root / "feature_list.json").write_text(json.dumps(baseline_model))
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "baseline")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(root),
                          capture_output=True, text=True).stdout.strip()
    _git(root, "update-ref", "refs/remotes/origin/main", head)  # fake origin/main at baseline
    return head


def test_compute_depth_feed_from_git(tmp_path):
    model = {"items": [{"id": "REQ-A-001", "type": "functional", "priority": 1,
                        "dependencies": [], "acceptance_criteria": ["x"],
                        "status": "unproven", "in_scope": True}]}
    baseline = _init_repo(tmp_path, model)
    # A change AFTER the baseline.
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "change")

    feed = compute_depth_feed(tmp_path)
    assert feed["baseline_commit"] == baseline           # merge-base origin/main HEAD
    assert "mod.py" in feed["changed_files"]
    assert feed["known_ids"] == {"REQ-A-001"}
    assert feed["feature_list_path"].endswith("feature_list.json")


def test_feed_failsoft_on_non_git_dir(tmp_path):
    """A non-git dir yields empty changed_files (pillars skip) — never raises."""
    feed = compute_depth_feed(tmp_path)
    assert feed["baseline_commit"] is None
    assert feed["changed_files"] == []
    assert feed["known_ids"] == set()


def test_depth_pillars_run_end_to_end_with_feed(tmp_path):
    """FULL CHAIN: a changed .py orphan in the diff makes the orphan pillar RUN (and
    reject) once the producer's feed is threaded into gated_advance — proving the depth
    pillars are no longer inert (Task 5 left them feedless)."""
    _init_repo(tmp_path, {"items": []})            # empty model -> any .py fn is a forward orphan
    (tmp_path / "orphan.py").write_text("def helper():\n    pass\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "add orphan")
    run_state_driver.init(tmp_path, "s")

    feed = compute_depth_feed(tmp_path)
    assert "orphan.py" in feed["changed_files"]      # the producer surfaced the changed file

    decision = loop_gate.gated_advance(
        root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER, max_self_heal=2,
        changed_files=feed["changed_files"], baseline_commit=feed["baseline_commit"],
        feature_list_path=feed["feature_list_path"], known_ids=feed["known_ids"])

    # Pillar 0 accepted (good evidence); the orphan pillar RAN and rejected -> not advance.
    assert decision["action"] != "advance", decision
    assert decision["code"] == "ORPHAN_DETECTED" or "orphan" in decision["reason"].lower()


def test_compute_depth_feed_never_raises(tmp_path):
    """The producer's 'never raises' contract (red-team F2): adversarial roots fail-soft
    to an empty feed rather than propagating an exception."""
    # nonexistent path, a file-as-root, and a bogus baseline ref all fail-soft.
    for bad in (tmp_path / "does-not-exist", tmp_path):
        feed = compute_depth_feed(bad, baseline_ref="totally-bogus-ref-xyz")
        assert feed["changed_files"] == []
        assert isinstance(feed["known_ids"], set)


def test_gated_prove_tolerates_non_dict_feed():
    """F1: a caller-supplied NON-dict depth_feed must not break the gate (the fail-soft
    promise covers the injected path too). Exercised via the_loop with a fake board."""
    import importlib.util
    pilot_spec = importlib.util.spec_from_file_location("gp", ROOT / "tools/governed_pilot.py")
    gp = importlib.util.module_from_spec(pilot_spec)
    pilot_spec.loader.exec_module(gp)
    pc = gp._mk_pc(strict=False)               # fake board client (no network)
    tl = gp._load_the_loop(pc)
    root = gp._fresh_root()
    ev = gp._good_evidence()
    # depth_feed=42 (non-dict) previously raised AttributeError on .get(); now coerced to {}.
    decision = tl.gated_prove(issue_id="X-1", evidence=ev, artifact="art",
                              ledger={"sessions": ["i", "v"]}, root=root, depth_feed=42)
    assert isinstance(decision, dict) and "action" in decision


def test_empty_feed_advances_pillars_skip(tmp_path):
    """Control: with NO changed files (empty feed) the pillars skip and a clean slice
    advances — confirming the orphan rejection above is the feed's doing, not noise."""
    _init_repo(tmp_path, {"items": []})
    run_state_driver.init(tmp_path, "s")
    decision = loop_gate.gated_advance(
        root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER,
        changed_files=[], feature_list_path=str(tmp_path / "feature_list.json"), known_ids=set())
    assert decision["action"] == "advance", decision

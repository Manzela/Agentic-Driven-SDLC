"""Integration test for WIRING ingestion + verifier failed-flip (Task 8).

Exercises the REAL wiring_ingest module + feature_list_init I/O:
  (a) WIRING candidates from emit_wiring_items() are written into feature_list.json
      via the unproven-birth path Task 7 permits;
  (b) the verifier flips an unreachable symbol unproven->failed (Req 8.2).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.wiring_checker import analyze, emit_wiring_items  # noqa: E402
from tools.wiring_ingest import (  # noqa: E402
    ingest_wiring_candidates,
    mark_wiring_failed,
)
from tools.feature_list_init import (  # noqa: E402
    init_feature_list,
    validate_against_schema,
    write_feature_list,
)


@pytest.fixture
def tmp_feature_list(tmp_path: Path) -> Path:
    model = init_feature_list(items=[])
    flist_path = tmp_path / "feature_list.json"
    write_feature_list(model, str(flist_path))
    return flist_path


def test_ingest_wiring_candidates_creates_items(tmp_feature_list: Path) -> None:
    source = '''
def reachable_func():
    """Called from module level."""
    return 42

def unreachable_func():
    """Never called."""
    return 99

if __name__ == "__main__":
    print(reachable_func())
'''
    result = analyze(["example.py"], sources={"example.py": source})
    candidates = emit_wiring_items(result)
    assert len(candidates) == 2
    assert all(c["type"] == "WIRING" for c in candidates)
    assert all(c["status"] == "unproven" for c in candidates)
    assert candidates[0]["wiring"]["reachable"] is True
    assert candidates[1]["wiring"]["reachable"] is False

    count = ingest_wiring_candidates(candidates, str(tmp_feature_list))
    assert count == 2

    content = json.loads(tmp_feature_list.read_text())
    items = content["items"]
    assert len(items) == 2
    for item in items:
        assert item["type"] == "WIRING"
        assert item["status"] == "unproven"
        assert item["in_scope"] is True
        assert "qualname" in item["wiring"]
    validate_against_schema(content)


def test_ingest_wiring_candidates_idempotent(tmp_feature_list: Path) -> None:
    source = '''
def func_a():
    return 1

if __name__ == "__main__":
    func_a()
'''
    candidates = emit_wiring_items(analyze(["test.py"], sources={"test.py": source}))
    assert len(candidates) == 1
    first_id = candidates[0]["id"]

    assert ingest_wiring_candidates(candidates, str(tmp_feature_list)) == 1
    content1 = json.loads(tmp_feature_list.read_text())
    assert len(content1["items"]) == 1
    assert content1["items"][0]["id"] == first_id

    # Re-ingest the same candidates -> de-duped by id, no duplication, count 0.
    candidates2 = emit_wiring_items(analyze(["test.py"], sources={"test.py": source}))
    assert ingest_wiring_candidates(candidates2, str(tmp_feature_list)) == 0
    content2 = json.loads(tmp_feature_list.read_text())
    assert len(content2["items"]) == 1
    assert content2["items"][0]["id"] == first_id
    assert content2["items"][0]["status"] == "unproven"


def test_mark_wiring_failed_flips_unreachable_symbols(tmp_feature_list: Path) -> None:
    source = '''
def reachable_handler():
    return "response"

def dead_utility():
    return "never called"

if __name__ == "__main__":
    print(reachable_handler())
'''
    candidates = emit_wiring_items(analyze(["app.py"], sources={"app.py": source}))
    ingest_wiring_candidates(candidates, str(tmp_feature_list))

    content_before = json.loads(tmp_feature_list.read_text())
    assert len([i for i in content_before["items"] if i["status"] == "unproven"]) == 2

    flipped = mark_wiring_failed(str(tmp_feature_list), unreachable_qualnames={"dead_utility"})
    assert flipped == 1

    content_after = json.loads(tmp_feature_list.read_text())
    by_qual = {i["wiring"]["qualname"]: i for i in content_after["items"]}
    assert by_qual["dead_utility"]["status"] == "failed"
    assert by_qual["reachable_handler"]["status"] == "unproven"
    validate_against_schema(content_after)


def test_mark_wiring_failed_only_affects_wiring_items(tmp_feature_list: Path) -> None:
    items = [
        {"id": "REQ-FUNC-001", "type": "functional", "priority": 1,
         "acceptance_criteria": ["must work"], "title": "A functional item"},
        {"id": "REQ-WIRE-001", "type": "WIRING", "priority": 1,
         "acceptance_criteria": ["symbol wired"], "status": "unproven", "in_scope": True,
         "wiring": {"symbol": "dead_func", "qualname": "dead_func", "file": "impl.py",
                    "line": 42, "reachable": False, "source": "wiring_checker.py"}},
    ]
    write_feature_list(init_feature_list(items=items), str(tmp_feature_list))

    assert mark_wiring_failed(str(tmp_feature_list), {"dead_func"}) == 1
    content = json.loads(tmp_feature_list.read_text())
    functional_item = [i for i in content["items"] if i["type"] == "functional"][0]
    wiring_item = [i for i in content["items"] if i["type"] == "WIRING"][0]
    assert functional_item["status"] == "unproven"
    assert wiring_item["status"] == "failed"
    validate_against_schema(content)


def test_mark_wiring_failed_no_flip_if_already_failed(tmp_feature_list: Path) -> None:
    items = [
        {"id": "REQ-WIRE-001", "type": "WIRING", "priority": 1,
         "acceptance_criteria": ["wired"], "status": "failed", "in_scope": True,
         "wiring": {"symbol": "dead_symbol", "qualname": "dead_symbol", "file": "mod.py",
                    "line": 10, "reachable": False, "source": "wiring_checker.py"}},
    ]
    write_feature_list(init_feature_list(items=items), str(tmp_feature_list))

    # Already failed -> no transition, count 0, status unchanged.
    assert mark_wiring_failed(str(tmp_feature_list), {"dead_symbol"}) == 0
    content = json.loads(tmp_feature_list.read_text())
    assert content["items"][0]["status"] == "failed"


def test_mark_wiring_failed_handles_missing_feature_list(tmp_path: Path) -> None:
    nonexistent = tmp_path / "missing.json"
    assert mark_wiring_failed(str(nonexistent), {"some_symbol"}) == 0


def test_ingest_handles_missing_feature_list(tmp_path: Path) -> None:
    nonexistent = tmp_path / "missing.json"
    cands = emit_wiring_items(analyze(["m.py"], sources={"m.py": "def f():\n    return 1\nf()\n"}))
    assert ingest_wiring_candidates(cands, str(nonexistent)) == 0


# === Red-team fix-locks (F-1..F-7) ==========================================
def test_f1_malformed_candidate_refused_model_stays_valid(tmp_feature_list: Path) -> None:
    """F-1: a candidate missing required fields must NOT be appended raw — the ingest
    validates the full model and refuses (returns 0, file untouched + schema-valid)."""
    before = tmp_feature_list.read_text()
    bad = {"id": "REQ-WIRE-001", "type": "WIRING", "priority": 1}  # no acceptance_criteria etc.
    assert ingest_wiring_candidates([bad], str(tmp_feature_list)) == 0
    assert tmp_feature_list.read_text() == before  # file untouched
    validate_against_schema(json.loads(tmp_feature_list.read_text()))


def test_f3_dedup_by_qualname_survives_ordinal_shift(tmp_feature_list: Path) -> None:
    """F-3: prepending a function shifts ordinal ids; de-dup by qualname must still
    ingest the genuinely-new symbol and never duplicate an existing one."""
    src1 = ("def func_a():\n    return 1\ndef func_b():\n    return 2\n"
            "if __name__ == '__main__':\n    func_a(); func_b()\n")
    ingest_wiring_candidates(emit_wiring_items(analyze(["m.py"], sources={"m.py": src1})),
                             str(tmp_feature_list))
    src2 = "def func_new():\n    return 0\n" + src1  # prepend -> ordinals shift
    n = ingest_wiring_candidates(emit_wiring_items(analyze(["m.py"], sources={"m.py": src2})),
                                 str(tmp_feature_list))
    quals = [i["wiring"]["qualname"] for i in json.loads(tmp_feature_list.read_text())["items"]]
    assert n == 1                                   # only func_new is new
    assert "func_new" in quals
    assert quals.count("func_b") == 1               # no phantom duplicate
    assert sorted(quals) == ["func_a", "func_b", "func_new"]


def test_f5_reachable_symbol_not_flipped_to_failed(tmp_feature_list: Path) -> None:
    """F-5: mark_wiring_failed must REFUSE to fail a reachable symbol even if its
    qualname is passed (a reachable obligation must be proven, never failed)."""
    items = [{"id": "REQ-WIRE-001", "type": "WIRING", "priority": 1,
              "acceptance_criteria": ["wired"], "status": "unproven", "in_scope": True,
              "wiring": {"symbol": "live", "qualname": "live", "file": "m.py", "line": 1,
                         "reachable": True, "source": "wiring_checker.py"}}]
    write_feature_list(init_feature_list(items=items), str(tmp_feature_list))
    assert mark_wiring_failed(str(tmp_feature_list), {"live"}) == 0
    assert json.loads(tmp_feature_list.read_text())["items"][0]["status"] == "unproven"


def test_f6_ingest_preserves_trailing_newline(tmp_feature_list: Path) -> None:
    """F-6: an ingest writes a POSIX trailing newline like write_feature_list."""
    cands = emit_wiring_items(analyze(["m.py"], sources={"m.py": "def f():\n    return 1\nf()\n"}))
    ingest_wiring_candidates(cands, str(tmp_feature_list))
    assert tmp_feature_list.read_text().endswith("\n")


def test_f7_within_batch_duplicate_qualname_deduped(tmp_feature_list: Path) -> None:
    """F-7: two candidates for the same symbol in ONE call de-dup to a single item."""
    cand = {"id": "REQ-WIRE-050", "type": "WIRING", "priority": 1,
            "acceptance_criteria": ["wired"], "status": "unproven", "in_scope": True,
            "wiring": {"symbol": "dup", "qualname": "dup", "file": "m.py", "line": 1,
                       "reachable": False, "source": "wiring_checker.py"}}
    dup2 = {**cand, "id": "REQ-WIRE-051"}  # same qualname, different id
    assert ingest_wiring_candidates([cand, dup2], str(tmp_feature_list)) == 1
    assert len(json.loads(tmp_feature_list.read_text())["items"]) == 1


def test_f2_atomic_write_no_temp_leak_on_replace_failure(tmp_path: Path) -> None:
    """F-2: when os.replace fails (dest is a directory), _atomic_write returns False
    and leaves NO temp file behind."""
    import tools.wiring_ingest as wi
    dest = tmp_path / "fl.json"
    dest.mkdir()  # a directory at the dest path -> os.replace raises
    assert wi._atomic_write({"items": []}, str(dest)) is False
    leaked = [p.name for p in tmp_path.iterdir() if p.name.startswith(".wiring_ingest_")]
    assert leaked == [], f"temp file leaked: {leaked}"

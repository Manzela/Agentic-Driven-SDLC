"""CLI-contract tests for orphan_detector.main() — the traceability-gate caller.

main() is the ONLY orphan_detector function with no direct unit coverage (the existing
suites import detect_orphans/detect_orphans_diff; test_phase1_ci_workflows invokes the CLI
with --help only). It owns the live `traceability-gate` contract: exit 0 = ok / 1 = orphan
(or a load failure), stdout = the structured JSON report. These tests PIN that contract so
the cognitive-complexity refactor of main() (tech-debt Order 5b) is behaviour-preserving —
they must pass against the CURRENT main() first, then unchanged against the refactor.
"""
import json

import tools.orphan_detector as od
from tools.orphan_detector import main


def _run(args, capsys):
    """Invoke main(argv), return (exit_code, parsed_report_or_None, raw_stdout)."""
    code = main(args)
    out = capsys.readouterr().out
    try:
        report = json.loads(out)
    except json.JSONDecodeError:
        report = None
    return code, report, out


def _write_fl(tmp_path, items):
    fl = tmp_path / "feature_list.json"
    fl.write_text(json.dumps({"items": items}), encoding="utf-8")
    return fl


# --- exit-code contract ------------------------------------------------------
def test_clean_repo_exits_0(tmp_path, capsys):
    # one requirement with an artifact, no .py in root -> no forward/backward orphans.
    fl = _write_fl(tmp_path, [{"id": "REQ-A-001", "has_artifact": True}])
    code, report, _ = _run(["--feature-list", str(fl), "--root", str(tmp_path)], capsys)
    assert code == 0
    assert report["ok"] is True
    assert report["forward_orphans"] == [] and report["backward_orphans"] == []


def test_forward_orphan_exits_1(tmp_path, capsys):
    fl = _write_fl(tmp_path, [])
    (tmp_path / "orphan.py").write_text("x = 1  # no requirement reference\n", encoding="utf-8")
    code, report, _ = _run(["--feature-list", str(fl), "--root", str(tmp_path)], capsys)
    assert code == 1
    assert report["ok"] is False
    assert any("orphan.py" in str(fo) for fo in report["forward_orphans"])


def test_backward_orphan_exits_1(tmp_path, capsys):
    # a requirement with no artifact + no referencing impl unit is a backward orphan.
    fl = _write_fl(tmp_path, [{"id": "REQ-A-001"}])
    code, report, _ = _run(["--feature-list", str(fl), "--root", str(tmp_path)], capsys)
    assert code == 1
    assert "REQ-A-001" in report["backward_orphans"]


# --- load-failure contract (fail to exit 1 with a structured error) ----------
def test_missing_feature_list_exits_1(tmp_path, capsys):
    code, report, _ = _run(
        ["--feature-list", str(tmp_path / "nope.json"), "--root", str(tmp_path)], capsys)
    assert code == 1
    assert report["ok"] is False
    assert "cannot load feature_list" in report["error"]


def test_malformed_feature_list_exits_1(tmp_path, capsys):
    fl = tmp_path / "feature_list.json"
    fl.write_text("{ this is not valid json", encoding="utf-8")
    code, report, _ = _run(["--feature-list", str(fl), "--root", str(tmp_path)], capsys)
    assert code == 1
    assert "cannot load feature_list" in report["error"]


# --- diff-aware (--baseline-commit) branch -----------------------------------
def test_baseline_unreachable_fails_closed_exits_1(tmp_path, capsys):
    # A non-git tmp => merge-base unreachable => CI fail-CLOSED (never a silent full-repo
    # widening). This is the load-bearing §3.4 contract of the diff-aware traceability-gate.
    fl = _write_fl(tmp_path, [{"id": "REQ-A-001", "has_artifact": True}])
    code, report, _ = _run(
        ["--feature-list", str(fl), "--root", str(tmp_path), "--baseline-commit", "deadbeef"], capsys)
    assert code == 1
    assert report["ok"] is False
    assert "unreachable" in report.get("error", "").lower()


def test_baseline_diff_aware_clean_exits_0(tmp_path, capsys, monkeypatch):
    # Reachable baseline + a clean PR diff -> exit 0. Mocks the git helpers (the plan's
    # approach) so the diff-aware branch is exercised without a real git repo.
    fl = _write_fl(tmp_path, [{"id": "REQ-A-001"}])
    (tmp_path / "impl.py").write_text("# implements REQ-A-001\n", encoding="utf-8")
    monkeypatch.setattr(od, "_get_merged_base", lambda *a, **k: "base_sha")      # reachable
    monkeypatch.setattr(od, "_get_changed_files", lambda *a, **k: ["impl.py"])
    monkeypatch.setattr(od, "_load_feature_list_from_commit", lambda *a, **k: {})  # -> model_delta None
    code, report, _ = _run(
        ["--feature-list", str(fl), "--root", str(tmp_path), "--baseline-commit", "base_sha"], capsys)
    assert code == 0
    assert report["ok"] is True


# --- --links fold-in resolves a backward orphan ------------------------------
def test_links_fold_in_resolves_backward_orphan(tmp_path, capsys):
    fl = _write_fl(tmp_path, [{"id": "REQ-A-001"}])  # no inline artifact -> backward orphan
    # without --links: REQ-A-001 is a backward orphan -> exit 1
    code1, report1, _ = _run(["--feature-list", str(fl), "--root", str(tmp_path)], capsys)
    assert code1 == 1 and "REQ-A-001" in report1["backward_orphans"]
    # with --links supplying a test link -> folded in -> has an artifact -> exit 0
    links = tmp_path / "links.json"
    links.write_text(json.dumps({"links": [{"requirement_id": "REQ-A-001", "link_type": "test"}]}),
                     encoding="utf-8")
    code2, report2, _ = _run(
        ["--feature-list", str(fl), "--root", str(tmp_path), "--links", str(links)], capsys)
    assert code2 == 0 and report2["ok"] is True


def test_output_is_sorted_indented_json(tmp_path, capsys):
    # The gate parses stdout; pin the json.dumps(indent=2, sort_keys=True) shape.
    fl = _write_fl(tmp_path, [{"id": "REQ-A-001", "has_artifact": True}])
    _, _, out = _run(["--feature-list", str(fl), "--root", str(tmp_path)], capsys)
    assert '"ok": true' in out and out.index('"backward_orphans"') < out.index('"forward_orphans"')


# --- CWE-22 path-traversal guard (--feature-list / --links confined to --root) -----------
def test_feature_list_outside_root_fails_closed(tmp_path, capsys):
    # A --feature-list resolving OUTSIDE --root is rejected as a load failure (fail-closed).
    (tmp_path / "root").mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"items": []}), encoding="utf-8")
    code, report, _ = _run(
        ["--feature-list", str(outside), "--root", str(tmp_path / "root")], capsys)
    assert code == 1
    assert "cannot load feature_list" in report["error"] and "escapes the scan root" in report["error"]


def test_links_outside_root_silently_ignored(tmp_path, capsys):
    # A --links OUTSIDE --root is ignored (links are optional) -> the backward orphan it would
    # have resolved stays unresolved -> exit 1, same as if no --links were passed.
    fl = _write_fl(tmp_path, [{"id": "REQ-A-001"}])
    evil = tmp_path.parent / "evil_links.json"
    evil.write_text(json.dumps({"links": [{"requirement_id": "REQ-A-001", "link_type": "test"}]}),
                    encoding="utf-8")
    code, report, _ = _run(
        ["--feature-list", str(fl), "--root", str(tmp_path), "--links", str(evil)], capsys)
    assert code == 1 and "REQ-A-001" in report["backward_orphans"]  # link ignored, still orphan

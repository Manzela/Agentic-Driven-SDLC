"""Structural oracle for the Phase-1 CI depth workflows (Task 15).

A GitHub Actions workflow can't run locally, but its CONTRACT is structural and fully
checkable: each gating job's `name:` must equal its registered required-check context
(RT-04 — the recurring drift bug), each must `fetch-depth: 0` + carry a fail-closed
merge-base self-test, and the fork guards must be exactly right (Semgrep fork-safe so it
binds on fork PRs; CodeQL/Sonar same-repo-only SARIF/secret). Also verifies the
orphan-detector CLI the traceability gate invokes actually accepts --baseline-commit.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WF = ROOT / ".github" / "workflows"


def _load(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text())


def _job(wf: dict, job_id: str) -> dict:
    return wf.get("jobs", {}).get(job_id, {})


def _steps(job: dict) -> list:
    return job.get("steps", [])


def _checkout(job: dict) -> dict:
    return next((s for s in _steps(job) if "checkout" in str(s.get("uses", ""))), {})


def _self_test(job: dict) -> dict:
    return next((s for s in _steps(job) if "merge-base" in str(s.get("run", ""))), {})


# (file, job_id, required-check CONTEXT == job name:) — RT-04: these MUST match exactly.
_GATING = [
    ("codeql.yml", "codeql-analysis", "sast-codeql"),
    ("semgrep.yml", "semgrep", "sast-semgrep"),
    ("traceability-gate.yml", "traceability-gate", "traceability-gate"),
]


@pytest.mark.parametrize("fname,job_id,context", _GATING)
def test_job_name_equals_required_check_context(fname, job_id, context):
    """RT-04: the job name: is the registered branch-protection context — exact match."""
    job = _job(_load(fname), job_id)
    assert job, f"{fname}: job '{job_id}' missing"
    assert job.get("name") == context, f"{fname}: job name {job.get('name')!r} != context {context!r}"


@pytest.mark.parametrize("fname,job_id,_c", _GATING)
def test_fetch_depth_zero(fname, job_id, _c):
    co = _checkout(_job(_load(fname), job_id))
    assert co.get("with", {}).get("fetch-depth") == 0, f"{fname}: checkout must fetch-depth: 0"


@pytest.mark.parametrize("fname,job_id,_c", _GATING)
def test_merge_base_self_test_fail_closed(fname, job_id, _c):
    st = _self_test(_job(_load(fname), job_id))
    assert st, f"{fname}: merge-base self-test step missing"
    run = st.get("run", "")
    assert "exit 1" in run, f"{fname}: self-test must exit non-zero on unreachable base"
    assert "fetch-depth:0 required" in run, f"{fname}: self-test must name the cause"


def test_codeql_sarif_same_repo_only():
    """CodeQL SARIF upload is same-repo-only (a fork's read-only token can't write it)."""
    job = _job(_load("codeql.yml"), "codeql-analysis")
    up = next((s for s in _steps(job) if "upload-sarif" in str(s.get("uses", ""))), {})
    assert "github.repository" in up.get("if", ""), "CodeQL SARIF upload must be same-repo-only"


def test_codeql_nightly_baseline_schedule():
    on = _load("codeql.yml").get(True, _load("codeql.yml").get("on", {}))  # 'on' may parse as True
    sched = on.get("schedule", []) if isinstance(on, dict) else []
    assert any("0 0" in s.get("cron", "") for s in sched), "CodeQL needs a nightly baseline cron"


def test_semgrep_is_fork_safe_no_secrets():
    """Semgrep is the BINDING fork backstop: OSS, no SEMGREP_APP_TOKEN / secret anywhere,
    so it runs on fork PRs (where CodeQL/Sonar are skipped)."""
    # Ignore comment lines — a comment documenting the ABSENCE of a token is fine; only
    # an actual `secrets.`/token USE makes it fork-unsafe.
    code = "\n".join(ln for ln in (WF / "semgrep.yml").read_text().splitlines()
                     if not ln.lstrip().startswith("#"))
    assert "secrets." not in code, "semgrep must not reference any repo secret (fork-unsafe)"
    assert "SEMGREP_APP_TOKEN" not in code, "semgrep must run in OSS mode (no app token)"
    run = " ".join(str(s.get("run", "")) for s in _steps(_job(_load("semgrep.yml"), "semgrep")))
    assert "--baseline-commit" in run, "semgrep must be diff-aware (--baseline-commit)"
    # Whole-branch I8/I9: block only on ERROR (HIGH/CRITICAL design + the local evidence_gate
    # twin), NOT bare --error which over-blocks on WARNING/INFO and diverges from the local gate.
    assert "--severity ERROR" in run, "semgrep must gate ERROR-only (not bare --error on any finding)"


def test_traceability_invokes_orphan_detector_diff_aware():
    run = " ".join(str(s.get("run", "")) for s in _steps(_job(_load("traceability-gate.yml"), "traceability-gate")))
    assert "orphan_detector.py" in run and "--baseline-commit" in run
    assert "REQ-" in run, "traceability gate must assert the REQ-6.2 commit trailer"


def test_sonar_properties_new_code_and_exclusions():
    props = dict(
        line.split("=", 1) for line in (ROOT / "sonar-project.properties").read_text().splitlines()
        if "=" in line and not line.strip().startswith("#")
    )
    assert props.get("sonar.newCode.referenceBranch") == "main"
    assert props.get("sonar.qualitygate.wait") == "true"
    assert "tools/**" in props.get("sonar.exclusions", "")


def test_orphan_detector_cli_accepts_baseline_commit():
    """The CLI the traceability gate invokes must actually accept --baseline-commit
    (it was deferred in Task 3; the gate would reference a phantom flag otherwise)."""
    out = subprocess.run([sys.executable, str(ROOT / "tools/orphan_detector.py"), "--help"],
                         capture_output=True, text=True, cwd=str(ROOT))
    assert out.returncode == 0
    assert "--baseline-commit" in out.stdout and "--exempt-paths" in out.stdout


# --- red-team fix-locks (C1 / I3 / I5) ---------------------------------------
def test_traceability_skips_when_feature_list_absent():
    """C1: feature_list.json is a runtime artifact (not committed); the gate must SKIP
    (not block every PR). The workflow guards the orphan step on the file's existence."""
    run = " ".join(str(s.get("run", "")) for s in _steps(
        _job(_load("traceability-gate.yml"), "traceability-gate")))
    assert "if [ ! -f feature_list.json ]" in run, "missing absent-model skip guard"


@pytest.mark.parametrize("fname,job_id,_c", _GATING)
def test_self_test_fetches_origin_main(fname, job_id, _c):
    """I5: the self-test must fetch origin/main first, else a missing remote-tracking ref
    on a PR checkout false-fails it and blocks every PR."""
    st = _self_test(_job(_load(fname), job_id))
    assert "git fetch" in st.get("run", "") and "origin main" in st.get("run", ""), fname


def _git(cwd, *a):
    subprocess.run(["git", *a], cwd=str(cwd), check=True, capture_output=True)


def _cli_diff(repo, base, exempt="tools/**"):
    return subprocess.run(
        [sys.executable, str(ROOT / "tools/orphan_detector.py"),
         "--baseline-commit", base, "--exempt-paths", exempt,
         "--feature-list", "feature_list.json", "--root", "."],
        cwd=str(repo), capture_output=True, text=True)


def test_cli_backward_pass_scoped_to_model_delta(tmp_path):
    """I3: an UNRELATED change must NOT be blocked by a pre-existing un-evidenced item —
    the CLI scopes the backward pass to the PR's model-delta (was: all requirements)."""
    import json as _json
    fl = {"items": [{"id": "REQ-OLD-001", "type": "functional", "priority": 1,
                     "dependencies": [], "acceptance_criteria": ["x"],
                     "status": "unproven", "in_scope": True}]}
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "feature_list.json").write_text(_json.dumps(fl))
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "base")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(tmp_path),
                          capture_output=True, text=True).stdout.strip()
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", base)
    # PR touches ONLY an unrelated docs file (not the model, not REQ-OLD-001).
    (tmp_path / "README.md").write_text("docs\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "unrelated docs")
    r = _cli_diff(tmp_path, base)
    assert r.returncode == 0, f"unrelated PR over-blocked: {r.stdout}"
    assert _json.loads(r.stdout)["backward_orphans"] == []

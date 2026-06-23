# tests/spine/test_ci_evidence_check.py
"""End-to-end CI-level tests for ci_evidence_check.run().

Covers the integration path from feature_list.json → evidence_gate, including
all red-team cases that must be caught at the CI entrypoint (not just in the
unit-level test_evidence_gate.py tests).
"""
import hashlib
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "cec", ROOT / "tools/ci_evidence_check.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_fl(path, items):
    path.write_text(json.dumps({"items": items}), encoding="utf-8")


def _write_led(path, sessions):
    path.write_text(json.dumps({"sessions": sessions}), encoding="utf-8")


def _good_evidence(test_file, artifact_text, impl="impl", verif="verif"):
    return {
        "test_file": test_file,
        "test_name": "t",
        "output_hash": _sha(artifact_text),
        "collected_at": "2026-06-22T00:00:00+00:00",
        "implementer_session_id": impl,
        "verifier_session_id": verif,
    }


# ---------------------------------------------------------------------------
# Original two scenarios (preserved)
# ---------------------------------------------------------------------------

def test_rejects_hash_mismatch_at_ci(tmp_path):
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    (art / "A.txt").write_text("real", encoding="utf-8")
    h = _sha("FORGED")  # declared hash of different bytes
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "proven", "evidence": {
        "test_file": "A.txt", "test_name": "n", "output_hash": h,
        "collected_at": "2026-06-22T00:00:00+00:00",
        "implementer_session_id": "i", "verifier_session_id": "v",
    }}])
    led = tmp_path / "ledger.json"
    _write_led(led, ["i", "v"])
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 1


def test_accepts_matching_hash(tmp_path):
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    (art / "A.txt").write_text("real", encoding="utf-8")
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "proven",
                    "evidence": _good_evidence("A.txt", "real")}])
    led = tmp_path / "ledger.json"
    _write_led(led, ["impl", "verif"])
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 0


# ---------------------------------------------------------------------------
# Red-team: same-session self-grade (end-to-end through run())
# ---------------------------------------------------------------------------

def test_rejects_same_session_at_ci(tmp_path):
    """Implementer and verifier with the same id must be rejected end-to-end."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    (art / "A.txt").write_text("data", encoding="utf-8")
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "proven",
                    "evidence": _good_evidence("A.txt", "data", impl="s1", verif="s1")}])
    led = tmp_path / "ledger.json"
    _write_led(led, ["s1"])
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 1


def test_rejects_same_session_case_variant_at_ci(tmp_path):
    """Case-variant ids ('impl' vs 'IMPL') must collapse to the same session."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    (art / "A.txt").write_text("data", encoding="utf-8")
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "proven",
                    "evidence": _good_evidence("A.txt", "data", impl="impl", verif="IMPL")}])
    led = tmp_path / "ledger.json"
    _write_led(led, ["impl", "IMPL"])
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 1


# ---------------------------------------------------------------------------
# Red-team: ghost / spoofed verifier session not in ledger
# ---------------------------------------------------------------------------

def test_rejects_ghost_verifier_session_at_ci(tmp_path):
    """A verifier session id not present in the dispatch ledger must be rejected."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    (art / "A.txt").write_text("data", encoding="utf-8")
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "proven",
                    "evidence": _good_evidence("A.txt", "data", impl="i", verif="ghost")}])
    led = tmp_path / "ledger.json"
    _write_led(led, ["i"])  # "ghost" absent from ledger
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 1


# ---------------------------------------------------------------------------
# Proven item with evidence=None must be rejected
# ---------------------------------------------------------------------------

def test_rejects_proven_with_no_evidence_at_ci(tmp_path):
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "proven", "evidence": None}])
    led = tmp_path / "ledger.json"
    _write_led(led, [])
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 1


# ---------------------------------------------------------------------------
# In-scope item with status != proven must be rejected
# ---------------------------------------------------------------------------

def test_rejects_in_scope_unproven_at_ci(tmp_path):
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "unproven", "evidence": None}])
    led = tmp_path / "ledger.json"
    _write_led(led, [])
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 1


# ---------------------------------------------------------------------------
# Graceful-skip contract — absent inputs must not fail CI
# ---------------------------------------------------------------------------

def test_skips_gracefully_when_feature_list_absent(tmp_path):
    """Absent feature_list.json is pre-delivery state — must exit 0."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    led = tmp_path / "ledger.json"
    _write_led(led, [])
    fl = tmp_path / "feature_list.json"  # NOT written — does not exist
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 0


def test_skips_gracefully_when_ledger_absent(tmp_path):
    """Absent dispatch_ledger.json is pre-delivery state — must exit 0."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [])
    led = tmp_path / "ledger.json"  # NOT written — does not exist
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 0


# ---------------------------------------------------------------------------
# Path-traversal guard
# ---------------------------------------------------------------------------

def test_rejects_path_traversal_in_test_file(tmp_path):
    """A test_file value that escapes artifacts_dir must cause rejection (not a bypass)."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    # Create a file outside artifacts_dir that the attacker claims as their artifact.
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    # Attacker computes the real sha256 of that file to forge valid-looking evidence.
    h = _sha("secret")
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "proven", "evidence": {
        "test_file": "../secret.txt",  # traversal
        "test_name": "t",
        "output_hash": h,
        "collected_at": "2026-06-22T00:00:00+00:00",
        "implementer_session_id": "i",
        "verifier_session_id": "v",
    }}])
    led = tmp_path / "ledger.json"
    _write_led(led, ["i", "v"])
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 1


# ---------------------------------------------------------------------------
# Protected baseline (Phase A.5) — RT-01 / RT-02 enforced at the CI entrypoint
# ---------------------------------------------------------------------------

def test_baseline_present_but_model_absent_denies(tmp_path):
    """RT-01: a delivery is expected (baseline declares required in-scope) but the
    PR payload omits feature_list.json — the absent-input skip must NOT fire; deny."""
    cec = _load()
    bl = tmp_path / "coverage_baseline.json"
    bl.write_text('{"required_in_scope":["A"]}', encoding="utf-8")
    rc = cec.run(
        feature_list_path=tmp_path / "nope.json",
        artifacts_dir=tmp_path,
        ledger_path=tmp_path / "nope2.json",
        baseline_path=bl,
    )
    assert rc == 1  # RT-01 closed: absent model when a delivery is expected


def test_baseline_required_item_flipped_out_of_scope_denies(tmp_path):
    """RT-02: a baseline-required item flipped to in_scope:false must deny — the
    baseline gate runs before any other check."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    (art / "A.txt").write_text("real", encoding="utf-8")
    fl = tmp_path / "feature_list.json"
    # Item A is present but flipped out of scope to dodge auditing.
    _write_fl(fl, [{"id": "A", "in_scope": False, "status": "proven",
                    "evidence": _good_evidence("A.txt", "real")}])
    led = tmp_path / "ledger.json"
    _write_led(led, ["impl", "verif"])
    bl = tmp_path / "coverage_baseline.json"
    bl.write_text('{"required_in_scope":["A"]}', encoding="utf-8")
    rc = cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led, baseline_path=bl)
    assert rc == 1  # RT-02 closed: in-scope shrinking denied


def test_baseline_required_item_removed_denies(tmp_path):
    """RT-02: a baseline-required item removed from the payload entirely must deny."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [])  # required item "A" no longer present at all
    led = tmp_path / "ledger.json"
    _write_led(led, [])
    bl = tmp_path / "coverage_baseline.json"
    bl.write_text('{"required_in_scope":["A"]}', encoding="utf-8")
    rc = cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led, baseline_path=bl)
    assert rc == 1


def test_baseline_satisfied_passes_through_to_evidence_gate(tmp_path):
    """A baseline whose required items are all in-scope+proven must pass (exit 0):
    the baseline gate is additive and does not block a well-formed delivery."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    (art / "A.txt").write_text("real", encoding="utf-8")
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "proven",
                    "evidence": _good_evidence("A.txt", "real")}])
    led = tmp_path / "ledger.json"
    _write_led(led, ["impl", "verif"])
    bl = tmp_path / "coverage_baseline.json"
    bl.write_text('{"required_in_scope":["A"]}', encoding="utf-8")
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led, baseline_path=bl) == 0


def test_malformed_baseline_required_fails_closed(tmp_path):
    """A malformed baseline (required_in_scope not a list) must fail closed (deny)."""
    cec = _load()
    bl = tmp_path / "coverage_baseline.json"
    bl.write_text('{"required_in_scope":"A"}', encoding="utf-8")  # str, not list
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "proven",
                    "evidence": None}])
    led = tmp_path / "ledger.json"
    _write_led(led, [])
    rc = cec.run(feature_list_path=fl, artifacts_dir=tmp_path, ledger_path=led, baseline_path=bl)
    assert rc == 1


def test_no_baseline_absent_inputs_still_skip(tmp_path):
    """No baseline (or no baseline file) + absent inputs => pre-delivery skip (exit 0)."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    # baseline_path points at a non-existent file => treated as no baseline.
    rc = cec.run(
        feature_list_path=tmp_path / "nope.json",
        artifacts_dir=art,
        ledger_path=tmp_path / "nope2.json",
        baseline_path=tmp_path / "absent_baseline.json",
    )
    assert rc == 0


def test_empty_baseline_required_set_absent_inputs_skip(tmp_path):
    """A baseline with an empty required_in_scope expects no delivery => skip (exit 0)."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    bl = tmp_path / "coverage_baseline.json"
    bl.write_text('{"required_in_scope":[]}', encoding="utf-8")
    rc = cec.run(
        feature_list_path=tmp_path / "nope.json",
        artifacts_dir=art,
        ledger_path=tmp_path / "nope2.json",
        baseline_path=bl,
    )
    assert rc == 0


# ---------------------------------------------------------------------------
# Trust-boundary guard (Gemini RT-01/RT-02): a baseline inside the agent-
# controlled checkout ($GITHUB_WORKSPACE) must NEVER be trusted — fail closed,
# even though it is a perfectly well-formed, dict-shaped baseline file.
# ---------------------------------------------------------------------------

def _set_workspace(monkeypatch, path):
    monkeypatch.setenv("GITHUB_WORKSPACE", str(path))


def test_baseline_inside_workspace_denies_even_if_wellformed(tmp_path, monkeypatch):
    """The exact attack: a malicious PR commits a baseline into the checkout that
    declares an EMPTY required set (which would otherwise skip RT-01/RT-02). With
    GITHUB_WORKSPACE pointing at the checkout, run() must fail CLOSED rather than
    read that PR-resident file as 'trusted'."""
    cec = _load()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _set_workspace(monkeypatch, workspace)
    # Attacker-planted baseline INSIDE the checkout, empty required set => would
    # otherwise neutralize the gate.
    bl = workspace / ".trusted-baseline" / "coverage_baseline.json"
    bl.parent.mkdir(parents=True)
    bl.write_text('{"required_in_scope":[]}', encoding="utf-8")
    rc = cec.run(
        feature_list_path=workspace / "nope.json",
        artifacts_dir=workspace,
        ledger_path=workspace / "nope2.json",
        baseline_path=bl,
    )
    assert rc == 1  # trust boundary: PR-resident baseline => fail closed


def test_baseline_at_workspace_root_path_denies(tmp_path, monkeypatch):
    """A baseline path equal to the workspace root itself is also rejected."""
    cec = _load()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _set_workspace(monkeypatch, workspace)
    bl = workspace / "coverage_baseline.json"
    bl.write_text('{"required_in_scope":["A"]}', encoding="utf-8")
    rc = cec.run(
        feature_list_path=workspace / "feature_list.json",
        artifacts_dir=workspace,
        ledger_path=workspace / "ledger.json",
        baseline_path=bl,
    )
    assert rc == 1


def test_baseline_outside_workspace_is_trusted(tmp_path, monkeypatch):
    """A baseline staged OUTSIDE $GITHUB_WORKSPACE (the $RUNNER_TEMP pattern) is
    honored: RT-01 still denies an absent model when the out-of-band baseline
    expects a delivery."""
    cec = _load()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _set_workspace(monkeypatch, workspace)
    # Out-of-band staging dir — a sibling of the workspace, NOT inside it.
    runner_temp = tmp_path / "runner_temp" / "trusted-baseline"
    runner_temp.mkdir(parents=True)
    bl = runner_temp / "coverage_baseline.json"
    bl.write_text('{"required_in_scope":["A"]}', encoding="utf-8")
    rc = cec.run(
        feature_list_path=workspace / "nope.json",  # model absent
        artifacts_dir=workspace,
        ledger_path=workspace / "nope2.json",
        baseline_path=bl,
    )
    assert rc == 1  # RT-01 fires from a TRUSTED out-of-band baseline


def test_no_workspace_env_baseline_path_unrestricted(tmp_path, monkeypatch):
    """Off-runner (no GITHUB_WORKSPACE) the guard is a no-op so local/unit runs and
    the existing tmp_path-based tests keep working."""
    cec = _load()
    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
    bl = tmp_path / "coverage_baseline.json"
    bl.write_text('{"required_in_scope":["A"]}', encoding="utf-8")
    rc = cec.run(
        feature_list_path=tmp_path / "nope.json",
        artifacts_dir=tmp_path,
        ledger_path=tmp_path / "nope2.json",
        baseline_path=bl,
    )
    assert rc == 1  # honored as trusted (no workspace surface to violate)


def test_default_baseline_path_uses_runner_temp(monkeypatch, tmp_path):
    """main()'s default baseline path is the out-of-band $RUNNER_TEMP location."""
    cec = _load()
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    expected = str(tmp_path / "trusted-baseline" / "coverage_baseline.json")
    assert cec._default_baseline_path() == expected
    monkeypatch.delenv("RUNNER_TEMP", raising=False)
    assert cec._default_baseline_path() == "coverage_baseline.json"


def test_rejects_absolute_path_traversal_in_test_file(tmp_path):
    """An absolute test_file path escaping artifacts_dir must also be rejected."""
    cec = _load()
    art = tmp_path / "arts"
    art.mkdir()
    h = _sha("irrelevant")
    fl = tmp_path / "feature_list.json"
    _write_fl(fl, [{"id": "A", "in_scope": True, "status": "proven", "evidence": {
        "test_file": "/etc/hostname",
        "test_name": "t",
        "output_hash": h,
        "collected_at": "2026-06-22T00:00:00+00:00",
        "implementer_session_id": "i",
        "verifier_session_id": "v",
    }}])
    led = tmp_path / "ledger.json"
    _write_led(led, ["i", "v"])
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 1

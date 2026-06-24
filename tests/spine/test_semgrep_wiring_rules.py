"""Test for tools/semgrep_rules/wiring_dead_code.yml custom WIRING dead-code rules.

Verifies (against a REAL semgrep run — skipped when semgrep is absent):
  - Decorator-routed handlers, registered callbacks, and job/scheduler registrations
    are reported, with the matched symbol name interpolated into the message.
  - Output conforms to the real semgrep --json shape (top-level path + start.line),
    usable to build an emit_wiring_items()-shaped WIRING item keyed by qualname.
  - The union-of-concerns binding comment is present in the rule file.

NOTE (2026-06-23, execution): the plan's shape assertion read finding["location"]["path"]
— semgrep's --json result actually carries top-level `path` and `start.line` (no
`location` key). Corrected here against a live semgrep 1.167 run. A skipif guard was
added (the plan had none) so the suite stays portable where semgrep is not installed;
CI installs semgrep so the rules are still gated there.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SEMGREP_RULES_FILE = "tools/semgrep_rules/wiring_dead_code.yml"
FIXTURE_DIR = "tests/fixtures/semgrep"

pytestmark = pytest.mark.skipif(
    shutil.which("semgrep") is None,
    reason="semgrep not installed; the WIRING rules are gated in CI (Task 15)",
)


def _run_semgrep(rel_fixture):
    """Run the custom rules against a fixture (cwd=repo root) and return parsed JSON."""
    result = subprocess.run(
        ["semgrep", "--config", SEMGREP_RULES_FILE, "--json", "--quiet",
         str(Path(FIXTURE_DIR) / rel_fixture)],
        capture_output=True, text=True, cwd=ROOT,
    )
    # semgrep exits 0 on findings; tolerate 1 (no-match / advisory) per the rule design.
    assert result.returncode in (0, 1), f"Semgrep error: {result.stderr}"
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError as e:  # pragma: no cover - diagnostic
        pytest.fail(f"Semgrep output not valid JSON: {e}\nstdout: {result.stdout}")


@pytest.mark.parametrize(
    "fixture_file,expected_dead_symbols",
    [
        ("handlers_dead_code.py",
         ["unused_handler", "dead_startup_hook", "dead_async_job", "scheduled_dead_task"]),
        ("callbacks_dead_code.py", ["dead_callback"]),
        ("jobs_dead_code.py", ["schedule_dead_job", "dead_queue_handler"]),
        # Red-team F1-F4 fix-locks: non-standard router names, bare job decorator,
        # first-arg callback registration, chained .weeks scheduler call.
        ("extra_patterns_dead_code.py",
         ["api_handler", "user_create", "bare_job_fn", "first_arg_cb", "weekly_job"]),
    ],
)
def test_semgrep_detects_dead_decorator_and_callback_symbols(fixture_file, expected_dead_symbols):
    """Semgrep custom rules find decorator-routed, callback, and job-registered symbols,
    interpolating each matched symbol name into the finding message."""
    assert (ROOT / FIXTURE_DIR / fixture_file).exists(), f"Fixture {fixture_file} not found"
    output = _run_semgrep(fixture_file)
    results = output.get("results", [])

    detected = set()
    for finding in results:
        message = finding.get("extra", {}).get("message", "")
        for sym in expected_dead_symbols:
            if sym in message or sym in finding.get("check_id", ""):
                detected.add(sym)

    # EVERY expected dead symbol must be detected — the rules genuinely fire (not ≥1).
    missing = set(expected_dead_symbols) - detected
    assert not missing, f"{fixture_file}: rules failed to detect {missing}; results={results}"


def test_semgrep_output_conforms_to_wiring_shape():
    """Each finding carries the location info needed to build a qualname-keyed WIRING
    item: real semgrep --json puts path + start.line at the TOP LEVEL of each result."""
    output = _run_semgrep("handlers_dead_code.py")
    results = output.get("results", [])
    assert results, "expected at least one finding to validate the shape against"
    for finding in results:
        assert "check_id" in finding, "missing check_id"
        assert finding.get("extra", {}).get("message"), "missing message"
        assert finding.get("path"), "missing top-level path"
        assert finding.get("start", {}).get("line"), "missing start.line"
        assert finding.get("end", {}).get("line"), "missing end.line"


def test_union_of_concerns_comment_present():
    """The rule file documents that a Semgrep clean verdict is advisory and cannot
    retract an AST orphan (the binding union-of-concerns contract). BOTH the named
    contract AND its consequence must be present (red-team F6: was an OR, too weak)."""
    content = (ROOT / SEMGREP_RULES_FILE).read_text()
    assert "union-of-concerns" in content.lower(), "missing the named union-of-concerns contract"
    assert "cannot retract an ast orphan" in content.lower(), \
        "missing the consequence: a Semgrep clean result cannot retract an AST orphan"


def test_reachable_handler_is_an_expected_advisory_false_positive():
    """F5 (red-team): Semgrep sees only the decorator, not reachability, so it ALSO
    flags the intentionally-reachable active_handler. This is an ACCEPTED advisory FP
    under union-of-concerns (the AST checker, not Semgrep, decides reachability). We
    pin it so the behavior is documented, not silently surprising downstream."""
    output = _run_semgrep("handlers_dead_code.py")
    flagged = {f.get("extra", {}).get("message", "") for f in output.get("results", [])}
    assert any("active_handler" in m for m in flagged), (
        "expected the reachable handler to be flagged too — Semgrep cannot verify "
        "invocation; if this stops firing, re-confirm the union-of-concerns framing"
    )

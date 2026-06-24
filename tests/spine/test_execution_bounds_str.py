# tests/spine/test_execution_bounds_str.py
import importlib


def test_str_helper_default(monkeypatch):
    """Test that _str returns the default when env var is not set."""
    # Ensure env is clean
    monkeypatch.delenv("TEST_STR_VAR", raising=False)

    import tools.execution_bounds as eb
    importlib.reload(eb)

    # _str helper should return the provided default
    result = eb._str("TEST_STR_VAR", "default_value")
    assert result == "default_value"


def test_str_helper_env_override(monkeypatch):
    """Test that _str reads from environment when set."""
    monkeypatch.setenv("TEST_STR_VAR", "env_value")

    import tools.execution_bounds as eb
    importlib.reload(eb)

    result = eb._str("TEST_STR_VAR", "default_value")
    assert result == "env_value"


def test_orphan_detector_baseline_default(monkeypatch):
    """Test ORPHAN_DETECTOR_BASELINE defaults to 'origin/main'."""
    monkeypatch.delenv("ORPHAN_DETECTOR_BASELINE", raising=False)

    import tools.execution_bounds as eb
    importlib.reload(eb)

    assert eb.ORPHAN_DETECTOR_BASELINE == "origin/main"


def test_orphan_detector_baseline_env_override(monkeypatch):
    """Test ORPHAN_DETECTOR_BASELINE can be overridden via env."""
    monkeypatch.setenv("ORPHAN_DETECTOR_BASELINE", "custom/baseline")

    import tools.execution_bounds as eb
    importlib.reload(eb)

    assert eb.ORPHAN_DETECTOR_BASELINE == "custom/baseline"


def test_semgrep_baseline_strategy_default(monkeypatch):
    """Test SEMGREP_BASELINE_STRATEGY defaults to 'auto'."""
    monkeypatch.delenv("SEMGREP_BASELINE_STRATEGY", raising=False)

    import tools.execution_bounds as eb
    importlib.reload(eb)

    assert eb.SEMGREP_BASELINE_STRATEGY == "auto"


def test_semgrep_baseline_strategy_env_override(monkeypatch):
    """Test SEMGREP_BASELINE_STRATEGY can be set to 'explicit' or 'off'."""
    monkeypatch.setenv("SEMGREP_BASELINE_STRATEGY", "explicit")

    import tools.execution_bounds as eb
    importlib.reload(eb)

    assert eb.SEMGREP_BASELINE_STRATEGY == "explicit"

    monkeypatch.setenv("SEMGREP_BASELINE_STRATEGY", "off")
    importlib.reload(eb)

    assert eb.SEMGREP_BASELINE_STRATEGY == "off"


def test_orphan_allowlist_pattern_default(monkeypatch):
    """Test ORPHAN_ALLOWLIST_PATTERN defaults to 'tools/.*'."""
    monkeypatch.delenv("ORPHAN_ALLOWLIST_PATTERN", raising=False)

    import tools.execution_bounds as eb
    importlib.reload(eb)

    assert eb.ORPHAN_ALLOWLIST_PATTERN == "tools/.*"


def test_orphan_allowlist_pattern_env_override(monkeypatch):
    """Test ORPHAN_ALLOWLIST_PATTERN can be overridden via env."""
    monkeypatch.setenv("ORPHAN_ALLOWLIST_PATTERN", "tests/.*")

    import tools.execution_bounds as eb
    importlib.reload(eb)

    assert eb.ORPHAN_ALLOWLIST_PATTERN == "tests/.*"

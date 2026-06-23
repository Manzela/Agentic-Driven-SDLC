"""Dispatcher preflight: refuse to EXEC from an ungoverned cwd (Stage 2)."""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "dispatcher", ROOT / "plane-integration" / "dispatcher.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_governed_cwd_ok_true_when_settings_disables_ralph(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(
        {"enabledPlugins": {"ralph-loop@claude-plugins-official": False}}))
    assert _load()._governed_cwd_ok(tmp_path) is True


def test_governed_cwd_ok_false_when_settings_missing(tmp_path):
    assert _load()._governed_cwd_ok(tmp_path) is False


def test_governed_cwd_ok_false_when_ralph_not_disabled(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(
        {"enabledPlugins": {"ralph-loop@claude-plugins-official": True}}))
    assert _load()._governed_cwd_ok(tmp_path) is False


def test_governed_cwd_ok_false_on_malformed_settings(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("{ not json")
    assert _load()._governed_cwd_ok(tmp_path) is False

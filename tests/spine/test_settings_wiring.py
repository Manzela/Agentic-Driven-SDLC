# tests/spine/test_settings_wiring.py
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
S = json.load(open(ROOT / ".claude/settings.json"))

def test_all_six_events_registered():
    assert set(S["hooks"]) == {"SessionStart","PreToolUse","PostToolUse","SubagentStop","Stop","PreCompact"}

def test_ralph_disabled_project_scoped():
    assert S["enabledPlugins"]["ralph-loop@claude-plugins-official"] is False

def test_commands_are_project_dir_relative():
    cmds = [h["command"] for ev in S["hooks"].values() for g in ev for h in g["hooks"]]
    assert cmds and all("${CLAUDE_PROJECT_DIR}" in c for c in cmds)

def test_canary_env_present():
    assert "SPINE_REQUIRED_EVENTS" in S["env"] and "SPINE_HOOK_TELEMETRY" in S["env"]

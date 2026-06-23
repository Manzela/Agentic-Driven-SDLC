import importlib.util, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    spec = importlib.util.spec_from_file_location("ssh", ROOT/".claude/hooks/session_start_hook.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_green_when_all_events_point_at_spine():
    m = _load()
    settings = {"enabledPlugins":{"ralph-loop@claude-plugins-official":False},
        "hooks":{e:[{"hooks":[{"type":"command","command":f"python3 ${{CLAUDE_PROJECT_DIR}}/.claude/hooks/{s}"}]}]
                 for e,s in [("PreToolUse","pre_tool_use_hook.py"),("PostToolUse","post_tool_use_hook.py"),
                             ("Stop","stop_hook.py"),("SubagentStop","subagent_stop_hook.py"),
                             ("SessionStart","session_start_hook.py"),("PreCompact","pre_compact_hook.py")]}}
    st = m.spine_status(settings, list(settings["hooks"]),
                        {"PreToolUse":"pre_tool_use_hook.py","PostToolUse":"post_tool_use_hook.py",
                         "Stop":"stop_hook.py","SubagentStop":"subagent_stop_hook.py",
                         "SessionStart":"session_start_hook.py","PreCompact":"pre_compact_hook.py"},
                        "ralph-loop@claude-plugins-official")
    assert st["ok"] and not st["missing"] and not st["ralph_shadow_risk"]

def test_red_when_ralph_not_disabled_and_stop_event_missing():
    m = _load()
    settings = {"hooks":{"PreToolUse":[{"hooks":[{"type":"command","command":"x/pre_tool_use_hook.py"}]}]}}
    st = m.spine_status(settings, ["PreToolUse","Stop"], {"Stop":"stop_hook.py","PreToolUse":"pre_tool_use_hook.py"},
                        "ralph-loop@claude-plugins-official")
    assert not st["ok"] and "Stop" in st["missing"] and st["ralph_shadow_risk"]

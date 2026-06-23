"""Independent verifier tests for the flagd agent kill-switch
(S-flagd_killswitch).

REQ-CTRL-001 / Requirement 32 / task 55 -- the OpenFeature/flagd agent
kill-switch. flagd source: flagd/flags.json ; client: tools/kill_switch.py.

Written independently of the implementer. The contract under test (per the
verifier brief):

  * kill-switch OFF and the capability's own flag ON-enabled (i.e. OFF kill)
        -> is_capability_enabled is True for that capability
  * kill-switch ON (global kill.all == True)
        -> is_capability_enabled is False for EVERY gated capability
  * a single capability's kill flag ON (kill.<cap> == True), kill.all OFF
        -> only THAT capability is False; the others stay True
  * load_flags() parses the on-disk flagd/flags.json, and the
        "agent-kill-switch" flag -- which maps onto the global kill.all key --
        exists in the parsed config.

These tests treat tools/kill_switch.py as a black box: they build flag dicts /
read the real flagd config and assert the resolved enabled/disabled booleans.
"""
import json
from pathlib import Path

import pytest

from tools.kill_switch import (
    GATED_CAPABILITIES,
    GLOBAL_KILL_FLAG,
    KILL_FLAG_PREFIX,
    is_capability_enabled,
    load_flags,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FLAGS_PATH = REPO_ROOT / "flagd" / "flags.json"

# The prompt's "agent-kill-switch" boolean maps onto the global master kill
# flag key. Pin the mapping so a rename of the key is caught here.
AGENT_KILL_SWITCH_KEY = "kill.all"


def _all_off() -> dict:
    """A resolved-flag dict with every kill flag explicitly OFF (False)."""
    flags = {GLOBAL_KILL_FLAG: False}
    for cap in GATED_CAPABILITIES:
        flags[KILL_FLAG_PREFIX + cap] = False
    return flags


# ---------------------------------------------------------------------------
# Contract 1: kill-switch OFF + capability flag OFF (enabled) -> True
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("capability", GATED_CAPABILITIES)
def test_killswitch_off_and_capability_on_is_enabled(capability):
    flags = _all_off()
    assert is_capability_enabled(capability, flags) is True


# ---------------------------------------------------------------------------
# Contract 2: kill-switch ON -> every capability disabled (False)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("capability", GATED_CAPABILITIES)
def test_global_killswitch_on_disables_every_capability(capability):
    flags = _all_off()
    flags[GLOBAL_KILL_FLAG] = True  # flip the global master kill-switch ON
    assert is_capability_enabled(capability, flags) is False


def test_global_killswitch_on_disables_all_capabilities_collectively():
    flags = _all_off()
    flags[GLOBAL_KILL_FLAG] = True
    results = {
        cap: is_capability_enabled(cap, flags) for cap in GATED_CAPABILITIES
    }
    assert results == {cap: False for cap in GATED_CAPABILITIES}


# ---------------------------------------------------------------------------
# Contract 3: a single capability's kill flag ON -> only that one is False
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("target", GATED_CAPABILITIES)
def test_per_capability_flag_disables_only_that_capability(target):
    flags = _all_off()
    flags[KILL_FLAG_PREFIX + target] = True  # ON => disable just `target`

    # The targeted capability is disabled...
    assert is_capability_enabled(target, flags) is False
    # ...and every OTHER capability remains enabled.
    for other in GATED_CAPABILITIES:
        if other == target:
            continue
        assert is_capability_enabled(other, flags) is True


# ---------------------------------------------------------------------------
# Contract 4: load_flags parses flagd/flags.json and the kill-switch exists
# ---------------------------------------------------------------------------
def test_flags_json_exists_and_is_valid_json():
    assert FLAGS_PATH.is_file(), f"missing flagd config: {FLAGS_PATH}"
    doc = json.loads(FLAGS_PATH.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    assert isinstance(doc.get("flags"), dict) and doc["flags"], (
        "flagd config has no 'flags' object"
    )


def test_load_flags_parses_config_and_agent_kill_switch_exists():
    resolved = load_flags(FLAGS_PATH)
    assert isinstance(resolved, dict)
    # The "agent-kill-switch" boolean -> kill.all key must be present...
    assert AGENT_KILL_SWITCH_KEY in resolved, (
        f"'agent-kill-switch' flag ({AGENT_KILL_SWITCH_KEY}) not parsed "
        f"from {FLAGS_PATH}; got keys {sorted(resolved)}"
    )
    # ...and it is identical to the module's own GLOBAL_KILL_FLAG constant.
    assert GLOBAL_KILL_FLAG == AGENT_KILL_SWITCH_KEY
    # Default state ships OFF (False) -> enabled-by-default.
    assert resolved[AGENT_KILL_SWITCH_KEY] is False


def test_default_config_leaves_all_capabilities_enabled():
    """End-to-end: the shipped config (all kills default OFF) must leave every
    gated capability ENABLED."""
    resolved = load_flags(FLAGS_PATH)
    for cap in GATED_CAPABILITIES:
        assert is_capability_enabled(cap, resolved) is True, (
            f"{cap} unexpectedly disabled under default flagd config"
        )

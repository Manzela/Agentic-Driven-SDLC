"""kill_switch.py -- OpenFeature/flagd agent kill-switch client wrapper.

Spec: .kiro/specs/spec-to-evidence-control/design.md, "Agent Kill-Switch
(REQ-CTRL-001)" subsection; .kiro/specs/spec-to-evidence-control/tasks.md task 57
(and the kill-switch instrumentability notes on task 10.2).
Requirements: REQ-CTRL-001 / Requirement 32 (32.1, 32.2, 32.3) ; REQ-GATE-005
(ambiguous/unreachable states resolve to BLOCKED, not passed).

Each agent entry point (initializer / implementer / verifier / research) QUERIES
the kill-switch at START-OF-TURN. A capability whose kill flag is effectively set
HARD-REFUSES -- operationally "disabled" -- analogous to a PreToolUse exit-2
block (design.md Agent Kill-Switch (a)).

Flag model (design.md Agent Kill-Switch (b)):
  - ``kill.<capability>``  per-capability boolean kill flag. ``true`` => that
    capability is DISABLED. Default ``false`` (OFF) => ENABLED.
  - ``kill.all``           global master kill-switch (the prompt's
    "agent-kill-switch" boolean). ``true`` => EVERY capability is DISABLED.

A capability is therefore ENABLED iff BOTH ``kill.all`` is off AND its own
``kill.<capability>`` is off. Equivalently it is DISABLED when the kill-switch
(``kill.all``) is on OR the capability's kill flag is on.

Fail-closed (design.md Agent Kill-Switch (d) / REQ-GATE-005): when the flagd
source is UNREACHABLE -- modeled here as ``flags`` being ``None`` or otherwise
unusable -- the capability resolves to DISABLED, never enabled. The kill-switch
never fails open.

This module is PURE STDLIB so the unit is testable without a live flagd server
(no ``openfeature``/``flagd`` runtime dependency required). In production the
same flag values arrive from the flagd gRPC-streaming provider (DEFAULT) or the
file-based provider (≤ 30 s poll) per design.md Agent Kill-Switch (c); this
wrapper takes the already-resolved flag dict and applies the kill semantics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

__all__ = [
    "GLOBAL_KILL_FLAG",
    "KILL_FLAG_PREFIX",
    "GATED_CAPABILITIES",
    "is_capability_enabled",
    "load_flags",
]

# Global master kill-switch flag key ("agent-kill-switch"): when on, ALL gated
# capabilities are disabled (design.md Agent Kill-Switch (b), "plus a global
# kill.all").
GLOBAL_KILL_FLAG = "kill.all"

# Per-capability kill flags are named ``kill.<capability>``.
KILL_FLAG_PREFIX = "kill."

# The four kill-switchable agent entry points (design.md Agent Kill-Switch (a)).
GATED_CAPABILITIES = ("initializer", "implementer", "verifier", "research")


def _coerce_flag(value: Any) -> Optional[bool]:
    """Coerce a resolved flag value into a strict boolean, or ``None`` if it is
    missing/unusable.

    flagd flag values resolve to JSON booleans, but a resolved-flag dict that
    came from a config file may carry the variant value in a few shapes. We
    accept only values that UNAMBIGUOUSLY mean true/false; anything else
    (``None``, a non-boolean, a malformed entry) returns ``None`` so the caller
    can treat ambiguity as fail-closed.

    Accepts: ``bool``; the strings ``"true"``/``"false"`` and ``"on"``/``"off"``
    (case-insensitive) -- the latter mirroring the flagd variant keys in
    ``flagd/flags.json``.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in ("true", "on"):
            return True
        if norm in ("false", "off"):
            return False
    return None


def _flag_is_set(flags: Dict[str, Any], key: str) -> Optional[bool]:
    """Return the strict boolean value of ``key`` in ``flags``.

    Returns ``None`` when the key is ABSENT. An absent per-capability or global
    kill flag is NOT itself an unreachable-source condition: if the flag dict is
    present and simply does not name this flag, the flag is treated as OFF (its
    flagd ``defaultVariant`` is ``off``). The fail-closed path is reserved for an
    UNUSABLE flag SOURCE (``flags is None``), handled in ``is_capability_enabled``.

    A flag that is PRESENT but carries a non-boolean / malformed value coerces to
    ``None`` here and is treated as fail-closed (set) by the caller, because we
    cannot prove the capability is permitted.
    """
    if key not in flags:
        return None
    return _coerce_flag(flags[key])


def is_capability_enabled(capability: str, flags: Optional[Dict[str, Any]]) -> bool:
    """Return ``True`` iff ``capability`` is permitted to run, else ``False``.

    A capability is DISABLED (returns ``False``) when ANY of the following holds
    (fail-closed by construction -- design.md Agent Kill-Switch (a)/(b)/(d),
    REQ-CTRL-001, REQ-GATE-005):

      1. the flag SOURCE is unreachable/unusable (``flags`` is ``None`` or not a
         mapping)  -> fail-closed;
      2. the global ``kill.all`` flag is on;
      3. this capability's ``kill.<capability>`` flag is on;
      4. ``capability`` is not a recognized gated capability               (unknown
         capabilities are refused rather than implicitly allowed);
      5. a relevant flag is present but carries a malformed (non-boolean)
         value that cannot be proven OFF.

    Otherwise (source present, ``kill.all`` off, ``kill.<capability>`` off) the
    capability is ENABLED and this returns ``True``.

    Parameters
    ----------
    capability:
        One of ``GATED_CAPABILITIES`` (e.g. ``"implementer"``). The bare
        capability name -- NOT the ``kill.`` flag key.
    flags:
        The resolved flag dict mapping flag key -> boolean (as produced by
        ``load_flags`` or by an OpenFeature client). ``None`` models an
        unreachable flagd source and resolves fail-closed (disabled).
    """
    # (1) Unreachable / unusable source -> fail-closed (DISABLED).
    if not isinstance(flags, dict):
        return False

    # (4) Unknown capability -> refuse (DISABLED). Only the four named agent
    # entry points are kill-switchable; anything else is not a permitted gated
    # capability and is fail-closed.
    if capability not in GATED_CAPABILITIES:
        return False

    # (2) Global master kill-switch. Present-and-on, or present-but-malformed,
    # both disable; absent (None) is treated as off.
    global_kill = _flag_is_set(flags, GLOBAL_KILL_FLAG)
    if global_kill is True:
        return False
    if GLOBAL_KILL_FLAG in flags and global_kill is None:
        # Present but unparseable -> cannot prove OFF -> fail-closed.
        return False

    # (3) Per-capability kill flag.
    cap_flag_key = KILL_FLAG_PREFIX + capability
    cap_kill = _flag_is_set(flags, cap_flag_key)
    if cap_kill is True:
        return False
    if cap_flag_key in flags and cap_kill is None:
        # Present but unparseable -> fail-closed.
        return False

    # kill.all off (or absent) AND kill.<capability> off (or absent) -> ENABLED.
    return True


def _resolve_default_value(flag_def: Dict[str, Any]) -> Optional[bool]:
    """Resolve a single flagd flag definition to its effective boolean value.

    Honors the flagd flag-config shape used in ``flagd/flags.json``:
    ``{"state": "...", "variants": {...}, "defaultVariant": "..."}``. A flag whose
    ``state`` is not ``"ENABLED"`` (e.g. ``"DISABLED"``) is treated by flagd as
    not served; we resolve such a flag to ``None`` so the kill semantics fall
    back to the flag's ABSENCE (treated as OFF) rather than guessing.

    Returns the boolean value the flag's ``defaultVariant`` points at, or
    ``None`` when it cannot be resolved.
    """
    if not isinstance(flag_def, dict):
        return None
    if flag_def.get("state") not in (None, "ENABLED"):
        return None
    variants = flag_def.get("variants")
    default_variant = flag_def.get("defaultVariant")
    if isinstance(variants, dict) and default_variant in variants:
        return _coerce_flag(variants[default_variant])
    return None


def load_flags(path: str | Path) -> Dict[str, bool]:
    """Read ``flagd/flags.json`` and return a resolved ``{flag_key: bool}`` dict.

    This reads the flagd flag-config file and resolves each flag to the boolean
    value of its ``defaultVariant`` -- the static "no targeting context" value,
    which is exactly the start-of-turn kill state the wrapper checks. Flags that
    cannot be resolved to a boolean (non-ENABLED state, missing/unknown
    ``defaultVariant``, non-boolean variant value) are OMITTED from the result;
    an omitted kill flag is read as OFF by ``is_capability_enabled`` (its flagd
    default is ``off``), which is the correct enabled-by-default behavior for an
    absent kill flag.

    The returned dict is the input ``flags`` argument for
    ``is_capability_enabled``.

    Raises ``FileNotFoundError`` if ``path`` does not exist and
    ``json.JSONDecodeError`` (a ``ValueError`` subclass) if the file is not valid
    JSON -- callers that want fail-closed behavior on a missing/corrupt source
    should catch these and pass ``flags=None`` (or ``{}``) to
    ``is_capability_enabled``, which then resolves DISABLED for any real kill flag
    that was expected.
    """
    raw = Path(path).read_text(encoding="utf-8")
    doc = json.loads(raw)
    resolved: Dict[str, bool] = {}
    flags_obj = doc.get("flags") if isinstance(doc, dict) else None
    if not isinstance(flags_obj, dict):
        return resolved
    for key, flag_def in flags_obj.items():
        value = _resolve_default_value(flag_def)
        if value is not None:
            resolved[key] = value
    return resolved


if __name__ == "__main__":  # pragma: no cover - manual smoke
    import sys

    _here = Path(__file__).resolve().parent.parent
    _default_path = _here / "flagd" / "flags.json"
    _path = Path(sys.argv[1]) if len(sys.argv) > 1 else _default_path
    try:
        _flags = load_flags(_path)
        _source_ok = True
    except (FileNotFoundError, ValueError):
        _flags = None
        _source_ok = False
    print(f"flagd source: {_path}  reachable={_source_ok}")
    print(f"resolved flags: {_flags}")
    for _cap in GATED_CAPABILITIES:
        print(f"  {_cap:>12}: enabled={is_capability_enabled(_cap, _flags)}")

"""coverage.py — canonical coverage-model helpers: transitions, authority, query.

Single-sources the rules the hooks and the OPA gate rely on:
  * ALLOWED_TRANSITIONS — the only legal status moves.
  * field authority (fix #4) — status writable only by the verifier; in_scope
    only by a human-signed change.
  * completion query — has_unproven_in_scope / is_complete.
Pure stdlib; importable and side-effect free.
"""
from __future__ import annotations

import json
from pathlib import Path

ALLOWED_TRANSITIONS = {
    ("unproven", "proven"),
    ("unproven", "failed"),
    ("failed", "unproven"),
    ("proven", "unproven"),  # amendment re-entry only
}
VERIFIER_AGENT = "verifier.md"


class TransitionError(Exception): ...
class AuthorityError(Exception): ...


def load(path) -> dict:
    return json.loads(Path(path).read_text())


def in_scope_items(model: dict) -> list[dict]:
    return [i for i in model.get("items", []) if i.get("in_scope")]


def has_unproven_in_scope(model: dict) -> bool:
    return any(i.get("status") != "proven" for i in in_scope_items(model))


def is_complete(model: dict) -> bool:
    items = in_scope_items(model)
    return bool(items) and not has_unproven_in_scope(model)


def assert_transition(frm: str, to: str) -> None:
    if (frm, to) not in ALLOWED_TRANSITIONS:
        raise TransitionError(f"{frm}->{to} is not an allowed transition")


def assert_field_authority(*, field: str, actor_agent: str, human_signed: bool) -> None:
    if field == "status":
        if actor_agent != VERIFIER_AGENT:
            raise AuthorityError(f"status is writable only by {VERIFIER_AGENT}")
    elif field == "in_scope":
        if not human_signed:
            raise AuthorityError("in_scope is mutable only via a human-signed change")
    else:
        raise AuthorityError(f"unknown protected field: {field}")

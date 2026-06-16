"""state_integrity.py — recompute the resumed-state hash on SessionStart.

Phase-2 component for **REQ-STATE-005** (Requirement 23, Resumed-State
Integrity; design.md Component Inventory row `state_integrity.py`; CHECK-11).
The sole guard against a corrupted/false resume: it deterministically hashes
the durable resume-state byte-set so SessionStart can compare its recomputation
against the recorded baseline (`run_state.resume_state_hash`) and write the
non-blocking `run_state.resume_integrity_ok` flag. The exit-2 block is owned by
the SEPARATE PreToolUse integrity guard (task 49.1) — this module only computes
the hash and the equality verdict; it never blocks.

Hash spec (canonical, per design.md "Property 26: Resumed-State Integrity",
single source of truth):

- **Byte-set hashed:** the canonical JSON projection of the in-scope
  `feature_list.json` items — the
  ``(id, type, priority, sorted(dependencies), acceptance_criteria,
  in_scope, status)`` projection, sorted by ``id``, deterministic JSON —
  CONCATENATED with the named `run_state` fields
  ``(phase, current_item_id, iteration_count, violation_count,
  last_commit_sha)``. Volatile fields (``updated_at``, ``token_cost_usd``,
  ``stop_hook_active``) are EXCLUDED.
- **Algorithm:** ``sha256`` — consistent with the Evidence_Record
  ``output_hash`` and ``gate_audit_log`` hash-chain conventions.
- **Determinism:** ``json.dumps`` with ``sort_keys=True`` and compact
  separators; the in-scope item list is sorted by ``id`` and dependency
  lists are sorted, so the digest is a pure function of the logical state
  (insertion order, whitespace, and dict key order never perturb it).

The public surface required by the task / SessionStart wiring:

    compute_state_hash(git_status, progress, feature_list) -> str
    check_resume_integrity(stored_hash, git_status, progress, feature_list) -> bool

`compute_state_hash` is the deterministic sha256 over the canonical
serialization of the run-state inputs; `check_resume_integrity` is
``True`` iff a fresh recomputation equals the stored baseline (this is the
``resume_integrity_ok`` verdict SessionStart writes).

PURE STDLIB (``hashlib``, ``json``).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

__all__ = [
    "FEATURE_PROJECTION_KEYS",
    "RUN_STATE_KEYS",
    "canonical_state_repr",
    "compute_state_hash",
    "check_resume_integrity",
]

# The exact, ordered feature-item projection pinned by Property 26. Only these
# keys participate in the hash; everything else on a feature item (evidence
# blobs, timestamps, feature_list_sha, etc.) is excluded so the digest reflects
# the LOGICAL resume state, not volatile bookkeeping.
FEATURE_PROJECTION_KEYS = (
    "id",
    "type",
    "priority",
    "dependencies",        # sorted before hashing
    "acceptance_criteria",
    "in_scope",
    "status",
)

# The named run_state fields concatenated after the feature projection. The
# volatile fields (updated_at, token_cost_usd, stop_hook_active) are pointedly
# NOT in this set — they change every tick and would make a faithful resume
# spuriously mismatch.
RUN_STATE_KEYS = (
    "phase",
    "current_item_id",
    "iteration_count",
    "violation_count",
    "last_commit_sha",
)


def _project_feature_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Project one feature item down to the Property-26 key-set.

    ``dependencies`` is sorted so dependency-list ORDER never perturbs the
    digest (it is a set semantically). Missing keys project to ``None`` so a
    sparse item hashes deterministically rather than raising — the absence is
    itself part of the state and must hash stably.
    """
    projected: Dict[str, Any] = {}
    for key in FEATURE_PROJECTION_KEYS:
        value = item.get(key)
        if key == "dependencies":
            # Sort deterministically; tolerate scalars/None by coercing to a
            # list first. ``sorted`` over str() keeps mixed types ordered.
            deps: List[Any]
            if value is None:
                deps = []
            elif isinstance(value, (list, tuple, set)):
                deps = list(value)
            else:
                deps = [value]
            value = sorted(deps, key=lambda d: json.dumps(d, sort_keys=True))
        projected[key] = value
    return projected


def _extract_in_scope_items(feature_list: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pull the in-scope feature items out of a ``feature_list.json`` mapping.

    Accepts both the wrapped shape ``{"items": [...]}`` (canonical
    ``feature_list.json``) and a bare ``{id: item}`` / ``[item, ...]`` shape so
    the function is robust to how the caller hands the model in. Only items
    whose ``in_scope`` is truthy participate — Property 26 hashes the
    *in-scope* projection. Items are sorted by ``id`` for determinism.
    """
    if isinstance(feature_list, dict) and "items" in feature_list:
        raw_items = feature_list["items"]
    else:
        raw_items = feature_list

    items: List[Dict[str, Any]]
    if isinstance(raw_items, dict):
        items = [v for v in raw_items.values() if isinstance(v, dict)]
    elif isinstance(raw_items, (list, tuple)):
        items = [v for v in raw_items if isinstance(v, dict)]
    else:
        items = []

    in_scope = [it for it in items if it.get("in_scope")]
    in_scope.sort(key=lambda it: str(it.get("id", "")))
    return in_scope


def canonical_state_repr(
    git_status: str,
    progress: str,
    feature_list: Dict[str, Any],
) -> str:
    """Build the canonical, deterministic string serialization of resume state.

    This is the exact byte-set the resumed-state hash is taken over. It is
    exposed (not just inlined into ``compute_state_hash``) so tests and the
    operator ``--reconcile`` path can inspect WHAT was hashed, and so the
    SessionStart hook and any verifier share one serialization.

    The three task-signature inputs map onto the Property-26 byte-set as:

    - ``feature_list``  → the in-scope feature-item projection.
    - ``progress``      → the durable ``run_state`` fields (the
      ``claude-progress`` durable mirror SessionStart loads); if a JSON object
      is supplied its named ``RUN_STATE_KEYS`` are projected, otherwise the
      raw progress string is carried verbatim.
    - ``git_status``    → the working-tree/commit context carried verbatim so
      a resume onto a divergent tree is detectable.

    Determinism guarantees: ``sort_keys=True`` + compact separators, in-scope
    items sorted by ``id``, dependency lists sorted. Insertion order and
    whitespace never affect the result.
    """
    projected_items = [_project_feature_item(it) for it in _extract_in_scope_items(feature_list)]

    # ``progress`` may arrive as a JSON-encoded run_state object (the durable
    # mirror) or as an opaque progress string. Project the named run_state
    # fields when it parses to an object; otherwise carry the raw text.
    run_state_repr: Any
    parsed_progress: Any = None
    if isinstance(progress, str):
        try:
            parsed_progress = json.loads(progress)
        except (ValueError, TypeError):
            parsed_progress = None
    elif isinstance(progress, dict):
        parsed_progress = progress

    if isinstance(parsed_progress, dict):
        run_state_repr = {k: parsed_progress.get(k) for k in RUN_STATE_KEYS}
    else:
        run_state_repr = progress

    canonical = {
        "feature_items": projected_items,
        "run_state": run_state_repr,
        "git_status": git_status,
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_state_hash(
    git_status: str,
    progress: str,
    feature_list: Dict[str, Any],
) -> str:
    """Return the deterministic sha256 hex digest of the resumed-state byte-set.

    Pure function of the logical resume state: identical inputs (modulo
    insertion order, whitespace, and dependency-list order) always yield the
    identical 64-char lowercase hex digest. This is the hash SessionStart
    recomputes and the value persisted in ``run_state.resume_state_hash``.
    """
    canonical = canonical_state_repr(git_status, progress, feature_list)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def check_resume_integrity(
    stored_hash: str,
    git_status: str,
    progress: str,
    feature_list: Dict[str, Any],
) -> bool:
    """Return ``True`` iff the recomputed state hash equals ``stored_hash``.

    This is the ``resume_integrity_ok`` verdict the SessionStart hook writes:
    equality → the resume faithfully reproduces the recorded durable state →
    ``True``; any mismatch (corrupted/false resumption) → ``False``. A
    ``None``/empty ``stored_hash`` (no recorded baseline — a fresh, non-resumed
    session) is NOT this function's concern: per the design's first-run rule,
    SessionStart sets ``resume_integrity_ok=TRUE`` when there is no baseline.
    This predicate is strictly the recorded-vs-recomputed equality test and
    returns ``False`` for a missing baseline; the no-baseline ALLOW is decided
    by the caller, faithful to Property 26.
    """
    if not stored_hash:
        return False
    return compute_state_hash(git_status, progress, feature_list) == str(stored_hash)

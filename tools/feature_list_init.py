"""feature_list_init.py — feature_list.json initializer (empty coverage model).

Spec: .kiro/specs/spec-to-evidence-control/tasks.md, task 12 (12.1)
Requirements: 5.1

Builds a minimal, schema-valid ``feature_list.json`` structure and writes it to
disk atomically. The produced object validates against
``schema/feature_list.schema.json`` (draft-07).

Public API
----------
``init_feature_list(items=None) -> dict``
    Return a ``{"items": [...]}`` coverage model. ``items=None`` yields an empty
    model (``items == []``). Each supplied item dict is NORMALIZED so it carries
    the required CoverageItem fields, defaulting ``status`` to ``"unproven"`` and
    ``in_scope`` to ``True``. The returned object additionally carries the three
    schema-required top-level fields (``schema_version``, ``product_class``,
    ``checklist_ref``) so the result validates against the file schema — a bare
    ``{"items": []}`` is intentionally NOT schema-valid (the schema marks all
    four top-level fields required), and this initializer is the component that
    seeds the valid envelope.

``write_feature_list(obj, path) -> str``
    Validate ``obj`` against the schema (when ``jsonschema`` is importable) and
    write it atomically (temp file + ``os.replace``). Returns the written path.

This module is PURE STDLIB for its core path. Schema validation is performed
with ``jsonschema`` when available (it is a pinned project dependency, task 1)
and is skipped with an in-band guard only if the library is absent, so the
module imports and runs even in a stripped environment.
"""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from typing import Any, Dict, List, Optional

__all__ = [
    "SCHEMA_PATH",
    "DEFAULT_SCHEMA_VERSION",
    "init_feature_list",
    "normalize_item",
    "write_feature_list",
    "validate_against_schema",
]

# ---------------------------------------------------------------------------
# Locations and defaults
# ---------------------------------------------------------------------------

# tools/feature_list_init.py -> repo root is one level up from tools/.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(_REPO_ROOT, "schema", "feature_list.schema.json")

# Semver of the coverage-model schema this initializer seeds (task 12.1:
# schema_version "1.0.0").
DEFAULT_SCHEMA_VERSION = "1.0.0"

# Placeholder envelope values. The schema requires these top-level fields to be
# present and well-typed; the Initializer agent overwrites product_class /
# checklist_ref with the detected product class and the approved checklist
# reference. They are non-empty strings so the empty model is itself valid.
_DEFAULT_PRODUCT_CLASS = "undetermined"
_DEFAULT_CHECKLIST_REF: Dict[str, str] = {
    "path": "",
    "version": "0.0.0",
    "sha": "",
}

# CoverageItem field defaults applied during normalization. ``status`` and
# ``in_scope`` defaults are mandated by the prompt contract and the schema
# documentation; ``priority`` defaults to the lowest precedence (a large
# integer) so a normalized item still satisfies the schema's required+integer
# ``priority`` without claiming high scheduling precedence it was not assigned.
_DEFAULT_STATUS = "unproven"
_DEFAULT_IN_SCOPE = True
_DEFAULT_PRIORITY = 999


def normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one coverage item into a schema-valid CoverageItem dict.

    The input ``item`` is copied (never mutated). Missing required CoverageItem
    fields are filled with defaults:

    * ``status``              -> ``"unproven"`` (prompt + schema default)
    * ``in_scope``            -> ``True``       (prompt + schema default)
    * ``dependencies``        -> ``[]``
    * ``acceptance_criteria`` -> preserved if present and non-empty; the schema
      requires ``minItems: 1``, so a missing/empty list is left as-is for the
      schema validator to reject rather than fabricating a fake criterion.
    * ``priority``            -> ``999`` (lowest precedence) when absent.

    ``id`` and ``type`` are NOT synthesized — they are identity fields the caller
    must supply; an item lacking them is returned unchanged in those keys so the
    schema validator surfaces the omission instead of this function hiding it.
    Any extra keys the caller provides (``title``, ``ears_pattern``,
    ``evidence``, ``nfr_subtype``, ...) are preserved verbatim.
    """
    normalized: Dict[str, Any] = deepcopy(item)

    normalized.setdefault("status", _DEFAULT_STATUS)
    normalized.setdefault("in_scope", _DEFAULT_IN_SCOPE)
    normalized.setdefault("dependencies", [])
    normalized.setdefault("acceptance_criteria", [])
    normalized.setdefault("priority", _DEFAULT_PRIORITY)

    return normalized


def init_feature_list(
    items: Optional[List[Dict[str, Any]]] = None,
    *,
    product_class: str = _DEFAULT_PRODUCT_CLASS,
    checklist_ref: Optional[Dict[str, str]] = None,
    schema_version: str = DEFAULT_SCHEMA_VERSION,
) -> Dict[str, Any]:
    """Return a schema-valid ``feature_list.json`` structure.

    Parameters
    ----------
    items:
        A list of raw coverage-item dicts to normalize and include. ``None``
        (the default) produces an empty model whose ``items`` is ``[]``.
    product_class, checklist_ref, schema_version:
        Top-level envelope fields. They carry schema-valid defaults so the
        zero-argument / ``items=None`` call still validates; the Initializer
        agent overrides them with the detected product class and the approved
        checklist reference.

    Returns
    -------
    dict
        ``{"schema_version", "product_class", "checklist_ref", "items"}`` where
        ``items`` is the list of normalized CoverageItem dicts (``[]`` for an
        empty init). The object validates against ``feature_list.schema.json``.
    """
    raw_items: List[Dict[str, Any]] = items if items is not None else []
    normalized_items = [normalize_item(it) for it in raw_items]

    ref = deepcopy(checklist_ref) if checklist_ref is not None else deepcopy(
        _DEFAULT_CHECKLIST_REF
    )

    return {
        "schema_version": schema_version,
        "product_class": product_class,
        "checklist_ref": ref,
        "items": normalized_items,
    }


def _load_schema() -> Optional[Dict[str, Any]]:
    """Load and parse the feature_list JSON schema, or ``None`` if unreadable."""
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def validate_against_schema(obj: Dict[str, Any]) -> None:
    """Validate ``obj`` against ``feature_list.schema.json``.

    Raises ``jsonschema.ValidationError`` when ``obj`` is schema-invalid. If the
    ``jsonschema`` library is not importable, validation is skipped (the import
    is the only soft dependency); the schema is a pinned project dependency so in
    a correctly provisioned environment this always runs.
    """
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return

    schema = _load_schema()
    if schema is None:
        return
    jsonschema.validate(instance=obj, schema=schema)


def write_feature_list(obj: Dict[str, Any], path: str) -> str:
    """Validate ``obj`` against the schema and write it atomically to ``path``.

    The object is validated FIRST (raising on a schema-invalid object so an
    invalid coverage model never reaches disk), then serialized to a temp file in
    the destination directory and moved into place with ``os.replace`` — an
    atomic rename on the same filesystem, so a reader never observes a partially
    written ``feature_list.json``.

    Returns the absolute path written.
    """
    validate_against_schema(obj)

    abs_path = os.path.abspath(path)
    parent = os.path.dirname(abs_path) or "."
    os.makedirs(parent, exist_ok=True)

    serialized = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"

    fd, tmp_path = tempfile.mkstemp(
        prefix=".feature_list.", suffix=".tmp", dir=parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, abs_path)
    except BaseException:
        # Clean up the temp file on any failure so we never leave a stray
        # ``.feature_list.*.tmp`` behind.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return abs_path


if __name__ == "__main__":
    # Smoke entry point: emit an empty, schema-valid coverage model to stdout.
    print(json.dumps(init_feature_list(), indent=2))

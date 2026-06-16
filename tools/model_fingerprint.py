"""model_fingerprint.py — stable fingerprint of the coverage MODEL.

The plan-approval freeze (gate #1) must bind the immutable shape of the
coverage model — the item set, types, priorities, dependencies, acceptance
criteria, and scope — NOT the mutable runtime fields (`status`, `evidence`)
that change as the build proves items. Hashing the whole file would make every
legitimate proven-flip look like coverage drift.

`fingerprint()` hashes a canonical projection (sorted by id, excluding
status/evidence/title), so:
  * adding/removing an item, changing its type/priority/deps/acceptance, or
    flipping `in_scope` -> CHANGES the fingerprint (requires re-approval);
  * proving an item (status unproven->proven + evidence) -> does NOT.
Pure stdlib.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

_FROZEN_FIELDS = ("id", "type", "nfr_subtype", "priority", "dependencies",
                  "acceptance_criteria", "in_scope")


def _projection(model: dict) -> list[dict]:
    rows = []
    for item in model.get("items", []):
        rows.append({k: item[k] for k in _FROZEN_FIELDS if k in item})
    rows.sort(key=lambda r: r["id"])
    return rows


def fingerprint(model: dict) -> str:
    canonical = json.dumps(_projection(model), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def fingerprint_file(path) -> str:
    return fingerprint(json.loads(Path(path).read_text()))


if __name__ == "__main__":
    import sys
    print(fingerprint_file(sys.argv[1] if len(sys.argv) > 1 else "apps/web/feature_list.json"))

"""opa_input.py — build the Conftest/OPA input document from the coverage model.

The coverage-gate CI check denies a merge when any in-scope item is unproven or
proven-without-evidence. This builder produces the {unproven_in_scope,
missing_evidence} document the Rego policy evaluates. Pure stdlib.
"""
from __future__ import annotations

import json
from pathlib import Path


def build_opa_input(feature_list_path) -> dict:
    model = json.loads(Path(feature_list_path).read_text())
    unproven, missing = [], []
    for i in model.get("items", []):
        if not i.get("in_scope"):
            continue
        if i.get("status") != "proven":
            unproven.append(i.get("id"))
        elif not i.get("evidence"):
            missing.append(i.get("id"))
    return {"unproven_in_scope": unproven, "missing_evidence": missing}

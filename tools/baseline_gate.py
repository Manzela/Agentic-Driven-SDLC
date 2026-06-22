"""baseline_gate.py — protected-baseline structural-integrity check (Phase A.5).

Closes Gemini RT-01 (coverage-model omission) and RT-02 (in-scope shrinking): the
agent controls the PR payload, so it can DELETE feature_list.json (making the gate
skip) or flip a target item to in_scope:false (excluding it from auditing). Neither
is caught by the evidence gate, which only inspects what the payload declares.

The fix: a TRUSTED baseline (dispatcher-owned, delivered out-of-band — NEVER from
the PR payload) declares which item ids are in-scope-required for this delivery.
This gate denies when the payload omits the model (a delivery was expected) or any
required item is missing / no longer in-scope. PHASE A.5: the baseline is trusted;
Phase B signs it. Pure stdlib; fails CLOSED.
"""
from __future__ import annotations


def baseline_gate(*, baseline: dict | None, feature_list: dict | None) -> dict:
    reasons: list[str] = []
    try:
        # No baseline (or an empty one) => no delivery expected => the existing
        # absent-input "pre-delivery skip" is safe. Allow.
        if not isinstance(baseline, dict):
            return {"deny": False, "reasons": []}
        required = baseline.get("required_in_scope")
        if required is None:
            return {"deny": False, "reasons": []}
        if not isinstance(required, list | tuple):
            return {"deny": True, "reasons": [
                "Merge denied: baseline.required_in_scope is not a list. Fail closed."]}
        required_set = {str(x) for x in required}
        if not required_set:
            return {"deny": False, "reasons": []}

        # A delivery IS expected. RT-01: the payload must carry the coverage model.
        if not isinstance(feature_list, dict):
            return {"deny": True, "reasons": [
                "Merge denied: a delivery is expected (baseline declares "
                f"{len(required_set)} required in-scope item(s)) but feature_list.json "
                "is absent or malformed. Fail closed (RT-01)."]}

        # RT-02: every required id must be present AND in_scope in the payload.
        # SECURITY: deduplicate by id before building the in-scope set. An agent can
        # include the same id twice — once with in_scope:false (the real item, evading
        # auditing) and once with in_scope:true (a ghost copy with fabricated evidence).
        # Without deduplication the ghost's True entry would satisfy the gate while the
        # real item is never audited. We resolve the id on FIRST OCCURRENCE in the
        # items list: if an id appears multiple times and the first occurrence has
        # in_scope:false, that id is treated as out-of-scope, regardless of any later
        # ghost entry. This closes the duplicate-id bypass for RT-02.
        seen_ids: set = set()
        payload_in_scope: set = set()
        for item in feature_list.get("items", []):
            iid = str(item.get("id"))
            if iid in seen_ids:
                continue  # first-occurrence wins; ignore duplicates
            seen_ids.add(iid)
            if item.get("in_scope"):
                payload_in_scope.add(iid)
        for rid in sorted(required_set):
            if rid not in payload_in_scope:
                reasons.append(
                    f"Merge denied: baseline-required item {rid!r} is missing or no "
                    f"longer in_scope in feature_list.json (RT-02: in-scope shrinking).")
        return {"deny": bool(reasons), "reasons": reasons}
    except Exception as exc:  # noqa: BLE001 — fail closed.
        return {"deny": True, "reasons": [
            f"Merge denied: baseline_gate raised {type(exc).__name__}: {exc}. Fail closed."]}

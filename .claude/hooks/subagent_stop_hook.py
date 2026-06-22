#!/usr/bin/env python3
"""SubagentStop gate — accept a verifier result ONLY if it is independently honest.

Layers the actor-independence fixes on top of the existing four-field evidence
contract (tools/evidence_collector.validate_evidence_record):

  fix #1  actor_agent is the runtime-resolved identity, not the payload's claim.
  fix #2  verifier_session_id must be present and DISTINCT from implementer_session_id.
  fix #3  output_hash is RE-DERIVED from the captured artifact and must match
          (the gate verifies the proof; it does not trust the declared hash).
  + the record's actor must be the verifier, and a non-empty omission_declaration
    must enumerate uncovered scenario classes (Req 29 / Property 30).

PURE importable core (`evaluate`) + thin stdin shell (`main`). Fails closed:
any ambiguity or exception → block (exit 2).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# Import the existing four-field validator so the in-session gate and the record
# builder enforce exactly the same contract.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.evidence_collector import validate_evidence_record  # noqa: E402
from tools.spine_roles import VERIFIER_ROLE  # noqa: E402  (single-source role constant)


def _rederive(output: str) -> str:
    return "sha256:" + hashlib.sha256(output.encode("utf-8")).hexdigest()


def evaluate(record: dict, output: str, resolved_actor: str,
             omission_declaration: str | None) -> dict:
    """Decide whether to accept a verifier's proven-flip evidence.

    Parameters
    ----------
    record: the Evidence_Record the verifier submitted (with session ids).
    output: the raw artifact text the hash should be re-derived from (fix #3).
    resolved_actor: the runtime-stamped actor identity (from actor_identity).
    omission_declaration: the verifier's enumeration of uncovered scenarios.

    Returns {"decision": "approve"|"block", "reason": str}.
    """
    try:
        # (0) four-field completeness + format (existing contract).
        if not validate_evidence_record(record):
            return {"decision": "block", "reason": "evidence record incomplete or malformed"}

        # (fix #1) only the verifier may flip; the record's actor must equal the
        # runtime-resolved actor (no forged actor_agent promotes a self-grade).
        if resolved_actor != VERIFIER_ROLE:
            return {"decision": "block",
                    "reason": f"only {VERIFIER_ROLE} may flip to proven; resolved actor={resolved_actor}"}
        if record.get("actor_agent") != resolved_actor:
            return {"decision": "block",
                    "reason": "record actor_agent does not match the runtime-resolved actor (forgery)"}

        # (fix #2) verifier and implementer sessions must be present and distinct.
        vs = record.get("verifier_session_id")
        is_ = record.get("implementer_session_id")
        if not vs or not is_:
            return {"decision": "block",
                    "reason": "missing verifier_session_id / implementer_session_id"}
        if vs == is_:
            return {"decision": "block",
                    "reason": "verifier session must differ from implementer session (self-grading)"}

        # (fix #3) re-derive the hash from the captured artifact; trust bytes, not claims.
        if output is None:
            return {"decision": "block", "reason": "no captured artifact to re-derive output_hash"}
        if _rederive(output) != record.get("output_hash"):
            return {"decision": "block", "reason": "output_hash does not match re-derived artifact hash"}

        # omission declaration must be present and non-empty (Property 30).
        if not omission_declaration or not str(omission_declaration).strip():
            return {"decision": "block", "reason": "missing non-empty omission_declaration"}

        return {"decision": "approve", "reason": "evidence independently verified"}
    except Exception as exc:  # noqa: BLE001 — fail closed.
        return {"decision": "block", "reason": f"subagent_stop raised {type(exc).__name__}: {exc}"}


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print(json.dumps({"decision": "block", "reason": "unparseable event"}))
        return 2
    from tools.actor_identity import resolve_identity
    try:
        actor = resolve_identity(event).actor_agent
    except ValueError as exc:
        print(json.dumps({"decision": "block", "reason": str(exc)}))
        return 2
    ti = event.get("tool_input", event)
    # The evidence gate applies ONLY to a proven-flip submission (an event that
    # actually carries an Evidence_Record). An ordinary subagent finishing its
    # turn submits no evidence — there is nothing to gate, so it is allowed to
    # stop. Gating every SubagentStop would make it impossible for any non-flip
    # subagent (e.g. an implementer) to ever terminate.
    record = ti.get("evidence")
    if not record:
        return 0
    decision = evaluate(
        record=record,
        output=ti.get("output", ti.get("artifact")),
        resolved_actor=actor,
        omission_declaration=ti.get("omission_declaration"),
    )
    print(json.dumps(decision))
    return 0 if decision["decision"] == "approve" else 2


if __name__ == "__main__":
    sys.exit(main())

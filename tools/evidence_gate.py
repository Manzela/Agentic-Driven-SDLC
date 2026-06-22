"""evidence_gate.py — deterministic per-slice evidence gate (the source of truth).

Zero-trust: never trusts the `status` field. `proven` is acceptable only when a
durable Evidence_Record (a) is four-field valid, (b) has an output_hash that
RE-DERIVES from the captured artifact, and (c) carries DISTINCT implementer and
verifier session ids that BOTH appear in the dispatch ledger.

PHASE A: the ledger is TRUSTED (cryptographic signing is Phase B). Pure stdlib;
fails CLOSED (any error / ambiguity → reject).
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.coverage import in_scope_items  # noqa: E402
from tools.evidence_collector import validate_evidence_record  # noqa: E402

CODES = (
    "OK",
    "EVIDENCE_MISSING",
    "EVIDENCE_MALFORMED",
    "HASH_MISMATCH",
    "SESSION_MISSING",
    "SAME_SESSION",
    "SESSION_NOT_IN_LEDGER",
)


def _reject(code: str, reason: str) -> dict:
    return {"accepted": False, "code": code, "reason": reason}


def _rederive(artifact: str) -> str:
    return "sha256:" + hashlib.sha256(artifact.encode("utf-8")).hexdigest()


def _norm_session(s) -> str:
    """Normalise an UNTRUSTED session id for comparison: strip whitespace, REJECT
    non-ASCII (→ ""), then casefold.

    ASCII-only is enforced so this normalisation is IDENTICAL to the Rego twin
    (`_norm_session` in coverage_query.rego uses OPA `lower`; over ASCII,
    `lower` == Python `casefold`). A non-ASCII id — e.g. 'ß', which Python
    `casefold` would fold to 'ss' but Rego `lower` would NOT — normalises to ""
    in BOTH implementations and is treated as absent. This closes (a) the
    casefold/lower twin-drift and (b) the Unicode self-grade class, on top of the
    whitespace/case-variant near-duplicate class ('i' vs ' i ' vs 'I').
    """
    if not isinstance(s, str):
        return ""
    s = s.strip()
    if not s or not s.isascii():
        return ""
    return s.casefold()  # == lower() for ASCII; explicit about intent


def check_slice(
    *, evidence: dict | None, artifact: str | None, ledger: dict
) -> dict:
    """Accept/reject one proven item's evidence. Fails closed."""
    try:
        if not evidence:
            return _reject(
                "EVIDENCE_MISSING",
                "no Evidence_Record present for a proven item",
            )
        if not validate_evidence_record(evidence):
            return _reject(
                "EVIDENCE_MALFORMED",
                "Evidence_Record fails four-field validation",
            )
        # (b) independent hash re-derivation — trust bytes, not the declared hash.
        if artifact is None or _rederive(artifact) != evidence.get("output_hash"):
            return _reject(
                "HASH_MISMATCH",
                "output_hash does not re-derive from the captured artifact",
            )
        # (c) actor-separation from provenance fields + the (trusted) ledger.
        # Normalise BOTH sides before any comparison; a non-string, empty,
        # whitespace-only, or non-ASCII id normalises to "" and is treated as
        # absent (SESSION_MISSING) — never silently distinct.
        vs = _norm_session(evidence.get("verifier_session_id"))
        is_ = _norm_session(evidence.get("implementer_session_id"))
        if not vs or not is_:
            return _reject(
                "SESSION_MISSING",
                "evidence lacks a valid (non-empty, ASCII) verifier/implementer session id",
            )
        if vs == is_:
            return _reject(
                "SAME_SESSION",
                "verifier session equals implementer session (self-grading)",
            )
        # Normalise ledger entries for the same reason; "" never matches.
        valid = {_norm_session(s) for s in ledger.get("sessions", [])}
        valid.discard("")
        if vs not in valid or is_ not in valid:
            return _reject(
                "SESSION_NOT_IN_LEDGER",
                "a declared session id is not in the dispatch ledger",
            )
        return {"accepted": True, "code": "OK", "reason": "evidence independently verified"}
    except Exception as exc:  # noqa: BLE001 — fail closed.
        return _reject(
            "EVIDENCE_MALFORMED",
            f"evidence_gate raised {type(exc).__name__}: {exc}",
        )


def check_model(*, model: dict, ledger: dict, artifacts: dict) -> dict:
    """Run check_slice for every in-scope PROVEN item; collect rejections (by id).

    Fails CLOSED: a malformed `model` (not a dict, or `items` not a list of
    dicts) is a MODEL_MALFORMED reject — never a vacuous accept. A non-list
    `items` (e.g. a string) must NOT be treated as 'nothing to reject': an
    adversarial feature_list that silently passes is the exact hole this guards.

    REUSE: delegates in-scope filtering to tools.coverage.in_scope_items so
    that any future evolution of the in_scope semantics (e.g. requiring explicit
    True vs truthy) is single-sourced there, not diverged here.
    """
    try:
        if not isinstance(model, dict):
            return {
                "accepted": False,
                "rejections": [
                    {
                        "id": None,
                        "code": "MODEL_MALFORMED",
                        "reason": f"model is {type(model).__name__}, not a dict",
                    }
                ],
            }
        items = model.get("items", [])
        if not isinstance(items, list | tuple):
            return {
                "accepted": False,
                "rejections": [
                    {
                        "id": None,
                        "code": "MODEL_MALFORMED",
                        "reason": (
                            f"model['items'] is {type(items).__name__}, not a list"
                        ),
                    }
                ],
            }
        if any(not isinstance(i, dict) for i in items):
            return {
                "accepted": False,
                "rejections": [
                    {
                        "id": None,
                        "code": "MODEL_MALFORMED",
                        "reason": "model['items'] contains a non-dict element",
                    }
                ],
            }
        rejections = []
        # REUSE tools.coverage.in_scope_items — do not duplicate the filter inline.
        for item in sorted(
            in_scope_items(model), key=lambda i: str(i.get("id", ""))
        ):
            if item.get("status") != "proven":
                rejections.append(
                    {
                        "id": item.get("id"),
                        "code": "EVIDENCE_MISSING",
                        "reason": (
                            f"in-scope item is {item.get('status')!r}, not proven"
                        ),
                    }
                )
                continue
            r = check_slice(
                evidence=item.get("evidence"),
                artifact=artifacts.get(item.get("id")),
                ledger=ledger,
            )
            if not r["accepted"]:
                rejections.append({"id": item.get("id"), **r})
        return {"accepted": not rejections, "rejections": rejections}
    except Exception as exc:  # noqa: BLE001 — fail closed.
        return {
            "accepted": False,
            "rejections": [
                {
                    "id": None,
                    "code": "MODEL_MALFORMED",
                    "reason": f"check_model raised {type(exc).__name__}: {exc}",
                }
            ],
        }


# Action-directive remediation (each names the ONE sanctioned next step — the
# self-heal prompt fed back to the agent on a local reject).
_HEAL = {
    "EVIDENCE_MISSING": (
        "Produce a four-field Evidence_Record (test_file, test_name, output_hash,"
        " collected_at) for this item via the verifier before marking it proven."
    ),
    "EVIDENCE_MALFORMED": (
        "Re-emit the Evidence_Record with a valid output_hash ('sha256:'+64 lowercase"
        " hex) and a timezone-aware collected_at; do not hand-edit the hash."
    ),
    "HASH_MISMATCH": (
        "Re-run the verification and let the verifier rebuild output_hash from the"
        " ACTUAL captured artifact bytes; the declared hash must re-derive."
    ),
    "SESSION_MISSING": (
        "Have the verifier (a session distinct from the implementer) produce the"
        " evidence and stamp both session ids."
    ),
    "SAME_SESSION": (
        "Hand the item to the VERIFIER subagent — a session distinct from the"
        " implementer must produce the evidence; an implementer may not self-verify."
    ),
    "SESSION_NOT_IN_LEDGER": (
        "Use the real dispatched verifier/implementer sessions; a session id not in"
        " the dispatch ledger cannot be attested."
    ),
}


def self_heal_prompt(result: dict) -> str:
    return _HEAL.get(
        result.get("code", ""),
        "Resolve the evidence-gate rejection before re-attempting the proven transition.",
    )

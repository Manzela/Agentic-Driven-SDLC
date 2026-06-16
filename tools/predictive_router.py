"""predictive_router.py — OPTIONAL, OFF-GATE predictive next-step routing.

Requirement 19 (REQ-PRED-001..003) / Property 4. Phase 6.

Predictive routing is an *acceleration* feature: given a feature signature and
the historical outcomes of prior routing decisions, `predict_route` advises
which agent/model/context is most likely to succeed, so the orchestrator can
pre-warm that path. It is purely advisory — injected only as context (REQ-19.1,
e.g. a `UserPromptSubmit` / `SessionStart` hook or an MCP retrieve tool).

CRITICAL INVARIANT (Property 4 / REQ-19.2, Z3 CHECK-5):
  Predictions are ADVISORY ONLY and MUST NEVER gate. The completion gate's
  verdict (allow/block, COMPLETE/HANDOFF) is a pure function of the coverage
  facts (`items[].in_scope` / `items[].status` — see `coverage.is_complete`)
  and SHALL be identical regardless of the value, presence, or absence of any
  prediction. Predictions SHALL NOT emit gate decisions and gates SHALL NOT
  read predictions.

  `gate_decision_is_prediction_independent` is the runtime witness of that
  invariant: it re-evaluates a candidate `gate_fn` over the SAME coverage state
  under (a) the supplied prediction, (b) a battery of adversarially perturbed
  predictions, and (c) no prediction at all, and returns True only if every
  verdict is identical. The static design-time proof of the same property lives
  in `verification/formal_verification_merged.py::CHECK-5`; this function is its
  runtime mirror, usable in `test_completion_gate.py`.

Pure stdlib; importable and side-effect free.
"""
from __future__ import annotations

import copy
from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: Feature signature
# ─────────────────────────────────────────────────────────────────────────────

# Fields of a history record / feature dict that characterize a routing context.
# A "feature signature" buckets historical outcomes so we can pick the candidate
# with the best historical success rate for *this kind* of work.
_SIGNATURE_FIELDS = ("type", "nfr_subtype", "priority", "phase", "baseline")


def _signature(features: Mapping[str, Any] | None) -> tuple:
    """A hashable, order-stable signature of the routing context.

    Missing fields are normalized to None so partial feature dicts still bucket
    deterministically. Returns () for an empty/None features mapping.
    """
    if not features:
        return ()
    return tuple((k, features.get(k)) for k in _SIGNATURE_FIELDS)


def _record_signature(record: Mapping[str, Any]) -> tuple:
    """Signature of a history record, read from its own `features` sub-dict if
    present, else from the record's top-level fields."""
    feats = record.get("features")
    if isinstance(feats, Mapping):
        return _signature(feats)
    return _signature(record)


def _is_success(record: Mapping[str, Any]) -> bool:
    """A historical routing record counts as a success when it explicitly says
    so. Accepts `success: bool` or `outcome in {"proven","success","pass"}`."""
    if "success" in record:
        return bool(record["success"])
    outcome = str(record.get("outcome", "")).lower()
    return outcome in {"proven", "success", "pass", "passed", "allow", "complete"}


def _record_choice(record: Mapping[str, Any]) -> Any:
    """The candidate that a history record routed to."""
    for key in ("choice", "candidate", "agent", "model", "route"):
        if key in record:
            return record[key]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Advisory prediction (REQ-PRED-001/003)
# ─────────────────────────────────────────────────────────────────────────────

def predict_route(
    history: Sequence[Mapping[str, Any]],
    candidates: Sequence[Any],
    features: Mapping[str, Any] | None = None,
) -> dict:
    """Advise which candidate to route to, given historical outcomes.

    Picks the candidate with the best historical success rate for the current
    feature signature (falling back to the global success rate when there is no
    signature-specific history). Ties break deterministically by the candidate's
    order in `candidates`, so the result is reproducible.

    This output is ADVISORY ONLY (Property 4 / REQ-19.2). It carries no gate
    authority: nothing in the completion gate reads it, and feeding it (or any
    perturbation of it) to the gate cannot change a verdict — see
    `gate_decision_is_prediction_independent`.

    Returns: {"choice": str, "confidence": float in [0,1], "rationale": str}.
    A confidence of 0.0 with an empty choice signals "no candidates"; otherwise
    the first candidate is always a safe advisory default even with no history.
    """
    cand_list = list(candidates)
    if not cand_list:
        return {
            "choice": "",
            "confidence": 0.0,
            "rationale": "no candidates supplied; nothing to advise",
        }

    sig = _signature(features)

    # Tally (success, total) per candidate, for the matching signature and globally.
    sig_stats: dict[Any, list[int]] = defaultdict(lambda: [0, 0])      # [success, total]
    global_stats: dict[Any, list[int]] = defaultdict(lambda: [0, 0])

    for record in history or ():
        if not isinstance(record, Mapping):
            continue
        choice = _record_choice(record)
        if choice is None:
            continue
        ok = 1 if _is_success(record) else 0
        global_stats[choice][0] += ok
        global_stats[choice][1] += 1
        if sig and _record_signature(record) == sig:
            sig_stats[choice][0] += ok
            sig_stats[choice][1] += 1

    def _rate(stats: dict[Any, list[int]], cand: Any) -> tuple[float, int]:
        succ, total = stats.get(cand, (0, 0))
        if total == 0:
            return (0.0, 0)
        return (succ / total, total)

    # Score each candidate: prefer signature-specific history; fall back to global.
    best = None  # (candidate, confidence, rate, total, scope)
    for cand in cand_list:
        rate, total = _rate(sig_stats, cand)
        scope = "signature"
        if total == 0:
            rate, total = _rate(global_stats, cand)
            scope = "global"
        # Confidence is the observed success rate, damped by sample size so a
        # 1/1 record does not masquerade as certainty (Wilson-ish shrink).
        confidence = rate * (total / (total + 1.0)) if total else 0.0
        cand_score = (confidence, total)
        if best is None or cand_score > (best[1], best[3]):
            best = (cand, confidence, rate, total, scope)

    cand, confidence, rate, total, scope = best

    if total == 0:
        # No usable history for any candidate: advise the first candidate as a
        # neutral default, with zero confidence and an explicit rationale.
        return {
            "choice": str(cand_list[0]),
            "confidence": 0.0,
            "rationale": (
                "advisory: no historical outcomes for these candidates"
                + (f" at signature {sig}" if sig else "")
                + f"; defaulting to first candidate {cand_list[0]!r} (advisory only, off-gate)"
            ),
        }

    return {
        "choice": str(cand),
        "confidence": round(float(confidence), 6),
        "rationale": (
            f"advisory: {cand!r} has the best {scope} success rate "
            f"{rate:.2%} over {total} prior route(s)"
            + (f" matching signature {sig}" if scope == "signature" else "")
            + "; advisory only, never gates (Property 4 / REQ-19.2)"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Prediction-independence witness (Property 4 / REQ-19.2 / CHECK-5)
# ─────────────────────────────────────────────────────────────────────────────

# A sentinel distinct from any caller value, used to prove the gate behaves
# identically when no prediction object exists at all.
_NO_PREDICTION = object()


def _perturbations(prediction: Any) -> list[Any]:
    """A battery of prediction values to feed the gate alongside the original.

    The set includes the original, structurally-mutated copies (flipped choice /
    confidence / rationale), polar opposites, and the no-prediction sentinel.
    If the gate's verdict is constant across all of these for a fixed state,
    the gate provably does not depend on the prediction.
    """
    variants: list[Any] = [prediction, _NO_PREDICTION, None]

    # Generic opposites that exercise truthiness-based leaks.
    variants.extend([
        True, False, 0, 1, "", "ROUTE_X", [], {},
    ])

    # Structure-aware mutations when the prediction looks like a predict_route dict.
    if isinstance(prediction, Mapping):
        flipped = dict(prediction)
        flipped["choice"] = f"__NOT__{prediction.get('choice', '')}"
        conf = prediction.get("confidence", 0.0)
        try:
            flipped["confidence"] = 0.0 if float(conf) > 0.5 else 1.0
        except (TypeError, ValueError):
            flipped["confidence"] = 0.0
        flipped["rationale"] = "ADVERSARIAL PERTURBATION"
        variants.append(flipped)

        zeroed = dict(prediction)
        zeroed["choice"] = ""
        zeroed["confidence"] = 0.0
        variants.append(zeroed)

        maxed = dict(prediction)
        maxed["confidence"] = 1.0
        variants.append(maxed)

    return variants


def _verdict(gate_fn: Callable[..., Any], state: Any, prediction: Any) -> Any:
    """Evaluate `gate_fn` over a deep-copied state.

    The state is deep-copied per call so a misbehaving gate that tries to read a
    prediction stashed in `state` cannot pollute later evaluations, and so the
    caller's state object is never mutated by this proof.

    A correct, prediction-independent gate accepts a single positional `state`
    (e.g. `coverage.is_complete`). To also catch a gate that *declares* a
    prediction parameter (already a Property-4 design violation, but we still
    prove behavioral independence), we try passing the prediction positionally
    and fall back to the single-argument call when the gate refuses it. The
    no-prediction sentinel always uses the single-argument form.
    """
    safe_state = copy.deepcopy(state)
    if prediction is _NO_PREDICTION:
        return gate_fn(safe_state)
    try:
        return gate_fn(safe_state, prediction)
    except TypeError:
        return gate_fn(safe_state)


def gate_decision_is_prediction_independent(
    gate_fn: Callable[..., Any],
    state: Any,
    prediction: Any,
) -> bool:
    """Prove the completion gate's verdict is identical regardless of prediction.

    Property 4 / REQ-19.2 (runtime mirror of Z3 CHECK-5). Returns True iff
    `gate_fn(state)` yields the SAME verdict under the supplied `prediction`,
    under a battery of adversarial perturbations of it, AND under no prediction
    at all. Any divergence — a gate whose decision moves with the prediction —
    returns False, exposing the off-gate-invariant violation.

    `gate_fn` is the completion gate (e.g. `coverage.is_complete`); `state` is
    the coverage model. The function is side-effect free: `state` is deep-copied
    for every evaluation, so neither the caller's state nor cross-evaluations are
    mutated.
    """
    baseline = _verdict(gate_fn, state, _NO_PREDICTION)
    for variant in _perturbations(prediction):
        if _verdict(gate_fn, state, variant) != baseline:
            return False
    return True


if __name__ == "__main__":  # pragma: no cover - manual smoke demo
    demo_history = [
        {"choice": "agent-a", "success": True, "features": {"type": "functional"}},
        {"choice": "agent-a", "success": True, "features": {"type": "functional"}},
        {"choice": "agent-b", "success": False, "features": {"type": "functional"}},
    ]
    print(predict_route(demo_history, ["agent-a", "agent-b"], {"type": "functional"}))

    # Independence witness against the canonical completion gate.
    try:
        from coverage import is_complete  # type: ignore
    except Exception:  # noqa: BLE001 - demo only
        is_complete = lambda m: bool(m.get("ok"))  # type: ignore
    state = {"items": [{"in_scope": True, "status": "proven"}]}
    pred = predict_route(demo_history, ["agent-a", "agent-b"], {"type": "functional"})
    print("prediction-independent:",
          gate_decision_is_prediction_independent(is_complete, state, pred))

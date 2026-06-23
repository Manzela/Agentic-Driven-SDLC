"""Independent verifier tests for tools/predictive_router.py.

Phase 6 / REQ-19 (predictive routing, OFF-GATE) / Property 4.
Plane requirement: REQ-ROUTE.

Written independently of the implementer. The contract under test:

  predict_route(history, candidates, features) ->
      {"choice", "confidence", "rationale"}
    * choice is one of the supplied candidates (never invented),
    * confidence is a float in [0, 1],
    * rationale is a non-empty string,
    * given history that favors one candidate, that candidate is chosen.

  gate_decision_is_prediction_independent(gate_fn, state, prediction) -> bool
    * returns True when the gate verdict is identical for two DIFFERENT
      predictions over the SAME coverage state — predictions never move
      the gate (Property 4 / REQ-19.2). The canonical gate used here is
      coverage.is_complete, a pure function of items[].in_scope / .status.
"""
from __future__ import annotations

import pytest

from tools.coverage import is_complete
from tools.predictive_router import (
    gate_decision_is_prediction_independent,
    predict_route,
)


# --------------------------------------------------------------------------- #
# predict_route: shape — choice in candidates, confidence in [0,1], rationale
# --------------------------------------------------------------------------- #
def test_predict_route_returns_candidate_confidence_rationale():
    candidates = ["agent-a", "agent-b", "agent-c"]
    history = [
        {"choice": "agent-a", "success": True},
        {"choice": "agent-b", "success": False},
    ]

    result = predict_route(history, candidates, {"type": "functional"})

    # choice is one of the supplied candidates (never invented)
    assert result["choice"] in candidates, result

    # confidence is a real number in the closed interval [0, 1]
    conf = result["confidence"]
    assert isinstance(conf, (int, float)) and not isinstance(conf, bool)
    assert 0.0 <= conf <= 1.0, conf

    # rationale is a non-empty string
    assert isinstance(result["rationale"], str)
    assert result["rationale"].strip(), "rationale must be non-empty"


def test_predict_route_confidence_in_range_for_extreme_histories():
    """Confidence stays within [0,1] for all-success and all-fail histories."""
    candidates = ["x", "y"]

    all_success = [{"choice": "x", "success": True} for _ in range(20)]
    all_fail = [{"choice": "x", "success": False} for _ in range(20)]

    for hist in (all_success, all_fail, []):
        out = predict_route(hist, candidates)
        assert out["choice"] in candidates, out
        assert 0.0 <= out["confidence"] <= 1.0, out


def test_predict_route_empty_candidates_is_safe():
    out = predict_route([{"choice": "z", "success": True}], [])
    assert 0.0 <= out["confidence"] <= 1.0
    assert isinstance(out["rationale"], str) and out["rationale"].strip()


# --------------------------------------------------------------------------- #
# predict_route: history favoring one candidate picks that candidate
# --------------------------------------------------------------------------- #
def test_history_favoring_one_candidate_picks_it():
    candidates = ["agent-a", "agent-b"]
    # agent-a: 4/4 successes; agent-b: 0/4 successes. a is clearly favored.
    history = [
        {"choice": "agent-a", "success": True},
        {"choice": "agent-a", "success": True},
        {"choice": "agent-a", "success": True},
        {"choice": "agent-a", "success": True},
        {"choice": "agent-b", "success": False},
        {"choice": "agent-b", "success": False},
        {"choice": "agent-b", "success": False},
        {"choice": "agent-b", "success": False},
    ]

    result = predict_route(history, candidates)

    assert result["choice"] == "agent-a", result
    # a confident pick should out-rank the failing candidate
    assert result["confidence"] > 0.0, result


def test_history_favoring_the_other_candidate_picks_it():
    """Same harness, opposite winner — guards against a hard-coded answer."""
    candidates = ["agent-a", "agent-b"]
    history = [
        {"choice": "agent-a", "success": False},
        {"choice": "agent-a", "success": False},
        {"choice": "agent-a", "success": False},
        {"choice": "agent-b", "success": True},
        {"choice": "agent-b", "success": True},
        {"choice": "agent-b", "success": True},
    ]

    result = predict_route(history, candidates)
    assert result["choice"] == "agent-b", result


def test_signature_specific_history_overrides_global():
    """A candidate winning for THIS feature signature is favored even if it
    looks worse globally."""
    candidates = ["agent-a", "agent-b"]
    feats = {"type": "nfr", "nfr_subtype": "perf"}
    history = [
        # For the perf signature, agent-b always wins.
        {"choice": "agent-b", "success": True, "features": feats},
        {"choice": "agent-b", "success": True, "features": feats},
        {"choice": "agent-a", "success": False, "features": feats},
        # Globally (other signatures) agent-a looks great, but off-signature.
        {"choice": "agent-a", "success": True, "features": {"type": "functional"}},
        {"choice": "agent-a", "success": True, "features": {"type": "functional"}},
    ]

    result = predict_route(history, candidates, feats)
    assert result["choice"] == "agent-b", result


# --------------------------------------------------------------------------- #
# Property 4: gate verdict is identical for two DIFFERENT predictions
# (predictions never change the gate)
# --------------------------------------------------------------------------- #
def _states():
    """Coverage states spanning both gate verdicts."""
    return [
        # complete: one in-scope proven item -> is_complete True
        {"items": [{"id": "A", "in_scope": True, "status": "proven"}]},
        # incomplete: an in-scope unproven item -> is_complete False
        {"items": [{"id": "B", "in_scope": True, "status": "unproven"}]},
        # mixed: in-scope failed dominates -> is_complete False
        {"items": [
            {"id": "C", "in_scope": True, "status": "proven"},
            {"id": "D", "in_scope": True, "status": "failed"},
            {"id": "E", "in_scope": False, "status": "unproven"},
        ]},
        # empty in-scope set -> is_complete False
        {"items": [{"id": "F", "in_scope": False, "status": "proven"}]},
    ]


def test_gate_decision_is_prediction_independent_returns_true():
    """The witness returns True: the gate's verdict does not move with the
    prediction, across both verdict outcomes."""
    for state in _states():
        pred = predict_route(
            [{"choice": "agent-a", "success": True}],
            ["agent-a", "agent-b"],
            {"type": "functional"},
        )
        assert gate_decision_is_prediction_independent(is_complete, state, pred) is True, state


def test_two_different_predictions_yield_identical_gate_verdict():
    """Directly: two DIFFERENT prediction objects produce the SAME gate
    verdict on the SAME state — the core of Property 4."""
    pred_one = {"choice": "agent-a", "confidence": 0.99, "rationale": "favor a"}
    pred_two = {"choice": "agent-b", "confidence": 0.01, "rationale": "favor b"}

    for state in _states():
        # The canonical gate ignores the prediction entirely.
        verdict_no_pred = is_complete(state)
        verdict_one = is_complete(state)  # gate never reads a prediction
        verdict_two = is_complete(state)
        assert verdict_one == verdict_two == verdict_no_pred

        # And the witness confirms independence under both predictions.
        assert gate_decision_is_prediction_independent(is_complete, state, pred_one) is True
        assert gate_decision_is_prediction_independent(is_complete, state, pred_two) is True


def test_witness_catches_a_prediction_dependent_gate():
    """Sanity: a BROKEN gate that lets the prediction change its verdict must
    be detected — the witness returns False. This proves the witness is not
    vacuously True."""
    def leaky_gate(state, prediction=None):
        # A gate that (wrongly) lets a high-confidence prediction force-allow.
        if isinstance(prediction, dict) and prediction.get("confidence", 0) > 0.5:
            return True
        return is_complete(state)

    # State whose true verdict is False (in-scope unproven), so a confident
    # prediction would flip it to True -> dependence is observable.
    state = {"items": [{"id": "X", "in_scope": True, "status": "unproven"}]}
    confident = {"choice": "agent-a", "confidence": 0.97, "rationale": "leak"}

    assert (
        gate_decision_is_prediction_independent(leaky_gate, state, confident) is False
    ), "witness must flag a prediction-dependent gate"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))

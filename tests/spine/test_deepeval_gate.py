"""Independent verifier tests for tools/deepeval_gate.py (S-deepeval_gate).

REQ-EVAL-001 / Requirement 30 / task 55 — the DeepEval eval-gating step.

design.md names NO Z3 Property/CHECK for REQ-EVAL-001 (requirements.md:542); the
named verification tool is the ``deepeval-gate`` CI check, so this test IS the
independent verification. Authored WITHOUT reference to the implementer's own
tests — it exercises the documented public contract of ``evaluate_gate`` only.

Contract under test (as specified by the verification task):

  * DEFAULT thresholds: faithfulness >= 0.8, answer_relevancy >= 0.7.
  * metrics meeting thresholds  -> passed True, failures [].
  * faithfulness 0.7 (below 0.8) -> passed False, a failure naming faithfulness.
  * answer_relevancy 0.6 (below 0.7) -> fail.
  * custom (operator) thresholds are honored.
  * fail-closed: absent / None / non-numeric / NaN scores fail, never pass.
  * the module imports with NO ``deepeval`` installed (guarded optional import).
"""

import importlib
import math

from tools.deepeval_gate import DEFAULT_THRESHOLDS, evaluate_gate


# --------------------------------------------------------------------------- #
# DEFAULT thresholds are exactly the spec values (faithfulness 0.8, AR 0.7).
# --------------------------------------------------------------------------- #
def test_default_thresholds_are_spec_values():
    assert DEFAULT_THRESHOLDS["faithfulness"] == 0.8
    assert DEFAULT_THRESHOLDS["answer_relevancy"] == 0.7


# --------------------------------------------------------------------------- #
# Metrics meeting thresholds -> passed True, failures [].
# --------------------------------------------------------------------------- #
def test_metrics_meeting_thresholds_pass():
    result = evaluate_gate({"faithfulness": 0.85, "answer_relevancy": 0.75})
    assert result["passed"] is True
    assert result["failures"] == []


def test_metrics_exactly_at_threshold_pass():
    # The gate is score >= threshold; the boundary value must PASS.
    result = evaluate_gate({"faithfulness": 0.8, "answer_relevancy": 0.7})
    assert result["passed"] is True
    assert result["failures"] == []


# --------------------------------------------------------------------------- #
# faithfulness 0.7 (below 0.8) -> passed False, failure naming faithfulness.
# --------------------------------------------------------------------------- #
def test_faithfulness_below_threshold_fails_and_names_it():
    result = evaluate_gate({"faithfulness": 0.7, "answer_relevancy": 0.9})
    assert result["passed"] is False
    failing_metrics = {f["metric"] for f in result["failures"]}
    assert "faithfulness" in failing_metrics
    # answer_relevancy at 0.9 is above its 0.7 bar and must NOT be a failure.
    assert "answer_relevancy" not in failing_metrics
    faithfulness_failure = next(
        f for f in result["failures"] if f["metric"] == "faithfulness"
    )
    assert faithfulness_failure["score"] == 0.7
    assert faithfulness_failure["threshold"] == 0.8


# --------------------------------------------------------------------------- #
# answer_relevancy 0.6 (below 0.7) -> fail.
# --------------------------------------------------------------------------- #
def test_answer_relevancy_below_threshold_fails():
    result = evaluate_gate({"faithfulness": 0.95, "answer_relevancy": 0.6})
    assert result["passed"] is False
    failing_metrics = {f["metric"] for f in result["failures"]}
    assert "answer_relevancy" in failing_metrics
    assert "faithfulness" not in failing_metrics
    ar_failure = next(
        f for f in result["failures"] if f["metric"] == "answer_relevancy"
    )
    assert ar_failure["score"] == 0.6
    assert ar_failure["threshold"] == 0.7


def test_both_below_threshold_report_both():
    result = evaluate_gate({"faithfulness": 0.5, "answer_relevancy": 0.5})
    assert result["passed"] is False
    failing_metrics = {f["metric"] for f in result["failures"]}
    assert failing_metrics == {"faithfulness", "answer_relevancy"}


# --------------------------------------------------------------------------- #
# Custom (operator-overridable) thresholds are honored.
# --------------------------------------------------------------------------- #
def test_custom_threshold_raises_the_bar():
    # 0.85 clears the DEFAULT 0.8 but not a stricter custom 0.9 -> must fail.
    result = evaluate_gate(
        {"faithfulness": 0.85, "answer_relevancy": 0.9},
        thresholds={"faithfulness": 0.9, "answer_relevancy": 0.7},
    )
    assert result["passed"] is False
    assert {f["metric"] for f in result["failures"]} == {"faithfulness"}


def test_custom_threshold_lowers_the_bar():
    # 0.65 fails the DEFAULT 0.7 but a lenient custom 0.6 lets it pass.
    result = evaluate_gate(
        {"answer_relevancy": 0.65},
        thresholds={"answer_relevancy": 0.6},
    )
    assert result["passed"] is True
    assert result["failures"] == []


def test_custom_threshold_can_gate_a_new_metric():
    result = evaluate_gate(
        {"hallucination": 0.3},
        thresholds={"hallucination": 0.5},
    )
    assert result["passed"] is False
    (failure,) = result["failures"]
    assert failure["metric"] == "hallucination"


# --------------------------------------------------------------------------- #
# Fail-closed: a thresholded metric that produces no usable score must FAIL.
# --------------------------------------------------------------------------- #
def test_absent_thresholded_metric_fails_closed():
    result = evaluate_gate({"faithfulness": 0.95})  # answer_relevancy missing
    assert result["passed"] is False
    assert "answer_relevancy" in {f["metric"] for f in result["failures"]}


def test_none_score_fails_closed():
    result = evaluate_gate({"faithfulness": None, "answer_relevancy": 0.9})
    assert result["passed"] is False
    assert {f["metric"] for f in result["failures"]} == {"faithfulness"}


def test_non_numeric_score_fails_closed():
    result = evaluate_gate({"faithfulness": "bad", "answer_relevancy": 0.9})
    assert result["passed"] is False
    assert {f["metric"] for f in result["failures"]} == {"faithfulness"}


def test_nan_score_fails_closed():
    result = evaluate_gate({"faithfulness": math.nan, "answer_relevancy": 0.9})
    assert result["passed"] is False
    assert {f["metric"] for f in result["failures"]} == {"faithfulness"}


# --------------------------------------------------------------------------- #
# Unthresholded extra metrics are informational only and never gate.
# --------------------------------------------------------------------------- #
def test_extra_unthresholded_metric_is_ignored():
    result = evaluate_gate(
        {"faithfulness": 0.9, "answer_relevancy": 0.8, "latency": 0.0}
    )
    assert result["passed"] is True
    assert result["failures"] == []


# --------------------------------------------------------------------------- #
# Importing the module does NOT require deepeval (guarded optional import).
# --------------------------------------------------------------------------- #
def test_module_imports_without_deepeval():
    mod = importlib.import_module("tools.deepeval_gate")
    assert hasattr(mod, "evaluate_gate")
    assert hasattr(mod, "assert_gate")

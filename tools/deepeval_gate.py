#!/usr/bin/env python3
"""deepeval_gate.py — DeepEval pytest-native eval gate (REQ-EVAL-001, Phase 3).

Spec: .kiro/specs/spec-to-evidence-control/design.md
        - Component Inventory row `deepeval_gate.py` (~line 152)
        - "DeepEval Quality Gate (`deepeval_gate.py`)" subsection (~line 1314)
        - Error Handling row "`deepeval-gate` evaluator-LLM failure" (~line 1373)
      .kiro/specs/spec-to-evidence-control/requirements.md, Requirement 30
        (REQ-EVAL-001), criteria 30.1/30.2/30.3 (~lines 506-508)
      .kiro/specs/spec-to-evidence-control/tasks.md, task 55 / 55.1.

This module is the DeepEval pytest-native eval step that runs as the REQUIRED
CI status check ``deepeval-gate`` at merge. It gates LLM output QUALITY on the
configured DEFAULT metric thresholds:

    faithfulness      >= 0.8
    answer_relevancy  >= 0.7

These are registered, operator-overridable DEFAULTs (Requirement 20 threshold
registry); they are NOT "e.g." illustrations (requirements.md:379-380).

Two layers, deliberately separated:

  * ``evaluate_gate(metrics, thresholds=None) -> {"passed": bool,
    "failures": [...]}`` — the PURE-STDLIB testable core. No ``deepeval`` import
    is required to exercise it; it is the deterministic threshold comparison the
    real DeepEval ``assert_test()`` wraps. Any metric strictly below its
    threshold fails the gate. This is what the unit + CI smoke tests assert
    against (the harness stops at CHECK-13b; no PBT covers REQ-EVAL-001, so a
    ``deepeval-gate`` test is the named verification tool, requirements.md:542).

  * ``assert_gate(test_case, metrics=None)`` — the thin DeepEval-native wrapper
    that calls ``deepeval.assert_test()`` on the configured metrics. The
    ``deepeval`` import is OPTIONAL and GUARDED so importing this module (and
    running the ``evaluate_gate`` unit) never requires ``deepeval`` to be
    installed; the wrapper raises a clear error only if actually invoked without
    the dependency.

Reconciliation with the governing invariant ("predictions never gate",
design.md (b) ~line 1319): ``deepeval_gate`` is a DETERMINISTIC (temperature-0,
seeded, fixed-judge) acceptance check on a fixed eval dataset, scoped to
product-output quality — NOT a model self-grade and NOT the completion gate that
decides "delivery is complete". The completion verdict stays computed solely
from verifiable facts (coverage/evidence/OPA); this is an independent quality
bar layered on top.

Fail-closed posture (design.md Error Handling ~line 1373): a metric that cannot
produce a score (None / non-numeric / NaN) is a FAILURE, never a silent pass —
consistent with every other gate. An empty metric set with no applicable
threshold is a vacuous PASS only when there is genuinely nothing to evaluate
(the criterion-30.3 "no LLM output to evaluate" case is handled one layer up,
at the fixture/collection level, not by fabricating scores here).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

__all__ = [
    "DEFAULT_THRESHOLDS",
    "evaluate_gate",
    "assert_gate",
]

# Configured DEFAULT metric thresholds (REQ-EVAL-001 / Requirement 30.2;
# requirements.md:379-380). Operator-overridable via the Requirement-20
# threshold registry — passed in as ``thresholds`` to override. A metric is
# gated by ``score >= threshold``; a metric strictly below its threshold fails.
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "faithfulness": 0.8,
    "answer_relevancy": 0.7,
}


def _coerce_score(value: Any) -> Optional[float]:
    """Coerce a raw metric value to a finite float, or ``None`` if it cannot be.

    A non-numeric, ``None``, ``NaN``, or infinite value is NOT a usable score.
    Returning ``None`` lets ``evaluate_gate`` treat it as a fail-closed failure
    (a metric that cannot produce a deterministic score is a blocking error,
    never a silent pass — design.md Error Handling row ~line 1373). ``bool`` is
    excluded explicitly: ``True``/``False`` are not valid metric scores even
    though ``bool`` is an ``int`` subclass.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        score = float(value)
    elif isinstance(value, str):
        try:
            score = float(value.strip())
        except (ValueError, AttributeError):
            return None
    else:
        return None
    if math.isnan(score) or math.isinf(score):
        return None
    return score


def evaluate_gate(
    metrics: Dict[str, Any],
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Evaluate measured metric scores against their thresholds.

    The PURE testable core of the DeepEval gate — no ``deepeval`` dependency.
    This is the deterministic comparison that the real DeepEval ``assert_test()``
    wraps as the REQUIRED ``deepeval-gate`` CI check.

    Parameters
    ----------
    metrics:
        Mapping of metric-name -> measured score (e.g.
        ``{"faithfulness": 0.83, "answer_relevancy": 0.71}``). Scores are
        coerced to finite floats; a ``None`` / non-numeric / ``NaN`` / infinite
        score is treated as a FAILURE (fail closed), never a pass.
    thresholds:
        Optional override of the gated thresholds. Defaults to
        ``DEFAULT_THRESHOLDS`` (faithfulness >= 0.8, answer_relevancy >= 0.7).
        Each entry is a metric-name -> minimum-acceptable score. ONLY metrics
        named in ``thresholds`` gate the build — an unthresholded metric present
        in ``metrics`` is informational and never fails the gate.

    Returns
    -------
    dict
        ``{"passed": bool, "failures": [ {metric, score, threshold, reason},
        ... ]}``. ``passed`` is ``True`` iff ``failures`` is empty. A metric
        gate FAILS when:
          * the metric is ABSENT from ``metrics`` (no score was produced for a
            threshold the gate requires), OR
          * its score cannot be coerced to a finite float (None/non-numeric/
            NaN/inf — fail closed), OR
          * its finite score is STRICTLY BELOW the threshold.
        Failures are ordered by metric name so the output is deterministic.

    Fail-closed: any unexpected error yields ``passed=False`` with a single
    failure carrying the exception, never a vacuous pass.
    """
    try:
        active = DEFAULT_THRESHOLDS if thresholds is None else thresholds
        if not isinstance(active, dict):
            return {
                "passed": False,
                "failures": [
                    {
                        "metric": "<thresholds>",
                        "score": None,
                        "threshold": None,
                        "reason": (
                            "thresholds is not a mapping "
                            f"(got {type(active).__name__}). Fail closed."
                        ),
                    }
                ],
            }
        if not isinstance(metrics, dict):
            return {
                "passed": False,
                "failures": [
                    {
                        "metric": "<metrics>",
                        "score": None,
                        "threshold": None,
                        "reason": (
                            "metrics is not a mapping "
                            f"(got {type(metrics).__name__}). Fail closed."
                        ),
                    }
                ],
            }

        failures: List[Dict[str, Any]] = []
        # Only thresholded metrics gate; iterate them in deterministic order.
        for metric in sorted(active):
            threshold = active[metric]
            coerced_threshold = _coerce_score(threshold)
            if coerced_threshold is None:
                failures.append(
                    {
                        "metric": metric,
                        "score": None,
                        "threshold": threshold,
                        "reason": (
                            f"threshold for {metric!r} is not a finite number "
                            f"({threshold!r}). Fail closed."
                        ),
                    }
                )
                continue

            if metric not in metrics:
                failures.append(
                    {
                        "metric": metric,
                        "score": None,
                        "threshold": coerced_threshold,
                        "reason": (
                            f"no score produced for required metric {metric!r}. "
                            "Fail closed."
                        ),
                    }
                )
                continue

            score = _coerce_score(metrics[metric])
            if score is None:
                failures.append(
                    {
                        "metric": metric,
                        "score": metrics[metric],
                        "threshold": coerced_threshold,
                        "reason": (
                            f"metric {metric!r} did not produce a finite score "
                            f"({metrics[metric]!r}). Fail closed."
                        ),
                    }
                )
                continue

            if score < coerced_threshold:
                failures.append(
                    {
                        "metric": metric,
                        "score": score,
                        "threshold": coerced_threshold,
                        "reason": (
                            f"{metric} score {score} is below threshold "
                            f"{coerced_threshold}."
                        ),
                    }
                )

        return {"passed": not failures, "failures": failures}

    except Exception as exc:  # noqa: BLE001 — fail CLOSED on any error.
        return {
            "passed": False,
            "failures": [
                {
                    "metric": "<error>",
                    "score": None,
                    "threshold": None,
                    "reason": (
                        f"evaluate_gate raised {type(exc).__name__}: {exc}. "
                        "Fail closed."
                    ),
                }
            ],
        }


# --------------------------------------------------------------------------- #
# DeepEval-native wrapper (optional dependency, guarded).
# --------------------------------------------------------------------------- #
# The real CI gate runs ``assert_test()`` under pytest. ``deepeval`` is imported
# LAZILY inside the wrapper so that importing this module — and running the
# ``evaluate_gate`` unit — never requires ``deepeval`` to be installed. The
# import error surfaces only if the DeepEval-native path is actually invoked.


def _default_metrics() -> List[Any]:
    """Construct the configured DeepEval metric objects at the DEFAULT thresholds.

    Imports ``deepeval`` lazily. The judge is pinned (temperature 0, fixed seed,
    fixed model) at the workflow / threshold-registry layer (design.md (a),
    ~line 1318) — DEFAULT judge ``claude-opus-4-8`` via Anthropic on Vertex AI —
    so scores are reproducible across runs. Raises ``RuntimeError`` with an
    actionable message if ``deepeval`` is not installed.
    """
    try:
        from deepeval.metrics import (  # type: ignore[import-not-found]
            AnswerRelevancyMetric,
            FaithfulnessMetric,
        )
    except ImportError as exc:  # deepeval is an OPTIONAL dependency of this unit.
        raise RuntimeError(
            "deepeval is not installed; the DeepEval-native assert_gate() path "
            "requires it (pip install deepeval). The pure evaluate_gate() core "
            "does not. See pyproject/requirements pinning per tasks.md task 1."
        ) from exc

    return [
        FaithfulnessMetric(threshold=DEFAULT_THRESHOLDS["faithfulness"]),
        AnswerRelevancyMetric(threshold=DEFAULT_THRESHOLDS["answer_relevancy"]),
    ]


def assert_gate(test_case: Any, metrics: Optional[List[Any]] = None) -> None:
    """DeepEval-native gate: assert ``test_case`` passes the configured metrics.

    Thin wrapper over ``deepeval.assert_test()`` — the pytest-native API
    Requirement 30.1 mandates. This is what the ``deepeval-gate`` CI check runs
    against each golden-set ``LLMTestCase`` fixture under ``tests/eval/``
    (requirements.md:507). Raises ``AssertionError`` (failing the build) when any
    metric is below its threshold, mirroring ``evaluate_gate``'s fail decision.

    ``deepeval`` is imported lazily; this function is only reachable when the
    optional dependency is present.
    """
    try:
        from deepeval import assert_test  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "deepeval is not installed; assert_gate() requires it "
            "(pip install deepeval). The pure evaluate_gate() core does not."
        ) from exc

    assert_test(test_case, metrics if metrics is not None else _default_metrics())


# --------------------------------------------------------------------------- #
# CLI shell — ad-hoc threshold check over a JSON metrics blob.
# --------------------------------------------------------------------------- #
# Reads a JSON object of measured scores from argv[1] (a file path) or stdin,
# evaluates against DEFAULT_THRESHOLDS, prints the decision, and exits 0 on pass
# / 1 on fail. All decision logic lives in evaluate_gate; this shell is trivial.


def main(argv: Optional[List[str]] = None) -> int:
    import json
    import sys

    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv:
            with open(argv[0], "r", encoding="utf-8") as fh:
                metrics = json.load(fh)
        else:
            raw = sys.stdin.read()
            metrics = json.loads(raw) if raw.strip() else {}
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "passed": False,
            "failures": [
                {
                    "metric": "<input>",
                    "score": None,
                    "threshold": None,
                    "reason": f"could not load metrics: {exc}. Fail closed.",
                }
            ],
        }
        print(json.dumps(result, indent=2))
        return 1

    result = evaluate_gate(metrics)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())

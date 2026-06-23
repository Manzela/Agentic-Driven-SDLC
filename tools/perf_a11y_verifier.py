"""perf_a11y_verifier.py — the Verifier's FIFTH layer (perf / a11y / ui-screen).

Spec: .kiro/specs/spec-to-evidence-control/design.md
      ("Performance / Accessibility / UI-Screen Verifier (``perf_a11y_verifier``)")
Requirements: 25.1, 25.2 (REQ-VERIFY-007, REQ-VERIFY-008)
Property: 31 (Perf / A11y / UI-Screen Evidence Required)
Task: 51 (subtasks 51.1 perf, 51.2 a11y, 51.3 ui-screen render, 51.4 property test)

This module is the assertion engine for the Verifier's fifth verification layer.
It dispatches on a coverage item's ``subtype`` discriminator
(``feature_list.json`` CoverageItem.subtype, mirrored on ``coverage_items.subtype``)
and returns a structured pass/fail verdict for each kind of item:

    * ``performance``  -> ``verify_performance``  : measured metrics vs numeric
      budgets (p95 latency, Core Web Vitals such as LCP) — REQ-VERIFY-007 / 25.1.
    * ``accessibility``-> ``verify_accessibility`` : an axe-core result is a pass
      iff it carries ZERO WCAG-A/AA violations — REQ-VERIFY-008 / 25.2.
    * ``ui-screen``    -> ``verify_ui_screen``     : every declared screen/state
      (at least ``empty``/``loading``/``error``/``ready``) must carry an attached
      render-assertion Evidence_Record produced by the Playwright BEHAVIORAL layer
      (``evidence_kind`` ``behavioral``/``integration``, NEVER a perf/a11y tool) —
      REQ-VERIFY-008 (Ubiquitous).

Threshold OWNERSHIP note (design (4)): this module does NOT own the perf budgets
or the a11y bar. Those live in the execution-bounds / NFR-threshold config
registry (Requirement 20, task 44). The verifier READS the budgets it is handed
and asserts the measured metrics against them; it is a pure assertion function,
not a threshold registry.

This module is PURE STDLIB — it asserts over already-collected tool reports
(k6 / Lighthouse / axe-core JSON, Playwright Evidence_Records). It does NOT shell
out to k6, Lighthouse, axe-core, or Playwright; running those tools and capturing
their artifacts is the job of the CI step + ``evidence_collector.py``. Keeping the
assertion logic pure makes Property 31 cheap to pin with a Hypothesis test
(``tests/property/test_perf_a11y.py``, task 39.21) and free of network/process
flakiness.
"""

from __future__ import annotations

from numbers import Real
from typing import Any, Dict, List

__all__ = [
    "REQUIRED_DECLARED_STATES",
    "PERF_SUBTYPE",
    "A11Y_SUBTYPE",
    "UI_SCREEN_SUBTYPE",
    "RENDER_ASSERTION_EVIDENCE_KINDS",
    "verify_performance",
    "verify_accessibility",
    "verify_ui_screen",
    "verify_item",
]

# ---------------------------------------------------------------------------
# Spec-pinned constants (single-sourced so caller + tests enumerate the same set)
# ---------------------------------------------------------------------------

# CoverageItem.subtype discriminator values this layer dispatches on (design (1)).
PERF_SUBTYPE = "performance"
A11Y_SUBTYPE = "accessibility"
UI_SCREEN_SUBTYPE = "ui-screen"

# REQ-VERIFY-008 (Ubiquitous): the MINIMUM set of declared screen/states a
# ``ui-screen`` item must enumerate. ``declared_states`` MAY add more; it may
# never carry fewer than these four. Held as a frozenset so order is irrelevant
# and membership/subset checks are O(1).
REQUIRED_DECLARED_STATES = frozenset({"empty", "loading", "error", "ready"})

# The render obligation is a BEHAVIORAL test routed through the Playwright
# behavioral layer (task 15) + the WIRING integration-test obligation
# (Req 8.3 / task 47) — NOT a perf/a11y tool. So a render-assertion
# Evidence_Record's ``evidence_kind`` must be one of these (design (1)/(3),
# Property 31). ``perf``/``a11y`` are explicitly NOT render evidence.
RENDER_ASSERTION_EVIDENCE_KINDS = frozenset({"behavioral", "integration"})


# ---------------------------------------------------------------------------
# (1) Performance — REQ-VERIFY-007 / 25.1
# ---------------------------------------------------------------------------

def verify_performance(metrics: Dict[str, Any], budgets: Dict[str, Any]) -> Dict[str, Any]:
    """Assert measured performance ``metrics`` against numeric ``budgets``.

    Each ``budget`` is an upper bound: the measured metric PASSES when
    ``metrics[k] <= budgets[k]`` (e.g. ``p95_ms <= 200``, ``LCP <= 2500``). This
    "lower-is-better, budget is a ceiling" convention matches both k6 latency
    percentiles and Lighthouse Core Web Vitals (REQ-VERIFY-007).

    Parameters
    ----------
    metrics:
        Measured values keyed by metric id, e.g.
        ``{"p95_ms": 180, "LCP": 2100, "CLS": 0.05}``. Values must be real
        numbers; a non-numeric or missing measurement for a budgeted metric is
        itself a violation (you cannot prove a budget you never measured).
    budgets:
        Numeric ceilings keyed by the SAME metric ids, e.g.
        ``{"p95_ms": 200, "LCP": 2500}``. Only metrics that appear in ``budgets``
        are checked; an unbudgeted metric in ``metrics`` is ignored. A
        non-numeric budget value is a configuration error and is reported as a
        violation rather than silently skipped.

    Returns
    -------
    dict
        ``{"passed": bool, "violations": [ {...}, ... ]}`` where ``passed`` is
        ``True`` iff ``violations`` is empty. Each violation is a structured
        record::

            {
                "metric":   <str>,          # the budgeted metric id
                "measured": <number|None>,  # the measured value (None if absent)
                "budget":   <number>,       # the ceiling it breached
                "reason":   <str>,          # human-readable explanation
            }

        A budget set with no measurement, a non-numeric measurement, or a
        non-numeric budget all yield a violation, so a ``passed: True`` verdict
        means EVERY declared budget was measured and met.
    """
    violations: List[Dict[str, Any]] = []

    if not isinstance(metrics, dict):
        metrics = {}

    if not isinstance(budgets, dict):
        return {
            "passed": False,
            "violations": [
                {
                    "metric": None,
                    "measured": None,
                    "budget": None,
                    "reason": "budgets is not a mapping; cannot evaluate perf budgets",
                }
            ],
        }

    for metric, budget in budgets.items():
        # A budget must itself be a real number to compare against.
        if not _is_real_number(budget):
            violations.append(
                {
                    "metric": metric,
                    "measured": metrics.get(metric),
                    "budget": budget,
                    "reason": "budget value is not numeric",
                }
            )
            continue

        measured = metrics.get(metric)

        # A budgeted metric that was never measured cannot be proven met.
        if metric not in metrics:
            violations.append(
                {
                    "metric": metric,
                    "measured": None,
                    "budget": budget,
                    "reason": "metric has a budget but no measured value",
                }
            )
            continue

        if not _is_real_number(measured):
            violations.append(
                {
                    "metric": metric,
                    "measured": measured,
                    "budget": budget,
                    "reason": "measured value is not numeric",
                }
            )
            continue

        # The actual budget assertion: lower-is-better, budget is the ceiling.
        if measured > budget:
            violations.append(
                {
                    "metric": metric,
                    "measured": measured,
                    "budget": budget,
                    "reason": "measured value exceeds budget",
                }
            )

    return {"passed": not violations, "violations": violations}


# ---------------------------------------------------------------------------
# (2) Accessibility — REQ-VERIFY-008 / 25.2
# ---------------------------------------------------------------------------

def verify_accessibility(axe_results: Dict[str, Any]) -> Dict[str, Any]:
    """Assert an axe-core result carries ZERO WCAG-A/AA violations.

    REQ-VERIFY-008 / 25.2: an ``accessibility`` item passes iff axe-core reports
    no WCAG-A/AA violations on the covered screen. This reads the canonical
    axe-core JSON shape — a top-level ``violations`` array, each entry carrying a
    rule ``id`` and a ``tags`` list (e.g. ``["wcag2a", "wcag2aa", "wcag412"]``).

    Only WCAG-A and WCAG-AA violations gate the verdict. axe-core also emits
    best-practice and WCAG-AAA findings; those are reported in the structured
    output for visibility but do NOT fail the item, because the bar
    (design (4)) is specifically "zero WCAG-A/AA violations".

    Parameters
    ----------
    axe_results:
        Parsed axe-core result object. The relevant key is ``violations`` (a
        list). A missing/empty ``violations`` list is a clean pass. A non-dict
        input, or a ``violations`` value that is not a list, is treated as a
        malformed report and fails closed (you cannot prove a11y from a result
        you cannot read).

    Returns
    -------
    dict
        ``{"passed": bool, "violations": [...], "non_gating": [...]}`` where
        ``passed`` is ``True`` iff there are zero WCAG-A/AA violations. Each
        gating violation is summarized as::

            {"id": <rule id>, "impact": <str|None>,
             "wcag_level": "A"|"AA", "tags": [<str>, ...], "node_count": <int>}

        ``non_gating`` lists any axe violations that are NOT WCAG-A/AA (e.g.
        best-practice, WCAG-AAA) so they are surfaced without failing the gate.
    """
    if not isinstance(axe_results, dict):
        return {
            "passed": False,
            "violations": [],
            "non_gating": [],
            "reason": "axe_results is not a mapping; cannot evaluate accessibility",
        }

    raw_violations = axe_results.get("violations", [])
    if not isinstance(raw_violations, list):
        return {
            "passed": False,
            "violations": [],
            "non_gating": [],
            "reason": "axe_results.violations is not a list; malformed axe report",
        }

    gating: List[Dict[str, Any]] = []
    non_gating: List[Dict[str, Any]] = []

    for entry in raw_violations:
        summary = _summarize_axe_violation(entry)
        if summary["wcag_level"] in ("A", "AA"):
            gating.append(summary)
        else:
            non_gating.append(summary)

    return {
        "passed": not gating,
        "violations": gating,
        "non_gating": non_gating,
    }


# ---------------------------------------------------------------------------
# (3) UI-screen render completeness — REQ-VERIFY-008 (Ubiquitous)
# ---------------------------------------------------------------------------

def verify_ui_screen(item: Dict[str, Any]) -> Dict[str, Any]:
    """Assert every declared screen/state of a ``ui-screen`` item has render evidence.

    REQ-VERIFY-008 (Ubiquitous) / design (3): a ``subtype=='ui-screen'`` item
    carries a ``declared_states`` array (at least ``empty``/``loading``/
    ``error``/``ready``). EACH declared state SHALL have an attached
    render-assertion Evidence_Record — a BEHAVIORAL test produced by the
    Playwright layer (``evidence_kind`` ``behavioral`` or ``integration``), never
    a perf/a11y tool. This turns "every declared screen/state renders" into an
    enumerable, checkable obligation.

    The item is expected to expose, per declared state, the evidence that proves
    it renders. This reader accepts the canonical shape — an ``evidence`` list of
    Evidence_Records each tagged with the state it covers — via either a
    ``state`` key or a ``test_name`` equal to the state id (the design's
    Evidence_Record mapping sets ``test_name`` = the ``screen/state`` id).

    Verdict rules (all must hold for ``passed``):

    1. ``declared_states`` enumerates AT LEAST the four required states
       (``empty``/``loading``/``error``/``ready``). A missing required state is a
       ``missing_required_state`` violation.
    2. Every declared state has at least one attached Evidence_Record.
       A state with none is a ``missing_render_evidence`` violation.
    3. Each such Evidence_Record's ``evidence_kind`` is a render-assertion kind
       (``behavioral``/``integration``). A state whose only evidence is
       ``perf``/``a11y``/``unit`` (or untagged) is a ``wrong_evidence_kind``
       violation — the render obligation must be a behavioral test.

    Parameters
    ----------
    item:
        The coverage item dict. Relevant keys: ``declared_states`` (list[str])
        and ``evidence`` (list[Evidence_Record]); each Evidence_Record names its
        state via ``state`` or ``test_name`` and its kind via ``evidence_kind``.

    Returns
    -------
    dict
        ``{"passed": bool, "violations": [...], "states": {<state>: bool, ...}}``.
        ``passed`` is ``True`` iff there are zero violations. ``states`` maps each
        declared (and each required) state to whether it is satisfied by a
        render-assertion Evidence_Record. Each violation is::

            {"state": <str>, "kind": <violation-kind>, "reason": <str>}
    """
    violations: List[Dict[str, Any]] = []

    if not isinstance(item, dict):
        return {
            "passed": False,
            "violations": [
                {"state": None, "kind": "malformed_item",
                 "reason": "item is not a mapping; cannot evaluate ui-screen"}
            ],
            "states": {},
        }

    declared_raw = item.get("declared_states", [])
    declared_states: List[str] = (
        [s for s in declared_raw if isinstance(s, str)]
        if isinstance(declared_raw, list)
        else []
    )

    # Build a state -> [evidence-kind, ...] map from the item's render evidence.
    state_to_kinds = _index_render_evidence_by_state(item.get("evidence", []))

    # The set of states we must adjudicate = declared states UNION the required
    # four, so a ui-screen item that simply omits "error" from declared_states is
    # still caught as a missing required state.
    states_to_check = list(
        dict.fromkeys(list(declared_states) + sorted(REQUIRED_DECLARED_STATES))
    )

    states_verdict: Dict[str, bool] = {}

    for state in states_to_check:
        satisfied = True

        # (1) Required-state enumeration.
        if state in REQUIRED_DECLARED_STATES and state not in declared_states:
            violations.append(
                {
                    "state": state,
                    "kind": "missing_required_state",
                    "reason": "required ui-screen state is not present in declared_states",
                }
            )
            satisfied = False

        kinds = state_to_kinds.get(state, [])

        # (2) Render evidence present at all.
        if not kinds:
            violations.append(
                {
                    "state": state,
                    "kind": "missing_render_evidence",
                    "reason": "declared state has no attached render-assertion Evidence_Record",
                }
            )
            satisfied = False
        # (3) Render evidence is a behavioral/integration kind.
        elif not any(k in RENDER_ASSERTION_EVIDENCE_KINDS for k in kinds):
            violations.append(
                {
                    "state": state,
                    "kind": "wrong_evidence_kind",
                    "reason": (
                        "render evidence_kind must be behavioral/integration "
                        "(Playwright render assertion), not perf/a11y/unit; got "
                        + ", ".join(sorted(set(str(k) for k in kinds)))
                    ),
                }
            )
            satisfied = False

        states_verdict[state] = satisfied

    return {
        "passed": not violations,
        "violations": violations,
        "states": states_verdict,
    }


# ---------------------------------------------------------------------------
# Top-level dispatch — routes a coverage item to its layer by ``subtype``
# ---------------------------------------------------------------------------

def verify_item(item: Dict[str, Any], budgets: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Dispatch a coverage ``item`` to the correct fifth-layer check by ``subtype``.

    This is the FIFTH verification layer's entry point (design (1)): it reads the
    item's ``subtype`` discriminator and routes deterministically — never guessing
    from free text (Req 25.1/25.2):

        * ``performance``   -> ``verify_performance(item["metrics"], budgets)``
        * ``accessibility`` -> ``verify_accessibility(item["axe_results"])``
        * ``ui-screen``     -> ``verify_ui_screen(item)``

    Parameters
    ----------
    item:
        The coverage item dict, carrying ``subtype`` plus the relevant payload
        (``metrics`` for perf, ``axe_results`` for a11y, ``declared_states`` +
        ``evidence`` for ui-screen).
    budgets:
        The perf budget registry slice (Req 20 / task 44). Only consulted for a
        ``performance`` item; defaults to an empty mapping. If a ``performance``
        item carries its own ``budgets`` key, the explicit ``budgets`` argument
        takes precedence when provided, else the item's own budgets are used.

    Returns
    -------
    dict
        The structured verdict from the routed checker, with an added
        ``"subtype"`` echo. An unknown/missing ``subtype`` returns
        ``{"passed": False, ...}`` with an ``unknown_subtype`` reason rather than
        silently passing — a fifth-layer item with no routable subtype is not
        provable.
    """
    subtype = item.get("subtype") if isinstance(item, dict) else None

    if subtype == PERF_SUBTYPE:
        item_budgets = budgets if budgets is not None else item.get("budgets", {})
        result = verify_performance(item.get("metrics", {}), item_budgets)
    elif subtype == A11Y_SUBTYPE:
        result = verify_accessibility(item.get("axe_results", {}))
    elif subtype == UI_SCREEN_SUBTYPE:
        result = verify_ui_screen(item)
    else:
        return {
            "passed": False,
            "violations": [],
            "subtype": subtype,
            "reason": (
                "unknown_subtype: expected one of "
                f"{PERF_SUBTYPE!r}/{A11Y_SUBTYPE!r}/{UI_SCREEN_SUBTYPE!r}"
            ),
        }

    result = dict(result)
    result["subtype"] = subtype
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_real_number(value: Any) -> bool:
    """Return ``True`` iff ``value`` is a real number usable in a budget compare.

    ``bool`` is a subclass of ``int`` but is rejected — a boolean is never a
    legitimate latency/CWV measurement or budget, and silently treating
    ``True``/``False`` as ``1``/``0`` would mask a malformed report.
    """
    return isinstance(value, Real) and not isinstance(value, bool)


def _wcag_level_from_tags(tags: Any) -> str | None:
    """Map an axe-core ``tags`` list to its gating WCAG level, or ``None``.

    Returns ``"A"`` or ``"AA"`` when the rule is tagged WCAG-A / WCAG-AA
    respectively (axe tags ``wcag2a``/``wcag21a`` -> A, ``wcag2aa``/``wcag21aa``
    -> AA). AA takes precedence in the (rare) case a rule carries both, since an
    AA-tagged violation gates regardless. Returns ``None`` for non-gating tag
    sets (best-practice, WCAG-AAA, or no recognizable WCAG-A/AA tag).
    """
    if not isinstance(tags, list):
        return None
    tagset = {t for t in tags if isinstance(t, str)}
    aa_tags = {"wcag2aa", "wcag21aa", "wcag22aa"}
    a_tags = {"wcag2a", "wcag21a", "wcag22a"}
    if tagset & aa_tags:
        return "AA"
    if tagset & a_tags:
        return "A"
    return None


def _summarize_axe_violation(entry: Any) -> Dict[str, Any]:
    """Normalize one axe-core violation entry into a stable summary dict."""
    if not isinstance(entry, dict):
        return {
            "id": None,
            "impact": None,
            "wcag_level": None,
            "tags": [],
            "node_count": 0,
        }
    tags = entry.get("tags", [])
    nodes = entry.get("nodes", [])
    return {
        "id": entry.get("id"),
        "impact": entry.get("impact"),
        "wcag_level": _wcag_level_from_tags(tags),
        "tags": [t for t in tags if isinstance(t, str)] if isinstance(tags, list) else [],
        "node_count": len(nodes) if isinstance(nodes, list) else 0,
    }


def _index_render_evidence_by_state(evidence: Any) -> Dict[str, List[Any]]:
    """Index a ui-screen item's render evidence as ``{state: [evidence_kind, ...]}``.

    Each Evidence_Record names the state it covers via an explicit ``state`` key
    or, per the design's Evidence_Record mapping, via ``test_name`` (= the
    ``screen/state`` id). Records with neither are not attributable to a state
    and are skipped (they cannot satisfy any state's render obligation).
    """
    index: Dict[str, List[Any]] = {}
    if not isinstance(evidence, list):
        return index
    for record in evidence:
        if not isinstance(record, dict):
            continue
        state = record.get("state")
        if not isinstance(state, str) or state == "":
            # Fall back to test_name as the state id (design Evidence_Record map).
            state = record.get("test_name")
        if not isinstance(state, str) or state == "":
            continue
        index.setdefault(state, []).append(record.get("evidence_kind"))
    return index


if __name__ == "__main__":
    # Smoke entry point: exercise each layer with a minimal passing example and
    # print the verdicts. Not a substitute for the Hypothesis property test
    # (tests/property/test_perf_a11y.py, task 39.21).
    import json

    perf = verify_performance(
        {"p95_ms": 180, "LCP": 2100}, {"p95_ms": 200, "LCP": 2500}
    )
    a11y = verify_accessibility({"violations": []})
    ui = verify_ui_screen(
        {
            "subtype": "ui-screen",
            "declared_states": ["empty", "loading", "error", "ready"],
            "evidence": [
                {"state": s, "evidence_kind": "behavioral"}
                for s in ("empty", "loading", "error", "ready")
            ],
        }
    )
    print(json.dumps({"perf": perf, "a11y": a11y, "ui_screen": ui}, indent=2))

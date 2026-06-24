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
    "SAST_HIGH_CRITICAL",
    "ORPHAN_DETECTED",
    "ORPHAN_DANGLING_REF",
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
    "SAST_HIGH_CRITICAL": (
        "Fix each HIGH or CRITICAL finding reported by semgrep, then re-run"
        " 'semgrep --baseline-commit <sha>' to confirm the findings are resolved."
    ),
    "ORPHAN_DETECTED": (
        "Forward orphan: reference an EXISTING requirement id (a fabricated or unknown"
        " id is itself a dangling-ref orphan — correct it). Backward orphan: route the"
        " missing proof to the VERIFIER, never self-grade. A new exemption outside"
        " tools/ is reviewed and fails the gate."
    ),
    "ORPHAN_DANGLING_REF": (
        "Correct the requirement id to an EXISTING id in feature_list.json, or have the"
        " requirement SEEDED as an unproven item before the code references it. Do not"
        " invent a trailer."
    ),
}


def self_heal_prompt(result: dict) -> str:
    return _HEAL.get(
        result.get("code", ""),
        "Resolve the evidence-gate rejection before re-attempting the proven transition.",
    )


# --------------------------------------------------------------------------- #
# Depth pillars (Task 4 §4.1-4.2): SAST + orphans. Both fail-OPEN on a tool error
# (a local depth pillar must never wedge the autonomous run — the CI gate is the
# binding backstop) and trivially ACCEPT on empty changed_files. Their fail-OPEN
# posture is DELIBERATELY separate from check_slice, which stays fail-CLOSED.
# --------------------------------------------------------------------------- #


def check_slice_semgrep(changed_files, baseline_commit) -> dict:
    """SAST depth check: semgrep on changed_files, blocking severities only.

    Returns {"accepted","code","reason"}. A blocking finding -> SAST_HIGH_CRITICAL;
    clean -> OK; empty/None changed_files -> OK (skip); ANY tool error (missing
    binary, timeout, crash, malformed JSON) -> OK + a 'warn' reason (fail-OPEN).
    NOTE: semgrep's JSON severity for a blocking finding is "ERROR" (WARNING=medium,
    INFO=low); HIGH/CRITICAL are also accepted for forward-compat.
    """
    if not changed_files:
        return {"accepted": True, "code": "OK", "reason": "no changed files; depth pillar skips"}

    import json as _json
    import subprocess

    from tools import execution_bounds as _eb

    # Build the command INSIDE the try — str(f) over changed_files, the baseline-strategy
    # lookup, and the timeout coercion all ran OUTSIDE it before, so a pathological
    # changed_files element (a __str__ that raises) propagated and could WEDGE the proof
    # path instead of failing-OPEN like the sibling check_slice_orphans (whole-branch I11).
    try:
        cmd = ["semgrep", "--config", "auto", "--json"]
        # F6: honor SEMGREP_BASELINE_STRATEGY — only attach the baseline when the
        # configured strategy enables it (anything but an explicit off/none/disabled).
        _strategy = str(getattr(_eb, "SEMGREP_BASELINE_STRATEGY", "auto")).lower()
        if baseline_commit and _strategy not in ("off", "none", "disabled"):
            cmd += ["--baseline-commit", str(baseline_commit)]
        cmd += [str(f) for f in changed_files]
        _timeout = int(getattr(_eb, "SEMGREP_TIMEOUT_SECONDS", 120))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_timeout)
    except FileNotFoundError:
        return {"accepted": True, "code": "OK", "reason": "semgrep binary not found; failing open (warn)"}
    except subprocess.TimeoutExpired:
        return {"accepted": True, "code": "OK", "reason": "semgrep timeout; failing open (warn)"}
    except Exception as exc:  # noqa: BLE001 — fail-OPEN on any subprocess error
        return {"accepted": True, "code": "OK", "reason": f"semgrep error ({type(exc).__name__}); failing open (warn)"}

    try:
        data = _json.loads(result.stdout or "{}")
    except (ValueError, _json.JSONDecodeError):
        return {"accepted": True, "code": "OK", "reason": "semgrep output malformed; failing open (warn)"}

    # F1: a well-formed-JSON-but-wrong-shape payload (`{"results": null}` or a
    # non-list) must FAIL-OPEN like any other tool malfunction — never raise.
    # Coerce results to a list of dicts and skip anything that is not a dict.
    if not isinstance(data, dict):
        return {"accepted": True, "code": "OK", "reason": "semgrep output not an object; failing open (warn)"}
    results = data.get("results")
    if not isinstance(results, list):
        results = []

    _BLOCKING = {"ERROR", "HIGH", "CRITICAL"}
    blocking = [
        f for f in results
        if isinstance(f, dict)
        and str((f.get("extra") or {}).get("severity", "")).upper() in _BLOCKING
    ]
    if blocking:
        return {"accepted": False, "code": "SAST_HIGH_CRITICAL",
                "reason": f"semgrep found {len(blocking)} blocking (HIGH/CRITICAL) finding(s)"}
    return {"accepted": True, "code": "OK", "reason": "semgrep clean (no blocking findings)"}


def _build_impl_units(changed_files, repo_root) -> list:
    """The changed ``.py`` files as impl-unit dicts ``{file, text}``; a non-.py, absent, or
    unreadable file is skipped (the read error is swallowed per-file, not fail-open-wide)."""
    impl_units = []
    for fp in changed_files:
        if not str(fp).endswith(".py"):
            continue
        full = repo_root / fp
        if not full.exists():
            continue
        try:
            impl_units.append({"file": fp, "text": full.read_text(encoding="utf-8")})
        except (UnicodeDecodeError, OSError):
            continue
    return impl_units


def _load_model_json(feature_list_path) -> dict:
    """The parsed feature_list.json, or ``{}`` when absent / unparseable / undecodable."""
    import json
    try:
        return json.loads(Path(feature_list_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _resolve_model_delta(baseline_commit, repo_root, model):
    """The PR-introduced model-delta id set for the diff-aware backward scope (F2), or None —
    no baseline, or an unreadable baseline ({}) → None (the core then conservatively checks
    all in-scope items, over-strict never under)."""
    if not baseline_commit:
        return None
    from tools.orphan_detector import _get_model_delta_ids, _load_feature_list_from_commit
    baseline_model = _load_feature_list_from_commit(baseline_commit, str(repo_root))
    return _get_model_delta_ids(baseline_model, model) if baseline_model else None


def _verdict_from_report(report) -> dict:
    """Map an orphan report to the depth-pillar verdict: a dangling-ref →
    ORPHAN_DANGLING_REF (first uid's message); any forward/backward orphan → ORPHAN_DETECTED
    (the fo[:3]/bo[:3] slice); else OK."""
    if report.get("dangling_refs"):
        uid = next(iter(report["dangling_refs"]))
        return {"accepted": False, "code": "ORPHAN_DANGLING_REF",
                "reason": report["dangling_refs"][uid]["message"]}
    fo = report.get("forward_orphans", [])
    bo = report.get("backward_orphans", [])
    if fo or bo:
        return {"accepted": False, "code": "ORPHAN_DETECTED",
                "reason": f"orphans — forward: {fo[:3]} backward: {bo[:3]}"}
    return {"accepted": True, "code": "OK", "reason": "no forward or backward orphans"}


def check_slice_orphans(changed_files, feature_list_path, known_ids,
                        baseline_commit=None, allowlist_dirs=None) -> dict:
    """Orphan depth check — DELEGATES to orphan_detector.detect_orphans_diff (the
    diff-aware, red-teamed core; §3.3-3.7) rather than re-implementing it.

    Forward orphan (changed .py minus allowlist, no req-id) or backward orphan
    (in-scope item with no artifact) -> ORPHAN_DETECTED. A unit citing an id absent
    from a NON-EMPTY model (REQ-WIRE-* exempt) -> ORPHAN_DANGLING_REF. Empty/None
    changed_files -> OK (skip). ANY tool/parse error -> OK + 'warn' (fail-OPEN).

    allowlist_dirs=None (default) sources the forward allowlist from
    execution_bounds.ORPHAN_ALLOWLIST_PATTERN via the core's config-default (§4.4 —
    thresholds/config are never hardcoded here). Pass an explicit tuple ONLY to
    override the configured pattern.

    baseline_commit, when supplied, scopes the BACKWARD pass to the PR-introduced
    model delta (the diff-aware contract, §3.3): the baseline feature_list is loaded
    from that commit and only added/modified item ids are checked. Without it, the
    backward pass conservatively checks ALL in-scope items (over-strict, never under).
    """
    if not changed_files:
        return {"accepted": True, "code": "OK", "reason": "no changed files; depth pillar skips"}
    try:
        import re as _re

        from tools.orphan_detector import detect_orphans_diff

        repo_root = Path(feature_list_path).resolve().parent
        impl_units = _build_impl_units(changed_files, repo_root)
        model = _load_model_json(feature_list_path)

        # Backward pass is over IN-SCOPE items only (§4.2 / Req 5.7), AND only when the model
        # file ITSELF is among the changed files. A slice that did not touch feature_list.json
        # introduces no model delta, hence no NEW backward orphan (diff-aware §3.3) — without
        # this a docs-only change wedges the advance on a pre-existing unproven item (F3).
        _fl_name = Path(feature_list_path).name
        model_changed = any(Path(str(f)).name == _fl_name for f in changed_files)
        requirements = (
            [i for i in model.get("items", []) if i.get("in_scope")]
            if model_changed else []
        )

        # F4: the dangling cross-check's known-id universe UNIONS the caller's known_ids with
        # every id already in the model, so a real seeded id is never mis-flagged dangling.
        model_ids = {i.get("id") for i in model.get("items", []) if i.get("id")}
        effective_known = set(known_ids or set()) | model_ids

        # F2: with a baseline, scope the BACKWARD pass to the PR-introduced model delta.
        model_delta_ids = _resolve_model_delta(baseline_commit, repo_root, model)

        # F3: allowlist_dirs=None -> "" -> the core applies the config-sourced default
        # (execution_bounds.ORPHAN_ALLOWLIST_PATTERN); an explicit tuple overrides it.
        allowlist_pattern = (
            "(" + "|".join(_re.escape(d) for d in allowlist_dirs) + ").*"
            if allowlist_dirs else ""
        )
        report = detect_orphans_diff(
            impl_units=impl_units,
            requirements=requirements,
            known_ids=effective_known,
            changed_files=set(changed_files),
            baseline_commit=baseline_commit,
            model_delta_ids=model_delta_ids,
            allowlist_pattern=allowlist_pattern,
        )
        return _verdict_from_report(report)
    except Exception as exc:  # noqa: BLE001 — fail-OPEN on any tool/parse error
        return {"accepted": True, "code": "OK",
                "reason": f"orphan check failed ({type(exc).__name__}); failing open (warn)"}

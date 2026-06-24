"""orphan_detector.py — bidirectional spec-to-evidence orphan check.

Spec: `.kiro/specs/spec-to-evidence-control/design.md` ("Orphan Detection")
      `.kiro/specs/spec-to-evidence-control/tasks.md` tasks 20.1 / 26.1
Requirement: REQ-6.3 (block the run on any orphan) / Property 11.

An *orphan* is a broken edge in the traceability graph, in either direction:

  * **forward orphan** — an implementation unit (file / function) that carries
    NO requirement-ID reference. It exists in code but is traceable to no
    requirement.
  * **backward orphan** — a requirement ID that maps to NO verification
    artifact (no impl unit references it AND/OR it has no test/evidence link).
    The requirement is declared but nothing proves it.

Both conditions INDEPENDENTLY trigger failure (Property 11): the check fails
when EITHER list is non-empty.

This module exposes two layers:

  1. A PURE, in-memory core — ``detect_orphans(impl_units, requirements)`` and
     ``scan_commit_trailers(text)`` — that takes already-parsed inputs and is
     trivially unit/property testable (the orchestrator + Property-11 contract).
  2. A thin ``main()`` CLI that loads ``feature_list.json`` + repo source,
     calls the core, prints the structured JSON report to stdout, and returns a
     non-zero exit when any orphan exists (the ``traceability-gate`` CI caller,
     task 40.4).

PURE STDLIB. The only requirement-ID regex lives in the shared
``tools/req_id_scan.py`` helper (imported below) so the pattern cannot drift
between this tool and ``traceability_writer.py`` (tasks.md 20.1 reconciliation,
"shared trailer helper").

Assurance level (design.md): orphan detection has ZERO Z3 coverage by design;
its assurance level is the runtime Hypothesis Property 11. Run as a CI gate
(not through a hook), it produces no ``gate_audit_log`` entry.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Shared, single-source requirement-ID extraction (also used by
# traceability_writer.py) — prevents regex drift between the two tools.
try:  # absolute import when ``tools`` is on sys.path / run as a script
    from req_id_scan import REQ_ID_RE, scan_req_ids
except ImportError:  # package-style import (``from tools.orphan_detector import ...``)
    from tools.req_id_scan import REQ_ID_RE, scan_req_ids  # type: ignore[no-redefine]

__all__ = [
    "detect_orphans",
    "scan_commit_trailers",
    "scan_source_text_for_req_ids",
    "main",
]

# Inline exemption marker (tasks.md 20.1, "forward-orphan exemption/allowlist").
# A unit annotated ``# orphan-exempt: <reason>`` is legitimately un-annotated
# (helpers, generated code, config) and does NOT count as a forward orphan.
ORPHAN_EXEMPT_MARKER = "orphan-exempt"

# Reason-required exemption (§3.2, T2): a bare "# orphan-exempt" (no reason) does
# NOT exempt — only "# orphan-exempt: <reason>" with a non-empty reason exempts.
# This makes a self-exemption a reviewed, justified surface rather than a free pass.
ORPHAN_EXEMPT_PATTERN = re.compile(r"#\s*orphan-exempt:\s*\S+")

# Default forward-scan path excludes (tasks.md 20.1 run-scope reconciliation):
# tests, generated/vendored dirs, package markers, and DB migrations are never
# forward orphans.
DEFAULT_EXCLUDE_DIRS = frozenset(
    {
        "tests",
        "test",
        "db/migrations",
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "build",
        "dist",
        ".kiro",
        "schema",
    }
)
DEFAULT_EXCLUDE_BASENAMES = frozenset({"__init__.py"})


# --------------------------------------------------------------------------- #
# Layer 1 — pure, in-memory core (orchestrator + Property-11 contract)
# --------------------------------------------------------------------------- #


def scan_commit_trailers(text: str) -> List[str]:
    """Extract requirement IDs from a commit message / trailer block.

    Returns the list of ``[A-Z]+-[A-Z]+-[0-9]{3}`` IDs present in ``text``,
    de-duplicated in first-seen order. Empty list when none are present (e.g. a
    commit with no requirement trailer). Delegates to the shared ``req_id_scan``
    helper so the pattern matches ``parse_commit_trailers`` in
    ``traceability_writer.py`` exactly.
    """
    return scan_req_ids(text)


# Backwards/forwards-compatible alias used elsewhere in the source scan path.
scan_source_text_for_req_ids = scan_commit_trailers


def _impl_unit_ref(unit: Dict[str, Any]) -> str:
    """Human-readable reference for an impl unit in the orphan report.

    Accepts the flexible unit dicts the in-memory API takes — any of
    ``ref`` / ``unit`` / ``function`` / ``name`` / ``file`` keys — and renders
    ``file::function`` when both are present.
    """
    explicit = unit.get("ref") or unit.get("unit")
    if explicit:
        return str(explicit)
    file_ = unit.get("file") or unit.get("path")
    func = unit.get("function") or unit.get("name") or unit.get("symbol")
    if file_ and func:
        return f"{file_}::{func}"
    return str(file_ or func or "<unknown-unit>")


def _impl_unit_is_exempt(unit: Dict[str, Any]) -> bool:
    """True when the unit is explicitly exempted from the forward-orphan rule.

    A unit is exempt when it carries an ``# orphan-exempt: <reason>`` marker
    (surfaced as ``exempt=True`` or an ``orphan_exempt``/``exempt_reason`` field
    by the source scanner) — legitimately un-annotated code that must not
    fail-noisy.
    """
    if unit.get("exempt") is True or unit.get("orphan_exempt") is True:
        return True
    reason = unit.get("exempt_reason") or unit.get("orphan_exempt_reason")
    if reason:
        return True
    text = unit.get("text") or unit.get("source") or ""
    # §3.2 (T2): reason REQUIRED — a bare "# orphan-exempt" does NOT exempt;
    # only "# orphan-exempt: <reason>" with a non-empty reason exempts.
    return bool(ORPHAN_EXEMPT_PATTERN.search(text))


def _impl_unit_req_ids(unit: Dict[str, Any]) -> List[str]:
    """All requirement IDs an impl unit references.

    Honors an explicit ``requirement_id`` / ``requirement_ids`` field when the
    caller already resolved them, and ALSO scans any raw ``text``/``source``
    body so a unit described only by its source is handled. The empty result
    means "no requirement ref" → forward-orphan candidate.
    """
    ids: List[str] = []
    single = unit.get("requirement_id")
    if single:
        ids.append(str(single))
    for key in ("requirement_ids", "requirements", "req_ids"):
        val = unit.get(key)
        if isinstance(val, (list, tuple, set)):
            ids.extend(str(v) for v in val)
        elif isinstance(val, str) and val:
            ids.append(val)
    text = unit.get("text") or unit.get("source")
    if text:
        ids.extend(scan_req_ids(text))
    # Keep only well-formed IDs, de-duplicated in order.
    seen: Dict[str, None] = {}
    for i in ids:
        if REQ_ID_RE.fullmatch(i) and i not in seen:
            seen[i] = None
    return list(seen.keys())


def _requirement_id(req: Dict[str, Any]) -> Optional[str]:
    rid = req.get("id") or req.get("requirement_id")
    return str(rid) if rid else None


def _requirement_has_artifact(req: Dict[str, Any], referenced_ids: Set[str]) -> bool:
    """True when a requirement maps to at least one verification artifact.

    A requirement is NOT a backward orphan when ANY of:
      * an impl unit references its ID (it appears in ``referenced_ids``), OR
      * it carries a non-empty ``evidence`` record / ``evidence[]`` list, OR
      * it carries a test/evidence traceability link
        (``traceability_links`` with ``link_type in {test, evidence}``), OR
      * it has an explicit ``has_artifact``/``verified`` truthy flag.

    This mirrors the canonical design definition: a backward orphan is a
    requirement ID with NO test/evidence link AND no evidence record AND no
    referencing impl unit.
    """
    rid = _requirement_id(req)
    if rid and rid in referenced_ids:
        return True
    if req.get("has_artifact") or req.get("verified"):
        return True
    evidence = req.get("evidence")
    if isinstance(evidence, dict) and evidence:
        return True
    if isinstance(evidence, (list, tuple)) and len(evidence) > 0:
        return True
    for link in req.get("traceability_links", []) or []:
        if isinstance(link, dict):
            if str(link.get("link_type", "")).lower() in {"test", "evidence"}:
                return True
        elif str(link).lower() in {"test", "evidence"}:
            return True
    if req.get("evidence_records"):
        return True
    return False


def _forward_pass(
    impl_units: List[Dict[str, Any]], known_ids: Set[str]
) -> Tuple[List[str], Set[str]]:
    """Forward orphan pass over impl units. Returns ``(forward_orphans, referenced_ids)``.
    A unit with no requirement ref (and not exempt) is a forward orphan; and — when a model
    is supplied (non-empty ``known_ids``; an EMPTY model is the pre-delivery local case and
    skips, §3.1/§7) — a reference to an id NOT in the model is a dangling-ref orphan
    (``[dangling-ref: …]`` string). WIRING-minted ids (REQ-WIRE-*) are exempt (§3.1 caveat, T1)."""
    forward_orphans: List[str] = []
    referenced_ids: Set[str] = set()
    for unit in impl_units:
        unit_ids = _impl_unit_req_ids(unit)
        if known_ids:
            for req_id in unit_ids:
                if not req_id.startswith("REQ-WIRE") and req_id not in known_ids:
                    forward_orphans.append(
                        f"{_impl_unit_ref(unit)} [dangling-ref: {req_id} not in model]"
                    )
        referenced_ids.update(unit_ids)
        if not unit_ids and not _impl_unit_is_exempt(unit):
            forward_orphans.append(_impl_unit_ref(unit))
    return forward_orphans, referenced_ids


def _backward_pass(
    requirements: List[Dict[str, Any]], referenced_ids: Set[str]
) -> List[str]:
    """Backward orphan pass: requirement ids that map to no verification artifact."""
    backward_orphans: List[str] = []
    for req in requirements:
        rid = _requirement_id(req)
        if rid is None:
            continue
        if not _requirement_has_artifact(req, referenced_ids):
            backward_orphans.append(rid)
    return backward_orphans


def detect_orphans(
    impl_units: List[Dict[str, Any]],
    requirements: List[Dict[str, Any]],
    known_ids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Bidirectional orphan detection over already-parsed inputs.

    Parameters
    ----------
    impl_units:
        Implementation units to check for FORWARD orphans. Each is a dict; a
        unit with no requirement-ID reference (and not exempted) is a forward
        orphan. Recognized keys: ``ref``/``file``/``function``/``name`` (for
        reporting), ``requirement_id``/``requirement_ids`` (resolved refs),
        ``text``/``source`` (raw body scanned for IDs), and
        ``exempt``/``exempt_reason`` (``# orphan-exempt`` marker).
    requirements:
        Requirement records to check for BACKWARD orphans. Each is a dict with
        an ``id``; a requirement that maps to no verification artifact is a
        backward orphan. (See ``_requirement_has_artifact`` for what counts.)

    Returns
    -------
    dict
        ``{"forward_orphans": [<impl unit refs>],
           "backward_orphans": [<requirement ids>],
           "ok": <bool>}``

        ``ok`` is ``True`` iff BOTH orphan lists are empty. Either condition
        independently makes ``ok`` False (Property 11 — both conditions
        independently trigger failure).
    """
    impl_units = impl_units or []
    requirements = requirements or []
    known_ids = known_ids or set()
    forward_orphans, referenced_ids = _forward_pass(impl_units, known_ids)
    backward_orphans = _backward_pass(requirements, referenced_ids)
    return {
        "forward_orphans": forward_orphans,
        "backward_orphans": backward_orphans,
        "ok": not forward_orphans and not backward_orphans,
    }


# --------------------------------------------------------------------------- #
# Diff-aware layer (Task 3 §3.3-3.7): scope the forward pass to changed .py files
# (minus the tools/ allowlist), the backward pass to feature_list.json
# model-deltas; fail CLOSED in CI when the merge-base is unreachable, full-repo
# fallback (+ logged reason) locally. The allowlist pattern is a REGEX
# (ORPHAN_DETECTOR default "tools/.*"), matched with re.match (start-anchored).
# --------------------------------------------------------------------------- #

# Allowlist regex default (§3 / §4.4): forward-orphan path exemption. SOURCED from
# execution_bounds (the config registry owns the value — thresholds-from-execution_bounds
# invariant), with a literal fallback only if that import is unavailable.
try:  # absolute import when ``tools`` is on sys.path / run as a script
    from execution_bounds import ORPHAN_ALLOWLIST_PATTERN as _DEFAULT_ALLOWLIST_PATTERN
except ImportError:  # package-style import
    try:
        from tools.execution_bounds import ORPHAN_ALLOWLIST_PATTERN as _DEFAULT_ALLOWLIST_PATTERN
    except ImportError:
        _DEFAULT_ALLOWLIST_PATTERN = "tools/.*"


# A git ref/commit reaching the OS `git` argv MUST look like a ref/SHA: it has to
# START with an alphanumeric and stay within a git-ref-safe charset. The leading-char
# rule is the security-relevant one — a value beginning with '-' (e.g. `--output=…`,
# `--upload-pack=…`) would be parsed by git as an OPTION rather than a commit, a CWE-88
# argument-injection vector even though every call here is shell=False (list argv).
# Baselines in practice are SHAs / branch names from --baseline-commit; anything else is
# rejected and the helper degrades to its fail-safe default (None / [] / {}).
_GIT_REF_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z._/-]{0,254}")


def _get_merged_base(baseline_ref: str, cwd: str = ".") -> Optional[str]:
    """The merge-base SHA between ``baseline_ref`` and HEAD, or None if unreachable."""
    if not baseline_ref or not _GIT_REF_RE.fullmatch(baseline_ref):
        return None  # CWE-88 argument-injection guard: not a legitimate git ref.
    try:
        result = subprocess.run(
            ["git", "merge-base", baseline_ref, "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # noqa: BLE001 — git absent/unreachable => None (caller decides)
        pass
    return None


def _get_changed_files(baseline_commit: str, cwd: str = ".") -> List[str]:
    """Relative paths changed between ``baseline_commit`` and HEAD (caller filters)."""
    if not baseline_commit or not _GIT_REF_RE.fullmatch(baseline_commit):
        return []  # CWE-88 argument-injection guard: not a legitimate git ref.
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", baseline_commit, "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
    except Exception:  # noqa: BLE001
        pass
    return []


def _load_feature_list_from_commit(commit_ref: str, cwd: str = ".") -> Dict[str, Any]:
    """Parsed feature_list.json at ``commit_ref``, or {} if absent/unparseable."""
    if not commit_ref or not _GIT_REF_RE.fullmatch(commit_ref):
        return {}  # CWE-88 argument-injection guard: not a legitimate git ref.
    try:
        result = subprocess.run(
            ["git", "show", f"{commit_ref}:feature_list.json"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:  # noqa: BLE001
        pass
    return {}


def _is_path_exempt(path: str, allowlist_pattern: str) -> bool:
    """True when ``path`` matches the forward-orphan allowlist REGEX (start-anchored).

    The pattern is a regex (default "tools/.*"), NOT a glob — re.match anchors at the
    start, so "tools/.*" exempts ``tools/anything`` and nothing outside ``tools/``.
    """
    if not allowlist_pattern:
        return False
    try:
        return bool(re.match(allowlist_pattern, path))
    except re.error:
        return False


def _filter_forward_units_by_changed(
    impl_units: List[Dict[str, Any]],
    changed_files: Optional[Set[str]],
    allowlist_pattern: str = "",
) -> List[Dict[str, Any]]:
    """Keep only units in a changed file, minus the allowlist. None => all units."""
    if changed_files is None:
        return impl_units
    changed = set(changed_files)
    filtered: List[Dict[str, Any]] = []
    for unit in impl_units:
        file_path = unit.get("file") or unit.get("path")
        if not file_path or file_path not in changed:
            continue
        if _is_path_exempt(file_path, allowlist_pattern):
            continue
        filtered.append(unit)
    return filtered


def _get_model_delta_ids(
    baseline_feature_list: Dict[str, Any],
    working_feature_list: Dict[str, Any],
) -> Set[str]:
    """Item IDs added or modified in feature_list.json relative to the baseline."""
    # Diff only the SEMANTIC fields (F2) — comparing whole dicts would treat any
    # auto-updating metadata field (e.g. a timestamp) as a modification and widen the
    # backward scope to the entire model, the explosion model-delta scoping prevents.
    _SEMANTIC = ("id", "type", "nfr_subtype", "status", "in_scope", "evidence",
                 "priority", "dependencies", "acceptance_criteria")

    def _proj(item: Dict[str, Any]) -> Dict[str, Any]:
        return {k: item.get(k) for k in _SEMANTIC}

    baseline_ids = {
        i.get("id"): _proj(i) for i in baseline_feature_list.get("items", []) if i.get("id")
    }
    delta: Set[str] = set()
    for i in working_feature_list.get("items", []):
        item_id = i.get("id")
        if not item_id:
            continue
        if item_id not in baseline_ids or baseline_ids[item_id] != _proj(i):
            delta.add(item_id)
    return delta


def _scope_diff_inputs(
    impl_units: List[Dict[str, Any]],
    requirements: List[Dict[str, Any]],
    changed_files: Optional[Set[str]],
    model_delta_ids: Optional[Set[str]],
    allowlist_pattern: str,
    baseline_commit: Optional[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    """Scope the diff-aware inputs → ``(filtered_units, scoped_requirements, fallback_reason)``.
    ``changed_files is None`` ⇒ full-repo fallback (+ a logged reason if a baseline was given);
    else forward = changed-files-minus-allowlist, backward = model-delta items only
    (``None`` ⇒ all; never path-exempt — a requirement still needs proof)."""
    if changed_files is None:
        fallback_reason = (
            f"diff not computed against {baseline_commit!r}; full-repo fallback (local)"
            if baseline_commit else None
        )
        return impl_units, requirements, fallback_reason
    filtered_units = _filter_forward_units_by_changed(impl_units, changed_files, allowlist_pattern)
    scoped_requirements = (
        [r for r in requirements if r.get("id") in model_delta_ids]
        if model_delta_ids is not None else requirements
    )
    return filtered_units, scoped_requirements, None


def _collect_dangling_refs(
    filtered_units: List[Dict[str, Any]], known_ids: Set[str]
) -> Dict[str, Dict[str, str]]:
    """Structured dangling-ref map: a forward unit citing an id NOT in the model (REQ-WIRE-*
    exempt). Empty when the model is empty (pre-delivery local case, §3.1) — consistent with
    detect_orphans, which also guards the cross-check on a non-empty model."""
    dangling_refs: Dict[str, Dict[str, str]] = {}
    if not known_ids:
        return dangling_refs
    for unit in filtered_units:
        for uid in _impl_unit_req_ids(unit):
            if uid not in known_ids and not uid.startswith("REQ-WIRE"):
                dangling_refs.setdefault(uid, {
                    "unit": _impl_unit_ref(unit),
                    "message": f"requirement ID '{uid}' does not exist in feature_list.json",
                })
    return dangling_refs


def _apply_dangling_refs(report: Dict[str, Any], dangling_refs: Dict[str, Dict[str, str]]) -> None:
    """Fold the structured dangling-ref map into ``report`` in place: attach it, set ok=False,
    and drop the ``[dangling-ref: …]`` strings detect_orphans pushed into forward_orphans so
    dangling_refs is the single structured source (F3 de-dup). No-op when empty."""
    if not dangling_refs:
        return
    report["dangling_refs"] = dangling_refs
    report["ok"] = False
    report["forward_orphans"] = [
        fo for fo in report.get("forward_orphans", [])
        if "[dangling-ref:" not in str(fo)
    ]


def detect_orphans_diff(
    impl_units: List[Dict[str, Any]],
    requirements: List[Dict[str, Any]],
    known_ids: Set[str],
    changed_files: Optional[Set[str]] = None,
    baseline_commit: Optional[str] = None,
    model_delta_ids: Optional[Set[str]] = None,
    allowlist_pattern: str = "",
    fail_closed_on_unreachable: bool = False,
    root: str = ".",
) -> Dict[str, Any]:
    """Diff-aware bidirectional orphan detection (Task 3 §3.3-3.7).

    Forward: scoped to ``changed_files`` (minus the ``allowlist_pattern`` regex).
    Backward: scoped to ``model_delta_ids`` (NEVER path-exempt — a requirement still
    needs proof). Dangling-ref: a unit citing only ids absent from ``known_ids``
    (REQ-WIRE-* exempt) is flagged. CI (``fail_closed_on_unreachable``): if the
    merge-base for ``baseline_commit`` is unreachable, fail CLOSED. Local: when
    ``changed_files is None`` (no diff), fall back to full-repo + a logged reason.
    """
    if not allowlist_pattern:
        allowlist_pattern = _DEFAULT_ALLOWLIST_PATTERN

    # CI fail-closed: an unreachable merge-base is a misconfiguration (fetch-depth:0),
    # never a silent full-repo widening of the gate (§3.4, closes T4).
    if fail_closed_on_unreachable and baseline_commit and _get_merged_base(baseline_commit, root) is None:
        return {
            "forward_orphans": [], "backward_orphans": [], "ok": False,
            "error": f"merge-base {baseline_commit!r} unreachable — fetch-depth:0 required "
                     f"(CI misconfiguration, not a degrade)",
        }

    filtered_units, scoped_requirements, fallback_reason = _scope_diff_inputs(
        impl_units, requirements, changed_files, model_delta_ids, allowlist_pattern, baseline_commit
    )
    report = detect_orphans(filtered_units, scoped_requirements, known_ids)
    if fallback_reason:
        report["baseline_fallback_reason"] = fallback_reason
    _apply_dangling_refs(report, _collect_dangling_refs(filtered_units, known_ids))
    return report


# --------------------------------------------------------------------------- #
# Layer 2 — CLI: load feature_list.json + repo source, then call the core
# --------------------------------------------------------------------------- #


def _load_feature_list(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _is_excluded_path(rel_path: str, exclude_dirs: Set[str]) -> bool:
    parts = rel_path.replace(os.sep, "/").split("/")
    if os.path.basename(rel_path) in DEFAULT_EXCLUDE_BASENAMES:
        return True
    for ex in exclude_dirs:
        ex_parts = ex.strip("/").split("/")
        # match a contiguous path segment run anywhere in the path
        for i in range(len(parts) - len(ex_parts) + 1):
            if parts[i : i + len(ex_parts)] == ex_parts:
                return True
    return False


def _scan_repo_impl_units(
    root: str, exclude_dirs: Set[str]
) -> List[Dict[str, Any]]:
    """Walk ``root`` for Python source files and turn each into an impl unit.

    File-level granularity (task 20.1: function-level via inline marker is
    handled by the exemption marker; file-level is the scan unit). Each file
    becomes one unit whose ``text`` is its full source — so both real
    requirement-ID references in comments/docstrings AND an inline
    ``# orphan-exempt`` marker are picked up by the pure core.
    """
    units: List[Dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded directories in place for efficiency
        dirnames[:] = [
            d
            for d in dirnames
            if not _is_excluded_path(
                os.path.relpath(os.path.join(dirpath, d), root), exclude_dirs
            )
        ]
        for name in filenames:
            if not name.endswith(".py"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            if _is_excluded_path(rel, exclude_dirs):
                continue
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    source = fh.read()
            except OSError:
                continue
            units.append({"file": rel, "text": source})
    return units


def _requirements_from_feature_list(feature_list: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(feature_list.get("items", []) or [])


def _build_arg_parser() -> argparse.ArgumentParser:
    """The orphan_detector CLI parser (--feature-list/--links/--root/--baseline-commit/
    --exempt-paths)."""
    parser = argparse.ArgumentParser(
        prog="orphan_detector.py",
        description="Bidirectional spec-to-evidence orphan check (REQ-6.3 / Property 11).",
    )
    parser.add_argument(
        "--feature-list",
        default="feature_list.json",
        help="Path to feature_list.json (the coverage model / requirement IDs).",
    )
    parser.add_argument(
        "--links",
        default=None,
        help="Optional path to a traceability_links JSON file (test/evidence links).",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repo root to scan for implementation units (default: cwd).",
    )
    parser.add_argument(
        "--baseline-commit",
        default=None,
        help="Diff-aware mode: orphan-check ONLY the PR's changes against this base "
             "(merge-base sha). CI fail-CLOSED if the merge-base is unreachable.",
    )
    parser.add_argument(
        "--exempt-paths",
        default=None,
        help="Forward-orphan allowlist as a glob (e.g. 'tools/**'); a changed file under "
             "it is exempt from the forward (no-req) orphan check. Diff-aware mode only.",
    )
    return parser


def _confine_to_root(path: str, root: str) -> str:
    """CWE-22 path-traversal guard: resolve ``path`` and confirm it stays WITHIN ``root`` (the
    scanned repo tree), so a crafted ``--feature-list`` / ``--links`` cannot make the CLI read
    a file outside the repo. Returns the resolved path; raises ``ValueError`` when it escapes
    ``root``. Real CI + test usage always passes files within ``--root``, so this only rejects
    a genuine traversal — it is a security guard, not a behavioural change for legitimate use."""
    root_real = os.path.realpath(root)
    resolved = os.path.realpath(path)
    if resolved != root_real and not resolved.startswith(root_real + os.sep):
        raise ValueError(f"path {path!r} escapes the scan root {root!r}")
    return resolved


def _load_model_or_error(
    path: str, root: str
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Load feature_list.json → ``(model, None)``, or ``(None, error_report)`` on an
    OSError/JSONDecodeError/traversal. ``path`` is confined to ``root`` first (CWE-22); a
    traversal attempt is a load failure (fail-closed). The error report is the COMPACT
    (no-indent) JSON the gate's load-failure contract expects (distinct from the indented
    success report)."""
    try:
        return _load_feature_list(_confine_to_root(path, root)), None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return None, {
            "forward_orphans": [],
            "backward_orphans": [],
            "ok": False,
            "error": f"cannot load feature_list: {exc}",
        }


def _fold_in_links(requirements: List[Dict[str, Any]], links_path: str, root: str) -> None:
    """Fold an optional external links file into each requirement's ``traceability_links``
    (in place) so the backward-orphan lookup sees test/evidence links not inlined in the
    coverage model. ``links_path`` is confined to ``root`` (CWE-22). Absence / parse-failure /
    traversal is non-fatal — links are an enrichment, so an out-of-root path is silently ignored."""
    try:
        with open(_confine_to_root(links_path, root), "r", encoding="utf-8") as fh:
            links_doc = json.load(fh)
        links_by_req: Dict[str, List[Any]] = {}
        for link in links_doc if isinstance(links_doc, list) else links_doc.get("links", []):
            rid = link.get("requirement_id") or link.get("id")
            if rid:
                links_by_req.setdefault(str(rid), []).append(link)
        for req in requirements:
            rid = _requirement_id(req)
            if rid and rid in links_by_req:
                merged = list(req.get("traceability_links", []) or [])
                merged.extend(links_by_req[rid])
                req["traceability_links"] = merged
    except (OSError, json.JSONDecodeError, ValueError):
        pass  # links are an optional enrichment; absence / traversal is not fatal


def _run_diff_aware(
    args: argparse.Namespace,
    impl_units: List[Dict[str, Any]],
    requirements: List[Dict[str, Any]],
    feature_list: Dict[str, Any],
) -> Dict[str, Any]:
    """Diff-aware orphan check (the traceability-gate CI path): orphan-check ONLY the PR's
    changes vs the merge-base, CI fail-CLOSED on an unreachable base (§3.3/§3.4). The BACKWARD
    pass is scoped to the PR's model-delta (red-team I3); an unreadable baseline model → None →
    conservative all-in-scope (the fail-closed direction), consistent with detect_orphans_diff."""
    known_ids = {rid for r in requirements if (rid := _requirement_id(r))}
    changed_files = set(_get_changed_files(args.baseline_commit, args.root))
    allowlist_pattern = _exempt_glob_to_regex(args.exempt_paths) if args.exempt_paths else ""
    baseline_model = _load_feature_list_from_commit(args.baseline_commit, args.root)
    model_delta_ids = (
        _get_model_delta_ids(baseline_model, feature_list) if baseline_model else None
    )
    return detect_orphans_diff(
        impl_units=impl_units, requirements=requirements, known_ids=known_ids,
        changed_files=changed_files, baseline_commit=args.baseline_commit,
        model_delta_ids=model_delta_ids, allowlist_pattern=allowlist_pattern,
        fail_closed_on_unreachable=True, root=args.root,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.

    Loads ``feature_list.json`` (requirement IDs + their evidence/links) and the
    repo Python source (impl units), runs ``detect_orphans``, prints the
    structured JSON report to stdout, and returns the exit code:
    ``0`` when ``ok`` (no orphans), ``1`` when any orphan exists — the
    "block the run" contract consumed by the ``traceability-gate`` CI check.
    """
    args = _build_arg_parser().parse_args(argv)
    feature_list, error = _load_model_or_error(args.feature_list, args.root)
    if error is not None:
        print(json.dumps(error))   # COMPACT (no indent) — the load-failure contract.
        return 1
    requirements = _requirements_from_feature_list(feature_list)
    if args.links:
        _fold_in_links(requirements, args.links, args.root)
    impl_units = _scan_repo_impl_units(args.root, set(DEFAULT_EXCLUDE_DIRS))
    if args.baseline_commit:
        report = _run_diff_aware(args, impl_units, requirements, feature_list)
    else:
        report = detect_orphans(impl_units, requirements)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


def _exempt_glob_to_regex(glob: str) -> str:
    """Convert a forward-orphan allowlist glob (``tools/**``) to the start-anchored regex
    detect_orphans_diff expects (re.match): ``**`` -> ``.*``, ``*`` -> ``[^/]*``."""
    return re.escape(glob).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")


if __name__ == "__main__":
    sys.exit(main())

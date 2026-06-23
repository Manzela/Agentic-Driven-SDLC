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
import sys
from typing import Any, Dict, List, Optional, Set

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

    # Forward pass: impl units with no requirement ref (excluding exempt ones).
    forward_orphans: List[str] = []
    referenced_ids: Set[str] = set()
    for unit in impl_units:
        unit_ids = _impl_unit_req_ids(unit)

        # Validity cross-check (§3.1, T1): when a model is supplied (non-empty
        # known_ids — an EMPTY model is the pre-delivery local case and skips,
        # §3.1/§7), a reference to an id NOT in the model is a dangling-ref
        # orphan. WIRING-minted ids (REQ-WIRE-*) are exempt — they are minted
        # per-analysis and may not yet be in the committed model (§3.1 caveat).
        if known_ids:
            for req_id in unit_ids:
                if not req_id.startswith("REQ-WIRE") and req_id not in known_ids:
                    forward_orphans.append(
                        f"{_impl_unit_ref(unit)} [dangling-ref: {req_id} not in model]"
                    )

        referenced_ids.update(unit_ids)
        if not unit_ids and not _impl_unit_is_exempt(unit):
            forward_orphans.append(_impl_unit_ref(unit))

    # Backward pass: requirements that map to no verification artifact.
    backward_orphans: List[str] = []
    for req in requirements:
        rid = _requirement_id(req)
        if rid is None:
            continue
        if not _requirement_has_artifact(req, referenced_ids):
            backward_orphans.append(rid)

    ok = not forward_orphans and not backward_orphans
    return {
        "forward_orphans": forward_orphans,
        "backward_orphans": backward_orphans,
        "ok": ok,
    }


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


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.

    Loads ``feature_list.json`` (requirement IDs + their evidence/links) and the
    repo Python source (impl units), runs ``detect_orphans``, prints the
    structured JSON report to stdout, and returns the exit code:
    ``0`` when ``ok`` (no orphans), ``1`` when any orphan exists — the
    "block the run" contract consumed by the ``traceability-gate`` CI check.
    """
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
    args = parser.parse_args(argv)

    try:
        feature_list = _load_feature_list(args.feature_list)
    except (OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "forward_orphans": [],
                    "backward_orphans": [],
                    "ok": False,
                    "error": f"cannot load feature_list: {exc}",
                }
            )
        )
        return 1

    requirements = _requirements_from_feature_list(feature_list)

    # Fold an optional external links file into the requirement records so the
    # backward-orphan lookup can see test/evidence links not inlined in the
    # coverage model.
    if args.links:
        try:
            with open(args.links, "r", encoding="utf-8") as fh:
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
        except (OSError, json.JSONDecodeError):
            pass  # links are an optional enrichment; absence is not fatal

    impl_units = _scan_repo_impl_units(args.root, set(DEFAULT_EXCLUDE_DIRS))

    report = detect_orphans(impl_units, requirements)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

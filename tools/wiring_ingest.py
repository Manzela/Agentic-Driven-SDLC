"""wiring_ingest.py — ingest WIRING candidates into feature_list.json + verifier flip.

Spec: docs/superpowers/specs/2026-06-23-phase1-verification-depth-design.md
  § 2.2 / task 19.3  (WIRING ingestion write-path)
  § 2.3 / task 8.2   (verifier unproven->failed flip for unreachable symbols)

``ingest_wiring_candidates`` reads ``wiring_checker.emit_wiring_items()`` output
(type="WIRING", status="unproven" CoverageItem candidates) and APPENDS the ones not
already present (de-dup by stable id) — the legitimate unproven-birth path the Task-7
PreToolUse insertion permit opened.

``mark_wiring_failed`` is the VERIFIER-OWNED ``unproven -> failed`` transition (Req 8.2):
when a WIRING symbol is confirmed unreachable, the verifier flips its item. Like the
verifier's evidence prover (prove_trivial_slice), it writes the model file directly —
its authority is the verifier session it runs in, not a tool-layer gate. Only WIRING
items are ever touched; the write is atomic (temp file + os.replace) and append-order is
preserved (status flips in place, items never reordered).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.feature_list_init import (  # noqa: E402
    normalize_item,
    validate_against_schema,
)

__all__ = ["ingest_wiring_candidates", "mark_wiring_failed"]


def _load_model(feature_list_path: str):
    """Return the parsed model dict, or None when absent / unreadable / wrong-shape."""
    flist_path = Path(feature_list_path)
    if not flist_path.exists():
        return None
    try:
        content = json.loads(flist_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    if not isinstance(content, dict) or not isinstance(content.get("items"), list):
        return None
    return content


def _atomic_write(content: Dict[str, Any], feature_list_path: str) -> bool:
    """Write ``content`` to ``feature_list_path`` atomically (same-dir temp + os.replace,
    so a crash mid-write never leaves a truncated model). Returns True on success."""
    flist_path = Path(feature_list_path)
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(
            dir=str(flist_path.parent), prefix=".wiring_ingest_", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            # Match write_feature_list's POSIX-correct trailing newline (F-6) so an
            # ingest does not introduce a spurious "No newline at end of file" diff.
            fh.write(json.dumps(content, indent=2) + "\n")
        os.replace(temp_path, str(flist_path))
    except OSError:
        # Clean up the temp file on ANY failure — including an os.replace error after
        # a successful dump (F-2: the old code only unlinked on a dump failure).
        if temp_path is not None and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        return False
    return True


def ingest_wiring_candidates(candidates: List[Dict[str, Any]], feature_list_path: str) -> int:
    """Append WIRING candidates to feature_list.json as unproven items, de-duped by id.

    Append-only: existing items are never mutated (the verifier owns status flips). A
    candidate whose id already exists is skipped. Returns the count actually written
    (<= len(candidates)); 0 if the model is absent/unreadable or nothing new was added.
    """
    if not candidates:
        return 0
    content = _load_model(feature_list_path)
    if content is None:
        return 0

    items = content["items"]

    def _qual(it: Dict[str, Any]):
        return (it.get("wiring") or {}).get("qualname") if isinstance(it, dict) else None

    # De-dup by the STABLE symbol identity (wiring.qualname), NOT the ordinal id.
    # emit_wiring_items mints REQ-WIRE-NNN by POSITION, so prepending a function shifts
    # every later id — id-keyed de-dup then drops a genuinely-new symbol and duplicates
    # an existing one (red-team F-3). qualname is position-independent. (A candidate
    # without a qualname falls back to id de-dup.)
    existing_quals: Set[str] = {q for q in (_qual(it) for it in items) if q is not None}
    existing_ids: Set[str] = {it.get("id") for it in items if isinstance(it, dict) and "id" in it}

    appended: List[Dict[str, Any]] = []
    for candidate in candidates:
        qual = _qual(candidate)
        cand_id = candidate.get("id")
        if qual is not None:
            if qual in existing_quals:
                continue
        elif cand_id is None or cand_id in existing_ids:
            continue
        # Normalize so a candidate missing a schema default is filled, never appended raw.
        norm = normalize_item(candidate)
        items.append(norm)
        appended.append(norm)
        if qual is not None:
            existing_quals.add(qual)
        if cand_id is not None:
            existing_ids.add(cand_id)

    if not appended:
        return 0
    # Never persist a schema-invalid model (F-1): validate the FULL post-append content
    # first and REFUSE the write (returning 0, file untouched) if it would corrupt.
    try:
        validate_against_schema(content)
    except Exception:  # noqa: BLE001 — any validation failure rolls back the in-memory append.
        for it in appended:
            items.remove(it)
        return 0
    return len(appended) if _atomic_write(content, feature_list_path) else 0


def mark_wiring_failed(feature_list_path: str, unreachable_qualnames: Set[str]) -> int:
    """Verifier-owned ``unproven -> failed`` flip for unreachable WIRING symbols (Req 8.2).

    For each WIRING item whose ``wiring.qualname`` is in ``unreachable_qualnames`` AND is
    currently ``unproven``, transition it to ``failed``. Non-WIRING items are never
    touched; an already-failed (or otherwise non-unproven) item is left as-is (idempotent).
    Returns the count actually transitioned; 0 if the file is absent, nothing matched, or
    the write failed.
    """
    if not unreachable_qualnames:
        return 0
    content = _load_model(feature_list_path)
    if content is None:
        return 0

    flipped = 0
    for item in content["items"]:
        if not isinstance(item, dict) or item.get("type") != "WIRING":
            continue
        if item.get("status") != "unproven":
            continue
        wiring = item.get("wiring") or {}
        # Defense-in-depth (F-5): refuse to fail a symbol the analysis found REACHABLE,
        # even if the caller passes its qualname. Only a wiring.reachable == False item
        # is eligible — a reachable obligation must be PROVEN, never failed.
        if wiring.get("reachable") is not False:
            continue
        if wiring.get("qualname") in unreachable_qualnames:
            item["status"] = "failed"
            flipped += 1

    if flipped == 0:
        return 0
    return flipped if _atomic_write(content, feature_list_path) else 0

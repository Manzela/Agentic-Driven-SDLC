"""ci_evidence_check.py — CI step: the parts the rego cannot do.

Re-derives each proven item's output_hash from the captured artifact on disk and
cross-checks the session ids against the dispatch ledger, via evidence_gate.
PHASE A: the ledger is TRUSTED (Phase B adds cryptographic attestation). Exit 1
on any rejection (merge denied); exit 0 only when every proven item passes.

ABSENT-INPUT CONTRACT (consistent with the coverage-gate deny_merge step):
  * feature_list.json absent → SKIP gracefully (exit 0).  The coverage model is
    a runtime artifact; its absence is the normal pre-delivery state.
  * dispatch_ledger.json absent → SKIP gracefully (exit 0).  The ledger is
    provisioned only once the dispatch plane has run; its absence before first
    delivery is equally valid.
Both inputs must be present for the gate to do real work.

PATH-TRAVERSAL GUARD:
  Artifact test_file values from feature_list.json are untrusted.  Each resolved
  path is checked to confirm it stays inside artifacts_dir before being opened.
  Any traversal attempt (relative ``../`` sequences or absolute paths escaping
  the directory) is treated as HASH_MISMATCH — the item is rejected, not skipped.

ENCODING:
  All text files (feature_list, ledger, artifact) are read with encoding='utf-8'
  so that hash re-derivation (which encodes as UTF-8 in evidence_gate._rederive)
  is consistent across CI hosts regardless of the locale setting.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import evidence_gate  # noqa: E402

_SKIP_MSG_FL = (
    "ci-evidence-check: feature_list.json not present — "
    "pre-delivery state, skipping gracefully (gate passes)."
)
_SKIP_MSG_LED = (
    "ci-evidence-check: dispatch_ledger.json not present — "
    "pre-delivery state, skipping gracefully (gate passes)."
)


def _safe_read_artifact(artifacts_dir: Path, test_file: str) -> str | None:
    """Return artifact text only if the resolved path is inside artifacts_dir.

    Returns None (treated as HASH_MISMATCH downstream) when:
      * test_file is empty / None
      * the resolved path escapes artifacts_dir (traversal attempt)
      * the file does not exist on disk
    """
    if not test_file:
        return None
    base = artifacts_dir.resolve()
    # Resolve without following symlinks that could escape the directory.
    candidate = (base / test_file).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        # Path escapes artifacts_dir — path traversal attempt; treat as missing.
        return None
    if not candidate.is_file():
        return None
    return candidate.read_text(encoding="utf-8")


def run(*, feature_list_path: str | Path, artifacts_dir: str | Path, ledger_path: str | Path) -> int:
    fl_path = Path(feature_list_path)
    led_path = Path(ledger_path)
    art_dir = Path(artifacts_dir)

    # ABSENT-INPUT CONTRACT — skip gracefully when either required input is absent.
    if not fl_path.is_file():
        print(_SKIP_MSG_FL)
        return 0
    if not led_path.is_file():
        print(_SKIP_MSG_LED)
        return 0

    model = json.loads(fl_path.read_text(encoding="utf-8"))
    ledger = json.loads(led_path.read_text(encoding="utf-8"))

    artifacts: dict[str | None, str | None] = {}
    for item in model.get("items", []):
        ev = item.get("evidence") or {}
        tf = ev.get("test_file")
        artifacts[item.get("id")] = _safe_read_artifact(art_dir, tf) if tf else None

    res = evidence_gate.check_model(model=model, ledger=ledger, artifacts=artifacts)
    if not res["accepted"]:
        for r in res["rejections"]:
            print(f"DENY {r['id']}: [{r['code']}] {r['reason']}", file=sys.stderr)
        return 1
    print("evidence gate: all proven items independently re-verified")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    fl, arts, led = (
        list(argv) + ["feature_list.json", "artifacts", "dispatch_ledger.json"]
    )[:3]
    return run(feature_list_path=fl, artifacts_dir=arts, ledger_path=led)


if __name__ == "__main__":
    sys.exit(main())

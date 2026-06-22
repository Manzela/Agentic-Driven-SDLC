"""ci_evidence_check.py — CI step: the parts the rego cannot do.

Re-derives each proven item's output_hash from the captured artifact on disk and
cross-checks the session ids against the dispatch ledger, via evidence_gate.
PHASE A: the ledger is TRUSTED (Phase B adds cryptographic attestation). Exit 1
on any rejection (merge denied); exit 0 only when every proven item passes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import evidence_gate  # noqa: E402

def run(*, feature_list_path, artifacts_dir, ledger_path) -> int:
    model = json.loads(Path(feature_list_path).read_text())
    ledger = json.loads(Path(ledger_path).read_text())
    artifacts = {}
    for item in model.get("items", []):
        ev = item.get("evidence") or {}
        tf = ev.get("test_file")
        p = Path(artifacts_dir) / tf if tf else None
        artifacts[item.get("id")] = p.read_text() if (p and p.is_file()) else None
    res = evidence_gate.check_model(model=model, ledger=ledger, artifacts=artifacts)
    if not res["accepted"]:
        for r in res["rejections"]:
            print(f"DENY {r['id']}: [{r['code']}] {r['reason']}", file=sys.stderr)
        return 1
    print("evidence gate: all proven items independently re-verified")
    return 0

def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    fl, arts, led = (argv + ["feature_list.json", "artifacts", "dispatch_ledger.json"])[:3]
    return run(feature_list_path=fl, artifacts_dir=arts, ledger_path=led)

if __name__ == "__main__":
    sys.exit(main())

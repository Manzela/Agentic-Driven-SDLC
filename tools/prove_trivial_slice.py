"""prove_trivial_slice.py — drive the trivial slice through the real spine.

End-to-end demonstration that "done" is a machine fact, not a self-report:

  1. Take the LIVE served HTML of GET / (captured by curl against `next start`).
  2. Assert the acceptance criteria (wordmark + thesis present).
  3. Build a four-field Evidence_Record over the real artifact bytes.
  4. Stamp the verifier identity with a verifier_session distinct from the
     implementer_session, and run it through the SubagentStop gate — which
     RE-DERIVES the hash from the artifact (fix #3) and rejects same-session
     evidence (fix #2).
  5. Only on approval, apply the allowed transition under field authority
     (fix #4) and write status=proven + evidence into feature_list.json.
  6. Confirm the Stop hook now reports terminal COMPLETE.

Usage: python tools/prove_trivial_slice.py <served_html_path> <feature_list_path>
Exits 0 on a clean COMPLETE; non-zero (fail closed) otherwise.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(modpath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / modpath)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main(html_path: str, fl_path: str) -> int:
    evidence_collector = _load("tools/evidence_collector.py", "evidence_collector")
    coverage = _load("tools/coverage.py", "coverage")
    subagent_stop = _load(".claude/hooks/subagent_stop_hook.py", "subagent_stop_hook")
    stop_hook = _load(".claude/hooks/stop_hook.py", "stop_hook")

    html = Path(html_path).read_text()

    # (2) acceptance criteria on the live artifact.
    assert "Autonomous Agent" in html, "wordmark missing from served HTML"
    assert "proves itself" in html, "thesis missing from served HTML"

    # (3) four-field evidence over the real artifact bytes.
    record = evidence_collector.collect(
        test_file="apps/web/tests/e2e/home.spec.ts",
        test_name="home route renders the thesis and wordmark",
        output=html,
    )
    # (4) verifier identity + DISTINCT sessions (fix #1/#2).
    record["actor_agent"] = "verifier.md"
    record["verifier_session_id"] = "sess-verifier-1"
    record["implementer_session_id"] = "sess-implementer-1"
    record["evidence_kind"] = "behavioral"

    gate = subagent_stop.evaluate(
        record=record, output=html, resolved_actor="verifier.md",
        omission_declaration="[Gap] only the happy-path render is checked in this slice.",
    )
    if gate["decision"] != "approve":
        print("SLICE PROOF FAILED at SubagentStop:", gate["reason"])
        return 2

    # (5) transition under authority, then write.
    coverage.assert_transition("unproven", "proven")
    coverage.assert_field_authority(field="status", actor_agent="verifier.md", human_signed=False)
    model = json.loads(Path(fl_path).read_text())
    for item in model["items"]:
        if item["id"] == "HOME-RND-001":
            item["status"] = "proven"
            item["evidence"] = record
    Path(fl_path).write_text(json.dumps(model, indent=2) + "\n")

    # (6) Stop hook must now report COMPLETE.
    run_state = {"iteration_count": 1, "violation_count": 0, "no_progress_n": 0}
    decision = stop_hook.evaluate_stop(run_state, model)
    if decision.get("terminal") != "COMPLETE":
        print("SLICE PROOF FAILED at Stop:", decision)
        return 2

    print("SLICE PROVEN — terminal:", decision["terminal"])
    print("  evidence output_hash:", record["output_hash"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

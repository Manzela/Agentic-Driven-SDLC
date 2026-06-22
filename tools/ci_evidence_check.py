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

PROTECTED-BASELINE OVERRIDE (Phase A.5):
  The absent-feature_list "skip" above is conditional. A TRUSTED baseline
  (dispatcher-owned, delivered OUT-OF-BAND — NEVER read from the PR payload) may
  declare which item ids were in-scope for this delivery. When such a baseline is
  present, baseline_gate (tools/baseline_gate.py) runs FIRST and the skip is
  suppressed: an absent model (RT-01) or a shrunk / item-removed model (RT-02)
  DENIES the merge instead of skipping. The skip survives ONLY when no baseline
  expects a delivery. The baseline is trusted in Phase A.5; Phase B signs it.

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
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import baseline_gate as _bg  # noqa: E402
from tools import evidence_gate  # noqa: E402

_SKIP_MSG_FL = (
    "ci-evidence-check: feature_list.json not present — "
    "pre-delivery state, skipping gracefully (gate passes)."
)
_SKIP_MSG_LED = (
    "ci-evidence-check: dispatch_ledger.json not present — "
    "pre-delivery state, skipping gracefully (gate passes)."
)


class _BaselineTrustError(Exception):
    """Raised when the baseline path violates the trust boundary (fail closed).

    The baseline MUST reach CI from a source the agent cannot tamper with and is
    NEVER read from the PR payload surface. The PR payload surface == the checkout
    populated from PR HEAD, i.e. GITHUB_WORKSPACE. A baseline that resolves INSIDE
    GITHUB_WORKSPACE is — by definition — a file the PR author could have committed,
    so trusting it would neutralize RT-01/RT-02. We reject it fail-closed regardless
    of what the YAML wiring did, so a workflow regression cannot silently re-open the
    bypass.
    """


def _assert_baseline_out_of_band(baseline_path: Path) -> None:
    """Fail closed if ``baseline_path`` lives inside the agent-controlled checkout.

    Enforced ONLY when GITHUB_WORKSPACE is set (i.e. on a GitHub-hosted runner). The
    baseline is trusted only when it is staged OUTSIDE the PR checkout (e.g. into
    ``$RUNNER_TEMP/trusted-baseline``). If the resolved baseline path is the workspace
    root or any descendant of it, the file is on the PR payload surface and is
    untrustworthy — raise so ``run`` denies the merge.
    """
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if not workspace:
        return  # Not on a GitHub runner (unit tests, local) — no workspace surface.
    try:
        ws = Path(workspace).resolve()
    except OSError:
        return
    resolved = baseline_path.resolve()
    if resolved == ws or ws in resolved.parents:
        raise _BaselineTrustError(
            "baseline path "
            f"{resolved} resolves INSIDE GITHUB_WORKSPACE ({ws}) — the agent-"
            "controlled PR checkout. The protected baseline MUST be staged out-of-band "
            "(e.g. $RUNNER_TEMP/trusted-baseline), NEVER read from the PR payload. "
            "Fail closed (RT-01/RT-02 trust boundary)."
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


def run(
    *,
    feature_list_path: str | Path,
    artifacts_dir: str | Path,
    ledger_path: str | Path,
    baseline_path: str | Path | None = None,
) -> int:
    fl_path = Path(feature_list_path)
    led_path = Path(ledger_path)
    art_dir = Path(artifacts_dir)

    # PROTECTED BASELINE (Phase A.5). The baseline declares which item ids were
    # in-scope for this delivery. It is TRUSTED in Phase A.5 (Phase B signs it) and
    # MUST reach CI from an out-of-band source the agent cannot tamper with (a
    # protected CI artifact / branch / secret) — it is NEVER read from the PR payload
    # alongside feature_list.json (that is the very thing the agent controls). See
    # tools/baseline_gate.py and .github/workflows/coverage-gate.yml.
    baseline = None
    if baseline_path is not None:
        bl_path = Path(baseline_path)
        # TRUST-BOUNDARY ENFORCEMENT (defense in depth). Even if the workflow YAML
        # regresses and points us at a PR-resident path, refuse to trust a baseline
        # that lives inside the agent-controlled checkout. Fail CLOSED on violation.
        try:
            _assert_baseline_out_of_band(bl_path)
        except _BaselineTrustError as exc:
            print(f"DENY baseline: {exc}", file=sys.stderr)
            return 1
        if bl_path.is_file():
            baseline = json.loads(bl_path.read_text(encoding="utf-8"))

    # The model may legitimately be absent (pre-delivery). Read it (or None) so the
    # baseline gate can decide whether that absence is acceptable.
    model = json.loads(fl_path.read_text(encoding="utf-8")) if fl_path.is_file() else None

    # Baseline gate FIRST (fails CLOSED). When a baseline expects a delivery, an
    # absent (RT-01) or shrunk / item-removed (RT-02) coverage model denies the merge.
    bg = _bg.baseline_gate(baseline=baseline, feature_list=model)
    if bg["deny"]:
        for r in bg["reasons"]:
            print(f"DENY baseline: {r}", file=sys.stderr)
        return 1

    # ABSENT-INPUT CONTRACT — skip gracefully when either required input is absent.
    # This is now safe: the baseline gate above has confirmed no baseline expected a
    # delivery (an expected-but-absent model would already have denied above).
    if model is None:
        print(_SKIP_MSG_FL)
        return 0
    if not led_path.is_file():
        print(_SKIP_MSG_LED)
        return 0

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


def _default_baseline_path() -> str:
    """Out-of-band default for the trusted baseline.

    Prefer ``$RUNNER_TEMP/trusted-baseline/coverage_baseline.json`` — a path the CI
    workflow stages OUTSIDE GITHUB_WORKSPACE (the agent-controlled PR checkout). When
    RUNNER_TEMP is unset (local / unit runs) fall back to a relative filename; the
    trust-boundary guard (``_assert_baseline_out_of_band``) is a no-op off-runner.
    """
    runner_temp = os.environ.get("RUNNER_TEMP")
    if runner_temp:
        return str(Path(runner_temp) / "trusted-baseline" / "coverage_baseline.json")
    return "coverage_baseline.json"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # Positional args: feature_list.json artifacts dispatch_ledger.json [baseline].
    # The baseline path defaults to the OUT-OF-BAND, TRUSTED location the dispatcher
    # (TCB) wrote it to ($RUNNER_TEMP/trusted-baseline/coverage_baseline.json). The CI
    # workflow stages this file from a protected source (artifact/branch/secret) into a
    # path OUTSIDE GITHUB_WORKSPACE, NEVER the PR checkout, before invoking this
    # entrypoint (see coverage-gate.yml). run() additionally fails closed if the
    # supplied baseline path resolves inside GITHUB_WORKSPACE.
    fl, arts, led, baseline = (
        list(argv)
        + ["feature_list.json", "artifacts", "dispatch_ledger.json", _default_baseline_path()]
    )[:4]
    return run(
        feature_list_path=fl,
        artifacts_dir=arts,
        ledger_path=led,
        baseline_path=baseline,
    )


if __name__ == "__main__":
    sys.exit(main())

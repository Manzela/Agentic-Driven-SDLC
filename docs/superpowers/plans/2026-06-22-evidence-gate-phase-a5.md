# Zero-Trust Evidence Gate — Phase A.5: Protected-Baseline Coverage Model

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Close the two confirmed Gemini red-team findings (RT-01 coverage-model omission, RT-02 in-scope shrinking) — the gate hardens *what* it audits but Phase A still trusts the agent-controlled *scope* (the coverage model's presence + its in-scope set) that decides *whether* it audits.

**Architecture:** A trusted, dispatcher-owned **baseline** (`coverage_baseline.json`) declares which item ids are in-scope-required for a delivery. A pure deterministic `baseline_gate` compares the UNTRUSTED payload `feature_list.json` against it and FAILS CLOSED when a delivery is expected but the model is absent (RT-01) or any required item is missing / flipped out of scope (RT-02). The baseline is **trusted in A.5** (delivered to CI out-of-band, not via the hostile payload) and **cryptographically signed in Phase B** — identical chain-of-custody principle as the ledger.

**Tech Stack:** Python 3 stdlib only; pytest; GitHub Actions.

## Global Constraints

- Stdlib only; `from __future__ import annotations`; **fail CLOSED** (any error/ambiguity → deny).
- The baseline is **TRUSTED in A.5** (Phase B signs it). It MUST reach CI from a source the agent cannot tamper — **not** read from the PR payload alongside `feature_list.json`. State this in code + the workflow.
- Reuse: `tools/coverage.in_scope_items`, `tools/evidence_gate`, `tools/coverage_gate.deny_merge`, `tools/ci_evidence_check`. baseline_gate is **additive** — the existing proven+evidence+actor-separation checks still run.
- Do NOT touch `apps/web/*`. Branch of record: `worktree-agentic-sdlc-optimization` (== `main`).

---

## File Structure

**New:**
- `tools/baseline_gate.py` — pure `baseline_gate(*, baseline, feature_list) -> {"deny", "reasons"}`.
- `tools/baseline_writer.py` — the dispatcher (TCB) writes `coverage_baseline.json` from its own record of dispatched in-scope items (the trusted source).
- `tests/spine/test_baseline_gate.py`, `tests/spine/test_baseline_writer.py`.

**Modified:**
- `tools/ci_evidence_check.py` — load the trusted baseline; when a baseline is present, the absent-`feature_list` path becomes a **DENY**, not a skip.
- `.github/workflows/coverage-gate.yml` — fetch the baseline out-of-band (trusted artifact / protected path), pass it to the check; document that it must NOT come from the PR payload.
- `plane-integration/dispatcher.py` — call `baseline_writer` when dispatching a delivery.

---

### Task 1: `baseline_gate` — protected-baseline structural-integrity check

**Files:** Create `tools/baseline_gate.py`, `tests/spine/test_baseline_gate.py`.

**Interfaces:**
- Produces: `baseline_gate(*, baseline: dict | None, feature_list: dict | None) -> dict` returning `{"deny": bool, "reasons": [str, ...]}`.
- `baseline` shape (trusted): `{"required_in_scope": [<item_id>, ...]}` — the ids the dispatcher declared in-scope for this delivery.

- [ ] **Step 1: Write the failing tests (RT-01 + RT-02 red-team)**

```python
# tests/spine/test_baseline_gate.py
import importlib.util, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    s = importlib.util.spec_from_file_location("bg", ROOT / "tools/baseline_gate.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def _fl(*ids_in_scope, extra=()):
    items = [{"id": i, "in_scope": True, "status": "proven"} for i in ids_in_scope]
    items += [{"id": i, "in_scope": False} for i in extra]
    return {"items": items}

def test_no_baseline_is_pre_delivery_allow():
    bg = _load()
    assert bg.baseline_gate(baseline=None, feature_list=None)["deny"] is False
    assert bg.baseline_gate(baseline={"required_in_scope": []}, feature_list=None)["deny"] is False

def test_RT01_absent_model_when_delivery_expected_denies():
    bg = _load()
    r = bg.baseline_gate(baseline={"required_in_scope": ["A", "B"]}, feature_list=None)
    assert r["deny"] is True and any("absent" in x.lower() or "missing" in x.lower() for x in r["reasons"])

def test_RT02_item_flipped_out_of_scope_denies():
    bg = _load()
    # baseline requires A,B in scope; payload keeps A in scope but drops B to out-of-scope
    r = bg.baseline_gate(baseline={"required_in_scope": ["A", "B"]},
                         feature_list=_fl("A", extra=("B",)))
    assert r["deny"] is True and any("B" in x for x in r["reasons"])

def test_RT02_item_removed_entirely_denies():
    bg = _load()
    r = bg.baseline_gate(baseline={"required_in_scope": ["A", "B"]}, feature_list=_fl("A"))
    assert r["deny"] is True and any("B" in x for x in r["reasons"])

def test_all_required_in_scope_passes():
    bg = _load()
    r = bg.baseline_gate(baseline={"required_in_scope": ["A", "B"]}, feature_list=_fl("A", "B"))
    assert r["deny"] is False

def test_malformed_inputs_fail_closed():
    bg = _load()
    assert bg.baseline_gate(baseline={"required_in_scope": ["A"]}, feature_list="x")["deny"] is True
    assert bg.baseline_gate(baseline={"required_in_scope": "A"}, feature_list=_fl("A"))["deny"] is True
```

- [ ] **Step 2: Run to confirm failure** — `python3 -m pytest tests/spine/test_baseline_gate.py -q` → FAIL.

- [ ] **Step 3: Create `tools/baseline_gate.py`**

```python
"""baseline_gate.py — protected-baseline structural-integrity check (Phase A.5).

Closes Gemini RT-01 (coverage-model omission) and RT-02 (in-scope shrinking): the
agent controls the PR payload, so it can DELETE feature_list.json (making the gate
skip) or flip a target item to in_scope:false (excluding it from auditing). Neither
is caught by the evidence gate, which only inspects what the payload declares.

The fix: a TRUSTED baseline (dispatcher-owned, delivered out-of-band — NEVER from
the PR payload) declares which item ids are in-scope-required for this delivery.
This gate denies when the payload omits the model (a delivery was expected) or any
required item is missing / no longer in-scope. PHASE A.5: the baseline is trusted;
Phase B signs it. Pure stdlib; fails CLOSED.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.coverage import in_scope_items  # noqa: E402


def baseline_gate(*, baseline: dict | None, feature_list: dict | None) -> dict:
    reasons: list[str] = []
    try:
        # No baseline (or an empty one) => no delivery expected => the existing
        # absent-input "pre-delivery skip" is safe. Allow.
        if not isinstance(baseline, dict):
            return {"deny": False, "reasons": []}
        required = baseline.get("required_in_scope")
        if required is None:
            return {"deny": False, "reasons": []}
        if not isinstance(required, (list, tuple)):
            return {"deny": True, "reasons": [
                "Merge denied: baseline.required_in_scope is not a list. Fail closed."]}
        required_set = {str(x) for x in required}
        if not required_set:
            return {"deny": False, "reasons": []}

        # A delivery IS expected. RT-01: the payload must carry the coverage model.
        if not isinstance(feature_list, dict):
            return {"deny": True, "reasons": [
                "Merge denied: a delivery is expected (baseline declares "
                f"{len(required_set)} required in-scope item(s)) but feature_list.json "
                "is absent or malformed. Fail closed (RT-01)."]}

        # RT-02: every required id must be present AND in_scope in the payload.
        payload_in_scope = {str(i.get("id")) for i in in_scope_items(feature_list)}
        for rid in sorted(required_set):
            if rid not in payload_in_scope:
                reasons.append(
                    f"Merge denied: baseline-required item {rid!r} is missing or no "
                    f"longer in_scope in feature_list.json (RT-02: in-scope shrinking).")
        return {"deny": bool(reasons), "reasons": reasons}
    except Exception as exc:  # noqa: BLE001 — fail closed.
        return {"deny": True, "reasons": [
            f"Merge denied: baseline_gate raised {type(exc).__name__}: {exc}. Fail closed."]}
```

- [ ] **Step 4: Run tests + full suite** — `python3 -m pytest tests/spine -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add tools/baseline_gate.py tests/spine/test_baseline_gate.py
git commit -m "feat(gate): protected-baseline gate — deny coverage-model omission / in-scope shrinking (RT-01/RT-02)"
```

---

### Task 2: Enforce the baseline at CI (absent-when-expected fails closed)

**Files:** Modify `tools/ci_evidence_check.py`, `.github/workflows/coverage-gate.yml`. Test: extend `tests/spine/test_ci_evidence_check.py`.

**Interfaces:** `ci_evidence_check.run` gains `baseline_path: str | Path | None = None`. When a baseline with `required_in_scope` is present, `baseline_gate` runs FIRST; a deny → exit 1. The absent-`feature_list`/`ledger` graceful-skip is retained ONLY when no baseline expects a delivery.

- [ ] **Step 1: Write failing tests** — (a) baseline present + feature_list absent → `run()==1` (was 0); (b) baseline present + item flipped out-of-scope → `run()==1`; (c) no baseline + absent inputs → `run()==0` (pre-delivery still skips).

```python
# add to tests/spine/test_ci_evidence_check.py
def test_baseline_present_but_model_absent_denies(tmp_path):
    cec = _load()
    bl = tmp_path/"coverage_baseline.json"; bl.write_text('{"required_in_scope":["A"]}')
    rc = cec.run(feature_list_path=tmp_path/"nope.json", artifacts_dir=tmp_path,
                 ledger_path=tmp_path/"nope2.json", baseline_path=bl)
    assert rc == 1   # RT-01 closed: absent model when a delivery is expected
```

- [ ] **Step 2: Run to confirm failure** — FAIL (no `baseline_path` param).

- [ ] **Step 3: Modify `ci_evidence_check.run`** — load the baseline first; enforce before the absent-skip:

```python
# tools/ci_evidence_check.py — inside run(), BEFORE the absent-input skip:
from tools import baseline_gate as _bg  # noqa: E402  (add to imports)

def run(*, feature_list_path, artifacts_dir, ledger_path, baseline_path=None) -> int:
    fl_path, led_path, art_dir = Path(feature_list_path), Path(ledger_path), Path(artifacts_dir)
    baseline = None
    if baseline_path is not None and Path(baseline_path).is_file():
        baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    model = json.loads(fl_path.read_text(encoding="utf-8")) if fl_path.is_file() else None
    # Protected-baseline gate FIRST: an expected-but-absent or shrunk model denies.
    bg = _bg.baseline_gate(baseline=baseline, feature_list=model)
    if bg["deny"]:
        for r in bg["reasons"]:
            print(f"DENY baseline: {r}", file=sys.stderr)
        return 1
    # Absent-input skip is now safe (no baseline expected a delivery).
    if model is None:
        print(_SKIP_MSG_FL); return 0
    if not led_path.is_file():
        print(_SKIP_MSG_LED); return 0
    # ... existing re-derivation + check_model unchanged ...
```

Update `main()` to pass `baseline_path="coverage_baseline.json"`.

- [ ] **Step 4: Wire the baseline into the workflow** — `.github/workflows/coverage-gate.yml`: fetch `coverage_baseline.json` from a TRUSTED out-of-band source (a protected CI artifact uploaded by the dispatcher job, or a protected branch/secret — **NOT** the PR checkout), then pass it. Document the trust requirement inline. Mirror the deny in the rego's own conftest tests.

- [ ] **Step 5: Run tests + suite** — `python3 -m pytest tests/spine -q` → all pass.

- [ ] **Step 6: Commit**

```bash
git add tools/ci_evidence_check.py .github/workflows/coverage-gate.yml tests/spine/test_ci_evidence_check.py
git commit -m "feat(ci): enforce protected baseline — absent/shrunk coverage model denies merge (RT-01/RT-02)"
```

---

### Task 3: Dispatcher writes the trusted baseline

**Files:** Create `tools/baseline_writer.py`, `tests/spine/test_baseline_writer.py`. Modify `plane-integration/dispatcher.py`.

**Interfaces:** `baseline_writer.write_baseline(*, required_in_scope: list[str], out_path) -> dict` — the dispatcher (TCB) records the in-scope item set it dispatched, out-of-band. In A.5 it is trusted; Phase B signs it.

- [ ] **Step 1: Write failing test**

```python
# tests/spine/test_baseline_writer.py
import importlib.util, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    s = importlib.util.spec_from_file_location("bw", ROOT / "tools/baseline_writer.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def test_write_baseline_roundtrip(tmp_path):
    bw = _load(); out = tmp_path / "coverage_baseline.json"
    bw.write_baseline(required_in_scope=["A", "B"], out_path=out)
    assert json.loads(out.read_text())["required_in_scope"] == ["A", "B"]
```

- [ ] **Step 2: Run to confirm failure** — FAIL.

- [ ] **Step 3: Create `tools/baseline_writer.py`**

```python
"""baseline_writer.py — the dispatcher (TCB) records the in-scope item set it
dispatched, as the TRUSTED baseline the merge gate checks the payload against.
Phase A.5: trusted JSON. Phase B: signed. Pure stdlib.
"""
from __future__ import annotations

import json
from pathlib import Path


def write_baseline(*, required_in_scope: list[str], out_path) -> dict:
    doc = {"required_in_scope": [str(x) for x in required_in_scope]}
    Path(out_path).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc
```

- [ ] **Step 4: Wire into the dispatcher** — `plane-integration/dispatcher.py`: when a delivery is dispatched, call `baseline_writer.write_baseline(...)` with the dispatched in-scope ids, writing to the out-of-band trusted location (NOT the agent workspace). Note the integration point + that Phase B signs the output.

- [ ] **Step 5: Run tests + suite** — `python3 -m pytest tests/spine tests/plane -q` → all pass.

- [ ] **Step 6: Commit**

```bash
git add tools/baseline_writer.py tests/spine/test_baseline_writer.py plane-integration/dispatcher.py
git commit -m "feat(dispatch): dispatcher writes the trusted coverage baseline (Phase A.5)"
```

---

## Self-Review

**Spec coverage:** RT-01 (absent-model-when-expected) → baseline_gate DENY (T1) + CI enforcement (T2); RT-02 (in-scope shrinking / item removal) → baseline_gate required-set ⊄ payload-in-scope DENY (T1) + CI (T2); the trusted-source requirement → dispatcher writer + out-of-band CI delivery (T3, workflow doc). The "baseline trusted in A.5, signed in B" boundary is stated in every module + the workflow.

**Placeholder scan:** T1 + T3 contain complete code; T2 shows the exact `run()` change and the workflow-wiring contract (the precise out-of-band delivery mechanism — protected artifact vs branch vs secret — is the one A.5 ops choice, flagged explicitly, not a placeholder).

**Type consistency:** `baseline_gate(*, baseline, feature_list) -> {"deny","reasons"}` matches `ci_evidence_check.run`'s consumption (deny → exit 1); `baseline["required_in_scope"]: list[str]` is written by `baseline_writer.write_baseline` and read by `baseline_gate`; reuses `coverage.in_scope_items` for the payload in-scope set (single-sourced).

**Scope:** Phase A.5 only — structural integrity of the coverage model. No crypto (the baseline is trusted; Phase B signs it), no sandbox. Deterministic + fully testable like Phase A.

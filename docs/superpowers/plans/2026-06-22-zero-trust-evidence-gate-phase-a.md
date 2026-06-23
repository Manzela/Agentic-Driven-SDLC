# Zero-Trust Evidence Gate — Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a self-graded / forged `proven` impossible to *advance* (locally) or *merge* (CI) using only deterministic, fully-testable logic — closing the enforcement-layer gap that in-session hooks cannot (they don't fire for subagents/headless).

**Architecture:** One shared deterministic gate module (`evidence_gate`) is the single source of truth for the per-slice accept/reject decision: four-field validity + **independent `output_hash` re-derivation** + **actor-separation** (distinct verifier/implementer sessions, both in the dispatch ledger). A loop-stateful wrapper (`loop_gate`) runs it pre-advance and, on reject, emits a bounded action-directive self-heal then escalates to HANDOFF (reusing the existing `block_streak` discipline — no new C-LOOP-04). The same checks run at CI/merge via the rego twin + a Python re-derivation/ledger step registered as a required status check.

**Tech Stack:** Python 3 stdlib only; pytest; Rego/Conftest (OPA); GitHub Actions.

## Global Constraints

- **Stdlib only**, `from __future__ import annotations`, gate functions **fail CLOSED** (any error / ambiguity → reject/deny).
- **Reuse, do not re-implement:** `tools/evidence_collector.validate_evidence_record` (four-field), `tools/coverage.in_scope_items`, `tools/coverage_gate.deny_merge` (Python twin of the rego), `tools/run_state_driver.{init,tick}` (loop counters incl. `block_streak`), `tools/opa_input.build_opa_input`.
- **Evidence_Record is four fields** (`test_file, test_name, output_hash, collected_at`); `verifier_session_id` / `implementer_session_id` are **provenance fields carried alongside**, not part of the four-field validator.
- **`output_hash` format:** `"sha256:" + sha256(artifact_utf8).hexdigest()` (lowercase hex), per `evidence_collector.collect`.
- **The dispatch ledger is TRUSTED in Phase A** (cryptographic signing is Phase B). The ledger is a JSON doc `{"sessions": [<session_id>, ...]}` the dispatcher owns. Note this assumption explicitly in code comments.
- **Do NOT touch `apps/web/*`** (concurrent session). Branch of record: `worktree-agentic-sdlc-optimization` (== `main`).
- Self-heal MUST be bounded → HANDOFF; never an unbounded correction loop.

---

## File Structure

**New files:**
- `tools/evidence_gate.py` — pure per-slice gate (`check_slice`, `check_model`, `GateResult` codes, `self_heal_prompt`). The single source of truth.
- `tools/loop_gate.py` — loop-stateful wrapper (`gated_advance`) over `evidence_gate` + `run_state_driver`; emits advance / bounded self-heal / HANDOFF.
- `tools/ci_evidence_check.py` — CI step: re-derive `output_hash` from artifacts + ledger cross-check (the parts rego can't do).
- `tests/spine/test_evidence_gate.py`, `tests/spine/test_loop_gate.py`, `tests/spine/test_ci_evidence_check.py`.

**Modified files:**
- `tools/coverage_gate.py` — add actor-separation **shape** rules (present + distinct session ids on proven items), keeping it the Python twin of the rego.
- `.github/policies/coverage_query.rego` — add the same actor-separation deny rules.
- `plane-integration/the_loop.py` — `prove()` runs `loop_gate.gated_advance` and only sets `Done` on `advance`.
- `.github/workflows/coverage-gate.yml` — run `ci_evidence_check.py` alongside conftest; both required.
- `tests/spine/test_coverage_gate*.py` (if present) — extend for the new shape rules.

---

### Task 1: `evidence_gate` — the shared deterministic slice gate

**Files:**
- Create: `tools/evidence_gate.py`
- Test: `tests/spine/test_evidence_gate.py`

**Interfaces:**
- Consumes: `evidence_collector.validate_evidence_record`, `hashlib`.
- Produces:
  - `CODES`: `"OK","EVIDENCE_MISSING","EVIDENCE_MALFORMED","HASH_MISMATCH","SESSION_MISSING","SAME_SESSION","SESSION_NOT_IN_LEDGER"`.
  - `check_slice(*, evidence: dict | None, artifact: str | None, ledger: dict) -> dict` returning `{"accepted": bool, "code": str, "reason": str}`.
  - `check_model(*, model: dict, ledger: dict, artifacts: dict[str,str]) -> dict` returning `{"accepted": bool, "rejections": [ {id, code, reason}, ... ]}`.
  - `self_heal_prompt(result: dict) -> str` (action-directive per code).

- [ ] **Step 1: Write the failing tests (incl. the forgery red-team)**

```python
# tests/spine/test_evidence_gate.py
import importlib.util, hashlib, pathlib, pytest
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    spec = importlib.util.spec_from_file_location("eg", ROOT / "tools/evidence_gate.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

ART = "the-real-artifact-bytes"
HASH = "sha256:" + hashlib.sha256(ART.encode()).hexdigest()
LEDGER = {"sessions": ["sess-impl", "sess-veri"]}
def _ev(**over):
    rec = {"test_file": "t.py", "test_name": "t::case", "output_hash": HASH,
           "collected_at": "2026-06-22T00:00:00+00:00",
           "implementer_session_id": "sess-impl", "verifier_session_id": "sess-veri"}
    rec.update(over); return rec

def test_valid_slice_accepted():
    eg = _load()
    r = eg.check_slice(evidence=_ev(), artifact=ART, ledger=LEDGER)
    assert r["accepted"] is True and r["code"] == "OK"

def test_missing_evidence_rejected():
    eg = _load()
    r = eg.check_slice(evidence=None, artifact=ART, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "EVIDENCE_MISSING"

def test_malformed_four_field_rejected():
    eg = _load()
    r = eg.check_slice(evidence=_ev(output_hash="sha256:NOThex"), artifact=ART, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "EVIDENCE_MALFORMED"

def test_hash_mismatch_rejected():           # RED-TEAM: forged hash of a different artifact
    eg = _load()
    r = eg.check_slice(evidence=_ev(), artifact="a-DIFFERENT-artifact", ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "HASH_MISMATCH"

def test_same_session_self_grade_rejected():  # RED-TEAM: implementer self-verifies
    eg = _load()
    r = eg.check_slice(evidence=_ev(verifier_session_id="sess-impl"), artifact=ART, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "SAME_SESSION"

def test_session_not_in_ledger_rejected():    # RED-TEAM: spoofed session id
    eg = _load()
    r = eg.check_slice(evidence=_ev(verifier_session_id="sess-GHOST"), artifact=ART, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "SESSION_NOT_IN_LEDGER"

def test_missing_session_ids_rejected():
    eg = _load()
    ev = _ev(); del ev["verifier_session_id"]
    r = eg.check_slice(evidence=ev, artifact=ART, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "SESSION_MISSING"

def test_no_artifact_fails_closed():
    eg = _load()
    r = eg.check_slice(evidence=_ev(), artifact=None, ledger=LEDGER)
    assert r["accepted"] is False and r["code"] == "HASH_MISMATCH"

def test_self_heal_prompt_is_action_directive():
    eg = _load()
    p = eg.self_heal_prompt(eg.check_slice(evidence=_ev(verifier_session_id="sess-impl"),
                                           artifact=ART, ledger=LEDGER))
    assert "verifier" in p.lower() and "session" in p.lower()  # names the corrective action

def test_check_model_collects_rejections():
    eg = _load()
    model = {"items": [
        {"id": "A", "in_scope": True, "status": "proven", "evidence": _ev()},
        {"id": "B", "in_scope": True, "status": "proven", "evidence": _ev(verifier_session_id="sess-impl")},
        {"id": "C", "in_scope": False, "status": "unproven"}]}
    r = eg.check_model(model=model, ledger=LEDGER, artifacts={"A": ART, "B": ART})
    assert r["accepted"] is False
    assert [x["id"] for x in r["rejections"]] == ["B"]   # only the self-grade; C is out-of-scope
```

- [ ] **Step 2: Run to confirm failure** — `python3 -m pytest tests/spine/test_evidence_gate.py -q` → FAIL (no module).

- [ ] **Step 3: Create `tools/evidence_gate.py`**

```python
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
from tools.evidence_collector import validate_evidence_record  # noqa: E402

CODES = ("OK", "EVIDENCE_MISSING", "EVIDENCE_MALFORMED", "HASH_MISMATCH",
         "SESSION_MISSING", "SAME_SESSION", "SESSION_NOT_IN_LEDGER")

def _reject(code: str, reason: str) -> dict:
    return {"accepted": False, "code": code, "reason": reason}

def _rederive(artifact: str) -> str:
    return "sha256:" + hashlib.sha256(artifact.encode("utf-8")).hexdigest()

def check_slice(*, evidence: dict | None, artifact: str | None, ledger: dict) -> dict:
    """Accept/reject one proven item's evidence. Fails closed."""
    try:
        if not evidence:
            return _reject("EVIDENCE_MISSING", "no Evidence_Record present for a proven item")
        if not validate_evidence_record(evidence):
            return _reject("EVIDENCE_MALFORMED", "Evidence_Record fails four-field validation")
        # (b) independent hash re-derivation — trust bytes, not the declared hash.
        if artifact is None or _rederive(artifact) != evidence.get("output_hash"):
            return _reject("HASH_MISMATCH",
                           "output_hash does not re-derive from the captured artifact")
        # (c) actor-separation from provenance fields + the (trusted) ledger.
        vs = evidence.get("verifier_session_id")
        is_ = evidence.get("implementer_session_id")
        if not vs or not is_:
            return _reject("SESSION_MISSING",
                           "evidence lacks verifier_session_id / implementer_session_id")
        if vs == is_:
            return _reject("SAME_SESSION",
                           "verifier session equals implementer session (self-grading)")
        valid = set(ledger.get("sessions", []))
        if vs not in valid or is_ not in valid:
            return _reject("SESSION_NOT_IN_LEDGER",
                           "a declared session id is not in the dispatch ledger")
        return {"accepted": True, "code": "OK", "reason": "evidence independently verified"}
    except Exception as exc:  # noqa: BLE001 — fail closed.
        return _reject("EVIDENCE_MALFORMED", f"evidence_gate raised {type(exc).__name__}: {exc}")

def check_model(*, model: dict, ledger: dict, artifacts: dict) -> dict:
    """Run check_slice for every in-scope PROVEN item; collect rejections (by id)."""
    rejections = []
    for item in sorted([i for i in model.get("items", []) if isinstance(i, dict) and i.get("in_scope")],
                       key=lambda i: str(i.get("id", ""))):
        if item.get("status") != "proven":
            rejections.append({"id": item.get("id"), "code": "EVIDENCE_MISSING",
                               "reason": f"in-scope item is {item.get('status')!r}, not proven"})
            continue
        r = check_slice(evidence=item.get("evidence"),
                        artifact=artifacts.get(item.get("id")), ledger=ledger)
        if not r["accepted"]:
            rejections.append({"id": item.get("id"), **r})
    return {"accepted": not rejections, "rejections": rejections}

# Action-directive remediation (each names the ONE sanctioned next step — the
# self-heal prompt fed back to the agent on a local reject).
_HEAL = {
    "EVIDENCE_MISSING": "Produce a four-field Evidence_Record (test_file, test_name, output_hash, collected_at) for this item via the verifier before marking it proven.",
    "EVIDENCE_MALFORMED": "Re-emit the Evidence_Record with a valid output_hash ('sha256:'+64 lowercase hex) and a timezone-aware collected_at; do not hand-edit the hash.",
    "HASH_MISMATCH": "Re-run the verification and let the verifier rebuild output_hash from the ACTUAL captured artifact bytes; the declared hash must re-derive.",
    "SESSION_MISSING": "Have the verifier (a session distinct from the implementer) produce the evidence and stamp both session ids.",
    "SAME_SESSION": "Hand the item to the VERIFIER subagent — a session distinct from the implementer must produce the evidence; an implementer may not self-verify.",
    "SESSION_NOT_IN_LEDGER": "Use the real dispatched verifier/implementer sessions; a session id not in the dispatch ledger cannot be attested.",
}

def self_heal_prompt(result: dict) -> str:
    return _HEAL.get(result.get("code", ""),
                     "Resolve the evidence-gate rejection before re-attempting the proven transition.")
```

- [ ] **Step 4: Run the tests** — `python3 -m pytest tests/spine/test_evidence_gate.py -q` → PASS.
- [ ] **Step 5: Full suite** — `python3 -m pytest tests/spine -q` → all pass.
- [ ] **Step 6: Commit**

```bash
git add tools/evidence_gate.py tests/spine/test_evidence_gate.py
git commit -m "feat(gate): deterministic evidence gate — hash re-derivation + actor-separation (Phase A)"
```

---

### Task 2: `loop_gate` — bounded pre-advance gate + self-heal/HANDOFF

**Files:**
- Create: `tools/loop_gate.py`
- Test: `tests/spine/test_loop_gate.py`

**Interfaces:**
- Consumes: `evidence_gate.{check_slice, self_heal_prompt}`, `run_state_driver.tick` (advances `block_streak`).
- Produces: `gated_advance(*, root, evidence, artifact, ledger, max_self_heal=3) -> dict` returning `{"action": "advance"|"self_heal"|"handoff", "code", "reason", "prompt"|None, "run_state": dict}`.

- [ ] **Step 1: Write failing tests**

```python
# tests/spine/test_loop_gate.py
import importlib.util, hashlib, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
ART = "art"; HASH = "sha256:" + hashlib.sha256(ART.encode()).hexdigest()
LEDGER = {"sessions": ["i", "v"]}
def _ev(**o):
    r = {"test_file": "t", "test_name": "n", "output_hash": HASH,
         "collected_at": "2026-06-22T00:00:00+00:00",
         "implementer_session_id": "i", "verifier_session_id": "v"}; r.update(o); return r

def test_accept_advances(tmp_path):
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    r = lg.gated_advance(root=tmp_path, evidence=_ev(), artifact=ART, ledger=LEDGER)
    assert r["action"] == "advance" and r["run_state"]["block_streak"] == 0

def test_reject_self_heals_then_handoffs(tmp_path):
    lg = _load("tools/loop_gate.py", "lg")
    rsd = _load("tools/run_state_driver.py", "rsd"); rsd.init(tmp_path, "s")
    bad = _ev(verifier_session_id="i")   # self-grade
    a = lg.gated_advance(root=tmp_path, evidence=bad, artifact=ART, ledger=LEDGER, max_self_heal=2)
    assert a["action"] == "self_heal" and "verifier" in a["prompt"].lower()
    b = lg.gated_advance(root=tmp_path, evidence=bad, artifact=ART, ledger=LEDGER, max_self_heal=2)
    assert b["action"] == "handoff" and b["code"] == "SAME_SESSION"   # bounded → HANDOFF
```

- [ ] **Step 2: Run to confirm failure** — FAIL.
- [ ] **Step 3: Create `tools/loop_gate.py`**

```python
"""loop_gate.py — local PRE-ADVANCE gate: run the deterministic evidence gate
before a slice may advance; on reject, emit a BOUNDED action-directive self-heal
then escalate to HANDOFF. Reuses run_state_driver's block_streak as the self-heal
counter — so a recurring reject converts to HANDOFF rather than looping forever
(do NOT recreate C-LOOP-04).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import evidence_gate, run_state_driver  # noqa: E402

def gated_advance(*, root, evidence, artifact, ledger, max_self_heal: int = 3) -> dict:
    res = evidence_gate.check_slice(evidence=evidence, artifact=artifact, ledger=ledger)
    if res["accepted"]:
        rs = run_state_driver.tick(root, made_progress=True, violation_count=0)
        return {"action": "advance", "code": "OK", "reason": res["reason"], "prompt": None, "run_state": rs}
    rs = run_state_driver.tick(root, made_progress=False, violation_count=1)
    if rs["block_streak"] >= max_self_heal:
        return {"action": "handoff", "code": res["code"],
                "reason": f"{res['reason']} (unresolved after {rs['block_streak']} self-heal "
                          f"attempts — escalating to HANDOFF, not Done)",
                "prompt": None, "run_state": rs}
    return {"action": "self_heal", "code": res["code"], "reason": res["reason"],
            "prompt": evidence_gate.self_heal_prompt(res), "run_state": rs}
```

- [ ] **Step 4: Run tests + full suite** — `python3 -m pytest tests/spine -q` → all pass.
- [ ] **Step 5: Commit**

```bash
git add tools/loop_gate.py tests/spine/test_loop_gate.py
git commit -m "feat(gate): bounded pre-advance self-heal → HANDOFF loop gate (Phase A)"
```

---

### Task 3: Wire the pre-advance gate into `the_loop.prove()`

**Files:**
- Modify: `plane-integration/the_loop.py` (`prove`)
- Test: `tests/plane/test_the_loop_gated_prove.py` (create)

**Interfaces:**
- Consumes: `loop_gate.gated_advance`. `prove` must NOT transition to `Done` unless `action == "advance"`.

- [ ] **Step 1: Write failing test** (inject a fake plane_client + a captured-artifact resolver so no live board is needed)

```python
# tests/plane/test_the_loop_gated_prove.py
import importlib.util, hashlib, pathlib, sys, types
ROOT = pathlib.Path(__file__).resolve().parents[2]
def test_prove_blocks_self_grade(monkeypatch, tmp_path):
    # stub plane_client so the_loop imports without a live board
    pc = types.ModuleType("plane_client"); pc.PBASE = ""; pc.STATES = {}
    pc.transition = lambda *a, **k: (_ for _ in ()).throw(AssertionError("must NOT transition on reject"))
    pc.post_evidence = lambda *a, **k: None
    sys.modules["plane_client"] = pc
    spec = importlib.util.spec_from_file_location("the_loop", ROOT / "plane-integration/the_loop.py")
    tl = importlib.util.module_from_spec(spec); spec.loader.exec_module(tl)
    # a self-grade slice (verifier==implementer) must be refused, not set Done
    out = tl.gated_prove(issue_id="X", evidence={
        "test_file":"t","test_name":"n",
        "output_hash":"sha256:"+hashlib.sha256(b"a").hexdigest(),
        "collected_at":"2026-06-22T00:00:00+00:00",
        "implementer_session_id":"i","verifier_session_id":"i"},
        artifact="a", ledger={"sessions":["i"]}, root=tmp_path)
    assert out["action"] in ("self_heal", "handoff")  # never advance/Done
```

- [ ] **Step 2: Run to confirm failure** — FAIL (no `gated_prove`).
- [ ] **Step 3: Add `gated_prove` to `the_loop.py`** (keep the legacy `prove` for compatibility; route Done through the gate)

```python
# plane-integration/the_loop.py — add near prove()
import importlib.util as _ilu
def _loop_gate():
    spec = _ilu.spec_from_file_location("loop_gate", pathlib.Path(__file__).resolve().parents[1] / "tools/loop_gate.py")
    m = _ilu.module_from_spec(spec); spec.loader.exec_module(m); return m

def gated_prove(*, issue_id, evidence, artifact, ledger, root):
    """Gate a proven transition: only set Done when the evidence gate ACCEPTS.
    On reject → return the self-heal/HANDOFF decision; the board is NOT moved to Done."""
    decision = _loop_gate().gated_advance(root=root, evidence=evidence, artifact=artifact, ledger=ledger)
    if decision["action"] == "advance":
        pc.post_evidence(issue_id, evidence["test_file"], evidence["test_name"],
                         evidence["output_hash"], evidence["collected_at"], "verifier")
        pc.transition(issue_id, "Done", "verifier")
    elif decision["action"] == "handoff":
        pc.comment(issue_id, f"<p><b>HANDOFF</b> — evidence gate: {decision['reason']}</p>")
        pc.transition(issue_id, "HANDOFF", "verifier")
    # self_heal → no board change; caller feeds decision['prompt'] back to the verifier
    return decision
```

- [ ] **Step 4: Run tests + suites** — `python3 -m pytest tests/plane tests/spine -q` → all pass.
- [ ] **Step 5: Commit**

```bash
git add plane-integration/the_loop.py tests/plane/test_the_loop_gated_prove.py
git commit -m "feat(loop): the_loop.gated_prove gates Done behind the evidence gate (Phase A)"
```

---

### Task 4: Actor-separation shape rules at the merge gate (Python twin + rego)

**Files:**
- Modify: `tools/coverage_gate.py` (`deny_merge` — add actor-separation), `tests/spine/test_coverage_gate_actor_sep.py` (create)
- Modify: `.github/policies/coverage_query.rego` (add the same deny rules)

**Interfaces:** `deny_merge(feature_list) -> {"deny", "reasons"}` (unchanged shape; gains actor-separation reasons).

- [ ] **Step 1: Write failing tests**

```python
# tests/spine/test_coverage_gate_actor_sep.py
import importlib.util, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _cg():
    spec = importlib.util.spec_from_file_location("cg", ROOT / "tools/coverage_gate.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def _ev(**o):
    r = {"test_file":"t","test_name":"n","output_hash":"sha256:"+"a"*64,
         "collected_at":"2026-06-22T00:00:00+00:00",
         "implementer_session_id":"i","verifier_session_id":"v"}; r.update(o); return r
def test_same_session_denies_merge():
    cg = _cg()
    m = {"items":[{"id":"A","in_scope":True,"status":"proven","evidence":_ev(verifier_session_id="i")}]}
    res = cg.deny_merge(m)
    assert res["deny"] is True and any("session" in r.lower() for r in res["reasons"])
def test_missing_session_denies_merge():
    cg = _cg(); ev = _ev(); del ev["verifier_session_id"]
    res = cg.deny_merge({"items":[{"id":"A","in_scope":True,"status":"proven","evidence":ev}]})
    assert res["deny"] is True
def test_distinct_sessions_pass_actor_sep():
    cg = _cg()
    res = cg.deny_merge({"items":[{"id":"A","in_scope":True,"status":"proven","evidence":_ev()}]})
    assert res["deny"] is False
```

- [ ] **Step 2: Run to confirm failure** — FAIL (no actor-sep rule yet).
- [ ] **Step 3: Extend `deny_merge`** — after the four-field check, for each proven in-scope item add:

```python
            # Rule 3 — actor-separation (provenance). A proven item's evidence
            # must name DISTINCT implementer/verifier sessions (zero-trust: an
            # implementer may not self-verify). Phase A trusts the ids; Phase B
            # adds cryptographic attestation + ledger cross-check at CI.
            ev = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
            vs, is_ = ev.get("verifier_session_id"), ev.get("implementer_session_id")
            if not vs or not is_:
                reasons.append(f"Merge denied: in-scope item {item_id!r} is 'proven' but its "
                               f"evidence lacks verifier_session_id / implementer_session_id.")
            elif vs == is_:
                reasons.append(f"Merge denied: in-scope item {item_id!r} evidence has the same "
                               f"verifier and implementer session (self-grading).")
```

- [ ] **Step 4: Mirror in `coverage_query.rego`** — add two `deny` rules:

```rego
# ── Rule 4: actor-separation (provenance) ────────────────────────────────────
deny contains msg if {
	some item in in_scope_items
	item.status == "proven"
	item.evidence
	not _distinct_sessions(item.evidence)
	msg := sprintf("Merge denied: in-scope item %q evidence lacks distinct verifier/implementer sessions (self-grading or missing provenance).", [object.get(item, "id", "<no-id>")])
}
_distinct_sessions(ev) if {
	v := ev.verifier_session_id; i := ev.implementer_session_id
	v != ""; i != ""; v != i
}
```

- [ ] **Step 5: Run tests + suite** — `python3 -m pytest tests/spine -q` → all pass; if `conftest`/`opa` is available, `conftest test <fixture>.json -p .github/policies/` denies the self-grade fixture.
- [ ] **Step 6: Commit**

```bash
git add tools/coverage_gate.py .github/policies/coverage_query.rego tests/spine/test_coverage_gate_actor_sep.py
git commit -m "feat(gate): actor-separation deny rules at merge (Python twin + rego) (Phase A)"
```

---

### Task 5: CI re-derivation + ledger cross-check, registered as a required check

**Files:**
- Create: `tools/ci_evidence_check.py`
- Test: `tests/spine/test_ci_evidence_check.py`
- Modify: `.github/workflows/coverage-gate.yml`

**Interfaces:** `run(*, feature_list_path, artifacts_dir, ledger_path) -> int` (0 = pass, 1 = deny); uses `evidence_gate.check_model`. Re-derivation + ledger are the parts rego cannot do.

- [ ] **Step 1: Write failing test**

```python
# tests/spine/test_ci_evidence_check.py
import importlib.util, hashlib, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    spec = importlib.util.spec_from_file_location("cec", ROOT / "tools/ci_evidence_check.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def test_rejects_hash_mismatch_at_ci(tmp_path):
    cec = _load()
    art = tmp_path / "arts"; art.mkdir()
    (art / "A.txt").write_text("real")
    h = "sha256:" + hashlib.sha256(b"FORGED").hexdigest()   # declared hash of different bytes
    fl = tmp_path / "feature_list.json"; fl.write_text(json.dumps({"items":[
        {"id":"A","in_scope":True,"status":"proven","evidence":{
            "test_file":"A.txt","test_name":"n","output_hash":h,
            "collected_at":"2026-06-22T00:00:00+00:00",
            "implementer_session_id":"i","verifier_session_id":"v"}}]}))
    led = tmp_path / "ledger.json"; led.write_text(json.dumps({"sessions":["i","v"]}))
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 1
def test_accepts_matching_hash(tmp_path):
    cec = _load()
    art = tmp_path / "arts"; art.mkdir(); (art / "A.txt").write_text("real")
    h = "sha256:" + hashlib.sha256(b"real").hexdigest()
    fl = tmp_path / "feature_list.json"; fl.write_text(json.dumps({"items":[
        {"id":"A","in_scope":True,"status":"proven","evidence":{
            "test_file":"A.txt","test_name":"n","output_hash":h,
            "collected_at":"2026-06-22T00:00:00+00:00",
            "implementer_session_id":"i","verifier_session_id":"v"}}]}))
    led = tmp_path / "ledger.json"; led.write_text(json.dumps({"sessions":["i","v"]}))
    assert cec.run(feature_list_path=fl, artifacts_dir=art, ledger_path=led) == 0
```

- [ ] **Step 2: Run to confirm failure** — FAIL.
- [ ] **Step 3: Create `tools/ci_evidence_check.py`**

```python
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
```

- [ ] **Step 4: Run tests + suite** — `python3 -m pytest tests/spine -q` → all pass.
- [ ] **Step 5: Register in CI** — add a step to `.github/workflows/coverage-gate.yml` after the conftest/rego step:

```yaml
      - name: Evidence re-derivation + ledger cross-check (Phase A)
        run: python3 tools/ci_evidence_check.py feature_list.json artifacts dispatch_ledger.json
```

Confirm the `coverage-gate` job remains a **required** status check in the branch ruleset (re-register if needed — a new required step does not auto-register).

- [ ] **Step 6: Commit**

```bash
git add tools/ci_evidence_check.py tests/spine/test_ci_evidence_check.py .github/workflows/coverage-gate.yml
git commit -m "feat(ci): evidence re-derivation + ledger cross-check as required merge check (Phase A)"
```

---

## Self-Review

**Spec coverage (design §8 Phase A → tasks):** shared deterministic gate (re-derivation + actor-separation) → T1; local pre-advance gate + bounded self-heal → HANDOFF → T2 + T3; CI rego/actor-separation completeness + independent re-derivation → T4 + T5. The forgery/self-grade red-team (same-session, missing-evidence, hash-mismatch) is covered in T1 (`check_slice`) and re-asserted at CI in T5. The "ledger trusted in Phase A" assumption is stated in T1/T5 code comments and Global Constraints.

**Placeholder scan:** every code step contains real, runnable code; no TBDs. The `conftest` invocation in T4 is gated on the tool being available (the Python twin `deny_merge` is the always-runnable assertion).

**Type consistency:** `check_slice(*, evidence, artifact, ledger) -> {"accepted","code","reason"}` is used identically in `check_model`, `loop_gate.gated_advance`, and `ci_evidence_check`. `gated_advance(...) -> {"action","code","reason","prompt","run_state"}` matches `the_loop.gated_prove`'s consumption (`action in {advance, self_heal, handoff}`). `run_state_driver.tick` keys (`block_streak`) match `gated_advance`'s escalation read. `EVIDENCE_FIELDS` reused from `coverage_gate`; four-field validity reused from `evidence_collector.validate_evidence_record`.

**Scope:** Phase A only — no signing, no sandbox; the ledger is an unsigned trusted JSON doc. Phases B–D (crypto chain-of-custody, isolation, TCB hardening) are separate plans per the design doc.

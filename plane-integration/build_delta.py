#!/usr/bin/env python3
"""Build the deepening-pass delta-plan.json from verified state.

Groups:
  G1 restore 6 over-written E7/E6-S5 descriptions (content-loss fix; rebuild from plane_backlog + true-up note)
  G2 create NEW-12 (missing migration-authoring owner; collision with REQ-INFRA-005 fixed by clean external_id)
  G3 relations (board has ZERO): NEW-14 blocked-by edges + R1/R5/R6 scope-contract/cross-link edges + prereq edges
  G4 Class-B hook-design refinements (append_md, sentinel-guarded) — the generalization/loop-prevention ACs
  G5 dedup reconciliation notes (NEW-11 vs E7-REQ11.3)
Resolves every logical token to a LIVE external_id from the current snapshot; emits only resolvable ops.
"""
import json, pathlib, re, html as _html

ROOT = pathlib.Path(__file__).resolve().parent.parent
SNAP = json.load(open(ROOT / "audit/plane-xref/board-snapshot.json"))
PLAN = json.load(open(ROOT / "docs/audits/spec-to-evidence-steering/plane-upsert-plan.json"))
BL = json.load(open(ROOT / "docs/plane/plane_backlog.json"))
OPS_BY_ID = {o.get("id"): o for o in PLAN["operations"]}
BL_STORY = {s["key"]: s for s in BL.get("stories", [])}

items = SNAP["work_items"]
ext_set = {w["external_id"] for w in items if w["external_id"]}


def esc(s):
    return _html.escape(str(s or ""), quote=False)


def resolve_story(token):
    """logical token (E8-13, E7-REQ6, E6-S2, E2-S1) -> live story: external_id."""
    cands = [f"story:{token}", f"story:ASCP-{token}", f"story:{token.replace('ASCP-','')}"]
    for c in cands:
        if c in ext_set:
            return c
    # endswith match
    for e in ext_set:
        if e and e.startswith("story:") and e.split(":", 1)[1].replace("ASCP-", "") == token.replace("ASCP-", ""):
            return e
    return None


# ---------- G1: restore 6 descriptions ----------
def story_html(s, trueup=True):
    h = []
    if trueup:
        h.append("<p><b>Status true-up (C16 / §4.4 S6/S7/S8):</b> moved to <b>Backlog</b> — the prior advanced "
                 "state outran on-disk evidence (underlying tools / migrations / telemetry are absent per the audit). "
                 "Re-advance only when the named prerequisites land. The original requirement content is preserved below "
                 "(it had been overwritten by a batch true-up note).</p>")
    h.append(f"<p><b>{esc(s.get('title'))}</b> — requirement <code>{esc(s.get('requirement_id'))}</code></p>")
    if s.get("ears"):
        h.append("<p><b>EARS requirements</b></p><ul>")
        for e in s["ears"]:
            h.append(f"<li><b>[{esc(e.get('pattern'))}]</b> {esc(e.get('text'))}</li>")
        h.append("</ul>")
    if s.get("acceptance_criteria"):
        h.append("<p><b>Acceptance criteria</b></p><ul>")
        for a in s["acceptance_criteria"]:
            h.append(f"<li>{esc(a)}</li>")
        h.append("</ul>")
    meta = {"epic": s.get("epic_id"), "requirement_id": s.get("requirement_id"),
            "agent_role": s.get("agent_role"), "coverage_type": s.get("coverage_type"), "key": s.get("key")}
    h.append("<p><b>Control metadata</b></p><ul>")
    for k, v in meta.items():
        if v:
            h.append(f"<li><code>{esc(k)}</code>: {esc(v)}</li>")
    h.append("</ul>")
    return "".join(h)


ops = []
G1_KEYS = ["ASCP-E7-REQ6", "ASCP-E7-REQ11", "ASCP-E7-REQ12", "ASCP-E7-REQ23", "ASCP-E7-REQ27", "E6-S5"]
for key in G1_KEYS:
    s = BL_STORY.get(key)
    ext = resolve_story(key)
    if not s or not ext:
        print(f"G1 SKIP unresolved: {key} (ext={ext})")
        continue
    ops.append({"kind": "update", "target_external_id": ext, "set_state": "Backlog",
                "description_html": story_html(s), "why": f"G1-restore-{key}"})

# ---------- G2: create NEW-12 ----------
n12 = OPS_BY_ID.get("NEW-12")
if n12 and "ascp-audit-reorg:NEW-12" not in ext_set:
    acs = n12.get("acceptance_criteria", [])
    dh = (n12.get("description_html") or "")
    dh += "<p><b>Acceptance criteria</b></p><ul>" + "".join(f"<li>{esc(a)}</li>" for a in acs) + "</ul>"
    dh += ("<p><b>Provenance:</b> created standalone in the deepening pass — the prior apply collided this op onto "
           "<code>story:REQ-INFRA-005</code> (shared match_key), so REQ-INFRA-005's true-up overwrote it and the "
           "migration-authoring owner never existed. REQ-INFRA-005 AC#4 depends on this item.</p>")
    ops.append({"kind": "create", "name": n12["target_name"], "external_id": "ascp-audit-reorg:NEW-12",
                "epic_module": "E1", "phase_cycle": "Phase 0 — Spine", "set_state": "Spec-Verified",
                "set_labels": ["phase:0", "type:wiring", "gate:security", "priority:blocking"],
                "description_html": dh, "why": "G2-create-NEW-12 (COV-01/XC-03/GT-D1)"})

# ---------- G3: relations ----------
def rel(frm, to, rt="blocked_by", why=""):
    f = resolve_story(frm) if not frm.startswith("ascp-audit-reorg:") else frm
    t = resolve_story(to) if not to.startswith("ascp-audit-reorg:") else to
    if not f or not t:
        print(f"G3 SKIP unresolved relation: {frm}({f}) -{rt}-> {to}({t})")
        return
    ops.append({"kind": "relation", "relation_type": rt, "from_external_id": f, "to_external_id": t, "why": why})

# NEW-14: every hook-consuming story blocked_by E8-13 (settings.json registration)
HOOK_CONSUMERS = ["E2-S1", "E2-S2", "E2-S3", "E3-1", "E3-2", "E3-4", "E3-22",
                  "E4-S1", "E4-S2", "E4-S3", "E4-S4", "E5-S10", "E6-S2", "E6-S3", "E6-S7",
                  "E7-REQ6", "E7-REQ11", "E7-REQ12", "E7-REQ16", "E7-REQ23", "E7-REQ27",
                  "E8-14", "E8-18", "E8-21", "E8-26"]
for c in HOOK_CONSUMERS:
    if resolve_story(c) == resolve_story("E8-13"):
        continue
    rel(c, "E8-13", "blocked_by", "NEW-14 spine-first topology (COV-02/PSD-01/GT-D2)")

# R1: the two stories that extend the unified A6 hook are blocked_by its owner NEW-10
rel("E4-S2", "ascp-audit-reorg:NEW-10", "blocked_by", "R1 extend-not-re-register the unified A6 hook")
rel("E4-S3", "ascp-audit-reorg:NEW-10", "blocked_by", "R1 extend-not-re-register the unified A6 hook")
# R5: overlapping evaluate_stop ownership scope contract (relates_to, not block)
rel("E8-14", "E8-21", "relates_to", "R5 evaluate_stop scope contract (E8-14=reentrancy guard, E8-21=escalation rungs)")
# R6: the 5 anti-idle layers cite the canonical HANDOFF contract (NEW-03)
for layer in ["E8-14", "E8-21", "E3-4", "E5-S10", "E6-S3"]:
    rel(layer, "ascp-audit-reorg:NEW-03", "relates_to", "R6 canonical HANDOFF contract single-source")
# Prereq edges: D3 populator (NEW-02) unblocks the HANDOFF/counter consumers
for c in ["E5-S10", "E3-4", "E8-21"]:
    rel(c, "ascp-audit-reorg:NEW-02", "blocked_by", "D3 run_state populator makes counters live (TWL-03/08)")
# COH-1: verifier.md literal consumers blocked_by NEW-05
for c in ["E2-S2", "E6-S4"]:
    rel(c, "ascp-audit-reorg:NEW-05", "blocked_by", "COH-1 actor-name reconciliation prerequisite")
# D7 PreCompact: NEW-01 (A5 resume-integrity) blocked_by NEW-11; NEW-11 relates_to E7-REQ11 (dup leg)
rel("ascp-audit-reorg:NEW-01", "ascp-audit-reorg:NEW-11", "blocked_by", "A5 resume-integrity needs D7 producer (PSD-04)")
rel("ascp-audit-reorg:NEW-11", "E7-REQ11", "relates_to", "NEW-11 vs E7-REQ11.3 PreCompact scope (COV-06/RED-06)")

# ---------- G4: Class-B hook-design refinements (append_md) ----------
G4 = {
 "E8-13": """**Deepening AC (xref pass — registration correctness & generalization).**
- The A1 register installs **exactly 5 events** — SessionStart, PreToolUse, PostToolUse, SubagentStop, Stop. **PreCompact is a separate hook (NEW-11), NOT part of this register** — `SPINE_REQUIRED_EVENTS` must scope to these 5 so the SessionStart canary is green when wired *as scoped* (COH-2), not perpetually yellow.
- The **PreToolUse matcher must include `Bash`** (not only `Write|Edit|MultiEdit`): protected-path anti-tamper is bypassable via `sed`/`tee`/`echo >`/`python -c` writes under Bash. Pair the tool matcher with a **content-level** protected-path check (resolve the target path from the command), not a tool-name allowlist alone.
- **Exit-code-2 steering reason MUST be written to STDERR**, never stdout. On a PreToolUse/Stop block, Claude Code feeds **stderr** back to the model; stdout is shown only to the user. A hook that prints its reason to stdout + exits 2 makes the steer invisible to the agent → the agent flails/loops. (Best-practice BP-3.)
- `settings.json` must live on the **run branch in the run cwd** — a hook registered off-branch never fires (the original silent-inertness root).
- Add a runtime **ralph-loop disable telemetry assert**: post-apply, `stop-hook.sh` is ABSENT from hook telemetry and the governance Stop hook owns the event (TWL-06).""",

 "E5-S10": """**Deepening AC (xref pass — anti-loop, testable).**
- Encode the **CH-10 escalate-don't-re-inject rung** as a runnable oracle: on Stop re-entry the hook emits **ZERO tokens** (no mega-prompt re-injection); after N consecutive no-progress streaks it routes to **HANDOFF**, never re-injects. A test must prove a 3-streak triggers HANDOFF, not the 49× re-injection the forensics found (C-LOOP-04).
- The **reentrancy guard keys on the hook-input payload `stop_hook_active` flag** that Claude Code supplies, **not** a self-authored `run_state.stop_hook_active` mutex (which is unwritten until D3/NEW-02 and races the very loop it guards). (TWL-01/02/04, BP-2.)
- The N=3 no-progress counters are inert until the D3 populator (NEW-02) writes them — this story is `blocked_by` NEW-02 (edge added).""",

 "E8-21": """**Deepening AC (xref pass — escalation ownership scope contract).**
- **Scope contract with E8-14 on `evaluate_stop`:** E8-14 owns the `stop_hook_active` reentrancy short-circuit; **E8-21 owns the escalation/HANDOFF rungs that consume `run_state`** (cap / budget / no-progress → HANDOFF). They edit one function — neither re-implements the other's leg. (R5.)
- Escalation rungs are live only after NEW-02 (D3) writes the counters → `blocked_by` NEW-02 (edge added). Cite the single canonical HANDOFF contract in NEW-03 rather than restating the rungs (R6).""",

 "E8-14": """**Deepening AC (xref pass — reentrancy scope contract).**
- E8-14 owns ONLY the `stop_hook_active` reentrancy short-circuit in `evaluate_stop` (read the flag from the hook input payload; if set, return immediately, emit nothing). The escalation/HANDOFF rungs belong to E8-21 (R5 scope contract; `relates_to` edge added).""",

 "E4-S1": """**Deepening AC (xref pass — SubagentStop correctness & anti-spoof).**
- The SubagentStop gate **must resolve the actor from `CLAUDE_AGENT_NAME` (server/runtime side), NOT from a payload-supplied `actor_agent`** — a payload field is spoofable by the very subagent being gated, defeating actor-independence (B-INTENT-02). (HGD-4.)
- The hook's JSON **`decision` value must be a valid SubagentStop value (`"block"` or omitted)** — `"approve"` is not a recognized SubagentStop decision and is silently ignored, so a self-graded record passes. (BP-4.)
- Block reasons go to **stderr** with exit 2 and name the **located evidence field** + one corrective step (not a generic 'failed').""",

 "ascp-audit-reorg:NEW-05": """**Deepening AC (xref pass — COH-1 generalization).**
- Resolve the verifier identity through a **single constant/env (`VERIFIER_ROLE`, default `verifier.md`)** imported by every gate (`pre_tool_use_hook.py`, `subagent_stop_hook.py`, fixtures), so a future role rename is a one-line change — not a brittle byte-for-byte literal duplicated across files that re-creates the G1 fail-closed-but-stuck failure when it drifts. The CI assert checks `CLAUDE_AGENT_NAME` resolves to that constant. (HGD-3.)""",
}
for tok, md in G4.items():
    ext = tok if tok.startswith("ascp-audit-reorg:") else resolve_story(tok)
    if not ext:
        print(f"G4 SKIP unresolved target: {tok}")
        continue
    ops.append({"kind": "update", "target_external_id": ext, "append_md": md,
                "why": f"G4-{tok}"})

# ---------- G5: dedup note on NEW-11 ----------
ops.append({"kind": "update", "target_external_id": "ascp-audit-reorg:NEW-11",
            "append_md": "**Scope note (xref):** NEW-11 owns the standalone **PreCompact hook** that writes "
                         "`resume_state_hash`. Existing task **E7-REQ11.3** is the durable-state *column writer* — a "
                         "distinct leg. `relates_to` edge added; neither re-implements the other. (RED-06/COV-06.)",
            "why": "G5-NEW-11-dedup"})

out = {"_meta": {"generated_for": "plane-xref deepening pass (post-agent-reapply state)",
                 "groups": {"G1_restore": len(G1_KEYS), "G2_create": 1, "G4_refine": len(G4)},
                 "counts": {}},
       "ops": ops}
from collections import Counter
c = Counter(o["kind"] for o in ops)
out["_meta"]["counts"] = dict(c)
(ROOT / "audit/plane-xref/delta-plan.json").write_text(json.dumps(out, indent=1))
print(f"\nwrote delta-plan.json: {len(ops)} ops -> {dict(c)}")

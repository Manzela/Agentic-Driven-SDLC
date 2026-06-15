"""
formal_verification_merged.py
Spec-to-Evidence Coverage Control System — Unified Z3 SMT Harness
Z3 v4.16.0  |  exit 0 = all checks pass, exit 1 = one or more failures

Supersedes formal_verification.py (deprecated; do not run — see banner in that file).

This harness encodes and machine-checks the critical invariants of the
Spec-to-Evidence Coverage Control System (canonical merged PRD, June 15 2026).

Check groups (counts are the ACTUAL number of check() calls, self-counted at runtime;
never hardcode — the reported total is computed from checks_run so it can never drift):
  Core    14  (CHECK-1..5c)    — core consistency / completion / prediction-independence,
                                  incl. the HANDOFF-exit-0 checks CHECK-5b/5c (REQ-LOOP-005)
  Kiro    12  (CHECK-6a..9c)   — scope-sequencing, evidence schema, no-progress (incl. HANDOFF
                                  exit-0 CHECK-8c), UNMAPPED
  New      8  (CHECK-10a..13b) — amendment monotonicity, resumed-state integrity,
                                  checklist-approval-before-use, omission-declaration gate

HANDOFF path (CHECK-5b/5c/8c) — REQ-LOOP-005: cap/no-progress ALLOWS termination (exit 0),
                                never blocks (exit 2). Fixes latent infinite-block defect.

Total: 34 machine-checked assertions (14 + 12 + 8). The earlier "29/29" figure undercounted
the three HANDOFF-exit-0 checks (CHECK-5b/5c/8c) that were added to fix the Stop-hook defect.

Run: python3 formal_verification_merged.py
"""

from z3 import (
    Bool, Int, And, Or, Not, Implies, Solver, sat, unsat, BoolVal
)
import sys

failures = []
checks_run = 0  # incremented per check() call so the reported total = real assertions run

def check(label, solver_or_expr, expected, description):
    """
    Run a satisfiability check and compare against expected result.
    expected: 'sat' or 'unsat'
    """
    global checks_run
    checks_run += 1
    s = Solver()
    if isinstance(solver_or_expr, list):
        for c in solver_or_expr:
            s.add(c)
    else:
        s.add(solver_or_expr)

    result = s.check()
    verdict = "sat" if result == sat else "unsat"
    passed_check = (verdict == expected)
    status = "✓" if passed_check else "✗ FAIL"
    print(f"  {status}  {label:12s}  expected={expected:5s}  got={verdict:5s}  | {description}")
    if not passed_check:
        failures.append((label, expected, verdict, description))
    return passed_check


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: Core model variables
# ─────────────────────────────────────────────────────────────────────────────

# Run-state
maint          = Bool("maint")           # system is in maintenance mode
writeAllowed   = Bool("writeAllowed")    # writes are permitted
planApproved   = Bool("planApproved")    # human approved the plan
codeWrite      = Bool("codeWrite")       # an implementation write is occurring
adminSave      = Bool("adminSave")       # an admin-initiated save

# Coverage / completion state
unproven       = Bool("unproven")        # any in-scope item is unproven
complete       = Bool("complete")        # run has reached COMPLETE terminal state
handoff        = Bool("handoff")         # run has reached HANDOFF terminal state
running        = Bool("running")         # run is in progress

# Loop controls
capReached     = Bool("capReached")      # iteration cap hit
budgetExceeded = Bool("budgetExceeded")  # cost/token budget exceeded
noProgress     = Bool("noProgress")      # no measurable progress across N iterations

# Stop hook exit path (REQ-LOOP-005: HANDOFF = allow exit, not block)
# hookExitsBlocking: True means the Stop hook returned exit-2 (blocking).
# Correct invariant: cap/budget/noProgress MUST produce hookExitsBlocking=False (exit-0).
hookExitsBlocking = Bool("hookExitsBlocking")  # True = exit-2, False = exit-0

# Evidence / verification
evidence       = Bool("evidence")        # evidence artifact is attached
testsPass      = Bool("testsPass")       # tests pass
passed         = Bool("passed")          # item is marked proven
gateBlock      = Bool("gateBlock")       # Stop hook is blocking (unproven-items case only)

# Prediction independence
predA          = Bool("predA")           # prediction variant A
predB          = Bool("predB")           # prediction variant B
gateA          = Bool("gateA")           # gate decision under prediction A
gateB          = Bool("gateB")           # gate decision under prediction B

# Scope-sequencing (CHECK-6 family)
priorItemUnproven   = Bool("priorItemUnproven")  # a prior slice item is unproven
newSliceStarting    = Bool("newSliceStarting")   # a new slice is being initiated
scopeGateBlocks     = Bool("scopeGateBlocks")    # scope-sequencing gate fires

# Evidence schema (CHECK-7 family)
evidenceHasTestFile  = Bool("evidenceHasTestFile")
evidenceHasTestName  = Bool("evidenceHasTestName")
evidenceHasHash      = Bool("evidenceHasHash")
evidenceHasTimestamp = Bool("evidenceHasTimestamp")
evidenceComplete     = Bool("evidenceComplete")

# No-progress operationalization (CHECK-8 family)
noItemsProvenLastN   = Bool("noItemsProvenLastN")
noCommitsLastN       = Bool("noCommitsLastN")
noProgressMeasurable = Bool("noProgressMeasurable")

# UNMAPPED / proactive discovery (CHECK-9 family)
unmappedExists       = Bool("unmappedExists")
advancementAllowed   = Bool("advancementAllowed")

# Amendment versioning (CHECK-10 family) — REQ-COV-007
requirementAmended   = Bool("requirementAmended")   # a requirement was amended post-approval
amendedItemReproven  = Bool("amendedItemReproven")  # the amended item has been re-proven

# Resumed-state integrity (CHECK-11 family) — REQ-STATE-005
resumeHashMismatch   = Bool("resumeHashMismatch")   # durable-store hash != resumed-state hash
runProceeds          = Bool("runProceeds")           # the resumed run is allowed to proceed

# Checklist approval (CHECK-12 family) — REQ-SPEC-016
checklistIsDraft     = Bool("checklistIsDraft")      # checklist has approved_at = NULL (DRAFT)
checklistUsedForDisc = Bool("checklistUsedForDisc")  # checklist was used for discovery


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Core axioms
# ─────────────────────────────────────────────────────────────────────────────
core_axioms = [
    # REQ-GATE-001: completion gate is a pure function of facts (unproven state)
    gateBlock == unproven,
    # REQ-GATE-002: COMPLETE implies gate not blocking (nothing unproven)
    Implies(complete, Not(gateBlock)),
    # REQ-HITL-001 / REQ-EXEC-004: no code-write without approved plan
    Implies(codeWrite, planApproved),
    # REQ-SEC-004 / REQ-COV: no writes in maintenance mode
    Implies(maint, Not(writeAllowed)),
    # REQ-COV-001/003: PASSED requires evidence AND passing tests
    Implies(passed, And(evidence, testsPass)),
    # REQ-LOOP-002 / REQ-LOOP-005 (corrected):
    # cap/budget/noProgress → HANDOFF (not COMPLETE), AND Stop hook ALLOWS termination (exit-0).
    # hookExitsBlocking = True would mean exit-2, which forces continuation — wrong for HANDOFF.
    Implies(
        Or(capReached, budgetExceeded, noProgress),
        And(handoff, Not(complete), Not(hookExitsBlocking))
    ),
    # Terminal exclusivity: COMPLETE or HANDOFF → not running
    Implies(Or(complete, handoff), Not(running)),
    # Cannot be both COMPLETE and HANDOFF
    Not(And(complete, handoff)),
    # Unproven-items Stop-hook path DOES block (exit-2) — this is the only legitimate blocking case
    Implies(And(gateBlock, unproven, Not(capReached), Not(budgetExceeded), Not(noProgress)),
            hookExitsBlocking),
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Original 12 checks
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Original 12 checks (core consistency / completion / prediction-independence) ──\n")

# CHECK-1: Core axioms admit a clean successful-completion state
check("CHECK-1", core_axioms + [
    Not(unproven),
    complete,
    Not(handoff),
    Not(running),
    planApproved,
    evidence,
    testsPass,
    passed,
    Not(capReached), Not(budgetExceeded), Not(noProgress),
    Not(maint),
    Not(hookExitsBlocking),
], "sat", "CHECK-1: Clean successful-completion state is reachable [REQ-GATE-001..002]")

# CHECK-2a: Classic conflict — maint ∧ adminSave naive write rule
check("CHECK-2a", core_axioms + [
    maint,
    adminSave,
    writeAllowed,
], "unsat", "CHECK-2a: maint ∧ naive-adminSave-write is UNSAT — conflict confirmed")

# CHECK-2b: Correction — adminSave write only when NOT in maintenance
check("CHECK-2b", core_axioms + [
    Not(maint),
    adminSave,
    writeAllowed,
], "sat", "CHECK-2b: (adminSave ∧ ¬maint) ⇒ write is SAT — correction holds")

# CHECK-3a: System-specific conflict — capReached ∧ unproven ∧ naive COMPLETE
check("CHECK-3a", core_axioms + [
    capReached,
    unproven,
    complete,
], "unsat", "CHECK-3a: capReached ∧ unproven ∧ complete is UNSAT — conflict confirmed")

# CHECK-3b: Correction — capReached ⇒ HANDOFF (REQ-LOOP-002)
check("CHECK-3b", core_axioms + [
    capReached,
    handoff,
    Not(complete),
    Not(hookExitsBlocking),  # HANDOFF path: exit-0, not exit-2
], "sat", "CHECK-3b: capReached ⇒ (handoff ∧ ¬complete ∧ exit-0) is SAT — REQ-LOOP-005 holds")

# CHECK-4a: Maintenance-reject guard is reachable (not dead)
check("CHECK-4a", core_axioms + [
    maint,
    Not(writeAllowed),
], "sat", "CHECK-4a: Maintenance write-reject is reachable — not a dead rule")

# CHECK-4b: Writes remain possible outside maintenance (rule not vacuous)
check("CHECK-4b", core_axioms + [
    Not(maint),
    writeAllowed,
], "sat", "CHECK-4b: Writes possible outside maintenance — rule not vacuous")

# CHECK-4c: Stop-gate can fire (unproven items case — exits blocking)
check("CHECK-4c", core_axioms + [
    unproven,
    gateBlock,
    Not(complete),
    Not(capReached), Not(budgetExceeded), Not(noProgress),
    hookExitsBlocking,
], "sat", "CHECK-4c: Stop-gate fires (exit-2) when unproven items exist — reachable [REQ-GATE-002]")

# CHECK-4d: Stop-gate can clear
check("CHECK-4d", core_axioms + [
    Not(unproven),
    Not(gateBlock),
    Not(hookExitsBlocking),
], "sat", "CHECK-4d: Stop-gate clears when all items proven — reachable")

# CHECK-4e: PASSED reachable with evidence+tests
check("CHECK-4e", core_axioms + [
    passed,
    evidence,
    testsPass,
], "sat", "CHECK-4e: PASSED state reachable with evidence+tests — not vacuous")

# CHECK-4f: Code-write without approved plan is impossible
check("CHECK-4f", core_axioms + [
    codeWrite,
    Not(planApproved),
], "unsat", "CHECK-4f: codeWrite ∧ ¬planApproved is UNSAT — PreToolUse gate holds [REQ-HITL-001]")

# CHECK-5: Prediction independence — differing prediction cannot produce differing gate decision
check("CHECK-5", [
    gateA == unproven,
    gateB == unproven,
    predA != predB,
    gateA != gateB,
], "unsat", "CHECK-5: Differing prediction cannot produce differing gate [REQ-STEER-006, REQ-PRED-002]")

# CHECK-5b: HANDOFF path exit-0 enforcement (REQ-LOOP-005 — new)
# If cap/budget/noProgress fires, hookExitsBlocking MUST be False (exit-0, allow stop).
# Assert the opposite (exits blocking on cap) → UNSAT confirms the invariant.
check("CHECK-5b", core_axioms + [
    capReached,
    hookExitsBlocking,  # assert it wrongly blocks — UNSAT expected
], "unsat", "CHECK-5b: capReached ∧ hookExitsBlocking is UNSAT — REQ-LOOP-005: HANDOFF MUST exit-0 not exit-2")

# CHECK-5c: noProgress path also requires exit-0 (not exit-2)
check("CHECK-5c", core_axioms + [
    noProgress,
    hookExitsBlocking,  # assert it wrongly blocks — UNSAT expected
], "unsat", "CHECK-5c: noProgress ∧ hookExitsBlocking is UNSAT — no-progress HANDOFF MUST exit-0 [REQ-LOOP-005]")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: Kiro 11 checks (scope-sequencing, evidence schema, no-progress, UNMAPPED)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Kiro 11 checks (scope-sequencing / evidence schema / no-progress / UNMAPPED) ──\n")

scope_sequencing_axioms = [
    Implies(priorItemUnproven, scopeGateBlocks),
    Implies(scopeGateBlocks, Not(newSliceStarting)),
]

# CHECK-6a: New slice cannot start while prior item is unproven
check("CHECK-6a", scope_sequencing_axioms + [
    priorItemUnproven,
    newSliceStarting,
], "unsat", "CHECK-6a: New slice start blocked while prior item unproven [REQ-EXEC-005]")

# CHECK-6b: New slice CAN start when prior item is proven
check("CHECK-6b", scope_sequencing_axioms + [
    Not(priorItemUnproven),
    Not(scopeGateBlocks),
    newSliceStarting,
], "sat", "CHECK-6b: New slice allowed when all prior items proven — rule not vacuous")

evidence_schema_axioms = [
    evidenceComplete == And(
        evidenceHasTestFile,
        evidenceHasTestName,
        evidenceHasHash,
        evidenceHasTimestamp,
    ),
    Implies(passed, evidenceComplete),
]

# CHECK-7a: Cannot be PASSED with incomplete evidence (missing hash)
check("CHECK-7a", evidence_schema_axioms + [
    passed,
    evidenceHasTestFile,
    evidenceHasTestName,
    Not(evidenceHasHash),
    evidenceHasTimestamp,
], "unsat", "CHECK-7a: PASSED without output_hash is UNSAT — evidence schema enforced [REQ-COV-006]")

# CHECK-7b: PASSED IS reachable with all four fields present
check("CHECK-7b", evidence_schema_axioms + [
    passed,
    evidenceHasTestFile,
    evidenceHasTestName,
    evidenceHasHash,
    evidenceHasTimestamp,
    evidenceComplete,
    testsPass,
], "sat", "CHECK-7b: PASSED reachable with complete 4-field evidence — not vacuous")

# CHECK-7c: Cannot flip to passed with zero evidence fields
check("CHECK-7c", evidence_schema_axioms + [
    passed,
    Not(evidenceHasTestFile),
    Not(evidenceHasTestName),
    Not(evidenceHasHash),
    Not(evidenceHasTimestamp),
], "unsat", "CHECK-7c: PASSED with zero evidence fields is UNSAT — fail-closed on empty evidence")

no_progress_axioms = [
    noProgressMeasurable == And(noItemsProvenLastN, noCommitsLastN),
    noProgress == noProgressMeasurable,
]

# CHECK-8a: No-progress when neither items proven nor commits produced → HANDOFF reachable
check("CHECK-8a", core_axioms + no_progress_axioms + [
    noItemsProvenLastN,
    noCommitsLastN,
    noProgressMeasurable,
    noProgress,
], "sat", "CHECK-8a: No-progress condition is reachable when both signals fire [REQ-LOOP-002]")

# CHECK-8b: No-progress + unproven → HANDOFF, never COMPLETE
check("CHECK-8b", core_axioms + no_progress_axioms + [
    noItemsProvenLastN,
    noCommitsLastN,
    noProgressMeasurable,
    noProgress,
    unproven,
    complete,
], "unsat", "CHECK-8b: No-progress ∧ unproven ∧ complete is UNSAT — HANDOFF only [REQ-LOOP-002]")

# CHECK-8c: No-progress HANDOFF path exits 0 (allow), not exit-2 (block) — REQ-LOOP-005
check("CHECK-8c", core_axioms + no_progress_axioms + [
    noItemsProvenLastN,
    noCommitsLastN,
    noProgressMeasurable,
    noProgress,
    hookExitsBlocking,  # assert wrong exit — UNSAT expected
], "unsat", "CHECK-8c: noProgress HANDOFF path hookExitsBlocking is UNSAT — MUST exit-0 [REQ-LOOP-005]")

# CHECK-8d: Active progress suppresses no-progress (rule not vacuous)
check("CHECK-8d", core_axioms + no_progress_axioms + [
    Not(noItemsProvenLastN),
    Not(noCommitsLastN),
    Not(noProgressMeasurable),
    Not(noProgress),
    running,
    Not(complete), Not(handoff),
], "sat", "CHECK-8d: Active progress suppresses no-progress condition — rule not vacuous")

unmapped_axioms = [
    Implies(unmappedExists, Not(advancementAllowed)),
]

# CHECK-9a: Advancement blocked when any baseline item is UNMAPPED
check("CHECK-9a", unmapped_axioms + [
    unmappedExists,
    advancementAllowed,
], "unsat", "CHECK-9a: Advancement while UNMAPPED items exist is UNSAT [REQ-SPEC-011]")

# CHECK-9b: Advancement IS allowed when all items are mapped
check("CHECK-9b", unmapped_axioms + [
    Not(unmappedExists),
    advancementAllowed,
], "sat", "CHECK-9b: Advancement allowed when all baseline items are mapped — not vacuous")

# CHECK-9c: UNMAPPED gate and completion gate are independent
check("CHECK-9c", unmapped_axioms + core_axioms + [
    Not(unmappedExists),
    Not(unproven),
    complete,
    Not(handoff),
    planApproved,
    Not(hookExitsBlocking),
], "sat", "CHECK-9c: Fully-mapped, fully-proven run can reach COMPLETE — gates are independent")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: New 6 checks — gap-closure invariants (canonical merge)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── New 6 checks (amendment monotonicity / resumed-state / checklist approval) ──\n")

# ── Amendment monotonicity (CHECK-10 family) — REQ-COV-007 ──────────────────
# If a requirement is amended (requirementAmended = True) and its coverage item
# has NOT been re-proven (amendedItemReproven = False), then COMPLETE is impossible.
amendment_axioms = [
    # Amended-but-not-reproven item is still functionally unproven
    Implies(And(requirementAmended, Not(amendedItemReproven)), unproven),
]

# CHECK-10a: Amended-not-reproven requirement → cannot be COMPLETE
check("CHECK-10a", core_axioms + amendment_axioms + [
    requirementAmended,
    Not(amendedItemReproven),
    complete,
], "unsat", "CHECK-10a: amended ∧ ¬reproven ∧ complete is UNSAT — amendment monotonicity [REQ-COV-007]")

# CHECK-10b: After re-proving the amended requirement, COMPLETE IS reachable
check("CHECK-10b", core_axioms + amendment_axioms + [
    requirementAmended,
    amendedItemReproven,
    Not(unproven),
    complete,
    Not(handoff),
    planApproved,
    evidence,
    testsPass,
    passed,
    Not(capReached), Not(budgetExceeded), Not(noProgress),
    Not(hookExitsBlocking),
], "sat", "CHECK-10b: amended ∧ reproven ∧ complete is SAT — re-proving enables completion")

# ── Resumed-state integrity (CHECK-11 family) — REQ-STATE-005 ───────────────
# If a session resumes and the resumed-state hash does not match the durable store,
# the run MUST NOT proceed (runProceeds = False).
resume_axioms = [
    Implies(resumeHashMismatch, Not(runProceeds)),
]

# CHECK-11a: Hash mismatch → run cannot proceed
check("CHECK-11a", resume_axioms + [
    resumeHashMismatch,
    runProceeds,
], "unsat", "CHECK-11a: resumeHashMismatch ∧ runProceeds is UNSAT — integrity gate blocks [REQ-STATE-005]")

# CHECK-11b: Hash match → run CAN proceed
check("CHECK-11b", resume_axioms + [
    Not(resumeHashMismatch),
    runProceeds,
], "sat", "CHECK-11b: ¬resumeHashMismatch ∧ runProceeds is SAT — clean resume allowed")

# ── Checklist approval before use (CHECK-12 family) — REQ-SPEC-016 ──────────
# A DRAFT (unapproved) checklist MUST NOT be used for proactive discovery.
checklist_axioms = [
    Implies(checklistIsDraft, Not(checklistUsedForDisc)),
]

# CHECK-12a: DRAFT checklist cannot be used for discovery
check("CHECK-12a", checklist_axioms + [
    checklistIsDraft,
    checklistUsedForDisc,
], "unsat", "CHECK-12a: DRAFT checklist ∧ used-for-discovery is UNSAT [REQ-SPEC-016]")

# CHECK-12b: Approved checklist CAN be used for discovery
check("CHECK-12b", checklist_axioms + [
    Not(checklistIsDraft),
    checklistUsedForDisc,
], "sat", "CHECK-12b: Approved checklist may be used for discovery — rule not vacuous")

# ── Omission-declaration gate (CHECK-13 family) — REQ-SPEC-018 ───────────────
# A subagent result whose omission_declaration field is null or absent MUST NOT be accepted.
# The SubagentStop hook rejects such results with exit 2 (Property 30).
omissionDeclNull   = Bool("omissionDeclNull")   # True = omission_declaration is null/absent
subagentAccepted13 = Bool("subagentAccepted13") # True = SubagentStop accepts the result
omission_gate_axioms = [
    Implies(omissionDeclNull, Not(subagentAccepted13)),
]

# CHECK-13a: null omission_declaration → subagent result CANNOT be accepted
check("CHECK-13a", omission_gate_axioms + [
    omissionDeclNull,
    subagentAccepted13,
], "unsat", "CHECK-13a: null omission_declaration ∧ result accepted is UNSAT [REQ-SPEC-018]")

# CHECK-13b: non-null omission_declaration → subagent result CAN be accepted
check("CHECK-13b", omission_gate_axioms + [
    Not(omissionDeclNull),
    subagentAccepted13,
], "sat", "CHECK-13b: non-null omission_declaration — result may be accepted [REQ-SPEC-018]")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: Final report
# ─────────────────────────────────────────────────────────────────────────────
TOTAL = checks_run            # real number of assertions executed (currently 34) — never hardcoded
passed_count = TOTAL - len(failures)

print(f"\n{'─'*72}")
print(f"  Result: {passed_count}/{TOTAL} checks passed")
if failures:
    print(f"\n  FAILURES ({len(failures)}):")
    for label, expected, got, desc in failures:
        print(f"    {label}: expected={expected}  got={got}")
        print(f"           {desc}")
    print()
    sys.exit(1)
else:
    print(f"  All {TOTAL} checks passed. exit 0.")
    print(f"  Groups: core-14 (CHECK-1..5c) + Kiro-12 (CHECK-6a..9c) + new-8 (CHECK-10a..13b) = {TOTAL}")
    print(f"{'─'*72}\n")
    sys.exit(0)

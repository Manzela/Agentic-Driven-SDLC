"""
formal_verification.py

╔══════════════════════════════════════════════════════════════════════════╗
║  DEPRECATED — SUPERSEDED BY formal_verification_merged.py (34 assertions).  ║
║  Do NOT run this in CI or cite its count. This predecessor executes 23      ║
║  check() calls but hardcodes total=21 (the same count bug fixed upstream).  ║
║  Retained for history only. The canonical harness is the merged file.      ║
╚══════════════════════════════════════════════════════════════════════════╝

Spec-to-Evidence Coverage Control System — Z3 SMT Harness (DEPRECATED)
Z3 v4.16.0  |  exit 0 = all checks pass, exit 1 = one or more failures

This harness encodes and machine-checks the critical invariants of the
Spec-to-Evidence Coverage Control System PRD. It covers:
  - The original 12 checks from the PRD (CHECK-1 through CHECK-5)
  - Extended checks for the three gap requirements identified in audit:
      CHECK-6: Scope-sequencing gate (REQ-EXEC-005 candidate)
      CHECK-7: Evidence schema completeness (REQ-COV-006 candidate)
      CHECK-8: No-progress predicate preciseness (REQ-LOOP-002 refinement)
      CHECK-9: Domain-baseline UNMAPPED blocks advancement (REQ-SPEC-011)

Run: python3 formal_verification.py
"""

from z3 import (
    Bool, And, Or, Not, Implies, Solver, sat, unsat, BoolVal
)
import sys

failures = []

def check(label, solver_or_expr, expected, description):
    """
    Run a satisfiability check and compare against expected result.
    expected: 'sat' or 'unsat'
    """
    s = Solver()
    if isinstance(solver_or_expr, list):
        for c in solver_or_expr:
            s.add(c)
    else:
        s.add(solver_or_expr)

    result = s.check()
    verdict = "sat" if result == sat else "unsat"
    passed = (verdict == expected)
    status = "✓" if passed else "✗ FAIL"
    print(f"  {status}  {label:10s}  expected={expected:5s}  got={verdict:5s}  | {description}")
    if not passed:
        failures.append((label, expected, verdict, description))
    return passed


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: Core model variables
# ─────────────────────────────────────────────────────────────────────────────
# Run-state
maint          = Bool("maint")           # system is in maintenance mode
writeAllowed   = Bool("writeAllowed")     # writes are permitted
planApproved   = Bool("planApproved")     # human approved the plan
codeWrite      = Bool("codeWrite")        # an implementation write is occurring
adminSave      = Bool("adminSave")        # an admin-initiated save

# Coverage / completion state
unproven       = Bool("unproven")         # any in-scope item is unproven
complete       = Bool("complete")         # run has reached COMPLETE terminal state
handoff        = Bool("handoff")          # run has reached HANDOFF terminal state
running        = Bool("running")          # run is in progress

# Loop controls
capReached     = Bool("capReached")       # iteration cap hit
budgetExceeded = Bool("budgetExceeded")   # cost/token budget exceeded
noProgress     = Bool("noProgress")       # no measurable progress across N iterations

# Evidence / verification
evidence       = Bool("evidence")         # evidence artifact is attached
testsPass      = Bool("testsPass")        # tests pass
passed         = Bool("passed")           # item is marked proven
gateBlock      = Bool("gateBlock")        # Stop hook is blocking

# Prediction independence
predA          = Bool("predA")            # prediction variant A
predB          = Bool("predB")            # prediction variant B
gateA          = Bool("gateA")            # gate decision under prediction A
gateB          = Bool("gateB")            # gate decision under prediction B

# Gap-closure variables (new)
priorItemUnproven   = Bool("priorItemUnproven")   # a prior slice item is unproven
newSliceStarting    = Bool("newSliceStarting")     # a new slice is being initiated
scopeGateBlocks     = Bool("scopeGateBlocks")      # scope-sequencing gate fires

evidenceHasTestFile  = Bool("evidenceHasTestFile")   # evidence includes test file ref
evidenceHasTestName  = Bool("evidenceHasTestName")   # evidence includes test name
evidenceHasHash      = Bool("evidenceHasHash")       # evidence includes output hash
evidenceHasTimestamp = Bool("evidenceHasTimestamp")  # evidence includes timestamp
evidenceComplete     = Bool("evidenceComplete")      # all four fields present

noItemsProvenLastN   = Bool("noItemsProvenLastN")    # zero items proven in last N slices
noCommitsLastN       = Bool("noCommitsLastN")        # zero commits in last N slices
noProgressMeasurable = Bool("noProgressMeasurable")  # operationalized no-progress

unmappedExists       = Bool("unmappedExists")        # any baseline item is UNMAPPED
advancementAllowed   = Bool("advancementAllowed")    # system may advance to implementation


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Core axioms (from PRD Step 3)
# ─────────────────────────────────────────────────────────────────────────────
core_axioms = [
    # REQ-GATE-001: gate is a pure function of facts
    gateBlock == unproven,
    # REQ-GATE-002: COMPLETE implies gate not blocking (nothing unproven)
    Implies(complete, Not(gateBlock)),
    # REQ-HITL-001 / REQ-EXEC-004: no code-write without approved plan
    Implies(codeWrite, planApproved),
    # REQ-SEC-004 / REQ-COV: no writes in maintenance mode
    Implies(maint, Not(writeAllowed)),
    # REQ-COV-001/003: PASSED requires evidence AND passing tests
    Implies(passed, And(evidence, testsPass)),
    # REQ-LOOP-002: cap/budget/no-progress → HANDOFF, never COMPLETE
    Implies(Or(capReached, budgetExceeded, noProgress),
            And(handoff, Not(complete))),
    # Terminal exclusivity: COMPLETE or HANDOFF → not running
    Implies(Or(complete, handoff), Not(running)),
    # Cannot be both COMPLETE and HANDOFF
    Not(And(complete, handoff)),
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Original 12 checks (PRD Step 3.3)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Original PRD checks (reproducing machine-verified claims) ─────────────\n")

# CHECK-1: Core axioms admit a clean successful-completion state
check("CHECK-1", core_axioms + [
    Not(unproven),   # all items proven
    complete,        # system declares COMPLETE
    Not(handoff),    # not a handoff
    Not(running),    # terminal
    planApproved,    # plan was approved
    evidence,        # evidence present
    testsPass,       # tests pass
    passed,          # items passed
    Not(capReached), Not(budgetExceeded), Not(noProgress),
    Not(maint),
], "sat", "CHECK-1: Clean successful-completion state is reachable [REQ-GATE-001..002]")

# CHECK-2a: Classic conflict — maint ∧ adminSave naive write rule
check("CHECK-2a", core_axioms + [
    maint,           # in maintenance
    adminSave,       # admin tries to save
    writeAllowed,    # naive rule: adminSave ⇒ write (enforced here as assumption)
], "unsat", "CHECK-2a: maint ∧ naive-adminSave-write is UNSAT — conflict confirmed")

# CHECK-2b: Correction — adminSave write only when NOT in maintenance
check("CHECK-2b", core_axioms + [
    Not(maint),      # NOT in maintenance
    adminSave,       # admin saves
    writeAllowed,    # write is allowed
], "sat", "CHECK-2b: (adminSave ∧ ¬maint) ⇒ write is SAT — correction holds")

# CHECK-3a: System-specific conflict — capReached ∧ unproven ∧ naive COMPLETE rule
check("CHECK-3a", core_axioms + [
    capReached,
    unproven,
    complete,        # naive rule: capReached ⇒ COMPLETE (tested as assumption)
], "unsat", "CHECK-3a: capReached ∧ unproven ∧ complete is UNSAT — conflict confirmed")

# CHECK-3b: Correction — capReached ⇒ HANDOFF (REQ-LOOP-002)
check("CHECK-3b", core_axioms + [
    capReached,
    handoff,
    Not(complete),
], "sat", "CHECK-3b: capReached ⇒ (handoff ∧ ¬complete) is SAT — REQ-LOOP-002 holds")

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

# CHECK-4c: Stop-gate can fire
check("CHECK-4c", core_axioms + [
    unproven,
    gateBlock,
    Not(complete),
], "sat", "CHECK-4c: Stop-gate fires when unproven items exist — reachable")

# CHECK-4d: Stop-gate can clear
check("CHECK-4d", core_axioms + [
    Not(unproven),
    Not(gateBlock),
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

# CHECK-5: Prediction independence — a differing prediction cannot produce a differing gate decision
# Encode: gate decisions are purely a function of facts (gateBlock = unproven, independent of pred)
# Assert pred differs but gate must differ → should be UNSAT
check("CHECK-5", [
    # Gate is a function of facts only, not predictions
    gateA == unproven,
    gateB == unproven,
    # Predictions differ
    predA != predB,
    # Assert gate decisions also differ (this should be impossible)
    gateA != gateB,
], "unsat", "CHECK-5: Differing prediction cannot produce differing gate — predictions never gate [REQ-STEER-006, REQ-PRED-002]")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: Extended checks — gap closure
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Extended checks (gap closure — new requirements) ─────────────────────\n")

# ── Gap 1: Scope-sequencing gate (REQ-EXEC-005 candidate) ────────────────────
# Proposed requirement: IF a prior slice item is unproven, THEN a new slice
# SHALL NOT start (scopeGateBlocks = true blocks newSliceStarting).
scope_sequencing_axioms = [
    # Scope gate: prior unproven item blocks new slice initiation
    Implies(priorItemUnproven, scopeGateBlocks),
    Implies(scopeGateBlocks, Not(newSliceStarting)),
]

# CHECK-6a: New slice cannot start while prior item is unproven
check("CHECK-6a", scope_sequencing_axioms + [
    priorItemUnproven,
    newSliceStarting,  # try to assert new slice IS starting — should be UNSAT
], "unsat", "CHECK-6a: New slice start blocked while prior item unproven [REQ-EXEC-005 candidate]")

# CHECK-6b: New slice CAN start when prior item is proven
check("CHECK-6b", scope_sequencing_axioms + [
    Not(priorItemUnproven),
    Not(scopeGateBlocks),
    newSliceStarting,
], "sat", "CHECK-6b: New slice allowed when all prior items proven — rule not vacuous")

# ── Gap 2: Evidence schema completeness (REQ-COV-006 candidate) ──────────────
# Proposed requirement: evidence is complete IFF all four fields are present.
# An item may not flip to proven without complete evidence.
evidence_schema_axioms = [
    # Complete evidence requires all four fields
    evidenceComplete == And(
        evidenceHasTestFile,
        evidenceHasTestName,
        evidenceHasHash,
        evidenceHasTimestamp,
    ),
    # Passed requires complete evidence (extends REQ-COV-003)
    Implies(passed, evidenceComplete),
]

# CHECK-7a: Cannot be PASSED with incomplete evidence (missing hash)
check("CHECK-7a", evidence_schema_axioms + [
    passed,
    evidenceHasTestFile,
    evidenceHasTestName,
    Not(evidenceHasHash),         # hash missing
    evidenceHasTimestamp,
], "unsat", "CHECK-7a: PASSED without output hash is UNSAT — evidence schema enforced [REQ-COV-006 candidate]")

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

# ── Gap 3: No-progress predicate — operationalized (REQ-LOOP-002 refinement) ─
# Proposed refinement: noProgress is TRUE iff both:
#   (a) no items proven in last N slices, AND
#   (b) no commits produced in last N slices
# This operationalizes the previously word-only "no-progress condition."
no_progress_axioms = [
    # No-progress is the conjunction of both measurable signals
    noProgressMeasurable == And(noItemsProvenLastN, noCommitsLastN),
    # noProgress (used in core axioms) maps to the measurable predicate
    noProgress == noProgressMeasurable,
]

# CHECK-8a: No-progress when neither items proven nor commits produced → HANDOFF
check("CHECK-8a", core_axioms + no_progress_axioms + [
    noItemsProvenLastN,
    noCommitsLastN,
    noProgressMeasurable,
    noProgress,         # fires
], "sat", "CHECK-8a: No-progress condition is reachable when both signals fire")

# CHECK-8b: No-progress + unproven → HANDOFF, never COMPLETE
check("CHECK-8b", core_axioms + no_progress_axioms + [
    noItemsProvenLastN,
    noCommitsLastN,
    noProgressMeasurable,
    noProgress,
    unproven,
    complete,           # try to assert COMPLETE — should be UNSAT
], "unsat", "CHECK-8b: No-progress ∧ unproven ∧ complete is UNSAT — HANDOFF is the only terminal [REQ-LOOP-002]")

# CHECK-8c: Progress IS possible (one item proven + one commit) → no trigger
check("CHECK-8c", core_axioms + no_progress_axioms + [
    Not(noItemsProvenLastN),   # items were proven
    Not(noCommitsLastN),       # commits were made
    Not(noProgressMeasurable),
    Not(noProgress),
    running,                   # still running
    Not(complete), Not(handoff),
], "sat", "CHECK-8c: Active progress suppresses no-progress condition — rule not vacuous")

# ── Gap 4: Domain-baseline UNMAPPED blocks advancement (REQ-SPEC-011) ─────────
# Requirement: IF any baseline item is UNMAPPED (zero proposed requirements),
# THEN advancementAllowed = false.
unmapped_axioms = [
    Implies(unmappedExists, Not(advancementAllowed)),
]

# CHECK-9a: Advancement blocked when any baseline item is UNMAPPED
check("CHECK-9a", unmapped_axioms + [
    unmappedExists,
    advancementAllowed,   # try to assert advancement IS allowed — should be UNSAT
], "unsat", "CHECK-9a: Advancement while UNMAPPED items exist is UNSAT [REQ-SPEC-011]")

# CHECK-9b: Advancement IS allowed when all items are mapped
check("CHECK-9b", unmapped_axioms + [
    Not(unmappedExists),
    advancementAllowed,
], "sat", "CHECK-9b: Advancement allowed when all baseline items are mapped — not vacuous")

# CHECK-9c: UNMAPPED condition does not block COMPLETE (it blocks advancement to impl,
# not the completion gate itself — they are independent)
check("CHECK-9c", unmapped_axioms + core_axioms + [
    # UNMAPPED only fires during spec phase; a fully mapped, proven run can complete
    Not(unmappedExists),
    Not(unproven),
    complete,
    Not(handoff),
    planApproved,
], "sat", "CHECK-9c: Fully-mapped, fully-proven run can reach COMPLETE — UNMAPPED gate and completion gate are independent")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: Final report
# ─────────────────────────────────────────────────────────────────────────────
total = 12 + 9   # 12 original + 9 extended
passed_count = total - len(failures)

print(f"\n{'─'*70}")
print(f"  Result: {passed_count}/{total} checks passed")
if failures:
    print(f"\n  FAILURES:")
    for label, expected, got, desc in failures:
        print(f"    {label}: expected {expected}, got {got}")
        print(f"           {desc}")
    print()
    sys.exit(1)
else:
    print(f"  All checks passed. exit 0.")
    print(f"{'─'*70}\n")
    sys.exit(0)

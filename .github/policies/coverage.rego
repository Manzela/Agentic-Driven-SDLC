package main

# Zero-evidence coverage gate (the merge-time mirror of the Stop hook).
# Denies the merge if any in-scope item is unproven or proven without evidence.

deny[msg] {
    count(input.unproven_in_scope) > 0
    msg := sprintf("coverage gate: %d in-scope item(s) still unproven: %v", [count(input.unproven_in_scope), input.unproven_in_scope])
}

deny[msg] {
    count(input.missing_evidence) > 0
    msg := sprintf("coverage gate: %d proven item(s) missing evidence: %v", [count(input.missing_evidence), input.missing_evidence])
}

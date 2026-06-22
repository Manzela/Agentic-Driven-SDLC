# Feature: spec-to-evidence-control, Property 22: OPA Zero-Evidence Policy at Merge
#
# Full OPA/Conftest zero-evidence merge policy (Phase-1 task 21.1), replacing the
# Phase-0 status-only stub. Conftest evaluates `feature_list.json` as the document
# `input`, i.e. `conftest test feature_list.json`. The `deny` rules below are the
# Rego twin of `tools/coverage_gate.py:deny_merge` and are kept LOGICALLY
# IDENTICAL to it and to the Stop completion gate `stop_hook.evaluate_stop`.
#
# Requirements: 5.7, 10.3 (REQ-GATE-002 mirror at the merge boundary).
# Property: Property 22 (design.md ~line 1613).
#
# Gate semantics (all over IN-SCOPE items only — Req 5.7):
#   1. Filter `input.items` to `in_scope == true` BEFORE any check. Out-of-scope
#      items NEVER trigger a denial.
#   2. Deny if any in-scope item has `status != "proven"` (a `failed` in-scope
#      item blocks identically to `unproven` — anything not exactly "proven").
#   3. Deny if any in-scope `proven` item lacks a complete four-field
#      Evidence_Record (`test_file`, `test_name`, `output_hash`, `collected_at`
#      each present AND non-empty) — matching the SubagentStop four-field gate.
#   4. Deny if there are zero in-scope items (empty coverage model): a valid INIT
#      state but never a valid COMPLETE/merge state; it must not vacuously pass.
#
# Any `deny` message present => Conftest fails the test => merge blocked.

package main

import rego.v1

# The four required Evidence_Record fields. Mirrors EVIDENCE_FIELDS in
# tools/coverage_gate.py and the JSON-Schema EvidenceRecord.required list.
# `actor_agent` / `evidence_kind` are provenance, NOT part of this gate.
evidence_fields := {"test_file", "test_name", "output_hash", "collected_at"}

# In-scope items only (Req 5.7), mirroring evaluate_stop's in_scope_items.
in_scope_items contains item if {
	some item in input.items
	item.in_scope == true
}

# ── Rule 1: status gate ──────────────────────────────────────────────────────
# Any in-scope item whose status is not exactly "proven" denies the merge.
deny contains msg if {
	some item in in_scope_items
	item.status != "proven"
	msg := sprintf(
		"Merge denied: in-scope item %q has status=%q (not 'proven').",
		[object.get(item, "id", "<no-id>"), object.get(item, "status", "<none>")],
	)
}

# ── Rule 2: evidence gate ────────────────────────────────────────────────────
# Any in-scope proven item missing its `evidence` object denies the merge.
deny contains msg if {
	some item in in_scope_items
	item.status == "proven"
	not item.evidence
	msg := sprintf(
		"Merge denied: in-scope item %q is 'proven' but carries no Evidence_Record object.",
		[object.get(item, "id", "<no-id>")],
	)
}

# Any in-scope proven item whose evidence object is missing/empty on any of the
# four required fields denies the merge.
deny contains msg if {
	some item in in_scope_items
	item.status == "proven"
	item.evidence
	some field in evidence_fields
	field_missing_or_empty(item.evidence, field)
	msg := sprintf(
		"Merge denied: in-scope item %q is 'proven' but its Evidence_Record field %q is missing or empty.",
		[object.get(item, "id", "<no-id>"), field],
	)
}

# ── Rule 3: empty-coverage-model gate ────────────────────────────────────────
# Zero in-scope items is a valid INIT state but never a valid COMPLETE/merge
# state — deny so it cannot vacuously satisfy the gate.
deny contains msg if {
	count(in_scope_items) == 0
	msg := "Merge denied: feature_list.json has zero in-scope items. A zero-item coverage model is a valid INIT state but never a valid COMPLETE/merge state."
}

# ── Rule 4: actor-separation (provenance) ────────────────────────────────────
# A proven in-scope item's evidence must name DISTINCT implementer/verifier
# sessions (zero-trust: an implementer may not self-verify). Phase A trusts the
# ids; Phase B adds cryptographic attestation + ledger cross-check at CI. This
# is the Rego twin of coverage_gate.deny_merge's Rule 3.
deny contains msg if {
	some item in in_scope_items
	item.status == "proven"
	item.evidence
	not _distinct_sessions(item.evidence)
	msg := sprintf("Merge denied: in-scope item %q evidence lacks distinct verifier/implementer sessions (self-grading or missing provenance).", [object.get(item, "id", "<no-id>")])
}

_distinct_sessions(ev) if {
	v := _norm_session(ev.verifier_session_id)
	i := _norm_session(ev.implementer_session_id)
	v != ""
	i != ""
	v != i
}

# Normalize an UNTRUSTED session id before the distinctness comparison: strip
# surrounding whitespace, REJECT non-ASCII (-> ""), then lower-case. This closes
# the near-duplicate forgery class ("i" vs " i " vs "I") AND keeps this helper
# IDENTICAL to the Python twin coverage_gate._norm_session / evidence_gate
# (which case-fold): over ASCII, OPA `lower` == Python `casefold`, and any
# non-ASCII id (e.g. "ß", which Python casefold folds to "ss" but OPA lower does
# NOT) normalizes to "" in BOTH and is treated as absent — closing the
# casefold/lower twin-drift. A non-string id normalizes to "". Phase B
# additionally rejects ids absent from the trusted ledger.
_norm_session(value) := lower(trim_space(value)) if {
	is_string(value)
	regex.match(`^[\x00-\x7f]+$`, trim_space(value))
}

_norm_session(value) := "" if not is_string(value)

_norm_session(value) := "" if {
	is_string(value)
	not regex.match(`^[\x00-\x7f]+$`, trim_space(value))
}

# ── Helper: a field is missing or empty on an evidence object ─────────────────
# True when the field is absent, or present but an empty/blank string.
field_missing_or_empty(evidence, field) if {
	not evidence[field]
}

field_missing_or_empty(evidence, field) if {
	value := evidence[field]
	is_string(value)
	trim_space(value) == ""
}

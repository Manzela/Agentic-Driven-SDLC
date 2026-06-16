-- 008_gate_audit_log.sql
-- gate_audit_log: tamper-evident hash-chained gate-decision log (REQ-AUDIT-001/002)
-- Source: .kiro/specs/spec-to-evidence-control/design.md (Merge Reconciliation Addendum)
-- Phase 2 (durable state). Faithful to the canonical CREATE TABLE block.
-- Append-only: prev_hash + entry_hash hash-chain (detective) AND REVOKE+trigger (preventive).

CREATE TABLE gate_audit_log (
    seq            BIGSERIAL PRIMARY KEY,
    event_name     TEXT NOT NULL,
    tool_name      TEXT,
    decision       TEXT NOT NULL CHECK (decision IN ('allow','block')),
    reason         TEXT,
    requirement_id TEXT,                       -- Reconciliation 2026-06-16: INTENTIONALLY bare nullable TEXT with NO FK to requirements(id), unlike the sibling tables (coverage_items/traceability_links/evidence_records/run_state/requirement_versions all FK requirement_id). A gate decision may legitimately be logged BEFORE any requirement is active (e.g. a plan-gate allow/block, or a destructive-Bash artifact-guard block) — those rows carry a NULL or not-yet-persisted requirement_id, so an FK would reject a valid audit entry. The dangling/absent requirement_id is a documented choice for this append-only audit table, not drift.
    actor_agent    TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    prev_hash      TEXT NOT NULL,             -- sha256 of the prior row's canonical form; genesis row uses sha256("") as a documented sentinel
    entry_hash     TEXT NOT NULL              -- sha256(canonical_row || prev_hash); INCLUDES seq and created_at
);
-- Reconciliation 2026-06-16: DB-LEVEL append-only enforcement (added to migration 008 / task 28.8).
--   The hash chain only DETECTS tampering after the fact; REQ-AUDIT-001 intends append-only, so the
--   DB must also PREVENT row mutation. Revoke UPDATE/DELETE from the app role and back it with a
--   trigger that hard-fails any UPDATE or DELETE:
REVOKE UPDATE, DELETE ON gate_audit_log FROM app_role;
CREATE OR REPLACE FUNCTION gate_audit_log_no_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'gate_audit_log is append-only (REQ-AUDIT-001): % forbidden', TG_OP;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER gate_audit_log_append_only
    BEFORE UPDATE OR DELETE ON gate_audit_log
    FOR EACH ROW EXECUTE FUNCTION gate_audit_log_no_mutation();
-- Hash-chain spec (Reconciliation 2026-06-15, from the decision sheet):
--   * Genesis entry: prev_hash = sha256("") (the empty-string digest) as a documented sentinel.
--   * Canonical form = deterministic JSON of (seq, event_name, tool_name, decision,
--       reason, requirement_id, actor_agent, created_at).
--   * NULL canonicalization (Reconciliation 2026-06-16): tool_name, reason, requirement_id are
--       nullable. The canonical JSON ALWAYS emits ALL eight keys (never omits a key), serializes a
--       NULL as the JSON `null` literal (never "" and never key-omission), uses sort_keys=true,
--       UTF-8, and compact separators (no insignificant whitespace). audit_log.py (task 52.1) and
--       audit_verify.py (task 52.2) MUST import ONE shared canonicalizer function so producer and
--       verifier serialize NULL identically — otherwise a divergent serialization would yield a
--       different entry_hash and spuriously fail tamper verification.
--   * entry_hash = sha256(canonical_row || prev_hash), INCLUDING seq and created_at.
--   * seq/created_at write protocol (Reconciliation 2026-06-16): entry_hash INCLUDES seq (BIGSERIAL,
--       DB-assigned) and created_at (DEFAULT now()), but append(event,tool,decision,reason,
--       requirement_id,actor_agent) receives neither — a chicken-and-egg, since hashing-then-INSERT
--       cannot know the DB-assigned values, and INSERT-then-UPDATE would violate append-only. RESOLVED
--       by PRE-ASSIGNING both client-side: append() does `SELECT nextval('gate_audit_log_seq_seq')` to
--       claim seq and sets created_at = now() in the client, computes entry_hash over those exact
--       values, then INSERTs the row supplying the pre-assigned seq + created_at literally — so the
--       stored seq/created_at equal the hashed ones and no post-INSERT UPDATE is ever needed. This is
--       pinned identically in requirements.md Req 27.5 and task 52.1.
--   * Producer: tools/audit_log.append(event, tool, decision, reason, requirement_id, actor_agent),
--       called by stop_hook.py, pre_tool_use_hook.py, and subagent_stop_hook.py on every allow/block.
--   * Verification trigger: a REQUIRED CI status check at merge PLUS on-demand via tools/audit_verify.py;
--       audit_verify recomputes the chain — any prev_hash != recomputed(prior) fails verification.
--   * Append-only is now BOTH convention+hash-chain (detective) AND REVOKE+trigger (preventive).
-- Reconciliation 2026-06-16: VERIFICATION-ACCESS indexes (added to migration task 28.8). The
--   chain re-hash walks rows ORDER BY seq, which is already backed by the BIGSERIAL PRIMARY KEY;
--   bounded whole-chain re-hash at merge is acceptable given the retention policy. For per-decision
--   lookups (audit queries by requirement or by session/time) add a requirement_id index so those
--   queries do not full-scan the unbounded append-only table:
CREATE INDEX idx_gate_audit_log_requirement_id ON gate_audit_log (requirement_id);
CREATE INDEX idx_gate_audit_log_created_at     ON gate_audit_log (created_at);

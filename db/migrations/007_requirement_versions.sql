-- 007_requirement_versions.sql
-- requirement_versions: amendment history (REQ-COV-007)
-- Source: .kiro/specs/spec-to-evidence-control/design.md (Merge Reconciliation Addendum)
-- Phase 2 (durable state). Faithful to the canonical CREATE TABLE block + append-only enforcement.

CREATE TABLE requirement_versions (
    id             SERIAL PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES requirements(id) ON DELETE RESTRICT,  -- Reconciliation 2026-06-16: history must survive requirement deletion
    version        INTEGER NOT NULL,
    prior_text     TEXT,
    new_text       TEXT NOT NULL,
    author         TEXT NOT NULL,
    rationale      TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (requirement_id, version)
);
-- Reconciliation 2026-06-16: VERSION MONOTONICITY mechanism (Property 25 requires a
--   "monotonically increasing version"; the bare UNIQUE (requirement_id, version) above
--   permits gapped/out-of-order sequences, e.g. inserting version=5 then version=3). The
--   amendment_handler (task 28.7 / task 48) computes the next version INSIDE its amendment
--   transaction as `version = COALESCE(MAX(version),0)+1` for the requirement_id (equivalently
--   a BEFORE INSERT trigger enforcing version = previous_max+1), so versions are dense and
--   strictly increasing with no gaps.
-- Reconciliation 2026-06-16: SEEDING semantics — the table holds AMENDMENTS only (no baseline
--   row): the FIRST amendment is version 1, and its `prior_text` is the original approved text
--   read from requirements.id, so `prior_text` is non-null from the first amendment onward.
--   `prior_text` is therefore NOT NULL in practice; a null `prior_text` is reserved for a future
--   optional seed/baseline row and is otherwise forbidden by the amendment_handler.
-- On amendment: insert a version row AND reset coverage_items.status to 'unproven'.
-- Reconciliation 2026-06-16: APPEND-ONLY enforcement for requirement_versions (Property 25 /
--   design says prior version text "shall be retained and never overwritten"). The table has no
--   in-place update path: REVOKE UPDATE/DELETE from the app role and back it with a trigger that
--   hard-fails any UPDATE or DELETE, mirroring gate_audit_log below. The amendment_handler is the
--   SOLE writer and only ever INSERTs (never UPDATEs/DELETEs). Added to migration task 28.7:
REVOKE UPDATE, DELETE ON requirement_versions FROM app_role;
CREATE OR REPLACE FUNCTION requirement_versions_no_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'requirement_versions is append-only (Property 25): % forbidden', TG_OP;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER requirement_versions_append_only
    BEFORE UPDATE OR DELETE ON requirement_versions
    FOR EACH ROW EXECUTE FUNCTION requirement_versions_no_mutation();
-- Reconciliation 2026-06-16: FK ON DELETE + reset mapping. The requirement_id FK above is declared
--   ON DELETE RESTRICT — amendment history must survive any attempt to delete its requirement (a
--   requirement with versioned history cannot be hard-deleted). The amendment's status reset
--   targets coverage_items, which the row references indirectly via requirement_id: the mapping is
--   requirement_id -> coverage_item(s) (1:1 in the common case, 1:many tolerated), and
--   amendment_handler locates the coverage_item(s) to reset by `WHERE requirement_id = $1`. An index
--   on requirement_id (below) backs both the amendment-history lookup and that reset query:
CREATE INDEX idx_requirement_versions_requirement_id ON requirement_versions (requirement_id);

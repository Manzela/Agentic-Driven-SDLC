-- 002_coverage_items.sql
-- coverage_items: mutable status view per requirement
-- Source: .kiro/specs/spec-to-evidence-control/design.md (Postgres Schema)
-- Phase 2 (durable state). Faithful to the canonical CREATE TABLE block.

CREATE TABLE coverage_items (
    id             SERIAL PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES requirements(id),
    status         TEXT NOT NULL CHECK (status IN ('unproven', 'proven', 'failed'))
                   DEFAULT 'unproven',
    subtype        TEXT CHECK (subtype IN ('performance', 'accessibility', 'ui-screen')),  -- Reconciliation 2026-06-16: mirrors feature_list.json CoverageItem.subtype; the Verifier-dispatch discriminator for the fifth (perf/a11y/ui-screen-render) verification layer (REQ-VERIFY-007/008)
    in_scope       BOOLEAN NOT NULL DEFAULT TRUE,  -- Reconciliation 2026-06-15: gates count ONLY in_scope items; leaves scope only via a human-authored transition
                   -- Reconciliation 2026-06-16: ENFORCEMENT of the "human-authored only" rule —
                   --   because gates count only in_scope items, an unguarded flip to in_scope=FALSE
                   --   silently drops a requirement from every completion/Stop gate. The hook/audit
                   --   layer captures every in_scope flip into gate_audit_log (actor_agent +
                   --   justification reason) so the scope-narrowing transition is tamper-evidently
                   --   logged; AND a BEFORE UPDATE trigger requires a non-empty actor + justification
                   --   on any UPDATE that sets in_scope=FALSE (the DB rejects an unattributed flip).
                   --   See REQ-COV / requirements.md:128 (human-authored only).
    slice_id       TEXT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Required index (design.md Migrations & Indexes): status view per requirement
CREATE INDEX idx_coverage_items_requirement_id ON coverage_items (requirement_id);

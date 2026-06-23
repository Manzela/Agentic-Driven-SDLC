-- 006_domain_baseline_checklists.sql
-- domain_baseline_checklists: version history of product-class checklists
-- Source: .kiro/specs/spec-to-evidence-control/design.md (Postgres Schema)
-- Phase 2 (durable state). REQ-SPEC-016 lifecycle. Faithful to the canonical CREATE TABLE block.
-- Reconciliation 2026-06-16: migration file `006_domain_baseline_checklists.sql` (task 28.6).
--   The 006 index was canonical only in tasks.md; named here so it is canonical in design too.
--   Numbering is consistent across files: 006=domain_baseline_checklists, 007=requirement_versions,
--   008=gate_audit_log — no collision; this is a documentation-completeness fix only.

CREATE TABLE domain_baseline_checklists (
    id              SERIAL PRIMARY KEY,
    product_class   TEXT NOT NULL,
    version         TEXT NOT NULL,
    sha             TEXT NOT NULL,    -- git blob SHA of the checklist file
    file_path       TEXT NOT NULL,    -- repo path (e.g. baselines/saas-auth.md)
    approved_at     TIMESTAMPTZ,      -- null = draft, non-null = human-approved
    approved_by     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_class, version)
);

-- 004_evidence_records.sql
-- evidence_records: the four-field Evidence_Record per proven item
-- Source: .kiro/specs/spec-to-evidence-control/design.md (Postgres Schema)
-- Phase 2 (durable state). Faithful to the canonical CREATE TABLE block.
-- Carries the 4 evidence fields (test_file, test_name, output_hash, collected_at)
-- + output_hash format CHECK + actor_agent (Property 24 provenance).

CREATE TABLE evidence_records (
    id              SERIAL PRIMARY KEY,
    requirement_id  TEXT NOT NULL REFERENCES requirements(id),
    commit_sha      TEXT NOT NULL,
    test_file       TEXT NOT NULL,
    test_name       TEXT NOT NULL,
    output_hash     TEXT NOT NULL,   -- sha256:<hex>
    collected_at    TIMESTAMPTZ NOT NULL,
    actor_agent     TEXT NOT NULL,   -- Reconciliation 2026-06-15: the agent that captured this record (MUST be the Verifier, never the Implementer — Property 24). Canonical name is actor_agent everywhere (no acting_agent).
    CONSTRAINT evidence_complete CHECK (
        test_file <> '' AND test_name <> '' AND
        output_hash <> '' AND collected_at IS NOT NULL AND
        -- Reconciliation 2026-06-16: enforce the SAME sha256 format the JSON Schema enforces
        --   (pattern ^sha256:[a-f0-9]{64}$), closing the DB/JSON enforcement asymmetry where a
        --   malformed hash passed the DB CHECK (non-empty only) but failed JSON-schema validation.
        --   Added to migration task 28.4.
        output_hash ~ '^sha256:[a-f0-9]{64}$'
    )
);

-- Required index (design.md Migrations & Indexes): Property 22 per-requirement COUNT
CREATE INDEX idx_evidence_records_requirement_id ON evidence_records (requirement_id);

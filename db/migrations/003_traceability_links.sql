-- 003_traceability_links.sql
-- traceability_links: bidirectional requirement<->code<->test<->commit<->owner graph
-- Source: .kiro/specs/spec-to-evidence-control/design.md (Postgres Schema)
-- Phase 2 (durable state). Faithful to the canonical CREATE TABLE block.

CREATE TABLE traceability_links (
    id              SERIAL PRIMARY KEY,
    requirement_id  TEXT NOT NULL REFERENCES requirements(id),
    link_type       TEXT NOT NULL CHECK (link_type IN
                      ('implementation', 'test', 'evidence', 'commit', 'owner')),
    target_ref      TEXT NOT NULL,   -- file path, commit SHA, owner name, etc.
    direction       TEXT NOT NULL CHECK (direction IN ('forward', 'backward')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Required index (design.md Migrations & Indexes): bidirectional, queried both ways
CREATE INDEX idx_traceability_links_requirement_id ON traceability_links (requirement_id);

-- 001_requirements.sql
-- requirements: the authoritative spec record per project run
-- Source: .kiro/specs/spec-to-evidence-control/design.md (Postgres Schema)
-- Phase 2 (durable state). Faithful to the canonical CREATE TABLE block.

CREATE TABLE requirements (
    id           TEXT PRIMARY KEY,         -- REQ-SPEC-001 etc.
    project_id   TEXT NOT NULL,
    type         TEXT NOT NULL CHECK (type IN ('functional', 'NFR', 'WIRING')),
    nfr_subtype  TEXT CHECK (nfr_subtype IN ('performance', 'accessibility', 'reliability', 'security')),
                 -- Reconciliation 2026-06-16: routing subtype, mirrors feature_list.json CoverageItem.nfr_subtype;
                 -- NOT NULL when type='NFR' is enforced by the writer (and the file-schema allOf), letting
                 -- perf_a11y_verifier pick k6/Lighthouse vs axe-core deterministically (Req 25.1/25.2)
    priority     INTEGER NOT NULL,
    ears_pattern TEXT NOT NULL,
    ears_stmt    TEXT NOT NULL,
    provenance   TEXT NOT NULL CHECK (provenance IN ('stated', 'inferred')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

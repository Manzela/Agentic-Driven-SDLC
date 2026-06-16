"""Independent verifier test for db/migrations/001..008_*.sql.

Written by the INDEPENDENT VERIFIER (not the implementer). Performs pure
string/regex checks against the SQL text — no DB connection required.

Covers:
  REQ-STORE-001..003  (durable schema: 8 tables, all CREATE TABLE)
  REQ-COV-007         (requirement_versions amendment history)
  REQ-AUDIT-001..002  (gate_audit_log tamper-evident hash chain)
  task 28             (Phase 2 migrations)
"""

import re
from pathlib import Path

import pytest

# Resolve db/migrations relative to this test file so the test is cwd-independent.
# tests/spine/test_migrations.py  ->  parents[2] == repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"

# (numeric prefix, expected table name) for each of the 8 migrations.
EXPECTED = [
    ("001", "requirements"),
    ("002", "coverage_items"),
    ("003", "traceability_links"),
    ("004", "evidence_records"),
    ("005", "run_state"),
    ("006", "domain_baseline_checklists"),
    ("007", "requirement_versions"),
    ("008", "gate_audit_log"),
]
EXPECTED_TABLES = {name for _, name in EXPECTED}


def _find_file(prefix: str) -> Path:
    """Locate the migration file whose name starts with the numeric prefix."""
    matches = sorted(MIGRATIONS_DIR.glob(f"{prefix}_*.sql"))
    assert matches, f"no migration file matching {prefix}_*.sql in {MIGRATIONS_DIR}"
    return matches[0]


def _read(prefix: str) -> str:
    return _find_file(prefix).read_text(encoding="utf-8")


def _create_table_columns_block(sql: str, table: str) -> str:
    """Return the text from `CREATE TABLE <table> (` up to the matching close.

    Used to assert a column belongs to THIS table's definition and is not merely
    mentioned in a comment elsewhere in the file. Falls back to whole-text search
    if the parenthesized block can't be isolated.
    """
    m = re.search(
        rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{re.escape(table)}\s*\(",
        sql,
        re.IGNORECASE,
    )
    if not m:
        return sql
    start = m.end() - 1  # position of the opening paren
    depth = 0
    for i in range(start, len(sql)):
        c = sql[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return sql[start : i + 1]
    return sql[start:]


# ---------------------------------------------------------------------------
# 1. All 8 files exist.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("prefix,table", EXPECTED)
def test_migration_file_exists(prefix, table):
    path = _find_file(prefix)
    assert path.is_file(), f"missing migration file for {prefix} ({table})"


def test_exactly_eight_migration_files():
    files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
    assert len(files) == 8, f"expected 8 numbered migration files, found {len(files)}: {[f.name for f in files]}"


# ---------------------------------------------------------------------------
# 2. Each file contains a CREATE TABLE statement.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("prefix,table", EXPECTED)
def test_file_contains_create_table(prefix, table):
    sql = _read(prefix)
    assert re.search(r"CREATE\s+TABLE", sql, re.IGNORECASE), \
        f"{prefix}_*.sql ({table}) has no CREATE TABLE"


# ---------------------------------------------------------------------------
# 3. The 8 expected table names are each created in their file.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("prefix,table", EXPECTED)
def test_expected_table_created(prefix, table):
    sql = _read(prefix)
    assert re.search(
        rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{re.escape(table)}\b",
        sql,
        re.IGNORECASE,
    ), f"{prefix}_*.sql does not CREATE TABLE {table}"


def test_all_expected_tables_covered_across_suite():
    """The full set of 8 canonical table names is created somewhere in db/migrations."""
    all_sql = "\n".join(p.read_text(encoding="utf-8") for p in MIGRATIONS_DIR.glob("*.sql"))
    created = set(re.findall(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)",
        all_sql,
        re.IGNORECASE,
    ))
    missing = EXPECTED_TABLES - created
    assert not missing, f"expected tables not created in any migration: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 4. evidence_records carries the 5 required columns.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "column", ["output_hash", "collected_at", "test_file", "test_name", "actor_agent"]
)
def test_evidence_records_has_column(column):
    block = _create_table_columns_block(_read("004"), "evidence_records")
    assert re.search(rf"\b{re.escape(column)}\b", block), \
        f"evidence_records is missing column {column}"


# ---------------------------------------------------------------------------
# 5. run_state carries status + resume_integrity_ok.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("column", ["status", "resume_integrity_ok"])
def test_run_state_has_column(column):
    block = _create_table_columns_block(_read("005"), "run_state")
    assert re.search(rf"\b{re.escape(column)}\b", block), \
        f"run_state is missing column {column}"


# ---------------------------------------------------------------------------
# 6. gate_audit_log has an entry-hash column AND a prior/prev-hash column.
# ---------------------------------------------------------------------------
def test_gate_audit_log_has_entry_hash():
    block = _create_table_columns_block(_read("008"), "gate_audit_log")
    assert re.search(r"\bentry_hash\b", block), "gate_audit_log missing entry_hash column"


def test_gate_audit_log_has_prev_hash():
    block = _create_table_columns_block(_read("008"), "gate_audit_log")
    # accept prev_hash / prior_hash / previous_hash as the chain-link column
    assert re.search(r"\b(?:prev|prior|previous)_hash\b", block), \
        "gate_audit_log missing a prior/prev-hash chain column"

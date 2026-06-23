"""Tests for tools/wiring_dedup.py — union-of-concerns merge (Task 10 / Property T6).

Spec §2.1: "A qualname flagged by EITHER source is a finding. A Semgrep 'clean' verdict
NEVER overrides an AST 'orphan' verdict." Both sources key candidates by qualname; the
merge is a mechanical union. Runs BEFORE Task 8's ingest write.
"""

import json
import tempfile
from pathlib import Path

from tools.feature_list_init import init_feature_list, validate_against_schema, write_feature_list
from tools.wiring_dedup import merge
from tools.wiring_ingest import ingest_wiring_candidates


def test_ast_orphan_alone_is_a_finding():
    ast = [{"id": "REQ-WIRE-001", "type": "WIRING", "qualname": "MyClass.unused_method",
            "wiring": {"symbol": "unused_method", "file": "app.py", "line": 42, "reachable": False}}]
    result = merge(ast, [])
    assert len(result) == 1
    assert result[0]["qualname"] == "MyClass.unused_method"
    assert result[0]["reachable"] is False
    assert "wiring" in result[0]


def test_semgrep_clean_alone_is_ok():
    semgrep = [{"qualname": "some_helper", "status": "clean", "decorator": None, "callback": None}]
    assert merge([], semgrep) == []


def test_semgrep_clean_does_not_retract_ast_orphan():
    """T6: AST says unreachable, Semgrep says clean. Union wins: finding."""
    ast = [{"id": "REQ-WIRE-042", "type": "WIRING", "qualname": "handler_func",
            "wiring": {"symbol": "handler_func", "file": "routes.py", "line": 99, "reachable": False}}]
    semgrep = [{"qualname": "handler_func", "status": "clean", "decorator": None, "callback": None}]
    result = merge(ast, semgrep)
    assert len(result) == 1
    assert result[0]["qualname"] == "handler_func"
    assert result[0]["reachable"] is False              # AST orphan preserved
    # Semgrep verdict enriches under semgrep_status — NOT status — so it can never
    # clobber the CoverageItem lifecycle status (red-team F1).
    assert result[0].get("semgrep_status") == "clean"


def test_semgrep_finding_alone_is_a_finding():
    """AST seeded the symbol reachable; Semgrep flags it dead with decorator context."""
    ast = [{"id": "REQ-WIRE-005", "type": "WIRING", "qualname": "RouteHandler.on_request",
            "wiring": {"symbol": "on_request", "file": "server.py", "line": 50, "reachable": True}}]
    semgrep = [{"qualname": "RouteHandler.on_request", "status": "dead",
                "decorator": "app.route", "callback": None,
                "reason": "decorator-routed but never registered"}]
    result = merge(ast, semgrep)
    assert len(result) == 1
    assert result[0]["qualname"] == "RouteHandler.on_request"
    assert result[0].get("decorator") == "app.route"


def test_both_sources_agree_on_reachable():
    ast = [{"id": "REQ-WIRE-010", "type": "WIRING", "qualname": "main",
            "wiring": {"symbol": "main", "file": "__main__.py", "line": 1, "reachable": True}}]
    semgrep = [{"qualname": "main", "status": "clean", "decorator": None, "callback": None}]
    assert merge(ast, semgrep) == []


def test_multiple_symbols_union_merge():
    ast = [
        {"id": "REQ-WIRE-001", "type": "WIRING", "qualname": "func_a",
         "wiring": {"symbol": "func_a", "file": "a.py", "line": 10, "reachable": False}},
        {"id": "REQ-WIRE-002", "type": "WIRING", "qualname": "func_b",
         "wiring": {"symbol": "func_b", "file": "b.py", "line": 20, "reachable": True}},
    ]
    semgrep = [
        {"qualname": "func_b", "status": "dead", "decorator": "app.route", "callback": None},
        {"qualname": "func_c", "status": "clean", "decorator": None, "callback": None},
    ]
    result = merge(ast, semgrep)
    # func_a: AST orphan -> finding; func_b: Semgrep dead -> finding; func_c: clean -> none.
    assert {r["qualname"] for r in result} == {"func_a", "func_b"}


def test_output_shape_matches_ingest_contract():
    ast = [{"id": "REQ-WIRE-042", "type": "WIRING", "priority": 1, "dependencies": [],
            "acceptance_criteria": ["Symbol is reachable from a real execution path."],
            "status": "unproven", "in_scope": True, "qualname": "dead_func",
            "wiring": {"symbol": "dead_func", "qualname": "dead_func", "file": "app.py",
                       "line": 55, "reachable": False}}]
    result = merge(ast, [])
    assert len(result) == 1
    merged = result[0]
    for key in ("id", "type", "qualname", "wiring"):
        assert key in merged
    assert merged["type"] == "WIRING"


def test_semgrep_dead_without_ast_is_a_finding():
    """'Either source' — a Semgrep 'dead' verdict with no AST counterpart is still a
    finding (symmetric union), SYNTHESIZED into a full ingestible unproven WIRING item
    (red-team F4: a bare {qualname, status} would be silently dropped at ingest)."""
    semgrep = [{"qualname": "ghost_handler", "status": "dead", "decorator": "app.get",
                "callback": None, "reason": "decorator-routed, never called"}]
    result = merge([], semgrep)
    assert len(result) == 1
    m = result[0]
    assert m["qualname"] == "ghost_handler"
    assert m["type"] == "WIRING"
    assert m["status"] == "unproven"            # lifecycle status, NOT the semgrep verdict
    assert m["semgrep_status"] == "dead"
    assert m["wiring"]["qualname"] == "ghost_handler"
    assert m.get("decorator") == "app.get"
    for key in ("id", "type", "priority", "dependencies", "acceptance_criteria",
                "status", "in_scope"):
        assert key in m                          # schema-required ingest fields


def test_merge_output_is_ingestible_end_to_end():
    """The merge output feeds Task-8 ingest unchanged: a dual-flagged AST+Semgrep item
    (lifecycle status preserved) AND a Semgrep-only finding both land as schema-valid
    unproven WIRING items (red-team F1+F4 — the merge→ingest pipeline holds)."""
    ast = [{"id": "REQ-WIRE-001", "type": "WIRING", "priority": 1, "dependencies": [],
            "acceptance_criteria": ["wired"], "status": "unproven", "in_scope": True,
            "qualname": "dual", "wiring": {"symbol": "dual", "qualname": "dual",
            "file": "a.py", "line": 1, "reachable": True}}]
    semgrep = [{"qualname": "dual", "status": "dead", "decorator": "app.route"},
               {"qualname": "ghost", "status": "dead", "decorator": "app.get"}]
    merged = merge(ast, semgrep)
    assert {m["qualname"] for m in merged} == {"dual", "ghost"}

    with tempfile.TemporaryDirectory() as t:
        fp = Path(t) / "feature_list.json"
        write_feature_list(init_feature_list(items=[]), str(fp))
        count = ingest_wiring_candidates(merged, str(fp))
        assert count == 2                         # BOTH ingested (none dropped, none rejected)
        content = json.loads(fp.read_text())
        validate_against_schema(content)          # the model stays schema-valid
        assert {i["wiring"]["qualname"] for i in content["items"]} == {"dual", "ghost"}

"""Independent verifier tests for tools/wiring_checker.py (slice: wiring_checker).

Contract under test (REQ-WIRE-001..003 / tasks.md task 19):

  * ``analyze([...])`` performs whole-repo static call-graph / dead-code
    analysis and flags a defined-but-never-referenced NON-test symbol as
    ``dead_code`` — and does NOT flag a symbol that is reached from a real
    execution path.
  * ``emit_wiring_items(analysis)`` projects the analysis into feature_list
    WIRING CoverageItem candidates, every one of which carries
    ``type == "WIRING"`` and ``status == "unproven"``.

These tests are written independently of the implementer; they build a real
temporary module on disk (one used function, one unused function) and assert
the analysis classifies EXACTLY the unused one as dead code.
"""

from __future__ import annotations

import textwrap

from tools.wiring_checker import analyze, emit_wiring_items


# A module with exactly two top-level functions:
#   * ``used_helper`` is called by ``entry_point``;
#   * ``entry_point`` is invoked from module-level executable code (a real
#     execution path / seeded entry point), which transitively makes
#     ``used_helper``'s bare name appear in the repo-wide reference pool.
#   * ``unused_orphan`` is defined but never referenced anywhere -> dead code.
_MODULE_SRC = textwrap.dedent(
    '''\
    """Fixture module for wiring_checker verification."""


    def used_helper(value):
        return value + 1


    def entry_point():
        return used_helper(41)


    def unused_orphan():
        return "never wired into any execution path"


    RESULT = entry_point()
    '''
)


def _write_module(tmp_path):
    mod = tmp_path / "fixture_mod.py"
    mod.write_text(_MODULE_SRC, encoding="utf-8")
    return str(mod)


def test_analyze_flags_only_the_unused_function_as_dead_code(tmp_path):
    """The orphan is flagged dead; the used helper and entry point are not."""
    path = _write_module(tmp_path)

    result = analyze([path])

    assert isinstance(result, dict)
    assert "dead_code" in result and "wiring_items" in result

    dead_symbols = {entry["symbol"] for entry in result["dead_code"]}

    # EXACTLY the unused function is dead code.
    assert dead_symbols == {"unused_orphan"}, (
        f"expected only 'unused_orphan' flagged dead, got {dead_symbols}"
    )

    # The used function and the entry point are explicitly NOT dead.
    assert "used_helper" not in dead_symbols
    assert "entry_point" not in dead_symbols

    # The dead-code entry points at the right file/symbol.
    (orphan_entry,) = result["dead_code"]
    assert orphan_entry["symbol"] == "unused_orphan"
    assert orphan_entry["file"] == path


def test_used_symbol_is_recorded_reachable_in_wiring_items(tmp_path):
    """The used helper appears as a reachable wiring obligation, not dead."""
    path = _write_module(tmp_path)

    result = analyze([path])

    by_symbol = {w["symbol"]: w for w in result["wiring_items"] if w.get("symbol")}

    assert by_symbol["used_helper"]["reachable"] is True
    assert by_symbol["entry_point"]["reachable"] is True
    assert by_symbol["unused_orphan"]["reachable"] is False


def test_emit_wiring_items_type_and_status_contract(tmp_path):
    """Every emitted candidate is type=='WIRING' and status=='unproven'."""
    path = _write_module(tmp_path)

    result = analyze([path])
    items = emit_wiring_items(result)

    # One candidate per analyzable defined symbol (3 here).
    assert len(items) >= 1
    assert len(items) == len(
        [w for w in result["wiring_items"] if w.get("symbol")]
    )

    for item in items:
        assert item["type"] == "WIRING", f"bad type on {item.get('id')}: {item}"
        assert item["status"] == "unproven", (
            f"bad status on {item.get('id')}: {item}"
        )
        # Minimal CoverageItem shape the ingestion path depends on.
        assert item["id"]
        assert item["acceptance_criteria"]

    # The orphan and the used helper are both projected as WIRING candidates.
    emitted_symbols = {item["wiring"]["symbol"] for item in items}
    assert {"used_helper", "entry_point", "unused_orphan"} <= emitted_symbols

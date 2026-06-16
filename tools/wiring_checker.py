"""wiring_checker.py — static call-graph / dead-code analysis (AST).

Spec
----
``.kiro/specs/spec-to-evidence-control/design.md`` — Component Inventory row
``wiring_checker.py`` (Phase 1) and the dedicated subsection
"Wiring / Dead-Code Analysis (`wiring_checker.py`)" (design.md §"Wiring /
Dead-Code Analysis"). Tasks ``tasks.md`` task 19 (19.1 implement, 19.3 the
WIRING-candidate ingestion contract). Requirement 8 / REQ-EXEC-010..012.

This is the ENGINE invoked by the PostToolUse hook (``post_tool_use_hook.py``,
task 18.1) on the changed-file set; it performs the static call-graph /
dead-code analysis and emits ``type: "WIRING"`` coverage-item candidates. It
does NOT gate — blocking is the hook's job; ``analyze`` never raises on a
finding and (when run as a CLI) the process exits 0 even when findings exist.

Faithful spec contract realized here
-------------------------------------
* **Whole-repo, not per-file reachability** (design.md "Reachability scope").
  Per-file AST graphs are MERGED into one repo-wide call/usage graph before
  reachability is computed, so a public/exported symbol called only from
  another file in the set is NOT a false-positive.

* **Real-execution-path / entry-point seeding** (design.md "Definition of
  'real execution path'"). Reachability is computed from seeded ENTRY POINTS:
  module-level `if __name__ == "__main__"` blocks, decorator-routed
  handlers/routes (`@app.route`, `@router.get`, registered hook/event
  callbacks), and module-level executable statements (a module's import-time
  body is a real execution path). **Test files are excluded from entry-point
  seeding** — a symbol reachable ONLY from a test is NOT "wired into a real
  execution path".

* **Division of labor with Semgrep** (tasks.md 19.1 / 24.1). This AST checker
  OWNS plain *defined-but-never-called* functions/classes. Decorator-routed
  handlers and registered-but-uninvoked callbacks are Semgrep's domain
  (`wiring_dead_code.yml`, task 24.1); a decorated handler is therefore SEEDED
  as an entry point here and emits ZERO candidates from this tool, avoiding
  double-reporting of the same 8.2 obligation.

* **Emission** (design.md "Emission" / Property 1 via task 19.3). For each
  defined-but-unreachable NON-test symbol the analysis records exactly ONE
  ``dead_code`` entry and one WIRING coverage-item candidate naming that
  symbol; for every reachable symbol it records a ``wiring_items`` obligation
  with the reached/unreached fact. ``emit_wiring_items`` projects the analysis
  into ``feature_list.json`` WIRING CoverageItems with ``type="WIRING"`` and
  ``status="unproven"``.

* **Assurance level** (design.md): no Z3 CHECK / no Correctness Property —
  runtime-verified by example tests (19.2, 26.1). Stated, not silent.

Pure stdlib (``ast`` only). Importable and side-effect free.
"""

from __future__ import annotations

import ast
import os
from typing import Any, Dict, List, Optional, Set, Tuple

__all__ = [
    "analyze",
    "emit_wiring_items",
    "WIRING_REQ_PREFIX",
    "is_test_path",
]

# WIRING coverage-item candidates synthesized by this tool carry a stable,
# tool-namespaced id prefix so the ingestion path (task 19.3) and the Verifier
# can recognize a wiring-checker-sourced candidate. The canonical
# CoverageItem.id pattern is ``^[A-Z]+-[A-Z]+-[0-9]{3}$``; ids minted here use
# the ``REQ-WIRE-NNN`` namespace.
WIRING_REQ_PREFIX = "REQ-WIRE"

# Decorator name fragments that mark a function as a route/handler/registered
# callback — i.e. an entry point reached by the framework, not by a direct
# in-repo call. These are SEEDED as reachable here and left to Semgrep
# (task 24.1) to judge as dead, so this tool never double-reports them.
_HANDLER_DECORATOR_HINTS: Tuple[str, ...] = (
    "route",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "head",
    "options",
    "websocket",
    "command",
    "callback",
    "handler",
    "on_event",
    "task",
    "listen",
    "subscribe",
    "hook",
    "fixture",
)


# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

def is_test_path(path: str) -> bool:
    """Return ``True`` when ``path`` denotes a test file.

    Test files are EXCLUDED from entry-point seeding (design.md: a symbol
    reachable only from a test is not wired into a real execution path) and
    their own defined symbols are not reported as dead code (test helpers are
    out of the wiring obligation's scope).

    A path is a test file when any path segment is ``tests``/``test``, or the
    basename starts with ``test_`` or ends with ``_test.py``, or it lives under
    a ``conftest.py``-style test fixture file.
    """
    norm = path.replace("\\", "/")
    base = os.path.basename(norm)
    parts = [p for p in norm.split("/") if p]
    for seg in parts[:-1]:
        if seg in ("tests", "test"):
            return True
    if base == "conftest.py":
        return True
    if base.startswith("test_") and base.endswith(".py"):
        return True
    if base.endswith("_test.py"):
        return True
    return False


# ---------------------------------------------------------------------------
# Per-file parse into a symbol/def + reference model
# ---------------------------------------------------------------------------

class _FileModel:
    """Parsed model of a single source file.

    Attributes
    ----------
    path:
        Source path as supplied by the caller.
    is_test:
        Whether this is a test file (excluded from entry-point seeding).
    defs:
        Mapping ``qualname -> _SymbolDef`` for every top-level and nested
        function/method/class definition in the file.
    referenced_names:
        The set of *bare* names referenced anywhere in the file (call targets,
        attribute roots, plain ``Name`` loads, decorator names). This is the
        repo-wide reference pool a symbol must appear in to be "called".
    entry_qualnames:
        Qualnames defined in this file that are SEEDED entry points: module
        ``__main__`` block targets, decorator-routed handlers, and module-level
        executable references. Empty for test files (no seeding).
    parse_error:
        ``None`` on success, else a short string describing the SyntaxError.
    """

    __slots__ = (
        "path",
        "is_test",
        "defs",
        "referenced_names",
        "entry_qualnames",
        "parse_error",
    )

    def __init__(self, path: str) -> None:
        self.path = path
        self.is_test = is_test_path(path)
        self.defs: Dict[str, "_SymbolDef"] = {}
        self.referenced_names: Set[str] = set()
        self.entry_qualnames: Set[str] = set()
        self.parse_error: Optional[str] = None


class _SymbolDef:
    """A single function/method/class definition discovered in a file."""

    __slots__ = ("name", "qualname", "kind", "path", "lineno", "decorated")

    def __init__(
        self,
        name: str,
        qualname: str,
        kind: str,
        path: str,
        lineno: int,
        decorated: bool,
    ) -> None:
        self.name = name           # bare symbol name (e.g. "handle")
        self.qualname = qualname   # dotted path within the file (e.g. "C.handle")
        self.kind = kind           # "function" | "method" | "class"
        self.path = path
        self.lineno = lineno
        self.decorated = decorated  # carries a route/handler/callback decorator


def _decorator_names(node: ast.AST) -> List[str]:
    """Return the textual names of a def/class node's decorators."""
    names: List[str] = []
    for dec in getattr(node, "decorator_list", []) or []:
        names.append(_dotted_tail(dec))
    return names


def _dotted_tail(node: ast.AST) -> str:
    """Best-effort last-component name of a decorator/attr/call expression.

    ``@app.route(...)`` -> ``route``; ``@router.get`` -> ``get``;
    ``@staticmethod`` -> ``staticmethod``; ``@a.b.c`` -> ``c``.
    """
    cur = node
    if isinstance(cur, ast.Call):
        cur = cur.func
    if isinstance(cur, ast.Attribute):
        return cur.attr
    if isinstance(cur, ast.Name):
        return cur.id
    return ""


def _is_handler_decorator(dec_name: str) -> bool:
    """Whether a decorator name marks a route/handler/registered callback."""
    low = dec_name.lower()
    return any(hint in low for hint in _HANDLER_DECORATOR_HINTS)


class _DefAndRefVisitor(ast.NodeVisitor):
    """Collects definitions, references, and seeded entry points for one file.

    Definitions: every function/async-function/class node, recorded with its
    dotted qualname within the file (``Outer.inner``). References: the bare name
    of every call target, attribute root, decorator, and ``Name`` load — the
    pool a definition must appear in to count as "called" repo-wide. Entry
    points: decorator-routed handlers, plus any def referenced from a
    module-level ``if __name__ == "__main__"`` block or other module-level
    executable code.
    """

    def __init__(self, model: _FileModel) -> None:
        self.model = model
        self._scope: List[str] = []          # enclosing def/class names
        self._class_depth = 0                # >0 means we are inside a class body

    # -- helpers ---------------------------------------------------------------

    def _qual(self, name: str) -> str:
        return ".".join([*self._scope, name]) if self._scope else name

    def _record_def(self, node: ast.AST, kind: str) -> None:
        name = getattr(node, "name", None)
        if not name:
            return
        qual = self._qual(name)
        decs = _decorator_names(node)
        decorated_handler = any(_is_handler_decorator(d) for d in decs)
        # A method is "kind=method"; a top-level def is "function".
        actual_kind = kind
        if kind == "function" and self._class_depth > 0:
            actual_kind = "method"
        self.model.defs[qual] = _SymbolDef(
            name=name,
            qualname=qual,
            kind=actual_kind,
            path=self.model.path,
            lineno=getattr(node, "lineno", 0),
            decorated=decorated_handler,
        )
        # Decorator-routed handlers are SEEDED entry points (Semgrep's domain),
        # but never for test files (no seeding there).
        if decorated_handler and not self.model.is_test:
            self.model.entry_qualnames.add(qual)
        # The decorator names themselves are references (so a decorator that
        # wraps-and-calls another symbol keeps it alive).
        for d in decs:
            if d:
                self.model.referenced_names.add(d)

    def _descend(self, node: ast.AST, name: str, is_class: bool) -> None:
        self._scope.append(name)
        if is_class:
            self._class_depth += 1
        for child in ast.iter_child_nodes(node):
            self.visit(child)
        if is_class:
            self._class_depth -= 1
        self._scope.pop()

    # -- definition nodes ------------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_def(node, "function")
        self._descend(node, node.name, is_class=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_def(node, "function")
        self._descend(node, node.name, is_class=False)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._record_def(node, "class")
        # base-class names are references (a class used only as a base is wired)
        for base in node.bases:
            self.model.referenced_names.add(_dotted_tail(base))
        self._descend(node, node.name, is_class=True)

    # -- reference nodes -------------------------------------------------------

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.model.referenced_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # record the attribute tail (method/attr name) AND the root name
        self.model.referenced_names.add(node.attr)
        root = node.value
        if isinstance(root, ast.Name):
            self.model.referenced_names.add(root.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        target = node.func
        if isinstance(target, ast.Name):
            self.model.referenced_names.add(target.id)
        elif isinstance(target, ast.Attribute):
            self.model.referenced_names.add(target.attr)
        self.generic_visit(node)


def _seed_module_level_entrypoints(tree: ast.Module, model: _FileModel) -> None:
    """Seed entry points from module-level executable code.

    The module body that runs at import/exec time is a real execution path.
    Any definition NAME referenced from module-level statements (including the
    ``if __name__ == "__main__":`` guard, which is just module-level code) is
    an entry point. Test files are excluded from seeding entirely.
    """
    if model.is_test:
        return

    def_names = {d.name for d in model.defs.values()}

    for stmt in tree.body:
        # Skip the definitions themselves and imports — they don't "invoke".
        if isinstance(
            stmt,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
             ast.Import, ast.ImportFrom),
        ):
            continue
        # Every Name/Attribute/Call referenced at module level (recursively,
        # which covers the __main__ guard body) that matches a def name seeds
        # the shortest matching qualname.
        for ref in ast.walk(stmt):
            ref_name: Optional[str] = None
            if isinstance(ref, ast.Name) and isinstance(ref.ctx, ast.Load):
                ref_name = ref.id
            elif isinstance(ref, ast.Attribute):
                ref_name = ref.attr
            elif isinstance(ref, ast.Call):
                fn = ref.func
                if isinstance(fn, ast.Name):
                    ref_name = fn.id
                elif isinstance(fn, ast.Attribute):
                    ref_name = fn.attr
            if ref_name and ref_name in def_names:
                # Seed every def whose bare name matches (handles top-level and
                # the common single-definition case unambiguously).
                for d in model.defs.values():
                    if d.name == ref_name:
                        model.entry_qualnames.add(d.qualname)


def _parse_file(path: str, source: Optional[str] = None) -> _FileModel:
    """Parse one file into a ``_FileModel``.

    ``source`` may be supplied directly (the file is then not read from disk),
    which keeps the function testable and lets the PostToolUse hook pass
    in-memory edited buffers. A ``SyntaxError`` or read error is captured on the
    model rather than raised — a single unparseable file in the changed set must
    not abort analysis of the rest.
    """
    model = _FileModel(path)
    text = source
    if text is None:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:
            model.parse_error = f"read-error: {exc}"
            return model
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError as exc:
        model.parse_error = f"syntax-error: line {exc.lineno}: {exc.msg}"
        return model

    visitor = _DefAndRefVisitor(model)
    visitor.visit(tree)
    _seed_module_level_entrypoints(tree, model)
    return model


# ---------------------------------------------------------------------------
# Whole-repo reachability + emission
# ---------------------------------------------------------------------------

def analyze(
    source_paths: List[str],
    *,
    sources: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Analyze ``source_paths`` and return wiring + dead-code findings.

    The per-file AST def/reference models are MERGED into one repo-wide
    reachability picture (design.md "Reachability scope (whole-repo, not
    per-file)"): a symbol counts as reached if its bare name appears in the
    repo-wide reference pool OR it is a seeded entry point. This is the
    canonical merged-graph behavior — a public symbol called from a sibling
    file in the set is NOT flagged.

    Parameters
    ----------
    source_paths:
        File paths to analyze (the changed-file set the PostToolUse hook
        derived from ``tool_input.file_path`` / a MultiEdit batch). One path per
        entry, mirroring the CLI argv contract (task 19.1).
    sources:
        Optional ``{path: source_text}`` override so callers (and tests / the
        PostToolUse hook) can supply in-memory buffers instead of reading disk.
        A path present here is not read from disk.

    Returns
    -------
    dict
        ``{"wiring_items": [...], "dead_code": [...]}``.

        * ``dead_code`` — one entry per defined-but-unreachable NON-test symbol:
          ``{"symbol", "qualname", "kind", "file", "line", "reason"}``.
        * ``wiring_items`` — one WIRING obligation per analyzable defined
          NON-test symbol (every symbol that "should be reached"):
          ``{"symbol", "qualname", "kind", "file", "line", "reachable",
          "entry_point", "reason"}``. ``reachable == False`` rows are exactly
          the dead-code set; ``reachable == True`` rows are proven-wired
          obligations carried so the coverage model can represent the wiring
          requirement either way (Req 8.1: "represent each wiring obligation as
          a WIRING coverage item").
    """
    sources = sources or {}
    # Preserve order, drop duplicates.
    seen: Set[str] = set()
    ordered_paths: List[str] = []
    for p in source_paths or []:
        if p not in seen:
            seen.add(p)
            ordered_paths.append(p)

    models: List[_FileModel] = [
        _parse_file(p, source=sources.get(p)) for p in ordered_paths
    ]

    # --- merge: one repo-wide reference pool + one entry-point set ------------
    repo_referenced: Set[str] = set()
    repo_entry_qualnames: Set[str] = set()
    repo_entry_names: Set[str] = set()
    for m in models:
        repo_referenced |= m.referenced_names
        repo_entry_qualnames |= m.entry_qualnames

    # Map entry qualnames back to their bare names so a seeded entry point is
    # always considered "reached" even if nothing else references it.
    qual_to_def: Dict[Tuple[str, str], _SymbolDef] = {}
    for m in models:
        for d in m.defs.values():
            qual_to_def[(m.path, d.qualname)] = d
            if d.qualname in repo_entry_qualnames:
                repo_entry_names.add(d.name)

    dead_code: List[Dict[str, Any]] = []
    wiring_items: List[Dict[str, Any]] = []

    for m in models:
        if m.parse_error is not None:
            # Surface the parse failure as a non-fatal wiring note so the caller
            # (PostToolUse) can report it; it is not a dead-code finding.
            wiring_items.append(
                {
                    "symbol": None,
                    "qualname": None,
                    "kind": "parse-error",
                    "file": m.path,
                    "line": 0,
                    "reachable": None,
                    "entry_point": False,
                    "reason": m.parse_error,
                }
            )
            continue

        # Test-file definitions are out of the wiring obligation entirely:
        # no dead-code reporting, no WIRING obligation row.
        if m.is_test:
            continue

        for d in m.defs.values():
            is_entry = d.qualname in m.entry_qualnames
            # "reached" iff: seeded entry point, OR a decorator-routed handler
            # (Semgrep's domain — never reported dead by THIS tool), OR its bare
            # name appears anywhere in the repo-wide reference pool, OR it is
            # the name of some seeded entry point.
            reached = (
                is_entry
                or d.decorated
                or d.name in repo_referenced
                or d.name in repo_entry_names
            )

            if reached:
                wiring_items.append(
                    {
                        "symbol": d.name,
                        "qualname": d.qualname,
                        "kind": d.kind,
                        "file": d.path,
                        "line": d.lineno,
                        "reachable": True,
                        "entry_point": is_entry or d.decorated,
                        "reason": "reachable from a real execution path",
                    }
                )
            else:
                reason = (
                    f"{d.kind} '{d.qualname}' is defined but never referenced "
                    f"from any real execution path in the analyzed set"
                )
                finding = {
                    "symbol": d.name,
                    "qualname": d.qualname,
                    "kind": d.kind,
                    "file": d.path,
                    "line": d.lineno,
                    "reason": reason,
                }
                dead_code.append(finding)
                wiring_items.append(
                    {
                        "symbol": d.name,
                        "qualname": d.qualname,
                        "kind": d.kind,
                        "file": d.path,
                        "line": d.lineno,
                        "reachable": False,
                        "entry_point": False,
                        "reason": reason,
                    }
                )

    return {"wiring_items": wiring_items, "dead_code": dead_code}


# ---------------------------------------------------------------------------
# Projection into feature_list.json WIRING CoverageItems
# ---------------------------------------------------------------------------

def emit_wiring_items(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Project an ``analyze(...)`` result into feature_list WIRING items.

    Each emitted item is a ``type="WIRING"``, ``status="unproven"`` CoverageItem
    candidate (task 19.3 / Property 1): non-empty ``id``, ``type``, ``priority``,
    ``dependencies``, ``acceptance_criteria`` (≥1), ``status``, ``in_scope``.
    The Verifier consumes these and either proves them with an integration-test
    Evidence_Record (Req 8.3) or transitions an unreachable-symbol item
    ``unproven -> failed`` (Req 8.2 / REQ-EXEC-011).

    One WIRING item is emitted per analyzed defined NON-test symbol (every
    ``wiring_items`` obligation from ``analyze``; parse-error notes are skipped
    here — they carry no symbol to wire). The id is minted in the
    ``REQ-WIRE-NNN`` namespace, stable within a single analysis by ordinal.

    Parameters
    ----------
    analysis:
        The dict returned by :func:`analyze`.

    Returns
    -------
    list[dict]
        feature_list.json-shaped WIRING CoverageItem candidates.
    """
    obligations = [
        w
        for w in analysis.get("wiring_items", [])
        if w.get("symbol") and w.get("kind") != "parse-error"
    ]

    items: List[Dict[str, Any]] = []
    for ordinal, w in enumerate(obligations, start=1):
        symbol = w["symbol"]
        qualname = w.get("qualname") or symbol
        file_path = w.get("file") or "<unknown>"
        reachable = w.get("reachable")
        item_id = f"{WIRING_REQ_PREFIX}-{ordinal:03d}"

        acceptance = [
            (
                f"Symbol '{qualname}' in {file_path} is reachable from a real "
                f"execution path and exercised by an integration test "
                f"(evidence_kind == 'integration')."
            )
        ]

        items.append(
            {
                "id": item_id,
                "type": "WIRING",
                "priority": 1,
                "dependencies": [],
                "acceptance_criteria": acceptance,
                "status": "unproven",
                "in_scope": True,
                "title": f"Wire '{qualname}' into a real execution path",
                "ears_statement": (
                    f"WHILE the system is running, THE platform SHALL reach "
                    f"'{qualname}' (defined in {file_path}) from a real "
                    f"execution path proven by an integration test."
                ),
                "wiring": {
                    "symbol": symbol,
                    "qualname": qualname,
                    "file": file_path,
                    "line": w.get("line", 0),
                    "reachable": reachable,
                    "source": "wiring_checker.py",
                },
            }
        )

    return items


# ---------------------------------------------------------------------------
# CLI entry point (task 19.1: one file path per positional arg; exit 0 always)
# ---------------------------------------------------------------------------

def _main(argv: List[str]) -> int:
    """CLI: ``wiring_checker.py <file> [<file> ...]`` -> JSON on stdout, exit 0.

    Findings never set a non-zero exit — blocking is the PostToolUse hook's job
    (task 19.1: "Exit 0 even when findings exist"). The combined object carries
    both the raw analysis and the emitted WIRING candidates.
    """
    import json

    paths = list(argv)
    result = analyze(paths)
    payload = {
        "wiring_items": result["wiring_items"],
        "dead_code": result["dead_code"],
        "wiring_candidates": emit_wiring_items(result),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))

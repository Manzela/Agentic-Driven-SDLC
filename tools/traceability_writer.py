"""traceability_writer.py — commit-trailer parser + req→code→test link builder.

Spec: .kiro/specs/spec-to-evidence-control/tasks.md, task 29.1 (Phase 2,
      integration-tested by task 33.1)
Requirements: REQ-TRACE-001..003 (Requirement 6.1 / 6.2 / 6.3)
Property: Property 10 — Commit Trailer Requirement ID

This module owns the COMMIT-HAS-REQ-ID gate (REQ-6.2 / Property 10) and builds
the requirement → code → test rows of the durable ``traceability_links`` graph
(REQ-6.1). Orphan detection (REQ-6.3 / Property 11) is owned separately by
``tools/orphan_detector.py``; both modules import the SAME requirement-ID regex
from ``tools/req_id_scan.py`` so the pattern can never drift between them.

The three public functions:

* ``parse_commit_trailers(message: str) -> list[str]``
      Extract every requirement ID (``[A-Z]+-[A-Z]+-[0-9]{3}``) referenced in a
      commit message. Returns ``[]`` when none are present.

* ``assert_commit_has_req_id(message: str) -> bool``
      The REQ-6.2 / Property 10 gate. Returns ``True`` when the message carries
      at least one requirement ID; raises ``TraceabilityError`` otherwise. Its
      caller is the merge-time commit-trailer CI gate (tasks.md task 40.x): a
      raised ``TraceabilityError`` becomes a non-zero exit that blocks the PR.

* ``build_links(commits, tests) -> list[dict]``
      Produce the ``traceability_links`` rows that wire each requirement to the
      commit that implemented it and the test that exercises it — the
      req → code → test leg of the bidirectional coverage graph (REQ-6.1). Each
      row is ``{requirement_id, commit_sha, test_file}``.

PURE STDLIB. The only third-party-free import is the sibling ``req_id_scan``
helper (also stdlib-only). No database, git, or network calls live in these
three functions: ``parse_commit_trailers`` operates on a message STRING passed
in by the caller, so the parser is deterministic and unit-testable without a
repo. (The DB-insert side — ``write_traceability_link`` against the
``traceability_links`` Postgres table — is the Phase-2 persistence concern and
is intentionally kept out of this pure-parsing core.)
"""

from __future__ import annotations

from typing import Dict, List

# Shared requirement-ID regex — single source of truth, imported (not
# re-declared) so traceability_writer and orphan_detector cannot drift apart.
# Import is tolerant of being run both as part of the ``tools`` package and as a
# bare module on sys.path (the hooks/CI invoke tools by file path).
try:  # pragma: no cover - import-shape shim
    from tools.req_id_scan import scan_req_ids
except ImportError:  # pragma: no cover - import-shape shim
    from req_id_scan import scan_req_ids

__all__ = [
    "TraceabilityError",
    "parse_commit_trailers",
    "assert_commit_has_req_id",
    "build_links",
]


class TraceabilityError(Exception):
    """Raised when a traceability invariant is violated.

    Specifically: a commit message that carries no requirement ID in its trailer
    fails the REQ-6.2 / Property 10 gate and raises this. The merge-time
    commit-trailer CI check (tasks.md task 40.x) translates the raised exception
    into a non-zero exit, blocking the offending commit / PR.
    """


def parse_commit_trailers(message: str) -> List[str]:
    """Extract referenced requirement IDs from a commit message.

    A "commit trailer" here is the conventional ``Key: value`` block at the foot
    of a commit message (the implementer stamps the requirement ID there, e.g.
    ``Requirement: REQ-TRACE-001``). In practice an ID can also appear in the
    subject or body; this parser scans the WHOLE message so a reference anywhere
    in the commit satisfies REQ-6.2, then de-duplicates.

    Parameters
    ----------
    message:
        The full commit message text (e.g. ``git log --format=%B -n1 <sha>``).
        ``None`` / empty is accepted and yields ``[]``.

    Returns
    -------
    list[str]
        Each distinct requirement ID matching ``[A-Z]+-[A-Z]+-[0-9]{3}``, in
        first-seen order, with duplicates removed. Empty when the message
        references no requirement (the condition that fails Property 10).
    """
    return scan_req_ids(message)


def assert_commit_has_req_id(message: str) -> bool:
    """Assert that a commit message references at least one requirement ID.

    This is the REQ-6.2 / Property 10 commit-trailer gate: *for any* commit
    created by the implementer subagent, the message MUST contain at least one
    requirement ID matching ``[A-Z]+-[A-Z]+-[0-9]{3}``; commits without one are
    rejected.

    Parameters
    ----------
    message:
        The full commit message text.

    Returns
    -------
    bool
        ``True`` when at least one requirement ID is present.

    Raises
    ------
    TraceabilityError
        When the message references no requirement ID. The caller (the
        merge-time commit-trailer CI check) surfaces this as a non-zero exit,
        blocking the commit / PR.
    """
    req_ids = parse_commit_trailers(message)
    if not req_ids:
        raise TraceabilityError(
            "Commit message has no requirement ID in its trailer "
            "(expected at least one id matching [A-Z]+-[A-Z]+-[0-9]{3}, "
            "e.g. 'Requirement: REQ-TRACE-001'). REQ-6.2 / Property 10."
        )
    return True


def build_links(
    commits: List[Dict], tests: List[Dict]
) -> List[Dict[str, str]]:
    """Build the requirement → commit → test ``traceability_links`` rows.

    This realizes the req → code → test leg of the bidirectional coverage graph
    (REQ-6.1). For every requirement ID referenced by a commit, the commit is
    the *code* link and any test whose own metadata references that same
    requirement ID is the *test* link; the emitted row joins all three.

    Parameters
    ----------
    commits:
        A list of commit dicts. Each is expected to carry:

        * ``sha``      — the commit SHA (also accepted under ``commit_sha``).
        * ``message``  — the commit message (its requirement IDs are parsed via
          ``parse_commit_trailers``). A pre-parsed ``requirement_ids`` /
          ``req_ids`` list is also honored if present, so a caller that already
          extracted IDs need not round-trip through the message.

    tests:
        A list of test dicts. Each is expected to carry:

        * ``test_file``      — the path to the test file (also accepted under
          ``file`` / ``path``).
        * ``requirement_id`` — the single requirement this test exercises, OR
          ``requirement_ids`` / ``req_ids`` (a list) for tests covering several.
          When absent, the test's ``test_file``/``test_name`` text is scanned
          for embedded requirement IDs as a fallback.

    Returns
    -------
    list[dict]
        One ``{requirement_id, commit_sha, test_file}`` row per
        (requirement, commit, test) triple where the test exercises the same
        requirement the commit references. Rows are de-duplicated and returned
        in a deterministic order (sorted by requirement_id, then commit_sha,
        then test_file) so the output is stable across runs — required for the
        content-addressed reproducibility the evidence/audit layers assume.

        A requirement referenced by a commit but with NO matching test still
        yields no row here; that requirement→commit-only state is exactly what
        the orphan detector (REQ-6.3) is responsible for flagging.
    """
    # Map requirement_id -> set of test_files that exercise it.
    tests_by_req: Dict[str, set] = {}
    for test in tests or []:
        if not isinstance(test, dict):
            continue
        test_file = (
            test.get("test_file")
            or test.get("file")
            or test.get("path")
            or ""
        )
        if not test_file:
            continue
        for req_id in _test_req_ids(test):
            tests_by_req.setdefault(req_id, set()).add(test_file)

    rows: set = set()
    for commit in commits or []:
        if not isinstance(commit, dict):
            continue
        commit_sha = commit.get("sha") or commit.get("commit_sha") or ""
        if not commit_sha:
            continue
        for req_id in _commit_req_ids(commit):
            for test_file in tests_by_req.get(req_id, ()):  # no match → skipped
                rows.add((req_id, commit_sha, test_file))

    return [
        {"requirement_id": r, "commit_sha": c, "test_file": t}
        for (r, c, t) in sorted(rows)
    ]


def _commit_req_ids(commit: Dict) -> List[str]:
    """Requirement IDs a commit references, from pre-parsed list or message."""
    explicit = commit.get("requirement_ids") or commit.get("req_ids")
    if isinstance(explicit, (list, tuple)):
        return [r for r in explicit if isinstance(r, str)]
    return parse_commit_trailers(commit.get("message", ""))


def _test_req_ids(test: Dict) -> List[str]:
    """Requirement IDs a test exercises, from explicit fields or a text scan."""
    single = test.get("requirement_id")
    if isinstance(single, str) and single:
        return [single]
    explicit = test.get("requirement_ids") or test.get("req_ids")
    if isinstance(explicit, (list, tuple)):
        return [r for r in explicit if isinstance(r, str)]
    # Fallback: scan the test's own identifiers for an embedded requirement ID.
    blob = " ".join(
        str(test.get(k, "")) for k in ("test_file", "test_name", "file", "path")
    )
    return scan_req_ids(blob)

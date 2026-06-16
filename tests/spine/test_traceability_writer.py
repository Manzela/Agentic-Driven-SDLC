"""Independent verifier test for tools/traceability_writer.py (task 33).

Covers the three public functions against the spec contract
(REQ-TRACE-001..003 / REQ-6.1 / 6.2 / 6.3, Property 10):

* parse_commit_trailers — extracts requirement IDs from a multi-line message,
  including a conventional ``Requirement: REQ-COV-001`` trailer line.
* assert_commit_has_req_id — the commit-has-req-id gate: a no-id message is
  rejected (the "False" case, signalled by raising TraceabilityError); a
  message carrying an id returns True.
* build_links — joins a commit and a test that share a requirement_id into one
  link row carrying all three keys {requirement_id, commit_sha, test_file}.

Written independently of the implementer; imports only the public surface.
"""
import pytest

from tools.traceability_writer import (
    TraceabilityError,
    assert_commit_has_req_id,
    build_links,
    parse_commit_trailers,
)


def test_parse_commit_trailers_extracts_id_from_multiline_trailer():
    message = (
        "feat(trace): wire requirement->code->test graph\n"
        "\n"
        "Implements the durable traceability_links rows so coverage is\n"
        "bidirectional across the req/code/test legs.\n"
        "\n"
        "Requirement: REQ-COV-001\n"
        "Co-Authored-By: Someone <someone@example.com>\n"
    )
    ids = parse_commit_trailers(message)
    assert "REQ-COV-001" in ids


def test_parse_commit_trailers_empty_when_no_id():
    assert parse_commit_trailers("chore: tidy up, no requirement referenced") == []


def test_assert_commit_has_req_id_false_for_message_with_no_id():
    # The "False" case of the gate: a commit with no requirement id is rejected.
    with pytest.raises(TraceabilityError):
        assert_commit_has_req_id("docs: typo fix with no requirement id")


def test_assert_commit_has_req_id_true_otherwise():
    message = "fix: enforce gate\n\nRequirement: REQ-COV-001\n"
    assert assert_commit_has_req_id(message) is True


def test_build_links_joins_commit_and_test_sharing_requirement_id():
    commits = [
        {"sha": "abc1234", "message": "feat: x\n\nRequirement: REQ-COV-001\n"},
    ]
    tests = [
        {"test_file": "tests/spine/test_x.py", "requirement_id": "REQ-COV-001"},
    ]
    links = build_links(commits, tests)

    assert len(links) == 1
    row = links[0]
    # All three keys present in the joined link row.
    assert set(row.keys()) == {"requirement_id", "commit_sha", "test_file"}
    assert row["requirement_id"] == "REQ-COV-001"
    assert row["commit_sha"] == "abc1234"
    assert row["test_file"] == "tests/spine/test_x.py"


def test_build_links_no_row_when_requirement_ids_differ():
    # A commit and a test that do NOT share a requirement id must not be joined.
    commits = [{"sha": "deadbee", "message": "feat\n\nRequirement: REQ-COV-001\n"}]
    tests = [{"test_file": "tests/test_y.py", "requirement_id": "REQ-TRACE-002"}]
    assert build_links(commits, tests) == []

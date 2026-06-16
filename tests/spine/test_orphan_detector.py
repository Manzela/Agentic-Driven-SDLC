"""Independent verifier tests for tools/orphan_detector.py (S-orphan_detector).

Asserts the bidirectional spec-to-evidence orphan contract (REQ-6.3 /
Property 11), written independently of the implementer:

  - an impl unit with NO requirement_id        -> forward_orphan
  - a requirement referenced by no impl unit    -> backward_orphan
  - ok == False when orphans exist (either direction)
  - ok == True  when every edge is mapped (fully traced, both directions)
  - scan_commit_trailers extracts "REQ-GATE-002" from a trailer line
"""
from tools.orphan_detector import detect_orphans, scan_commit_trailers


# --------------------------------------------------------------------------- #
# forward orphan: impl unit without a requirement_id
# --------------------------------------------------------------------------- #
def test_impl_unit_without_requirement_id_is_forward_orphan():
    impl_units = [
        {"ref": "tools/widget.py::do_thing"},  # no requirement ref at all
    ]
    requirements = []
    report = detect_orphans(impl_units, requirements)

    assert "tools/widget.py::do_thing" in report["forward_orphans"]
    assert report["backward_orphans"] == []
    assert report["ok"] is False


# --------------------------------------------------------------------------- #
# backward orphan: a requirement referenced by no impl unit
# --------------------------------------------------------------------------- #
def test_requirement_referenced_by_no_impl_is_backward_orphan():
    # An impl unit that references REQ-CORE-001 only — so REQ-CORE-999 is
    # declared but nothing proves it.
    impl_units = [
        {"ref": "tools/core.py::run", "requirement_id": "REQ-CORE-001"},
    ]
    requirements = [
        {"id": "REQ-CORE-001"},  # mapped (referenced by the impl unit above)
        {"id": "REQ-CORE-999"},  # orphan: no impl unit / no evidence
    ]
    report = detect_orphans(impl_units, requirements)

    assert "REQ-CORE-999" in report["backward_orphans"]
    assert "REQ-CORE-001" not in report["backward_orphans"]
    assert report["forward_orphans"] == []
    assert report["ok"] is False


# --------------------------------------------------------------------------- #
# ok == False when orphans exist (both directions populated)
# --------------------------------------------------------------------------- #
def test_ok_false_when_orphans_exist_both_directions():
    impl_units = [
        {"ref": "tools/orphaned_impl.py"},  # forward orphan (no req ref)
    ]
    requirements = [
        {"id": "REQ-LONELY-001"},  # backward orphan (no impl, no evidence)
    ]
    report = detect_orphans(impl_units, requirements)

    assert report["forward_orphans"] != []
    assert report["backward_orphans"] != []
    assert report["ok"] is False


# --------------------------------------------------------------------------- #
# ok == True when every edge is mapped (fully traced in both directions)
# --------------------------------------------------------------------------- #
def test_ok_true_when_fully_mapped():
    impl_units = [
        {"ref": "tools/a.py::fn", "requirement_id": "REQ-ALPHA-001"},
        {"ref": "tools/b.py::fn", "requirement_id": "REQ-BETA-002"},
    ]
    requirements = [
        {"id": "REQ-ALPHA-001"},  # referenced by tools/a.py::fn
        {"id": "REQ-BETA-002"},   # referenced by tools/b.py::fn
    ]
    report = detect_orphans(impl_units, requirements)

    assert report["forward_orphans"] == []
    assert report["backward_orphans"] == []
    assert report["ok"] is True


# --------------------------------------------------------------------------- #
# scan_commit_trailers extracts REQ-GATE-002 from a trailer line
# --------------------------------------------------------------------------- #
def test_scan_commit_trailers_extracts_req_gate_002():
    trailer = "Requirement: REQ-GATE-002"
    ids = scan_commit_trailers(trailer)
    assert "REQ-GATE-002" in ids


def test_scan_commit_trailers_extracts_from_full_commit_message():
    message = (
        "feat(gate): enforce coverage threshold\n"
        "\n"
        "Implements the deterministic coverage gate.\n"
        "\n"
        "Requirement: REQ-GATE-002\n"
    )
    ids = scan_commit_trailers(message)
    assert ids == ["REQ-GATE-002"]


def test_scan_commit_trailers_empty_when_no_trailer():
    assert scan_commit_trailers("chore: tidy up, no requirement here") == []

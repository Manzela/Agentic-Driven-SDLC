"""Independent verifier test for sandbox_guard (REQ-17.4 / task 46, plane REQ-SEC).

Verifies the two host-side isolation predicates exposed by tools/sandbox_guard.py:

  * egress_allowed   — network egress is DENIED by default; only allowlisted
                       hosts may be reached.
  * check_worktree_confinement — filesystem writes are confined to the per-slice
                       worktree root; traversal / absolute-outside paths blocked.

Written independently of the implementer's own tests.
"""
import os

import pytest

from tools.sandbox_guard import check_worktree_confinement, egress_allowed


# --------------------------------------------------------------------------- #
# egress_allowed: default-deny network admission
# --------------------------------------------------------------------------- #


def test_egress_allowed_for_allowlisted_host():
    # An allowlisted host is admitted.
    assert egress_allowed("https://api.trusted.example/v1", ["api.trusted.example"]) is True


def test_egress_denied_for_non_allowlisted_host():
    # A host that is NOT on the allowlist is denied.
    assert egress_allowed("https://evil.test/steal", ["api.trusted.example"]) is False


def test_egress_denied_for_empty_allowlist_default_deny():
    # An empty allowlist means NO exceptions → every host is denied (default-deny).
    assert egress_allowed("https://api.trusted.example/v1", []) is False


# --------------------------------------------------------------------------- #
# check_worktree_confinement: writes confined to the worktree root
# --------------------------------------------------------------------------- #


def test_confinement_true_inside_allowed_root(tmp_path):
    root = str(tmp_path)
    inside = os.path.join(root, "slice-7", "src", "main.py")
    assert check_worktree_confinement(inside, root) is True


def test_confinement_false_for_relative_escape(tmp_path):
    # '../escape' resolves outside the allowed root → blocked.
    root = os.path.join(str(tmp_path), "wt")
    os.makedirs(root, exist_ok=True)
    escape = os.path.join(root, "..", "escape")
    assert check_worktree_confinement(escape, root) is False


def test_confinement_false_for_absolute_outside_path(tmp_path):
    # An absolute path that does not sit under the root → blocked.
    root = str(tmp_path)
    assert check_worktree_confinement("/etc/passwd", root) is False


def test_confinement_false_for_traversal_sequence(tmp_path):
    # A deep '../../..' traversal sequence that climbs out of the root → blocked.
    root = os.path.join(str(tmp_path), "a", "b", "c")
    os.makedirs(root, exist_ok=True)
    traversal = os.path.join(root, "..", "..", "..", "..", "etc", "passwd")
    assert check_worktree_confinement(traversal, root) is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

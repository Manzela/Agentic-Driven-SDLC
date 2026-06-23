"""The freeze fingerprint is stable across proven-flips, sensitive to model drift."""
import copy
from tools.model_fingerprint import fingerprint

BASE = {"items": [
    {"id": "A-B-001", "type": "functional", "priority": 1, "dependencies": [],
     "acceptance_criteria": ["x"], "in_scope": True, "status": "unproven"},
    {"id": "A-B-002", "type": "functional", "priority": 2, "dependencies": [],
     "acceptance_criteria": ["y"], "in_scope": True, "status": "unproven"},
]}


def test_proven_flip_does_not_change_fingerprint():
    after = copy.deepcopy(BASE)
    after["items"][0]["status"] = "proven"
    after["items"][0]["evidence"] = {"test_file": "t", "test_name": "n",
                                     "output_hash": "sha256:" + "a" * 64,
                                     "collected_at": "2026-06-16T00:00:00+00:00"}
    assert fingerprint(BASE) == fingerprint(after)


def test_adding_item_changes_fingerprint():
    after = copy.deepcopy(BASE)
    after["items"].append({"id": "A-B-003", "type": "functional", "priority": 3,
                           "dependencies": [], "acceptance_criteria": ["z"], "in_scope": True, "status": "unproven"})
    assert fingerprint(BASE) != fingerprint(after)


def test_scope_change_changes_fingerprint():
    after = copy.deepcopy(BASE)
    after["items"][0]["in_scope"] = False
    assert fingerprint(BASE) != fingerprint(after)


def test_order_independent():
    shuffled = {"items": list(reversed(BASE["items"]))}
    assert fingerprint(BASE) == fingerprint(shuffled)

"""Independent verifier tests for tools/spec_validator.py (S7-specvalidator).

Asserts the non-LLM EARS structural validator contract:
  - a clean well-formed spec      -> violation_count == 0
  - a requirement with no ears_pattern -> ambiguity (count goes up)
  - text "must be fast and secure"     -> ambiguity (vague adjectives)
  - an unreferenced baseline_item      -> uncovered
  - duplicate id, conflicting outcome  -> contradiction
  - the returned dict carries all four contract keys
"""
from tools.spec_validator import validate_spec


def _clean_spec():
    """A well-formed spec where every baseline item is covered and no
    requirement is ambiguous or contradictory."""
    requirements = [
        {
            "id": "REQ-1",
            "ears_pattern": "ubiquitous",
            "outcome": "ok",
            "covers": ["BL-1"],
            "text": "The system shall record the actor identity from the runtime.",
        },
        {
            "id": "REQ-2",
            "ears_pattern": "event-driven",
            "outcome": "ok",
            "covers": ["BL-2"],
            "text": "When a tool call completes the system shall append an evidence row.",
        },
    ]
    baseline_items = ["BL-1", "BL-2"]
    return requirements, baseline_items


def test_clean_spec_has_zero_violations():
    requirements, baseline_items = _clean_spec()
    result = validate_spec(requirements, baseline_items)
    assert result["violation_count"] == 0
    assert result["contradictions"] == []
    assert result["ambiguities"] == []
    assert result["uncovered"] == []


def test_missing_ears_pattern_is_ambiguity():
    # Same spec as clean, but strip the ears_pattern off the first requirement.
    requirements, baseline_items = _clean_spec()
    requirements[0].pop("ears_pattern")
    result = validate_spec(requirements, baseline_items)

    assert result["violation_count"] >= 1
    kinds = [a.get("kind") for a in result["ambiguities"]]
    assert "ears_pattern" in kinds
    # the offending requirement is flagged for the missing tag
    flagged = [a for a in result["ambiguities"] if a.get("kind") == "ears_pattern"]
    assert any(a.get("id") == "REQ-1" for a in flagged)


def test_missing_ears_pattern_increases_count_versus_clean():
    clean_reqs, baseline = _clean_spec()
    clean_count = validate_spec(clean_reqs, baseline)["violation_count"]

    dirty_reqs, _ = _clean_spec()
    dirty_reqs[0].pop("ears_pattern")
    dirty_count = validate_spec(dirty_reqs, baseline)["violation_count"]

    assert dirty_count > clean_count


def test_fast_and_secure_text_is_ambiguity():
    requirements = [
        {
            "id": "REQ-PERF",
            "ears_pattern": "ubiquitous",
            "outcome": "ok",
            "text": "The system must be fast and secure.",
        },
    ]
    result = validate_spec(requirements, baseline_items=[])

    vague = [a for a in result["ambiguities"] if a.get("kind") == "vague_adjective"]
    assert len(vague) >= 1
    adjectives = set()
    for a in vague:
        adjectives.update(a.get("adjectives", []))
    assert "fast" in adjectives
    assert "secure" in adjectives
    assert result["violation_count"] >= 1


def test_unreferenced_baseline_item_is_uncovered():
    requirements = [
        {
            "id": "REQ-1",
            "ears_pattern": "ubiquitous",
            "outcome": "ok",
            "covers": ["BL-1"],
            "text": "The system shall do the covered thing.",
        },
    ]
    # BL-2 is never referenced by any covers[] -> uncovered
    baseline_items = ["BL-1", "BL-2"]
    result = validate_spec(requirements, baseline_items)

    uncovered_ids = [u.get("baseline_item") for u in result["uncovered"]]
    assert "BL-2" in uncovered_ids
    assert "BL-1" not in uncovered_ids
    assert result["violation_count"] >= 1


def test_duplicate_id_conflicting_outcome_is_contradiction():
    requirements = [
        {
            "id": "REQ-DUP",
            "ears_pattern": "ubiquitous",
            "outcome": "accept",
            "text": "The system shall accept the request.",
        },
        {
            "id": "REQ-DUP",
            "ears_pattern": "ubiquitous",
            "outcome": "reject",
            "text": "The system shall accept the request.",
        },
    ]
    result = validate_spec(requirements, baseline_items=[])

    assert len(result["contradictions"]) >= 1
    conflict = result["contradictions"][0]
    assert conflict.get("id") == "REQ-DUP"
    assert result["violation_count"] >= 1


def test_return_dict_has_all_four_keys():
    requirements, baseline_items = _clean_spec()
    result = validate_spec(requirements, baseline_items)
    assert isinstance(result, dict)
    for key in ("contradictions", "ambiguities", "uncovered", "violation_count"):
        assert key in result
    assert isinstance(result["contradictions"], list)
    assert isinstance(result["ambiguities"], list)
    assert isinstance(result["uncovered"], list)
    assert isinstance(result["violation_count"], int)

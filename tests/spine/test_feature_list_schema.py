"""Independent verifier test for S1-schema (REQ-COV-001/003/006).

Loads schema/feature_list.schema.json with jsonschema and asserts a
hand-written valid feature_list passes plus five rejection cases. This test
was written by an independent verifier and does NOT trust the implementer.
"""

import copy
import json
import os

import pytest
from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError

# schema/feature_list.schema.json lives two levels up from this test file:
# <repo>/tests/spine/test_feature_list_schema.py -> <repo>/schema/...
REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
)
SCHEMA_PATH = os.path.join(REPO_ROOT, "schema", "feature_list.schema.json")


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def validator():
    schema = load_schema()
    # check_schema raises if the schema document itself is malformed.
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema)


def valid_item():
    """A hand-written CoverageItem that satisfies every required field."""
    return {
        "id": "REQ-COV-001",
        "type": "functional",
        "priority": 1,
        "dependencies": [],
        "acceptance_criteria": ["The feature list validates against the schema."],
        "status": "proven",
        "in_scope": True,
        "evidence": {
            "test_file": "tests/spine/test_feature_list_schema.py",
            "test_name": "test_valid_feature_list_passes",
            "output_hash": "sha256:"
            + "a" * 64,
            "collected_at": "2026-06-15T12:00:00Z",
            "actor_agent": "verifier.md",
            "evidence_kind": "unit",
        },
    }


def valid_feature_list():
    """A hand-written, fully valid FeatureList document."""
    return {
        "schema_version": "1.0.0",
        "product_class": "agentic-sdlc-control-plane",
        "checklist_ref": {
            "path": "checklists/agentic-sdlc.md",
            "version": "1.0.0",
            "sha": "deadbeef",
        },
        "items": [valid_item()],
    }


def is_valid(validator, doc):
    return validator.is_valid(doc)


def first_error(validator, doc):
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    return errors[0] if errors else None


# (1) A hand-written VALID feature_list passes.
def test_valid_feature_list_passes(validator):
    doc = valid_feature_list()
    # Should produce zero validation errors.
    errors = list(validator.iter_errors(doc))
    assert errors == [], f"expected valid doc, got errors: {[e.message for e in errors]}"
    assert is_valid(validator, doc)


# (2) An item missing output_hash inside its evidence is REJECTED.
def test_evidence_missing_output_hash_is_rejected(validator):
    doc = valid_feature_list()
    del doc["items"][0]["evidence"]["output_hash"]
    assert not is_valid(validator, doc), (
        "evidence without output_hash must be rejected"
    )
    err = first_error(validator, doc)
    assert err is not None
    assert "output_hash" in err.message


# (3) An item with status='proven' and NO evidence object is REJECTED
#     (the allOf if/then conditional).
def test_proven_without_evidence_is_rejected(validator):
    doc = valid_feature_list()
    item = doc["items"][0]
    item["status"] = "proven"
    item.pop("evidence", None)
    assert "evidence" not in item
    assert not is_valid(validator, doc), (
        "status=proven with no evidence object must be rejected by the conditional"
    )
    # Sanity-check the same item with status=unproven (and no evidence) is fine,
    # proving it is the conditional - not some other field - doing the rejecting.
    ok_doc = valid_feature_list()
    ok_item = ok_doc["items"][0]
    ok_item["status"] = "unproven"
    ok_item.pop("evidence", None)
    assert is_valid(validator, ok_doc), (
        "status=unproven with no evidence should be valid; "
        "if this fails the rejection above is not isolated to the conditional"
    )


# (4) An item with an empty-string test_file is REJECTED (minLength).
def test_empty_test_file_is_rejected(validator):
    doc = valid_feature_list()
    doc["items"][0]["evidence"]["test_file"] = ""
    assert not is_valid(validator, doc), "empty-string test_file must be rejected"
    # Confirm minLength is the responsible keyword.
    errors = list(validator.iter_errors(doc))
    assert any(
        e.validator == "minLength" and "test_file" in list(e.absolute_path)
        for e in errors
    ), f"expected a minLength failure on test_file, got: {[(e.validator, list(e.absolute_path)) for e in errors]}"


# (5) An item with type='bogus' is REJECTED (enum).
def test_bogus_type_is_rejected(validator):
    doc = valid_feature_list()
    doc["items"][0]["type"] = "bogus"
    assert not is_valid(validator, doc), "type='bogus' must be rejected"
    errors = list(validator.iter_errors(doc))
    assert any(
        e.validator == "enum" and "type" in list(e.absolute_path) for e in errors
    ), f"expected an enum failure on type, got: {[(e.validator, list(e.absolute_path)) for e in errors]}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

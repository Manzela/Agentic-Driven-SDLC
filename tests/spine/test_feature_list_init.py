"""Independent verifier test for S9-flinit (REQ-COV-001 / task 12).

This test was written by an INDEPENDENT VERIFIER. It does NOT trust the
implementer's own assertions. It loads schema/feature_list.schema.json directly
with jsonschema (Draft7Validator) and checks the behaviour the slice promises:

1. init with a sample functional item yields a dict whose single item validates
   against schema/feature_list.schema.json;
2. status defaults to "unproven" for an item that did not supply one;
3. empty init yields an items list equal to [] (``{"items": []}``);
4. an item written to disk (via write_feature_list) and re-validated still
   passes the schema.

The verifier supplies its OWN sample input and its OWN schema validation; it
only calls the public API surface of tools/feature_list_init.py.
"""

import json
import os
import sys

import pytest
from jsonschema import Draft7Validator

# <repo>/tests/spine/test_feature_list_init.py -> <repo> is two levels up.
REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
)
SCHEMA_PATH = os.path.join(REPO_ROOT, "schema", "feature_list.schema.json")

# Import the implementation under test from tools/.
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))
import feature_list_init  # noqa: E402


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def validator():
    schema = load_schema()
    # Fail loudly if the schema document itself is malformed.
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema)


def sample_functional_item():
    """A minimal raw functional coverage item the verifier hands to the init.

    It deliberately OMITS status / in_scope / dependencies / acceptance? — no:
    acceptance_criteria must be supplied because the schema requires minItems:1
    and the initializer (correctly) does NOT fabricate criteria. status and
    in_scope are omitted so we can assert the initializer defaults them.
    """
    return {
        "id": "REQ-FUN-001",
        "type": "functional",
        "priority": 1,
        "acceptance_criteria": ["The initializer seeds a schema-valid envelope."],
        "title": "Sample functional requirement",
    }


# (1) init with a sample functional item yields a dict whose single item
#     validates against the schema.
def test_init_with_functional_item_validates(validator):
    result = feature_list_init.init_feature_list([sample_functional_item()])

    assert isinstance(result, dict)
    assert isinstance(result["items"], list)
    assert len(result["items"]) == 1, "exactly one item expected"

    # The whole document must validate against the file schema.
    errors = sorted(validator.iter_errors(result), key=lambda e: list(e.path))
    assert errors == [], (
        "expected init document to validate, got: "
        + repr([e.message for e in errors])
    )

    # And the single item itself, checked against the CoverageItem subschema,
    # must validate independently (no envelope masking an item defect).
    schema = load_schema()
    item_schema = dict(schema["definitions"]["CoverageItem"])
    item_schema["definitions"] = schema["definitions"]
    Draft7Validator.check_schema(item_schema)
    item_validator = Draft7Validator(item_schema)
    item_errors = list(item_validator.iter_errors(result["items"][0]))
    assert item_errors == [], (
        "single coverage item failed CoverageItem schema: "
        + repr([e.message for e in item_errors])
    )


# (2) status defaults to "unproven" when the input omits it.
def test_status_defaults_to_unproven():
    result = feature_list_init.init_feature_list([sample_functional_item()])
    item = result["items"][0]
    assert item["status"] == "unproven", (
        "an item without an explicit status must default to 'unproven'"
    )
    # And an explicitly supplied status must be preserved, not clobbered.
    raw = sample_functional_item()
    raw["status"] = "failed"
    kept = feature_list_init.init_feature_list([raw])["items"][0]
    assert kept["status"] == "failed", "an explicit status must be preserved"


# (3) empty init yields {"items": []}.
def test_empty_init_yields_empty_items(validator):
    empty = feature_list_init.init_feature_list()
    assert empty["items"] == [], "empty init must yield an empty items list"

    # The empty envelope must itself be schema-valid (all four top-level
    # required fields present).
    errors = list(validator.iter_errors(empty))
    assert errors == [], (
        "empty init document must validate against the schema, got: "
        + repr([e.message for e in errors])
    )

    # items=None and items=[] behave identically for the items list.
    assert feature_list_init.init_feature_list(None)["items"] == []
    assert feature_list_init.init_feature_list([])["items"] == []


# (4) an item written to disk then re-validated passes.
def test_written_item_revalidates(tmp_path, validator):
    result = feature_list_init.init_feature_list([sample_functional_item()])

    out_path = os.path.join(str(tmp_path), "feature_list.json")
    written = feature_list_init.write_feature_list(result, out_path)
    assert os.path.isfile(written), "write_feature_list must create the file"

    with open(written, "r", encoding="utf-8") as fh:
        reloaded = json.load(fh)

    # Re-validate the document as it was persisted (round-trip through disk).
    errors = list(validator.iter_errors(reloaded))
    assert errors == [], (
        "written-then-reloaded document must still validate, got: "
        + repr([e.message for e in errors])
    )
    assert reloaded["items"][0]["status"] == "unproven"
    assert reloaded == result, "round-trip must preserve the document exactly"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

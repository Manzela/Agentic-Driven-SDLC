"""The materialized coverage model is 209 items, schema-valid, all unproven."""
import json
import re
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ID_PAT = re.compile(r"^[A-Z]+-[A-Z]+-[0-9]{3}$")


def _model():
    from tools.materialize_feature_list import materialize
    return materialize(ROOT / "docs/website/autonomous-agent.dev/requirements.md")


def test_count_is_209():
    assert len(_model()["items"]) == 209  # 205 spec + 4 Bucket-A/SCA


def test_all_unproven_and_canonical_ids():
    for i in _model()["items"]:
        assert i["status"] == "unproven"
        assert ID_PAT.match(i["id"]), i["id"]
        assert isinstance(i["priority"], int) and i["priority"] >= 1
        assert i["acceptance_criteria"]


def test_nfr_items_carry_subtype():
    for i in _model()["items"]:
        if i["type"] == "NFR":
            assert i.get("nfr_subtype") in ("performance", "accessibility", "reliability", "security")


def test_schema_validates():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schema/feature_list.schema.json").read_text())
    jsonschema.validate(_model(), schema)


def test_traceability_preserved():
    ids = {i["source_ears_id"] for i in _model()["items"]}
    # representative spec IDs survive as source_ears_id
    for sid in ("DS-01", "HOME-01", "A11Y-16", "PERF-17", "PRIV-15"):
        assert sid in ids, sid

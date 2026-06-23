"""Task 7: PreToolUse insertion-permit + deletion (T10) + MultiEdit (T12) + in_scope:false (T11).

The gate must distinguish a new-id INSERTION (a born item) from an existing-id MUTATION
and from a DELETION, and apply:
  R1.1  new item born status:unproven from initializer/implementer/main -> allow
  R1.2  new item born status:proven from any non-verifier            -> block (T9)
  R2.1  new item born in_scope:true (or absent default)              -> allow
  R2.2  new item born in_scope:false from non-human                  -> block (T11)
  R1    existing-id status change from non-verifier                  -> block (unchanged)
  R2    existing-id in_scope change without human_signed             -> block (unchanged)
  R4    non-verifier deletion of an in-scope OR unproven item        -> block (T10)
  MultiEdit.edits[] is parsed for status/in_scope value flips (T12).

The test loads the hook module directly (evaluate is a pure core) and also exercises the
real stdin subprocess shell (exit 0 = allow, exit 2 = block).
"""

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude/hooks/pre_tool_use_hook.py"

_spec = importlib.util.spec_from_file_location("pre_tool_use_hook", HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def _ev(actor, *, tool="Edit", old=None, new=None, content=None, edits=None,
        path="feature_list.json", human_signed=False):
    ti = {"file_path": path}
    if old is not None or new is not None:
        ti["old_string"] = old or ""
        ti["new_string"] = new or ""
    if content is not None:
        ti["content"] = content
    if edits is not None:
        ti["edits"] = edits
    return hook.evaluate(tool_name=tool, tool_input=ti, resolved_actor=actor,
                         human_signed=human_signed)


def _run(event, env=None):
    e = {**os.environ, **(env or {})}
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event),
                       capture_output=True, text=True, env=e, cwd=str(ROOT))
    return p.returncode, p.stdout, p.stderr


_EMPTY = '{"items":[]}'


def _doc(id_, status="unproven", in_scope=True):
    sc = "true" if in_scope else "false"
    return f'{{"items":[{{"id":"{id_}","status":"{status}","in_scope":{sc}}}]}}'


# --- INSERTION: new-id births (R1.1 / R1.2 / R2.1 / R2.2) ---------------------
def test_new_unproven_birth_by_initializer_allows():
    assert _ev("initializer", old=_EMPTY, new=_doc("F-999"))["decision"] == "allow"


def test_new_unproven_birth_by_implementer_allows():
    assert _ev("implementer", old=_EMPTY, new=_doc("F-999"))["decision"] == "allow"


def test_new_proven_birth_by_implementer_blocks():
    out = _ev("implementer", old=_EMPTY, new=_doc("F-999", status="proven"))
    assert out["decision"] == "block"
    assert "proven" in out["reason"].lower() or "status" in out["reason"].lower()


def test_new_proven_birth_by_verifier_allows():
    assert _ev("verifier", old=_EMPTY, new=_doc("F-999", status="proven"))["decision"] == "allow"


def test_new_in_scope_true_by_initializer_allows():
    assert _ev("initializer", old=_EMPTY, new=_doc("F-999", in_scope=True))["decision"] == "allow"


def test_new_in_scope_absent_defaults_allow():
    new = '{"items":[{"id":"F-999","status":"unproven"}]}'  # no in_scope -> default true
    assert _ev("initializer", old=_EMPTY, new=new)["decision"] == "allow"


def test_new_in_scope_false_by_initializer_blocks():
    out = _ev("initializer", old=_EMPTY, new=_doc("F-999", in_scope=False))
    assert out["decision"] == "block"
    assert "in_scope" in out["reason"].lower()


def test_new_in_scope_false_with_human_signed_allows():
    out = _ev("initializer", old=_EMPTY, new=_doc("F-999", in_scope=False), human_signed=True)
    assert out["decision"] == "allow"


# --- existing-id MUTATION (R1 / R2 unchanged) --------------------------------
def test_existing_status_flip_by_implementer_blocks():
    out = _ev("implementer", old=_doc("F-1"), new=_doc("F-1", status="proven"))
    assert out["decision"] == "block"
    assert "verifier" in out["reason"].lower() or "status" in out["reason"].lower()


def test_existing_status_flip_by_verifier_allows():
    assert _ev("verifier", old=_doc("F-1"), new=_doc("F-1", status="proven"))["decision"] == "allow"


def test_existing_in_scope_flip_without_human_blocks():
    out = _ev("verifier", old=_doc("F-1"), new=_doc("F-1", in_scope=False))
    assert out["decision"] == "block"
    assert "in_scope" in out["reason"].lower() or "human" in out["reason"].lower()


def test_existing_in_scope_flip_with_human_allows():
    out = _ev("verifier", old=_doc("F-1"), new=_doc("F-1", in_scope=False), human_signed=True)
    assert out["decision"] == "allow"


# --- DELETION (R4 / T10) -----------------------------------------------------
def test_delete_in_scope_unproven_by_implementer_blocks():
    out = _ev("implementer", old=_doc("F-1"), new=_EMPTY)
    assert out["decision"] == "block"
    assert "delet" in out["reason"].lower() or "append" in out["reason"].lower()


def test_delete_by_verifier_allows():
    assert _ev("verifier", old=_doc("F-1"), new=_EMPTY)["decision"] == "allow"


def test_delete_out_of_scope_proven_by_implementer_allows():
    # out-of-scope AND not unproven -> not a blockable deletion
    out = _ev("implementer", old=_doc("F-1", status="proven", in_scope=False), new=_EMPTY)
    assert out["decision"] == "allow"


def test_delete_in_scope_proven_by_implementer_blocks():
    out = _ev("implementer", old=_doc("F-1", status="proven", in_scope=True), new=_EMPTY)
    assert out["decision"] == "block"


def test_delete_out_of_scope_unproven_by_implementer_blocks():
    # unproven is blockable even when out of scope (proof still owed)
    out = _ev("implementer", old=_doc("F-1", status="unproven", in_scope=False), new=_EMPTY)
    assert out["decision"] == "block"


# --- MultiEdit (T12): edits[] parsed for status/in_scope value flips ----------
def test_multiedit_status_flip_blocks():
    out = _ev("implementer", tool="MultiEdit",
              edits=[{"old_string": '"status":"unproven"', "new_string": '"status":"proven"'}])
    assert out["decision"] == "block"
    assert "status" in out["reason"].lower() or "verifier" in out["reason"].lower()


def test_multiedit_in_scope_flip_without_human_blocks():
    out = _ev("implementer", tool="MultiEdit",
              edits=[{"old_string": '"in_scope":false', "new_string": '"in_scope":true'}])
    assert out["decision"] == "block"
    assert "in_scope" in out["reason"].lower() or "human" in out["reason"].lower()


def test_multiedit_benign_edit_allows():
    out = _ev("implementer", tool="MultiEdit",
              edits=[{"old_string": '"acceptance_criteria":[]', "new_string": '"acceptance_criteria":["A"]'}])
    assert out["decision"] == "allow"


def test_multiedit_title_edit_near_status_does_not_false_block():
    # 'status' appears in both fragments but its VALUE is unchanged -> benign, must allow.
    out = _ev("implementer", tool="MultiEdit",
              edits=[{"old_string": '"status":"unproven","title":"A"',
                      "new_string": '"status":"unproven","title":"B"'}])
    assert out["decision"] == "allow"


# --- integration: insertion + deletion together ------------------------------
def test_insertion_plus_deletion_blocks():
    out = _ev("implementer", old=_doc("OLD"), new=_doc("NEW"))  # OLD removed, NEW added
    assert out["decision"] == "block"
    assert "delet" in out["reason"].lower() or "append" in out["reason"].lower()


# --- actor matrix ------------------------------------------------------------
@pytest.mark.parametrize("actor,status,in_scope,expect", [
    ("initializer", "unproven", True, "allow"),   # R1.1
    ("initializer", "unproven", False, "block"),  # R2.2
    ("initializer", "proven", True, "block"),     # R1.2
    ("implementer", "unproven", True, "allow"),   # R1.1
    ("implementer", "unproven", False, "block"),  # R2.2
    ("implementer", "proven", True, "block"),     # R1.2
    ("verifier", "unproven", True, "allow"),
    ("verifier", "proven", True, "allow"),        # verifier owns status
    ("main", "unproven", True, "allow"),
    ("main", "proven", True, "block"),            # main holds no flip authority
])
def test_new_item_actor_matrix(actor, status, in_scope, expect):
    out = _ev(actor, old=_EMPTY, new=_doc("F-TEST", status=status, in_scope=in_scope))
    assert out["decision"] == expect, f"{actor}/{status}/in_scope={in_scope}: got {out}"


# --- Write tool (same logic, different payload shape) -------------------------
def test_write_new_unproven_allows(tmp_path):
    fp = tmp_path / "feature_list.json"
    fp.write_text(_EMPTY)
    out = _ev("initializer", tool="Write", content=_doc("F-NEW"), path=str(fp))
    assert out["decision"] == "allow"


def test_write_existing_status_flip_blocks(tmp_path):
    fp = tmp_path / "feature_list.json"
    fp.write_text(_doc("F-1"))
    out = _ev("implementer", tool="Write", content=_doc("F-1", status="proven"), path=str(fp))
    assert out["decision"] == "block"


def test_write_deletion_blocks(tmp_path):
    fp = tmp_path / "feature_list.json"
    fp.write_text(_doc("F-1"))
    out = _ev("implementer", tool="Write", content=_EMPTY, path=str(fp))
    assert out["decision"] == "block"


# --- subprocess layer (exit 0 allow / exit 2 block) --------------------------
def test_subprocess_insertion_unproven_allows():
    rc, _o, _e = _run({"session_id": "s1", "agent_type": "initializer", "tool_name": "Edit",
                       "tool_input": {"file_path": "feature_list.json",
                                      "old_string": _EMPTY, "new_string": _doc("F-NEW")}})
    assert rc == 0


def test_subprocess_in_scope_false_blocks():
    rc, _o, err = _run({"session_id": "s1", "agent_type": "initializer", "tool_name": "Edit",
                        "tool_input": {"file_path": "feature_list.json",
                                       "old_string": _EMPTY, "new_string": _doc("F-NEW", in_scope=False)}})
    assert rc == 2
    assert "in_scope" in err.lower()


def test_subprocess_deletion_blocks():
    rc, _o, err = _run({"session_id": "s1", "agent_type": "implementer", "tool_name": "Edit",
                        "tool_input": {"file_path": "feature_list.json",
                                       "old_string": _doc("F-1"), "new_string": _EMPTY}})
    assert rc == 2
    assert "delet" in err.lower() or "append" in err.lower()


# === Red-team fix-locks (F1-F7) ==============================================
def test_f1_bash_redirect_to_coverage_by_implementer_blocks():
    """F1 (CRITICAL): a Bash redirect into the coverage model bypasses R1/R2/R4 — a
    non-verifier coverage redirect/tee is denied outright (can't be field-diffed)."""
    out = hook.evaluate(tool_name="Bash",
                        tool_input={"command": "echo x > apps/web/feature_list.json"},
                        resolved_actor="implementer", human_signed=False)
    assert out["decision"] == "block"
    out_tee = hook.evaluate(tool_name="Bash",
                            tool_input={"command": "echo x | tee feature_list.json"},
                            resolved_actor="initializer", human_signed=False)
    assert out_tee["decision"] == "block"


def test_f1_bash_redirect_to_coverage_by_verifier_allows():
    """F1: the verifier (owns status + deletion) may write the model via shell."""
    out = hook.evaluate(tool_name="Bash",
                        tool_input={"command": "echo x > feature_list.json"},
                        resolved_actor="verifier", human_signed=False)
    assert out["decision"] == "allow"


def test_f1_bash_non_coverage_redirect_still_allowed():
    """F1: a redirect to a NON-coverage, non-protected path is unaffected."""
    out = hook.evaluate(tool_name="Bash",
                        tool_input={"command": "echo x > /tmp/scratch.txt"},
                        resolved_actor="implementer", human_signed=False)
    assert out["decision"] == "allow"


def test_f2_non_dict_tool_input_fails_closed():
    """F2 (CRITICAL): a present-but-non-dict tool_input must BLOCK (the old code
    re-raised in the except and exited 1 = a non-blocking error = fail OPEN)."""
    for bad in ("not-a-dict", ["a", "b"], 42):
        out = hook.evaluate(tool_name="Edit", tool_input=bad,
                            resolved_actor="implementer", human_signed=False)
        assert out["decision"] == "block", f"non-dict {bad!r} must fail closed"


def test_f2_non_dict_subprocess_exits_2_not_1():
    rc, _o, err = _run({"session_id": "s1", "agent_type": "implementer",
                        "tool_name": "Edit", "tool_input": "not-a-dict"})
    assert rc == 2, f"want exit 2 (block); got {rc} (1 = fail-open via crash)"
    assert "Traceback" not in err


def test_f3_multiedit_born_proven_with_proven_anchor_blocks():
    """F3: appending a born-proven item with an old_string anchor that already
    contains status:proven (no first-match value move) must still block (T9)."""
    out = _ev("implementer", tool="MultiEdit", edits=[{
        "old_string": '{"id":"DONE","status":"proven"}]',
        "new_string": '{"id":"DONE","status":"proven"},{"id":"NEW","status":"proven"}]'}])
    assert out["decision"] == "block"


def test_f4_multiedit_born_in_scope_false_with_false_anchor_blocks():
    """F4(a): appending a born-in_scope:false item past a false anchor blocks (T11)."""
    out = _ev("implementer", tool="MultiEdit", edits=[{
        "old_string": '{"id":"DONE","in_scope":false}]',
        "new_string": '{"id":"DONE","in_scope":false},{"id":"NEW","in_scope":false}]'}])
    assert out["decision"] == "block"


@pytest.mark.parametrize("scope_literal", ['"false"', "0", '"no"'])
def test_f4_non_bool_in_scope_born_blocks(scope_literal):
    """F4(b): a born item with a NON-bool in_scope literal is treated as out-of-scope
    (needs a human signature), not silently in-scope (T11)."""
    new = f'{{"items":[{{"id":"X","status":"unproven","in_scope":{scope_literal}}}]}}'
    out = _ev("implementer", old=_EMPTY, new=new)
    assert out["decision"] == "block"


def test_f5_fragment_delete_without_status_token_blocks():
    """F5: a fragment Edit removing an item whose window carries NO status/in_scope
    token is still seen as a deletion via the id-token delta (T10)."""
    out = _ev("implementer", old='{"id":"F-1","title":"foo","priority":3},', new="")
    assert out["decision"] == "block"
    assert "delet" in out["reason"].lower() or "append" in out["reason"].lower()


def test_f6_verifier_multiedit_delete_not_false_blocked():
    """F6(a): a verifier deleting an item via a MultiEdit fragment must NOT be
    false-blocked as an in_scope mutation — the verifier owns deletion."""
    out = _ev("verifier", tool="MultiEdit",
              edits=[{"old_string": '{"id":"F-1","status":"unproven","in_scope":true},', "new_string": ""}])
    assert out["decision"] == "allow"


def test_f6_benign_fragment_spanning_in_scope_token_allows():
    """F6(b): a benign edit whose window merely SPANS an in_scope:true token (without
    moving its value or removing an id) must not false-block."""
    out = _ev("implementer",
              old='"in_scope":true,"acceptance_criteria":[]',
              new='"in_scope":true,"acceptance_criteria":["a"]')
    assert out["decision"] == "allow"


def test_f7_dup_id_proven_shadow_blocks():
    """F7: a full-doc Edit that flips the real item proven and appends a duplicate-id
    unproven shadow must not hide the proven copy behind last-wins."""
    old = '{"items":[{"id":"F-1","status":"unproven","in_scope":true}]}'
    new = ('{"items":[{"id":"F-1","status":"proven","in_scope":true},'
           '{"id":"F-1","status":"unproven","in_scope":true}]}')
    out = _ev("implementer", old=old, new=new)
    assert out["decision"] == "block"


def test_n1_trailing_space_coverage_path_still_gated():
    """N1 (re-red-team): a trailing-space 'feature_list.json ' must NOT dodge the gate
    — basename matching normalizes the space, so an impl status flip still blocks."""
    out = _ev("implementer", old=_doc("F-1"), new=_doc("F-1", status="proven"),
              path="feature_list.json ")
    assert out["decision"] == "block"


def test_n2_real_nested_coverage_path_still_matches():
    """N2: the real nested model path (apps/web/feature_list.json) still matches by
    basename — the suffix→basename change must not stop gating the genuine model."""
    out = _ev("implementer", old=_doc("F-1"), new=_doc("F-1", status="proven"),
              path="apps/web/feature_list.json")
    assert out["decision"] == "block"


def test_n2_differently_named_file_not_treated_as_coverage():
    """N2: a genuinely different file merely NAMED like the model
    (my_feature_list.json) must NOT be subjected to coverage rules — basename
    'my_feature_list.json' != 'feature_list.json', so a status edit there is allowed."""
    out = _ev("implementer", old=_doc("F-1"), new=_doc("F-1", status="proven"),
              path="my_feature_list.json")
    assert out["decision"] == "allow"


def test_n2_bash_redirect_to_differently_named_file_allowed():
    """N2: Bash redirect to a non-coverage file named like the model is no longer
    over-blocked (basename mismatch)."""
    out = hook.evaluate(tool_name="Bash",
                        tool_input={"command": "echo x > docs/old_feature_list.json"},
                        resolved_actor="main", human_signed=False)
    assert out["decision"] == "allow"

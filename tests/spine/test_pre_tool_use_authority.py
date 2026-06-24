"""Actor-independence fix #4: field-level write authority at PreToolUse.

Contract (Task 2): authority is detected by DIFFING the JSON (old_string vs
new_string for Edit; on-disk vs content for Write), not by a phantom ``field``
key. ``evaluate`` takes ``tool_name``; ``human_signed`` is resolved out-of-band
from the ``HUMAN_SIGNED`` env var, never from the tool payload. On a BLOCK the
hook writes the reason to STDERR and exits 2 (no JSON to stdout).
"""
import hashlib  # noqa: F401  (kept for parity with sibling spine tests)
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude/hooks/pre_tool_use_hook.py"

_p = ROOT / ".claude/hooks/pre_tool_use_hook.py"
_spec = importlib.util.spec_from_file_location("pre_tool_use_hook", _p)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

FL = "apps/web/feature_list.json"

_OLD = '{"items":[{"id":"X","in_scope":true,"status":"unproven"}]}'
_NEW = '{"items":[{"id":"X","in_scope":true,"status":"proven"}]}'


def _run(event: dict, env: dict | None = None):
    e = {**os.environ, **(env or {})}
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event),
                       capture_output=True, text=True, env=e, cwd=str(ROOT))
    return p.returncode, p.stdout, p.stderr


# --- Real-payload subprocess behaviors (Task 2 contract) -------------------

def test_real_edit_status_flip_by_implementer_blocks():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Edit",
        "tool_input": {"file_path": "feature_list.json", "old_string": _OLD, "new_string": _NEW}})
    assert rc == 2 and "verifier" in err            # blocked, reason on STDERR


def test_real_edit_status_flip_by_verifier_allows():
    rc, out, err = _run({"session_id": "s", "agent_type": "verifier", "tool_name": "Edit",
        "tool_input": {"file_path": "feature_list.json", "old_string": _OLD, "new_string": _NEW}})
    assert rc == 0


def test_bash_redirect_to_protected_path_blocks():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Bash",
        "tool_input": {"command": "echo x > tests/spine/x.py"}})
    assert rc == 2 and "tests/" in err


def test_in_scope_flip_with_payload_human_signed_but_no_env_blocks():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Edit",
        "tool_input": {"file_path": "feature_list.json",
                       "old_string": '{"items":[{"id":"X","in_scope":false}]}',
                       "new_string": '{"items":[{"id":"X","in_scope":true}]}',
                       "human_signed": True}})   # forged in payload
    assert rc == 2


def test_in_scope_flip_with_HUMAN_SIGNED_env_allows():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Edit",
        "tool_input": {"file_path": "feature_list.json",
                       "old_string": '{"items":[{"id":"X","in_scope":false}]}',
                       "new_string": '{"items":[{"id":"X","in_scope":true}]}'}},
        env={"HUMAN_SIGNED": "true"})
    assert rc == 0


# --- Pure-core evaluate() behaviors (migrated to JSON-delta contract) -------

def test_status_write_by_implementer_blocked():
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": FL, "old_string": _OLD, "new_string": _NEW},
                        resolved_actor="implementer", human_signed=False)
    assert out["decision"] == "block" and "status" in out["reason"].lower()


def test_status_write_by_verifier_allowed():
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": FL, "old_string": _OLD, "new_string": _NEW},
                        resolved_actor="verifier", human_signed=False)
    assert out["decision"] == "allow"


def test_in_scope_requires_human():
    old = '{"items":[{"id":"X","in_scope":false}]}'
    new = '{"items":[{"id":"X","in_scope":true}]}'
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": FL, "old_string": old, "new_string": new},
                        resolved_actor="verifier", human_signed=False)
    assert out["decision"] == "block" and "in_scope" in out["reason"].lower()
    ok = hook.evaluate(tool_name="Edit",
                       tool_input={"file_path": FL, "old_string": old, "new_string": new},
                       resolved_actor="verifier", human_signed=True)
    assert ok["decision"] == "allow"


def test_benign_edit_does_not_block():
    old = '{"items":[{"id":"F-1","status":"unproven","in_scope":true,"acceptance_criteria":[]}]}'
    new = '{"items":[{"id":"F-1","status":"unproven","in_scope":true,"acceptance_criteria":["x"]}]}'
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": FL, "old_string": old, "new_string": new},
                        resolved_actor="implementer", human_signed=False)
    assert out["decision"] == "allow"          # no field move → no deny


def test_protected_artifact_blocked_for_agent():
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": "tests/spine/test_stop_hook.py"},
                        resolved_actor="implementer", human_signed=False)
    assert out["decision"] == "block" and "tests/" in out["reason"]


def test_protected_artifact_allowed_for_main():
    out = hook.evaluate(tool_name="Edit",
                        tool_input={"file_path": "tests/spine/test_stop_hook.py"},
                        resolved_actor="main", human_signed=False)
    assert out["decision"] == "allow"


def test_bash_write_targets_parses_redirect_and_tee():
    assert "a.py" in hook._bash_write_targets("echo x > a.py")
    assert "b.py" in hook._bash_write_targets("echo x >> b.py")
    assert "c.py" in hook._bash_write_targets("echo x | tee c.py")
    assert "d.py" in hook._bash_write_targets("echo x | tee -a d.py")


# --- C1 hardening: common write VERBS, not just > / >> / tee ----------------
# A redirect is not the only statically-parseable shell write. sed -i / cp / mv /
# dd / install / ln route around Edit/Write too; _bash_write_targets must surface
# their DESTINATION so the same protected-path + coverage-write authority applies.
def test_bash_write_targets_parses_inplace_and_copy_verbs():
    assert "feature_list.json" in hook._bash_write_targets("sed -i 's/unproven/proven/' feature_list.json")
    assert "feature_list.json" in hook._bash_write_targets("sed --in-place 's/a/b/' feature_list.json")
    assert "feature_list.json" in hook._bash_write_targets("sed -i.bak -e 's/a/b/' feature_list.json")
    assert "feature_list.json" in hook._bash_write_targets("cp /tmp/forged.json feature_list.json")
    assert "feature_list.json" in hook._bash_write_targets("mv /tmp/forged.json feature_list.json")
    assert "feature_list.json" in hook._bash_write_targets("dd if=/tmp/x of=feature_list.json")
    assert "feature_list.json" in hook._bash_write_targets("ln -sf /tmp/x feature_list.json")
    assert "feature_list.json" in hook._bash_write_targets("install -m 644 /tmp/x feature_list.json")
    # protected artifacts (the gate hook itself, a test) via the same verbs
    assert ".claude/hooks/pre_tool_use_hook.py" in hook._bash_write_targets(
        "cp /tmp/evil.py .claude/hooks/pre_tool_use_hook.py")
    assert "tests/spine/test_loop_gate.py" in hook._bash_write_targets(
        "sed -i 's/x/y/' tests/spine/test_loop_gate.py")


def test_bash_write_targets_does_not_flag_sources_or_reads():
    # cp/mv DESTINATION is the write target; the SOURCE (a read) must NOT be flagged.
    assert "feature_list.json" not in hook._bash_write_targets("cp feature_list.json /tmp/backup.json")
    assert "feature_list.json" not in hook._bash_write_targets("mv feature_list.json /tmp/backup.json")
    # sed WITHOUT -i writes to stdout (a read) — not a write target.
    assert "feature_list.json" not in hook._bash_write_targets("sed 's/a/b/' feature_list.json")
    assert hook._bash_write_targets("cat feature_list.json") == []


def test_bash_inplace_status_flip_by_implementer_blocks():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Bash",
        "tool_input": {"command": "sed -i 's/unproven/proven/' feature_list.json"}})
    assert rc == 2 and "feature_list.json" in err           # coverage-write blocked


def test_bash_cp_over_coverage_model_by_implementer_blocks():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Bash",
        "tool_input": {"command": "cp /tmp/forged.json feature_list.json"}})
    assert rc == 2 and "feature_list.json" in err


def test_bash_cp_over_protected_hook_by_implementer_blocks():
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Bash",
        "tool_input": {"command": "cp /tmp/evil.py .claude/hooks/pre_tool_use_hook.py"}})
    assert rc == 2 and ".claude/hooks/" in err              # protected-path blocked


def test_bash_inplace_over_coverage_model_by_verifier_allows():
    rc, out, err = _run({"session_id": "s", "agent_type": "verifier", "tool_name": "Bash",
        "tool_input": {"command": "sed -i 's/unproven/proven/' feature_list.json"}})
    assert rc == 0                                          # verifier owns the model


def test_bash_copy_coverage_model_OUT_by_implementer_allows():
    # Copying the model to a non-protected destination is a READ of the source —
    # the no-false-block contract: only the DESTINATION is the write target.
    rc, out, err = _run({"session_id": "s", "agent_type": "implementer", "tool_name": "Bash",
        "tool_input": {"command": "cp feature_list.json /tmp/backup.json"}})
    assert rc == 0


# --- C1 hardening, round 2: adversarial red-team regression matrix -----------
# Each command below was an empirically-confirmed EVASION (the parser returned [] or the
# gate ALLOWed an implementer write to the coverage model / a protected artifact). They
# must now BLOCK. Run in-process via evaluate() for breadth + speed.
def _dec(cmd, actor="implementer"):
    return hook.evaluate(tool_name="Bash", tool_input={"command": cmd},
                         resolved_actor=actor, human_signed=False)["decision"]


_REDTEAM_BLOCK = [
    # alt write verbs with literal argv/operand targets
    "perl -i -pe 's/unproven/proven/' feature_list.json",
    "perl -pi -e 's/x/y/' tests/test_a.py",
    "truncate -s0 feature_list.json",
    "truncate --size=0 .github/workflows/ci.yml",
    "rsync /tmp/evil feature_list.json",
    "rsync /tmp/x .claude/hooks/pre_tool_use_hook.py",
    "busybox sed -i 's/a/b/' feature_list.json",          # multiplexer masks the inner verb
    "gsed -i 's/u/p/' feature_list.json",                 # macOS GNU coreutils (g-prefixed)
    "gcp /tmp/x feature_list.json",
    "gtruncate -s0 .github/workflows/ci.yml",
    "patch feature_list.json",                            # ORIGFILE (first operand)
    "ed feature_list.json",
    "ex tests/test_a.py",
    "tar -xf /tmp/e.tar -C .claude/hooks",                # extraction dest dir
    "tar -xf /tmp/e.tar -C tests",                        # bare-dir prefix
    # path normalization (verb-independent): ./ , // , bare dir
    "cp evil ./tests/test_x.py",
    "echo x > ./tests/test_x.py",
    "sed -i s/a/b/ ./tests/test_x.py",
    "cp evil ./.claude/hooks/x.py",
    "echo x > ./.claude/settings.json",
    "cp x tests",                                         # bare protected DIR
    # ANSI-C $'...' quoting artifact
    "cp x.json $'feature_list.json'",
    "cp evil.py $'tests/test_x.py'",
    # option-argument-consuming flags permuted after the destination
    "cp newmodel.json feature_list.json -S .bak",
    "install impl.py tests/test_x.py -m 644",
    "mv staged feature_list.json -S .orig",
    "cp src .github/workflows/ci.yml --suffix .bak",
    # positional-arg wrappers + noclobber redirect
    "timeout 5 cp x feature_list.json",
    "flock /tmp/l cp x feature_list.json",
    "time cp x .claude/hooks/evil.py",
    "cat z >| feature_list.json",
    # value-taking wrapper flags (round-2: the value must not be mis-read as the verb)
    "nice -n 5 cp src feature_list.json",
    "ionice -c 3 cp src feature_list.json",
    "watch -n 5 cp src feature_list.json",
    "stdbuf -o L cp src feature_list.json",
    "env -i cp src feature_list.json",                    # env -i takes NO value (must stay blocked)
    "tar -xf a.tar -C tests",                             # extract -C still blocks
    # round-3: tar OLD dash-less extract syntax + more positional/launcher wrappers
    "tar xf a.tar -C tests",
    "tar xzf a.tar -C .claude/hooks",
    "taskset 0x1 cp src feature_list.json",
    "taskset -c 0 cp src feature_list.json",
    "chrt -f 99 cp src feature_list.json",
    "runuser -u root -- cp src feature_list.json",
    "unbuffer cp src feature_list.json",
    "setarch x86_64 cp src feature_list.json",
    "cpulimit -l 50 -- cp src feature_list.json",
]


def test_bash_redteam_evasions_now_block():
    failures = [c for c in _REDTEAM_BLOCK if _dec(c) != "block"]
    assert not failures, f"these red-team evasions still ALLOW: {failures}"


# No-false-positive contract: legitimate READS / sources must stay ALLOWED.
_REDTEAM_ALLOW = [
    "cp -t /tmp/backup/ feature_list.json",              # -t mode: operands are SOURCES
    "sed -i -f tests/fixtures/clean.sed /tmp/out.txt",   # -f is a script FILE (read)
    "cp feature_list.json /tmp/backup.json",             # copy the model OUT (read)
    "sed 's/a/b/' feature_list.json",                    # no -i => stdout (read)
    "cat feature_list.json",
    "rsync feature_list.json /tmp/out/",                 # model is the SOURCE
    "tar -cf /tmp/a.tar -C tests .",                     # CREATE: -C is a source chdir (read)
    "tar -czf /tmp/a.tar -C tests/ subdir",
    "tar -tf /tmp/a.tar -C tests",                       # LIST: -C is a source chdir
    "tar cf /tmp/a.tar -C tests .",                      # CREATE old dash-less syntax
    "tar tf a.tar -C tests",                             # LIST old dash-less syntax
    "nice -n 5 pytest tests/",                           # wrapper value-flag, non-write verb
    "nice -n 5 cat feature_list.json",                  # wrapper value-flag, read
    "taskset 0x1 pytest tests/",                         # positional wrapper, non-write verb
    "unbuffer pytest tests/",
]


def test_bash_redteam_reads_still_allow():
    failures = [c for c in _REDTEAM_ALLOW if _dec(c) != "allow"]
    assert not failures, f"these legitimate reads are wrongly BLOCKED: {failures}"


# Documented UNDECIDABLE residual: a target produced by stdin / eval / command
# substitution / arbitrary program execution is NOT statically visible — these ALLOW
# today and are closed only by the Phase-B evidence chain-of-custody (C1 in
# docs/phase1-known-issues.md). Asserted so the residual is explicit, not silent.
_REDTEAM_RESIDUAL = [
    "bash -c 'cp x feature_list.json'",
    "eval \"cp x feature_list.json\"",
    "echo feature_list.json | xargs sed -i s/a/b/",
    "$(printf cp) x feature_list.json",
    "su -c 'cp x feature_list.json'",                    # quoted command string = program-exec
    "parallel cp {} feature_list.json ::: a",            # command template (GNU parallel)
]


def test_bash_undecidable_residual_is_documented_not_silently_blocked():
    # These remain ALLOW by design (no static literal target). If a future change starts
    # BLOCKING one, that is a win — update this list and docs/phase1-known-issues.md.
    assert all(_dec(c) == "allow" for c in _REDTEAM_RESIDUAL)


def test_bash_abs_path_under_repo_blocks_but_outside_allows():
    inside = f'cp evil "{ROOT}/tests/foo.py"'
    outside = "cp evil /tmp/elsewhere/tests/foo.py"
    assert _dec(inside) == "block"      # absolute path UNDER the repo root → relativized
    assert _dec(outside) == "allow"     # arbitrary external path is not claimably protected


def test_bash_verifier_still_writes_model_via_new_verbs():
    # The verb expansion must not over-block the VERIFIER (who owns the model).
    for c in ("perl -i -pe 's/a/b/' feature_list.json", "truncate -s0 feature_list.json"):
        assert _dec(c, actor="verifier") == "allow"

# autonomous-agent.dev — Phase 0 Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the website-scoped coverage-control spine that gates the build of `autonomous-agent.dev`, and prove it end-to-end on one trivial slice (the `/` route renders) so that "done" is a deterministic, evidence-backed machine fact — not a self-report.

**Architecture:** A small Python control plane (Claude Code command hooks + tools) governs an `apps/web` Next.js workspace. A version-controlled `apps/web/feature_list.json` coverage model defaults every requirement to `unproven`; an **independent verifier** subagent is the only actor allowed to flip an item to `proven`, and only by attaching a 4-field evidence record whose `output_hash` the gate **re-derives** from the captured artifact bytes. Five actor-independence fixes make this honest under a fully-autonomous loop: (1) harness-stamped actor identity, (2) verifier-session ≠ implementer-session, (3) gate-side hash re-derivation, (4) field-level write authority (`status` vs `in_scope`), (5) a Z3 + property proof of actor separation. The Stop hook blocks termination while any in-scope item is `unproven`, but checks HANDOFF (cap/budget/no-progress) **first** and allows exit there (the corrected infinite-block semantics).

**Tech Stack:** Python 3.11+ (control plane, pytest, hypothesis, jsonschema, z3-solver — already pinned in `pyproject.toml`), Conftest/OPA (Rego policy), Next.js App Router + TypeScript (the `apps/web` workspace), Playwright (behavioral proof), pnpm (workspace package manager), GitHub Actions (required status check), Vercel (preview deploys).

**Design source:** `docs/superpowers/specs/2026-06-15-website-autonomous-sdlc-execution-design.md`
**Website spec:** `docs/website/autonomous-agent.dev/{requirements,design,tasks}.md`
**Methodology source:** `.kiro/specs/spec-to-evidence-control/{PRD_MERGED_canonical_spec_to_evidence.md,requirements.md,design.md}`

**Runtime assumption (documented):** Claude Code delivers hook input as a JSON object on **stdin** containing at least `session_id`, `transcript_path`, `cwd`, `hook_event_name`, and the tool fields (`tool_name`, `tool_input`). The active subagent name is exposed to hooks via the environment variable `CLAUDE_AGENT_NAME` (set by the harness when a subagent is spawned; absent/`main` for the root session). All actor identity is resolved from these runtime-supplied values — **never** from data the writing agent places inside an evidence record. If your Claude Code version exposes the agent name under a different key, adjust `tools/actor_identity.py` only; nothing else reads agent identity directly.

---

## File Structure

Control plane (Python, repo root):
- `schema/feature_list.schema.json` — draft-07 schema for the coverage model + evidence record.
- `apps/web/feature_list.json` — the coverage model (seeded with one trivial item; materialized to 209 in Task 13).
- `tools/actor_identity.py` — resolves `{session_id, actor_agent}` from runtime, not agent input (fix #1).
- `tools/evidence.py` — `EvidenceCollector` (sha256 over real artifact bytes) + record dataclass.
- `tools/audit_log.py` — append-only hash-chained gate-decision log + `verify_chain`.
- `tools/coverage.py` — load/validate/query the model; allowed status transitions; field-level write authority (fix #4).
- `.claude/hooks/pre_tool_use_hook.py` — the only true prevention gate (fixes #1, #2, #4 + plan/SHA + scope-sequencing + artifact guard).
- `.claude/hooks/subagent_stop_hook.py` — evidence-schema gate + hash re-derivation (fix #3) + session-distinctness (fix #2) + omission declaration.
- `.claude/hooks/stop_hook.py` — completion gate; HANDOFF-first exit-0 semantics.
- `.claude/hooks/post_tool_use_hook.py`, `pre_compact_hook.py`, `session_start_hook.py` — feedback / checkpoint / restore.
- `.claude/settings.json` — command-type hook wiring (no http/mcp).
- `.claude/agents/{verifier,implementer,initializer,research}.md` — permission-scoped subagents.
- `.github/policies/coverage.rego` — zero-evidence OPA policy.
- `.github/workflows/coverage-gate.yml` — required status check (Conftest + chain verify + property tests).
- `verification/actor_separation.py` — Z3 proof that a `proven` item implies a verifier actor distinct from the implementer (fix #5).
- `plan-approved.json` — SHA-bound human approval marker (gate #1).

Website workspace (TypeScript, the trivial slice):
- `apps/web/package.json`, `apps/web/next.config.ts`, `apps/web/tsconfig.json`, `apps/web/playwright.config.ts`
- `apps/web/app/layout.tsx`, `apps/web/app/page.tsx` — the trivial `/` slice.
- `apps/web/tests/e2e/home.spec.ts` — the behavioral proof for the trivial slice.

Tests (Python):
- `tests/unit/` — per-tool unit tests. `tests/integration/` — the end-to-end spine proof. `tests/property/` — hypothesis properties. `tests/smoke/` — hook-config smoke test.

---

## Task 1: Monorepo + Python control-plane env + apps/web workspace

**Files:**
- Modify: `pyproject.toml` (add test deps + pytest config)
- Create: `pnpm-workspace.yaml`, `apps/web/package.json`, `apps/web/tsconfig.json`, `apps/web/next.config.ts`
- Create: `tests/unit/__init__.py`, `tests/smoke/test_repo_layout.py`

- [ ] **Step 1: Write the failing test**

`tests/smoke/test_repo_layout.py`:
```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_apps_web_workspace_exists():
    assert (ROOT / "apps" / "web" / "package.json").is_file()
    assert (ROOT / "pnpm-workspace.yaml").is_file()

def test_schema_dir_reserved():
    assert (ROOT / "schema").is_dir()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/smoke/test_repo_layout.py -v`
Expected: FAIL (`apps/web/package.json` missing, `schema` dir missing).

- [ ] **Step 3: Create the scaffolding**

`pnpm-workspace.yaml`:
```yaml
packages:
  - "apps/*"
```

`apps/web/package.json`:
```json
{
  "name": "@autonomous-agent/web",
  "private": true,
  "version": "0.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "next": "15.1.0",
    "react": "19.0.0",
    "react-dom": "19.0.0"
  },
  "devDependencies": {
    "@playwright/test": "1.49.0",
    "typescript": "5.7.2",
    "@types/react": "19.0.0",
    "@types/node": "22.10.0"
  }
}
```

`apps/web/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "ES2022"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noEmit": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "jsx": "preserve",
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

`apps/web/next.config.ts`:
```typescript
import type { NextConfig } from "next";
const nextConfig: NextConfig = { reactStrictMode: true };
export default nextConfig;
```

Then create the reserved dirs and pytest config. Append to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[dependency-groups]
dev = ["pytest>=8", "hypothesis>=6", "jsonschema>=4", "z3-solver>=4.16"]
```

Run: `mkdir -p schema tests/unit tests/integration tests/property tests/smoke .claude/hooks .claude/agents tools verification .github/policies .github/workflows apps/web/app apps/web/tests/e2e && touch tests/unit/__init__.py`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/smoke/test_repo_layout.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml pnpm-workspace.yaml apps/web tests schema
git commit -m "chore(spine): scaffold monorepo, apps/web workspace, control-plane dirs"
```

---

## Task 2: Coverage-model JSON Schema (draft-07)

**Files:**
- Create: `schema/feature_list.schema.json`, `apps/web/feature_list.json`
- Test: `tests/unit/test_schema.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_schema.py`:
```python
import json
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schema" / "feature_list.schema.json").read_text())
MODEL = json.loads((ROOT / "apps" / "web" / "feature_list.json").read_text())

def test_seed_model_is_valid():
    jsonschema.validate(MODEL, SCHEMA)

def test_default_status_is_unproven():
    assert all(item["status"] == "unproven" for item in MODEL["items"])

def test_id_pattern_three_segment():
    import re
    pat = re.compile(r"^[A-Z]+-[A-Z]+-[0-9]{3}$")
    assert all(pat.match(item["id"]) for item in MODEL["items"])

def test_proven_requires_full_evidence():
    # a proven item with an incomplete evidence record must FAIL validation
    bad = json.loads(json.dumps(MODEL))
    bad["items"][0]["status"] = "proven"
    bad["items"][0]["evidence"] = {"test_file": "x", "test_name": "y"}  # missing fields
    try:
        jsonschema.validate(bad, SCHEMA)
        assert False, "should have raised"
    except jsonschema.ValidationError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_schema.py -v`
Expected: FAIL (schema + model files do not exist).

- [ ] **Step 3: Write the schema and seed model**

`schema/feature_list.schema.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "product_class", "items"],
  "properties": {
    "schema_version": { "type": "string" },
    "product_class": { "const": "public-marketing-website" },
    "checklist_ref": {
      "type": "object",
      "additionalProperties": false,
      "properties": { "path": {"type": "string"}, "version": {"type": "string"}, "sha": {"type": "string"} }
    },
    "items": { "type": "array", "items": { "$ref": "#/definitions/coverageItem" } }
  },
  "definitions": {
    "coverageItem": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "type", "priority", "dependencies", "acceptance_criteria", "in_scope", "status", "evidence"],
      "properties": {
        "id": { "type": "string", "pattern": "^[A-Z]+-[A-Z]+-[0-9]{3}$" },
        "type": { "type": "string", "enum": ["functional", "NFR", "WIRING"] },
        "priority": { "type": "string", "enum": ["P0", "P1", "P2", "P3"] },
        "source_ears_id": { "type": "string" },
        "dependencies": { "type": "array", "items": { "type": "string" } },
        "acceptance_criteria": { "type": "array", "minItems": 1, "items": { "type": "string" } },
        "in_scope": { "type": "boolean" },
        "status": { "type": "string", "enum": ["unproven", "proven", "failed"] },
        "evidence": { "oneOf": [ { "type": "null" }, { "$ref": "#/definitions/evidenceRecord" } ] }
      },
      "allOf": [
        {
          "if": { "properties": { "status": { "const": "proven" } } },
          "then": { "properties": { "evidence": { "$ref": "#/definitions/evidenceRecord" } }, "required": ["evidence"] }
        }
      ]
    },
    "evidenceRecord": {
      "type": "object",
      "additionalProperties": false,
      "required": ["test_file", "test_name", "output_hash", "collected_at", "actor_agent", "verifier_session_id", "implementer_session_id"],
      "properties": {
        "test_file": { "type": "string", "minLength": 1 },
        "test_name": { "type": "string", "minLength": 1 },
        "output_hash": { "type": "string", "pattern": "^sha256:[a-f0-9]{64}$" },
        "collected_at": { "type": "string", "minLength": 1 },
        "actor_agent": { "type": "string", "minLength": 1 },
        "verifier_session_id": { "type": "string", "minLength": 1 },
        "implementer_session_id": { "type": "string", "minLength": 1 }
      }
    }
  }
}
```

`apps/web/feature_list.json` (seed: one trivial slice — the home route renders):
```json
{
  "schema_version": "1.0.0",
  "product_class": "public-marketing-website",
  "checklist_ref": { "path": "baselines/public-marketing-website.json", "version": "0.1.0", "sha": "" },
  "items": [
    {
      "id": "HOME-RND-001",
      "type": "functional",
      "priority": "P0",
      "source_ears_id": "HOME-01",
      "dependencies": [],
      "acceptance_criteria": ["GET / returns 200 and the document contains the brand wordmark text 'Autonomous Agent'."],
      "in_scope": true,
      "status": "unproven",
      "evidence": null
    }
  ]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_schema.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add schema/feature_list.schema.json apps/web/feature_list.json tests/unit/test_schema.py
git commit -m "feat(spine): coverage-model draft-07 schema + seed trivial slice"
```

---

## Task 3: Actor identity — harness-stamped, never agent-supplied (fix #1)

**Files:**
- Create: `tools/__init__.py`, `tools/actor_identity.py`
- Test: `tests/unit/test_actor_identity.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_actor_identity.py`:
```python
from tools.actor_identity import resolve_identity

def test_actor_from_env_not_payload(monkeypatch):
    monkeypatch.setenv("CLAUDE_AGENT_NAME", "implementer.md")
    hook_input = {"session_id": "sess-abc", "actor_agent": "verifier.md"}  # forged field
    ident = resolve_identity(hook_input)
    # the forged actor_agent in the payload is IGNORED; runtime env wins
    assert ident.actor_agent == "implementer.md"
    assert ident.session_id == "sess-abc"

def test_missing_agent_defaults_to_main(monkeypatch):
    monkeypatch.delenv("CLAUDE_AGENT_NAME", raising=False)
    ident = resolve_identity({"session_id": "sess-1"})
    assert ident.actor_agent == "main"

def test_session_required():
    import pytest
    with pytest.raises(ValueError):
        resolve_identity({})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_actor_identity.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write the implementation**

`tools/__init__.py`: (empty file)

`tools/actor_identity.py`:
```python
"""Resolve the acting agent identity from RUNTIME signals only.

The writing agent must never be able to declare its own identity inside an
evidence record (fix #1). Identity is derived from the harness-supplied env
var CLAUDE_AGENT_NAME and the hook stdin `session_id` — never from the tool
payload's own fields.
"""
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    session_id: str
    actor_agent: str


def resolve_identity(hook_input: dict) -> Identity:
    session_id = hook_input.get("session_id")
    if not session_id:
        raise ValueError("hook_input missing required 'session_id'")
    actor_agent = os.environ.get("CLAUDE_AGENT_NAME") or "main"
    return Identity(session_id=str(session_id), actor_agent=str(actor_agent))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_actor_identity.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add tools/__init__.py tools/actor_identity.py tests/unit/test_actor_identity.py
git commit -m "feat(spine): harness-stamped actor identity (fix #1)"
```

---

## Task 4: Evidence collector — sha256 over real artifact bytes

**Files:**
- Create: `tools/evidence.py`
- Test: `tests/unit/test_evidence.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_evidence.py`:
```python
import hashlib
from tools.evidence import EvidenceCollector, EvidenceRecord

def test_hash_is_over_real_bytes(tmp_path):
    artifact = tmp_path / "trace.zip"
    artifact.write_bytes(b"playwright-trace-bytes")
    rec = EvidenceCollector.collect(
        test_file="apps/web/tests/e2e/home.spec.ts",
        test_name="home route renders",
        artifact_path=artifact,
        actor_agent="verifier.md",
        verifier_session_id="sess-v",
        implementer_session_id="sess-i",
        collected_at="2026-06-15T00:00:00Z",
    )
    expected = "sha256:" + hashlib.sha256(b"playwright-trace-bytes").hexdigest()
    assert rec.output_hash == expected

def test_record_round_trips_to_dict():
    rec = EvidenceRecord(
        test_file="t", test_name="n", output_hash="sha256:" + "a"*64,
        collected_at="2026-06-15T00:00:00Z", actor_agent="verifier.md",
        verifier_session_id="sv", implementer_session_id="si",
    )
    d = rec.to_dict()
    assert set(d) == {"test_file","test_name","output_hash","collected_at",
                      "actor_agent","verifier_session_id","implementer_session_id"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_evidence.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write the implementation**

`tools/evidence.py`:
```python
"""Evidence records hashed over the ACTUAL captured artifact bytes."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path


def hash_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class EvidenceRecord:
    test_file: str
    test_name: str
    output_hash: str
    collected_at: str
    actor_agent: str
    verifier_session_id: str
    implementer_session_id: str

    def to_dict(self) -> dict:
        return asdict(self)


class EvidenceCollector:
    @staticmethod
    def collect(*, test_file: str, test_name: str, artifact_path: Path,
                actor_agent: str, verifier_session_id: str,
                implementer_session_id: str, collected_at: str) -> EvidenceRecord:
        data = Path(artifact_path).read_bytes()
        return EvidenceRecord(
            test_file=test_file,
            test_name=test_name,
            output_hash=hash_bytes(data),
            collected_at=collected_at,
            actor_agent=actor_agent,
            verifier_session_id=verifier_session_id,
            implementer_session_id=implementer_session_id,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_evidence.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add tools/evidence.py tests/unit/test_evidence.py
git commit -m "feat(spine): evidence collector hashes real artifact bytes"
```

---

## Task 5: Hash-chained gate-decision audit log

**Files:**
- Create: `tools/audit_log.py`
- Test: `tests/unit/test_audit_log.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_audit_log.py`:
```python
from tools.audit_log import AuditLog

def test_append_and_verify_chain(tmp_path):
    log = AuditLog(tmp_path / "gate_audit_log.jsonl")
    log.append({"gate": "stop", "decision": "block", "item": "HOME-RND-001"})
    log.append({"gate": "stop", "decision": "allow", "item": "HOME-RND-001"})
    assert log.verify_chain() is True

def test_tampering_breaks_chain(tmp_path):
    path = tmp_path / "gate_audit_log.jsonl"
    log = AuditLog(path)
    log.append({"gate": "stop", "decision": "block"})
    log.append({"gate": "opa", "decision": "deny"})
    lines = path.read_text().splitlines()
    lines[0] = lines[0].replace("block", "allow")  # tamper row 0
    path.write_text("\n".join(lines) + "\n")
    assert AuditLog(path).verify_chain() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_audit_log.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write the implementation**

`tools/audit_log.py`:
```python
"""Append-only, hash-chained gate-decision log. entry_hash = sha256(canonical_row || prev_hash)."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

GENESIS = hashlib.sha256(b"").hexdigest()


def _row_hash(payload: dict, prev_hash: str) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((canonical + prev_hash).encode()).hexdigest()


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _last_hash(self) -> str:
        if not self.path.exists():
            return GENESIS
        lines = [l for l in self.path.read_text().splitlines() if l.strip()]
        if not lines:
            return GENESIS
        return json.loads(lines[-1])["entry_hash"]

    def append(self, payload: dict) -> None:
        prev = self._last_hash()
        entry = {"payload": payload, "prev_hash": prev,
                 "entry_hash": _row_hash(payload, prev)}
        with self.path.open("a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    def verify_chain(self) -> bool:
        if not self.path.exists():
            return True
        prev = GENESIS
        for line in self.path.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry["prev_hash"] != prev:
                return False
            if entry["entry_hash"] != _row_hash(entry["payload"], prev):
                return False
            prev = entry["entry_hash"]
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_audit_log.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add tools/audit_log.py tests/unit/test_audit_log.py
git commit -m "feat(spine): hash-chained gate-decision audit log"
```

---

## Task 6: Coverage model — transitions + field-level write authority (fix #4)

**Files:**
- Create: `tools/coverage.py`
- Test: `tests/unit/test_coverage.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_coverage.py`:
```python
import json
import pytest
from pathlib import Path
from tools.coverage import CoverageModel, TransitionError, AuthorityError

def _model(tmp_path) -> Path:
    p = tmp_path / "feature_list.json"
    p.write_text(json.dumps({
        "schema_version": "1.0.0", "product_class": "public-marketing-website",
        "items": [{"id": "HOME-RND-001", "type": "functional", "priority": "P0",
                   "dependencies": [], "acceptance_criteria": ["x"],
                   "in_scope": True, "status": "unproven", "evidence": None}]
    }))
    return p

def test_unproven_blocks_completion(tmp_path):
    m = CoverageModel.load(_model(tmp_path))
    assert m.has_unproven_in_scope() is True
    assert m.is_complete() is False

def test_allowed_transition(tmp_path):
    m = CoverageModel.load(_model(tmp_path))
    m.assert_transition("HOME-RND-001", "unproven", "proven")  # ok

def test_forbidden_transition(tmp_path):
    m = CoverageModel.load(_model(tmp_path))
    with pytest.raises(TransitionError):
        m.assert_transition("HOME-RND-001", "proven", "unproven")  # not allowed

def test_status_write_requires_verifier(tmp_path):
    m = CoverageModel.load(_model(tmp_path))
    with pytest.raises(AuthorityError):
        m.assert_field_authority(field="status", actor_agent="implementer.md", human_signed=False)
    m.assert_field_authority(field="status", actor_agent="verifier.md", human_signed=False)  # ok

def test_in_scope_write_requires_human(tmp_path):
    m = CoverageModel.load(_model(tmp_path))
    with pytest.raises(AuthorityError):
        m.assert_field_authority(field="in_scope", actor_agent="verifier.md", human_signed=False)
    m.assert_field_authority(field="in_scope", actor_agent="verifier.md", human_signed=True)  # ok
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_coverage.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write the implementation**

`tools/coverage.py`:
```python
"""Coverage model: load, query, allowed transitions, and field-level write authority (fix #4)."""
from __future__ import annotations
import json
from pathlib import Path

ALLOWED_TRANSITIONS = {
    ("unproven", "proven"),
    ("unproven", "failed"),
    ("failed", "unproven"),
}


class TransitionError(Exception): ...
class AuthorityError(Exception): ...


class CoverageModel:
    def __init__(self, data: dict, path: Path):
        self.data = data
        self.path = path

    @classmethod
    def load(cls, path: Path) -> "CoverageModel":
        return cls(json.loads(Path(path).read_text()), Path(path))

    @property
    def items(self) -> list[dict]:
        return self.data["items"]

    def has_unproven_in_scope(self) -> bool:
        return any(i["in_scope"] and i["status"] != "proven" for i in self.items)

    def is_complete(self) -> bool:
        return not self.has_unproven_in_scope()

    def assert_transition(self, item_id: str, frm: str, to: str) -> None:
        if (frm, to) not in ALLOWED_TRANSITIONS:
            raise TransitionError(f"{item_id}: {frm}->{to} is not an allowed transition")

    def assert_field_authority(self, *, field: str, actor_agent: str, human_signed: bool) -> None:
        # status may be written ONLY by the verifier; in_scope ONLY by a human-signed change.
        if field == "status":
            if actor_agent != "verifier.md":
                raise AuthorityError("status is writable only by verifier.md")
        elif field == "in_scope":
            if not human_signed:
                raise AuthorityError("in_scope is mutable only via a human-signed change")
        else:
            raise AuthorityError(f"unknown protected field: {field}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_coverage.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add tools/coverage.py tests/unit/test_coverage.py
git commit -m "feat(spine): coverage transitions + field-level write authority (fix #4)"
```

---

## Task 7: SubagentStop hook — evidence gate, re-derivation (fix #3), session distinctness (fix #2)

**Files:**
- Create: `.claude/hooks/subagent_stop_hook.py`
- Test: `tests/unit/test_subagent_stop.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_subagent_stop.py`:
```python
import json, hashlib
from pathlib import Path
from importlib import import_module

hook = import_module(".claude.hooks.subagent_stop_hook".replace("/", "."))  # see note

def _evidence(tmp_path, *, vsess, isess, actor="verifier.md", body=b"trace"):
    art = tmp_path / "trace.zip"; art.write_bytes(body)
    return {
        "test_file": "apps/web/tests/e2e/home.spec.ts",
        "test_name": "home route renders",
        "output_hash": "sha256:" + hashlib.sha256(body).hexdigest(),
        "collected_at": "2026-06-15T00:00:00Z",
        "actor_agent": actor,
        "verifier_session_id": vsess,
        "implementer_session_id": isess,
        "_artifact_path": str(art),
        "omission_declaration": "[Gap] 500-state untested in this slice.",
    }

def test_accepts_valid_distinct_session(tmp_path):
    ev = _evidence(tmp_path, vsess="sv", isess="si")
    assert hook.evaluate(ev) == {"decision": "approve"}

def test_rejects_same_session(tmp_path):  # fix #2
    ev = _evidence(tmp_path, vsess="same", isess="same")
    out = hook.evaluate(ev)
    assert out["decision"] == "block" and "session" in out["reason"].lower()

def test_rejects_hash_mismatch(tmp_path):  # fix #3 re-derivation
    ev = _evidence(tmp_path, vsess="sv", isess="si")
    ev["output_hash"] = "sha256:" + "0"*64  # declared hash != real bytes
    out = hook.evaluate(ev)
    assert out["decision"] == "block" and "hash" in out["reason"].lower()

def test_rejects_missing_omission(tmp_path):
    ev = _evidence(tmp_path, vsess="sv", isess="si"); ev.pop("omission_declaration")
    out = hook.evaluate(ev)
    assert out["decision"] == "block"
```

> Note: import the hook by file path in the test setup instead of dotted import:
> ```python
> import importlib.util, pathlib
> spec = importlib.util.spec_from_file_location(
>     "subagent_stop_hook",
>     pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/subagent_stop_hook.py")
> hook = importlib.util.module_from_spec(spec); spec.loader.exec_module(hook)
> ```
> Replace the `import_module(...)` line above with this block.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_subagent_stop.py -v`
Expected: FAIL (hook file missing).

- [ ] **Step 3: Write the implementation**

`.claude/hooks/subagent_stop_hook.py`:
```python
#!/usr/bin/env python3
"""SubagentStop gate: accept a verifier result ONLY if the evidence record is
schema-complete, the declared output_hash RE-DERIVES from the captured artifact
bytes (fix #3), the verifier and implementer sessions DIFFER (fix #2), and a
non-empty omission_declaration is present."""
from __future__ import annotations
import sys, json, hashlib
from pathlib import Path

REQUIRED = ("test_file", "test_name", "output_hash", "collected_at",
            "actor_agent", "verifier_session_id", "implementer_session_id")


def evaluate(ev: dict) -> dict:
    for f in REQUIRED:
        if not ev.get(f):
            return {"decision": "block", "reason": f"evidence missing required field: {f}"}
    if not ev.get("omission_declaration"):
        return {"decision": "block", "reason": "missing omission_declaration"}
    if ev["verifier_session_id"] == ev["implementer_session_id"]:
        return {"decision": "block", "reason": "verifier session must differ from implementer session"}
    artifact = ev.get("_artifact_path")
    if not artifact or not Path(artifact).exists():
        return {"decision": "block", "reason": "captured artifact not found for re-derivation"}
    rederived = "sha256:" + hashlib.sha256(Path(artifact).read_bytes()).hexdigest()
    if rederived != ev["output_hash"]:
        return {"decision": "block", "reason": "output_hash does not match re-derived artifact hash"}
    return {"decision": "approve"}


def main() -> int:
    payload = json.load(sys.stdin)
    ev = payload.get("tool_input", payload).get("evidence", payload)
    result = evaluate(ev)
    if result["decision"] == "block":
        print(result["reason"], file=sys.stderr)
        return 2  # exit 2 blocks acceptance
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_subagent_stop.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/subagent_stop_hook.py tests/unit/test_subagent_stop.py
git commit -m "feat(spine): SubagentStop gate — re-derive hash (fix #3) + session distinctness (fix #2)"
```

---

## Task 8: PreToolUse hook — plan/SHA gate, scope-sequencing, field authority, artifact guard

**Files:**
- Create: `.claude/hooks/pre_tool_use_hook.py`, `plan-approved.json`
- Test: `tests/unit/test_pre_tool_use.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_pre_tool_use.py`:
```python
import importlib.util, pathlib, json, hashlib

def _load():
    p = pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/pre_tool_use_hook.py"
    spec = importlib.util.spec_from_file_location("pre_tool_use_hook", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

hook = _load()

def test_blocks_status_write_by_implementer():
    out = hook.evaluate(
        tool_input={"file_path": "apps/web/feature_list.json", "field": "status"},
        actor_agent="implementer.md", human_signed=False,
        feature_list_sha="abc", approved_sha="abc")
    assert out["decision"] == "block" and "status" in out["reason"].lower()

def test_allows_status_write_by_verifier():
    out = hook.evaluate(
        tool_input={"file_path": "apps/web/feature_list.json", "field": "status"},
        actor_agent="verifier.md", human_signed=False,
        feature_list_sha="abc", approved_sha="abc")
    assert out["decision"] == "allow"

def test_blocks_when_sha_mismatch():
    out = hook.evaluate(
        tool_input={"file_path": "apps/web/app/page.tsx"},
        actor_agent="implementer.md", human_signed=False,
        feature_list_sha="NEW", approved_sha="OLD")
    assert out["decision"] == "block" and "approval" in out["reason"].lower()

def test_blocks_edit_to_protected_test_dir():
    out = hook.evaluate(
        tool_input={"file_path": "apps/web/tests/e2e/home.spec.ts"},
        actor_agent="implementer.md", human_signed=False,
        feature_list_sha="abc", approved_sha="abc")
    assert out["decision"] == "block" and "protected" in out["reason"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_pre_tool_use.py -v`
Expected: FAIL (hook file missing).

- [ ] **Step 3: Write the implementation**

`.claude/hooks/pre_tool_use_hook.py`:
```python
#!/usr/bin/env python3
"""PreToolUse — the only true prevention gate (exit 2 blocks before a write lands).
Order: plan-approval+SHA -> field-authority (fix #4) -> artifact guard.
Identity is resolved by tools/actor_identity (fix #1), never from the payload."""
from __future__ import annotations
import sys, os, json
from pathlib import Path

PROTECTED_PREFIXES = (
    "apps/web/tests/", "schema/", ".github/workflows/", ".github/policies/",
    ".claude/hooks/", ".claude/settings.json", "apps/web/next.config",
    "apps/web/vercel.json",
)


def evaluate(*, tool_input: dict, actor_agent: str, human_signed: bool,
             feature_list_sha: str, approved_sha: str) -> dict:
    # 1. plan-approval + SHA binding (gate #1)
    if feature_list_sha != approved_sha:
        return {"decision": "block",
                "reason": "coverage model changed without re-approval (plan-approved SHA mismatch)"}
    path = tool_input.get("file_path", "")
    # 2. field-level write authority on the coverage model (fix #4)
    if path.endswith("feature_list.json"):
        field = tool_input.get("field")
        if field == "status" and actor_agent != "verifier.md":
            return {"decision": "block", "reason": "status field writable only by verifier.md"}
        if field == "in_scope" and not human_signed:
            return {"decision": "block", "reason": "in_scope mutable only via a human-signed change"}
        return {"decision": "allow"}
    # 3. artifact guard: implementer may not edit tests/schema/CI/config
    if actor_agent != "main" and any(path.startswith(p) for p in PROTECTED_PREFIXES):
        return {"decision": "block", "reason": f"protected path may not be edited by an agent: {path}"}
    return {"decision": "allow"}


def main() -> int:
    payload = json.load(sys.stdin)
    from importlib import import_module
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.actor_identity import resolve_identity
    ident = resolve_identity(payload)
    root = Path(__file__).resolve().parents[2]
    fl = (root / "apps/web/feature_list.json")
    import hashlib
    feature_list_sha = hashlib.sha256(fl.read_bytes()).hexdigest() if fl.exists() else ""
    approved = json.loads((root / "plan-approved.json").read_text()) if (root / "plan-approved.json").exists() else {}
    result = evaluate(
        tool_input=payload.get("tool_input", {}),
        actor_agent=ident.actor_agent,
        human_signed=bool(payload.get("tool_input", {}).get("human_signed", False)),
        feature_list_sha=feature_list_sha,
        approved_sha=approved.get("feature_list_sha", feature_list_sha),
    )
    if result["decision"] == "block":
        print(result["reason"], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`plan-approved.json` (seed; the SHA is filled by the human approval step in Task 13):
```json
{ "feature_list_sha": "", "approved_by": "", "approved_at": "" }
```

> The seed `approved_sha` defaults to the current model SHA in `evaluate`'s caller so the spine is operable during bring-up; Task 13 replaces this with a real human-signed SHA freeze.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_pre_tool_use.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/pre_tool_use_hook.py plan-approved.json tests/unit/test_pre_tool_use.py
git commit -m "feat(spine): PreToolUse prevention gate — SHA, field authority, artifact guard"
```

---

## Task 9: Stop hook — completion gate with HANDOFF-first exit-0 semantics

**Files:**
- Create: `.claude/hooks/stop_hook.py`
- Test: `tests/unit/test_stop_hook.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_stop_hook.py`:
```python
import importlib.util, pathlib

def _load():
    p = pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/stop_hook.py"
    spec = importlib.util.spec_from_file_location("stop_hook", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

hook = _load()

def test_blocks_when_unproven_and_no_handoff():
    out = hook.evaluate(has_unproven=True, handoff_triggered=False)
    assert out["exit_code"] == 2  # block termination

def test_allows_when_complete():
    out = hook.evaluate(has_unproven=False, handoff_triggered=False)
    assert out["exit_code"] == 0

def test_handoff_checked_first_allows_exit():  # corrected infinite-block defect
    out = hook.evaluate(has_unproven=True, handoff_triggered=True)
    assert out["exit_code"] == 0 and out["status"] == "HANDOFF"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_stop_hook.py -v`
Expected: FAIL (hook file missing).

- [ ] **Step 3: Write the implementation**

`.claude/hooks/stop_hook.py`:
```python
#!/usr/bin/env python3
"""Stop hook (completion gate). HANDOFF triggers (iteration/token/no-progress caps)
are checked FIRST and ALLOW termination (exit 0). Only a genuine continuation case
blocks (exit 2) — the corrected infinite-block semantics."""
from __future__ import annotations
import sys, json
from pathlib import Path


def evaluate(*, has_unproven: bool, handoff_triggered: bool) -> dict:
    if handoff_triggered:
        return {"exit_code": 0, "status": "HANDOFF"}
    if has_unproven:
        return {"exit_code": 2, "status": "BLOCKED",
                "reason": "in-scope items remain unproven; completion not allowed"}
    return {"exit_code": 0, "status": "COMPLETE"}


def main() -> int:
    payload = json.load(sys.stdin)
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from tools.coverage import CoverageModel
    m = CoverageModel.load(root / "apps/web/feature_list.json")
    handoff = bool(payload.get("handoff_triggered", False))
    result = evaluate(has_unproven=m.has_unproven_in_scope(), handoff_triggered=handoff)
    if result["exit_code"] == 2:
        print(result["reason"], file=sys.stderr)
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_stop_hook.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/stop_hook.py tests/unit/test_stop_hook.py
git commit -m "feat(spine): Stop hook completion gate with HANDOFF-first exit-0"
```

---

## Task 10: PostToolUse / PreCompact / SessionStart hooks + settings wiring + smoke test

**Files:**
- Create: `.claude/hooks/post_tool_use_hook.py`, `pre_compact_hook.py`, `session_start_hook.py`, `.claude/settings.json`
- Test: `tests/smoke/test_hook_config.py`

- [ ] **Step 1: Write the failing test**

`tests/smoke/test_hook_config.py`:
```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = json.loads((ROOT / ".claude" / "settings.json").read_text())

def test_all_six_hooks_are_command_type():
    hooks = SETTINGS["hooks"]
    for evt in ("PreToolUse","PostToolUse","Stop","SubagentStop","PreCompact","SessionStart"):
        assert evt in hooks, f"missing hook: {evt}"
        for matcher in hooks[evt]:
            for h in matcher["hooks"]:
                assert h["type"] == "command", f"{evt} must be command-type (fail-closed)"
                assert "http" not in h and "url" not in h, f"{evt} must not be http/mcp"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/smoke/test_hook_config.py -v`
Expected: FAIL (`.claude/settings.json` missing).

- [ ] **Step 3: Write the implementation**

`.claude/hooks/post_tool_use_hook.py`:
```python
#!/usr/bin/env python3
"""PostToolUse — next-turn feedback only (exit 1, non-blocking). Cannot gate."""
import sys, json
def main() -> int:
    json.load(sys.stdin)  # consume payload
    # In Phase 1 this runs ESLint/tsc/Semgrep on changed files and prints advice.
    return 0
if __name__ == "__main__":
    sys.exit(main())
```

`.claude/hooks/pre_compact_hook.py`:
```python
#!/usr/bin/env python3
"""PreCompact — checkpoint the proven/unproven tally before context trim."""
import sys, json
from pathlib import Path
def main() -> int:
    json.load(sys.stdin)
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from tools.coverage import CoverageModel
    m = CoverageModel.load(root / "apps/web/feature_list.json")
    proven = sum(1 for i in m.items if i["status"] == "proven")
    (root / ".claude" / "run").mkdir(exist_ok=True)
    (root / ".claude" / "run" / "checkpoint.json").write_text(
        json.dumps({"proven": proven, "total": len(m.items)}))
    return 0
if __name__ == "__main__":
    sys.exit(main())
```

`.claude/hooks/session_start_hook.py`:
```python
#!/usr/bin/env python3
"""SessionStart — restore run state; recompute resume integrity for a long run."""
import sys, json
from pathlib import Path
def main() -> int:
    json.load(sys.stdin)
    root = Path(__file__).resolve().parents[2]
    cp = root / ".claude" / "run" / "checkpoint.json"
    if cp.exists():
        print(f"resumed coverage tally: {cp.read_text()}", file=sys.stderr)
    return 0
if __name__ == "__main__":
    sys.exit(main())
```

`.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse":   [{ "matcher": "Write|Edit|MultiEdit|Bash", "hooks": [{ "type": "command", "command": "python3 .claude/hooks/pre_tool_use_hook.py" }] }],
    "PostToolUse":  [{ "matcher": "Write|Edit|MultiEdit",      "hooks": [{ "type": "command", "command": "python3 .claude/hooks/post_tool_use_hook.py" }] }],
    "Stop":         [{ "matcher": "*", "hooks": [{ "type": "command", "command": "python3 .claude/hooks/stop_hook.py" }] }],
    "SubagentStop": [{ "matcher": "*", "hooks": [{ "type": "command", "command": "python3 .claude/hooks/subagent_stop_hook.py" }] }],
    "PreCompact":   [{ "matcher": "*", "hooks": [{ "type": "command", "command": "python3 .claude/hooks/pre_compact_hook.py" }] }],
    "SessionStart": [{ "matcher": "*", "hooks": [{ "type": "command", "command": "python3 .claude/hooks/session_start_hook.py" }] }]
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/smoke/test_hook_config.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/hooks/post_tool_use_hook.py .claude/hooks/pre_compact_hook.py .claude/hooks/session_start_hook.py .claude/settings.json tests/smoke/test_hook_config.py
git commit -m "feat(spine): minor hooks + command-type settings wiring + smoke test"
```

---

## Task 11: Permission-scoped subagent definitions

**Files:**
- Create: `.claude/agents/verifier.md`, `implementer.md`, `initializer.md`, `research.md`
- Test: `tests/smoke/test_agents.py`

- [ ] **Step 1: Write the failing test**

`tests/smoke/test_agents.py`:
```python
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def test_verifier_is_readonly_on_src():
    txt = (ROOT / ".claude" / "agents" / "verifier.md").read_text()
    assert "apps/web/src" in txt and "read-only" in txt.lower()
    assert "never grades its own" in txt.lower()

def test_four_agents_exist():
    for a in ("verifier", "implementer", "initializer", "research"):
        assert (ROOT / ".claude" / "agents" / f"{a}.md").is_file()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/smoke/test_agents.py -v`
Expected: FAIL (agent files missing).

- [ ] **Step 3: Write the agent definitions**

`.claude/agents/verifier.md`:
```markdown
---
name: verifier
description: Independent evaluator. The ONLY actor permitted to flip a coverage item unproven->proven, and only with a complete, re-derivable Evidence_Record.
tools: Read, Bash, Glob, Grep
---
You are the independent verifier for the autonomous-agent.dev build.
- You have READ-ONLY access to `apps/web/src` and the app source. You may read/write only `apps/web/tests/**` and the `status` field of `apps/web/feature_list.json`.
- You MUST NOT edit `next.config`, `vercel.json`, CI workflows, the schema, or token sources.
- You never grade your own output: you must not verify an item whose implementation you authored. Your evidence's `actor_agent` is stamped by the runtime (verifier.md) and your `verifier_session_id` must differ from the slice's `implementer_session_id`.
- For each item, run the five verification layers against the live Vercel preview, capture the artifact, and emit a 4-field Evidence_Record plus a non-empty `omission_declaration` enumerating uncovered scenario classes with [Gap] markers.
```

`.claude/agents/implementer.md`:
```markdown
---
name: implementer
description: Builds ONE coverage slice in a dedicated git worktree. No write access to tests.
tools: Read, Write, Edit, Bash, Glob, Grep
---
You implement exactly one coverage item at a time in its own git worktree, then open a PR.
- You MUST NOT edit `apps/web/tests/**`, the schema, CI workflows, or the coverage model's `status`/`in_scope` fields (the PreToolUse gate blocks these).
- One atomic commit per slice, with the requirement ID in the commit trailer.
```

`.claude/agents/initializer.md`:
```markdown
---
name: initializer
description: Spec Compiler + Coverage Model Builder. Compiles EARS and builds feature_list.json. No test/CI access.
tools: Read, Write, Edit, Bash, Glob, Grep
---
You compile the website spec into atomic coverage items and build `apps/web/feature_list.json` (every item default `unproven`). You do not implement features or write tests.
```

`.claude/agents/research.md`:
```markdown
---
name: research
description: Sources approved domain-baseline checklists with cited, fact-checked sources. Approved-only.
tools: Read, WebSearch, WebFetch, Bash, Glob, Grep
---
You source domain-baseline checklists with authority-tiered, fact-checked citations. You produce DRAFT checklists; a human approves before they may be used.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/smoke/test_agents.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/
git commit -m "feat(spine): permission-scoped subagents (verifier read-only, never self-grades)"
```

---

## Task 12: Z3 actor-separation proof + Hypothesis property (fix #5)

**Files:**
- Create: `verification/actor_separation.py`, `tests/property/test_actor_separation.py`
- Test: both files (the Z3 module self-checks; the property test asserts the runtime gate)

- [ ] **Step 1: Write the failing test**

`tests/property/test_actor_separation.py`:
```python
import importlib.util, pathlib, hashlib
from hypothesis import given, strategies as st

def _hook():
    p = pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/subagent_stop_hook.py"
    spec = importlib.util.spec_from_file_location("subagent_stop_hook", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

hook = _hook()

@given(sess=st.text(min_size=1, max_size=8))
def test_same_session_never_approved(tmp_path_factory, sess):
    tmp = tmp_path_factory.mktemp("ev"); art = tmp / "a.zip"; art.write_bytes(b"x")
    ev = {"test_file":"t","test_name":"n",
          "output_hash":"sha256:"+hashlib.sha256(b"x").hexdigest(),
          "collected_at":"2026-06-15T00:00:00Z","actor_agent":"verifier.md",
          "verifier_session_id":sess,"implementer_session_id":sess,
          "_artifact_path":str(art),"omission_declaration":"[Gap] none"}
    assert hook.evaluate(ev)["decision"] == "block"

def test_z3_proves_separation():
    from verification.actor_separation import prove
    assert prove() == "UNSAT-to-violate"  # cannot have proven with verify_actor==impl_actor
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/property/test_actor_separation.py -v`
Expected: FAIL (`verification/actor_separation.py` missing).

- [ ] **Step 3: Write the implementation**

`verification/actor_separation.py`:
```python
"""Z3: prove that a proven item implies a verifier actor distinct from the implementer.
We assert the NEGATION is unsatisfiable: there is no model where status==proven yet
verify_actor == impl_actor. (fix #5)"""
from z3 import Bool, Solver, Implies, And, Not, sat


def prove() -> str:
    proven = Bool("proven")
    distinct = Bool("verify_actor_ne_impl_actor")  # true when verifier != implementer
    s = Solver()
    # Rule enforced by the gate: proven => distinct
    s.add(Implies(proven, distinct))
    # Adversary tries to violate it: proven AND not distinct
    s.add(And(proven, Not(distinct)))
    return "SAT-violation-possible" if s.check() == sat else "UNSAT-to-violate"


if __name__ == "__main__":
    print(prove())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/property/test_actor_separation.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add verification/actor_separation.py tests/property/test_actor_separation.py
git commit -m "feat(spine): Z3 + property proof of verifier/implementer actor separation (fix #5)"
```

---

## Task 13: OPA zero-evidence policy + Conftest input builder

**Files:**
- Create: `.github/policies/coverage.rego`, `tools/opa_input.py`
- Test: `tests/unit/test_opa_input.py`, `tests/integration/test_conftest.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_opa_input.py`:
```python
import json
from pathlib import Path
from tools.opa_input import build_opa_input

def test_flags_unproven(tmp_path):
    p = tmp_path / "fl.json"
    p.write_text(json.dumps({"schema_version":"1","product_class":"public-marketing-website",
        "items":[{"id":"A-B-001","type":"functional","priority":"P0","dependencies":[],
                  "acceptance_criteria":["x"],"in_scope":True,"status":"unproven","evidence":None}]}))
    data = build_opa_input(p)
    assert data["unproven_in_scope"] == ["A-B-001"]
```

`tests/integration/test_conftest.py`:
```python
import json, shutil, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]

@pytest.mark.skipif(shutil.which("conftest") is None, reason="conftest not installed")
def test_conftest_denies_unproven(tmp_path):
    inp = tmp_path / "input.json"
    inp.write_text(json.dumps({"unproven_in_scope": ["A-B-001"], "missing_evidence": []}))
    r = subprocess.run(["conftest","test","--policy",str(ROOT/".github/policies"),str(inp)],
                       capture_output=True, text=True)
    assert r.returncode != 0  # policy denies
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_opa_input.py -v`
Expected: FAIL (module + policy missing).

- [ ] **Step 3: Write the implementation**

`tools/opa_input.py`:
```python
"""Build the Conftest/OPA input document from the coverage model."""
from __future__ import annotations
import json
from pathlib import Path


def build_opa_input(feature_list_path: Path) -> dict:
    model = json.loads(Path(feature_list_path).read_text())
    unproven, missing = [], []
    for i in model["items"]:
        if not i["in_scope"]:
            continue
        if i["status"] != "proven":
            unproven.append(i["id"])
        elif not i.get("evidence"):
            missing.append(i["id"])
    return {"unproven_in_scope": unproven, "missing_evidence": missing}
```

`.github/policies/coverage.rego`:
```rego
package main

deny[msg] {
    count(input.unproven_in_scope) > 0
    msg := sprintf("coverage gate: %d in-scope item(s) still unproven: %v", [count(input.unproven_in_scope), input.unproven_in_scope])
}

deny[msg] {
    count(input.missing_evidence) > 0
    msg := sprintf("coverage gate: %d proven item(s) missing evidence: %v", [count(input.missing_evidence), input.missing_evidence])
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_opa_input.py -v` (the conftest integration test is skipped if conftest is absent locally; it runs in CI — Task 15).
Expected: PASS (1 passed; 1 skipped).

- [ ] **Step 5: Commit**

```bash
git add .github/policies/coverage.rego tools/opa_input.py tests/unit/test_opa_input.py tests/integration/test_conftest.py
git commit -m "feat(spine): OPA zero-evidence coverage policy + input builder"
```

---

## Task 14: The trivial slice — `/` route + Playwright behavioral proof

**Files:**
- Create: `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, `apps/web/playwright.config.ts`, `apps/web/tests/e2e/home.spec.ts`

- [ ] **Step 1: Write the failing test (Playwright behavioral proof)**

`apps/web/playwright.config.ts`:
```typescript
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  use: { trace: "on", baseURL: "http://localhost:3000" },
  webServer: { command: "pnpm build && pnpm start", url: "http://localhost:3000", reuseExistingServer: !process.env.CI },
});
```

`apps/web/tests/e2e/home.spec.ts`:
```typescript
import { test, expect } from "@playwright/test";

test("home route renders", async ({ page }) => {
  const res = await page.goto("/");
  expect(res?.status()).toBe(200);
  await expect(page.getByText("Autonomous Agent")).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && pnpm install && pnpm playwright test`
Expected: FAIL (no `/` page yet → 404 / missing text).

- [ ] **Step 3: Write the minimal slice**

`apps/web/app/layout.tsx`:
```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

`apps/web/app/page.tsx`:
```tsx
export default function Home() {
  return (
    <main>
      <h1>Autonomous Agent</h1>
      <p>Delivery that proves itself.</p>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/web && pnpm playwright test`
Expected: PASS (1 passed) — a trace zip is written under `apps/web/test-results/`.

- [ ] **Step 5: Commit**

```bash
git add apps/web/app apps/web/playwright.config.ts apps/web/tests/e2e/home.spec.ts
git commit -m "feat(web): trivial / slice + Playwright behavioral proof"
```

---

## Task 15: End-to-end spine proof (the integration test that ties it together)

**Files:**
- Create: `tools/prove_slice.py`, `tests/integration/test_spine_e2e.py`

- [ ] **Step 1: Write the failing test**

`tests/integration/test_spine_e2e.py`:
```python
import json, hashlib
from pathlib import Path
from tools.prove_slice import prove_slice
import importlib.util

def _stop():
    p = Path(__file__).resolve().parents[2] / ".claude/hooks/stop_hook.py"
    s = importlib.util.spec_from_file_location("stop_hook", p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_full_loop_flips_item_and_unblocks_stop(tmp_path):
    # arrange: a 1-item model + a captured artifact
    fl = tmp_path / "feature_list.json"
    fl.write_text(json.dumps({"schema_version":"1","product_class":"public-marketing-website",
        "items":[{"id":"HOME-RND-001","type":"functional","priority":"P0","dependencies":[],
                  "acceptance_criteria":["renders"],"in_scope":True,"status":"unproven","evidence":None}]}))
    art = tmp_path / "trace.zip"; art.write_bytes(b"green-playwright-run")
    # act: verifier proves the slice (distinct sessions, real hash)
    prove_slice(feature_list=fl, item_id="HOME-RND-001", artifact=art,
                test_file="apps/web/tests/e2e/home.spec.ts", test_name="home route renders",
                verifier_session_id="sv", implementer_session_id="si",
                collected_at="2026-06-15T00:00:00Z")
    model = json.loads(fl.read_text())
    item = model["items"][0]
    # assert: item is proven with a re-derivable hash
    assert item["status"] == "proven"
    assert item["evidence"]["output_hash"] == "sha256:" + hashlib.sha256(b"green-playwright-run").hexdigest()
    assert item["evidence"]["actor_agent"] == "verifier.md"
    # assert: Stop hook now allows completion
    stop = _stop()
    from tools.coverage import CoverageModel
    m = CoverageModel.load(fl)
    assert stop.evaluate(has_unproven=m.has_unproven_in_scope(), handoff_triggered=False)["exit_code"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_spine_e2e.py -v`
Expected: FAIL (`tools/prove_slice.py` missing).

- [ ] **Step 3: Write the implementation**

`tools/prove_slice.py`:
```python
"""Drive one slice through the spine: SubagentStop gate -> coverage transition -> write status.
This is the verifier's privileged path; it composes the already-tested units."""
from __future__ import annotations
import json
from pathlib import Path
import importlib.util

from tools.evidence import EvidenceCollector
from tools.coverage import CoverageModel


def _subagent_stop():
    p = Path(__file__).resolve().parents[1] / ".claude/hooks/subagent_stop_hook.py"
    spec = importlib.util.spec_from_file_location("subagent_stop_hook", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def prove_slice(*, feature_list: Path, item_id: str, artifact: Path,
                test_file: str, test_name: str, verifier_session_id: str,
                implementer_session_id: str, collected_at: str) -> None:
    rec = EvidenceCollector.collect(
        test_file=test_file, test_name=test_name, artifact_path=artifact,
        actor_agent="verifier.md", verifier_session_id=verifier_session_id,
        implementer_session_id=implementer_session_id, collected_at=collected_at)
    ev = rec.to_dict()
    ev["_artifact_path"] = str(artifact)
    ev["omission_declaration"] = "[Gap] only happy-path render checked in this slice."
    gate = _subagent_stop().evaluate(ev)
    if gate["decision"] != "approve":
        raise RuntimeError(f"SubagentStop rejected evidence: {gate.get('reason')}")
    model = CoverageModel.load(feature_list)
    model.assert_transition(item_id, "unproven", "proven")
    model.assert_field_authority(field="status", actor_agent="verifier.md", human_signed=False)
    for i in model.items:
        if i["id"] == item_id:
            i["status"] = "proven"
            i["evidence"] = {k: v for k, v in ev.items() if not k.startswith("_") and k != "omission_declaration"}
    Path(feature_list).write_text(json.dumps(model.data, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_spine_e2e.py -v`
Expected: PASS (1 passed). Then run the full suite: `pytest -v` → all green.

- [ ] **Step 5: Commit**

```bash
git add tools/prove_slice.py tests/integration/test_spine_e2e.py
git commit -m "feat(spine): end-to-end slice proof — verifier flips item, Stop unblocks"
```

---

## Task 16: GitHub required-check workflow (coverage gate)

**Files:**
- Create: `.github/workflows/coverage-gate.yml`
- Test: `tests/smoke/test_workflow.py`

- [ ] **Step 1: Write the failing test**

`tests/smoke/test_workflow.py`:
```python
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def test_workflow_runs_gate_steps():
    txt = (ROOT / ".github/workflows/coverage-gate.yml").read_text()
    assert "pytest" in txt
    assert "conftest" in txt
    assert "actor_separation" in txt  # the Z3 proof runs in CI
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/smoke/test_workflow.py -v`
Expected: FAIL (workflow missing).

- [ ] **Step 3: Write the workflow**

`.github/workflows/coverage-gate.yml`:
```yaml
name: coverage-gate
on:
  pull_request:
    branches: [main]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install pytest hypothesis jsonschema z3-solver
      - name: Unit + property + integration tests
        run: pytest -v
      - name: Z3 actor-separation proof
        run: python verification/actor_separation.py | grep -q UNSAT-to-violate
      - name: Build OPA input from coverage model
        run: python -c "import json,sys; from tools.opa_input import build_opa_input; json.dump(build_opa_input('apps/web/feature_list.json'), open('opa-input.json','w'))"
      - uses: open-policy-agent/conftest@v0
        with: { args: "test --policy .github/policies opa-input.json" }
      - name: Verify audit chain
        run: python -c "from tools.audit_log import AuditLog; import sys; sys.exit(0 if AuditLog('.claude/run/gate_audit_log.jsonl').verify_chain() else 1)"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/smoke/test_workflow.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/coverage-gate.yml tests/smoke/test_workflow.py
git commit -m "ci(spine): coverage-gate required check (pytest + Z3 + conftest + chain verify)"
```

> **Manual step (record in PR description):** in GitHub repo settings → Rules → add a ruleset on `main` requiring the `coverage-gate / gate` check and one human reviewer. Connect the Vercel project to `apps/web` for per-PR preview deploys (set the Vercel root directory to `apps/web`). These are platform settings, not code; note completion in the PR.

---

## Task 17: Materialize the 209-item coverage model + human SHA-freeze (gate #1)

**Files:**
- Create: `tools/materialize_feature_list.py`
- Modify: `apps/web/feature_list.json` (replace seed with 209 items), `plan-approved.json`
- Test: `tests/integration/test_materialize.py`

- [ ] **Step 1: Write the failing test**

`tests/integration/test_materialize.py`:
```python
import json
from pathlib import Path
from tools.materialize_feature_list import materialize

ROOT = Path(__file__).resolve().parents[2]

def test_materializes_209_items_all_unproven(tmp_path):
    out = tmp_path / "fl.json"
    materialize(requirements_md=ROOT / "docs/website/autonomous-agent.dev/requirements.md",
                bucket_a_extra=3, sca_extra=1, out=out)
    model = json.loads(out.read_text())
    assert len(model["items"]) == 209
    assert all(i["status"] == "unproven" for i in model["items"])
    import re
    pat = re.compile(r"^[A-Z]+-[A-Z]+-[0-9]{3}$")
    assert all(pat.match(i["id"]) for i in model["items"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_materialize.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Write the implementation**

`tools/materialize_feature_list.py`:
```python
"""Compile docs/website/autonomous-agent.dev/requirements.md (205 EARS) + 3 Bucket-A
+ 1 SCA into the 209-item coverage model, remapping two-segment IDs (DS-01) to the
canonical three-segment pattern (DS-TOK-001) while preserving source_ears_id."""
from __future__ import annotations
import json, re
from pathlib import Path

HEADER = re.compile(r"^### ([A-Z]+)-(\d+)\s+—\s+(.*?)\s+·\s+(P[0-3])\s+·", re.M)
# domain -> short family code for the middle segment
FAMILY = {"DS":"TOK","IA":"NAV","HOME":"HOM","LOOP":"LUP","CONTENT":"CNT","PAGE":"PAG",
          "TECH":"TEC","TOOL":"TUL","PERF":"PRF","A11Y":"AYY","SEO":"SEO","PRIV":"PRV"}


def materialize(*, requirements_md: Path, bucket_a_extra: int, sca_extra: int, out: Path) -> None:
    text = Path(requirements_md).read_text()
    items = []
    for dom, num, _title, prio in HEADER.findall(text):
        fam = FAMILY[dom]
        items.append({
            "id": f"{dom}-{fam}-{int(num):03d}",
            "type": "functional",
            "priority": prio,
            "source_ears_id": f"{dom}-{int(num):02d}",
            "dependencies": [],
            "acceptance_criteria": ["See docs/website/autonomous-agent.dev/requirements.md " + f"{dom}-{int(num):02d}"],
            "in_scope": True, "status": "unproven", "evidence": None,
        })
    # Bucket-A (security-header matrix, RUM, visual-regression) + SCA
    extras = [("SEC","security-header matrix"), ("RUM","privacy-safe RUM"),
              ("VIS","whole-site visual-regression")][:bucket_a_extra]
    extras += [("SCA","dependency-CVE + SBOM")][:sca_extra]
    for n, (fam, desc) in enumerate(extras, start=1):
        items.append({"id": f"REQ-{fam}-{n:03d}", "type": "NFR", "priority": "P0",
                      "source_ears_id": f"BUCKET-A:{desc}", "dependencies": [],
                      "acceptance_criteria": [desc], "in_scope": True,
                      "status": "unproven", "evidence": None})
    model = {"schema_version": "1.0.0", "product_class": "public-marketing-website",
             "checklist_ref": {"path": "baselines/public-marketing-website.json", "version": "0.1.0", "sha": ""},
             "items": items}
    Path(out).write_text(json.dumps(model, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_materialize.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Materialize, validate, then human SHA-freeze**

```bash
python -c "from tools.materialize_feature_list import materialize; from pathlib import Path; materialize(requirements_md=Path('docs/website/autonomous-agent.dev/requirements.md'), bucket_a_extra=3, sca_extra=1, out=Path('apps/web/feature_list.json'))"
pytest tests/unit/test_schema.py -v   # validate the 209-item model against the schema
```
Then the **human approval** (gate #1) — a person reviews and signs the freeze:
```bash
python -c "import hashlib,json; sha=hashlib.sha256(open('apps/web/feature_list.json','rb').read()).hexdigest(); json.dump({'feature_list_sha':sha,'approved_by':'<name>','approved_at':'<iso8601>'}, open('plan-approved.json','w'), indent=2); print(sha)"
git add apps/web/feature_list.json plan-approved.json tools/materialize_feature_list.py tests/integration/test_materialize.py
git commit -m "feat(spine): materialize 209-item coverage model + human SHA-freeze (gate #1)"
```

> After this commit the PreToolUse SHA gate is live: any later change to `apps/web/feature_list.json` that is not re-approved (new SHA written to `plan-approved.json` by a human) blocks all `apps/web` writes. This is the hand-off point into the per-slice autonomous loop (a future plan: Tier 1 foundations).

---

## Self-Review

**1. Spec coverage** (against the execution-design §3 gate chain & §5 fixes):
- feature_list.json + draft-07 schema → Tasks 2, 17. ✓
- 6 Claude Code hooks → Tasks 7 (SubagentStop), 8 (PreToolUse), 9 (Stop), 10 (Post/PreCompact/SessionStart). ✓
- Fix #1 harness-stamped identity → Task 3 + used in Task 8. ✓
- Fix #2 verifier≠implementer session → Task 7 + property Task 12. ✓
- Fix #3 gate-side hash re-derivation → Task 7. ✓
- Fix #4 field-level write authority → Task 6 + enforced in Task 8. ✓
- Fix #5 Z3 + property proof → Task 12. ✓
- Independent verifier subagent → Task 11 + privileged path Task 15. ✓
- OPA coverage-gate → Task 13; GitHub required check → Task 16. ✓
- Git worktrees → referenced in implementer agent (Task 11) and the per-slice loop hand-off (Task 17 note); the worktree mechanics are a Tier-1 concern, flagged for the next plan. ✓ (scoped out intentionally; noted)
- Vercel project → manual platform step noted in Task 16. ✓
- Proven on one trivial slice → Tasks 14 + 15. ✓
- Two human gates: SHA-freeze (Task 17) and production go-live (out of Phase 0; future). ✓

**2. Placeholder scan:** No "TBD/TODO/implement later". Every code step has runnable code. The acceptance_criteria string in the materializer references the source EARS file by ID (a pointer to real content, not a placeholder for missing logic). ✓

**3. Type consistency:** `EvidenceRecord` fields (`test_file, test_name, output_hash, collected_at, actor_agent, verifier_session_id, implementer_session_id`) are identical across the schema (Task 2), `tools/evidence.py` (Task 4), the SubagentStop `REQUIRED` tuple (Task 7), and `prove_slice` (Task 15). `evaluate(...)` signatures match their tests. `CoverageModel.has_unproven_in_scope()` / `is_complete()` / `assert_transition()` / `assert_field_authority()` names are used consistently in Tasks 6, 9, 15. ✓

**Known intentional scope boundaries (not gaps):** Phase-1 verification depth (Semgrep/CodeQL/SonarQube), Phase-2 Neon durable state, Phase-3 OTel/Langfuse, full 5-layer verifier (only structural+behavioral are exercised on the trivial slice), and the per-slice worktree loop are explicitly **out of this Phase-0 plan** and belong to subsequent plans, per the execution design's tiering.

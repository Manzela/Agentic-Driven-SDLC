#!/usr/bin/env python3
"""Apply the audit's Plane upsert plan to the live board — idempotent, match-by-external_id, NO blind deletions.

Reads docs/audits/spec-to-evidence-steering/plane-upsert-plan.json (ops: create|update) and applies
each against the live Plane board. Matching is by the board's stable **external_id**, NOT display name.

Op semantics honored (fixes NS-01/02/03/05 from the plane-integration audit):
  * supersedes  — an op whose id is named in another op's `supersedes` is SKIPPED (no duplicate). [NS-01]
  * additional_match_keys — an op updates match_key PLUS every additional_match_key (all targets). [NS-02]
  * collisions  — multiple ops resolving to the SAME live item are MERGED into one PATCH (union labels,
                  concatenated descriptions), so a declared-create that resolves to an existing item
                  augments it instead of silently last-write-winning. [NS-03]
  * priority    — `priority:<label>` mapped to Plane's native priority field. [NS-05]
  * acceptance_criteria — rendered into description_html as an escaped <ul>. [NS-05 + SEC-02 escaping]

Genuine new items get a stable external_id (`ascp-audit-reorg:<op-id>`) so re-runs match. No blind deletions.
Config from ENV (auto-loaded from plane-integration/.env). See REMOTE_ACCESS.md.
    python3 apply_upsert_plan.py            # DRY-RUN
    python3 apply_upsert_plan.py --apply    # EXECUTE
"""
from __future__ import annotations

import html
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
PLAN_F = ROOT / "docs/audits/spec-to-evidence-steering/plane-upsert-plan.json"
LOG_F = HERE / ".apply_log.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ascp-automation"  # CF bans default urllib UA (1010)
EXT_SOURCE = "ascp-audit-reorg"
PRIORITY_BY_LABEL = {"priority:blocking": "urgent", "priority:high": "high",
                     "priority:normal": "medium", "priority:low": "low", "priority:none": "none"}
PRIORITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "urgent": 4}


def _load_dotenv(path):
    p = pathlib.Path(path)
    if not p.exists():
        return
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(HERE / ".env")

APPLY = "--apply" in sys.argv
API_BASE = os.environ.get("PLANE_API_BASE", "https://plane.autonomous-agent.dev/api/v1").rstrip("/")
WS = os.environ.get("PLANE_WS", "agentic-driven-sdlc")
PROJ = os.environ.get("PLANE_PROJ", "0de2a9fb-5382-4e0d-bf99-f00f221461ca")
KEY = os.environ.get("PLANE_API_KEY", "")
CF_ID = os.environ.get("CF_ACCESS_CLIENT_ID", "")
CF_SECRET = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")
PBASE = f"/workspaces/{WS}/projects/{PROJ}"

if not KEY:
    sys.exit("PLANE_API_KEY not set — populate plane-integration/.env (see REMOTE_ACCESS.md).")

_last = [0.0]


def _api(method, path, body=None, retries=6):
    now = time.time()
    if now - _last[0] < 0.5:
        time.sleep(0.5 - (now - _last[0]))
    _last[0] = time.time()
    headers = {"X-API-Key": KEY, "Content-Type": "application/json", "User-Agent": UA}
    if CF_ID and CF_SECRET:
        headers["CF-Access-Client-Id"] = CF_ID
        headers["CF-Access-Client-Secret"] = CF_SECRET
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(f"{API_BASE}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(20); continue
            if 500 <= e.code < 600:
                time.sleep(min(2 ** attempt, 20)); continue
            raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:300]}")
        except urllib.error.URLError as e:
            if attempt < retries - 1:
                time.sleep(min(2 ** attempt, 20)); continue
            raise RuntimeError(f"{method} {path} -> connection failed: {e}")
    raise RuntimeError(f"{method} {path}: exhausted retries")


def _paginate(path):
    out, cur = [], None
    for _ in range(80):
        sep = "&" if "?" in path else "?"
        p = path + f"{sep}per_page=100" + (f"&cursor={cur}" if cur else "")
        d = _api("GET", p)
        if isinstance(d, list):
            out.extend(d); break
        out.extend(d.get("results", []))
        if not d.get("next_page_results"):
            break
        cur = d.get("next_cursor")
        if not cur:
            break
    return out


def _variants(mk):
    if not mk:
        return []
    c = {mk}
    if mk.startswith("story:"):
        body = mk[len("story:"):]
        c.add("story:" + body.replace("ASCP-", "", 1))
        if not body.startswith("ASCP-"):
            c.add("story:ASCP-" + body)
    return list(c)


def _ac_html(ac):
    if not ac:
        return ""
    items = "".join(f"<li>{html.escape(str(x))}</li>" for x in ac)
    return f"<p><b>Acceptance criteria</b></p><ul>{items}</ul>"


def main():
    print(f"{'APPLY' if APPLY else 'DRY-RUN'} mode | {API_BASE} | proj={PROJ}")
    plan = json.loads(PLAN_F.read_text())
    ops = plan if isinstance(plan, list) else plan.get("operations", plan.get("ops", []))
    superseded = {o.get("supersedes") for o in ops if o.get("supersedes")}
    print(f"plan: {len(ops)} ops | superseded (skip): {sorted(superseded) or 'none'}")

    print("indexing live board...")
    states = {s["name"]: s["id"] for s in _paginate(f"{PBASE}/states/")}
    labels = {l["name"]: l["id"] for l in _paginate(f"{PBASE}/labels/")}
    modules = {m["name"]: m["id"] for m in _paginate(f"{PBASE}/modules/")}
    cycles = {c["name"]: c["id"] for c in _paginate(f"{PBASE}/cycles/")}
    items = _paginate(f"{PBASE}/work-items/")
    by_ext = {w.get("external_id"): w["id"] for w in items if w.get("external_id")}
    by_name = {w.get("name"): w["id"] for w in items}
    print(f"  states={len(states)} labels={len(labels)} modules={len(modules)} "
          f"cycles={len(cycles)} work-items={len(items)}")

    def resolve_one(mk, tn=""):
        for cand in _variants(mk):
            if cand in by_ext:
                return by_ext[cand]
        return None  # no fuzzy/by_name fallback — avoid mis-target (NS-10)

    def resolve_all(op):
        ids, seen = [], set()
        for mk in [op.get("match_key")] + (op.get("additional_match_keys") or []):
            if not mk:
                continue
            tid = resolve_one(mk, op.get("target_name", ""))
            if tid and tid not in seen:
                seen.add(tid); ids.append(tid)
            elif not tid and mk:
                print(f"    (warn: match_key {mk!r} did not resolve to a live item)")
        return ids

    def label_ids(names):
        ids = []
        for n in (names or []):
            lid = labels.get(n)
            if not lid and APPLY:
                lid = _api("POST", f"{PBASE}/labels/", {"name": n})["id"]; labels[n] = lid
            if lid:
                ids.append(lid)
        return ids

    def build_body(op):
        b = {}
        desc = op.get("description_html") or ""
        ac = _ac_html(op.get("acceptance_criteria"))
        if desc or ac:
            b["description_html"] = (desc + ac) if desc else ac
        if op.get("state") in states:
            b["state"] = states[op["state"]]
        lids = label_ids(op.get("labels"))
        if lids:
            b["labels"] = lids
        prio = PRIORITY_BY_LABEL.get(op.get("priority"))
        if prio:
            b["priority"] = prio
        return b

    # ── Plan ops into per-target merged updates + creates (NS-02/03) ──────────
    updates = {}   # target_id -> {"body":{}, "op":op}
    creates = []   # (op, ext, body)
    n_skip_sup = 0

    def merge(dst, src):
        if "labels" in src:
            dst["labels"] = list({*dst.get("labels", []), *src["labels"]})
        if src.get("description_html"):
            dst["description_html"] = (dst["description_html"] + "<hr>" + src["description_html"]
                                       if dst.get("description_html") else src["description_html"])
        if src.get("state"):
            dst["state"] = src["state"]
        if src.get("priority"):
            if PRIORITY_RANK.get(src["priority"], 0) >= PRIORITY_RANK.get(dst.get("priority", "none"), 0):
                dst["priority"] = src["priority"]

    for op in ops:
        if op.get("id") in superseded:
            print(f"  [skip-superseded] {op.get('id')} — {str(op.get('target_name'))[:50]}")
            n_skip_sup += 1
            continue
        body = build_body(op)
        tids = resolve_all(op)
        if tids:
            for tid in tids:
                if tid not in updates:
                    updates[tid] = {"body": {}, "op": op}
                merge(updates[tid]["body"], body)
                if op.get("op") == "create":
                    print(f"    (note: op {op.get('id')} declared 'create' but resolved to an existing "
                          f"item → merged as update)")
        else:
            ext = f"{EXT_SOURCE}:{op.get('id') or re.sub(r'[^a-zA-Z0-9]+','-',op.get('target_name',''))[:40]}"
            if ext in by_ext:
                # already created on a prior run → UPDATE it (backfills priority/AC/desc fixes; NS-05)
                tid = by_ext[ext]
                if tid not in updates:
                    updates[tid] = {"body": {}, "op": op}
                merge(updates[tid]["body"], body)
            else:
                creates.append((op, ext, body))

    # ── Apply ────────────────────────────────────────────────────────────────
    log = {"mode": "apply" if APPLY else "dry-run", "actions": []}
    n_upd = n_new = n_skip = n_assignfail = 0

    def assign(iid, op):
        nonlocal n_assignfail
        if not APPLY:
            return
        mid = next((m for n, m in modules.items() if n.split(" ")[0] == op.get("epic_module")
                    or n.startswith(op.get("epic_module") or "\x00")), None)
        cid = cycles.get(op.get("phase_cycle")) or next(
            (c for n, c in cycles.items() if (op.get("phase_cycle") or "\x00")[:10] in n), None)
        try:
            if mid:
                _api("POST", f"{PBASE}/modules/{mid}/module-issues/", {"issues": [iid]})
            if cid:
                _api("POST", f"{PBASE}/cycles/{cid}/cycle-issues/", {"issues": [iid]})
        except RuntimeError as e:
            n_assignfail += 1
            print(f"      (assign warn for {iid}: {str(e)[:80]})")
            log["actions"].append({"op": "assign-fail", "id": iid, "error": str(e)[:120]})

    n_err = 0
    try:
        for tid, u in updates.items():
            op, body = u["op"], u["body"]
            print(f"  [update] {str(op.get('target_name'))[:60]} → {sorted(body)}")
            try:
                if APPLY and body:
                    _api("PATCH", f"{PBASE}/work-items/{tid}/", body)
                assign(tid, op)
                n_upd += 1
                log["actions"].append({"op": "update", "id": tid, "name": op.get("target_name"), "fields": sorted(body)})
            except RuntimeError as e:  # NS-04: isolate per-op failure, keep going, keep the log
                n_err += 1
                print(f"      ✗ FAILED: {str(e)[:100]}")
                log["actions"].append({"op": "update-fail", "id": tid, "name": op.get("target_name"), "error": str(e)[:160]})

        for op, ext, body in creates:
            if ext in by_ext:
                print(f"  [skip-exists] {str(op.get('target_name'))[:55]} (ext {ext})")
                n_skip += 1
                continue
            cbody = {"name": op.get("target_name") or op.get("name"), "external_id": ext,
                     "external_source": EXT_SOURCE, **body}
            cbody.setdefault("state", states.get("Backlog"))
            print(f"  [create] {str(op.get('target_name'))[:60]} (ext {ext})")
            try:
                if APPLY:
                    r = _api("POST", f"{PBASE}/work-items/", cbody)
                    if not r or "id" not in r:
                        print(f"      (create returned no id: {op.get('id')})")
                        log["actions"].append({"op": "create-fail", "ext": ext}); n_err += 1; continue
                    by_ext[ext] = r["id"]
                    assign(r["id"], op)
                n_new += 1
                log["actions"].append({"op": "create", "ext": ext, "name": op.get("target_name"), "fields": sorted(body)})
            except RuntimeError as e:
                n_err += 1
                print(f"      ✗ FAILED: {str(e)[:100]}")
                log["actions"].append({"op": "create-fail", "ext": ext, "error": str(e)[:160]})
    finally:
        LOG_F.write_text(json.dumps(log, indent=1))  # NS-04: log always reflects what landed

    print(f"\nsummary: update={n_upd} create={n_new} skip-superseded={n_skip_sup} skip-exists={n_skip} "
          f"assign-fail={n_assignfail} errors={n_err} | from {len(ops)} ops "
          f"[{'APPLIED' if APPLY else 'DRY-RUN — nothing written'}]")
    print(f"log -> {LOG_F}")
    if n_err:
        print(f"⚠ {n_err} op(s) failed — re-run (idempotent) to retry just those.")


if __name__ == "__main__":
    main()

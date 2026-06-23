#!/usr/bin/env python3
"""Apply the deepening-pass DELTA plan to the live Plane board — handles what apply_upsert_plan.py can't:
relation edges (blocked_by/blocking/relates_to), markdown→html descriptions, and module+cycle assignment
on creates. Idempotent, match-by-external_id, NO deletions.

Reads audit/plane-xref/delta-plan.json. Ops:
  {"kind":"update","target_external_id":"story:ASCP-E5-S10","description_md":..,"set_state":..,"set_labels":[..],"why":..}
  {"kind":"create","name":..,"external_id":"ascp-audit-reorg:NEW-12","epic_module":"E1","phase_cycle":"Phase 0 — Spine",
     "set_state":"Spec-Verified","set_labels":[..],"description_md":..,"why":..}
  {"kind":"relation","relation_type":"blocked_by","from_external_id":"story:ASCP-E2-S1","to_external_id":"story:ASCP-E8-13","why":..}

    python3 apply_delta.py           # DRY-RUN
    python3 apply_delta.py --apply   # EXECUTE
"""
from __future__ import annotations
import html as _html
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
PLAN_F = ROOT / "audit/plane-xref/delta-plan.json"
LOG_F = HERE / ".apply_delta_log.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ascp-automation"


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
API_BASE = os.environ.get("PLANE_API_BASE", "").rstrip("/")
WS = os.environ.get("PLANE_WS")
PROJ = os.environ.get("PLANE_PROJ")
KEY = os.environ.get("PLANE_API_KEY", "")
CF_ID = os.environ.get("CF_ACCESS_CLIENT_ID", "")
CF_SECRET = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")
PBASE = f"/workspaces/{WS}/projects/{PROJ}"
EXT_SOURCE = "ascp-audit-reorg"
PRIORITY_BY_LABEL = {"priority:blocking": "urgent", "priority:high": "high", "priority:normal": "medium"}
if not KEY:
    sys.exit("PLANE_API_KEY not set — populate plane-integration/.env")
_last = [0.0]


def _api(method, path, body=None, retries=6):
    now = time.time()
    if now - _last[0] < 0.4:
        time.sleep(0.4 - (now - _last[0]))
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
            raise RuntimeError(f"{method} {path} -> connection failed: {e}")
    raise RuntimeError(f"{method} {path}: exhausted retries")


def _paginate(path):
    out, cur = [], None
    for _ in range(120):
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


def _esc(s):
    return _html.escape(s or "", quote=False)


def md_to_html(md):
    """Minimal, safe markdown→html consistent with the board's existing description_html style."""
    if not md:
        return "<p></p>"
    lines = md.replace("\r\n", "\n").split("\n")
    out, in_ul, in_ol = [], False, False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>"); in_ul = False
        if in_ol:
            out.append("</ol>"); in_ol = False

    def inline(t):
        t = _esc(t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
        return t

    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            close_lists()
            continue
        h = re.match(r"^(#{1,6})\s+(.*)$", s)
        if h:
            close_lists()
            lvl = min(len(h.group(1)) + 2, 6)
            out.append(f"<h{lvl}>{inline(h.group(2))}</h{lvl}>")
            continue
        m = re.match(r"^\s*[-*]\s+(.*)$", s)
        if m:
            if in_ol:
                out.append("</ol>"); in_ol = False
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline(m.group(1))}</li>")
            continue
        m = re.match(r"^\s*\d+[.)]\s+(.*)$", s)
        if m:
            if in_ul:
                out.append("</ul>"); in_ul = False
            if not in_ol:
                out.append("<ol>"); in_ol = True
            out.append(f"<li>{inline(m.group(1))}</li>")
            continue
        close_lists()
        out.append(f"<p>{inline(s)}</p>")
    close_lists()
    return "".join(out)


def _variants(ext):
    if not ext:
        return []
    c = {ext}
    if ext.startswith("story:"):
        body = ext[len("story:"):]
        c.add("story:" + body.replace("ASCP-", "", 1))
        if not body.startswith("ASCP-"):
            c.add("story:ASCP-" + body)
    return list(c)


def main():
    print(f"{'APPLY' if APPLY else 'DRY-RUN'} | {API_BASE} | proj={PROJ}")
    if not PLAN_F.exists():
        sys.exit(f"plan not found: {PLAN_F}")
    plan = json.loads(PLAN_F.read_text())
    ops = plan.get("ops", plan if isinstance(plan, list) else [])
    print(f"plan: {len(ops)} ops")

    print("indexing live board...")
    states = {s["name"]: s["id"] for s in _paginate(f"{PBASE}/states/")}
    labels = {l["name"]: l["id"] for l in _paginate(f"{PBASE}/labels/")}
    modules = _paginate(f"{PBASE}/modules/")
    cycles = _paginate(f"{PBASE}/cycles/")
    items = _paginate(f"{PBASE}/work-items/")
    by_ext = {w.get("external_id"): w["id"] for w in items if w.get("external_id")}
    by_name = {w.get("name"): w["id"] for w in items}
    print(f"  states={len(states)} labels={len(labels)} modules={len(modules)} cycles={len(cycles)} items={len(items)}")

    def resolve(ext, name=None):
        for cand in _variants(ext):
            if cand in by_ext:
                return by_ext[cand]
        tok = re.search(r"E\d+-\w+", ext or "")
        if tok:
            for e, i in by_ext.items():
                if e and tok.group(0) in e and (e.startswith("story:") or e.startswith("task:")):
                    return i
        return by_name.get(name)

    def module_id(emod):
        if not emod:
            return None
        return next((m["id"] for m in modules if m["name"].split(" ")[0] == emod or m["name"].startswith(emod)), None)

    def cycle_id(name):
        if not name:
            return None
        return next((c["id"] for c in cycles if c["name"] == name or name[:10] in c["name"]), None)

    def label_ids(names):
        ids = []
        for n in (names or []):
            lid = labels.get(n)
            if not lid and APPLY:
                lid = _api("POST", f"{PBASE}/labels/", {"name": n})["id"]; labels[n] = lid
            if lid:
                ids.append(lid)
        return ids

    def priority_of(names):
        for n in (names or []):
            if n in PRIORITY_BY_LABEL:
                return PRIORITY_BY_LABEL[n]
        return None

    log = {"mode": "apply" if APPLY else "dry-run", "actions": []}
    counts = {"update": 0, "create": 0, "relation": 0, "skip": 0, "error": 0}

    for op in ops:
        kind = op.get("kind")
        why = op.get("why", "")
        try:
            if kind in ("update", "create"):
                body = {}
                if op.get("description_html"):
                    body["description_html"] = op["description_html"]
                elif op.get("description_md"):
                    body["description_html"] = md_to_html(op["description_md"])
                if op.get("set_state") and op["set_state"] in states:
                    body["state"] = states[op["set_state"]]
                lids = label_ids(op.get("set_labels"))
                if lids:
                    body["labels"] = lids
                pr = priority_of(op.get("set_labels"))
                if pr:
                    body["priority"] = pr

                if kind == "update":
                    tid = resolve(op.get("target_external_id"), op.get("name"))
                    if not tid:
                        print(f"  [MISS update] {op.get('target_external_id')} ({why})")
                        counts["error"] += 1
                        log["actions"].append({"op": "update", "miss": op.get("target_external_id"), "why": why})
                        continue
                    # append mode: add a sentinel-guarded block to the CURRENT description (no overwrite)
                    if op.get("append_md"):
                        sentinel = f"<!--xref:{op.get('why', 'append')}-->"
                        cur = _api("GET", f"{PBASE}/work-items/{tid}/")
                        curhtml = (cur or {}).get("description_html") or ""
                        if sentinel in curhtml:
                            print(f"  [skip-append] {op.get('target_external_id')} (already has {why})")
                            counts["skip"] += 1
                            continue
                        body["description_html"] = curhtml + sentinel + md_to_html(op["append_md"])
                    print(f"  [update] {op.get('target_external_id')} -> {list(body)} ({why})")
                    if APPLY and body:
                        _api("PATCH", f"{PBASE}/work-items/{tid}/", body)
                    counts["update"] += 1
                    log["actions"].append({"op": "update", "id": tid, "ext": op.get("target_external_id"), "fields": list(body), "why": why})
                else:
                    ext = op.get("external_id") or f"{EXT_SOURCE}:{re.sub(r'[^A-Za-z0-9]+','-',op.get('name',''))[:40]}"
                    if ext in by_ext:
                        print(f"  [skip-exists create] {ext} ({why})")
                        counts["skip"] += 1
                        log["actions"].append({"op": "create", "skip": ext, "why": why})
                        continue
                    cbody = {"name": op["name"][:250], "external_id": ext, "external_source": EXT_SOURCE, **body}
                    cbody.setdefault("description_html", "<p></p>")
                    cbody.setdefault("state", states.get("Backlog"))
                    print(f"  [create] {op['name'][:60]} (ext {ext}) ({why})")
                    nid = None
                    if APPLY:
                        nid = _api("POST", f"{PBASE}/work-items/", cbody)["id"]
                        by_ext[ext] = nid
                        mid, cid = module_id(op.get("epic_module")), cycle_id(op.get("phase_cycle"))
                        if mid:
                            _api("POST", f"{PBASE}/modules/{mid}/module-issues/", {"issues": [nid]})
                        if cid:
                            _api("POST", f"{PBASE}/cycles/{cid}/cycle-issues/", {"issues": [nid]})
                    counts["create"] += 1
                    log["actions"].append({"op": "create", "id": nid, "ext": ext, "module": op.get("epic_module"),
                                           "cycle": op.get("phase_cycle"), "why": why})

            elif kind == "relation":
                rt = op.get("relation_type", "blocked_by")
                fid = resolve(op.get("from_external_id"))
                tid = resolve(op.get("to_external_id"))
                if not fid or not tid:
                    print(f"  [MISS relation] {op.get('from_external_id')} -{rt}-> {op.get('to_external_id')}")
                    counts["error"] += 1
                    log["actions"].append({"op": "relation", "miss": [op.get("from_external_id"), op.get("to_external_id")], "why": why})
                    continue
                # idempotency: skip if edge already present
                exists = False
                try:
                    rel = _api("GET", f"{PBASE}/work-items/{fid}/relations/")
                    bucket = (rel or {}).get(rt, []) if isinstance(rel, dict) else []
                    exists = any((r.get("id") == tid or r.get("entity_identifier") == tid or
                                  r.get("related_issue") == tid or r.get("issue") == tid) for r in bucket)
                except RuntimeError:
                    pass
                if exists:
                    print(f"  [skip-rel] {op.get('from_external_id')} -{rt}-> {op.get('to_external_id')}")
                    counts["skip"] += 1
                    continue
                print(f"  [relation] {op.get('from_external_id')} -{rt}-> {op.get('to_external_id')} ({why})")
                if APPLY:
                    _api("POST", f"{PBASE}/work-items/{fid}/relations/", {"relation_type": rt, "issues": [tid]})
                counts["relation"] += 1
                log["actions"].append({"op": "relation", "type": rt, "from": fid, "to": tid,
                                       "from_ext": op.get("from_external_id"), "to_ext": op.get("to_external_id"), "why": why})
            else:
                print(f"  [unknown kind] {kind}")
                counts["error"] += 1
        except RuntimeError as e:
            print(f"  [ERROR] {kind} {why}: {str(e)[:160]}")
            counts["error"] += 1
            log["actions"].append({"op": kind, "error": str(e)[:200], "why": why})

    print(f"\nsummary: {counts}  [{'APPLIED' if APPLY else 'DRY-RUN — nothing written'}]")
    LOG_F.write_text(json.dumps(log, indent=1))
    print(f"log -> {LOG_F}")


if __name__ == "__main__":
    main()

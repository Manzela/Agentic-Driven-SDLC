#!/usr/bin/env python3
"""Full read-only inventory dump of the live Plane board → JSON for cross-reference analysis.

Pulls states, labels, modules, cycles, and ALL work-items (with descriptions, parent/child,
priority, state, labels, module+cycle membership). Writes audit/plane-xref/board-snapshot.json.
Read-only: issues only GET requests.
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
OUT_DIR = ROOT / "audit/plane-xref"
OUT_DIR.mkdir(parents=True, exist_ok=True)
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
API_BASE = os.environ.get("PLANE_API_BASE").rstrip("/")
WS = os.environ.get("PLANE_WS")
PROJ = os.environ.get("PLANE_PROJ")
KEY = os.environ.get("PLANE_API_KEY", "")
CF_ID = os.environ.get("CF_ACCESS_CLIENT_ID", "")
CF_SECRET = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")
PBASE = f"/workspaces/{WS}/projects/{PROJ}"
_last = [0.0]


def _api(method, path, body=None, retries=6):
    now = time.time()
    if now - _last[0] < 0.34:
        time.sleep(0.34 - (now - _last[0]))
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


def _strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    print("pulling states/labels/modules/cycles...", file=sys.stderr)
    states = _paginate(f"{PBASE}/states/")
    labels = _paginate(f"{PBASE}/labels/")
    modules = _paginate(f"{PBASE}/modules/")
    cycles = _paginate(f"{PBASE}/cycles/")
    state_by_id = {s["id"]: s["name"] for s in states}
    label_by_id = {l["id"]: l["name"] for l in labels}

    print("pulling work-items (list)...", file=sys.stderr)
    items = _paginate(f"{PBASE}/work-items/")
    print(f"  {len(items)} work-items", file=sys.stderr)

    # module + cycle membership maps
    mod_members = {}
    for m in modules:
        mi = _paginate(f"{PBASE}/modules/{m['id']}/module-issues/")
        for r in mi:
            mod_members.setdefault(r.get("issue") or r.get("id"), []).append(m["name"])
    cyc_members = {}
    for c in cycles:
        ci = _paginate(f"{PBASE}/cycles/{c['id']}/cycle-issues/")
        for r in ci:
            cyc_members.setdefault(r.get("issue") or r.get("id"), []).append(c["name"])

    enriched = []
    n = len(items)
    for idx, w in enumerate(items):
        iid = w["id"]
        desc = w.get("description_html")
        if desc is None:
            # fetch detail for description
            det = _api("GET", f"{PBASE}/work-items/{iid}/")
            desc = det.get("description_html") if det else None
            for k in ("parent", "priority", "sequence_id", "sort_order"):
                if det and w.get(k) is None:
                    w[k] = det.get(k)
        enriched.append({
            "id": iid,
            "seq": w.get("sequence_id"),
            "name": w.get("name"),
            "external_id": w.get("external_id"),
            "external_source": w.get("external_source"),
            "state": state_by_id.get(w.get("state"), w.get("state")),
            "priority": w.get("priority"),
            "parent": w.get("parent"),
            "labels": [label_by_id.get(l, l) for l in (w.get("labels") or [])],
            "modules": mod_members.get(iid, []),
            "cycles": cyc_members.get(iid, []),
            "completed_at": w.get("completed_at"),
            "created_at": w.get("created_at"),
            "updated_at": w.get("updated_at"),
            "desc_text": _strip_html(desc),
            "desc_len": len(desc or ""),
        })
        if (idx + 1) % 25 == 0:
            print(f"  enriched {idx+1}/{n}", file=sys.stderr)

    snap = {
        "project": PROJ,
        "counts": {"states": len(states), "labels": len(labels), "modules": len(modules),
                   "cycles": len(cycles), "work_items": len(items)},
        "states": [{"name": s["name"], "group": s.get("group"), "id": s["id"]} for s in states],
        "labels": [l["name"] for l in labels],
        "modules": [{"name": m["name"], "id": m["id"]} for m in modules],
        "cycles": [{"name": c["name"], "id": c["id"], "start": c.get("start_date"),
                    "end": c.get("end_date")} for c in cycles],
        "work_items": enriched,
    }
    out = OUT_DIR / "board-snapshot.json"
    out.write_text(json.dumps(snap, indent=1))
    print(f"\nwrote {out} ({out.stat().st_size} bytes)", file=sys.stderr)
    # quick stats
    from collections import Counter
    print("states:", dict(Counter(e["state"] for e in enriched)), file=sys.stderr)
    print("sources:", dict(Counter(e["external_source"] for e in enriched)), file=sys.stderr)
    parents = sum(1 for e in enriched if e["parent"])
    print(f"items with parent: {parents}", file=sys.stderr)


if __name__ == "__main__":
    main()

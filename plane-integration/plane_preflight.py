#!/usr/bin/env python3
"""Plane remote-access preflight — turns an opaque Cloudflare 302 into an actionable diagnosis.

Run this FIRST whenever Plane access misbehaves. It probes the live board with the configured
service token and, on failure, decodes Cloudflare's signed deny `meta` to tell you exactly which
condition failed and how to fix it — instead of the silent redirect-to-login that cost a whole
session once.

Reads creds from plane-integration/.env (or env vars):
    PLANE_API_BASE, PLANE_WS, PLANE_PROJ, PLANE_API_KEY, CF_ACCESS_CLIENT_ID, CF_ACCESS_CLIENT_SECRET

Exit 0 = reachable; exit 1 = blocked (prints the precise reason + fix).
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent


def _load_dotenv(p):
    p = pathlib.Path(p)
    if not p.exists():
        return
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(HERE / ".env")

BASE = os.environ.get("PLANE_API_BASE", "https://YOUR-PLANE-HOST.example.com/api/v1").rstrip("/")
WS = os.environ.get("PLANE_WS", "your-workspace-slug")
PROJ = os.environ.get("PLANE_PROJ", "YOUR_PROJECT_UUID")
KEY = os.environ.get("PLANE_API_KEY", "")
CID = os.environ.get("CF_ACCESS_CLIENT_ID", "")
CSEC = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")

URL = f"{BASE}/workspaces/{WS}/projects/{PROJ}/states/"


def fix(msg):
    print("\n❌ BLOCKED — " + msg)
    print("\nFix path (run the durable setup, then re-run this preflight):")
    print("  CF_API_TOKEN=<account 'Access: Apps and Policies — Edit' token> \\")
    print("    python3 plane-integration/setup_cf_access.py --apply")
    print("See plane-integration/REMOTE_ACCESS.md for the full runbook.")
    sys.exit(1)


def main():
    print(f"preflight → {URL}")
    if not KEY:
        fix("PLANE_API_KEY missing. Populate plane-integration/.env (see REMOTE_ACCESS.md).")
    headers = {"X-API-Key": KEY,
               "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ascp-automation"}
    if CID and CSEC:
        headers["CF-Access-Client-Id"] = CID
        headers["CF-Access-Client-Secret"] = CSEC
    else:
        print("  (no CF service-token creds set — only works from inside the CF perimeter)")

    # NS-09: a no-redirect opener so a CF 302→login surfaces as HTTPError (and the
    # meta-decode branch below runs) instead of being auto-followed to a 200 HTML page.
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(_NoRedirect)

    req = urllib.request.Request(URL, headers=headers)
    try:
        with opener.open(req, timeout=20) as r:
            raw = r.read()
            ctype = r.headers.get("Content-Type", "")
            if "json" not in ctype and not raw.strip().startswith(b"{"):
                fix("got a non-JSON 200 (likely a Cloudflare Access HTML page). "
                    "The service token is not being honored by the app's policy.")
            try:
                d = json.loads(raw)
            except ValueError:
                fix("200 with an unparseable body — not the Plane API (CF interstitial?).")
            n = len(d.get("results", d) if isinstance(d, dict) else d)
            print(f"\n✅ REACHABLE — HTTP {r.status}, {n} workflow states. Plane API is good to go.")
            return 0
    except urllib.error.HTTPError as e:
        if e.code == 403:
            fix("HTTP 403 from Plane — the X-API-Key is invalid for this workspace. "
                "Check PLANE_API_KEY targets the agentic-driven-sdlc workspace.")
        if e.code in (301, 302):
            loc = e.headers.get("location", "")
            if "cloudflareaccess.com" in loc:
                meta = _decode_meta(loc)
                sts = meta.get("service_token_status")
                if sts is False:
                    fix("Cloudflare Access rejected the service token (service_token_status=false). "
                        "Either no service-token policy is BOUND to the app, or the token's "
                        "Client-Id/Secret are wrong. This is the #1 recurring failure — run the "
                        "setup script below; it binds a dedicated service-token policy to the app.")
                fix(f"Cloudflare Access denied (meta={meta}).")
            fix(f"Unexpected redirect to {loc[:80]}…")
        fix(f"HTTP {e.code}: {e.read().decode()[:200]}")
    except urllib.error.URLError as e:
        fix(f"connection failed: {e}. Endpoint {BASE} unreachable (tunnel down / wrong host?).")


def _decode_meta(location):
    try:
        seg = location.split("meta=", 1)[1].split("&", 1)[0]
        payload = seg.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        d = json.loads(base64.urlsafe_b64decode(payload))
        return {k: d.get(k) for k in ("service_token_status", "auth_status", "aud")}
    except Exception:
        return {}


if __name__ == "__main__":
    sys.exit(main())

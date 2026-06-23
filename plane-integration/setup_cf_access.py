#!/usr/bin/env python3
"""Idempotent Cloudflare Access setup for programmatic Plane API access — the DURABLE fix.

Ensures (idempotently) a dedicated Service-Auth policy (any valid service token, or a specific
token via ASCP_BIND_TOKEN_ID) is attached to the Plane ASCP application, SEPARATE from the human
SSO policy, then verifies connectivity end to end.

Hardened per the plane-integration audit:
  * Attach via a FULL-OBJECT round-trip: GET the full app, append the policy to its EXISTING
    policies, PUT the whole object back (preserves `domain` + every required field + the human
    "Owner only" policy). [NS-06/NS-07]
  * Read-back after PUT: assert every pre-existing policy still attached; abort loudly if one
    vanished (never silently drop human SSO). [NS-06]
  * Loads plane-integration/.env and reads CF_ACCESS_CLIENT_ID/SECRET (PLANE_CF_* fallback) for
    the verify step. [NS-08]

Run:  CF_API_TOKEN=cfat_... python3 setup_cf_access.py            # DRY-RUN
      CF_API_TOKEN=cfat_... python3 setup_cf_access.py --apply    # make changes
Optional verify: also set PLANE_API_KEY + CF_ACCESS_CLIENT_ID/SECRET (or rely on .env).
Optional tighten: ASCP_BIND_TOKEN_ID=<service_token_uuid> (allow only that token).
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent


def _load_dotenv(p):  # NS-08
    try:
        for ln in pathlib.Path(p).read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_load_dotenv(HERE / ".env")

ACCT = os.environ.get("CF_ACCOUNT_ID", "YOUR_CF_ACCOUNT_ID")
APP_DOMAIN = os.environ.get("ASCP_APP_DOMAIN", "YOUR-PLANE-HOST.example.com")
POLICY_NAME = os.environ.get("ASCP_POLICY_NAME", "ASCP API — service tokens")
BIND_TOKEN_ID = os.environ.get("ASCP_BIND_TOKEN_ID")
CF_API = os.environ.get("CF_API_TOKEN", "")
APPLY = "--apply" in sys.argv
CFB = "https://api.cloudflare.com/client/v4"
WRITABLE = ("name", "domain", "type", "session_duration", "app_launcher_visible",
            "allowed_idps", "auto_redirect_to_identity", "enable_binding_cookie",
            "http_only_cookie_attribute", "options_preflight_bypass",
            "destinations", "self_hosted_domains", "tags")

if not CF_API:
    sys.exit("CF_API_TOKEN not set (account-scoped 'Access: Apps and Policies — Edit' token).")


def cf(method, path, body=None):
    req = urllib.request.Request(
        CFB + path, data=(json.dumps(body).encode() if body is not None else None), method=method,
        headers={"Authorization": "Bearer " + CF_API, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}


def want_include():
    return [{"service_token": {"token_id": BIND_TOKEN_ID}}] if BIND_TOKEN_ID else [{"any_valid_service_token": {}}]


def main():
    print(f"{'APPLY' if APPLY else 'DRY-RUN'} | account {ACCT} | app {APP_DOMAIN}")
    st, d = cf("GET", f"/accounts/{ACCT}/tokens/verify")
    if not d.get("success"):
        sys.exit(f"CF API token invalid/not account-scoped: {d.get('errors')}")
    print("CF API token: valid ✓")

    st, d = cf("GET", f"/accounts/{ACCT}/access/apps?per_page=50")
    if not d.get("success"):
        sys.exit(f"cannot list Access apps: {d.get('errors')}")
    stub = next((a for a in d["result"] if APP_DOMAIN in str(a.get("domain", ""))
                 or APP_DOMAIN in str(a.get("self_hosted_domains", []))), None)
    if not stub:
        sys.exit(f"no Access app for {APP_DOMAIN}")
    app_id = stub["id"]

    # FULL object (authoritative policies + all required fields) — NS-06/NS-07
    st, d = cf("GET", f"/accounts/{ACCT}/access/apps/{app_id}")
    app = d.get("result", {})
    cur_pol = app.get("policies") or []
    pre_ids = {p.get("id") for p in cur_pol}
    print(f"app: {app.get('name')} ({app_id}) | existing policies: {[p.get('name') for p in cur_pol]}")

    # ensure the dedicated service-auth policy exists
    st, d = cf("GET", f"/accounts/{ACCT}/access/policies?per_page=100")
    pols = d.get("result", []) if d.get("success") else []
    svc = next((p for p in pols if p.get("name") == POLICY_NAME), None)
    if svc:
        print(f"policy '{POLICY_NAME}' exists ({svc['id']})")
    else:
        print(f"policy '{POLICY_NAME}': MISSING → create")
        if APPLY:
            st, d = cf("POST", f"/accounts/{ACCT}/access/policies",
                       {"name": POLICY_NAME, "decision": "non_identity",
                        "include": want_include(), "exclude": [], "require": []})
            if not d.get("success"):
                sys.exit(f"create policy failed: {d.get('errors')}")
            svc = d["result"]; print(f"  created {svc['id']}")
        else:
            svc = {"id": "<new>"}

    if svc["id"] in pre_ids:
        print("policy already attached ✓ (no-op)")
    else:
        print("attaching policy via full-object round-trip (preserves human policy + domain)")
        if APPLY:
            new_pols = [{"id": p["id"], "precedence": p.get("precedence", i + 1)}
                        for i, p in enumerate(cur_pol)]
            new_pols.append({"id": svc["id"], "precedence": len(new_pols) + 1})
            body = {k: app[k] for k in WRITABLE if k in app and app[k] is not None}
            body["policies"] = new_pols
            if "domain" not in body and app.get("domain"):
                body["domain"] = app["domain"]            # NS-07 guarantee
            st, d = cf("PUT", f"/accounts/{ACCT}/access/apps/{app_id}", body)
            if not d.get("success"):
                sys.exit(f"attach failed: {d.get('errors')}")
            # read-back: every pre-existing policy must survive (NS-06)
            _, rb = cf("GET", f"/accounts/{ACCT}/access/apps/{app_id}")
            now_ids = {p.get("id") for p in (rb.get("result", {}).get("policies") or [])}
            dropped = pre_ids - now_ids
            if dropped:
                sys.exit(f"ABORT: pre-existing policies were dropped: {dropped} — restore in dashboard")
            if svc["id"] not in now_ids:
                sys.exit("ABORT: new policy not present after PUT")
            print(f"  attached ✓ (policies now: {len(now_ids)}, human policy preserved)")

    # verify end-to-end (NS-08 env names + .env)
    cid = os.environ.get("CF_ACCESS_CLIENT_ID") or os.environ.get("PLANE_CF_CLIENT_ID")
    csec = os.environ.get("CF_ACCESS_CLIENT_SECRET") or os.environ.get("PLANE_CF_CLIENT_SECRET")
    pkey = os.environ.get("PLANE_API_KEY")
    if cid and csec and pkey and APPLY:
        url = (f"https://{APP_DOMAIN}/api/v1/workspaces/"
               f"{os.environ.get('PLANE_WS', 'your-workspace-slug')}/projects/"
               f"{os.environ.get('PLANE_PROJ', 'YOUR_PROJECT_UUID')}/states/")
        req = urllib.request.Request(url, headers={
            "CF-Access-Client-Id": cid, "CF-Access-Client-Secret": csec, "X-API-Key": pkey,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ascp-automation"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                print(f"verify: HTTP {r.status} ✅ service token reaches the board")
        except urllib.error.HTTPError as e:
            print(f"verify: HTTP {e.code} — allow ~30s for edge propagation, re-run")
    else:
        print("verify: skipped (set CF_ACCESS_CLIENT_ID/SECRET + PLANE_API_KEY, and --apply)")
    print("DONE." + ("" if APPLY else "  (dry-run)"))


if __name__ == "__main__":
    main()

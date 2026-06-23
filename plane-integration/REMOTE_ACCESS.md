# Plane remote access — durable runbook

How to reach the **remote** Plane board (`plane.autonomous-agent.dev`, workspace
`agentic-driven-sdlc`, project `0de2a9fb-5382-4e0d-bf99-f00f221461ca`) programmatically,
securely, and repeatably — so the multi-hour access scramble never recurs.

> The existing `plane_client.py` targets the **local** Docker Plane (`localhost:8090`, workspace
> `ascp`). This document is about the **remote production** board, which is different and sits
> behind Cloudflare Access.

## Architecture (why it kept failing)

```
client ──HTTPS──▶ Cloudflare edge ──(Access policy check)──▶ cloudflared tunnel ──▶ plane-2:80 (Plane API)
                        │
                        └─ if no allow-rule matches → 302 to *.cloudflareaccess.com/login  (the opaque failure)
```

Two independent gates must BOTH pass:
1. **Cloudflare Access** — needs a **service token** (`CF-Access-Client-Id` / `CF-Access-Client-Secret`)
   that is allowed by a policy **bound to the application**. The recurring trap: editing a reusable
   policy in the dashboard does **not** reliably attach it to the app, so tokens fail with
   `service_token_status:false` and a 302. The app must actually list the policy.
2. **Plane** — needs `X-API-Key: <plane personal/api key>` for the workspace.

Human/browser access uses the **`Owner only`** email policy (SSO). Automation uses a **separate**
service-token policy. Keep them separate — never put `everyone` on a public hostname.

## One-time setup (idempotent, self-healing)

1. Create an **account-scoped** Cloudflare API token: Permissions → `Access: Apps and Policies`
   → **Edit**; Resources → **Account → your account** (NOT "All zones" — that yields `10000` auth
   errors on account endpoints).
2. Bind a dedicated service-token policy to the app and verify:
   ```bash
   CF_API_TOKEN=cfat_xxx \
   PLANE_API_KEY=plane_api_xxx \
   PLANE_CF_CLIENT_ID=xxx.access PLANE_CF_CLIENT_SECRET=xxx \
   python3 plane-integration/setup_cf_access.py --apply
   ```
   This creates `ASCP API — service tokens` (decision `non_identity`, include *any valid service
   token*), attaches it to the `Plane ASCP` app, and runs an end-to-end check. Re-running is safe
   (no-ops if already correct; repairs drift). To restrict to ONE token: set
   `ASCP_BIND_TOKEN_ID=<service_token_uuid>`.
3. Write the gitignored creds file `plane-integration/.env` (loaded automatically by the tools):
   ```
   PLANE_API_BASE=https://plane.autonomous-agent.dev/api/v1
   PLANE_WS=agentic-driven-sdlc
   PLANE_PROJ=0de2a9fb-5382-4e0d-bf99-f00f221461ca
   PLANE_API_KEY=plane_api_xxx
   CF_ACCESS_CLIENT_ID=xxx.access
   CF_ACCESS_CLIENT_SECRET=xxx
   ```

## Daily use

```bash
python3 plane-integration/plane_preflight.py        # confirm reachable (self-diagnosing)
python3 plane-integration/apply_upsert_plan.py      # dry-run the audit upsert plan
python3 plane-integration/apply_upsert_plan.py --apply   # write (idempotent, NO deletions)
```
All three auto-load `plane-integration/.env`, so no env vars needed once it's filled.

## Security

- **Least privilege:** the API token is scoped to `Access: Apps and Policies` only; the service
  token only passes a `non_identity` policy (no identity bypass; no `everyone`).
- **Separation:** human SSO (`Owner only` email) and automation (`ASCP API — service tokens`) are
  distinct policies; revoking one never affects the other.
- **Rotation:** rotate the service token in Zero Trust → Service Auth; if you keep the policy on
  *any valid service token*, no policy change is needed after rotation — just update `.env`. If you
  pinned `ASCP_BIND_TOKEN_ID`, re-run `setup_cf_access.py --apply` with the new id.
- **Hygiene:** `.env`, `.apply_log.json`, and all OCI/CF keys are gitignored. Never commit secrets.
  Revoke any token that has appeared in a chat/transcript.

## Troubleshooting — every failure we actually hit, and its fix

| Symptom | Cause | Fix |
|---|---|---|
| `302` → `*.cloudflareaccess.com/login`, `service_token_status:false` | No service-token policy **bound to the app** (dashboard edit didn't attach) | `setup_cf_access.py --apply` (binds + verifies) |
| `302` even with a brand-new valid token | Same as above — it's the binding, not the token | same |
| `403 {"detail":"Given API token is not valid"}` | `X-API-Key` is for the wrong instance/workspace (e.g. local `ascp`, not remote) | use the remote workspace's key |
| CF API `10000 Authentication error` on `/access/apps` | API token scoped to **zones**, not the **account** | recreate token with Resources → Account |
| `ssh … Permission denied (publickey)` with `*.pem` | That `.pem` is an **OCI API signing key**, not an SSH key (`-----BEGIN PRIVATE KEY----- … OCI_API_KEY`) | use the instance SSH key, or skip SSH (use CF service token) |
| Agent can't mint/modify CF Access from its sandbox | Safety guardrail blocks security-config changes | run `setup_cf_access.py` yourself (account token) |
| `ssh -i key-N …` "Identity file not accessible" | missing space → `key.pem-N` parsed as filename | put a space before `-N` |

## Files

- `setup_cf_access.py` — idempotent CF Access binding + verify (run once / on drift).
- `plane_preflight.py` — self-diagnosing connectivity check (run first when in doubt).
- `apply_upsert_plan.py` — applies `docs/audits/spec-to-evidence-steering/plane-upsert-plan.json`
  (upsert-by-name, no deletions; dry-run default).
- `.env` (gitignored) — the single creds home, auto-loaded by all of the above.

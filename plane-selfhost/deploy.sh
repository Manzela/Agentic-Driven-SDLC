#!/usr/bin/env bash
# deploy.sh — turnkey bring-up of the self-hosted Plane stack for the ASCP
# control plane. Run ON THE VM (Ubuntu 22.04) from this directory after Docker
# is installed. Idempotent: safe to re-run. See docs/deploy/PLANE_EDGE_DEPLOY.md.
#
# What it automates (the version-stable, official steps):
#   1. preflight (docker + compose + plane.env)
#   2. validate + pull + bring up all ~13 services with persistent volumes
#   3. wait for the web/api surface to answer
#   4. provision the 8 epics / 49 stories / 186 tasks / 7 cycles IF credentials.env
#      is filled (otherwise it prints the exact one-time human bootstrap steps)
#
# What it intentionally does NOT do: fabricate the first admin user / workspace /
# API token via undocumented Django internals. Plane gates first-run setup on
# purpose; that one human step (4a) is a UI flow and is called out explicitly.

set -Eeuo pipefail
cd "$(dirname "$0")"

log()  { printf '\033[1;36m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[deploy]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[deploy] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ── compose shim (supports both `docker compose` and legacy `docker-compose`) ──
if docker compose version >/dev/null 2>&1; then COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then COMPOSE=(docker-compose)
else die "Docker Compose not found. Install Docker first: curl -fsSL https://get.docker.com | sh"; fi
command -v docker >/dev/null 2>&1 || die "docker not found."

ENV_FILE="plane.env"
COMPOSE+=(--env-file "$ENV_FILE")

# ── 1. preflight ──────────────────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
  warn "No plane.env found. Creating one from the template — EDIT IT (set every"
  warn "__REPLACE…__ secret) then re-run this script."
  cp plane.env.template "$ENV_FILE"
  die "plane.env created. Fill the secrets (openssl rand -hex 32) and re-run."
fi
if grep -q "__REPLACE" "$ENV_FILE"; then
  die "plane.env still contains __REPLACE…__ placeholders. Set real secrets first."
fi

# source the port for the health probe (default 80)
LISTEN_HTTP_PORT="$(grep -E '^LISTEN_HTTP_PORT=' "$ENV_FILE" | tail -1 | cut -d= -f2)"
LISTEN_HTTP_PORT="${LISTEN_HTTP_PORT:-80}"

# ── 2. validate + pull + up ───────────────────────────────────────────────────
log "Validating compose config…"
"${COMPOSE[@]}" config -q || die "docker compose config failed — check plane.env / docker-compose.yml."
log "Pulling images (APP_RELEASE from plane.env)…"
"${COMPOSE[@]}" pull
log "Starting the stack (detached)…"
"${COMPOSE[@]}" up -d

# ── 3. wait for the surface ───────────────────────────────────────────────────
log "Waiting for Plane to answer on http://localhost:${LISTEN_HTTP_PORT}/ …"
deadline=$(( $(date +%s) + 300 ))
until curl -fsS -o /dev/null "http://localhost:${LISTEN_HTTP_PORT}/"; do
  [[ $(date +%s) -gt $deadline ]] && die "Plane did not become reachable within 5m. Check: ${COMPOSE[*]} logs --tail=100"
  sleep 5
done
log "Plane web surface is up."

# ── 4. provision the board (or print the one-time bootstrap steps) ────────────
CREDS="credentials.env"
if [[ -f "$CREDS" ]] && ! grep -q "__REPLACE" "$CREDS"; then
  log "credentials.env present — provisioning the ASCP board from the .kiro backlog…"
  python3 ../plane-integration/provision_plane.py all
  python3 ../plane-integration/reorg_plane.py all || warn "reorg step reported issues — review output above."
  log "Done. Real Plane board provisioned: 8 epics / 49 stories / 186 tasks / 7 cycles."
  log "Next: bring up the Cloudflare Tunnel + Access (Steps 2–3 of PLANE_EDGE_DEPLOY.md)."
else
  cat <<'EOF'

────────────────────────────────────────────────────────────────────────────
 The stack is RUNNING, but the board is not provisioned yet because this is a
 fresh instance. Do the one-time human bootstrap (Plane gates first-run setup):

   4a. Open the instance and complete first-run admin setup:
         http://localhost:<LISTEN_HTTP_PORT>/   (or https://plane.autonomous-agent.dev
         once the Cloudflare Tunnel from Step 2 is live)
   4b. Create a workspace with slug  ascp  and a project named  ASCP.
   4c. Workspace Settings → API tokens → add a token. Copy the project UUID
       from the project URL/Settings.
   4d. Fill credentials.env:
         cp credentials.env.template credentials.env && $EDITOR credentials.env
   4e. Re-run this script (./deploy.sh) — it will detect credentials.env and
       provision the 8 epics / 49 stories / 186 tasks / 7 cycles automatically.
────────────────────────────────────────────────────────────────────────────
EOF
fi

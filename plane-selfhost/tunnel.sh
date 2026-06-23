#!/usr/bin/env bash
# tunnel.sh — publish the running Plane stack at https://plane.autonomous-agent.dev
# via a Cloudflare Tunnel (no inbound ports on the origin), and print the
# Cloudflare Access (Zero-Trust) setup. Run ON THE VM after ./deploy.sh has the
# stack answering on localhost. Idempotent. See docs/deploy/PLANE_EDGE_DEPLOY.md
# Steps 2–3. This is the cutover that replaces the static mock with real Plane.
#
# Cloudflare account actions (tunnel create / DNS route / Access app) authenticate
# interactively via `cloudflared tunnel login` — NO API keys are baked into this
# script or the repo.

set -Eeuo pipefail
cd "$(dirname "$0")"

HOSTNAME="${HOSTNAME_OVERRIDE:-plane.autonomous-agent.dev}"
TUNNEL_NAME="${TUNNEL_NAME:-plane-ascp}"
LOCAL_PORT="${LOCAL_PORT:-80}"     # Plane proxy/web port (compose default; match LISTEN_HTTP_PORT)

log()  { printf '\033[1;36m[tunnel]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[tunnel]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[tunnel] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ── 1. install cloudflared if missing ─────────────────────────────────────────
if ! command -v cloudflared >/dev/null 2>&1; then
  log "Installing cloudflared…"
  curl -fsSL https://pkg.cloudflare.com/install.sh | sudo bash
  sudo apt-get install -y cloudflared
fi
command -v cloudflared >/dev/null 2>&1 || die "cloudflared install failed."

# ── 2. authenticate to the zone (interactive, browser) ────────────────────────
if [[ ! -f "$HOME/.cloudflared/cert.pem" ]]; then
  log "Authenticating to Cloudflare (a browser URL will be printed; pick the autonomous-agent.dev zone)…"
  cloudflared tunnel login
fi

# ── 3. create the tunnel (idempotent) ─────────────────────────────────────────
if cloudflared tunnel list 2>/dev/null | awk '{print $2}' | grep -qx "$TUNNEL_NAME"; then
  log "Tunnel '$TUNNEL_NAME' already exists — reusing."
else
  log "Creating tunnel '$TUNNEL_NAME'…"
  cloudflared tunnel create "$TUNNEL_NAME"
fi
TUNNEL_UUID="$(cloudflared tunnel list 2>/dev/null | awk -v n="$TUNNEL_NAME" '$2==n {print $1}' | head -1)"
[[ -n "$TUNNEL_UUID" ]] || die "could not resolve tunnel UUID for '$TUNNEL_NAME'."
log "Tunnel UUID: $TUNNEL_UUID"

# ── 4. write ingress config ───────────────────────────────────────────────────
CFG_DIR="$HOME/.cloudflared"
CFG="$CFG_DIR/config.yml"
mkdir -p "$CFG_DIR"
log "Writing $CFG (ingress $HOSTNAME -> http://localhost:$LOCAL_PORT)…"
cat > "$CFG" <<EOF
tunnel: $TUNNEL_UUID
credentials-file: $CFG_DIR/$TUNNEL_UUID.json
ingress:
  - hostname: $HOSTNAME
    service: http://localhost:$LOCAL_PORT
  - service: http_status:404
EOF

# ── 5. route DNS (creates/updates the proxied CNAME) ──────────────────────────
log "Routing DNS: $HOSTNAME -> $TUNNEL_UUID.cfargotunnel.com …"
cloudflared tunnel route dns "$TUNNEL_NAME" "$HOSTNAME" || \
  warn "DNS route returned non-zero (often means the record already exists) — verify in the dashboard."

# ── 6. install as an always-on systemd service ────────────────────────────────
if ! systemctl list-unit-files 2>/dev/null | grep -q '^cloudflared'; then
  log "Installing cloudflared as a systemd service…"
  sudo cloudflared service install
fi
sudo systemctl enable --now cloudflared
log "cloudflared service is enabled and running."

# ── 7. Cloudflare Access (Zero-Trust identity gate) — guided ──────────────────
cat <<EOF

────────────────────────────────────────────────────────────────────────────
 Tunnel is live: https://$HOSTNAME now serves the REAL Plane stack (the static
 'Mission Control' mock is no longer what answers this hostname).

 FINISH the security gate — add a Cloudflare Access application so only you can
 reach it (dashboard: Zero Trust → Access → Applications → Add → Self-hosted):
   • Application domain: $HOSTNAME
   • Session duration:   24h
   • Policy:             Allow, include = your email (danielq1603@gmail.com)
   • IMPORTANT: add a SERVICE-TOKEN bypass policy for the E6 webhook path so
     Plane's signed webhook deliveries to the dispatcher aren't blocked by the
     interactive identity gate (see PLANE_EDGE_DEPLOY.md Step 4).

 Then verify:
   curl -I https://$HOSTNAME        # expect a Cloudflare Access login redirect
────────────────────────────────────────────────────────────────────────────
EOF

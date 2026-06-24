#!/usr/bin/env bash
# oci-lock-ingress.sh — lock the Plane origin VM's OCI ingress to a hardened posture.
#
# WHY: the origin VM's public IP was briefly committed in cleartext (redacted in PR #31).
# The origin runs a Cloudflare TUNNEL (cloudflared dials OUT; no inbound 80/443 is needed —
# see docs/deploy/PLANE_EDGE_DEPLOY.md:11,212-213), so the safest posture is DENY-ALL inbound
# except an SSH management CIDR. As defense-in-depth (only useful if a service is ever a
# classic CF-proxied origin instead of a tunnel) it ALSO allows TCP/443 from Cloudflare's
# published CIDRs. Closes the OWNER action in docs/github-public-repo-checklist.md §4.
#
# ⚠️  SSH-LOCKOUT RISK — READ THIS. This REPLACES the security list's ingress rules. If
#     SSH_MGMT_CIDR is wrong or missing you lose SSH access (the tunnel is outbound-only and
#     will NOT save you). Mitigations built in: the script REFUSES to run without
#     SSH_MGMT_CIDR, DRY-RUNS by default (prints the proposed rules and exits 0 — it only
#     mutates when you pass APPLY=1 after reviewing), and BACKS UP the current rules first.
#
# PREREQUISITES:
#   - oci CLI configured (~/.oci/config — confirm it holds the key ROTATED 2026-06-23 — or
#     OCI_CLI_* env vars; region il-jerusalem-1).   brew install oci-cli   # or pip install oci-cli
#   - jq and curl installed.
#   - The VM's INSTANCE_OCID (Console → Compute → Instances → your VM → OCID), OR set
#     SECURITY_LIST_OCID directly to skip instance→subnet discovery.
#   - If the VNIC uses a Network Security Group instead of the subnet's security list, set
#     SECURITY_LIST_OCID to that NSG and adapt to `oci network nsg ...` (see NOTE below).
#
# USAGE:
#   SSH_MGMT_CIDR=203.0.113.4/32 INSTANCE_OCID=ocid1.instance.oc1...  ./oci-lock-ingress.sh         # dry-run
#   SSH_MGMT_CIDR=203.0.113.4/32 INSTANCE_OCID=ocid1.instance.oc1... APPLY=1 ./oci-lock-ingress.sh  # apply
#   SSH_MGMT_CIDR=203.0.113.4/32 SECURITY_LIST_OCID=ocid1.securitylist.oc1... ./oci-lock-ingress.sh # skip discovery
#
# REVERSIBLE: the current ingress rules are saved to ./oci-ingress-backup-<ts>.json before any
# change. To roll back, restore them in the Console (Networking → VCN → Security Lists → edit),
# or convert that backup's kebab-case keys to camelCase and re-apply with the same `update`.
#
# NOTE on OCI-CLI JSON casing: the `--ingress-security-rules` INPUT uses camelCase
# (`sourceType`, `isStateless`, `tcpOptions.destinationPortRange`), while the `get --query`
# OUTPUT is kebab-case (`source-type`, `is-stateless`, `tcp-options`). This script builds
# camelCase for input. Review the dry-run output before APPLY=1; this script has not been
# executed against a live tenancy from here (no oci CLI available in the dev env).
set -euo pipefail

: "${SSH_MGMT_CIDR:?Set SSH_MGMT_CIDR to the IP/range you SSH FROM (e.g. 203.0.113.4/32) — REQUIRED to avoid SSH lockout}"
APPLY="${APPLY:-0}"
PORT_SSH=22
PORT_HTTPS=443

command -v oci  >/dev/null || { echo "ERROR: oci CLI not found.  brew install oci-cli"; exit 1; }
command -v jq   >/dev/null || { echo "ERROR: jq not found."; exit 1; }
command -v curl >/dev/null || { echo "ERROR: curl not found."; exit 1; }

# --- Cloudflare CIDRs (defense-in-depth on 443). Live fetch, pinned fallback. -----------
echo "Fetching live Cloudflare CIDRs…"
CF4=$(curl -fsS https://www.cloudflare.com/ips-v4 2>/dev/null || true)
CF6=$(curl -fsS https://www.cloudflare.com/ips-v6 2>/dev/null || true)
if [ -z "$CF4" ] || [ -z "$CF6" ]; then
  echo "  (live fetch failed — using the pinned 2026-06-24 snapshot, etag 38f79d05)"
  CF4=$'173.245.48.0/20\n103.21.244.0/22\n103.22.200.0/22\n103.31.4.0/22\n141.101.64.0/18\n108.162.192.0/18\n190.93.240.0/20\n188.114.96.0/20\n197.234.240.0/22\n198.41.128.0/17\n162.158.0.0/15\n104.16.0.0/13\n104.24.0.0/14\n172.64.0.0/13\n131.0.72.0/22'
  CF6=$'2400:cb00::/32\n2606:4700::/32\n2803:f800::/32\n2405:b500::/32\n2405:8100::/32\n2a06:98c0::/29\n2c0f:f248::/32'
fi

# --- Discover the security-list OCID (instance → VNIC → subnet → security_list_ids) ------
if [ -z "${SECURITY_LIST_OCID:-}" ]; then
  : "${INSTANCE_OCID:?Set INSTANCE_OCID, or set SECURITY_LIST_OCID directly}"
  echo "Discovering the security list from the instance…"
  SUBNET_OCID=$(oci compute instance list-vnics --instance-id "$INSTANCE_OCID" \
                  --query 'data[0]."subnet-id"' --raw-output)
  SECURITY_LIST_OCID=$(oci network subnet get --subnet-id "$SUBNET_OCID" \
                  --query 'data."security-list-ids"[0]' --raw-output)
  echo "  subnet        = $SUBNET_OCID"
  echo "  security-list = $SECURITY_LIST_OCID"
fi

# --- Back up the current ingress rules --------------------------------------------------
TS=$(date +%Y%m%d-%H%M%S)
BACKUP="oci-ingress-backup-${TS}.json"
oci network security-list get --security-list-id "$SECURITY_LIST_OCID" \
  --query 'data."ingress-security-rules"' > "$BACKUP"
echo "Current ingress rules → $BACKUP:"
jq -r '.[] | "  src=\(.source)  proto=\(.protocol)  stateless=\(."is-stateless")  ports=\(((."tcp-options"."destination-port-range") // {min:"any",max:"any"}) | "\(.min)-\(.max)")"' "$BACKUP" 2>/dev/null || cat "$BACKUP"

# --- Build the new ingress rule set (camelCase = OCI-CLI input format) -------------------
_rule() { # $1=source-cidr  $2=port
  jq -nc --arg src "$1" --argjson port "$2" \
    '{source:$src, sourceType:"CIDR_BLOCK", protocol:"6", isStateless:false,
      tcpOptions:{destinationPortRange:{min:$port, max:$port}}}'
}
RULES='[]'
RULES=$(jq -c ". + [$(_rule "$SSH_MGMT_CIDR" "$PORT_SSH")]" <<<"$RULES")          # SSH/22 from mgmt CIDR
while IFS= read -r c; do [ -n "$c" ] && RULES=$(jq -c ". + [$(_rule "$c" "$PORT_HTTPS")]" <<<"$RULES"); done <<<"$CF4"
while IFS= read -r c; do [ -n "$c" ] && RULES=$(jq -c ". + [$(_rule "$c" "$PORT_HTTPS")]" <<<"$RULES"); done <<<"$CF6"
PROPOSED="oci-ingress-proposed-${TS}.json"
echo "$RULES" | jq . > "$PROPOSED"

CF_COUNT=$(( $(grep -c . <<<"$CF4") + $(grep -c . <<<"$CF6") ))
echo
echo "Proposed ingress ($(jq length "$PROPOSED") rules) → $PROPOSED:"
echo "  - SSH/22  from $SSH_MGMT_CIDR"
echo "  - 443     from $CF_COUNT Cloudflare CIDRs (defense-in-depth)"
echo "  - NO 0.0.0.0/0 inbound (egress is left untouched — cloudflared needs outbound 443)."

# --- Apply (only with APPLY=1) ----------------------------------------------------------
if [ "$APPLY" != "1" ]; then
  echo
  echo "DRY-RUN — nothing changed. Review $PROPOSED, confirm SSH_MGMT_CIDR=$SSH_MGMT_CIDR is"
  echo "the range you actually SSH from, then re-run with APPLY=1 to apply."
  exit 0
fi

echo
echo "APPLYING to $SECURITY_LIST_OCID …"
oci network security-list update --security-list-id "$SECURITY_LIST_OCID" \
  --ingress-security-rules "file://${PROPOSED}" --force

echo "Verifying…"
LEFT=$(oci network security-list get --security-list-id "$SECURITY_LIST_OCID" \
        --query 'data."ingress-security-rules"[?source==`0.0.0.0/0`] | length(@)' --raw-output 2>/dev/null || echo "?")
if [ "$LEFT" = "0" ]; then
  echo "OK: no 0.0.0.0/0 inbound rule remains."
else
  echo "WARNING: $LEFT open-to-the-world (0.0.0.0/0) inbound rule(s) still present — review!"
fi
echo "External oracle: from a NON-Cloudflare host, 'curl -m5 https://<origin-ip>' should TIME OUT,"
echo "while the app stays reachable via the edge hostname (through the tunnel). Backup: $BACKUP"

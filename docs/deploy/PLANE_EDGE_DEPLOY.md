# Plane on the edge — `plane.autonomous-agent.dev` (rehost + Cloudflare Tunnel + Access)

Target architecture (the chosen path: **rehost the stack on a cloud server**, **gate with Cloudflare Access**):

```
Browser / Agent
      │  https://plane.autonomous-agent.dev
      ▼
Cloudflare edge ──[Access: Zero-Trust identity gate]──┐
      │  (TLS terminated at edge; no inbound ports open on the origin)
      ▼
cloudflared tunnel  ⇄  Cloud VM (Ubuntu 22.04)
                          └─ docker compose: Plane self-host (~13 services:
                             web, api, worker, beat, admin, space, proxy,
                             postgres, redis, minio, rabbitmq, …)
```

Why this shape: Plane is a **stateful multi-service** app (Postgres + Redis + MinIO + RabbitMQ
with persistent volumes). Cloudflare Pages/Workers can't host that backend, so the origin is a
real VM and Cloudflare provides the **edge + TLS + identity gate** via a Tunnel (no open ports).

---

## Quickstart — scripted path (after the VM exists)

The manual steps below are fully scripted in `plane-selfhost/`. SSH into the VM
(Oracle Cloud default user: `opc` for Oracle Linux, `ubuntu` for Ubuntu images),
then run as one self-contained block:

```bash
# 0. Docker (skip if already installed)
curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker "$USER" && newgrp docker

# 1. get the repo on this deploy branch
git clone <your-repo-url> && cd Agentic-Driven-SDLC
git checkout claude/plane-vm-deploy-turnkey
cd plane-selfhost

# 2. configure + deploy
cp plane.env.template plane.env && $EDITOR plane.env   # set every __REPLACE…__ secret (openssl rand -hex 32)
./deploy.sh                                            # Step 1: bring up the ~13 services; prints first-run steps
# → finish admin setup + create workspace `ascp` + project `ASCP` + an API token in the UI
cp credentials.env.template credentials.env && $EDITOR credentials.env
./deploy.sh                                            # re-run: provisions 8 epics / 49 stories / 186 tasks / 7 cycles
./tunnel.sh                                            # Steps 2–3: Cloudflare Tunnel + Access cutover at the domain
```

`deploy.sh` and `tunnel.sh` are idempotent and safe to re-run. The sections below
are the reference detail behind each scripted step.

---

## Continuous deployment without SSH — OCI Run Command (`.github/workflows/deploy-plane-oci.yml`)

For when you don't have the VM's SSH key: a GitHub runner authenticates to OCI with
an **API signing key** and uses the **Oracle Cloud Agent "Run Command"** service to
make the instance run `deploy.sh` on itself. Triggers on manual dispatch and on push
to `main` touching the deploy surface.

**OCI prerequisites (set in the OCI Console — can't be done from CI):**
- Oracle Cloud Agent → **"Compute Instance Run Command" plugin = Enabled** on the instance.
- The API user has IAM rights for Run Command, e.g. `Allow group <grp> to manage instance-agent-command-family in tenancy` (a tenancy admin already does).

**GitHub secrets** (repo → Settings → Secrets and variables → Actions) — generate a fresh OCI API key, **download** the private key, and never paste it in chat:

| Name | From |
|---|---|
| `OCI_CLI_USER` | Identity → Users → your user → OCID |
| `OCI_CLI_TENANCY` | Profile → Tenancy → OCID |
| `OCI_CLI_FINGERPRINT` | shown after you add the API key |
| `OCI_CLI_KEY_CONTENT` | the API **private** key PEM you downloaded |
| `OCI_CLI_REGION` | e.g. `il-jerusalem-1` |
| `OCI_INSTANCE_OCID` | `ocid1.instance.oc1.il-jerusalem-1.…` (this VM) |
| `OCI_COMPARTMENT_OCID` | the instance's compartment (often = tenancy OCID) |
| `PLANE_ENV` | filled `plane.env` contents (hands-off first boot) |
| `CREDENTIALS_ENV` | filled `credentials.env` (after first-run; enables provisioning) |

The workflow renders the env files and a **short-lived** clone token into the Run
Command content (stored transiently by OCI, then **deleted** by the workflow; GitHub
masks secrets in logs). For a stronger posture, switch repo/env delivery to an Object
Storage pre-authenticated request. SSH variant: `deploy-plane.yml`.

---

## Step 0 — Provision the VM  *(USER action — billable; I can't create paid accounts/payment)*

| Spec | Minimum | Recommended |
|---|---|---|
| vCPU | 2 | 4 |
| RAM | 4 GB | 8 GB |
| Disk | 50 GB SSD | 80 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

Provider options (pick one; rough cost):
- **GCP Compute Engine** `e2-standard-2` (2 vCPU/8 GB) ≈ $50/mo — *you already have the `i-for-ai`
  GCP project, so this stays in an account you control.*
- **Hetzner Cloud** `CX32` (4 vCPU/8 GB) ≈ €11/mo — best price/perf for a single-VM self-host.
- **DigitalOcean** 4 GB/2 vCPU droplet ≈ $24/mo.

**The clean split that respects the security boundary:** *you* create the bare VM and add my SSH
key (or paste me a throwaway one); *I* do everything below (Docker install, Plane deploy, data
migration, tunnel, Access, DNS). No payment instruments or account creation pass through me.

---

## Step 1 — Install Docker + deploy Plane on the VM

```bash
# on the VM
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER" && newgrp docker
# Plane self-host (official installer pins a release + writes plane.env)
mkdir -p ~/plane && cd ~/plane
curl -fsSL -o setup.sh https://github.com/makeplane/plane/releases/latest/download/setup.sh
chmod +x setup.sh && ./setup.sh    # choose the stable channel
# set the public origin BEFORE first boot (CORS / web URL / cookies):
#   plane.env:  WEB_URL=https://plane.autonomous-agent.dev
#               CORS_ALLOWED_ORIGINS=https://plane.autonomous-agent.dev
docker compose up -d
```

### Migrate the existing board (optional — keeps the 8 epics / 49 stories / 186 tasks + cycles)

```bash
# on the Mac (source)
docker exec ascp-plane-db pg_dump -U plane -Fc plane > plane.dump
mc mirror local-minio/uploads ./minio-uploads     # if using mc; else copy the MinIO volume
# copy plane.dump + minio-uploads to the VM, then on the VM:
docker exec -i plane-db pg_restore -U plane -d plane --clean --if-exists < plane.dump
# re-point credentials.env PLANE_API_BASE at the new origin and regenerate an API token.
```
*If you'd rather start fresh on the server, skip the migration and re-run
`plane-integration/provision_plane.py` + `reorg_plane.py` against the new instance.*

---

## Step 2 — Cloudflare Tunnel (edge, no open ports)

```bash
# on the VM
curl -fsSL https://pkg.cloudflare.com/install.sh | sudo bash   # or download the cloudflared deb
sudo apt-get install -y cloudflared
cloudflared tunnel login                       # browser auth to the autonomous-agent.dev zone
cloudflared tunnel create plane-ascp           # writes ~/.cloudflared/<UUID>.json
```

`~/.cloudflared/config.yml`:
```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /home/USER/.cloudflared/<TUNNEL_UUID>.json
ingress:
  - hostname: plane.autonomous-agent.dev
    service: http://localhost:80          # Plane's proxy/web port (compose default)
  - service: http_status:404
```

```bash
cloudflared tunnel route dns plane-ascp plane.autonomous-agent.dev   # creates the CNAME
sudo cloudflared service install                                     # always-on (systemd)
sudo systemctl enable --now cloudflared
```

Equivalent DNS via API (Global Key — zone `ed301b85…`; **rotate this key after**, see Step 5):
```bash
# CNAME plane -> <TUNNEL_UUID>.cfargotunnel.com, proxied
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/dns_records" \
  -H "X-Auth-Email: danielq1603@gmail.com" -H "X-Auth-Key: $CF_GLOBAL_KEY" \
  -H "Content-Type: application/json" \
  --data '{"type":"CNAME","name":"plane","content":"<TUNNEL_UUID>.cfargotunnel.com","proxied":true}'
```

---

## Step 3 — Cloudflare Access (Zero-Trust identity gate)

Self-hosted Access application over the hostname, policy = your identity only:
```bash
ACCOUNT_ID=$(curl -s "https://api.cloudflare.com/client/v4/accounts" \
  -H "X-Auth-Email: danielq1603@gmail.com" -H "X-Auth-Key: $CF_GLOBAL_KEY" | python3 -c "import sys,json;print(json.load(sys.stdin)['result'][0]['id'])")

curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/access/apps" \
  -H "X-Auth-Email: danielq1603@gmail.com" -H "X-Auth-Key: $CF_GLOBAL_KEY" \
  -H "Content-Type: application/json" --data '{
    "name":"Plane ASCP","domain":"plane.autonomous-agent.dev",
    "type":"self_hosted","session_duration":"24h"}'
# then attach a policy: decision=allow, include=[{"email":{"email":"danielq1603@gmail.com"}}]
# IMPORTANT: add a SERVICE-TOKEN bypass policy for the E6 webhook path so Plane can POST
# webhooks to the dispatcher without an interactive Access login (see Step 4).
```

---

## Step 4 — Wire the E6 bridge to the public origin

- **agent → board**: the `plane-ascp` MCP server (`plane-integration/plane_mcp_server.py`) — just
  re-point `PLANE_API_BASE` at `https://plane.autonomous-agent.dev/api/v1` and regenerate the API
  token. Already built + verified.
- **board → agent**: Plane webhook → the dispatcher. Set the Plane webhook target to the
  dispatcher's public endpoint (or keep the dispatcher private and have it *poll* the API).
  Behind Access, give the webhook a **service token** so signed deliveries aren't blocked by the
  identity gate. The dispatcher itself (queue consumer) is the **next build** — see
  `plane-integration/README-mcp.md` and the roadmap.

---

## Step 5 — Harden / rotate

- **Rotate the Global API Key now** (it was used here and is exposed in chat). In the Cloudflare
  dashboard → My Profile → API Tokens → *Roll* the Global Key, **or** mint a scoped **API Token**
  (Account: Cloudflare Tunnel · Edit; Zone: DNS · Edit + Zone · Read on `autonomous-agent.dev`;
  Account: Access: Apps · Edit) and use that going forward.
- VM firewall: deny all inbound except SSH (cloudflared makes only outbound connections — no
  80/443 ingress needed). Consider Cloudflare Tunnel for SSH too.
- Plane: strong admin password, `SECRET_KEY` set, S3/MinIO creds rotated off defaults.

---

## Staging option (live today, server later)

If you want `plane.autonomous-agent.dev` **live now** while the VM is provisioned, the same Tunnel
+ Access can run from this Mac against the existing local Plane (Steps 2–3, run on the Mac). It's
Mac-dependent uptime, but it gets the public, Access-gated URL working immediately; the rehost
then becomes a data move + re-point with no URL change.

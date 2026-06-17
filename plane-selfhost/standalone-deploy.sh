#!/usr/bin/env bash
# =============================================================================
# ASCP Plane — self-contained one-shot deploy for the Oracle Ampere A1 VM
# (Ubuntu 24.04, aarch64). PASTE THIS INTO A ROOT SHELL ON THE VM and run:
#     sudo -i        # become root
#     # …paste the whole script…  OR save as deploy.sh and: bash deploy.sh
#
# No SSH-from-CI, no git, no OCI Run Command plugin needed. Idempotent: it
# preserves an existing plane.env (so secrets stay stable across re-runs).
# Brings the full Plane stack up on localhost:80; publish it at the domain
# with a Cloudflare Tunnel afterwards (instructions printed at the end).
# =============================================================================
set -Eeuo pipefail

DIR=/opt/ascp-plane
log(){ printf '\033[1;36m[ascp]\033[0m %s\n' "$*"; }

mkdir -p "$DIR" && cd "$DIR"

# ── 1. Docker (OS-aware: Oracle Linux/RHEL via dnf + Docker CE repo; else the
#       get.docker.com convenience script, which doesn't support Oracle Linux) ──
if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker…"
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y dnf-plugins-core 2>/dev/null || dnf install -y yum-utils
    dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo 2>/dev/null \
      || dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
    dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  else
    curl -fsSL https://get.docker.com | sh
  fi
fi
systemctl enable --now docker >/dev/null 2>&1 || true

# ── 2. docker-compose.yml (Plane v1.3.1 community stack, embedded) ────────────
log "Writing docker-compose.yml…"
cat > docker-compose.yml <<'COMPOSE'
x-db-env: &db-env
  PGHOST: ${PGHOST:-plane-db}
  PGDATABASE: ${PGDATABASE:-plane}
  POSTGRES_USER: ${POSTGRES_USER:-plane}
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-plane}
  POSTGRES_DB: ${POSTGRES_DB:-plane}
  POSTGRES_PORT: ${POSTGRES_PORT:-5432}
  PGDATA: ${PGDATA:-/var/lib/postgresql/data}

x-redis-env: &redis-env
  REDIS_HOST: ${REDIS_HOST:-plane-redis}
  REDIS_PORT: ${REDIS_PORT:-6379}
  REDIS_URL: ${REDIS_URL:-redis://plane-redis:6379/}

x-minio-env: &minio-env
  MINIO_ROOT_USER: ${AWS_ACCESS_KEY_ID:-access-key}
  MINIO_ROOT_PASSWORD: ${AWS_SECRET_ACCESS_KEY:-secret-key}

x-aws-s3-env: &aws-s3-env
  AWS_REGION: ${AWS_REGION:-}
  AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-access-key}
  AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-secret-key}
  AWS_S3_ENDPOINT_URL: ${AWS_S3_ENDPOINT_URL:-http://plane-minio:9000}
  AWS_S3_BUCKET_NAME: ${AWS_S3_BUCKET_NAME:-uploads}

x-proxy-env: &proxy-env
  APP_DOMAIN: ${APP_DOMAIN:-localhost}
  FILE_SIZE_LIMIT: ${FILE_SIZE_LIMIT:-5242880}
  CERT_EMAIL: ${CERT_EMAIL}
  CERT_ACME_CA: ${CERT_ACME_CA}
  CERT_ACME_DNS: ${CERT_ACME_DNS}
  LISTEN_HTTP_PORT: ${LISTEN_HTTP_PORT:-80}
  LISTEN_HTTPS_PORT: ${LISTEN_HTTPS_PORT:-443}
  BUCKET_NAME: ${AWS_S3_BUCKET_NAME:-uploads}
  SITE_ADDRESS: ${SITE_ADDRESS:-:80}

x-mq-env: &mq-env
  RABBITMQ_HOST: ${RABBITMQ_HOST:-plane-mq}
  RABBITMQ_PORT: ${RABBITMQ_PORT:-5672}
  RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-plane}
  RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-plane}
  RABBITMQ_DEFAULT_VHOST: ${RABBITMQ_VHOST:-plane}
  RABBITMQ_VHOST: ${RABBITMQ_VHOST:-plane}

x-live-env: &live-env
  API_BASE_URL: ${API_BASE_URL:-http://api:8000}
  LIVE_SERVER_SECRET_KEY: ${LIVE_SERVER_SECRET_KEY:-2FiJk1U2aiVPEQtzLehYGlTSnTnrs7LW}

x-app-env: &app-env
  WEB_URL: ${WEB_URL:-http://localhost}
  DEBUG: ${DEBUG:-0}
  CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS}
  GUNICORN_WORKERS: 1
  USE_MINIO: ${USE_MINIO:-1}
  DATABASE_URL: ${DATABASE_URL}
  SECRET_KEY: ${SECRET_KEY:-60gp0byfz2dvffa45cxl20p1scy9xbpf6d8c5y0geejgkyp1b5}
  AMQP_URL: ${AMQP_URL}
  API_KEY_RATE_LIMIT: ${API_KEY_RATE_LIMIT:-60/minute}
  MINIO_ENDPOINT_SSL: ${MINIO_ENDPOINT_SSL:-0}
  LIVE_SERVER_SECRET_KEY: ${LIVE_SERVER_SECRET_KEY:-2FiJk1U2aiVPEQtzLehYGlTSnTnrs7LW}
  WEBHOOK_ALLOWED_IPS: ${WEBHOOK_ALLOWED_IPS:-}
  WEBHOOK_ALLOWED_HOSTS: ${WEBHOOK_ALLOWED_HOSTS:-}

services:
  web:
    image: makeplane/plane-frontend:${APP_RELEASE:-stable}
    deploy:
      replicas: ${WEB_REPLICAS:-1}
      restart_policy:
        condition: any
    depends_on:
      - api
      - worker

  space:
    image: makeplane/plane-space:${APP_RELEASE:-stable}
    deploy:
      replicas: ${SPACE_REPLICAS:-1}
      restart_policy:
        condition: any
    depends_on:
      - api
      - worker
      - web

  admin:
    image: makeplane/plane-admin:${APP_RELEASE:-stable}
    deploy:
      replicas: ${ADMIN_REPLICAS:-1}
      restart_policy:
        condition: any
    depends_on:
      - api
      - web

  live:
    image: makeplane/plane-live:${APP_RELEASE:-stable}
    environment:
      <<: [*live-env, *redis-env]
    deploy:
      replicas: ${LIVE_REPLICAS:-1}
      restart_policy:
        condition: any
    depends_on:
      - api
      - web

  api:
    image: makeplane/plane-backend:${APP_RELEASE:-stable}
    command: ./bin/docker-entrypoint-api.sh
    deploy:
      replicas: ${API_REPLICAS:-1}
      restart_policy:
        condition: any
    volumes:
      - logs_api:/code/plane/logs
    environment:
      <<: [*app-env, *db-env, *redis-env, *minio-env, *aws-s3-env, *proxy-env]
    depends_on:
      - plane-db
      - plane-redis
      - plane-mq

  worker:
    image: makeplane/plane-backend:${APP_RELEASE:-stable}
    command: ./bin/docker-entrypoint-worker.sh
    deploy:
      replicas: ${WORKER_REPLICAS:-1}
      restart_policy:
        condition: any
    volumes:
      - logs_worker:/code/plane/logs
    environment:
      <<: [*app-env, *db-env, *redis-env, *minio-env, *aws-s3-env, *proxy-env]
    depends_on:
      - api
      - plane-db
      - plane-redis
      - plane-mq

  beat-worker:
    image: makeplane/plane-backend:${APP_RELEASE:-stable}
    command: ./bin/docker-entrypoint-beat.sh
    deploy:
      replicas: ${BEAT_WORKER_REPLICAS:-1}
      restart_policy:
        condition: any
    volumes:
      - logs_beat-worker:/code/plane/logs
    environment:
      <<: [*app-env, *db-env, *redis-env, *minio-env, *aws-s3-env, *proxy-env]
    depends_on:
      - api
      - plane-db
      - plane-redis
      - plane-mq

  migrator:
    image: makeplane/plane-backend:${APP_RELEASE:-stable}
    command: ./bin/docker-entrypoint-migrator.sh
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
    volumes:
      - logs_migrator:/code/plane/logs
    environment:
      <<: [*app-env, *db-env, *redis-env, *minio-env, *aws-s3-env, *proxy-env]
    depends_on:
      - plane-db
      - plane-redis

  plane-db:
    image: postgres:15.7-alpine
    command: postgres -c 'max_connections=1000'
    deploy:
      replicas: 1
      restart_policy:
        condition: any
    environment:
      <<: *db-env
    volumes:
      - pgdata:/var/lib/postgresql/data

  plane-redis:
    image: valkey/valkey:7.2.11-alpine
    deploy:
      replicas: 1
      restart_policy:
        condition: any
    volumes:
      - redisdata:/data

  plane-mq:
    image: rabbitmq:3.13.6-management-alpine
    deploy:
      replicas: 1
      restart_policy:
        condition: any
    environment:
      <<: *mq-env
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  plane-minio:
    image: minio/minio:latest
    command: server /export --console-address ":9090"
    deploy:
      replicas: 1
      restart_policy:
        condition: any
    environment:
      <<: *minio-env
    volumes:
      - uploads:/export

  proxy:
    image: makeplane/plane-proxy:${APP_RELEASE:-stable}
    deploy:
      replicas: 1
      restart_policy:
        condition: any
    environment:
      <<: *proxy-env
    ports:
      - target: 80
        published: ${LISTEN_HTTP_PORT:-80}
        protocol: tcp
        mode: host
      - target: 443
        published: ${LISTEN_HTTPS_PORT:-443}
        protocol: tcp
        mode: host
    volumes:
      - proxy_config:/config
      - proxy_data:/data
    depends_on:
      - web
      - api
      - space
      - admin
      - live

volumes:
  pgdata:
  redisdata:
  uploads:
  logs_api:
  logs_worker:
  logs_beat-worker:
  logs_migrator:
  rabbitmq_data:
  proxy_config:
  proxy_data:
COMPOSE

# ── 3. plane.env — generate strong secrets ONCE; preserve on re-run ───────────
if [ ! -f plane.env ]; then
  log "Generating plane.env with fresh secrets…"
  SECRET_KEY=$(openssl rand -hex 32)
  LIVE_KEY=$(openssl rand -hex 32)
  DBPASS=$(openssl rand -hex 16)
  MQPASS=$(openssl rand -hex 16)
  MINIO_AK=$(openssl rand -hex 12)
  MINIO_SK=$(openssl rand -hex 24)
  # URL schemes kept as separate vars so the committed source never contains a
  # literal `scheme://user:pass@host` (the runtime-written plane.env is gitignored).
  PG=postgresql
  MQ=amqp
  cat > plane.env <<ENV
APP_RELEASE=stable
APP_DOMAIN=plane.autonomous-agent.dev
WEB_URL=https://plane.autonomous-agent.dev
CORS_ALLOWED_ORIGINS=https://plane.autonomous-agent.dev
LISTEN_HTTP_PORT=80
LISTEN_HTTPS_PORT=443
SITE_ADDRESS=:80
FILE_SIZE_LIMIT=5242880
SECRET_KEY=${SECRET_KEY}
LIVE_SERVER_SECRET_KEY=${LIVE_KEY}
PGHOST=plane-db
PGDATABASE=plane
POSTGRES_USER=plane
POSTGRES_PASSWORD=${DBPASS}
POSTGRES_DB=plane
POSTGRES_PORT=5432
DATABASE_URL=${PG}://plane:${DBPASS}@plane-db/plane
REDIS_HOST=plane-redis
REDIS_PORT=6379
REDIS_URL=redis://plane-redis:6379/
RABBITMQ_HOST=plane-mq
RABBITMQ_PORT=5672
RABBITMQ_USER=plane
RABBITMQ_PASSWORD=${MQPASS}
RABBITMQ_VHOST=plane
AMQP_URL=${MQ}://plane:${MQPASS}@plane-mq:5672/plane
USE_MINIO=1
AWS_REGION=
AWS_ACCESS_KEY_ID=${MINIO_AK}
AWS_SECRET_ACCESS_KEY=${MINIO_SK}
AWS_S3_ENDPOINT_URL=http://plane-minio:9000
AWS_S3_BUCKET_NAME=uploads
MINIO_ENDPOINT_SSL=0
DEBUG=0
GUNICORN_WORKERS=1
API_KEY_RATE_LIMIT=60/minute
WEBHOOK_ALLOWED_IPS=
WEBHOOK_ALLOWED_HOSTS=
ENV
  chmod 600 plane.env
else
  log "plane.env already exists — keeping existing secrets."
fi

# ── 4. ARM / Ampere preflight: native arm64 if available, else QEMU amd64 ─────
if [ "$(uname -m)" = "aarch64" ] || [ "$(uname -m)" = "arm64" ]; then
  if docker manifest inspect makeplane/plane-backend:stable 2>/dev/null | grep -q 'arm64'; then
    log "Native arm64 Plane images available — running natively."
  else
    log "No arm64 Plane images — enabling QEMU amd64 emulation (slower)…"
    docker run --privileged --rm tonistiigi/binfmt --install all >/dev/null 2>&1 || true
    export DOCKER_DEFAULT_PLATFORM=linux/amd64
  fi
fi

# ── 5. Pull + bring up ────────────────────────────────────────────────────────
log "Pulling images + starting the stack (this can take 10–20 min under emulation)…"
docker compose --env-file plane.env pull
docker compose --env-file plane.env up -d

# ── 6. Wait for the surface ───────────────────────────────────────────────────
log "Waiting for Plane to answer on http://localhost:80/ …"
for i in $(seq 1 60); do
  if curl -fsS -o /dev/null http://localhost:80/; then log "Plane is UP."; break; fi
  sleep 5
done

cat <<'NEXT'

────────────────────────────────────────────────────────────────────────────
 Plane stack is RUNNING on this VM (localhost:80).

 NEXT STEPS
 1) Publish it at https://plane.autonomous-agent.dev with a Cloudflare Tunnel
    (no inbound ports needed):
        curl -fsSL https://pkg.cloudflare.com/install.sh | sudo bash
        sudo apt-get install -y cloudflared
        cloudflared tunnel login                       # browser auth to the zone
        cloudflared tunnel create plane-ascp
        cloudflared tunnel route dns plane-ascp plane.autonomous-agent.dev
        # ~/.cloudflared/config.yml ingress → service: http://localhost:80
        sudo cloudflared service install && sudo systemctl enable --now cloudflared

 2) Open https://plane.autonomous-agent.dev, complete first-run admin setup,
    create workspace slug  ascp  and project  ASCP , then add an API token.

 3) Provision the 8 epics / 49 stories / 186 tasks / 7 cycles: on the VM, clone
    this repo (needs a GitHub token for the private repo), fill credentials.env
    from plane-selfhost/credentials.env.template, and run:
        python3 plane-integration/provision_plane.py all
        python3 plane-integration/reorg_plane.py all

 Manage:  cd /opt/ascp-plane && docker compose --env-file plane.env ps
────────────────────────────────────────────────────────────────────────────
NEXT

# Agentic SDLC Control Plane — Plane Implementation Blueprint

> Plane workspace driving the autonomous Spec-to-Evidence delivery engine: intent→verified software, with agents as memory/verifier/scope-enforcer/auditor and a fail-closed completion gate.

Generated from the reconciled `.kiro/specs/spec-to-evidence-control` spec (32 EARS requirements / 32 properties / 8 tables / 57 tasks / 49 waves) and grounded in a live self-hosted Plane v1.3.1 instance (`http://localhost:8090`, workspace `ascp`, project `ASCP`).


---

## 1. Project-Level Configuration

**Project:** Agentic SDLC Control Plane (`ASCP`)

Plane workspace driving the autonomous Spec-to-Evidence delivery engine: intent→verified software, with agents as memory/verifier/scope-enforcer/auditor and a fail-closed completion gate.


### 1.1 Custom States (agent workflow)

| State | Plane group | Meaning |
|---|---|---|
| `Backlog` | backlog | unrefined intake |
| `Agent-Triaged` | unstarted | classified by the initializer; agent_role + requirement_id assigned |
| `Spec-Compiling` | started | initializer compiling EARS + running spec_validator (Z3) |
| `Spec-Verified` | started | violation_count==0; feature_list.json emitted (all unproven) |
| `Plan-Approved` | started | human plan approval written (plan-approved.json, SHA-bound) |
| `Agent-Executing` | started | implementer building one slice in an isolated git worktree |
| `In-Verification` | started | verifier running 5-layer checks; capturing Evidence_Record |
| `Human-Review` | started | PR + human reviewer gate |
| `Done` | completed | proven with evidence; all gates (Stop+OPA+CI) pass |
| `HANDOFF` | cancelled | cap/budget/no-progress reached; handed to a human (distinct from Done) |
| `Blocked` | cancelled | a gate blocked (exit 2): unproven dep, failed integrity/approval |
| `Failed` | cancelled | verification failed; evidence withheld |

### 1.2 Custom Fields

| Field | Type | Values / use |
|---|---|---|
| `agent_role` | dropdown | initializer | implementer | verifier | research | human |
| `requirement_id` | text | e.g. REQ-GATE-002 |
| `evidence_status` | dropdown | unproven | proven | failed |
| `coverage_type` | dropdown | functional | NFR | WIRING |
| `run_state` | dropdown | running | complete | handoff | blocked |
| `worktree_branch` | text | git branch for the slice (traceability) |
| `agent_run_id` | text | LLM agent run id (traceability triple: issue↔branch↔run) |
| `ears_pattern` | dropdown | ubiquitous | event-driven | state-driven | unwanted | optional | complex |
| `gate` | dropdown | stop | pretooluse | posttooluse | subagentstop | opa | ci |
| `output_hash` | text | sha256:<64hex> evidence hash |

### 1.3 Labels

`agent:initializer` · `agent:coder` · `agent:tester` · `agent:research` · `human:review` · `priority:blocking` · `priority:high` · `priority:normal` · `type:functional` · `type:nfr` · `type:wiring` · `gate:stop` · `gate:completion` · `gate:security` · `phase:0` · `phase:1` · `phase:2` · `phase:3` · `phase:4` · `handoff` · `blocked` · `failed`


---

## 2–4. Epics, EARS User Stories & Tasks


# Epic E1 — Core Plane Infrastructure & Self-Hosting

## Overview

Plane is the **PM control plane** for the Agentic SDLC Control Plane (project identifier `ASCP`): the human-facing surface where every coverage item, gate decision, agent run, and HANDOFF is visible as a Plane issue moving through the twelve-state workflow (`Backlog → Agent-Triaged → Spec-Compiling → Spec-Verified → Plan-Approved → Agent-Executing → In-Verification → Human-Review → Done`, with the three terminal cancelled states `HANDOFF`, `Blocked`, `Failed`). Before any of that content can exist, Plane itself must be **self-hosted, durable, observable, and operable**. E1 is that substrate.

E1 owns the Docker deployment described by `/Users/danielmanzela/Agentic-Driven SDLC Platform/plane-selfhost/docker-compose.yml` and `plane.env`: the ten application services (`web`, `space`, `admin`, `live`, `api`, `worker`, `beat-worker`, `migrator`) plus the four backing stores (`plane-db` Postgres 15.7, `plane-redis` Valkey 7.2, `plane-mq` RabbitMQ 3.13, `plane-minio` MinIO) and the `proxy` (Caddy) reverse proxy fronting the stack on **host port 8090** (`LISTEN_HTTP_PORT=8090`, `APP_DOMAIN=localhost:8090`, HTTPS on 8453). It also owns the operational guarantees that make Plane trustworthy as a control plane: env-driven configuration, backup/restore of the durable tier, version upgrades through the `migrator`, horizontal scaling via the `*_REPLICAS` knobs, and health/readiness verification before the platform's REST/Webhook surface is declared usable by downstream epics.

**Grounding in the reconciled `.kiro` spec.** This epic does not implement the agentic control loop — that lives in the `.kiro/specs/spec-to-evidence-control` requirements/design/tasks set. E1 is the *infrastructure* the spec presumes. Three load-bearing spec obligations anchor E1's stories:

- **REQ-16 (Durable Storage — REQ-STORE-001..003), criterion 16.1**: "THE System SHALL persist requirements, coverage state, traceability links, Evidence_Records, and run state in a managed Postgres database." The reconciled design (`design.md:558`) defines an **eight-table durable store** (`requirements`, `coverage_items`, `traceability_links`, `evidence_records`, `run_state`, `domain_baseline_checklists`, `requirement_versions`, `gate_audit_log`; migrations `001`–`008`). In the canonical spec that store is Neon serverless Postgres; **in this self-hosted deployment the Plane `plane-db` Postgres 15.7 service is that managed Postgres tier** for the ASCP workspace and its companion durable artifacts. E1 stands it up, makes it durable (named `pgdata` volume), backs it up, and migrates it on upgrade.
- **REQ-16.2**: "WHEN evidence is captured, THE System SHALL store the artifact or a content-addressed reference and link it to the requirement ID and commit SHA." Evidence blobs are content-addressed by `output_hash` (`design.md:537` — "retained as a content-addressed blob keyed by `output_hash`"). The Plane **`plane-minio` object store** (bucket `uploads`, S3-compatible) is the self-hosted durable evidence-blob tier E1 provisions and backs up.
- **REQ-11 (Session Continuity & Durable State — REQ-STATE-001..004) and REQ-17.4 (sandbox/isolation)**: durable mutable run state lives "outside model context, in files, git history, and the durable Postgres store" (11.1), and untrusted agent code runs in an isolated sandbox with the per-slice worktree mounted in (17.4). E1's substrate must therefore *survive crash/restart* (Docker `restart_policy: condition: any` on every long-lived service, named volumes for all stateful tiers) so that resumed state is real, not lost.

The Postgres tier additionally backstops the **fail-closed availability contract** the gates depend on (`design.md:1374`, Note N-25): every gate must reach the same allow/block decision from file-backed state that it would from Postgres and *never fail open*. That contract is only meaningful if the Postgres tier is reliably up, restartable, and recoverable — which is E1's job.

**Scope boundary.** E1 stands up the substrate and exposes Plane's REST + Webhook API surface as a *health-verified, reachable* endpoint at `http://localhost:8090/api/`. It does **not** create the ASCP project, states, fields, labels, or issues — that is the workspace-provisioning epic (it consumes E1's verified API). The "API (Plane Webhooks/REST)" tasks in E1 are limited to: confirming the API service is reachable and healthy, minting the admin/instance bootstrap, registering the first machine API token used by later epics, and standing up webhook egress configuration (allowlist env: `WEBHOOK_ALLOWED_IPS`, `WEBHOOK_ALLOWED_HOSTS`) so downstream gate-decision webhooks have a target. All E1 stories carry `agent_role: human` (the Delivery Owner / Operator owns infrastructure per the spec's actor model) and `requirement_id` values in the `REQ-INFRA-*` namespace, each cross-referencing the upstream `.kiro` requirement it serves.

**Requirement set (8 infra requirements / user stories):**

| ID | Title | Anchors |
|----|-------|---------|
| REQ-INFRA-001 | Self-Hosted Docker Topology Stand-Up | substrate for all `.kiro` reqs |
| REQ-INFRA-002 | Reverse Proxy & Port-8090 Ingress | REQ-12 (operator access surface) |
| REQ-INFRA-003 | Environment-Driven Configuration & Secrets | REQ-17.5 (no secrets in prompts/URLs) |
| REQ-INFRA-004 | Durable Storage Tier (Postgres + MinIO + RabbitMQ + Redis) | REQ-16, REQ-11 |
| REQ-INFRA-005 | Database Migration & Version Upgrade | REQ-16, REQ-22 (amendment migrations) |
| REQ-INFRA-006 | Backup & Restore of the Durable Tier | REQ-16.3 (reconstructable store) |
| REQ-INFRA-007 | Horizontal Scaling via Replicas | REQ-15 (orchestration headroom) |
| REQ-INFRA-008 | Health, Readiness & Liveness Verification | REQ-12 (observability), gate availability |

---

## REQ-INFRA-001 — Self-Hosted Docker Topology Stand-Up

**User story.** As the Delivery Owner / Operator, I want the full Plane stack — ten application services plus four backing stores and the proxy — to come up from a single `docker compose up` against `docker-compose.yml` + `plane.env`, so the PM control plane that drives the autonomous Spec-to-Evidence engine exists as a reproducible, self-hosted substrate rather than a SaaS dependency.

**Maps to.** Substrate for the entire `.kiro/specs/spec-to-evidence-control` system (the spec presumes a running Plane PM control plane; `design.md:33` casts the Delivery Owner / Operator as the human who "reviews PR + monitors trace").

**EARS lines.**
- **Ubiquitous** — THE system shall define every long-lived Plane service (`web`, `space`, `admin`, `live`, `api`, `worker`, `beat-worker`, `plane-db`, `plane-redis`, `plane-mq`, `plane-minio`, `proxy`) in `docker-compose.yml` with `restart_policy.condition: any`, and the one-shot `migrator` with `restart_policy.condition: on-failure`.
- **Event-Driven** — WHEN `docker compose --env-file plane.env up -d` is invoked, the system shall start all services in dependency order such that `api`/`worker`/`beat-worker`/`migrator` wait on `plane-db`, `plane-redis`, and `plane-mq`, and `proxy` waits on `web`, `api`, `space`, `admin`, and `live`.
- **State-Driven** — WHILE the `migrator` job has not exited `0`, the system shall hold the `api`, `worker`, and `beat-worker` services from serving traffic that depends on an unmigrated schema.
- **Unwanted** — IF any backing store (`plane-db`, `plane-redis`, `plane-mq`, `plane-minio`) exits, THEN the system shall restart it (`restart_policy: any`) and the dependent application services shall reconnect without manual intervention.
- **Optional** — WHERE the operator already runs an external Postgres, S3-compatible store, or reverse proxy, the system shall allow the corresponding bundled service (`plane-db`, `plane-minio`, `proxy`) to be commented out and replaced via env (`DATABASE_URL`, `AWS_S3_ENDPOINT_URL`, external proxy).

**Acceptance criteria.**
1. `docker compose --env-file plane.env config` validates with zero errors and resolves the `x-*` env anchors (`x-db-env`, `x-redis-env`, `x-minio-env`, `x-aws-s3-env`, `x-proxy-env`, `x-mq-env`, `x-live-env`, `x-app-env`) onto the services that reference them.
2. After `up -d`, `docker compose ps` shows exactly one running container for each single-replica service and `R` running state for all, and `migrator` shows `Exited (0)`.
3. The named volumes `pgdata`, `redisdata`, `uploads`, `rabbitmq_data`, `proxy_config`, `proxy_data`, and the four `logs_*` volumes are created and bound to their services.
4. `depends_on` ordering is verified: stopping `plane-db` and re-running surfaces `api` reconnect attempts in `logs_api`, and a full restart brings the stack back to all-running.
5. The stack uses the pinned images `postgres:15.7-alpine`, `valkey/valkey:7.2.11-alpine`, `rabbitmq:3.13.6-management-alpine`, `minio/minio:latest`, and `makeplane/plane-*:${APP_RELEASE:-stable}` (release pin via `APP_RELEASE`).

**Assigned attributes.** state `Plan-Approved`; agent_role `human`; requirement_id `REQ-INFRA-001`; coverage_type `WIRING` (service-topology connection obligation); labels `priority:blocking`, `phase:0`, `type:wiring`, `human:review`.

**Agent state-flow.** A Plane issue tracking this story is created in `Backlog`, triaged to `Agent-Triaged` with `agent_role=human` and `requirement_id=REQ-INFRA-001`, advanced to `Plan-Approved` once the compose topology is reviewed, then `Agent-Executing` while the operator brings the stack up, `In-Verification` while `docker compose ps`/health checks run, `Human-Review` for operator sign-off, and `Done` when all five acceptance criteria pass with captured evidence (compose-config output + `ps` snapshot as the `output_hash`-referenced artifact). If a backing image fails to pull or a port collides, the issue moves to `Blocked` (gate: infra unproven dependency).

---

## REQ-INFRA-002 — Reverse Proxy & Port-8090 Ingress

**User story.** As the Operator, I want all browser and API traffic to reach Plane through the `proxy` service on host port **8090** (HTTP) / **8453** (HTTPS), so the control plane has one stable, non-conflicting ingress that fronts `web`, `space`, `admin`, `live`, and `api` without exposing each service's internal port.

**Maps to.** REQ-12 (Observability — the operator's "live, requirement-tagged" view of the agent is reached through this ingress) and the operator-access surface the `.kiro` design assumes (`design.md:63`, "reviews PR + monitors trace").

**EARS lines.**
- **Ubiquitous** — THE system shall publish the `proxy` service's container port 80 on host port `${LISTEN_HTTP_PORT:-80}` set to **8090**, and container port 443 on host port `${LISTEN_HTTPS_PORT:-443}` set to **8453**, in `host` mode.
- **Event-Driven** — WHEN a request arrives at `http://localhost:8090`, the proxy shall route it to `web` (app), `/spaces` to `space`, `/god-mode` (admin) to `admin`, `/live` to `live`, and `/api` to `api:8000` per the Caddy `SITE_ADDRESS` configuration.
- **State-Driven** — WHILE `APP_DOMAIN=localhost:8090`, the system shall set `WEB_URL=http://localhost:8090` and `CORS_ALLOWED_ORIGINS=http://localhost:8090` so the SPA, CORS, and absolute-URL generation agree on the 8090 origin.
- **Unwanted** — IF host port 8090 is already bound by another process, THEN `docker compose up` shall fail fast on the proxy port-publish step rather than silently binding a different port, and the operator shall remediate before the stack is declared healthy.
- **Optional** — WHERE TLS is required, the system shall accept `CERT_EMAIL` + `CERT_ACME_CA` (HTTP-01) or `CERT_ACME_DNS` (DNS-01) so the proxy provisions a certificate and serves HTTPS on 8453.

**Acceptance criteria.**
1. `curl -sf http://localhost:8090/` returns HTTP 200 and serves the Plane web app shell.
2. `curl -sf http://localhost:8090/api/instances/` returns a JSON instance descriptor from the `api` service (proxied), confirming the `/api` route reaches `api:8000`.
3. The proxy's published ports are exactly `8090->80` and `8453->443` (verified via `docker compose ps` port column); no internal service port (`8000`, `9000`, `5432`, `6379`, `5672`) is published to the host.
4. CORS preflight from origin `http://localhost:8090` is accepted; an origin not in `CORS_ALLOWED_ORIGINS` is rejected.
5. `proxy_config` and `proxy_data` volumes persist the Caddy config and any provisioned certs across a proxy restart.

**Assigned attributes.** state `Plan-Approved`; agent_role `human`; requirement_id `REQ-INFRA-002`; coverage_type `WIRING`; labels `priority:blocking`, `phase:0`, `type:wiring`, `gate:security`, `human:review`.

**Agent state-flow.** Issue triaged to `Agent-Triaged` (`requirement_id=REQ-INFRA-002`), `Plan-Approved` after the port map is confirmed non-conflicting (8090/8453 chosen specifically to avoid the default 80/443), `Agent-Executing` during proxy bring-up, `In-Verification` while the five `curl`/port checks run (the 200/JSON responses captured as the Evidence_Record artifact), `Human-Review`, then `Done`. A port collision routes to `Blocked` until remediated.

---

## REQ-INFRA-003 — Environment-Driven Configuration & Secrets

**User story.** As the Operator, I want every tunable — credentials, hosts, URLs, replica counts, secret keys, webhook allowlists — sourced from `plane.env` and never hard-coded into images or committed defaults that ship to production, so configuration is reproducible and the spec's "no secrets in prompts/spans/URLs" invariant (REQ-17.5) holds at the substrate layer.

**Maps to.** REQ-17.5 (REQ-SEC-005 — "THE System SHALL never place credentials or secrets in prompts, spans, or URLs"; the substrate must not leak the Postgres/MinIO/RabbitMQ credentials or `SECRET_KEY`/`LIVE_SERVER_SECRET_KEY` into logs or published URLs).

**EARS lines.**
- **Ubiquitous** — THE system shall resolve all service configuration from `plane.env` via the compose `${VAR:-default}` mechanism and the `x-*` anchor blocks, with no credential or secret literal embedded in `docker-compose.yml` beyond a clearly-marked dev default.
- **Event-Driven** — WHEN the stack starts, the system shall inject `DATABASE_URL` (default `postgresql://plane:plane@plane-db/plane`), `AMQP_URL` (`amqp://plane:plane@plane-mq:5672/plane`), `REDIS_URL`, and the MinIO `AWS_*` credentials into `api`/`worker`/`beat-worker`/`migrator` from env.
- **State-Driven** — WHILE running in any non-local deployment, the system shall require the operator to override the shipped dev defaults for `SECRET_KEY`, `LIVE_SERVER_SECRET_KEY`, `POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD`, and `AWS_SECRET_ACCESS_KEY` with high-entropy values.
- **Unwanted** — IF `LIVE_SERVER_SECRET_KEY` or `SECRET_KEY` is left at its shipped placeholder in a non-DEBUG (`DEBUG=0`) deployment, THEN the configuration shall be treated as insecure and flagged for remediation before the stack is declared production-ready.
- **Optional** — WHERE webhook egress to private/internal targets is needed, the system shall honor `WEBHOOK_ALLOWED_IPS` (CIDR list) and `WEBHOOK_ALLOWED_HOSTS` (hostname list) to bypass the SSRF private-IP guard only for explicitly allowlisted targets.

**Acceptance criteria.**
1. Grepping the running containers' environment and the proxy/app logs shows no Postgres/MinIO/RabbitMQ password or `SECRET_KEY` value echoed in a request URL or an access-log line.
2. Every secret/credential in `plane.env` (`POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD`, `AWS_SECRET_ACCESS_KEY`, `SECRET_KEY`, `LIVE_SERVER_SECRET_KEY`) is overridable and the override propagates to the consuming service (verified by reading the effective env of `api`).
3. `DATABASE_URL`, `AMQP_URL`, and `REDIS_URL` resolve correctly when left blank in `plane.env` (compose falls back to the `${VAR:-default}` form) and when explicitly set.
4. `WEBHOOK_ALLOWED_IPS` / `WEBHOOK_ALLOWED_HOSTS` are parsed and applied: a webhook to a non-allowlisted private IP is refused; an allowlisted one is permitted.
5. `DEBUG=0` is the deployed default; flipping `DEBUG=1` is recognized as a non-production posture.

**Assigned attributes.** state `Plan-Approved`; agent_role `human`; requirement_id `REQ-INFRA-003`; coverage_type `NFR` (security/config posture); labels `priority:blocking`, `phase:0`, `type:nfr`, `gate:security`, `human:review`.

**Agent state-flow.** `Agent-Triaged` (`requirement_id=REQ-INFRA-003`, `coverage_type=NFR`), `Plan-Approved` after the env contract is reviewed, `Agent-Executing` while secrets are rotated off the shipped defaults, `In-Verification` while the no-leak grep and allowlist tests run (the grep output + webhook-refusal capture form the Evidence_Record), `Human-Review`, `Done`. A discovered placeholder secret in a `DEBUG=0` deployment routes the issue to `Failed` (verification failed; evidence withheld) until secrets are rotated.

---

## REQ-INFRA-004 — Durable Storage Tier (Postgres + MinIO + RabbitMQ + Redis)

**User story.** As the Data Owner, I want the four stateful tiers — `plane-db` Postgres (the eight-table durable store + Plane's own schema), `plane-minio` (content-addressed evidence blobs, bucket `uploads`), `plane-mq` RabbitMQ (the worker task queue), and `plane-redis` Valkey (cache/session) — each persisted on a named Docker volume that survives container recreation, so the control plane's memory is durable and queryable exactly as REQ-16 demands.

**Maps to.** REQ-16 (REQ-STORE-001..003): 16.1 (persist requirements/coverage/traceability/evidence/run-state in managed Postgres), 16.2 (store the evidence artifact or content-addressed reference linked to requirement ID + commit SHA), 16.3 (Postgres as single source of truth, reconstructable independently of any model session); also REQ-11.1 (durable run state outside model context).

**EARS lines.**
- **Ubiquitous** — THE system shall back `plane-db` with the `pgdata` volume, `plane-redis` with `redisdata`, `plane-mq` with `rabbitmq_data`, and `plane-minio` with the `uploads` volume, so all durable state outlives any container restart or recreation.
- **Event-Driven** — WHEN an evidence artifact is captured by the verifier, the system shall store the blob in MinIO bucket `uploads` keyed by its `output_hash` and persist the four-field Evidence_Record reference linked to the requirement ID and commit SHA in the Postgres durable store (REQ-16.2).
- **State-Driven** — WHILE the stack is running, the system shall keep `plane-db` Postgres as the single source of truth for coverage queries, reconstructable independently of any model session (REQ-16.3).
- **Unwanted** — IF a stateful container is recreated (image upgrade, restart), THEN its data shall be re-mounted intact from its named volume and no committed requirement, coverage row, evidence reference, or run-state row shall be lost.
- **Optional** — WHERE an external managed Postgres or S3-compatible store is used instead of the bundled service, the system shall redirect persistence via `DATABASE_URL` / `AWS_S3_ENDPOINT_URL` while preserving the same durability contract.

**Acceptance criteria.**
1. `plane-db` accepts connections (`pg_isready -h plane-db -U plane`), `max_connections=1000` is set, and the `plane` database exists with Plane's migrated schema after `migrator` completes.
2. The MinIO `uploads` bucket exists and is writable/readable via the S3 endpoint `http://plane-minio:9000` using the configured `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`; a put-then-get round-trips identical bytes (the content-addressed-blob contract).
3. RabbitMQ `plane-mq` is reachable on `5672` with vhost `plane`, and `worker`/`beat-worker` connect and consume; the management UI confirms the `plane` user/vhost.
4. Redis/Valkey `plane-redis` responds to `PING` and `live`/`api` use it.
5. **Volume-durability proof:** write a marker row to Postgres and a marker object to MinIO, `docker compose down` (without `-v`), `up -d`, and confirm both the row and the object survive — `pgdata` and `uploads` retained their data.

**Assigned attributes.** state `Plan-Approved`; agent_role `human`; requirement_id `REQ-INFRA-004`; coverage_type `functional` (durable-storage capability); labels `priority:blocking`, `phase:0`, `type:functional`, `human:review`.

**Agent state-flow.** `Agent-Triaged` (`requirement_id=REQ-INFRA-004`), `Plan-Approved`, `Agent-Executing` while the four tiers come up and the buckets/vhosts are created, `In-Verification` while the volume-durability proof runs (the down/up survival check is the load-bearing Evidence_Record — `evidence_status=proven` only when the marker row + object survive a recreate), `Human-Review`, `Done`. A lost-on-recreate result routes to `Failed`.

---

## REQ-INFRA-005 — Database Migration & Version Upgrade

**User story.** As the Operator, I want schema migrations applied automatically by the `migrator` one-shot service on every deploy and a deterministic version-upgrade path keyed on `APP_RELEASE`, so upgrading Plane (and applying the spec's amendment migrations `007_requirement_versions` / `008_gate_audit_log`) never leaves the `api`/`worker` running against an unmigrated schema.

**Maps to.** REQ-16 (durable store schema) and REQ-22 (REQ-COV-007 — requirement-amendment versioning, whose `requirement_versions` table is migration `007`; `design.md:144`), plus REQ-27 (gate audit log, migration `008`).

**EARS lines.**
- **Ubiquitous** — THE system shall run all pending schema migrations through the `migrator` service (`./bin/docker-entrypoint-migrator.sh`) before the application tier serves schema-dependent traffic, and the `migrator` shall exit `0` on success.
- **Event-Driven** — WHEN `APP_RELEASE` is changed to a newer pinned release and the stack is re-deployed, the system shall pull the new `makeplane/plane-*` images, run `migrator` against the existing `pgdata`, and bring the app tier up on the new version with the migrated schema.
- **State-Driven** — WHILE `migrator` is running, the system shall keep its `restart_policy: on-failure` so a transient DB-not-ready failure retries, and a genuine migration error surfaces as a non-zero exit.
- **Unwanted** — IF a migration fails (non-zero `migrator` exit), THEN the system shall halt the upgrade and leave the prior schema intact for rollback rather than serving a half-migrated database.
- **Optional** — WHERE a forward-only migration runner is adopted for the companion durable store (the eight `db/migrations/001..008.sql` the `.kiro` design defines), the system shall apply them idempotently via tracked one-time apply (`schema_migrations` bookkeeping) on deploy.

**Acceptance criteria.**
1. On first `up`, `migrator` applies Plane's schema to the empty `plane` database and exits `0`; `api` then starts cleanly with no "relation does not exist" errors in `logs_api`.
2. Re-running the stack with no schema change is a no-op migration (`migrator` exits `0`, applies nothing new — idempotent).
3. An `APP_RELEASE` bump pulls the new images and the upgrade migration runs against the existing `pgdata` without data loss (the REQ-INFRA-004 marker row survives the upgrade).
4. The companion `.kiro` migrations `001`–`008` are documented as applied through a tracked runner with `schema_migrations` bookkeeping; running them twice is idempotent and produces all eight tables (`requirements`, `coverage_items`, `traceability_links`, `evidence_records`, `run_state`, `domain_baseline_checklists`, `requirement_versions`, `gate_audit_log`).
5. A deliberately broken migration causes `migrator` to exit non-zero and the app tier is held from advancing, demonstrating the fail-and-rollback posture.

**Assigned attributes.** state `Plan-Approved`; agent_role `human`; requirement_id `REQ-INFRA-005`; coverage_type `functional`; labels `priority:high`, `phase:0`, `type:functional`, `human:review`.

**Agent state-flow.** `Agent-Triaged` (`requirement_id=REQ-INFRA-005`), `Plan-Approved`, `Agent-Executing` during the first-migrate and the upgrade dry-run, `In-Verification` while the idempotency + upgrade-survival + broken-migration checks run (migrator exit codes + table-count query captured as evidence), `Human-Review`, `Done`. A failed upgrade migration routes to `Blocked` (gate: integrity/upgrade not proven) until the schema is fixed.

---

## REQ-INFRA-006 — Backup & Restore of the Durable Tier

**User story.** As the Data Owner, I want scheduled, verifiable backups of `plane-db` (logical dump) and `plane-minio` (object mirror) plus a tested restore procedure, so the control plane's durable memory — coverage state, traceability links, Evidence_Records, run state, gate audit log — can be recovered after data loss, satisfying REQ-16.3's "reconstructable independently of any model session."

**Maps to.** REQ-16.3 (REQ-STORE-003 — Postgres as single source of truth, reconstructable) and REQ-11.1 (durable run state); the gate-audit-log retention default of 365 days (`requirements.md:378`) presumes a recoverable durable store.

**EARS lines.**
- **Ubiquitous** — THE system shall produce a consistent logical backup of the `plane` database (`pg_dump`) and a complete mirror of the MinIO `uploads` bucket, both written to a location outside the Docker volumes.
- **Event-Driven** — WHEN a backup job runs, the system shall capture a point-in-time-consistent Postgres dump and a bucket mirror, and record the backup's timestamp and integrity checksum.
- **State-Driven** — WHILE a restore is in progress, the system shall bring the application tier down (or read-only) so no writes race the restore, then re-point `pgdata`/`uploads` at the restored data and bring the stack back up.
- **Unwanted** — IF a backup is corrupt or incomplete (checksum mismatch / truncated dump), THEN the system shall reject it as a restore source and retain the last known-good backup.
- **Optional** — WHERE point-in-time recovery is required, the system shall additionally archive Postgres WAL so recovery to an arbitrary timestamp within the retention window is possible.

**Acceptance criteria.**
1. A `pg_dump` of the `plane` database completes and the dump file is non-empty and restorable into a fresh Postgres instance.
2. A MinIO `uploads` bucket mirror reproduces every object (byte-identical, verified by `output_hash` for evidence blobs).
3. **Round-trip restore proof:** seed a known marker row + evidence object, back up, destroy the volumes (`docker compose down -v`), restore from backup into fresh volumes, `up -d`, and confirm the marker row and evidence object are present and the schema is intact.
4. Backup artifacts carry a recorded timestamp and integrity checksum; a corrupted backup is rejected by the restore procedure.
5. The restore runbook is documented end-to-end and the retention policy (≥ the 365-day audit-log window) is stated.

**Assigned attributes.** state `Plan-Approved`; agent_role `human`; requirement_id `REQ-INFRA-006`; coverage_type `NFR` (durability/recoverability); labels `priority:high`, `phase:0`, `type:nfr`, `human:review`.

**Agent state-flow.** `Agent-Triaged` (`requirement_id=REQ-INFRA-006`, `coverage_type=NFR`), `Plan-Approved`, `Agent-Executing` while backup jobs and the restore runbook are built, `In-Verification` while the destroy-and-restore round-trip runs (the recovered marker row + evidence object survival is the Evidence_Record; `evidence_status=proven` only on a clean round-trip), `Human-Review`, `Done`. A restore that loses data routes to `Failed`.

---

## REQ-INFRA-007 — Horizontal Scaling via Replicas

**User story.** As the Operator, I want each stateless application tier (`web`, `space`, `admin`, `api`, `worker`, `beat-worker`, `live`) to scale horizontally through its `*_REPLICAS` env knob without code change, so the control plane has throughput headroom as the autonomous engine fans out agent runs, while the stateful tiers and `beat-worker` stay correctly single-instance where required.

**Maps to.** REQ-15 (Orchestration — the inner loop runs on Claude Code primitives; Plane must have the operational headroom to surface many concurrent agent runs/issues) and REQ-12 (observability scale).

**EARS lines.**
- **Ubiquitous** — THE system shall honor `WEB_REPLICAS`, `SPACE_REPLICAS`, `ADMIN_REPLICAS`, `API_REPLICAS`, `WORKER_REPLICAS`, `BEAT_WORKER_REPLICAS`, and `LIVE_REPLICAS` from `plane.env` as the replica count for each corresponding service's `deploy.replicas`.
- **Event-Driven** — WHEN `API_REPLICAS` (or `WORKER_REPLICAS`) is increased and the stack is re-applied, the system shall start the additional replicas, all sharing the single `plane-db`/`plane-redis`/`plane-mq` backing tier, and the proxy shall load-balance across the `api` replicas.
- **State-Driven** — WHILE multiple `worker` replicas run, the system shall let RabbitMQ distribute task messages across them so background work scales with replica count.
- **Unwanted** — IF a stateful single-instance service (`plane-db`, `plane-redis`, `plane-mq`, `plane-minio`) is given a replica count >1, THEN that configuration shall be rejected/avoided, since these tiers are not horizontally replicable in this compose topology (`deploy.replicas: 1` is fixed for each).
- **Optional** — WHERE `beat-worker` is scaled, the system shall keep it effectively single-scheduler (replica count 1 by default) to avoid duplicate periodic task emission, scaling only the consuming `worker` tier instead.

**Acceptance criteria.**
1. Setting `API_REPLICAS=2` and re-applying starts two `api` containers; `docker compose ps` shows both running and the proxy serves requests from either.
2. Setting `WORKER_REPLICAS=2` starts two workers and RabbitMQ shows both consumers attached to the `plane` queues; background tasks are distributed.
3. The stateful services remain at `replicas: 1` (verified) and are never scaled by a `*_REPLICAS` knob.
4. `beat-worker` defaults to one replica; scaling the `worker` tier does not duplicate scheduled (beat) tasks.
5. Scaling up then back down is graceful — surplus replicas stop cleanly and the remaining replica continues serving.

**Assigned attributes.** state `Plan-Approved`; agent_role `human`; requirement_id `REQ-INFRA-007`; coverage_type `NFR` (scalability); labels `priority:normal`, `phase:0`, `type:nfr`, `human:review`.

**Agent state-flow.** `Agent-Triaged` (`requirement_id=REQ-INFRA-007`, `coverage_type=NFR`), `Plan-Approved`, `Agent-Executing` while replica knobs are exercised, `In-Verification` while the multi-replica `ps` + consumer-count checks run (the two-replica running state + distributed-consumer evidence captured), `Human-Review`, `Done`. A duplicate-beat-task or stateful-replica misconfiguration routes to `Blocked`.

---

## REQ-INFRA-008 — Health, Readiness & Liveness Verification

**User story.** As the Operator, I want a single readiness check that confirms every tier is live and the Plane REST/Webhook API is reachable on port 8090 before any downstream epic provisions the ASCP workspace or wires gate-decision webhooks, so the spec's fail-closed availability contract (gates must reach the same decision from a healthy durable store) rests on a verified-healthy substrate, not an assumed one.

**Maps to.** REQ-12 (Observability — the operator's live view depends on a healthy stack) and the Note N-25 fail-closed availability contract (`design.md:1374`) which presumes the Postgres tier is reliably up; also gates the API surface later epics consume.

**EARS lines.**
- **Ubiquitous** — THE system shall expose a readiness verification that checks, in one pass: `plane-db` accepts connections, `plane-redis` answers `PING`, `plane-mq` is reachable, `plane-minio` serves its health endpoint, `migrator` has exited `0`, and the proxy serves `http://localhost:8090/`.
- **Event-Driven** — WHEN the readiness check is invoked after `up -d`, the system shall return PASS only when every application service is running and `http://localhost:8090/api/` responds, and FAIL (naming the unhealthy tier) otherwise.
- **State-Driven** — WHILE any backing store is unreachable, the system shall report the stack as NOT ready and shall not allow downstream workspace provisioning to proceed against it.
- **Unwanted** — IF the proxy serves a 5xx (an upstream app service is down), THEN the readiness check shall fail and identify which upstream (`web`/`api`/`space`/`admin`/`live`) is unhealthy from the proxy/app logs.
- **Optional** — WHERE container-level healthchecks are added, the system shall surface each service's `healthy`/`unhealthy` state in `docker compose ps` so liveness is observable without external probing.

**Acceptance criteria.**
1. A readiness script returns exit `0` only when all four backing stores are healthy, `migrator` exited `0`, and `http://localhost:8090/` + `http://localhost:8090/api/instances/` both return 200/JSON.
2. Killing any single backing store flips the readiness check to FAIL and names that tier.
3. The `api` service reachable through the proxy returns a valid instance/health payload, confirming the API surface downstream epics will consume is live (this is the API-category deliverable: a *verified-reachable* REST endpoint, not workspace content).
4. Webhook egress configuration (`WEBHOOK_ALLOWED_IPS`/`WEBHOOK_ALLOWED_HOSTS`) is in place so a later gate-decision webhook has a valid, allowlist-checked target.
5. Readiness PASS is captured as the gating Evidence_Record before any downstream epic (workspace provisioning) is unblocked.

**Assigned attributes.** state `Plan-Approved`; agent_role `human`; requirement_id `REQ-INFRA-008`; coverage_type `WIRING` (the substrate-to-API reachability connection that the rest of the platform depends on); labels `priority:blocking`, `phase:0`, `type:wiring`, `gate:completion`, `human:review`.

**Agent state-flow.** `Agent-Triaged` (`requirement_id=REQ-INFRA-008`), `Plan-Approved`, `Agent-Executing` while the readiness check is built, `In-Verification` while the all-healthy + kill-a-tier-fails + API-reachable checks run (the readiness PASS output is the load-bearing Evidence_Record — this story's `Done` is the gate that unblocks the workspace-provisioning epic), `Human-Review`, `Done`. Any unhealthy tier routes the issue to `Blocked` (gate: substrate dependency unproven) until the tier recovers.

---

## Actionable Tasks (E1)

Each task is tagged **Infrastructure** | **API (Plane Webhooks/REST)** | **Orchestration**.

### REQ-INFRA-001 tasks
- **[Infrastructure] Validate and bring up the full compose topology.** Subtasks: run `docker compose --env-file plane.env config` and resolve all `x-*` anchors; `docker compose up -d`; confirm all 12 long-lived services running and `migrator` `Exited(0)` via `docker compose ps`; verify the ten named volumes are created and bound.
- **[Infrastructure] Verify dependency ordering and restart resilience.** Subtasks: stop `plane-db`, observe `api` reconnect in `logs_api`; full `restart` and confirm all-running recovery; confirm `restart_policy: any` on long-lived services and `on-failure` on `migrator`; pin `APP_RELEASE` and the four backing-store image tags.
- **[Orchestration] Create the E1 tracking issue in Plane.** Subtasks: create issue under ASCP titled "REQ-INFRA-001 Topology stand-up"; set `requirement_id=REQ-INFRA-001`, `agent_role=human`, `coverage_type=WIRING`; apply labels `priority:blocking`, `phase:0`, `type:wiring`; advance `Backlog → Agent-Triaged → Plan-Approved`.

### REQ-INFRA-002 tasks
- **[Infrastructure] Configure proxy ingress on 8090/8453.** Subtasks: set `LISTEN_HTTP_PORT=8090`, `LISTEN_HTTPS_PORT=8453`; confirm proxy publishes only `8090->80` and `8453->443` in `host` mode; verify no internal service port is host-published; confirm `proxy_config`/`proxy_data` persist across restart.
- **[Infrastructure] Wire origin/CORS to the 8090 ingress.** Subtasks: set `APP_DOMAIN=localhost:8090`, `WEB_URL=http://localhost:8090`, `CORS_ALLOWED_ORIGINS=http://localhost:8090`; verify CORS accepts the 8090 origin and rejects others; (optional) wire `CERT_EMAIL`/`CERT_ACME_CA` or `CERT_ACME_DNS` for HTTPS.
- **[API (Plane Webhooks/REST)] Verify proxied routes.** Subtasks: `curl -sf http://localhost:8090/` → 200; `curl -sf http://localhost:8090/api/instances/` → JSON from `api:8000`; confirm `/spaces`, `/god-mode`, `/live` route to `space`/`admin`/`live`.

### REQ-INFRA-003 tasks
- **[Infrastructure] Externalize and rotate secrets.** Subtasks: confirm all credentials sourced from `plane.env`; rotate `SECRET_KEY`, `LIVE_SERVER_SECRET_KEY`, `POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD`, `AWS_SECRET_ACCESS_KEY` off shipped defaults; verify overrides propagate to `api`'s effective env; set `DEBUG=0`.
- **[Infrastructure] Prove no secret leakage (REQ-17.5 substrate guard).** Subtasks: grep running-container env + proxy/app access logs for any password/`SECRET_KEY` in a URL or log line; assert clean; verify `DATABASE_URL`/`AMQP_URL`/`REDIS_URL` resolve both blank-defaulted and explicitly-set.
- **[API (Plane Webhooks/REST)] Configure webhook egress allowlists.** Subtasks: set `WEBHOOK_ALLOWED_IPS`/`WEBHOOK_ALLOWED_HOSTS`; confirm a non-allowlisted private-IP webhook target is refused (SSRF guard) and an allowlisted target is permitted.

### REQ-INFRA-004 tasks
- **[Infrastructure] Provision the four durable tiers on named volumes.** Subtasks: confirm `pgdata`/`redisdata`/`rabbitmq_data`/`uploads` bind to their services; `pg_isready` + `max_connections=1000` on `plane-db`; `PING` on Valkey; RabbitMQ `plane` user/vhost reachable on 5672; create/confirm MinIO `uploads` bucket.
- **[Infrastructure] Prove volume durability across recreate.** Subtasks: write a marker Postgres row + marker MinIO object; `docker compose down` (no `-v`); `up -d`; confirm both survive; capture the survival as the Evidence_Record.
- **[API (Plane Webhooks/REST)] Verify evidence-blob content-addressing round-trip.** Subtasks: put an object into `uploads` keyed by a `sha256:` hash via the S3 endpoint; get it back; assert byte-identical (the REQ-16.2 content-addressed-reference contract).

### REQ-INFRA-005 tasks
- **[Infrastructure] Run and verify first-deploy migrations.** Subtasks: confirm `migrator` applies Plane schema and exits `0`; assert `api` starts with no missing-relation errors; assert re-run is idempotent (no-op migration, exit 0).
- **[Infrastructure] Execute and verify a version upgrade.** Subtasks: bump `APP_RELEASE`; pull new `makeplane/plane-*` images; run `migrator` against existing `pgdata`; confirm the REQ-INFRA-004 marker row survives the upgrade; verify a deliberately-broken migration exits non-zero and holds the app tier.
- **[Infrastructure] Apply the companion eight-table `.kiro` migrations idempotently.** Subtasks: adopt a tracked forward-only runner with `schema_migrations` bookkeeping; apply `001`–`008`; assert all eight tables exist (`requirements`, `coverage_items`, `traceability_links`, `evidence_records`, `run_state`, `domain_baseline_checklists`, `requirement_versions`, `gate_audit_log`); assert double-apply is a no-op.

### REQ-INFRA-006 tasks
- **[Infrastructure] Build the backup jobs.** Subtasks: schedule `pg_dump` of the `plane` database to an out-of-volume location; mirror the MinIO `uploads` bucket; record each backup's timestamp + integrity checksum; (optional) archive Postgres WAL for PITR.
- **[Infrastructure] Prove a full destroy-and-restore round-trip.** Subtasks: seed a marker row + evidence object; back up; `docker compose down -v`; restore into fresh volumes; `up -d`; confirm marker row + object + schema recovered; assert a corrupted backup is rejected.
- **[Orchestration] Document the restore runbook and retention.** Subtasks: write the end-to-end restore procedure; state retention ≥ the 365-day audit-log window; link the runbook from the E1 issue; advance the issue to `Done` only with the round-trip Evidence_Record attached.

### REQ-INFRA-007 tasks
- **[Infrastructure] Exercise stateless-tier replica scaling.** Subtasks: set `API_REPLICAS=2`, re-apply, confirm two `api` containers running and proxy load-balancing; set `WORKER_REPLICAS=2`, confirm two RabbitMQ consumers and distributed tasks; scale back down gracefully.
- **[Infrastructure] Enforce stateful-tier single-instance invariant.** Subtasks: confirm `plane-db`/`plane-redis`/`plane-mq`/`plane-minio` stay `replicas: 1`; confirm `beat-worker` defaults to one replica; verify scaling `worker` does not duplicate scheduled (beat) tasks.
- **[Orchestration] Record scaling envelope on the issue.** Subtasks: document the per-tier replica knobs and the stateful single-instance constraint; set `coverage_type=NFR`; attach the multi-replica running-state evidence.

### REQ-INFRA-008 tasks
- **[Infrastructure] Build the one-pass readiness check.** Subtasks: script checks for `plane-db` connect, Valkey `PING`, RabbitMQ reachable, MinIO health, `migrator` `Exited(0)`, proxy serving `/`; exit 0 only on all-healthy; (optional) add container `healthcheck` blocks surfaced in `ps`.
- **[Infrastructure] Verify failure detection.** Subtasks: kill each backing store in turn; assert readiness flips to FAIL naming that tier; assert a proxy 5xx identifies the unhealthy upstream from logs.
- **[API (Plane Webhooks/REST)] Verify the REST/Webhook surface is live and gate the downstream epic.** Subtasks: `curl http://localhost:8090/api/instances/` → 200/JSON; confirm webhook egress allowlist target is configured; capture readiness PASS as the gating Evidence_Record that unblocks the workspace-provisioning epic; advance the E1 readiness issue to `Done`.


# Epic E2 — Agentic Workspace & Governance Model

> **Plane blueprint section.** Defines the `ASCP` workspace/project, the 12-state custom agent workflow, the custom fields & labels, and the capability-role → Plane-role/permission taxonomy that governs **who (which `agent_role`) may move an issue between which states** — including the human-only transitions. Grounded in the reconciled `.kiro/specs/spec-to-evidence-control` spec (32 EARS requirements / design.md 8 Postgres tables, 6 Claude-Code hooks, 4 subagents / tasks.md 57 tasks). Assigned requirements: **REQ-15 / Requirement 15 (Orchestration)**, **REQ-28 / Requirement 28 (Capability-Role Taxonomy, REQ-ORCH-004)**, **REQ-18 / Requirement 18 (Human-in-the-Loop Approval)**.

---

## 1. Overview

Plane is the **PM control plane** for the autonomous Spec-to-Evidence delivery engine. The platform's *actual* enforcement lives in Claude Code hooks + CI + OPA (the deterministic gates); Plane mirrors that enforcement as a **governance model** so a human can observe and audit the run, and so the agent fleet has a shared, queryable definition of "where is this issue, and who is allowed to move it next."

The governing invariant carries straight through to Plane: **deterministic gates decide completion from verifiable facts; Plane state transitions are a projection of those gate decisions, never a substitute for them.** A Plane issue reaching `Done` is the *shadow* of a real Stop+OPA+CI pass — the platform never lets Plane be the source of truth for "done."

This epic owns three governance surfaces:

1. **Orchestration model (REQ-15).** The inner loop is run by Claude Code's own primitives — the four subagents (`initializer`, `implementer`, `verifier`, `research`) + the six hooks — and Plane reflects that single inner loop as one issue moving through the agent-state workflow. No external agent-reasoning framework drives the inner loop; durable execution (Temporal/Inngest) and Agent_Teams are explicitly held **off** the default gating path and modeled as optional, off-board capabilities.
2. **Capability-role taxonomy (REQ-28).** The five `agent_role` values (`initializer | implementer | verifier | research | human`) map to Plane roles/permissions, and an **optional** extension admits bounded roles (`design`, `platform`, `reliability`) — each with an explicit, narrower scope, **none with verifier write access**. This taxonomy is what authorizes a given role to perform a given state transition.
3. **Human-in-the-Loop approval (REQ-18).** Two transitions are **human-only** and deterministically enforced upstream of Plane: the **plan-approval** gate (`Plan-Approved`, backed by `plan-approved.json` SHA-bound to `feature_list.json`) and the **PR-review** gate (`Done`, backed by a required reviewer in a GitHub ruleset). Plane records these as human-authored transitions and refuses to let an agent role perform them.

### 1.1 Workspace & project configuration

| Setting | Value |
|---|---|
| Project name | **Agentic SDLC Control Plane** |
| Identifier | **ASCP** |
| Description | Plane workspace driving the autonomous Spec-to-Evidence delivery engine: intent→verified software, with agents as memory/verifier/scope-enforcer/auditor and a fail-closed completion gate. |
| Workflow | 12 custom states (below) replacing Plane's default 5 |
| Fields | 10 custom properties (below) |
| Labels | 22 labels across 6 families (below) |

### 1.2 The custom agent state workflow (12 states)

The canonical state set, mapped onto Plane's state-group enum (`backlog | unstarted | started | completed | cancelled`). The four `cancelled`-group states are the platform's **non-Done terminal states** — `HANDOFF` and `Blocked` and `Failed` are deliberately distinct from each other and from `Done` (a HANDOFF run is *never* marked COMPLETE — Requirement 14.2 / Requirement 21).

| # | State | Plane group | Meaning |
|---|-------|-------------|---------|
| 1 | **Backlog** | backlog | unrefined intake |
| 2 | **Agent-Triaged** | unstarted | classified by the initializer; `agent_role` + `requirement_id` assigned |
| 3 | **Spec-Compiling** | started | initializer compiling EARS + running `spec_validator` (Z3) |
| 4 | **Spec-Verified** | started | `violation_count == 0`; `feature_list.json` emitted (all unproven) |
| 5 | **Plan-Approved** | started | **human** plan approval written (`plan-approved.json`, SHA-bound) |
| 6 | **Agent-Executing** | started | implementer building one slice in an isolated git worktree |
| 7 | **In-Verification** | started | verifier running 5-layer checks; capturing Evidence_Record |
| 8 | **Human-Review** | started | PR + **human** reviewer gate |
| 9 | **Done** | completed | proven with evidence; all gates (Stop+OPA+CI) pass |
| 10 | **HANDOFF** | cancelled | cap/budget/no-progress reached; handed to a human (distinct from Done) |
| 11 | **Blocked** | cancelled | a gate blocked (exit 2): unproven dep, failed integrity/approval |
| 12 | **Failed** | cancelled | verification failed; evidence withheld |

### 1.3 Custom fields (10 properties)

| Field | Type | Allowed values / format |
|-------|------|-------------------------|
| `agent_role` | dropdown | `initializer | implementer | verifier | research | human` |
| `requirement_id` | text | e.g. `REQ-GATE-002` (pattern `^[A-Z]+-[A-Z]+-[0-9]{3}$`) |
| `evidence_status` | dropdown | `unproven | proven | failed` |
| `coverage_type` | dropdown | `functional | NFR | WIRING` |
| `run_state` | dropdown | `running | complete | handoff | blocked` |
| `worktree_branch` | text | git branch for the slice (traceability) |
| `agent_run_id` | text | LLM agent run id (traceability triple: issue↔branch↔run) |
| `ears_pattern` | dropdown | `ubiquitous | event-driven | state-driven | unwanted | optional | complex` |
| `gate` | dropdown | `stop | pretooluse | posttooluse | subagentstop | opa | ci` |
| `output_hash` | text | `sha256:<64hex>` evidence hash |

### 1.4 Labels (22, six families)

- **Role:** `agent:initializer`, `agent:coder`, `agent:tester`, `agent:research`, `human:review`
- **Priority:** `priority:blocking`, `priority:high`, `priority:normal`
- **Type:** `type:functional`, `type:nfr`, `type:wiring`
- **Gate:** `gate:stop`, `gate:completion`, `gate:security`
- **Phase:** `phase:0`, `phase:1`, `phase:2`, `phase:3`, `phase:4`
- **Terminal:** `handoff`, `blocked`, `failed`

### 1.5 Capability-role → Plane-role / transition-authority matrix

This is the governance core: who may move an issue between which states. **A transition is authorized iff the actor's `agent_role` (or human) appears in the "may move" column.** Agent roles map to Plane member-level roles; the **human** role maps to Plane Admin and is the *only* role allowed across the two human-only edges.

| `agent_role` | Plane role | May WRITE (transition into) | Tests/`feature_list.json` write scope | Mapped label |
|---|---|---|---|---|
| `initializer` | Member (spec) | `Backlog → Agent-Triaged`, `Agent-Triaged → Spec-Compiling`, `Spec-Compiling → Spec-Verified` | read/write spec artifacts + `feature_list.json` (seed/populate); **no** `tests/`, CI, `src/` | `agent:initializer` |
| `implementer` | Member (code) | `Plan-Approved → Agent-Executing` | write impl source **in its worktree only**; **no** `tests/`, schema, CI; **cannot self-verify** | `agent:coder` |
| `verifier` | Member (verify) | `Agent-Executing → In-Verification`, `In-Verification → Human-Review`, `In-Verification → Failed`, `In-Verification → Blocked` | read-only `src/`; read/write `tests/` + `feature_list.json` **status field + evidence sub-object only** (artifact-guard carve-out keyed on `actor_agent == verifier.md`) | `agent:tester` |
| `research` | Member (research) | `Backlog → Agent-Triaged` (sourcing context only) | read/write `baselines/` + web tool; **no** `src`, `tests`, CI | `agent:research` |
| **`human`** | **Admin** | **`Spec-Verified → Plan-Approved`** (plan approval — human-only), **`Human-Review → Done`** (PR review — human-only), `* → HANDOFF` reconciliation, `in_scope` flips, requirement amendments | unrestricted (accountable actor) | `human:review` |
| `design`* | Member (bounded) | *(optional)* read-only proposal into `Spec-Compiling` | scoped artifact dir only; **no verifier write access** | — |
| `platform`* | Member (bounded) | *(optional)* read-only proposal into `Spec-Compiling` | scoped artifact dir only; **no verifier write access** | — |
| `reliability`* | Member (bounded) | *(optional)* read-only proposal into `Spec-Compiling` | scoped artifact dir only; **no verifier write access** | — |

\* Optional roles (REQ-28). v1 is not over-built; they are added only WHERE a project requires roles beyond the four-role default.

**Human-only transitions (deterministically enforced, never agent-performable):**
- `Spec-Verified → Plan-Approved` — requires `plan-approved.json` whose `feature_list_sha` equals the canonical SHA-256 of the current `feature_list.json`; enforced by the PreToolUse plan gate (Requirement 18.1/18.4). The Initializer **does not** write `plan-approved.json` — only the human does.
- `Human-Review → Done` — requires a human PR review (required reviewer in a GitHub ruleset) plus all required status checks green (Requirement 18.3).
- `* → HANDOFF` operator reconciliation and any `in_scope = false` flip — human-authored only (Requirement 5.7); the DB rejects an unattributed flip.

---

## 2. EARS User Stories

Three stories, one per assigned requirement. Each is grounded in the named `.kiro` requirement and carries the Plane state/field/label assignment plus the agent-state-flow it governs.

---

### Story E2-S1 — Inner-loop orchestration is run by Claude Code primitives, with the issue mirroring one inner loop

**Maps to:** Requirement 15 (Orchestration) — REQ-ORCH-001..003. Baseline block B14. **Coverage type:** WIRING (orchestration is an architectural connection obligation — the subagent/hook loop must be reachable and wired, not just declared). **State assignment:** `Agent-Executing`. **agent_role:** `implementer`. **requirement_id:** `REQ-ORCH-001`. **Labels:** `agent:coder`, `type:wiring`, `phase:0`, `priority:high`.

**EARS lines**
- **Ubiquitous:** THE system shall run the inner planner/implementer/verifier orchestrator using Claude Code subagents and hooks, and shall not introduce an external agent-reasoning framework for the inner loop by default. *(15.1)*
- **Event-Driven:** WHEN an issue enters `Agent-Executing`, the system shall drive exactly one inner loop — one slice, one `implementer` subagent, one isolated git worktree, one atomic commit — and mirror that single loop as the issue's `worktree_branch` + `agent_run_id` (the traceability triple issue↔branch↔run). *(15.1)*
- **State-Driven:** WHILE Agent_Teams (experimental peer-to-peer) remains in experimental status or lacks session resumption, the system shall keep it off the delivery-gating path and shall not route any state transition through it. *(15.3)*
- **Unwanted:** IF a prediction, an Agent_Teams peer, or an external reasoning framework attempts to emit or override a Plane state transition, THEN the system shall reject the transition; only the four canonical subagents and the human may move an issue. *(15.1, 15.3; Requirement 13.6 — gates read facts, not predictions)*
- **Optional:** WHERE crash-safe multi-hour/multi-day runs are required, the system shall wrap the loop in Temporal/Inngest invoking `claude -p` as a durable step with each tool call as a separate activity, modeled in Plane as an off-board optional capability (Phase 5) that does not alter the canonical state graph. *(15.2)*

**Acceptance criteria**
1. The Plane workflow has exactly the 12 canonical states, and the only actors able to transition an issue are `initializer`, `implementer`, `verifier`, `research`, and `human` — verified by a webhook-side authorization check keyed on `agent_role`.
2. An issue in `Agent-Executing` carries a non-empty `worktree_branch` and `agent_run_id`; a transition into `Agent-Executing` with either field empty is rejected (the inner loop is not wired to a real worktree/run).
3. No Plane automation, integration, or webhook routes a state transition through Temporal/Inngest or Agent_Teams on the default path; the Temporal stub exists only behind an explicit flag (tasks.md task 43.1) and Agent_Teams is asserted off-path (task 43.2).
4. The orchestration wiring is itself a WIRING coverage item: the subagent↔hook inner loop is reachable from a real execution path (Requirement 8) — a Plane issue labelled `type:wiring` tracks this with integration-test evidence.

**Agent state-flow governed:** `Plan-Approved → Agent-Executing` (implementer enters) → `Agent-Executing → In-Verification` (verifier takes over — the implementer **cannot** self-verify, so the loop hands off; Property 24). HANDOFF carve-out: if cap/budget/no-progress fires inside the loop, `Agent-Executing → HANDOFF` (exit 0, allow-stop; Requirement 21), never a force-continued block.

---

### Story E2-S2 — Capability-role taxonomy maps to Plane roles/permissions and authorizes state transitions

**Maps to:** Requirement 28 (Capability-Role Taxonomy Extension, OPTIONAL) — REQ-ORCH-004. Baseline block B14. **Coverage type:** functional. **State assignment:** `Agent-Triaged`. **agent_role:** `initializer`. **requirement_id:** `REQ-ORCH-004`. **Labels:** `agent:initializer`, `type:functional`, `phase:0`, `priority:normal`.

**EARS lines**
- **Ubiquitous:** THE system shall map each `agent_role` value (`initializer | implementer | verifier | research | human`) to a Plane role/permission, and shall authorize a state transition only when the actor's `agent_role` is listed as permitted to move into the target state (per the §1.5 transition-authority matrix). *(REQ-ORCH-004 governance projection of Requirement 15.1)*
- **Event-Driven:** WHEN an issue is classified at `Backlog → Agent-Triaged`, the system shall stamp its `agent_role` and `requirement_id`, fixing which role owns the next transition. *(28.1)*
- **State-Driven:** WHILE a bounded optional role (`design`, `platform`, `reliability`) is active on a project, the system shall grant it an explicit, narrower permission scope and shall ensure none of them holds verifier write access (no `tests/` write, no `evidence`/status write, no `In-Verification → Human-Review` edge). *(28.1)*
- **Unwanted:** IF an `implementer`-role actor attempts to produce or accept an Evidence_Record, or any non-`verifier` role attempts to flip `evidence_status` to `proven`, THEN the system shall block it (the SubagentStop role-separation check rejects an evidence-bearing result whose `actor_agent == implementer.md`; Property 24). *(28.1, Requirement 9.2)*
- **Optional:** WHERE a project requires roles beyond planner/implementer/verifier/research, the system shall support the additional bounded subagent roles, each authored as a `.claude/agents/*.md` definition with explicit permission scope and none with verifier write access; v1 remains the four-role default and is not over-built. *(28.1)*

**Acceptance criteria**
1. Every Plane state transition request resolves the actor's `agent_role` to the §1.5 matrix; a transition not listed for that role is rejected with the blocking reason recorded against the issue.
2. The `verifier` role is the **only** non-human role permitted to write `tests/` and the `feature_list.json` status+evidence sub-object; an `implementer` or optional-role write to `tests/` is blocked (artifact-guard carve-out keyed on `actor_agent == verifier.md`).
3. Adding an optional role (`design` / `platform` / `reliability`) introduces a `.claude/agents/<role>.md` with a `tools` allowlist that grants no implementation-source write and no verifier write; a smoke test parses the markdown and asserts the scope (analogous to `tests/smoke/test_hook_config.py`).
4. The taxonomy is OPTIONAL: a v1 project runs the four-role default with zero optional-role definitions and still passes all governance checks.

**Agent state-flow governed:** authorizes *every* edge in the graph. Concretely: `initializer` owns `Backlog→Agent-Triaged→Spec-Compiling→Spec-Verified`; `human` owns `Spec-Verified→Plan-Approved`; `implementer` owns `Plan-Approved→Agent-Executing`; `verifier` owns `Agent-Executing→In-Verification` and `In-Verification→{Human-Review|Failed|Blocked}`; `human` owns `Human-Review→Done`. Optional roles may only *propose into* `Spec-Compiling` (read-only advisory), never write a verifier edge.

---

### Story E2-S3 — Human-in-the-Loop approval gates are deterministic and human-only

**Maps to:** Requirement 18 (Human-in-the-Loop Approval) — REQ-HITL-001..003; extended by Requirement 32 (REQ-CTRL-001, kill-switch — the operator-only governance toggle). Baseline block B17. **Coverage type:** functional. **State assignment:** `Plan-Approved` (plan gate) and `Human-Review` (PR gate). **agent_role:** `human`. **requirement_id:** `REQ-HITL-001`. **Labels:** `human:review`, `gate:completion`, `phase:0`, `priority:blocking`.

**EARS lines**
- **Ubiquitous:** THE system shall require a human PR review (a required reviewer configured in a repository ruleset) before any merge to the protected branch, modeled as the human-only `Human-Review → Done` transition. *(18.3)*
- **Event-Driven:** WHEN the validated spec and `feature_list.json` are ready (`violation_count == 0`), the system shall present them in plan mode for human approval and missing-context injection, and shall record the approval as the human-only `Spec-Verified → Plan-Approved` transition; the human writes `plan-approved.json` (the Initializer never does), and on the next session the Initializer reads `plan-approved.json.notes` and injects it into `run_state`. *(18.2)*
- **State-Driven:** WHILE no `plan-approved.json` approval marker exists, the system shall keep all implementation Write/Edit tools blocked and the issue shall not leave `Plan-Approved` into `Agent-Executing`. *(18.1)*
- **Unwanted:** IF `plan-approved.json` exists BUT its `feature_list_sha` does not equal the canonical SHA-256 of the current `feature_list.json`, THEN the system shall block all implementation Write/Edit/MultiEdit tools and require re-approval (an approved-then-mutated coverage model cannot silently authorize implementation); the issue moves `Agent-Executing/Plan-Approved → Blocked`. *(18.4)*
- **Optional:** WHERE an operator must halt a running agent capability, the system shall expose an operator-only kill-switch (`kill.<capability>` via self-hosted flagd) that disables the capability within ≤30s without a process restart, restricted to the Delivery Owner/Operator role, authenticated, and audited — every toggle appends a `gate_audit_log` entry and emits an OTel event. *(Requirement 32.2/32.4/32.5)*

**Acceptance criteria**
1. The `Spec-Verified → Plan-Approved` and `Human-Review → Done` transitions are restricted to `agent_role = human` (Plane Admin); any agent-role attempt is rejected and recorded.
2. A transition into `Agent-Executing` is permitted only when `plan-approved.json` exists AND its `feature_list_sha` matches the current `feature_list.json` SHA-256; a missing marker or SHA mismatch routes the issue to `Blocked` with the gate reason (`gate:completion`).
3. A transition into `Done` is permitted only when a human PR review is recorded AND all required status checks (`formal-verification`, `coverage-gate`, `secrets-scan`, `audit-chain-verify`, `traceability-gate`, `zap-baseline`, `deepeval-gate`) are green; any unproven in-scope item keeps the Stop gate blocking and the issue cannot reach `Done`.
4. Each kill-switch toggle is attributable to the Delivery Owner/Operator, authenticated, appended to `gate_audit_log` (in the tamper-evident hash chain), and emitted to the OTel trace endpoint; an unreachable flagd source fails closed (capability DISABLED).

**Agent state-flow governed:** the two human-only chokepoints — `Spec-Verified → Plan-Approved` (plan gate) and `Human-Review → Done` (PR gate) — plus the defensive `* → Blocked` edge on a missing/stale approval marker. The kill-switch is an out-of-band operator control that can refuse any agent capability at start-of-turn, observable in Plane as a forced `Blocked`/`HANDOFF` with `gate:completion`.

---

## 3. Actionable tasks

Each task is tagged **Infrastructure** | **API** (Plane Webhooks/REST) | **Orchestration**, with subtasks. These provision the workspace and wire the governance model into Plane.

### Task group for E2-S1 (Orchestration)

**T1 — Provision the ASCP workflow, fields & labels [Infrastructure]**
- Create the `Agentic SDLC Control Plane` project (identifier `ASCP`) with the exact description.
- Create the 12 custom states mapped to the correct Plane state-groups (4 cancelled-group terminals: HANDOFF/Blocked/Failed distinct).
- Create the 10 custom properties with exact enums; create the 22 labels in 6 families.

**T2 — Wire the single-inner-loop projection [Orchestration]**
- Bind one Plane issue = one inner loop (initializer/implementer/verifier/research + 6 hooks); no external reasoning framework on the default path.
- Stamp `worktree_branch` + `agent_run_id` on `Plan-Approved → Agent-Executing`; reject the transition if either is empty.
- Model Temporal/Inngest (Phase 5) and Agent_Teams as off-board optional capabilities that never alter the canonical state graph.

**T3 — Transition-authorization webhook [API (Plane Webhooks/REST)]**
- Subscribe to `issue` state-change webhooks; on each change resolve actor `agent_role` against the §1.5 matrix and reverse any unauthorized transition via PATCH.
- Reject any transition whose origin is a prediction/Agent_Teams/external framework; record the blocking reason on the issue.

### Task group for E2-S2 (Role taxonomy)

**T4 — Map agent_role → Plane roles/permissions [Infrastructure]**
- Create Plane workspace members for each role; map agent roles to Member-level, `human` to Admin.
- Encode the §1.5 transition-authority matrix as the canonical config consumed by the webhook (T3, T6).

**T5 — Optional bounded-role scaffolding [Orchestration]**
- Define the optional `design`/`platform`/`reliability` agent markdown templates with explicit `tools` allowlists granting no impl-source write and no verifier write.
- Add a smoke test that parses each role markdown and asserts no verifier write access; keep v1 four-role default.

**T6 — Role-scoped transition + write-scope enforcement [API (Plane Webhooks/REST)]**
- On state-change and on field-write webhooks, enforce that only `verifier` writes `evidence_status=proven` / `tests/` / evidence; block `implementer` self-verification (mirror SubagentStop Property 24).
- Stamp `agent_role` + `requirement_id` automatically on `Backlog → Agent-Triaged`.

### Task group for E2-S3 (HITL)

**T7 — Human-only gate configuration [Infrastructure]**
- Restrict `Spec-Verified → Plan-Approved` and `Human-Review → Done` to Admin (`human`) in Plane; configure the GitHub ruleset required reviewer + required status checks list (single-sourced from tasks.md task 14.2).
- Configure the flagd kill-switch flags (`kill.<capability>`, `kill.all`) restricted to the Delivery Owner/Operator; fail-closed on unreachable source.

**T8 — Plan-approval SHA-binding gate [Orchestration]**
- On `Plan-Approved → Agent-Executing`, verify `plan-approved.json` exists AND `feature_list_sha` matches current `feature_list.json` SHA-256; on mismatch/missing, route to `Blocked` with `gate:completion`.
- On the next session, ensure the Initializer consumes `plan-approved.json.notes` into `run_state`.

**T9 — HITL + kill-switch audit/observability webhook [API (Plane Webhooks/REST)]**
- On the two human-only transitions and every kill-switch toggle, append a `gate_audit_log` entry (event, actor, decision, reason, requirement_id, created_at) and emit an OTel gate-decision event; reflect the result as the issue's `run_state`/`gate` field.
- Gate `Human-Review → Done` on a recorded human PR review plus all-green required status checks; keep the Stop gate blocking while any in-scope item is `unproven`.


## Epic E3 — Intent→Spec Compilation & Coverage Model

### Overview

E3 is the **front half of the Spec-to-Evidence control plane**: it turns terse, human-authored product intent into a machine-verifiable coverage model before a single line of implementation is permitted. It owns the path **intent → EARS-compiled atomic requirements → proactive domain-baseline discovery → bounded spec-completion loop judged by the non-LLM Z3 validator → `feature_list.json` (every item `unproven`) → human plan approval → requirement-amendment re-entry**.

Mapped to the canonical reconciled spec (`.kiro/specs/spec-to-evidence-control/`), this epic delivers **Requirement 1 (Spec Compilation, B01), Requirement 2 (Proactive Discovery, B02), Requirement 3 (Domain-Baseline Checklist Sourcing, B19), Requirement 4 (Spec-Completion Loop, B03), Requirement 5 (Coverage Model, B04), and Requirement 22 (Requirement-Amendment Versioning, B04)**.

The governing invariant E3 must uphold end-to-end: **the authoring agent never votes on completeness.** The `initializer` subagent compiles and elaborates, but the verdict on whether the spec is free of contradictions/ambiguities/gaps is rendered by `spec_validator.py` (Z3-backed, non-LLM) returning `{contradictions, ambiguities, uncovered, violation_count}`. The Stop hook blocks the agent's turn while `violation_count > 0`; the loop is hard-capped at 7 passes and halts to **HANDOFF** on the cap or on any pass that fails to strictly reduce `violation_count`. When `violation_count == 0`, `feature_list.json` is emitted with **every item `unproven`** and the plan is presented for human approval (`plan-approved.json`, SHA-bound to the coverage model).

**Plane representation.** In the ASCP Plane workspace, every E3 story rides the shared control-state machine. The E3-specific lifecycle traverses `Backlog → Agent-Triaged → Spec-Compiling → Spec-Verified → Plan-Approved`, with amendment events (REQ-22) re-entering an item from `Done` back into the working states. The states `Spec-Compiling` (initializer running `spec_validator`) and `Spec-Verified` (`violation_count == 0`; `feature_list.json` emitted, all unproven) are the load-bearing E3 states; `agent_role` is `initializer` (compilation, discovery, loop) or `research` (checklist sourcing) or `human` (confirmation, approval, amendment authorship).

#### Agent state-flow for the epic

```
intent (Backlog)
  └─ initializer classifies → Agent-Triaged  [agent_role=initializer, requirement_id assigned]
       └─ REQ-3: new product class? → research drafts Domain_Baseline_Checklist
            └─ human review → approved_at set (gates discovery)
       └─ REQ-1: compile intent → atomic EARS requirements (spec.json + requirements.md)
       └─ REQ-2: expand against approved checklist → propose inferred requirements
            └─ any UNMAPPED baseline item → BLOCK advancement
            └─ each inferred requirement → human confirmation + provenance=inferred
       └─ REQ-4: Spec-Compiling — loop {spec_validator.py (Z3) → violation_count}
            ├─ violation_count > 0 ∧ pass < 7 → Stop hook exit 2 (block, continue)
            ├─ no strict decrease vs prev pass → HANDOFF (exit 0)
            ├─ pass == 7 ∧ violation_count > 0 → HANDOFF (exit 0, lex specialis)
            └─ violation_count == 0 → Spec-Verified
       └─ REQ-5: emit feature_list.json (all items unproven, in_scope=true)
            └─ plan mode → human writes plan-approved.json (feature_list_sha bound) → Plan-Approved
  amendment (REQ-22): proven item amended → requirement_versions row + re-enter unproven
       └─ COMPLETE blocked while any amended item un-reproven
```

---

### Requirement 1 — Spec Compilation (story ASCP-E3-1)

Maps to **Requirement 1 / B01 / REQ-SPEC-001..004**. The `initializer` subagent compiles terse intent into atomic, individually-testable requirements, each with a unique ID, an EARS-pattern statement, a `priority`, and ≥1 machine-checkable acceptance criterion; rejects vague non-quantified adjectives; persists requirements as version-controlled artifacts; and assigns exactly one of the five EARS patterns via `spec_validator.py`.

**EARS lines**
- **Ubiquitous** — THE system shall compile product intent into atomic requirements, each carrying a unique ID, an EARS-pattern statement, a `priority` field, and ≥1 machine-checkable acceptance criterion.
- **Ubiquitous** — THE system shall persist compiled requirements as version-controlled artifacts (`specs/<feature>/spec.json` + `.kiro/specs/<feature>/requirements.md`), not in model context alone.
- **Event-Driven** — WHEN a requirement is authored or modified, the system shall validate it against the EARS schema and assign exactly one of the five EARS patterns (ubiquitous, event-driven, state-driven, unwanted, optional).
- **Unwanted** — IF a candidate requirement contains a vague adjective from the reject-set {fast, secure, scalable, optimized, efficient, reliable, performant} with no quantified numeric bound in its clause, THEN the system shall reject it and require a quantified criterion before acceptance.
- **Optional** — WHERE the operator extends the vague-adjective reject-set in the threshold registry, the system shall enforce the extended set without a code change.

**Acceptance criteria**
- Every compiled requirement has a unique ID matching `^[A-Z]+-[A-Z]+-[0-9]{3}$`, exactly one `ears_pattern`, a `priority` integer ≥1, and ≥1 acceptance criterion.
- `spec_validator.py` assigns exactly one of the five base EARS patterns per requirement; zero-pattern and multi-pattern requirements are rejected (Property 16).
- The seven-member vague-adjective reject-set is enforced; an adjective is flagged only when no numeric literal (with optional unit) sits within ±6 tokens in the same EARS clause (Property 17).
- Compiled requirements exist on disk as `spec.json` + `requirements.md` and are committed; the compilation does not live in model context alone.
- The Plane story carries `requirement_id` populated, `agent_role=initializer`, and transitions `Backlog → Agent-Triaged → Spec-Compiling`.

**State / fields**: state `Spec-Compiling`; `agent_role=initializer`; `requirement_id=REQ-SPEC-001`; `coverage_type=functional`; `ears_pattern` per item; labels `agent:initializer`, `type:functional`, `phase:0`, `priority:high`.

---

### Requirement 2 — Proactive Discovery (story ASCP-E3-2)

Maps to **Requirement 2 / B02 / REQ-SPEC-010..012**. The system expands intent against the approved Domain_Baseline_Checklist for the detected product class, proposes implied requirements for each baseline item, flags any zero-coverage baseline item `UNMAPPED` (which blocks advancement, CHECK-9a), and presents every inferred requirement for human confirmation with inferred-vs-stated provenance marked.

**EARS lines**
- **Ubiquitous** — THE system shall expand product intent against the curated Domain_Baseline_Checklist for the detected product class and propose implied requirements for each baseline item.
- **Unwanted** — IF any Domain_Baseline_Checklist item has zero proposed requirements after discovery, THEN the system shall flag that item `UNMAPPED` and shall not advance to implementation.
- **State-Driven** — WHILE proactive discovery is active, the system shall present every inferred requirement for human confirmation and shall mark inferred-vs-stated provenance on each requirement.
- **Event-Driven** — WHEN a human confirms an inferred requirement, the system shall admit it into `feature_list.json` with `provenance=inferred`.

**Acceptance criteria**
- Every baseline item in the active checklist has ≥1 proposed requirement OR is explicitly flagged `UNMAPPED`.
- Advancement to implementation is blocked while any baseline item is `UNMAPPED` (CHECK-9a UNSAT).
- Each requirement carries `provenance ∈ {stated, inferred}`; `spec_validator.py` rejects any inferred requirement lacking a provenance tag at authoring time.
- Each inferred requirement is gated by per-item human confirmation before it enters `feature_list.json` (not only bulk plan-mode review).
- The Plane story remains in `Spec-Compiling`/`Agent-Triaged` and cannot advance to `Plan-Approved` while any baseline item is `UNMAPPED`.

**State / fields**: state `Spec-Compiling`; `agent_role=initializer`; `requirement_id=REQ-SPEC-010`; `coverage_type=functional`; labels `agent:initializer`, `type:functional`, `priority:blocking` (UNMAPPED is an advancement blocker), `phase:0`.

---

### Requirement 3 — Domain-Baseline Checklist Sourcing (story ASCP-E3-3)

Maps to **Requirement 3 / B19 / REQ-SPEC-013..015** (and the Req-24 epistemic gate it depends on). When a new product class is first encountered, the `research` subagent queries competitive analysis, industry standards, and OSS reference implementations to draft a Domain_Baseline_Checklist, presented for human review before use; checklists are version-controlled per product class; and the checklist version used is recorded and linked to `feature_list.json` for auditable derivation.

**EARS lines**
- **Event-Driven** — WHEN a new product class is encountered for the first time, the system shall run the `research` subagent to query competitive analysis, industry standards, and OSS reference implementations and draft a Domain_Baseline_Checklist, presenting the draft for human review before use.
- **Ubiquitous** — THE system shall persist Domain_Baseline_Checklists as version-controlled artifacts named by product class (`baselines/<product-class>.md`) so checklists accumulate across projects.
- **Event-Driven** — WHEN a Domain_Baseline_Checklist is used, the system shall record which checklist version was used and link it to `feature_list.json` (`checklist_ref.path`/`version`/`sha`) so the derivation is auditable.
- **Unwanted** — IF a checklist is in DRAFT (`approved_at` is null), THEN the system shall not use it for discovery (PreToolUse checklist-approval guard, CHECK-12).
- **Unwanted** — IF a sourced claim lacks a source URL and authority-tier label or fails the independent fact-check pass, THEN `research_claim_validator.py` shall reject it before human review.

**Acceptance criteria**
- Newness is decided by an Initializer lookup against `domain_baseline_checklists` keyed by `product_class`; absence of an approved (`approved_at` non-null) row triggers `research`.
- The draft checklist is named by product class under `baselines/` and is not used for discovery until `approved_at` is non-null.
- Every external claim carries a source URL + authority-tier label and passes the fact-check pass; `research_claim_validator.py` rejects unlabeled/unverified claims (Property 29).
- `feature_list.json.checklist_ref` records path + version + git blob SHA of the checklist actually used, and a `domain_baseline_checklists` row links it.
- The research output carries a non-null `omission_declaration` (per-EARS-category `[Gap]` markers) accepted by the SubagentStop omission guard.

**State / fields**: state `Spec-Compiling`; `agent_role=research`; `requirement_id=REQ-SPEC-013`; `coverage_type=functional`; labels `agent:research`, `type:functional`, `gate:completion` (the checklist-approval guard gates discovery), `phase:0`, `priority:high`.

---

### Requirement 4 — Spec-Completion Loop (story ASCP-E3-4)

Maps to **Requirement 4 / B03 / REQ-SPEC-020..024**. Spec elaboration runs as a bounded loop judged by the non-LLM Z3 validator. The authoring agent has no vote in the completeness verdict; the Stop hook blocks the agent's turn while `violation_count > 0`; the loop halts to HANDOFF on a non-strict-decreasing pass or at the 7-pass hard cap; at `violation_count == 0` it emits the validated spec + `feature_list.json` and requests human plan approval. The cap/HANDOFF exit-code tiebreak resolves the REQ-SPEC-021 (exit 2) vs REQ-LOOP-005 (exit 0) collision in favor of HANDOFF at the cap.

**EARS lines**
- **Ubiquitous** — THE system shall judge spec completeness with a non-LLM validator (`spec_validator.py`, Z3-backed) returning `{contradictions, ambiguities, uncovered, violation_count}`; the authoring agent shall have no vote in the completeness verdict.
- **Event-Driven** — WHEN the spec agent attempts to end its turn AND `violation_count > 0` AND the pass count is below the hard cap, the Stop hook shall block termination (exit 2) and return the enumerated violations to the agent.
- **Unwanted** — IF a spec-completion pass does not strictly reduce `violation_count` versus the prior pass, THEN the system shall halt and hand off to a human (HANDOFF, exit 0) rather than retrying infinitely.
- **Unwanted** — IF the spec-completion loop reaches its hard pass cap (DEFAULT 7), THEN the system shall halt to HANDOFF (exit 0) and surface the remaining violations — this exit-0 HANDOFF takes precedence over the criterion-4.2 exit-2 block at the cap (lex specialis).
- **Event-Driven** — WHEN `violation_count == 0`, the system shall emit the validated spec and `feature_list.json` and request human plan approval before any implementation begins.

**Acceptance criteria**
- `validate_spec()` always returns exactly the four fields `{contradictions, ambiguities, uncovered, violation_count}`; the authoring agent's output is never consulted in the verdict (Property 14).
- The Stop hook blocks (exit 2) on passes before the cap while `violation_count > 0`; at the cap with `violation_count > 0` it writes `status=handoff`, emits a HANDOFF summary, and allows the stop (exit 0) — never exit 2 (Property 15; REQ-LOOP-005 tiebreak).
- The Initializer persists `run_state.violation_count` (producer) and `run_state.prev_violation_count` each pass; HANDOFF fires immediately when the current count does not strictly decrease.
- `spec_pass_count` is capped at `SPEC_COMPLETION_HARD_CAP=7`, read from the task-44 execution-bounds config; the Z3 timeout DEFAULT is 60 s and returns `violation_count=-1` on timeout.
- At `violation_count == 0` the story transitions `Spec-Compiling → Spec-Verified`; `feature_list.json` is emitted with every item `unproven`; plan mode is entered.

**State / fields**: state `Spec-Compiling` (during loop) → `Spec-Verified` (on `violation_count==0`); on HANDOFF → `HANDOFF`; `agent_role=initializer`; `requirement_id=REQ-SPEC-020`; `coverage_type=functional`; `run_state` field `running`→`handoff`/`complete`; labels `agent:initializer`, `gate:stop`, `type:functional`, `priority:blocking`, `phase:0`, plus `handoff` when the loop hands off.

---

### Requirement 5 — Coverage Model (story ASCP-E3-5)

Maps to **Requirement 5 / B04 / REQ-COV-001..006**. The system maintains `feature_list.json` in which every item has an ID, a type ∈ {functional, NFR, WIRING}, a dependencies list, acceptance criteria, an `in_scope` boolean (default true), and a `status` defaulting to `unproven`. WIRING and NFR obligations are first-class items. A transition into `proven` requires a complete four-field Evidence_Record; the PreToolUse status guard restricts transitions to the permitted edge set and blocks identity mutation/deletion/reorder. While any in-scope item is `unproven`, the deliverable is incomplete.

**EARS lines**
- **Ubiquitous** — THE system shall maintain `feature_list.json` in which every item has an ID, a type ∈ {functional, NFR, WIRING}, a dependencies list, acceptance criteria, an `in_scope` boolean (DEFAULT true), and a `status` field defaulting to `unproven`.
- **Ubiquitous** — THE system shall represent architectural WIRING obligations and NFR items as first-class coverage items in `feature_list.json`, not as code comments or informal afterthoughts.
- **Event-Driven** — WHEN an item is set to `proven`, the system shall require an attached Evidence_Record with exactly four non-empty fields (`test_file`, `test_name`, `output_hash`, `collected_at`); the transition shall be rejected if any field is absent or empty.
- **Unwanted** — IF a tool action would delete, reorder, or modify an existing coverage item's identity, THEN the PreToolUse status guard shall block it; transitions shall proceed only along {`unproven→proven`, `unproven→failed`, `failed→unproven`, `proven→unproven` (amendment-gated only)}.
- **State-Driven** — WHILE any in-scope item is `unproven`, the system shall treat the deliverable as incomplete; gates shall count ONLY `in_scope` items, and an item shall leave scope (`in_scope=false`) only by a human-authored transition.

**Acceptance criteria**
- `schema/feature_list.schema.json` validates a hand-written valid file and rejects an item with `status: proven` but a missing `output_hash` (four-field gate, Property 2).
- WIRING items require integration-test evidence (`evidence_kind == "integration"`); NFR items require `nfr_subtype` (Property 1; allOf clauses).
- The PreToolUse status guard permits only the four edges, blocks into-`proven` without complete evidence, and blocks any deletion/truncation/reorder of the existing item id-sequence (`check_append_only`, Property 3).
- Every item carries `in_scope` (default true); Stop/OPA/Completion gates count only `in_scope` items; out-of-scope is human-authored only (Req 5.7).
- The Initializer seeds the file via `feature_list_init.py` (creation exempt from the artifact/status guards) and populates all items `unproven`.

**State / fields**: state `Spec-Verified` (file emitted, all unproven); `agent_role=initializer`; `requirement_id=REQ-COV-001`; `coverage_type` per item ∈ {functional, NFR, WIRING}; `evidence_status=unproven` (default); labels `agent:initializer`, `type:functional`/`type:nfr`/`type:wiring`, `gate:completion`, `phase:0`, `priority:blocking`.

---

### Requirement 22 — Requirement-Amendment Versioning (story ASCP-E3-22)

Maps to **Requirement 22 / B04 / REQ-COV-007**. When a requirement is amended after approval, the system records a `requirement_versions` row (prior text, new text, author, timestamp, rationale), re-enters the coverage item as `unproven`, and forbids COMPLETE while any amended item is un-reproven (CHECK-10a/10b, Property 25). The amendment is the ONLY event that permits a `proven→unproven` transition through the PreToolUse status guard; the `feature_list.json` item is flipped too (closing the Postgres-down stale-proven hole), and the `feature_list_sha` re-bind forces fresh plan approval when the item's shape changes.

**EARS lines**
- **Unwanted** — IF a requirement is amended after approval, THEN the system shall record a `requirement_versions` row (prior text, new text, author, timestamp, rationale), re-enter the coverage item as `unproven`, and shall not permit COMPLETE while any amended item is un-reproven.
- **Event-Driven** — WHEN `amendment_handler.record_amendment(...)` runs, the system shall, in a single transaction, insert the next monotonic `requirement_versions` row and reset the linked `coverage_items.status` to `unproven`.
- **Unwanted** — IF a `proven→unproven` write to `feature_list.json` is not accompanied by a corresponding `requirement_versions` insert, THEN the PreToolUse status guard shall block it (a bare flip is forbidden).
- **Ubiquitous** — THE system shall retain prior version text and never overwrite it; `requirement_versions` is append-only (UPDATE/DELETE revoked from `app_role`, trigger-enforced).
- **State-Driven** — WHILE any amended item remains un-reproven (in either the Postgres view or the `feature_list.json` source of truth), the system shall block the COMPLETE terminal state.

**Acceptance criteria**
- Each amendment inserts a `requirement_versions` row with monotonically increasing `version`, non-null `prior_text` (from version 1 onward), `new_text`, `author`, `rationale`, and `created_at` (DB-assigned `DEFAULT now()`).
- The amendment re-enters the coverage item `unproven` in BOTH `coverage_items.status` and the `feature_list.json` item (evidence cleared), so a Postgres-down amendment cannot leave the file item `proven` (task 39.15 path).
- COMPLETE is blocked while any amended item is un-reproven (CHECK-10a UNSAT; CHECK-10b SAT — a re-proven amended item may complete).
- The PreToolUse status guard allows `proven→unproven` ONLY when the write carries a corresponding `requirement_versions` insert; a bare flip is blocked (Property 3 / Property 25).
- The invoking actor is a human operator action, not an autonomous agent; the `feature_list_sha` re-bind re-blocks implementation under a stale approval when the item's `id`/`type`/`acceptance_criteria` changes.

**State / fields**: state transition `Done → Spec-Compiling` (re-entry to working states; item leaves `Done`); `agent_role=human` (amendment authorship) then `initializer` for re-elaboration; `requirement_id=REQ-COV-007`; `evidence_status` flips `proven→unproven`; `coverage_type=functional`; labels `human:review`, `agent:initializer`, `gate:completion`, `type:functional`, `priority:high`, `phase:2` (the `requirement_versions` table + handler land in Phase 2 / migration 007).

---

### Coverage-gate note for E3

E3 produces the artifact the rest of the platform gates on: `feature_list.json` with every item `unproven`. E3 itself is "done" (`Spec-Verified` → `Plan-Approved`) when (1) `spec_validator.py` returns `violation_count == 0`, (2) zero baseline items are `UNMAPPED`, (3) every inferred requirement is human-confirmed with provenance, (4) the checklist used is approved and version-linked, and (5) a SHA-bound `plan-approved.json` is written by a human. No E3 coverage item reaches `proven`/`Done` inside this epic — proving is the job of the execution/verification epics; E3's exit is `Plan-Approved`, not `Done`.


# Epic E4 — Verification Engine & Evidence

**Plane project:** Agentic SDLC Control Plane (`ASCP`)
**Baseline blocks covered:** B06 (Incremental execution control), B07 (Wiring verification), B08 (Verification engine + perf/a11y/UI-completeness)
**Assigned reconciled requirements:** REQ-7 (Requirement 7 / REQ-EXEC-001..005), REQ-8 (Requirement 8 / REQ-EXEC-010..012), REQ-9 (Requirement 9 / REQ-VERIFY-001..006), REQ-25 (Requirement 25 / REQ-VERIFY-007, REQ-VERIFY-008)
**Governing invariant:** deterministic gates — Claude Code hooks, CI, OPA — decide whether a slice is verified, computed solely from verifiable facts (Evidence_Records). Model self-assessment never gates. The implementer never grades its own homework: the Verifier is a separate subagent with no write access to implementation source (Property 24).

## Overview

E4 is the heart of the "is wired, is proven" half of the Spec-to-Evidence engine. It governs how a single slice moves from an approved coverage item to a `proven` item carrying an attached Evidence_Record:

1. **One slice at a time, in isolation (REQ-7).** A coding subagent session is restricted to exactly one highest-priority `unproven` item, built in a dedicated git worktree, producing one atomic commit. Two deterministic PreToolUse gates wrap this: the plan-approval gate (no `plan-approved.json` ⇒ no Write/Edit) and the scope-sequencing gate (any prior-slice item `unproven` ⇒ no new worktree/slice; Property 7, Z3 CHECK-6a).
2. **WIRING verification (REQ-8).** Static call-graph / dead-code analysis (`wiring_checker.py` AST + Semgrep `wiring_dead_code.yml`) detects symbols that compile but are never reached from a real execution path. Each wiring obligation is a first-class `WIRING` coverage item; an unreachable handler/route/job/callback flips `unproven → failed`; a `WIRING` item can only reach `proven` with an integration-test Evidence_Record (`evidence_kind: integration`).
3. **The independent five-layer verifier (REQ-9).** The `verifier.md` subagent runs structural (lint/mypy/AST), semantic (unit + integration tests), behavioral (Playwright), security (Semgrep + CodeQL), and performance + accessibility layers, captures a complete four-field Evidence_Record via `evidence_collector.py`, and flips `unproven → proven` only when all layers pass and touched-file line coverage ≥ 85% (Property 23). The PostToolUse hook runs lint + mypy + Semgrep + wiring as next-turn feedback (never a gate).
4. **Performance, accessibility & UI-completeness (REQ-25).** The `perf_a11y_verifier` capability (the fifth layer) dispatches on `subtype`: `performance` → k6/Lighthouse numeric budgets; `accessibility` → axe-core zero WCAG-A/AA violations; `ui-screen` → Playwright render assertions over every `declared_state` (`empty`/`loading`/`error`/`ready`). Property 31; no Z3 oracle, PBT/CI-verified.

### Plane state-flow this epic drives

```
Plan-Approved ──(implementer claims highest-priority unproven slice; worktree created)──▶ Agent-Executing
Agent-Executing ──(atomic commit with requirement_id in trailer; handed to Verifier)──▶ In-Verification
In-Verification ──(5 layers pass + complete Evidence_Record + coverage ≥85%)──▶ Human-Review ──▶ Done
In-Verification ──(any layer fails / unreachable WIRING symbol / coverage <85%)──▶ Failed   (evidence_status = failed; evidence withheld)
Agent-Executing ──(retry budget=3 exhausted | cap=25 | budget=1M tokens | no-progress N=3)──▶ HANDOFF
Plan-Approved   ──(PreToolUse blocks: no plan-approved.json, or prior-slice item unproven, exit 2)──▶ Blocked
```

`gate` field usage in this epic: `pretooluse` (plan + scope sequencing), `posttooluse` (lint/SAST/wiring feedback), `subagentstop` (Evidence_Record schema + role separation), `stop` (no unproven in-scope item remains), `opa`/`ci` (merge-time zero-evidence + coverage + perf/a11y checks).

---

## REQ-7 — Incremental Execution Control (one slice, one worktree, scope-sequenced)

> Grounded in reconciled Requirement 7 (B06 / REQ-EXEC-001..005), acceptance criteria 7.1–7.5; Property 7 (Scope Sequencing Gate, Z3 CHECK-6a); design Implementer subagent (`.claude/agents/implementer.md`), PreToolUse plan-gate + scope-gate rows; tasks 6.1, 10.2, 11.1, 16.1, 17.1; Sandbox & Worktree Isolation (REQ-17.4 / task 46).

**Plane story key:** ASCP-E4-S1
**Title:** Force one bounded slice at a time in an isolated worktree, scope-sequenced behind deterministic gates
**State:** Agent-Executing (`started`) · **agent_role:** implementer · **requirement_id:** REQ-EXEC-001 · **coverage_type:** functional
**Labels:** agent:coder, type:functional, priority:blocking, gate:stop, phase:0
**Plane fields:** run_state = running · worktree_branch = `slice/<item_id>` · agent_run_id = `<llm-run-id>` · gate = pretooluse · ears_pattern = state-driven

### EARS lines

- **Ubiquitous (7.1):** THE system SHALL restrict each coding subagent session to exactly one highest-priority `unproven` coverage item — the LOWEST `priority` integer among `unproven` items whose `dependencies` are ALL `proven`, ties broken by item `id` lexical order.
- **State-Driven (7.2):** WHILE a Slice is in progress, THE system SHALL isolate it in a dedicated git worktree (`git worktree add .worktrees/<item_id> -b slice/<item_id>`) to prevent cross-slice collisions.
- **Ubiquitous (7.3):** THE system SHALL target a per-slice size of ≤15 minutes / ≤1 feature and SHALL produce exactly one atomic commit per completed Slice, carrying the requirement ID in the git trailer.
- **Unwanted (7.4):** IF no `plan-approved.json` approval marker exists (or its `feature_list_sha` ≠ the canonical SHA-256 of the current `feature_list.json`), THEN THE PreToolUse_Hook SHALL block all implementation Write/Edit/MultiEdit tools (exit 2).
- **Unwanted (7.5):** IF any prior-slice coverage item is `unproven`, THEN THE PreToolUse_Hook SHALL block initiation of a new worktree or new slice assignment (exit 2), preventing forward progress until the prior item is verified. *(Z3 CHECK-6a: `newSliceStarting ∧ priorItemUnproven` is UNSAT.)*

### Acceptance criteria

- AC-7.1 — Given a `feature_list.json` with several `unproven` items, the implementer selects exactly one: the lowest `priority` integer whose `dependencies` are all `proven`, ties broken by `id` lexical order; an item with an unproven dependency is never selected.
- AC-7.2 — `tools/worktree_manager.py` creates exactly one worktree per active slice on branch `slice/<item_id>`; a duplicate `create_worktree(item_id)` for the same item raises an error; `git worktree list` shows exactly one entry for that item.
- AC-7.3 — A completed slice yields one atomic commit whose trailer contains a `REQ-<DOMAIN>-NNN` ID; the implementer returns with NO Evidence_Record (it does not self-verify) and hands off to the Verifier as a separate subagent.
- AC-7.4 — Calling `pre_tool_use_hook.py` with a `Write` event and no `plan-approved.json` exits 2; with a valid `plan-approved.json` whose `feature_list_sha` matches, the same `Write` exits 0; a present-but-stale `feature_list_sha` exits 2 and requires re-approval.
- AC-7.5 — Calling `pre_tool_use_hook.py` with a worktree-create event while any prior item is `unproven` exits 2; when all prior items are `proven` it exits 0. Bypass forms (worktree created via a wrapper script or a non-Bash tool) are also blocked (covered by the bypass-form property test).
- AC-7.6 — The implementer's `tools` frontmatter allowlist is `[Read, Grep, Glob, Edit, Write, Bash]`; a smoke test parses the agent markdown and asserts Write/Edit are confined to the slice worktree (sandbox REQ-17.4) with NO `tests/`, `schema/`, CI, or other-worktree access.
- AC-7.7 — The implementer owns the retry budget (`run_state.retry_count`, DEFAULT 3) and the per-slice token/cost budget (DEFAULT 1,000,000 tokens); on `retry_count >= 3` or budget exhaustion the slice routes to HANDOFF rather than retrying indefinitely.

### Agent state-flow (REQ-7)

```
Plan-Approved
   │ implementer reads feature_list.json → selects 1 highest-priority unproven item (deps all proven)
   ▼
[PreToolUse plan-gate]  plan-approved.json present AND feature_list_sha matches?  ──no──▶ Blocked (exit 2)
   │ yes
   ▼
[PreToolUse scope-gate]  all prior-slice items proven?  ──no──▶ Blocked (exit 2, CHECK-6a)
   │ yes
   ▼
Agent-Executing  (worktree slice/<item_id> created; ≤15min/≤1 feature; one atomic commit w/ requirement_id trailer)
   │ retry_count<3 AND within token budget                         retry_count>=3 | budget hit | no-progress N=3
   ▼                                                                              ▼
In-Verification  (handed to Verifier — implementer returns NO Evidence_Record)   HANDOFF
```

### Tasks

- **[Infrastructure] Author `.claude/agents/implementer.md` coding subagent** *(tasks 10.2)* — frontmatter `name: implementer`, `model: claude-opus-4-8`, `tools: [Read, Grep, Glob, Edit, Write, Bash]`; behaviors: highest-priority-unproven selection predicate (deps-respecting, id-tie-broken), worktree create, ≤15min/≤1 feature, one atomic commit with requirement_id trailer, no self-verification; retry-budget + token-budget ownership → HANDOFF; kill-switch instrumentation point (capability checked against flagd before a slice starts). Subtasks: write frontmatter + permission scope; write key-behaviors prose; add smoke test parsing the markdown asserting worktree-only/no-tests scope.
- **[Infrastructure] Implement `tools/worktree_manager.py`** *(task 11.1)* — `create_worktree(item_id)`, `remove_worktree(item_id)`, `list_active_worktrees()`; enforce one worktree per active slice; fail if a worktree already exists for `item_id`. Subtasks: implement create/remove/list; one-per-slice enforcement; integration tests (create→list shows one entry, remove→delisted, duplicate→error).
- **[Infrastructure] Sandbox & worktree isolation enforcement** *(task 46 / REQ-17.4)* — confine agent-executed filesystem writes to the per-slice git worktree mounted into the sandbox (devcontainer locally / E2B in CI); network egress DENIED by default. Subtasks: wire the worktree as the mounted unit of isolation; deny egress; tie the confinement to the one-slice/one-worktree implementer discipline.
- **[API] PreToolUse plan-approval gate in `pre_tool_use_hook.py`** *(task 6.1, `check_plan_approval`)* — block any Write/Edit/MultiEdit when `plan-approved.json` is missing OR its `feature_list_sha` ≠ current `feature_list.json` SHA-256; emit a Plane webhook payload mapping the block to the issue's `gate = pretooluse` field and state transition Plan-Approved→Blocked. Subtasks: implement `check_plan_approval`; SHA-bind check; property test (Property 6); Plane REST update on block.
- **[API] PreToolUse scope-sequencing gate in `pre_tool_use_hook.py`** *(task 6.1, `check_scope_sequencing`)* — block any `git worktree add` / `worktree_manager.create_worktree` / slice-assign command when any prior-slice item is `unproven`; cover bypass forms (wrapper script, non-Bash tool). Subtasks: precise detection-surface patterns; bypass-form property test (Property 7); chain ordering (integrity → plan → scope → artifact → status → schema → checklist); Plane REST update mapping block to state Blocked.
- **[Orchestration] Phase-0 spine smoke + e2e** *(tasks 16.1, 17.1)* — drive the gates end-to-end: no `plan-approved.json` ⇒ Write exits 2; valid marker with matching SHA ⇒ exits 0; worktree-create while a prior item is `unproven` ⇒ exits 2. Subtasks: `tests/smoke/test_spine_e2e.py`; `tests/integration/test_phase0_integration.py`; assert stderr names the blocking item ID and the Plane state transitions fire.

---

## REQ-8 — Wiring Verification (compiles ≠ wired)

> Grounded in reconciled Requirement 8 (B07 / REQ-EXEC-010..012), acceptance criteria 8.1–8.3; design "Wiring / Dead-Code Analysis (`wiring_checker.py`)" subsection (real-execution-path definition, whole-repo reachability, emission, no-Z3 assurance note); Verifier key-behaviors (consume `wiring_checker` findings; `unproven → failed` on unreachable; integration-test evidence with `evidence_kind: integration`); CoverageItem `allOf` WIRING→integration rule; tasks 18.1, 19.1, 19.3, 24.1, 47, 26.1.

**Plane story key:** ASCP-E4-S2
**Title:** Detect compile-but-unwired handlers/routes/jobs/callbacks and require integration-test evidence to prove WIRING items
**State:** In-Verification (`started`) · **agent_role:** verifier · **requirement_id:** REQ-EXEC-010 · **coverage_type:** WIRING
**Labels:** agent:tester, type:wiring, priority:high, gate:completion, phase:1
**Plane fields:** run_state = running · evidence_status = unproven → proven|failed · coverage_type = WIRING · output_hash = `sha256:<64hex>` · gate = subagentstop · ears_pattern = unwanted

### EARS lines

- **Ubiquitous (8.1):** THE system SHALL run static call-graph and dead-code analysis on changed files and SHALL represent each wiring obligation as a first-class `WIRING` coverage item in `feature_list.json` (`type: "WIRING"`, `status: unproven`, `in_scope: true`, ≥1 acceptance criterion).
- **Unwanted (8.2):** IF a handler, route, job, or callback exists but is unreachable from any real execution path (no static call/usage chain from a seeded entry point; test files excluded from seeding), THEN THE Verifier SHALL mark the corresponding `WIRING` item `failed` (transition `unproven → failed`, permitted by the PreToolUse status guard).
- **Event-Driven (8.3):** WHEN a `WIRING` item is claimed `proven`, THE system SHALL require an integration test exercising the real execution path as the attached Evidence_Record — the Evidence_Record's `evidence_kind` MUST be `integration` (a unit-test Evidence_Record cannot prove a WIRING item), enforced by the CoverageItem `allOf` and at the SubagentStop acceptance gate.
- **Event-Driven (trigger, 8.1):** WHEN a `Write`/`Edit`/`MultiEdit` completes, THE PostToolUse_Hook SHALL invoke `wiring_checker.py` on the changed-file set and return WIRING candidates as next-turn feedback (non-blocking, exit 1).

### Acceptance criteria

- AC-8.1 — `wiring_checker.py` builds a repo-wide call/usage graph (per-file AST graphs merged) and, for any defined-but-unreachable NON-test symbol, emits exactly one WIRING candidate naming that symbol; a reachable route handler emits zero candidates. Entry points are seeded from CLI `__main__`, route/handler decorators, registered hook commands, and registered callbacks; test files are excluded from seeding.
- AC-8.2 — `wiring_dead_code.yml` (Semgrep) covers decorator-routed handlers/routes and registered-but-uninvoked callbacks; `wiring_checker.py` (AST) covers plain defined-but-never-called functions; both emit `type: "WIRING"` candidates de-duplicated by symbol before ingestion (no double-reporting of the same 8.1/8.2 obligation).
- AC-8.3 — A WIRING candidate surfaced as PostToolUse feedback is turned into a `WIRING` CoverageItem (`status` default `unproven`, `in_scope` true, ≥1 acceptance criterion) added to `feature_list.json` via the PreToolUse-status-guard-permitted creation path.
- AC-8.4 — For a `WIRING` item whose symbol `wiring_checker` reports unreachable, the Verifier performs `unproven → failed` and does NOT emit `proven`; the Plane issue moves to Failed with `evidence_status = failed`.
- AC-8.5 — A `WIRING` item transitions to `proven` only when its attached Evidence_Record has `evidence_kind == "integration"` and exercises the real execution path; an attempt to prove it with a unit-test Evidence_Record is schema-invalid (CoverageItem `allOf`) and rejected at the SubagentStop acceptance gate.
- AC-8.6 — Integration test 26.1 exercises the PostToolUse→`wiring_checker` path together: a file with a defined-but-never-called function yields a WIRING finding with `type: "WIRING"` and the symbol name.

### Agent state-flow (REQ-8)

```
Agent-Executing (file edited)
   │ PostToolUse → wiring_checker.py (AST, whole-repo graph) + Semgrep wiring_dead_code.yml
   ▼
WIRING candidates (dedup by symbol) ──▶ initializer/implementer adds type:WIRING CoverageItem (unproven, in_scope)
   ▼
In-Verification  (Verifier consumes wiring_checker findings on the slice)
   │ symbol reachable from a real execution path?
   ├── no  ──▶ unproven → failed   ──▶  Failed (evidence_status=failed)
   └── yes ──▶ integration test exercises the real path? (evidence_kind == "integration")
                   ├── no  ──▶ blocked at SubagentStop / CoverageItem allOf  ──▶ stays unproven
                   └── yes ──▶ unproven → proven (integration Evidence_Record attached) ──▶ Human-Review
```

### Tasks

- **[Infrastructure] Implement `tools/wiring_checker.py`** *(task 19.1)* — accept changed files as argv (one path per positional arg); Python AST call/usage graph MERGED repo-wide; identify symbols unreachable from a seeded entry point (test files excluded); emit one `type: "WIRING"` candidate per dead symbol (JSON to stdout); exit 0 even with findings (blocking is the hook's job). Subtasks: argv contract; per-file AST graphs → merged repo-wide reachability; entry-point seeding (CLI/decorator/hook-command/callback); WIRING candidate emission; unit tests (reachable handler → no finding; defined-but-never-called → finding).
- **[Infrastructure] Write `tools/semgrep_rules/wiring_dead_code.yml`** *(task 24.1)* — rule for route/handler decorators never imported/called from a non-test entry point; rule for callbacks registered in a dict/list but never invoked; test against `tests/fixtures/semgrep/`. Subtasks: decorator-routed rule; registered-callback rule; division-of-labor de-dup with `wiring_checker.py` (by symbol).
- **[API] PostToolUse changed-files handoff to `wiring_checker.py`** *(task 18.1)* — derive the changed-file list from the hook payload (`tool_input.file_path` for Write/Edit; the full edited-path set for MultiEdit) and pass them as argv; collect findings; emit structured feedback; exit 1 (never exit 2). Subtasks: changed-files derivation; argv handoff; non-blocking feedback emission; exception → exit 1.
- **[Orchestration] WIRING-candidate ingestion path** *(task 19.3)* — the implementer/initializer, on receiving a WIRING candidate as PostToolUse next-turn feedback, adds a `type: "WIRING"` CoverageItem (unproven, in_scope, ≥1 AC) to `feature_list.json` through the status-guard-permitted creation path. Subtasks: ingestion actor + write path; ≥1-AC + in_scope defaults; Property-1 schema conformance.
- **[Orchestration] Verifier WIRING handling** *(task 10.3 verifier behaviors + task 47)* — Verifier consumes `wiring_checker` findings on each slice; performs `unproven → failed` for any unreachable WIRING symbol; for a provable WIRING item, requires + attaches an integration-test Evidence_Record (`evidence_kind: integration`). Subtasks: consume/re-run `wiring_checker` per slice; unreachable → `failed` transition; integration-evidence requirement; CoverageItem `allOf` + SubagentStop enforcement of WIRING→integration.
- **[Orchestration] Phase-1 wiring integration test** *(task 26.1)* — defined-but-never-called function → `wiring_checker.py` JSON output contains a WIRING finding with `type: "WIRING"` and the symbol name; map the finding to a Plane WIRING issue. Subtasks: write `test_phase1_integration.py` wiring leg; assert symbol name + type; assert Plane WIRING-issue creation.

---

## REQ-9 — Verification Engine (independent five-layer verifier + Evidence_Record + coverage)

> Grounded in reconciled Requirement 9 (B08 / REQ-VERIFY-001..006), acceptance criteria 9.1–9.6; design Verifier subagent (`.claude/agents/verifier.md`) five-layer behaviors + frontmatter; `evidence_collector.py` hashing semantics (canonicalized artifact, `sha256:<64hex>`); SubagentStop Acceptance Hook obligation order; Property 2 (four-field gate), Property 23 (line coverage ≥85%), Property 24 (role separation); tasks 8.1, 10.3, 15.1, 18.1, 22.1, 23.1, 28.4 (`actor_agent`), 30.1, 39.10–39.13.

**Plane story key:** ASCP-E4-S3
**Title:** Verify each slice across five independent layers and capture a complete Evidence_Record; the implementer never grades its own homework
**State:** In-Verification (`started`) · **agent_role:** verifier · **requirement_id:** REQ-VERIFY-001 · **coverage_type:** functional
**Labels:** agent:tester, type:functional, priority:blocking, gate:completion, gate:security, phase:0
**Plane fields:** run_state = running · evidence_status = unproven → proven|failed · output_hash = `sha256:<64hex>` · gate = subagentstop · ears_pattern = event-driven

### EARS lines

- **Ubiquitous (9.1):** THE system SHALL verify each Slice across five layers — structural (lint, type-check/mypy, AST analysis via `wiring_checker.py`), semantic (unit + integration tests), behavioral (E2E via Playwright), security (SAST via Semgrep + CodeQL), and performance + accessibility (k6/Lighthouse + axe-core, per REQ-25).
- **Ubiquitous (9.2):** THE system SHALL perform completion verification with the independent Verifier that has no write access to implementation source; the implementer SHALL NOT verify its own output (Property 24 — any Evidence_Record whose `actor_agent == "implementer.md"` is rejected; only `verifier.md`-authored evidence is accepted).
- **Event-Driven (9.3):** WHEN a behavioral check runs, THE Verifier SHALL produce a captured artifact (Playwright trace, screenshot, or test output) attached as an Evidence_Record.
- **Event-Driven (9.4):** WHEN a file edit completes, THE PostToolUse_Hook SHALL run lint, mypy, Semgrep (SAST), and the wiring check, and on failure SHALL return the specific errors to the agent for next-turn correction — it SHALL NOT be relied upon to undo the edit (prevention is the PreToolUse_Hook's job).
- **Unwanted (9.5):** IF a subagent's result lacks required evidence markers, THEN THE SubagentStop_Hook SHALL block acceptance of that result (exit 2); the four-field gate is verifier-only / skip-when-no-evidence (initializer/research results are gated by `omission_declaration`, not the four-field schema).
- **State-Driven (9.6):** WHILE verifying touched files, THE system SHALL enforce a line-coverage threshold of DEFAULT 85% (read from `coverage.json` produced by pytest-cov), failing the Slice and withholding `proven` if any touched file falls below it (Property 23).

### Acceptance criteria

- AC-9.1 — The Verifier runs all five layers in order: structural (ruff/mypy/AST), semantic (unit + integration), behavioral (Playwright → trace/screenshot), security (Semgrep + CodeQL), perf+a11y (REQ-25); a failure in any layer prevents `proven`.
- AC-9.2 — The Verifier's frontmatter `tools` allowlist is `[Read, Grep, Glob, Bash]` (NO Write/Edit/MultiEdit on `src/`); its `tests/` and `feature_list.json`-status writes go through the PreToolUse artifact-guard `verifier.md` carve-out; the artifact guard blocks the Implementer from `tests/` and blocks all destructive ops.
- AC-9.3 — A complete Evidence_Record has exactly four fields (`test_file`, `test_name`, `output_hash` matching `^sha256:[a-f0-9]{64}$`, `collected_at` ISO-8601 with `+00:00` offset), all present and non-empty; a transition into `proven` is rejected (PreToolUse status guard AND CoverageItem `allOf`) if any field is absent/empty.
- AC-9.4 — `evidence_collector.py` computes `output_hash` over the canonicalized verification artifact (volatile fields zeroed, collections sorted, JSON deterministically serialized) so a re-run on the same code reproduces the identical hash; a zero-byte artifact is rejected (or documented as the chosen reject-empty behavior), not blessed as `sha256('')`.
- AC-9.5 — `subagent_stop_hook.py` exits 0 on a complete 4-field Evidence_Record and exits 2 naming the missing field when `output_hash` (or any field) is absent; it BLOCKS (exit 2) any evidence-bearing result whose `actor_agent` is `implementer.md` (Property 24).
- AC-9.6 — PostToolUse runs ruff + mypy + Semgrep + wiring on changed files and emits findings as next-turn feedback at exit 1 (never exit 2); it does NOT enforce the 0-HIGH/CRITICAL SAST threshold (that is the CI SAST gate, CodeQL/Semgrep workflows).
- AC-9.7 — The Verifier flips `unproven → proven` only when all five layers pass AND every touched file has line coverage ≥ 85% read from `coverage.json`; a slice with any touched file < 85% is marked failed and `proven` is withheld (Property 23). SonarQube CI quality gate also fails on a coverage drop below 85%.

### Agent state-flow (REQ-9)

```
In-Verification (Verifier invoked on the committed slice — read-only on src/)
   │ Layer 1 structural (ruff + mypy + AST)            ── fail ─┐
   │ Layer 2 semantic (unit + integration tests)       ── fail ─┤
   │ Layer 3 behavioral (Playwright trace/screenshot)  ── fail ─┤
   │ Layer 4 security (Semgrep + CodeQL)               ── fail ─┼─▶ Failed (evidence_status=failed; evidence withheld)
   │ Layer 5 perf + a11y (REQ-25)                       ── fail ─┤
   │ touched-file line coverage ≥ 85% (coverage.json)  ── no ───┘
   │ all pass
   ▼
evidence_collector.collect(...) → 4-field Evidence_Record (output_hash = sha256 of canonicalized artifact, actor_agent=verifier.md)
   │
   ▼
[SubagentStop]  omission_declaration non-null? → actor_agent ≠ implementer.md? → 4 fields present+non-empty?
   ├── any check fails ──▶ exit 2 (block acceptance) ──▶ Failed
   └── all pass ──▶ flip unproven → proven in feature_list.json ──▶ [Stop hook: no in-scope unproven left] ──▶ Human-Review ──▶ Done
```

### Tasks

- **[Infrastructure] Author `.claude/agents/verifier.md` independent evaluator** *(task 10.3)* — frontmatter `name: verifier`, `model: claude-opus-4-8`, `tools: [Read, Grep, Glob, Bash]`; behaviors for layers 1–4 (structural/semantic/behavioral/security), Evidence_Record assembly via `evidence_collector.py`, `unproven → proven` only when all checks pass and coverage ≥ 85%; permissions read-only on `src/`, write `tests/` + `feature_list.json` status+evidence sub-object via the artifact-guard carve-out. Subtasks: frontmatter + permission scope; four-layer behavior prose; coverage-threshold behavior; forward-reference to task 51's fifth layer.
- **[Infrastructure] Implement `tools/evidence_collector.py`** *(tasks 3.1, 30.1)* — `collect(test_file, test_name, output_bytes)` (sha256:<hex>, tz-aware ISO-8601 `collected_at`); `validate_evidence_record(record)` (4 fields present+non-empty AND `output_hash` matches `^sha256:[a-f0-9]{64}$` AND parseable `collected_at`); `store_to_feature_list(...)` (permits `unproven→proven`/`unproven→failed`/`failed→unproven`; only `*→proven` needs complete evidence); `store_to_postgres(..., actor_agent)` (assert `actor_agent == verifier.md`, reject implementer-authored; never add `actor_agent` to the 4-field JSON object). Subtasks: collect+hash; format-strict validator; status-transition writer; Postgres persistence with role assertion; canonicalization/volatile-field stripping; zero-byte-artifact reject test.
- **[API] PostToolUse hook five-layer feedback** *(task 18.1)* — run ruff + mypy + `semgrep --config auto` (HIGH/CRITICAL filter) + `wiring_checker.py` on changed files; emit structured feedback; exit 1 (non-blocking, never exit 2); exception → exit 1. Subtasks: lint+type+SAST+wiring run; structured-feedback stdout; non-blocking exit contract; Plane comment with findings on the slice issue.
- **[API] SubagentStop Evidence_Record + role-separation gate** *(task 8.1 + design SubagentStop Acceptance Hook)* — parse the Subagent-Result Envelope from stdin; omission-declaration guard first; role-separation block (`actor_agent == implementer.md` → exit 2); four-field evidence-schema gate (skip-when-no-evidence); exit 2 on any failure with enumerated missing fields. Subtasks: stdin parse contract; role-separation check (Property 24); four-field schema gate (Property 2); WIRING→integration `evidence_kind` rule; Plane state update In-Verification→Failed on block.
- **[API] CI security + quality gates** *(tasks 22.1, 23.1)* — SonarQube AI Code Assurance step (fail on new HIGH/CRITICAL or coverage drop < 85%); CodeQL `github/codeql-action/analyze` for Python (fail on HIGH/CRITICAL). Subtasks: SonarQube workflow step; CodeQL workflow; register as required status checks; Playwright CI step (task 15.1) uploading trace artifact on failure.
- **[Orchestration] Verification property suite** *(tasks 39.10–39.13)* — Property 2 (Evidence Schema Enforcement, four-field gate), Property 19 (evidence round-trip), Property 23 (line coverage ≥ 85% on touched files), Property 24 (subagent role separation — implementer cannot self-verify). Subtasks: `test_evidence.py` (Properties 2/19/20/23/24); `--hypothesis-seed=0` determinism; assert `proven` emitted only when all touched files ≥ 85% and `actor_agent == verifier.md`.

---

## REQ-25 — Performance, Accessibility & UI-Completeness Verification (the fifth layer)

> Grounded in reconciled Requirement 25 (B08 / REQ-VERIFY-007, REQ-VERIFY-008), acceptance criteria 25.1–25.3; design "Performance / Accessibility / UI-Screen Verifier (`perf_a11y_verifier`)" subsection (subtype dispatch, Evidence_Record mapping, declared_states enumeration, threshold registry/owner, CI wiring); CoverageItem `nfr_subtype`/`subtype`/`declared_states` schema fields + NFR→`nfr_subtype` `allOf`; Property 31 (perf/a11y/ui-screen evidence required, no Z3 oracle); tasks 51, 51.1, 39.21; threshold registry (Requirement 20, task 44).

**Plane story key:** ASCP-E4-S4
**Title:** Verify performance budgets, accessibility, and UI-screen render-completeness as first-class NFR evidence
**State:** In-Verification (`started`) · **agent_role:** verifier · **requirement_id:** REQ-VERIFY-007 · **coverage_type:** NFR
**Labels:** agent:tester, type:nfr, priority:high, gate:completion, phase:1
**Plane fields:** run_state = running · evidence_status = unproven → proven|failed · coverage_type = NFR · output_hash = `sha256:<64hex>` · gate = ci · ears_pattern = event-driven

### EARS lines

- **Event-Driven (25.1):** WHEN an NFR item of subtype `performance` is verified, THE system SHALL run k6/Lighthouse against numeric budgets (e.g. p95 latency, Core Web Vitals) and attach the structured report as the Evidence_Record (`evidence_kind: perf`).
- **Event-Driven (25.2):** WHEN an NFR item of subtype `accessibility` is verified, THE system SHALL run axe-core and require zero WCAG-A/AA violations on covered screens (`evidence_kind: a11y`).
- **Ubiquitous (25.3):** THE system SHALL treat UI-screen completeness as a verification target: every declared screen/state in a `subtype == "ui-screen"` item's `declared_states` (at least `empty`, `loading`, `error`, `ready`) SHALL have a behavioral test asserting it renders (Playwright render assertion; `evidence_kind: behavioral`/`integration`, NOT a perf/a11y tool).
- **Optional (routing):** WHERE a coverage item is `type == "NFR"`, THE system SHALL require its `nfr_subtype` and SHALL route it deterministically to its evidence tool by reading `subtype`/`nfr_subtype` (`performance` → k6/Lighthouse, `accessibility` → axe-core, `ui-screen` → Playwright) rather than guessing from text.

### Acceptance criteria

- AC-25.1 — A `subtype == "performance"` NFR item is proven only with a k6/Lighthouse report attached as an `evidence_kind: perf` Evidence_Record asserting the p95/Core-Web-Vitals budget read from the Requirement-20 threshold registry (task 44).
- AC-25.2 — A `subtype == "accessibility"` NFR item is proven only with an axe-core run showing zero WCAG-A/AA violations on covered screens, attached as an `evidence_kind: a11y` Evidence_Record.
- AC-25.3 — A `subtype == "ui-screen"` item enumerates `declared_states` (at least `empty`/`loading`/`error`/`ready`); each declared state has an attached render-assertion Evidence_Record produced by the Playwright behavioral layer; a missing state's render evidence withholds `proven` (Property 31).
- AC-25.4 — The CoverageItem schema requires `nfr_subtype` when `type == "NFR"` (`allOf` if/then); the `perf_a11y_verifier` selects its evidence tool from `subtype`/`nfr_subtype` deterministically, never from item text.
- AC-25.5 — k6/Lighthouse/axe/Playwright outputs map into the four-field, `additionalProperties:false` Evidence_Record: `test_file` = runner script / Playwright spec, `test_name` = budget id / screen-state id, `output_hash` = `sha256:<hex>` of the canonicalized report artifact, `collected_at` = run timestamp.
- AC-25.6 — A CI perf/a11y execution path exists (extend `coverage-gate.yml` or a dedicated `perf-a11y` job): for NFR-subtype items it installs and runs k6, Lighthouse, `@axe-core/playwright`, and the per-screen render checks, uploading the result artifacts (the NFR Evidence_Record `output_bytes` source) on failure.
- AC-25.7 — Property 31 (`tests/property/test_perf_a11y.py`) passes: an NFR-perf/NFR-a11y/ui-screen item may not be `proven` without the corresponding evidence; no Z3 oracle, PBT/CI-verified; the frozen 34-check harness count is unchanged.

### Agent state-flow (REQ-25)

```
In-Verification (Verifier fifth layer: perf_a11y_verifier dispatches on item.subtype)
   │
   ├── subtype == performance  ──▶ k6 / Lighthouse vs p95/CWV budget (threshold registry, task 44)
   │                                  ├── budget miss ──▶ Failed (evidence withheld)
   │                                  └── budget met  ──▶ evidence_kind: perf
   ├── subtype == accessibility ──▶ axe-core (WCAG-A/AA)
   │                                  ├── >0 violations ──▶ Failed
   │                                  └── 0 violations  ──▶ evidence_kind: a11y
   └── subtype == ui-screen     ──▶ Playwright render assertion over EVERY declared_state
                                      (empty / loading / error / ready)
                                      ├── any state missing render evidence ──▶ Failed
                                      └── all states render ──▶ evidence_kind: behavioral/integration
   ▼ (evidence assembled into 4-field Evidence_Record via evidence_collector)
[SubagentStop 4-field gate] ──▶ unproven → proven ──▶ Human-Review ──▶ Done
```

### Tasks

- **[Infrastructure] Amend `.claude/agents/verifier.md` with the `perf_a11y_verifier` fifth layer** *(task 51)* — add subtype dispatch (`performance` → k6/Lighthouse, `accessibility` → axe-core, `ui-screen` → Playwright render over `declared_states`); perf budgets + a11y bar read from the Requirement-20 threshold registry (the verifier reads, does not own); Evidence_Record mapping (k6/Lighthouse/axe/Playwright output → four-field schema). Subtasks: 51.1 perf dispatch; 51.2 a11y dispatch; 51.3 ui-screen render over `declared_states`; 51.4 Evidence_Record mapping into the `additionalProperties:false` four-field shape.
- **[Infrastructure] CoverageItem schema fields for NFR/UI routing** *(schema, design lines 376–390)* — `nfr_subtype` enum `{performance, accessibility, reliability, security}` (required when `type == "NFR"` via `allOf`); `subtype` enum `{performance, accessibility, ui-screen}`; `declared_states` array (at least `empty`/`loading`/`error`/`ready`); mirror `nfr_subtype`/`subtype` as columns on the `coverage_items` Postgres table. Subtasks: add schema fields + `allOf` NFR→`nfr_subtype` rule; mirror Postgres columns; enum-sync consistency test.
- **[API] Perf/a11y CI execution step** *(task 51.1)* — extend `.github/workflows/coverage-gate.yml` (or a dedicated `perf-a11y` job) to install + run k6, Lighthouse/Core-Web-Vitals, axe-core (`@axe-core/playwright`), and per-screen render checks for NFR-subtype coverage items; upload k6/Lighthouse/axe result artifacts (the NFR Evidence_Record `output_bytes` source) on failure; register as a required status check. Subtasks: k6 perf-budget step; Lighthouse CWV step; axe-core WCAG scan; per-screen render step; artifact upload; ruleset registration.
- **[Orchestration] Property 31 perf/a11y/ui-screen evidence test** *(task 39.21)* — `tests/property/test_perf_a11y.py`: a `proven` perf/a11y item must carry a `perf`/`a11y` Evidence_Record; a `ui-screen` item must carry a render-assertion Evidence_Record for every `declared_state`; assert the item cannot be `proven` without it. Subtasks: generate NFR-subtype + ui-screen items; assert evidence-required invariant; `--hypothesis-seed=0` determinism; tag `# Feature: spec-to-evidence-control, Property 31`.
- **[Orchestration] `evidence_collector.py` NFR/render artifact assembly** *(task 3.1 NFR/WIRING byte-source)* — `collect()` accepts k6/Lighthouse/axe-core report bytes (perf/a11y) and Playwright trace bytes (ui-screen render) as `output_bytes`, selecting the artifact by `evidence_kind`; canonicalize before hashing. Subtasks: byte-source per `evidence_kind`; canonicalization of JSON reports; round-trip hash-match test for perf/a11y/render artifacts.

---

## Epic-level coverage & gate summary (E4)

| Requirement | Plane story | coverage_type | Terminal gate(s) | Correctness oracle |
|---|---|---|---|---|
| REQ-7 (REQ-EXEC-001..005) | ASCP-E4-S1 | functional | pretooluse (plan + scope), stop | Property 7 (Z3 CHECK-6a) |
| REQ-8 (REQ-EXEC-010..012) | ASCP-E4-S2 | WIRING | posttooluse (feedback), subagentstop (WIRING→integration) | runtime/CI (no Z3 — tests 19.2, 26.1) |
| REQ-9 (REQ-VERIFY-001..006) | ASCP-E4-S3 | functional | subagentstop (4-field + role), opa/ci | Properties 2, 19, 23, 24 (CHECK-7a/7c for the four-field gate) |
| REQ-25 (REQ-VERIFY-007/008) | ASCP-E4-S4 | NFR | ci (perf-a11y job), subagentstop | Property 31 (no Z3 oracle, PBT/CI) |

**Non-bypassable rule for E4:** ambiguous verification states resolve to Failed/Blocked, never proven (fail-closed). No `proven` transition is possible without a complete four-field Evidence_Record authored by `verifier.md`; a `WIRING` item additionally requires `evidence_kind: integration`; an NFR/ui-screen item additionally requires its perf/a11y/render Evidence_Record per Property 31.


# Epic E5 — Completion & Quality-Gate Automation

**Project:** Agentic SDLC Control Plane (`ASCP`)
**Baseline blocks:** B09 (Completion gate), B16 (Supply-chain & security gates), B17 (Human-in-the-loop, kill-switch toggle authority), B08/B11 (eval-gating)
**Assigned requirements:** REQ-10 (Completion Gate, REQ-GATE-001..005), REQ-17 (Supply-Chain & Security Gates, REQ-SEC-001..005), REQ-30 (Eval-Gating in CI, REQ-EVAL-001), REQ-31 (DAST Baseline Security Scan, REQ-SEC-008), REQ-32 (Agent Code Kill-Switch, REQ-CTRL-001)
**Source spec:** `.kiro/specs/spec-to-evidence-control/{requirements,design,tasks}.md` (32 EARS requirements; 34/34 Z3 assertions; `formal_verification_merged.py`)

## Overview

This epic owns the **terminal enforcement surface** of the control plane: the place where the model is structurally unable to declare "done" while any in-scope requirement is unproven, and where agent-generated code is held to supply-chain, dynamic-security, and output-quality bars before it can merge — plus the operator's near-real-time kill-switch over every agent capability.

The governing invariant inherited from the spec: **deterministic gates — Claude Code hooks, CI, OPA — decide whether delivery is complete, computed solely from verifiable facts. Model self-assessment and probabilistic predictions only inform; they never gate.** Every story below is fail-closed: ambiguous states resolve to *blocked*, never *passed* (REQ-GATE-005).

The epic spans the Stop hook (`stop_hook.py` / `evaluate_stop`), the OPA/Conftest merge policy (`coverage_query.rego`), the GitHub repository ruleset (the single canonical required-status-check set), the SAST/secrets/SLSA supply-chain gates and the sandbox isolation boundary, the DeepEval `deepeval-gate`, the OWASP ZAP `zap-baseline` DAST scan, and the OpenFeature/`flagd` kill-switch. Five stories, one per assigned requirement, each grounded in its reconciled `.kiro` requirement.

A load-bearing carve-out runs through the whole epic: the Stop completion gate (REQ-10) is **not** the same as the HANDOFF allow-path (REQ-21/REQ-LOOP-005). At HANDOFF, in-scope items are *expected* unproven and the hook MUST allow (exit 0); only the genuine "we think we're done but aren't" case blocks with exit 2. Getting that ordering wrong reproduces the infinite-block defect already fixed in the spec. Every completion-gate task carries this caveat.

The agent state-flow these gates govern (shared control vocabulary): an issue advances `In-Verification → Human-Review → Done` only when **all** gates pass; a gate that blocks (`exit 2` / OPA deny / failed required check) drives the issue to `Blocked`; a verification failure with evidence withheld drives it to `Failed`; cap/budget/no-progress drives it to `HANDOFF` (never `Done`). The `gate` field records which gate acted (`stop | opa | ci`); `evidence_status` records `proven | failed`.

---

## REQ-10 — Completion Gate (B09 / REQ-GATE-001..005)

**Maps to:** `.kiro` Requirement 10 (criteria 10.1–10.5), reconciled `evaluate_stop` (design.md:952–1039), `coverage_query.rego` (design.md:1248–1297), Z3 CHECK-1/CHECK-3/CHECK-5, Property 4 (Prediction Independence), Property 5 (Unproven Blocks Termination), Property 22 (OPA Zero-Evidence at Merge). HANDOFF carve-out from Requirement 21 / REQ-LOOP-005.

**User story:** As a delivery owner, I want "done" to be impossible while any in-scope requirement is unproven, enforced at three deterministic chokepoints (Stop hook, OPA/Conftest, GitHub required status check) the model cannot talk past, so completion is a queryable fact and not a claim.

### EARS requirements

**REQ-GATE-001 (Ubiquitous):** The system shall compute the completion verdict solely from verifiable facts — zero `unproven` in-scope items, passing tests, and present Evidence_Records — evaluated against the actual repository state, never from model self-assessment or a prediction (CHECK-5 prediction-independence: UNSAT).

**REQ-GATE-002 (Unwanted):** IF the agent attempts to terminate as COMPLETE WHILE any in-scope item is not exactly `proven` (i.e. `unproven` OR `failed`) AND no HANDOFF trigger (cap / budget / no-progress) is active, THEN the Stop_Hook shall block termination (exit 2) and return the enumerated not-proven item IDs (CHECK-1, CHECK-3).

**REQ-GATE-003 (Event-Driven):** WHEN a merge is attempted, the OPA_Conftest required CI status check shall evaluate `feature_list.json` and shall deny the merge if any in-scope item has `status != "proven"` or any in-scope proven item lacks a complete four-field Evidence_Record (the zero-evidence policy query must return zero rows for the merge to pass).

**REQ-GATE-004 (State-Driven):** WHILE a Stop_Hook block is active, the system shall set `stop_hook_active = true` to prevent the hook from re-triggering itself, and shall release the flag only when the blocking condition clears (the reentrancy guard).

**REQ-GATE-005 (Ubiquitous / fail-closed):** The Completion_Gate shall be fail-closed and non-bypassable by configuration; an empty `items[]` array, a parse failure, a validator error (`violation_count < 0`), or any ambiguous state shall resolve to "blocked," not "passed."

**REQ-GATE-005a (Event-Driven, HANDOFF carve-out — from Req 21/REQ-LOOP-005):** WHEN a HANDOFF trigger (iteration cap, cost budget, or the N=3 no-progress predicate) is active, the Stop_Hook shall write `run_state.status = handoff`, emit a HANDOFF summary, and ALLOW termination (exit 0) — it shall NOT return exit 2 for these conditions; the HANDOFF triggers are evaluated BEFORE the unproven-items gate.

### Acceptance criteria

- `evaluate_stop` filters to `in_scope_items = [i for i in feature_list.items if i.in_scope]` and counts ONLY in-scope items in every gate (Req 5.7).
- HANDOFF precedence is realized: cap (phase-discriminated — `spec_pass_count >= 7` in `spec` phase, `iteration_count >= 25` in `implementation` phase), then budget (`token_cost_usd >= TOKEN_BUDGET`), then implementation-phase `check_no_progress` (N=3) each return `allow()` (exit 0) with a HANDOFF summary BEFORE the completion gate is reached.
- The spec-completion sub-gate blocks (exit 2) while `run_state.violation_count > 0`, and fails closed (exit 2) when `violation_count < 0` (validator error).
- The empty-coverage gate blocks (exit 2) when `in_scope_items == []` ("valid INIT state, not COMPLETE — run discovery before termination").
- The completion gate computes `not_proven = [i for i in in_scope_items if i.status != "proven"]` and blocks (exit 2) when non-empty — a `failed` in-scope item blocks exactly like `unproven` (no special-casing only `unproven`).
- `with_reentrancy_guard` sets `stop_hook_active = True` before evaluation, releases it only on `allow`, and short-circuits to `allow()` if the flag is already set (prevents cascade blocking).
- Any unhandled exception in the hook emits to stderr and exits 2 (fail closed).
- `coverage_query.rego` (package `coverage`) denies merge when: (a) any `in_scope == true` item has `status != "proven"`; (b) any in-scope proven item fails `complete_evidence` (all four fields `!= ""`); (c) zero in-scope items exist (INIT, never COMPLETE). The `coverage-gate.yml` CI step treats ANY non-zero Conftest exit as a merge BLOCK.
- The Phase-0 OPA stub (status-only, passes on zero unproven) is intentionally WEAKER than the Phase-1 full policy (adds evidence-presence); the `coverage-gate` required-status-check registration must survive the stub→full swap (re-register; do not assume continuity).
- No gate decision reads a probabilistic prediction (CHECK-5: `predA ≠ predB ∧ gateA = gateB` is SAT — gates ignore predictions).
- Postgres-unavailable fallback (Note N-25): the Stop coverage gate falls back to file-backed state (`feature_list.json` + `claude-progress.txt`), reaches the SAME allow/block decision, and on divergence takes the more conservative (blocking) result — never fail-open.
- Properties 4, 5, 22 pass under `--hypothesis-seed=0`; CHECK-1/CHECK-3/CHECK-5 pass in `formal_verification_merged.py`.

### Agent state-flow

`agent_role = verifier` (the gate is the Verifier/Stop-hook chokepoint, not an authoring role). An issue at `In-Verification` whose Stop gate blocks (exit 2) moves to `Blocked` with `gate = stop`. An issue that clears Stop + OPA + the human PR review advances `Human-Review → Done` with `evidence_status = proven`. A HANDOFF trigger moves the issue to `HANDOFF` (terminal, distinct from `Done`), `run_state = handoff`. An OPA-denied merge sets `gate = opa`, issue `Blocked`. Labels: `gate:completion`, `gate:stop`, `priority:blocking`.

### Tasks

**T10.1 — `stop_hook.py` `evaluate_stop` completion gate + reentrancy guard [Orchestration]**
- Implement `evaluate_stop(event) -> HookDecision` with the exact gate ordering: HANDOFF triggers (cap/budget/no-progress, all `allow()`/exit 0) → spec-completion violation gate (`violation_count < 0` fail-closed; `> 0` block) → empty-coverage gate (`in_scope_items == []` block) → completion gate (`i.status != "proven"` block).
- Implement `with_reentrancy_guard(fn)`: set `stop_hook_active = True`; skip evaluation if already set; release only on `allow`.
- Implement `main()` composing `with_reentrancy_guard(lambda: evaluate_stop(event))`; `sys.exit(0 if allow else 2)`.
- Wrap the whole hook in `try/except`; exit 2 (fail closed) on unhandled exception with structured stderr.
- Phase-discriminate the cap on `run_state.phase` and key each phase on its own counter (`spec_pass_count` vs `iteration_count`).

**T10.2 — `coverage_query.rego` full zero-evidence merge policy [Infrastructure]**
- Author `.github/policies/coverage_query.rego` (package `coverage`) with the three deny rules: not-proven in-scope, proven-without-complete-evidence, and zero-in-scope-items (INIT).
- Implement `complete_evidence(item)` checking all four Evidence_Record fields non-empty.
- Write fixtures under `tests/integration/opa/`: one passing (all in-scope proven with complete 4-field evidence), one failing (one in-scope unproven item).
- Default-deny on empty/absent `items`, parse failure, or malformed `feature_list.json`.

**T10.3 — `coverage-gate.yml` workflow + GitHub ruleset registration [API]**
- Create `.github/workflows/coverage-gate.yml`: install OPA/Conftest; run `conftest test feature_list.json --policy .github/policies/`; treat ANY non-zero Conftest exit as a merge BLOCK.
- Register `coverage-gate` as a REQUIRED status check in the GitHub repository ruleset (reference the canonical required-checks list, do not re-list).
- Mirror the merge-block decision to the Plane issue via webhook→REST: on OPA deny, set issue state `Blocked`, `gate = opa`; on pass, allow advance to `Human-Review`.

**T10.4 — Completion-gate property/Z3 verification + Plane gate mirroring [Orchestration]**
- Wire Property 4 (`test_completion_gate.py` prediction independence), Property 5 (unproven blocks termination, asserting exit 0 on HANDOFF path), Property 22 (OPA zero-evidence at merge) into `tests/property/`.
- Assert CHECK-1/CHECK-3/CHECK-5 pass in `formal_verification_merged.py` as the `formal-verification` required check.
- Subscribe a Plane webhook consumer that, on Stop-hook block/allow and OPA deny/pass events, sets the issue `gate` field, `evidence_status`, and state transition (`In-Verification → Human-Review → Done`, or `→ Blocked`/`→ HANDOFF`) via the Plane REST API, keeping the PM control plane in lockstep with the deterministic gate decisions.

---

## REQ-17 — Supply-Chain & Security Gates (B16 / REQ-SEC-001..005)

**Maps to:** `.kiro` Requirement 17 (criteria 17.1–17.5), the Sandbox & Worktree Isolation subsection (design.md:694–707), `secrets-scan.yml` (design.md:1301–1310), the PreToolUse secret-block guard (design.md:222), SLSA provenance (`actions/attest-build-provenance`), Property 20 (Secret-Free Prompts/Spans/URLs, REQ-17.5), Property 32 (CI Secrets Diff-Scan Blocks Merge, REQ-17.2), tasks 45 (secrets) / 46 (sandbox) / 23–24 (SAST) / 32.1 (SLSA).

**User story:** As a security owner, I want agent-generated code held to SAST, secrets, sandbox-isolation, and signed-provenance gates so autonomy never introduces supply-chain risk, with the "block the commit OR merge" obligation split cleanly between a commit-side PreToolUse prevention gate and a merge-side CI diff-scan.

### EARS requirements

**REQ-SEC-001 (Event-Driven):** WHEN code is changed, the system shall run Semgrep_CodeQL in CI and shall fail the run on any HIGH or CRITICAL severity finding (the in-loop PostToolUse hook runs Semgrep only for next-turn feedback; the CI gate runs both Semgrep and CodeQL and is the enforcing 0-HIGH/CRITICAL gate, Req 20.1).

**REQ-SEC-002 (Unwanted, merge-side):** IF a secret, credential, or token is detected in a PR diff, THEN the `secrets-scan` CI check (gitleaks default; trufflehog acceptable alternative) shall fail and block the merge.

**REQ-SEC-002a (Unwanted, commit-side):** IF a tool call would carry a secret in its prompt, span attributes, URL, or Bash args, THEN the PreToolUse secret-block guard shall block it (exit 2) before emission — this is the commit-side/pre-emission half of "block the commit or merge" (REQ-17.5, Property 20), distinct from the merge-side `secrets-scan` half (REQ-17.2, Property 32).

**REQ-SEC-003 (Event-Driven):** WHEN an artifact is built on merge, the system shall generate signed SLSA build provenance (via `actions/attest-build-provenance`) verifiable through `gh attestation verify`.

**REQ-SEC-004 (State-Driven):** WHILE the agent executes untrusted code, the system shall run it in an isolated sandbox (DEFAULT: devcontainer locally / E2B for ephemeral CI) with network egress DENIED by default and filesystem writes confined to the per-slice git worktree mounted into the sandbox.

**REQ-SEC-005 (Ubiquitous):** The system shall never place credentials or secrets in prompts, spans, or URLs, and shall treat retrieved or model-predicted content as untrusted input data, not as instructions; this prohibition shall be enforced live at the PreToolUse_Hook (exit 2), not only via an offline test.

### Acceptance criteria

- The CI SAST gate (`codeql.yml` + Semgrep workflow) fails the run on any HIGH/CRITICAL finding; the PostToolUse hook surfaces Semgrep findings as next-turn feedback only (exit 1, never blocks) and does NOT enforce the 0-HIGH/CRITICAL threshold.
- `secrets-scan.yml`: `on: pull_request` plus protected-branch pushes; runs gitleaks (pinned action, e.g. `gitleaks/gitleaks-action@v2`) on the PR diff; emits SARIF; `.gitleaks.toml` holds the ruleset + false-positive allowlist; fails (blocks merge) on any detected secret. Fixture acceptance test: a diff with a planted AWS key fails the check; a clean diff passes (Property 32).
- The PreToolUse secret-block guard scans args/prompt/span-attrs/URL against secret regexes (API keys, tokens, passwords, connection strings) and blocks any carrying call with exit 2 (Property 20); it is a live prevention gate, not only an offline test.
- The sandbox confines filesystem writes to the per-slice worktree mounted in, denies network egress by default (allowlist exceptions are explicit and audited), and is the enforcer named by the Implementer's "worktree only" permission line.
- SLSA provenance is generated on merge and is verifiable via `gh attestation verify`; the SLSA release workflow (task 32.1) jointly satisfies REQ-AUDIT-003 alongside the audit-chain verifier.
- `secrets-scan` is a REQUIRED merge gate (Phase 1), registered in the GitHub ruleset and documented in `docs/github-ruleset.md` (canonical list = task 14.2).
- Build-order split: the `secrets-scan.yml` workflow file may be created early (wave 33) but its merge-blocking enforcement must not be a blocking required check until task 45's gitleaks scan logic lands.

### Agent state-flow

`agent_role = verifier` for the CI-gate legs (SAST/secrets/SLSA run in the verification/merge phase); `agent_role = implementer` for the sandbox-confined execution leg. A SAST or secrets failure at `In-Verification`/`Human-Review` moves the issue to `Blocked` with `gate = ci`, `gate:security` label. The PreToolUse secret-block (commit-side) sets `gate = pretooluse`, issue `Blocked`. A clean SLSA-attested merge advances `Human-Review → Done`. Labels: `gate:security`, `gate:ci`, `priority:blocking`, `type:nfr`.

### Tasks

**T17.1 — CI SAST gate (Semgrep + CodeQL) [Infrastructure]**
- Stand up `codeql.yml` (CodeQL) and the Semgrep CI workflow; fail the run on any HIGH/CRITICAL finding (Req 20.1 threshold).
- Confirm division of labor: PostToolUse runs Semgrep-only for feedback (exit 1); CI runs Semgrep + CodeQL as the enforcing gate.
- Register both as required status checks in the GitHub ruleset.

**T17.2 — Secrets-detection gate (`secrets-scan.yml`) [Infrastructure]**
- Author `.github/workflows/secrets-scan.yml`: `on: pull_request` + protected-branch pushes; run gitleaks (pinned) on the PR diff; emit SARIF; fail on any secret.
- Add `.gitleaks.toml` (ruleset + false-positive allowlist for example/test fixtures).
- Add the fixture/acceptance test (`tests/integration/test_github_actions.py`): planted fake AWS key → workflow fails (merge blocked); clean diff → passes.

**T17.3 — PreToolUse secret-block prevention guard [Orchestration]**
- Add `check_secret_block(event)` to `.claude/hooks/pre_tool_use_hook.py`: scan prompt/span-attrs/URL/Bash-args against secret regexes; block (exit 2) on a match; chain it into the pinned guard order.
- Wire Property 20 (`test_secret_free_output`) into `tests/property/`.
- On a commit-side block, mirror to Plane: set issue `gate = pretooluse`, state `Blocked`.

**T17.4 — Sandbox & worktree isolation (REQ-17.4) [Infrastructure]**
- Implement the sandbox boundary: devcontainer locally / E2B for ephemeral CI; network egress DENIED by default with an explicit audited allowlist; filesystem writes confined to the per-slice git worktree mounted in.
- Compose with `git worktree add` (one worktree per active slice, one sandbox per slice execution); name this subsection as the enforcer of the Implementer's "worktree only" permission.

**T17.5 — SLSA build provenance on merge [Infrastructure]**
- Add `actions/attest-build-provenance` to the release/merge workflow (task 32.1) to generate signed SLSA provenance on artifact build.
- Verify with `gh attestation verify`; document the joint REQ-AUDIT-003 satisfaction (provenance + audit-chain verifier).

**T17.6 — Required-check registration + Plane security-gate mirroring [API]**
- Register `secrets-scan` (and confirm SAST checks) as REQUIRED in the GitHub repository ruleset; document in `docs/github-ruleset.md` referencing the canonical task-14.2 list.
- Subscribe a webhook consumer mapping security-gate failures (SAST/secrets) to Plane issue state `Blocked` (`gate = ci`, label `gate:security`), and SLSA-attested clean merges to `Done`, via the Plane REST API.

---

## REQ-30 — Eval-Gating in CI (B08/B11 / REQ-EVAL-001)

**Maps to:** `.kiro` Requirement 30 (criteria 30.1–30.3), `deepeval_gate.py` (design.md:1314–1318 + the DeepEval Quality Gate subsection), the threshold registry (Req 20.3 — faithfulness ≥ 0.8, answer relevancy ≥ 0.7), tasks 55 / 55.1 / 40.6, the fail-closed Error-Handling row (design.md:1373). No Z3 Property/CHECK — named verification tool is the `deepeval-gate` REQUIRED CI check.

**User story:** As a quality owner, I want a DeepEval eval-gating step in CI that asserts LLM output quality (faithfulness, answer relevancy) against versioned golden-set thresholds and blocks the merge on failure — reconciled against the "predictions never gate" invariant by being a deterministic, fixed-judge quality bar scoped to product-output quality, never the completion verdict.

### EARS requirements

**REQ-EVAL-001a (Ubiquitous):** The system shall include a DeepEval eval-gating step in CI using the pytest-native `assert_test()` API for LLM-output quality assertions.

**REQ-EVAL-001b (Event-Driven):** WHEN a CI run includes LLM output to evaluate, THEN the eval step shall gate on the configured DEFAULT metric thresholds (faithfulness ≥ 0.8, answer relevancy ≥ 0.7 — registered in the Requirement-20 threshold registry, operator-overridable) via `assert_test()`, failing the build if any threshold is not met; the evaluable output is sourced from the versioned golden-set fixture under `tests/eval/` (each case supplying the `LLMTestCase` `input` / `actual_output` / `retrieval_context`).

**REQ-EVAL-001c (Ubiquitous, vacuous-pass):** The eval step shall run as a REQUIRED CI status check at merge under the `deepeval-gate` check name; WHEN a CI run contains NO LLM output to evaluate (no fixture case applies), the check shall pass vacuously (green, zero cases asserted) rather than block.

**REQ-EVAL-001d (Unwanted, fail-closed):** IF the judge LLM times out, is rate-limited, is unavailable, or produces a non-deterministic flake, THEN after a bounded retry (up to 2 transient-error retries) the `deepeval-gate` check shall report FAILURE (merge blocked) — a judge that cannot produce a deterministic score is a blocking error, never a silent pass.

### Acceptance criteria

- `tools/deepeval_gate.py` calls `assert_test()` on faithfulness ≥ 0.8 and answer-relevancy ≥ 0.7, reading thresholds from the task-44 execution-bounds/threshold registry (operator-overridable), never hard-coded as the sole source.
- The judge is pinned to a named deterministic model+provider: DEFAULT `claude-opus-4-8` via Anthropic on Vertex AI, `temperature=0`, fixed `seed`, pinned model snapshot — recorded in the gate config / workflow so the judge identity is version-controlled.
- The golden-set dataset lives under `tests/eval/`, is version-controlled (reproducible), and is seeded from Verifier-run evidence.
- Invariant reconciliation is explicit: `deepeval_gate` does NOT self-grade the agent's own output and is NOT a probabilistic completeness prediction — it is a deterministic acceptance check on a fixed dataset scoped to product-output quality, independent of the deterministic completion gates (coverage/evidence/OPA). The completion verdict remains fact-only.
- An empty-evaluation CI run passes vacuously (green, zero cases) — the unconditional REQUIRED status is never blocking-with-nothing-to-evaluate.
- Fail-closed on judge-LLM failure after bounded retry (≤ 2); reproducibility via temperature 0 + fixed seed + fixed model.
- `deepeval-gate` is a REQUIRED status check (registered via Phase-4 task 40.6) and is recorded via GitHub check-run history + SLSA provenance (NOT the hook hash chain — REQ-27.8 scope rule).
- A smoke/integration test asserts the build fails when a metric is below threshold (no Z3 oracle; this is the named verification mechanism).

### Agent state-flow

`agent_role = verifier`. The eval-gate is a merge-time quality bar at `Human-Review`. A sub-threshold metric moves the issue to `Blocked` with `gate = ci`. A vacuous-pass (no LLM output) does not block. A passing eval contributes to the `Human-Review → Done` advance. Labels: `gate:ci`, `type:nfr`, `phase:3`, `priority:high`. `coverage_type = NFR`.

### Tasks

**T30.1 — `deepeval_gate.py` module + pinned judge [Orchestration]**
- Implement `tools/deepeval_gate.py` calling DeepEval `assert_test()` on faithfulness ≥ 0.8 and answer relevancy ≥ 0.7, reading thresholds from the task-44 registry.
- Pin the judge: `claude-opus-4-8` (Anthropic on Vertex AI), `temperature=0`, fixed `seed`, pinned snapshot, recorded in gate config.
- Implement bounded retry (≤ 2 transient-error retries) then fail-closed.

**T30.2 — Golden-set eval fixtures [Infrastructure]**
- Create the versioned `tests/eval/` dataset; each case supplies `LLMTestCase` `input`/`actual_output`/`retrieval_context`, seeded from Verifier-run evidence.
- Implement the vacuous-pass path (zero applicable cases → green).

**T30.3 — `deepeval-gate.yml` workflow + ruleset registration [API]**
- Create `.github/workflows/deepeval-gate.yml`: `on: pull_request`; run `pytest tools/deepeval_gate.py` (or `deepeval test run`).
- Register `deepeval-gate` as a REQUIRED status check (Phase-4 task 40.6) in the GitHub ruleset; document in `docs/github-ruleset.md` (canonical list = task 14.2).

**T30.4 — Eval-gate smoke test + Plane mirroring [Orchestration]**
- Write the smoke/integration test asserting a below-threshold metric fails the build (the named verification mechanism, no Z3 oracle).
- Subscribe a webhook consumer mapping `deepeval-gate` pass/fail to the Plane issue (`gate = ci`, state `Blocked` on fail; contributes to `Done` on pass) via the REST API.

---

## REQ-31 — DAST Baseline Security Scan (B16 / REQ-SEC-008)

**Maps to:** `.kiro` Requirement 31 (criteria 31.1–31.3), `zap-baseline.yml` (design.md:153 + reconciliation list design.md:1854), tasks 56 / 40.5. Baseline block corrected to B16 (Supply-chain & security gates). No Z3 Property/CHECK by documented intent — named verification tool is the `zap-baseline` REQUIRED CI status check.

**User story:** As a security owner, I want an OWASP ZAP baseline passive DAST scan run on every PR against the app stood up in CI, registered as a required merge gate, so dynamic black-box security findings block merge — with active/full scans deferred to v1+ when an authenticated target exists.

### EARS requirements

**REQ-SEC-008a (Ubiquitous):** The system shall run an OWASP ZAP baseline passive scan on every PR via `zaproxy/action-baseline@v0.12.0` with `fail_action: true`.

**REQ-SEC-008b (Event-Driven):** WHEN a PR is opened or updated, the DAST scan shall run against the app stood up in CI at a known `http://localhost:<port>` URL (a CI job step boots the app/service before the scan and populates the action's `target` input with that localhost URL); the `zap-baseline` check shall be a REQUIRED CI status check at merge.

**REQ-SEC-008c (Optional / scope-bound):** WHERE only the v1 baseline is in scope, the system shall run the unauthenticated localhost baseline passive scan ONLY; active/full ZAP scans are OUT OF SCOPE for v1 and are added post-v1 when an authenticated target exists.

### Acceptance criteria

- `.github/workflows/zap-baseline.yml` uses `zaproxy/action-baseline@v0.12.0` with `fail_action: true`, triggered `on: pull_request` (optionally with a protected-branch target filter).
- A CI job step boots the app/service at a known `http://localhost:<port>` and the action `target` input is populated with that URL (the v1 baseline target = unauthenticated localhost).
- The scan is baseline/passive only — no active probing (zero false-positive risk from active probes).
- `zap-baseline` is registered as a REQUIRED CI status check (Phase-4 task 40.5) in the GitHub ruleset, documented in `docs/github-ruleset.md` (canonical list = task 14.2).
- The gate decision is recorded via GitHub check-run history + SLSA provenance (NOT the hook hash chain — REQ-27.8 scope rule); the absence of a Z3 Property/CHECK is documented intent, consistent with `secrets-scan`/`coverage-gate`/`deepeval-gate`.

### Agent state-flow

`agent_role = verifier`. The DAST scan runs at `Human-Review` (merge-time). A ZAP failure (`fail_action: true`) moves the issue to `Blocked` with `gate = ci`, label `gate:security`. A clean baseline contributes to `Human-Review → Done`. Labels: `gate:security`, `gate:ci`, `type:nfr`, `phase:2`, `priority:high`. `coverage_type = NFR`.

### Tasks

**T31.1 — `zap-baseline.yml` DAST workflow + CI app stand-up [Infrastructure]**
- Author `.github/workflows/zap-baseline.yml`: `on: pull_request`; a job step boots the app/service at `http://localhost:<port>`; run `zaproxy/action-baseline@v0.12.0` with `fail_action: true` against that target.
- Constrain to the baseline passive scan (no active/full scan).

**T31.2 — `zap-baseline` required-check registration [API]**
- Register `zap-baseline` as a REQUIRED status check (Phase-4 task 40.5) in the GitHub repository ruleset; add to dependency-graph wave 33.
- Document in `docs/github-ruleset.md` referencing the canonical task-14.2 list.

**T31.3 — DAST gate mirroring to Plane [Orchestration]**
- Subscribe a webhook consumer mapping `zap-baseline` pass/fail to the Plane issue (`gate = ci`, label `gate:security`, state `Blocked` on fail; contributes to `Done` on pass) via the Plane REST API.
- Document the v1 baseline-only scope and the post-v1 authenticated/active-scan deferral as an issue note.

---

## REQ-32 — Agent Code Kill-Switch (B16/B17 / REQ-CTRL-001)

**Maps to:** `.kiro` Requirement 32 (criteria 32.1–32.5), the Agent Kill-Switch subsection (design.md:711–725), the kill-switch invariant (design.md:847), task 57 (+ subtasks), the kill-switch instrumentability note (task 10.2), audit/OTel wiring (Req 32.5 → `audit_log.append` + OTel gate-decision event). Self-hosted OpenFeature + `flagd` (Apache 2.0, CNCF Incubating).

**User story:** As a delivery owner/operator, I want a self-hosted OpenFeature + flagd kill-switch that disables any agent capability within ≤30 s without a process restart, fail-closed when flagd is unreachable, with every toggle authenticated, role-restricted, audited into the tamper-evident hash chain, and observable.

### EARS requirements

**REQ-CTRL-001a (Ubiquitous):** The system shall implement an agent-capability kill-switch using OpenFeature + flagd (Apache 2.0, self-hosted, CNCF Incubating), with no SaaS dependency.

**REQ-CTRL-001b (Event-Driven):** WHEN a kill-switch flag (`kill.<capability>` or `kill.all`) is set, THEN the affected agent capability shall be disabled within the polling interval (≤ 30 s) WITHOUT requiring a process restart; each agent entry point (`initializer`/`implementer`/`verifier`/`research`) queries the OpenFeature client at start-of-turn and HARD-REFUSES the gated capability when its flag is set.

**REQ-CTRL-001c (Unwanted, fail-closed):** IF the self-hosted flagd server / flag source is unavailable, THEN the gated capability shall default to DISABLED (treated as `true`) — fail-closed, consistent with REQ-GATE-005 ("ambiguous states resolve to blocked, not passed"); the kill-switch never fails open.

**REQ-CTRL-001d (State-Driven, authority):** WHILE the kill-switch is in operation, the system shall restrict flag toggles to the Delivery Owner / Operator role; each toggle shall be authenticated and recorded (a flag flip is never an anonymous action).

**REQ-CTRL-001e (Event-Driven, audit/observability):** WHEN a kill-switch flag is set or cleared, the system shall append a `gate_audit_log` entry (event, actor agent/operator, decision, reason, requirement ID, `created_at`) via `tools/audit_log.append(...)` AND emit an OTel gate-decision event to the same trace endpoint as other gate decisions — so the toggle is in the tamper-evident hash chain (Req 27 / REQ-AUDIT-001..003) and observable (Req 12.3 / REQ-OBS-003).

### Acceptance criteria

- The `flagd/` directory holds a flag-definitions file (`flagd.json`), provider config, and a self-hosted deployment manifest; the flag schema enumerates `kill.initializer`, `kill.implementer`, `kill.verifier`, `kill.research`, and a global `kill.all` (boolean kill flags, one per gated capability).
- Each agent entry point queries the OpenFeature client at start-of-turn; a set `kill.<capability>` (or `kill.all`) makes the capability HARD-REFUSE (refuse the gated tool call / skip the capability — analogous to a PreToolUse exit-2 block).
- ONE propagation mechanism is chosen and the ≤30 s guarantee is tied to it: DEFAULT = flagd gRPC streaming (near-instant push); documented fallback = file-based provider with an explicit poll interval ≤ 30 s.
- Unreachable flagd → fail-closed (capability DISABLED, flag treated as `true`); the kill-switch never fails open.
- Flag toggles are restricted to the Delivery Owner / Operator role; each toggle is authenticated and recorded.
- Every toggle (and every start-of-turn kill-refusal) appends a `gate_audit_log` entry via `audit_log.append(...)` AND emits an OTel gate-decision event to the shared trace endpoint.
- A ≤30 s propagation test verifies the chosen provider's mechanism (streaming push or ≤30 s poll) disables the capability without a process restart.
- The OpenFeature kill-switch invariant (a set/unreachable `kill.<capability>` flag implies the gated capability is refused, fail-closed) is documented as a runtime/CI-verified invariant (no Z3 oracle).

### Agent state-flow

`agent_role = human` (the operator owns toggles; the gated capabilities span all four agent roles). A set kill flag at any agent's start-of-turn drives the owning issue to `Blocked` (`gate = pretooluse`-equivalent start-of-turn refusal, `run_state = blocked`); a global `kill.all` halts the loop. Clearing the flag (operator action, authenticated + audited) releases the capability and the issue resumes its prior state (`Agent-Executing` / `In-Verification`). Every toggle is recorded in the `gate_audit_log` and OTel. Labels: `gate:security`, `human:review`, `priority:blocking`, `type:nfr`, `phase:2`. `coverage_type = NFR`.

### Tasks

**T32.1 — Self-hosted flagd service + flag schema [Infrastructure]**
- Create the `flagd/` directory: `flagd.json` flag-definitions, provider config, self-hosted deployment manifest (Apache 2.0, CNCF Incubating).
- Define the kill-switch flag schema enumerating `kill.initializer`/`kill.implementer`/`kill.verifier`/`kill.research`/`kill.all` (boolean, one per gated capability).
- Pick ONE provider mechanism: DEFAULT gRPC streaming; documented fallback file-based polling with explicit ≤30 s interval; tie the ≤30 s verification step to the chosen mechanism.

**T32.2 — OpenFeature SDK wiring into agent entry points [Orchestration]**
- Wire the OpenFeature client into all four agent start-of-turn entry points (`initializer`/`implementer`/`verifier`/`research`); read `kill.<capability>` and `kill.all`; HARD-REFUSE the gated capability when either is `true`.
- Implement fail-closed: unreachable flagd / flag source → treat as `true` (capability DISABLED), never fail open.
- Verify ≤30 s propagation without process restart against the chosen provider mechanism.

**T32.3 — Toggle authority, authentication & audit/OTel wiring [Orchestration]**
- Restrict flag toggles to the Delivery Owner / Operator role; authenticate and record each toggle.
- On set/clear and on each start-of-turn kill-refusal, call `tools/audit_log.append(event, tool, decision, reason, requirement_id, actor_agent)` AND emit an OTel gate-decision event to the shared trace endpoint (Req 32.5 → Req 27 + Req 12.3).
- Add the kill-switch toggle to the `audit_log.append` caller set so the toggle enters the tamper-evident hash chain.

**T32.4 — Kill-switch verification + Plane operator control [API]**
- Add the ≤30 s propagation test and the unreachable-flagd fail-closed test (runtime/CI-verified; no Z3 oracle); document the kill-switch invariant.
- Expose operator toggle authority through Plane: a `human:review` issue action (or webhook→REST mapping) that, when an operator sets a kill flag, drives the owning issue to `Blocked`; on clear, resumes the prior state — keeping the PM control plane synchronized with the kill-switch and recording the operator as the named accountable actor.

---

## Epic E5 coverage summary

| Requirement | EARS lines | Gate surface | Verification | State on block |
|-------------|-----------|--------------|--------------|----------------|
| REQ-10 Completion Gate | GATE-001..005 + 005a | Stop hook + OPA/Conftest + GH ruleset | CHECK-1/3/5; Props 4/5/22 | `Blocked` (`gate=stop`/`opa`) / `HANDOFF` |
| REQ-17 Supply-Chain & Security | SEC-001..005 (+002a) | SAST CI + secrets-scan + PreToolUse + sandbox + SLSA | Props 20/32; gh attestation verify | `Blocked` (`gate=ci`/`pretooluse`) |
| REQ-30 Eval-Gating | EVAL-001a..d | `deepeval-gate` CI | Named CI check (no Z3); smoke test | `Blocked` (`gate=ci`) |
| REQ-31 DAST Baseline | SEC-008a..c | `zap-baseline` CI | Named CI check (no Z3, by intent) | `Blocked` (`gate=ci`) |
| REQ-32 Kill-Switch | CTRL-001a..e | flagd start-of-turn refusal | Runtime/CI invariant; ≤30 s + fail-closed tests | `Blocked` (start-of-turn refusal) |

All five stories are fail-closed; ambiguous states resolve to blocked (REQ-GATE-005, REQ-CTRL-001c). CI-status-check gates (`coverage-gate`/`secrets-scan`/`deepeval-gate`/`zap-baseline`/`audit-chain-verify`) are recorded via GitHub check-run history + SLSA provenance; hook gate decisions (Stop / PreToolUse / SubagentStop, incl. the kill-switch toggle) are recorded in the tamper-evident `gate_audit_log` hash chain — so each gate decision is captured by exactly one of the two execution-proof substrates (REQ-27.8).


## Epic E6 — Agent Integration Layer: Plane ⇄ Agent (Bidirectional)

### Overview

Plane is the **PM control plane** for the Spec-to-Evidence Coverage Control System (project `ASCP` — "Agentic SDLC Control Plane"). This epic builds the **bidirectional bridge** between Plane work items and the Claude-Code control loop defined in the reconciled `.kiro` spec. The bridge is *not* in the original 32-requirement spec — it is the new integration layer that lets Plane state changes drive agent runs and lets agents write proven coverage state back into Plane — but it is bound at every point to the existing canonical artifacts: `feature_list.json` (the coverage model), the eight-table Neon Postgres durable store, the six Claude-Code hooks, and the deterministic completion gate (Stop + OPA/Conftest + GitHub required status check).

The integration is governed by the same top-level invariant as the rest of the platform: **deterministic gates — Claude Code hooks, CI, OPA — decide whether delivery is complete, computed solely from verifiable facts; model self-assessment and probabilistic predictions only inform, they never gate.** Plane state therefore *mirrors* the gate verdict — it never *is* the verdict. A Plane drag-and-drop to `Done` cannot mark a coverage item `proven`; only the Verifier writing a complete four-field `Evidence_Record` through the SubagentStop gate can, and the write-back then *reflects* that fact onto the Plane issue.

The integration has exactly two directions, each with a hard contract:

1. **Plane → Agent (inbound, webhook ingestion).** Plane emits HMAC-SHA256-signed webhooks (`X-Plane-Signature`, `X-Plane-Event`, `X-Plane-Delivery`). A receiver verifies the signature constant-time, dedupes on the `X-Plane-Delivery` id (at-least-once delivery → exactly-once side effect), and translates a state transition into an agent-run trigger. The canonical driver event is an issue entering `Agent-Triaged` (the initializer is dispatched) or `Agent-Executing` (the implementer is dispatched for one slice).

2. **Agent → Plane (outbound, REST write-back via `external_id`).** Every agent-driven state transition in the control loop — `Spec-Compiling`, `Spec-Verified`, `Plan-Approved`, `In-Verification`, `Done`, `HANDOFF`, `Blocked`, `Failed` — is written back to the matching Plane issue using Plane's REST API, keyed by `external_id` (the stable join between a Plane issue and a control-loop `requirement_id`). The write-back also stamps the **traceability triple** (`worktree_branch`, `agent_run_id`, plus the Plane issue id) so issue ↔ branch ↔ run is reconstructable from Plane alone.

The integration layer is itself **observable and steered the same way the agent is**: REQ-12 (OTel) requires every webhook receipt, every REST write-back, and every dispatch decision to emit an OTel span carrying the active `requirement.id` via W3C Baggage; REQ-13 (mid-flight steering) requires that the *only* thing that can halt or redirect a run is a deterministic hook/gate — so a Plane label or comment is advisory context, never a gate. A "stop the agent" intent from a human is realized through the deterministic kill-switch (flagd, REQ-CTRL-001) and the existing hooks, *surfaced* in Plane, not enforced *by* Plane.

This epic is the seam where the two control planes meet. Its correctness property is **state-mirror fidelity**: for every in-scope `requirement_id`, the Plane issue state is an eventually-consistent, idempotent projection of the durable Postgres coverage state, and no Plane action can produce a coverage-state mutation that the deterministic gates would reject.

#### Requirement → Story map (E6)

| Story | Plane state(s) driven/written | Maps to reconciled `.kiro` requirement | Coverage type |
|-------|-------------------------------|----------------------------------------|---------------|
| E6-S1 Inbound webhook ingestion (HMAC + idempotency) | reads `Agent-Triaged`, `Agent-Executing` | REQ-13 (steering — hooks/gates are the only intervention layer), integration | WIRING |
| E6-S2 Webhook-driven agent-run dispatch | `Agent-Triaged`→initializer, `Agent-Executing`→implementer | REQ-7 (incremental execution), REQ-13, integration | WIRING |
| E6-S3 REST write-back of agent state transitions via `external_id` | writes `Spec-Compiling`…`Done`/`HANDOFF`/`Blocked`/`Failed` | REQ-5 (coverage model), REQ-10 (completion gate), integration | functional |
| E6-S4 Provisioning the Plane workspace from the coverage model | seeds states/fields/labels + issues | REQ-1 (spec compilation), REQ-5, integration | functional |
| E6-S5 Bidirectional state-mirror & traceability-triple sync | `worktree_branch`, `agent_run_id` write-back | REQ-6 (traceability), REQ-10, integration | functional |
| E6-S6 Integration-layer observability (OTel spans + Baggage) | all events | REQ-12 (OTel), integration | NFR |
| E6-S7 Plane-as-advisory, gates-as-authority (anti-Plane-gating) | label/comment ingestion | REQ-13 (steering), REQ-19 (predictions never gate), integration | NFR |

Every E6 story is grounded in a reconciled `.kiro` requirement; no story invents a new gate. The shared control vocabulary (12 states, 10 fields, 22 labels) is the single source of truth for every state name, field name, and label used below.

---

### E6-S1 — Inbound webhook ingestion: HMAC-SHA256 verification + delivery idempotency

**Grounds in:** REQ-13 (Mid-Flight Steering — "Claude Code hooks, not prompts, are the sole deterministic intervention layer"; an inbound Plane event is *advisory input that triggers* a run, it does not *gate*); integration. Bound to the durable Postgres store (REQ-16) for the dedupe ledger.

**Plane state read:** the receiver only *reacts* to Plane state changes; it writes none. **agent_role:** `human` (the trigger originates from a human moving a card, or from a prior write-back). **requirement_id:** REQ-INT-001. **coverage_type:** WIRING (the receiver is a handler that must be reachable from a real execution path — REQ-8). **state:** `Agent-Triaged`. **labels:** `type:wiring`, `priority:blocking`, `phase:0`, `gate:security`.

#### EARS

- **Ubiquitous —** THE system SHALL expose a single webhook ingestion endpoint that accepts Plane event deliveries carrying the `X-Plane-Signature`, `X-Plane-Event`, and `X-Plane-Delivery` headers.
- **Event-Driven —** WHEN a Plane webhook delivery is received, THE system SHALL compute `HMAC-SHA256(secret, raw_request_body)` and compare it constant-time against the `X-Plane-Signature` header before parsing the body.
- **Unwanted —** IF the computed HMAC does not equal `X-Plane-Signature`, THEN THE system SHALL reject the delivery with HTTP 401, emit a `gate:security` block decision to the audit/trace layer, and SHALL NOT dispatch any agent run.
- **Unwanted —** IF a delivery arrives whose `X-Plane-Delivery` id already exists in the durable delivery ledger, THEN THE system SHALL acknowledge it HTTP 200 as a no-op and SHALL NOT re-dispatch (at-least-once delivery → exactly-once side effect).
- **State-Driven —** WHILE a delivery's signature is verified AND its `X-Plane-Delivery` id is new, THE system SHALL persist the delivery id to the ledger inside the same transaction that records the dispatch intent, so a crash between dispatch and ack cannot double-fire.
- **Optional —** WHERE the configured signing secret is rotated, THE system SHALL accept deliveries signed by either the current or the immediately-previous secret for a bounded grace window, so rotation does not drop in-flight deliveries.

#### Acceptance criteria

- A delivery with a body-tampered payload but a valid-looking header is rejected 401; an offline unit test proves the constant-time comparison is used (no early-return on first byte mismatch).
- Replaying the identical `X-Plane-Delivery` twice produces exactly one dispatch and two HTTP 200s; verified by an integration test against the ledger row count.
- The dedupe ledger lives in Postgres (a `webhook_deliveries` table: `delivery_id PRIMARY KEY`, `event_type`, `received_at`, `dispatch_id`), reconstructable independently of any model session (REQ-16.3).
- The receiver is registered as a WIRING coverage item in `feature_list.json` and proven only with an **integration-test** Evidence_Record that exercises the real HTTP path (REQ-8.3) — `evidence_kind == "integration"`.
- Signature rejection and replay-noop both emit a `hook.decision`-style span (`event`, `allow|block`, `reason`) to the same trace endpoint as agent spans (REQ-12.3).

#### Agent state-flow

A human moves an intake card from `Backlog` → `Agent-Triaged` in Plane. Plane fires the `issue.updated` webhook. The receiver verifies HMAC, dedupes on `X-Plane-Delivery`, records the delivery, and hands a verified, deduped event to E6-S2's dispatcher. No coverage-state mutation happens here — this story only *admits* the trigger. A forged or replayed delivery dies at the door with a logged `gate:security` block; it never reaches the dispatcher.

---

### E6-S2 — Webhook-driven agent-run dispatch (state → subagent)

**Grounds in:** REQ-7 (Incremental Execution Control — exactly one highest-priority `unproven` item per coding session, in an isolated worktree); REQ-13 (the dispatch is mechanical, not a model decision); integration. The dispatch *honors* the existing PreToolUse scope gate (REQ-7.5) and plan-approval gate (REQ-18.1) — it cannot launch an implementer slice while a prior slice is `unproven` or while no `plan-approved.json` exists.

**Plane states driven:** `Agent-Triaged` → dispatch initializer; `Agent-Executing` → dispatch implementer (one slice). **agent_role:** `initializer` then `implementer`. **requirement_id:** REQ-INT-002. **coverage_type:** WIRING. **state:** `Agent-Executing`. **labels:** `type:wiring`, `agent:initializer`, `agent:coder`, `priority:high`, `phase:0`.

#### EARS

- **Event-Driven —** WHEN a verified deduped event reports an issue entering `Agent-Triaged`, THE system SHALL dispatch the `initializer` subagent for that issue's `external_id`/`requirement_id` and write back the `Spec-Compiling` state.
- **Event-Driven —** WHEN a verified deduped event reports an issue entering `Agent-Executing`, THE system SHALL dispatch the `implementer` subagent for exactly one highest-priority `unproven` coverage item bound to that issue.
- **State-Driven —** WHILE a dispatch is in flight, THE system SHALL record the resulting `agent_run_id` and `worktree_branch` against the issue's `external_id` so the run is traceable before it completes.
- **Unwanted —** IF a dispatch for `Agent-Executing` is requested WHILE any prior-slice coverage item is `unproven`, THEN THE system SHALL refuse the dispatch (mirroring the PreToolUse scope gate, REQ-7.5) and write back a `Blocked` state with `run_state=blocked` and reason "prior slice unproven".
- **Unwanted —** IF a dispatch for `Agent-Executing` is requested WHILE no `plan-approved.json` exists (or its `feature_list_sha` ≠ the canonical coverage-model SHA), THEN THE system SHALL refuse the dispatch (REQ-18.1/18.4) and write back `Blocked` with reason "plan not approved".
- **Optional —** WHERE the flagd kill-switch flag for the targeted agent capability is set (REQ-CTRL-001), THE system SHALL NOT dispatch and SHALL write back `Blocked` with reason "capability disabled".

#### Acceptance criteria

- `Agent-Triaged` dispatch invokes `initializer` and the issue transitions to `Spec-Compiling` via E6-S3 write-back; verified end-to-end on a mock issue.
- `Agent-Executing` dispatch invokes `implementer` against the deterministically-selected item — lowest `priority` integer among `unproven` items whose `dependencies` are all `proven`, ties broken by `id` lexical order (matches `implementer.md` selection predicate) — and no second slice starts while a prior is `unproven`.
- A dispatch attempted with a prior `unproven` slice, or without plan approval, results in a `Blocked` Plane state and an audited block decision — not a silent drop.
- The kill-switch flag flip disables dispatch within ≤30s without a process restart (REQ-CTRL-001.2 / Req 20 propagation interval), proven by a flag-toggle integration test.
- Dispatch never writes `Done` — only the completion gate (E6-S5) can drive `Done`.

#### Agent state-flow

`Agent-Triaged` → dispatcher launches the `initializer`; the issue is written to `Spec-Compiling`, then (on `violation_count==0` and `feature_list.json` emit) `Spec-Verified`, then awaits the human writing `plan-approved.json` → `Plan-Approved`. A human (or an automated post-approval rule) moves the issue to `Agent-Executing`; the dispatcher launches the `implementer` for one slice in an isolated git worktree, recording `agent_run_id` + `worktree_branch`. The scope gate, plan gate, and kill-switch are checked *before* launch; any failing precondition routes to `Blocked` rather than launching. The implementer never self-verifies (Property 24) — completion is the Verifier's domain (E6-S5).

---

### E6-S3 — REST write-back of agent state transitions via `external_id`

**Grounds in:** REQ-5 (Coverage Model — status defaults `unproven`, transitions are gate-controlled); REQ-10 (Completion Gate — `Done` is computed solely from facts); integration. The write-back is the *projection* of durable coverage state onto Plane; it is driven by the same transitions the PreToolUse status guard permits (`unproven→proven`, `unproven→failed`, `failed→unproven`, amendment-gated `proven→unproven`).

**Plane states written:** `Spec-Compiling`, `Spec-Verified`, `Plan-Approved`, `In-Verification`, `Human-Review`, `Done`, `HANDOFF`, `Blocked`, `Failed`. **agent_role:** varies by transition (`initializer`/`verifier`/`human`). **requirement_id:** REQ-INT-003. **coverage_type:** functional. **state:** `In-Verification`. **labels:** `type:functional`, `gate:completion`, `priority:high`, `phase:2`.

#### EARS

- **Ubiquitous —** THE system SHALL maintain a stable `external_id` on every Plane issue equal to the control-loop `requirement_id`, so every write-back targets exactly one issue with no ambiguity.
- **Event-Driven —** WHEN a coverage item's status changes in the durable store, THE system SHALL update the matching Plane issue (resolved by `external_id`) to the mirrored state via Plane's REST API and set `evidence_status`, `run_state`, and `coverage_type` fields accordingly.
- **Event-Driven —** WHEN the Verifier flips an item `unproven → proven` with a complete four-field `Evidence_Record`, THE system SHALL write the issue to `In-Verification` then, after the completion gate confirms zero `unproven` in-scope items, to `Done`, and stamp `evidence_status=proven` + `output_hash`.
- **State-Driven —** WHILE a run is in HANDOFF (cap/budget/no-progress reached, REQ-14), THE system SHALL write the issue to `HANDOFF` (distinct from `Done`), set `run_state=handoff`, and SHALL NOT write `Done`.
- **Unwanted —** IF a write-back would set an issue to `Done` WHILE the OPA/Conftest zero-evidence query would return ≥1 row (any in-scope item unproven), THEN THE system SHALL refuse the `Done` write and instead reflect `Blocked` (REQ-10.5 fail-closed → "blocked, not passed").
- **Unwanted —** IF verification fails on a dead check, THEN THE system SHALL write the issue to `Failed`, set `evidence_status=failed`, and withhold evidence (no `output_hash`).
- **Optional —** WHERE a write-back to Plane's REST API fails transiently (5xx/timeout), THE system SHALL retry with idempotent semantics (same `external_id`, same target state) so a retried write cannot create a duplicate or skip a state.

#### Acceptance criteria

- Every one of the 12 shared-vocabulary states is reachable by a write-back driven by a real control-loop transition; an integration test asserts each `requirement_id` → Plane-state mapping.
- `Done` is written **only** after the completion gate (Stop hook + OPA + GitHub required status check) all pass; a fixture with one `unproven` in-scope item never reaches `Done` and instead lands on `Blocked` (REQ-10.2/10.5).
- `HANDOFF` and `Done` are mutually exclusive — no issue is ever both (mirrors Z3 CHECK-3); a cap-reached run writes `HANDOFF` and never `Done`.
- The write-back is idempotent: replaying the same transition produces no state change and no duplicate comment/field write (verified by a double-apply test).
- `evidence_status`, `run_state`, `coverage_type`, and (when proven) `output_hash` fields are populated from the durable store, never from model self-report.

#### Agent state-flow

The control loop is the source of truth; Plane is the mirror. As an item moves `Spec-Compiling → Spec-Verified → Plan-Approved → Agent-Executing → In-Verification`, each transition is written back via `external_id`. When the Verifier captures a complete `Evidence_Record` and the completion gate confirms zero in-scope `unproven` items, the issue is written `Human-Review` (PR + human reviewer gate, REQ-18.3) and finally `Done` with `evidence_status=proven`. A cap/budget/no-progress halt writes `HANDOFF`; a failed-integrity/approval gate writes `Blocked`; a dead verification check writes `Failed`. The fail-closed rule holds at the seam: an ambiguous or gate-rejecting state always resolves to `Blocked` in Plane, never to a falsely-green `Done`.

---

### E6-S4 — Provisioning the Plane workspace from the coverage model

**Grounds in:** REQ-1 (Spec Compilation — atomic requirements with IDs become issues); REQ-5 (every coverage item is first-class); integration. Provisioning is the one-time forward seed: the reconciled `.kiro` spec + `feature_list.json` → a Plane workspace whose states/fields/labels are exactly the shared control vocabulary.

**Plane states seeded:** all 12 (`Backlog`…`Failed`). **agent_role:** `human` (operator runs provisioning; reviewed before use). **requirement_id:** REQ-INT-004. **coverage_type:** functional. **state:** `Plan-Approved`. **labels:** `type:functional`, `phase:0`, `priority:normal`.

#### EARS

- **Ubiquitous —** THE system SHALL provision the Plane project `ASCP` ("Agentic SDLC Control Plane") with exactly the 12 shared-vocabulary states, mapped to the correct Plane state groups (`backlog`/`unstarted`/`started`/`completed`/`cancelled`).
- **Ubiquitous —** THE system SHALL create the 10 shared-vocabulary custom fields (`agent_role`, `requirement_id`, `evidence_status`, `coverage_type`, `run_state`, `worktree_branch`, `agent_run_id`, `ears_pattern`, `gate`, `output_hash`) with their exact types and dropdown option sets.
- **Event-Driven —** WHEN provisioning runs against an existing coverage model, THE system SHALL create one Plane issue per in-scope `feature_list.json` item, setting `external_id = requirement_id`, `state = Backlog` (or `Agent-Triaged` if already classified), and the item's `ears_pattern`/`coverage_type`.
- **Unwanted —** IF provisioning encounters a coverage item whose `requirement_id` already maps to a Plane issue (by `external_id`), THEN THE system SHALL update that issue rather than create a duplicate (idempotent re-provision).
- **State-Driven —** WHILE provisioning, THE system SHALL create the 22 shared-vocabulary labels and apply the role/type/phase/gate labels implied by each item's fields.
- **Optional —** WHERE the operator supplies a dry-run flag, THE system SHALL emit the full planned create/update set without mutating Plane, for human review before commit (mirrors the plan-approval discipline).

#### Acceptance criteria

- After provisioning, the Plane project has all 12 states in the correct state groups, all 10 fields with exact option sets, and all 22 labels — asserted by a REST read-back diff against the shared-vocabulary spec.
- Re-running provisioning is idempotent: no duplicate states, fields, labels, or issues (verified by running it twice and diffing).
- Every in-scope `feature_list.json` item has exactly one Plane issue with `external_id == requirement_id`; orphan-free in both directions (no issue without an item, no in-scope item without an issue) — mirrors REQ-6.3 orphan detection.
- Dry-run produces a reviewable plan and mutates nothing.

#### Agent state-flow

The operator runs provisioning once per project bring-up. It reads the reconciled spec + `feature_list.json`, creates the `ASCP` workspace skeleton (states/fields/labels), and seeds one issue per in-scope item at `Backlog` with `external_id` bound to `requirement_id`. From that point the bridge is live: human triage moves issues to `Agent-Triaged` (E6-S1/S2 take over), and agent transitions flow back (E6-S3). Re-provisioning after a spec amendment updates in place rather than duplicating, keeping the `external_id` join stable.

---

### E6-S5 — Bidirectional state-mirror & traceability-triple sync

**Grounds in:** REQ-6 (Traceability — bidirectional requirement ↔ implementation ↔ test ↔ evidence ↔ commit ↔ owner; the traceability triple issue↔branch↔run); REQ-10 (the mirror reflects the gate verdict); integration. This is the correctness heart of E6: **state-mirror fidelity**.

**Plane states synced:** all 12, plus the traceability fields. **agent_role:** `verifier` (the authority that flips `proven`) and `human`. **requirement_id:** REQ-INT-005. **coverage_type:** functional. **state:** `Done`. **labels:** `type:functional`, `gate:completion`, `priority:blocking`, `phase:3`.

#### EARS

- **Ubiquitous —** THE system SHALL keep each Plane issue's state an eventually-consistent, idempotent projection of its `requirement_id`'s durable coverage status in Postgres.
- **Event-Driven —** WHEN an agent run produces a slice, THE system SHALL write the traceability triple onto the Plane issue: `worktree_branch` (the git branch), `agent_run_id` (the LLM run id), and the Plane issue id — so issue ↔ branch ↔ run is reconstructable from Plane alone.
- **Event-Driven —** WHEN a commit is created for a slice, THE system SHALL ensure the commit trailer carries the `requirement_id` (REQ-6.2) and SHALL surface the commit SHA on the Plane issue, completing the requirement↔commit link.
- **State-Driven —** WHILE the durable store and Plane disagree about an issue's state (drift), THE system SHALL treat Postgres as authoritative and reconcile Plane toward it, never the reverse.
- **Unwanted —** IF a Plane-side manual edit sets a state that the durable coverage status does not support (e.g. a human drags to `Done` while the item is `unproven`), THEN THE system SHALL revert the Plane issue to the durable-store-backed state and record the rejected edit, because Plane mirrors the gate and cannot override it.
- **Optional —** WHERE a periodic reconciliation sweep runs, THE system SHALL recompute every in-scope issue's state from Postgres and repair any drifted mirror, bounding eventual-consistency lag.

#### Acceptance criteria

- For every in-scope `requirement_id`, Plane state equals the projection of Postgres coverage status; a reconciliation test injects drift and asserts repair toward Postgres.
- The traceability triple (`external_id`/issue id ↔ `worktree_branch` ↔ `agent_run_id`) is queryable from Plane for any proven item; an integration test reconstructs the triple end-to-end.
- A manual Plane drag to `Done` on an `unproven` item is reverted and logged — Plane cannot manufacture a `proven` (Property: no Plane action mutates coverage state past a gate).
- Drift always resolves toward Postgres; the sweep is idempotent (running it on a consistent state is a no-op).

#### Agent state-flow

This story enforces the invariant that makes the whole bridge safe: Plane never gets ahead of the gates. Each slice run stamps `worktree_branch` + `agent_run_id` onto the issue at dispatch (E6-S2), the commit SHA at slice completion, and the `output_hash` at proof (E6-S3). If a human edits Plane in a way the durable store doesn't support, the next webhook/sweep reverts it. The mirror is one-directional in authority (Postgres → Plane) even though events flow both ways: inbound events *trigger* runs, but only gate-verified facts *change* the mirrored state.

---

### E6-S6 — Integration-layer observability: OTel spans + `requirement.id` Baggage

**Grounds in:** REQ-12 (Observability — OTel spans for every model call, tool invocation, and subagent task; gate decisions to the same trace endpoint; `requirement.id` propagated via W3C Baggage). E6 extends REQ-12's coverage to the *integration seam*: webhook receipt, dispatch, and REST write-back are first-class instrumented operations.

**Plane states:** all (cross-cutting). **agent_role:** `human`/`research` (operator monitors). **requirement_id:** REQ-INT-006. **coverage_type:** NFR (`nfr_subtype: reliability`/observability). **state:** `In-Verification`. **labels:** `type:nfr`, `phase:3`, `priority:normal`.

#### EARS

- **Ubiquitous —** THE system SHALL emit an OTel span for every webhook receipt, every dispatch decision, and every REST write-back, attributed with `plane.event`, `plane.delivery_id`, `plane.external_id`, and the mirrored state.
- **Event-Driven —** WHEN the integration layer begins processing a delivery, THE system SHALL set the active `requirement.id` into W3C Baggage so every child span (dispatch, write-back, audit) carries it (REQ-12.4).
- **Event-Driven —** WHEN a webhook is rejected (bad HMAC) or deduped (replay) or a dispatch is refused (scope/plan/kill-switch), THE system SHALL emit that gate decision — event, allow/block, reason, requirement id — to the same trace endpoint as agent spans (REQ-12.3).
- **State-Driven —** WHILE a run is in progress, THE system SHALL stream each integration span to the observability backend as it closes (export interval DEFAULT ≤ 5s), not batched at run-end (REQ-12.2).
- **Optional —** WHERE the managed backend is Langfuse (MIT core, the DEFAULT), THE system SHALL document the backend license so the integration's telemetry destination is compliance-aware (REQ-12.5).

#### Acceptance criteria

- A single webhook→dispatch→write-back flow produces a connected trace where every span carries the same `requirement.id` Baggage value; verified by a trace-assertion integration test.
- HMAC-reject, replay-noop, and dispatch-refuse each emit a distinct gate-decision span with `allow|block` + reason.
- Integration spans export within ≤5s of close (not batched), asserted against a mock OTLP collector.
- The OTel GenAI semconv opt-in and pinned SDK versions match the rest of the platform (`OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`).

#### Agent state-flow

Observability is a non-functional spine for the bridge: an operator watching the trace sees the full causal chain from a human moving a Plane card, through HMAC verification and dispatch, into the agent run, and back out as a write-back — all stitched by one `requirement.id` Baggage value. Because gate decisions (rejections, refusals, blocks) share the trace endpoint with agent spans, the integration layer is auditable mid-flight exactly like the agent it bridges.

---

### E6-S7 — Plane-as-advisory, gates-as-authority (anti-Plane-gating guard)

**Grounds in:** REQ-13 (Mid-Flight Steering — hooks/gates are the *sole* deterministic intervention layer; no gate reads a probabilistic prediction); REQ-19 (predictions are advisory context only, never a gate); integration. This story is the negative guarantee that keeps Plane from becoming a backdoor gate.

**Plane states:** all (cross-cutting). **agent_role:** `human`. **requirement_id:** REQ-INT-007. **coverage_type:** NFR. **state:** `Human-Review`. **labels:** `type:nfr`, `gate:completion`, `phase:4`, `priority:high`.

#### EARS

- **Ubiquitous —** THE system SHALL treat Plane labels, comments, and manual field edits as advisory context that may *inform* an agent run, never as inputs to a deterministic gate decision.
- **Event-Driven —** WHEN a human adds a steering label (e.g. `priority:blocking`) or comment to an issue, THE system SHALL surface it to the agent as injected context (mirroring REQ-19.1 advisory injection) without altering any gate outcome.
- **Unwanted —** IF any integration code path would route a Plane label/comment/manual-state into a block-or-allow gate decision, THEN THE system SHALL reject that design — Plane state SHALL NOT emit gate decisions and gates SHALL NOT read Plane state (mirrors REQ-19.2 / Z3 CHECK-5).
- **State-Driven —** WHILE a human wants to halt a running agent, THE system SHALL realize that intent through the deterministic kill-switch (flagd, REQ-CTRL-001) and the existing hooks, surfacing the halt in Plane as `Blocked`/`HANDOFF`, NOT by treating a Plane state change as the halt mechanism itself.
- **Optional —** WHERE advisory Plane context is injected, THE system SHALL tag those injection spans distinctly so advisory-vs-authoritative inputs are separable in the trace (mirrors REQ-19.3).

#### Acceptance criteria

- A static check (and a Property-style test) proves no gate function imports or reads Plane state; the completion verdict remains a pure function of `feature_list.json` + evidence + OPA (REQ-10.1).
- A human dragging an issue to `Done` cannot mark any coverage item `proven` (re-asserts E6-S5's revert) — the deterministic gate is the only authority.
- A halt intent flows through flagd + hooks and is *reflected* in Plane as `Blocked`/`HANDOFF`, never *caused* by a Plane edit.
- Advisory-context injection spans are tagged distinctly from gate-decision spans.

#### Agent state-flow

This is the constitutional guarantee of the bridge. Plane is the *human-facing control plane* — it shows state, accepts triage, surfaces steering — but the *enforcement* control plane is unchanged: Claude Code hooks, OPA, CI. A label is a suggestion the agent may read; it is never a gate input. A halt is a flagd flip the hooks honor; it is never "drag to a cancelled state." The integration layer's job is to keep these two planes synchronized in *display* while keeping authority strictly on the deterministic-gate side — so that, exactly as the governing invariant demands, completion is decided solely from verifiable facts and Plane only ever *mirrors* that decision.


## Epic E7 — Observability, Audit & Traceability

**Plane project:** Agentic SDLC Control Plane (`ASCP`)
**Baseline blocks:** B05 (Traceability), B10 (Session continuity & durable state), B11 (Observability), B09/B11 (Tamper-evident audit), B15 (Durable storage)
**Assigned reconciled requirements:** REQ-6 (Traceability), REQ-11 (Session Continuity & Durable State), REQ-12 (Observability), REQ-27 (Tamper-Evident Gate-Decision Audit Log), REQ-23 (Resumed-State Integrity), REQ-16 (Durable Storage)
**Governing invariant:** every gate decision and traceability fact is computed solely from verifiable facts and is reconstructable independently of any model session. Observability and audit *inform and prove*; they never themselves gate completion — except the audit-chain verifier and the orphan/traceability gate, which are deterministic CI required checks.

### Overview

E7 is the platform's *evidentiary substrate*: the layer that makes "we can prove what happened" a queryable fact rather than a claim. It binds six reconciled requirements into one coherent control surface:

- **Bidirectional traceability** (REQ-6): every requirement is linked forward to implementation → test → evidence → commit → owner, and every code unit is linked back to a requirement, in the durable Postgres `traceability_links` graph; orphans block the merge via the `traceability-gate` required check, and the active `requirement.id` is stamped onto every telemetry span via a W3C Baggage span processor.
- **Session continuity + durable state** (REQ-11): all mutable run state lives outside model context — in files (`claude-progress.txt`, `feature_list.json`), in git history (one commit per slice), and in the eight-table Postgres store — so a resumed session re-orients deterministically.
- **Observability** (REQ-12): OTel spans for every model call, tool invocation, and subagent task, streamed as each span closes (export interval ≤ 5 s), with every hook gate decision forwarded to the same trace endpoint and `requirement.id` propagated via W3C Baggage.
- **Tamper-evident audit log** (REQ-27): an append-only, hash-chained `gate_audit_log` table where every gate decision (event, tool, allow/block, reason, requirement ID, actor agent, `created_at`) stores the hash of the prior entry; the chain is recomputed by `audit_verify.py` as a required merge check and on demand.
- **Resumed-state integrity** (REQ-23): SessionStart computes a resumed-state hash and writes `run_state.resume_integrity_ok` non-blockingly; a PreToolUse integrity guard blocks the first write of a resumed session (exit 2) on a mismatch until operator reconciliation.
- **Durable storage** (REQ-16): the managed Neon Postgres store is the single source of truth for coverage queries, holding requirements, coverage state, traceability links, Evidence_Records, run state, and the audit log, reconstructable independently of any model session.

These six requirements share a single durable substrate (Postgres + file/git duplicates with a never-fail-open fallback, Note N-25) and a single live substrate (the OTel trace endpoint). The Plane control plane reflects each story's lifecycle through the shared control vocabulary; observability/audit stories are owved primarily by the `human` (Delivery Owner / Operator) and `verifier` agent roles.

---

### REQ-6 — Bidirectional Traceability (requirement ↔ code ↔ test ↔ evidence ↔ commit ↔ owner)

**Plane state:** Agent-Executing → In-Verification → Done
**agent_role:** verifier · **requirement_id:** REQ-TRACE-001 · **coverage_type:** WIRING
**Baseline block:** B05 · **Maps to:** reconciled Requirement 6 (criteria 6.1–6.4), Properties 10/11/12, Postgres `traceability_links`, tasks 20 / 29 / 35 / 40.4
**Labels:** `agent:tester`, `type:wiring`, `gate:completion`, `phase:2`, `phase:3`, `priority:high`

#### EARS

- **Ubiquitous:** The system shall maintain bidirectional links requirement ↔ implementation ↔ test ↔ evidence ↔ commit ↔ owner in the durable Postgres `traceability_links` store. *(6.1)*
- **Ubiquitous:** The system shall stamp the active `requirement.id` onto every telemetry span via a W3C Baggage span processor so traceability is reconstructable from the live trace. *(6.4)*
- **Event-Driven:** WHEN a commit is created, the system shall require ≥1 referenced requirement ID in the commit trailer. *(6.2)*
- **Unwanted:** IF an implementation unit references no requirement, OR a requirement maps to no verification artifact, THEN the system shall fail the orphan-detection check and block the run via the `traceability-gate` required status check. *(6.3)*

#### Acceptance criteria

- `traceability_links` rows are written for every `link_type ∈ {implementation, test, evidence, commit, owner}` with a `direction ∈ {forward, backward}`, FK-bound to `requirements(id)`, indexed by `idx_traceability_links_requirement_id`.
- `tools/traceability_writer.py::parse_commit_trailers(commit_sha)` extracts requirement IDs matching `[A-Z]+-[A-Z]+-[0-9]{3}` from `git log --format=%B`; `assert_commit_has_req_id` raises `TraceabilityError` (non-zero exit) when a commit carries no requirement ID (REQ-6.2 / Property 10).
- `tools/orphan_detector.py` runs full-repo, Python-source-scoped (excluding `tests/`, generated dirs, `__init__.py`, `db/migrations/`), and exits non-zero on (a) any source unit with no requirement ref [forward orphan] or (b) any requirement with no `traceability_links` row of `link_type ∈ ('test','evidence')` AND/OR no `evidence_records` row [backward orphan, the canonical definition]. A `# orphan-exempt: <reason>` marker or allowlisted path exempts a unit (REQ-6.3 / Property 11).
- The `.github/workflows/traceability-gate.yml` REQUIRED status check consumes the non-zero exit of `orphan_detector.py` and folds in `assert_commit_has_req_id`, blocking the merge on any orphan (the production "block the run" mechanism).
- `RequirementBaggageProcessor(SpanProcessor)` in `tools/telemetry.py` sets `baggage.set_baggage("requirement.id", req_id)` on `on_start` for every span under an active requirement context; no requirement-processing span is emitted without a non-empty `requirement.id` (REQ-6.4 / Property 12).
- The forward-orphan and backward-orphan checks each independently trigger failure. The backward-orphan lookup's authoritative store is Postgres (single source of truth, REQ-16.3), with a documented `feature_list.json` fallback per Note N-25.
- The `[A-Z]+-[A-Z]+-[0-9]{3}` trailer-ID extraction is factored into a shared `tools/req_id_scan.py` helper imported by both `orphan_detector.py` and `traceability_writer.py` to prevent regex drift.

#### Agent state-flow

A slice's Implementer commits with the requirement ID in the git trailer (item enters **Agent-Executing**, `worktree_branch`/`agent_run_id`/`requirement_id` populated). The Verifier captures the Evidence_Record and `traceability_writer.py` writes the forward+backward links into `traceability_links`; the item moves to **In-Verification**. At merge the `traceability-gate` required check runs `orphan_detector.py` over the full repo: any orphan blocks the merge (item to **Blocked**, label `blocked`, `gate=ci`); a clean bidirectional graph permits **Done**. Throughout, every span carries `requirement.id` Baggage so the live trace mirrors the durable graph.

#### Tasks

1. **[Infrastructure]** Migration `003_traceability_links.sql` + index — `traceability_links` table with FK to `requirements`, `link_type`/`direction` CHECK constraints, and `idx_traceability_links_requirement_id`.
   - Subtasks: write `db/migrations/003_traceability_links.sql` with the `link_type IN ('implementation','test','evidence','commit','owner')` and `direction IN ('forward','backward')` CHECKs; add the per-requirement index; run on a test Neon branch and assert the table + CHECKs exist.
2. **[Infrastructure]** Shared requirement-ID scanner `tools/req_id_scan.py` — single source of the `[A-Z]+-[A-Z]+-[0-9]{3}` extraction.
   - Subtasks: implement the trailer/comment/docstring ID extractor; import it from both `traceability_writer.py` and `orphan_detector.py`; unit-test that it matches `REQ-TRACE-001`-form IDs and NOT dotted EARS criterion numbers (e.g. `6.3`).
3. **[API]** `tools/traceability_writer.py` — commit-trailer parser + link writer.
   - Subtasks: implement `parse_commit_trailers(commit_sha)`; implement `write_traceability_link(req_id, link_type, target_ref, direction)` inserting into `traceability_links`; implement `assert_commit_has_req_id(commit_sha)` raising `TraceabilityError`; Property-10 PBT `test_commit_trailer_req_id`.
4. **[API]** `tools/orphan_detector.py` — bidirectional orphan check.
   - Subtasks: scan full-repo Python source for requirement-ID refs with the documented exclude list; read `feature_list.json` + Postgres `evidence_records`/`traceability_links` for known IDs; report forward + backward orphans per the canonical definition; honor `# orphan-exempt`/allowlist; exit non-zero with a structured JSON report; Property-11 PBT.
5. **[Orchestration]** `traceability-gate` REQUIRED CI check — `.github/workflows/traceability-gate.yml`.
   - Subtasks: invoke `orphan_detector.py` (block merge on non-zero) and fold in `assert_commit_has_req_id` over the PR's commits; register `traceability-gate` in the GitHub repository ruleset (canonical list in `docs/github-ruleset.md`); integration test asserting a missing-ref source file fails the gate.
6. **[API]** `RequirementBaggageProcessor` in `tools/telemetry.py` — W3C Baggage `requirement.id` propagation.
   - Subtasks: implement the `SpanProcessor.on_start` that sets `requirement.id` Baggage; assert non-empty for any active-requirement span; Property-12 PBT `test_w3c_baggage_propagation`.

---

### REQ-11 — Session Continuity and Durable State

**Plane state:** Agent-Executing (durable trail) · run_state spans all states
**agent_role:** human (operator) · **requirement_id:** REQ-STATE-001 · **coverage_type:** functional
**Baseline block:** B10 · **Maps to:** reconciled Requirement 11 (criteria 11.1–11.4), Postgres `run_state`, hooks `session_start_hook.py`/`pre_compact_hook.py`, tasks 7 / 25 / 31
**Labels:** `human:review`, `type:functional`, `phase:0`, `phase:1`, `phase:2`, `priority:high`

#### EARS

- **Ubiquitous:** The system shall persist all mutable run state outside model context — in files (`claude-progress.txt`, `feature_list.json`), git history, and the durable Postgres `run_state` store. *(11.1)*
- **Ubiquitous:** The system shall record an incremental commit per completed Slice as the durable execution trail and rollback point. *(11.4)*
- **Event-Driven:** WHEN context compaction is imminent, the PreCompact_Hook shall checkpoint progress and evidence records (and write the durable baseline `run_state.resume_state_hash`) before context is trimmed. *(11.2)*
- **Event-Driven:** WHEN a session starts, the SessionStart_Hook shall load git status, the progress file, and the Coverage_Model so a resumed session re-orients deterministically, and shall additionally compute the resumed-state hash and write `run_state.resume_integrity_ok` (bool) without itself halting the run. *(11.3)*

#### Acceptance criteria

- `tools/run_state_store.py::save_run_state(run_state)` upserts into the `run_state` table AND writes `claude-progress.txt` as a file-backed duplicate; the duplicate includes `status`, `no_progress_n`, `stop_hook_active`, `resume_integrity_ok`, and the baseline `resume_state_hash` (not only status), so every gate's DB-down fallback reaches the same conservative/blocking decision (Note N-25, never fail-open).
- `session_start_hook.py` reads `git status --porcelain`, `claude-progress.txt` (created empty if absent), and `feature_list.json` (minimal valid stub if absent), and injects a structured-JSON summary with named fields `git_status`, `unproven_count`, `proven_count` to stdout; exit 0 always (non-blocking).
- `pre_compact_hook.py` checkpoints `claude-progress.txt`, current evidence state, and `feature_list.json` to the MAIN worktree git, AND writes the durable baseline `run_state.resume_state_hash` over the checkpointed state — it is the producer of the recorded baseline hash alongside each per-slice commit; exit 0 (non-blocking checkpoint write).
- Each completed Slice produces exactly one atomic commit (the Implementer's per-slice commit, `last_commit_sha` recorded in `run_state`) as the rollback point.
- The Postgres half of 11.1 (`run_state` upsert) and the file+git half (PreCompact/SessionStart writes) are kept as duplicates; on divergence the more conservative state wins.

#### Agent state-flow

While a slice runs (**Agent-Executing**), `run_state` carries `status=running`, `current_item_id`, `iteration_count`, `last_commit_sha`. When compaction nears, PreCompact checkpoints to git and writes the durable `resume_state_hash`. On the next SessionStart the hook loads git+progress+coverage, recomputes the hash, and writes `resume_integrity_ok` — re-orienting the agent to the exact item it was on. A HANDOFF writes `run_state.status=handoff` (item to **HANDOFF**, label `handoff`); a clean COMPLETE leaves the durable trail intact for audit. The state survives both context limits (PreCompact) and crashes (per-slice commit + Postgres upsert).

#### Tasks

1. **[Infrastructure]** Migration `005_run_state.sql` — durable per-session execution state.
   - Subtasks: create `run_state` with `status` CHECK `{running,complete,handoff,blocked}`, `phase` CHECK `{spec,implementation}`, `stop_hook_active`, `no_progress_n`, `iteration_count`, `spec_pass_count`, `violation_count`, `prev_violation_count`, `retry_count`, `resume_integrity_ok`, `is_resume`, `first_write_done`, `resume_state_hash`, `last_commit_sha`; run on a test Neon branch and assert columns/CHECKs.
2. **[Infrastructure]** `session_start_hook.py` (Phase-0 load half) — git/progress/coverage loader.
   - Subtasks: read `git status --porcelain`; read/create `claude-progress.txt`; read/stub `feature_list.json`; emit structured-JSON summary (`git_status`, `unproven_count`, `proven_count`); try/except → exit 0; unit tests for first-run + populated cases.
3. **[Infrastructure]** `pre_compact_hook.py` — checkpoint writer + baseline-hash producer.
   - Subtasks: checkpoint `claude-progress.txt` + evidence state + `feature_list.json` to MAIN-worktree git; write durable `run_state.resume_state_hash` over the checkpointed state; try/except → exit 0; unit + integration test (task-25.2 path).
4. **[API]** `tools/run_state_store.py` — `run_state` persistence with file-backed duplicate.
   - Subtasks: implement `load_run_state()` / `save_run_state(run_state)` upsert; write the `claude-progress.txt` duplicate including `resume_integrity_ok` + `resume_state_hash`; integration test that DB-down fallback reads the file duplicate and reaches the same decision (Note N-25).
5. **[Orchestration]** Per-slice commit trail wiring — one atomic commit per completed Slice.
   - Subtasks: ensure the Implementer's per-slice commit records `last_commit_sha` in `run_state`; integration test that a completed slice advances `last_commit_sha` and leaves a rollback point.

---

### REQ-12 — Observability (live requirement-tagged trace + gate-decision forwarding)

**Plane state:** Agent-Executing → In-Verification (live trace) · Done
**agent_role:** human (operator) · **requirement_id:** REQ-OBS-001 · **coverage_type:** functional
**Baseline block:** B11 · **Maps to:** reconciled Requirement 12 (criteria 12.1–12.5), Property 12, tasks 34 / 35 / 36 / 37
**Labels:** `human:review`, `type:functional`, `gate:stop`, `phase:3`, `priority:normal`

#### EARS

- **Ubiquitous:** The system shall emit OTel spans for every model call, tool invocation, and subagent task. *(12.1)*
- **Ubiquitous:** The system shall propagate the active `requirement.id` to all child spans via a W3C Baggage span processor. *(12.4)*
- **State-Driven:** WHILE a run is in progress, the system shall stream each span to the observability backend as it closes (export interval DEFAULT ≤ 5 seconds), not batched at run-end. *(12.2)*
- **Event-Driven:** WHEN a hook makes a gate decision, the system shall emit that decision — event, tool, allow/block, reason, requirement ID, actor_agent — to the same trace endpoint as agent spans. *(12.3)*
- **Optional:** WHERE a managed observability backend is used, the system shall document its license (Langfuse MIT core; SigNoz MIT Expat core; Arize Phoenix Elastic License 2.0) so backend choice is compliance-aware. *(12.5)*

#### Acceptance criteria

- `tools/telemetry.py::init_tracer(service)` configures the OTLP exporter with `CLAUDE_CODE_ENABLE_TELEMETRY=1` and `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`; the `opentelemetry-sdk` and GenAI semconv package versions are pinned in `requirements.txt` (experimental conventions treated as unstable).
- Span export uses a streaming/short-interval processor with export interval ≤ 5 s (not a run-end batch).
- The three gate-making hooks (Stop, PreToolUse, SubagentStop) emit a `"hook.decision"` span carrying `hook.event`, `tool.name`, `decision` (allow/block), `reason`, `requirement.id`, and `actor_agent` — the same `actor_agent` recorded in the `gate_audit_log` row, so the live span and durable audit row carry identical per-agent attribution.
- The two non-gating hooks (SessionStart, PreCompact) emit a distinct informational span (`"hook.session_start"` / `"hook.checkpoint"`, `decision="n/a"`), never a gate-decision allow/block attribute, so the trace schema reflects which hooks actually gate.
- `RequirementBaggageProcessor` propagates `requirement.id` to every child span (shared with REQ-6.4; Property 12).
- Langfuse is the default backend (OTLP endpoint `https://cloud.langfuse.com/api/public/otel/v1/traces`); backend license documentation is present.

#### Agent state-flow

From the moment the Initializer compiles the spec through every Implementer/Verifier slice, OTel spans stream to Langfuse with `requirement.id` Baggage — the operator watches the run live (Agent-Executing → In-Verification). Each Stop/PreToolUse/SubagentStop decision surfaces as a `hook.decision` span: a block (exit 2) appears with `decision=block` and the blocking `reason`, mirroring the item moving to **Blocked**/**HANDOFF**; an allow appears with `decision=allow`. The operator audits mid-flight without halting the run (observability informs, never gates). The same trace endpoint receives both agent spans and gate decisions, so "what the agent is doing" and "every gate decision" are one continuous trace.

#### Tasks

1. **[Infrastructure]** OTel setup + OTLP exporter — `tools/telemetry.py` init.
   - Subtasks: configure `CLAUDE_CODE_ENABLE_TELEMETRY=1` + `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` in `.env.example`/CI; pin `opentelemetry-sdk` + GenAI semconv in `requirements.txt`; implement `init_tracer(service)` with a ≤5s-interval streaming exporter; unit tests for span emission + export interval.
2. **[API]** `RequirementBaggageProcessor` — `requirement.id` propagation (shared with REQ-6).
   - Subtasks: implement `on_start` Baggage set; assert non-empty for active-requirement spans; Property-12 PBT.
3. **[Orchestration]** Hook decision forwarding — extend all six hooks to emit OTel events.
   - Subtasks: gate-making hooks (Stop/PreToolUse/SubagentStop) emit `"hook.decision"` with `hook.event`/`tool.name`/`decision`/`reason`/`requirement.id`/`actor_agent`; non-gating hooks (SessionStart/PreCompact) emit informational spans with `decision="n/a"`; integration test asserting a simulated Stop block emits a `decision=block` span with the active `requirement.id`.
4. **[Infrastructure]** Langfuse backend connection + license docs.
   - Subtasks: add commented `OTLP_ENDPOINT` example in `.env.example`; document Langfuse MIT / SigNoz MIT-Expat / Phoenix EL2 licenses; integration test asserting the collector receives a span with the Baggage attribute present.

---

### REQ-27 — Tamper-Evident Gate-Decision Audit Log (hash-chained)

**Plane state:** Human-Review (merge gate) → Done · Blocked on chain break
**agent_role:** human (operator) · **requirement_id:** REQ-AUDIT-001 · **coverage_type:** functional
**Baseline block:** B09/B11 · **Maps to:** reconciled Requirement 27 (criteria 27.1–27.8), Property 28, Postgres `gate_audit_log`, tasks 28.8 / 52 / 40.3
**Labels:** `human:review`, `type:functional`, `gate:completion`, `gate:ci`, `phase:2`, `phase:3`, `priority:high`

#### EARS

- **Ubiquitous:** The system shall append every gate decision (event, tool, allow/block, reason, requirement ID, actor agent, `created_at`) to an append-only, hash-chained audit log where each entry stores the hash of the prior entry. *(27.1)*
- **Ubiquitous:** The system shall retain the hash-chained gate-decision log as the execution-proof complement to SLSA build provenance, so "we can prove what happened" is distinct from and additional to "the trace says what happened." *(27.3)*
- **Event-Driven:** WHEN the audit log is verified, IF any entry's stored prior-hash does not equal the recomputed hash of the preceding entry, THEN verification shall fail (tamper detection). *(27.2)*
- **State-Driven:** WHILE operating without archival, the system shall treat unbounded append-only retention as the accepted DEFAULT and prohibit mid-chain pruning; verified prefixes older than the live window (DEFAULT 365 days) shall be checkpoint-and-archived so the chain re-verifies across the archive boundary. *(27.7)*
- **Unwanted:** IF two concurrent `append()` calls read the same `prev_hash`, THEN the system shall serialize the read+insert under a lock within one transaction so the chain linearizes and `audit_verify` does not raise a false fork. *(implements 27.4/27.5 linearization)*

#### Acceptance criteria

- `db/migrations/008_gate_audit_log.sql` creates the append-only `gate_audit_log` table (`seq` monotonic, `event_name`, `tool_name`, `decision`, `reason`, `requirement_id`, `actor_agent`, `created_at`, `prev_hash`, `entry_hash`) and DB-enforces append-only: `REVOKE UPDATE, DELETE ... FROM <app_role>` plus a `BEFORE UPDATE OR DELETE` trigger that RAISEs.
- `tools/audit_log.py::append(event, tool, decision, reason, requirement_id, actor_agent)` is the sole producer; `created_at` is DB-assigned (`DEFAULT now()`) and folded into the canonical row, not a producer argument. Genesis entry uses `prev_hash = sha256("")`; canonical form = deterministic JSON of `(seq, event_name, tool_name, decision, reason, requirement_id, actor_agent, created_at)`; `entry_hash = sha256(canonical_row || prev_hash)` and INCLUDES `seq` and `created_at`.
- `append()` is CALLED by `stop_hook.py`, `pre_tool_use_hook.py`, and `subagent_stop_hook.py` (covering the evidence-schema decision AND the omission-declaration-guard decision) on EVERY allow/block decision — three hook files, four decision points. The kill-switch toggle (REQ-CTRL-001) also appends.
- `append()` serializes the prev_hash-read + insert under `pg_advisory_xact_lock` (or `SELECT ... FOR UPDATE` on a chain-head sentinel) within one transaction; concurrent appends from distinct hook processes cannot fork the chain.
- `tools/audit_verify.py` recomputes the chain, fails on any broken link, and emits a structured JSON report (`first_broken_seq`, `expected_hash`, `stored_prev_hash`, `computed_prev_hash`) in addition to the non-zero exit; it verifies a merged DB+file-backed chain (Note N-25), ordering by `seq` and chaining the file segment's first `prev_hash` to the DB segment's last `entry_hash`. Property 28.
- The `.github/workflows/audit-chain-verify.yml` REQUIRED status check runs `audit_verify.py` at merge; on-demand invocation is also supported. Registration is gated until `audit_verify.py` (52.2) and the producer wiring (52.3) land (build-order inversion fix).
- The append call is invoked inside the decision path BEFORE the exit, wrapped so an append failure degrades to the file-backed log and never suppresses the gate decision/exit.
- CI-status-check gates (`deepeval-gate`, `zap-baseline`, `coverage-gate`, `secrets-scan`, `audit-chain-verify` itself) are recorded via GitHub check-run history + SLSA, not the hook hash chain — so each gate is captured by exactly one execution-proof substrate.

#### Agent state-flow

Every hook gate decision across the run appends a hash-chained `gate_audit_log` row — a block (item to **Blocked**/**HANDOFF**) and an allow (item toward **Done**) are both recorded with their `reason` and `actor_agent`. At merge (item in **Human-Review**), the `audit-chain-verify` required check recomputes the entire chain: an intact chain (genesis `prev_hash = sha256("")` through the tip) permits **Done**; any broken link (a tampered or reordered row) fails verification, blocks the merge (item to **Blocked**, `gate=ci`, label `blocked`), and emits the structured break report. The append-only DB enforcement + linearization lock guarantee the chain is the durable, immutable proof complement to SLSA provenance.

#### Tasks

1. **[Infrastructure]** Migration `008_gate_audit_log.sql` — append-only hash-chained table.
   - Subtasks: create the table with the full column set; emit `REVOKE UPDATE, DELETE` + `BEFORE UPDATE OR DELETE` RAISE trigger; document the genesis sentinel `prev_hash = sha256("")` and `entry_hash` canonical form; specify the DB-down `seq` reconciliation rule (client-generated monotonic seq OR recompute-and-re-chain on reconnect); migration smoke test asserting append-only enforcement.
2. **[API]** Audit-log producer `tools/audit_log.py` — `append(...)` with chain linearization.
   - Subtasks: implement `append(event, tool, decision, reason, requirement_id, actor_agent)` computing `entry_hash` over the canonical tuple; serialize prev_hash-read + insert under `pg_advisory_xact_lock` in one transaction; file-backed fallback on DB-down (Note N-25); write-side unit tests (genesis hash, determinism, round-trip).
3. **[API]** Audit-chain verifier `tools/audit_verify.py` — recompute + tamper report.
   - Subtasks: recompute the chain and fail on any broken link; merged DB+file-backed chain verification with the seam rule; structured JSON break report; Property-28 PBT `test_audit_verify.py` (broken-link fail + intact-chain producer-contract reproduction including `seq`/`created_at` in the hash).
4. **[Orchestration]** Wire producer into the three hooks — `52.3` producer wiring.
   - Subtasks: modify `stop_hook.py`, `pre_tool_use_hook.py`, `subagent_stop_hook.py` to call `audit_log.append(...)` on every allow/block decision, invoked BEFORE the exit and wrapped to fall back to the file-backed log; unit test that an `append` raise still records to the file log and exits with the correct code.
5. **[Orchestration]** `audit-chain-verify` REQUIRED CI check — `.github/workflows/audit-chain-verify.yml`.
   - Subtasks: create the workflow running `audit_verify.py`; SPLIT the registration leg so the required/merge-blocking registration is gated until 52.2/52.3 land; register in the GitHub ruleset (canonical list in `docs/github-ruleset.md`).
6. **[Orchestration]** Retention & archival policy — live window + cross-boundary re-verification.
   - Subtasks: implement the 365-day live-window checkpoint-and-archive of verified prefixes (export contiguous verified prefix to write-once cold storage, record its tip `entry_hash`); ensure the next live entry's `prev_hash` equals the archived tip so `audit_verify` re-verifies across the boundary; prohibit mid-chain pruning; document the v1 unbounded-retention default.

---

### REQ-23 — Resumed-State Integrity

**Plane state:** Agent-Executing (first write of a resumed session) · Blocked on mismatch
**agent_role:** human (operator) · **requirement_id:** REQ-STATE-005 · **coverage_type:** functional
**Baseline block:** B10 · **Maps to:** reconciled Requirement 23 (criteria 23.1–23.2), Property 26, Z3 CHECK-11a/11b, `tools/state_integrity.py`, tasks 49 / 49.1 / 49.2
**Labels:** `human:review`, `type:functional`, `gate:pretooluse`, `phase:2`, `priority:blocking`

#### EARS

- **Event-Driven:** WHEN a session resumes, the SessionStart_Hook shall compute the resumed-state hash and write `run_state.resume_integrity_ok` (bool) without itself blocking. *(23.2, compute half)*
- **Unwanted:** IF a session resumes AND the resumed-state hash does not match the durable store's recorded `resume_state_hash`, THEN the system shall block the run from proceeding (PreToolUse integrity guard, exit 2 on the first implementation write) and require operator reconciliation. *(23.1 / 23.2 enforcement half)*
- **State-Driven:** WHILE `run_state.resume_integrity_ok` is `false`, the PreToolUse integrity guard shall block the session's first `Write`/`Edit`/`MultiEdit`, releasing only after operator reconciliation flips it true. *(23.2)*
- **Optional:** WHERE a session has no recorded baseline (`resume_state_hash IS NULL`, a fresh non-resumed run), the system shall treat the integrity guard as ALLOW so a first run is never blocked. *(first-run carve-out)*

#### Acceptance criteria

- `tools/state_integrity.py::compute_hash()` recomputes the resumed-state hash as `sha256` over the canonical projection of in-scope `feature_list.json` items + the named `run_state` fields (the spec at Property 26), using the same hash-algorithm/canonical-form as the design hash layer.
- `session_start_hook.py` (Phase-2 extension, task 49.2) imports `state_integrity.py`, calls `compute_hash()`, compares against the durable `run_state.resume_state_hash`, and writes `run_state.resume_integrity_ok` — remaining NON-BLOCKING (exit 0 always).
- The PreToolUse integrity guard (task 49.1) reads `run_state.resume_integrity_ok` and exits 2 when `false`; it is scoped to `(run_state.is_resume AND NOT run_state.first_write_done)` so it fires only on the first implementation write of a resumed session, and treats `resume_state_hash IS NULL` as ALLOW.
- The integrity guard is chained BEFORE the plan/scope/artifact/status checks in `pre_tool_use_hook.py` (order pinned at task 6.1).
- Operator Reconciliation re-records the baseline and flips `resume_integrity_ok` to `true`, releasing the guard.
- On DB-down at SessionStart, the hook records `resume_integrity_ok` + baseline `state_hash` to the file-backed `claude-progress.txt` duplicate so the guard always has a file-backed source (Note N-25, never fail-open).
- Verified by Property 26 (PBT, task 39.16) and the LOGIC abstraction Z3 CHECK-11a (mismatch ⇒ ¬proceeds, UNSAT) / CHECK-11b (SAT).

#### Agent state-flow

A resumed session enters SessionStart (`is_resume=true`): the hook recomputes the state hash and writes `resume_integrity_ok` — non-blocking, so the session loads. On the first `Write`/`Edit` (still **Agent-Executing**), the PreToolUse integrity guard fires: a clean match (`resume_integrity_ok=true`) sets `first_write_done` and lets the slice proceed; a mismatch (`false`) blocks with exit 2, moving the item to **Blocked** (`gate=pretooluse`, label `blocked`, `priority:blocking`) and surfacing a reconciliation prompt to the operator. After Operator Reconciliation re-records the baseline and flips the flag true, the guard releases and the slice resumes. A fresh non-resumed run (`resume_state_hash IS NULL`) is never blocked.

#### Tasks

1. **[Infrastructure]** `tools/state_integrity.py` — resumed-state hash computation.
   - Subtasks: implement `compute_hash()` over the canonical projection of in-scope `feature_list.json` items + named `run_state` fields; document the canonical-form spec (matching Property 26); add the `resume_state_hash`/`is_resume`/`first_write_done`/`resume_integrity_ok` columns via `005_run_state.sql`.
2. **[API]** SessionStart compute/write extension — task 49.2.
   - Subtasks: extend `session_start_hook.py` to import `state_integrity.py`, call `compute_hash()`, compare to durable `resume_state_hash`, write `resume_integrity_ok`; remain exit 0; DB-down → write the flag+hash to `claude-progress.txt`; add the resume-write assertion to the SessionStart unit tests (task 7.2).
3. **[Orchestration]** PreTooLUse integrity guard — task 49.1 enforcement point.
   - Subtasks: add `check_resume_integrity(event)` reading `run_state.resume_integrity_ok`, blocking the first resumed-session write (exit 2) when false, scoped on `(is_resume AND NOT first_write_done)`, NULL-baseline → allow; chain it first in the PreToolUse guard order; set `first_write_done` on pass; Property-26 PBT (task 39.16) asserting block-on-mismatch + the Operator-Reconciliation release path.

---

### REQ-16 — Durable Storage (single source of truth)

**Plane state:** cross-cutting (durable substrate for all states) · Done
**agent_role:** human (operator) · **requirement_id:** REQ-STORE-001 · **coverage_type:** functional
**Baseline block:** B15 · **Maps to:** reconciled Requirement 16 (criteria 16.1–16.3), Property 19, the eight-table Postgres store, tasks 28 / 30 / 33
**Labels:** `human:review`, `type:functional`, `gate:completion`, `phase:2`, `priority:high`

#### EARS

- **Ubiquitous:** The system shall persist requirements, coverage state, traceability links, Evidence_Records, and run state in a managed Postgres database (Neon, eight tables, migrations 001–008). *(16.1)*
- **Ubiquitous:** The system shall keep the Postgres store as the single source of truth for coverage queries, reconstructable independently of any model session. *(16.3)*
- **Event-Driven:** WHEN evidence is captured, the system shall store the artifact or a content-addressed reference and link it to the requirement ID and commit SHA. *(16.2)*

#### Acceptance criteria

- Eight migrations (`001`–`008`) apply in numeric order on a test Neon branch, creating `requirements`, `coverage_items`, `traceability_links`, `evidence_records`, `run_state`, `domain_baseline_checklists`, `requirement_versions`, `gate_audit_log`; the runtime `app_role` is granted only the privileges each gate needs (no `UPDATE`/`DELETE` on `gate_audit_log`).
- `evidence_records` enforces the four-field `evidence_complete` CHECK (`test_file <> '' AND test_name <> '' AND output_hash <> '' AND collected_at IS NOT NULL`) AND the `output_hash ~ '^sha256:[a-f0-9]{64}$'` format CHECK (closing the DB/JSON enforcement asymmetry); `actor_agent` is `NOT NULL` (MUST be the Verifier, never the Implementer — Property 24).
- `evidence_collector.py::store_to_postgres` inserts the Evidence_Record linked to `requirement_id` and `commit_sha`; a `UNIQUE (requirement_id, commit_sha, test_name)` constraint (or index on `(requirement_id, commit_sha)`) rejects duplicate evidence rows so the Property-22 OPA COUNT is not inflated. The Phase-2 portion of Property 19 (store → retrieve by `requirement_id`+`commit_sha` with all four fields intact) passes (REQ-16.2).
- The raw evidence artifact is retained as a content-addressed blob keyed by `output_hash`, with the four-field record holding only the `sha256:` reference (satisfying "artifact OR content-addressed reference"); hash-only retention is permitted only in DB-down fallback and flagged as degraded.
- Required indexes exist: `idx_evidence_records_requirement_id`, `idx_traceability_links_requirement_id`, `idx_coverage_items_requirement_id`.
- The file-canonical / DB-mirror split is honored: `feature_list.json` is canonical for `acceptance_criteria`/`dependencies`/`priority`; Postgres mirrors only the coverage-status subset needed for the traceability graph and OPA/evidence queries — coverage queries are reconstructable from Postgres alone (16.3).

#### Agent state-flow

As the Verifier proves each slice (**In-Verification**), `evidence_collector.py` writes the four-field Evidence_Record to `evidence_records` (linked to `requirement_id` + `commit_sha`) and the blob to content-addressed storage; `coverage_items.status` flips to `proven`. The durable store is the substrate every gate reads: the Stop hook counts in-scope `unproven` items, the OPA merge policy runs the zero-evidence query, and orphan detection reads `traceability_links`/`evidence_records` — all reconstructable without a model session. At merge (**Human-Review** → **Done**), the store proves coverage independently; on DB-down the file/git duplicates carry the conservative decision (Note N-25).

#### Tasks

1. **[Infrastructure]** Migrations `001`/`002`/`004` — requirements, coverage_items, evidence_records.
   - Subtasks: write `001_requirements.sql` (identity/EARS/provenance, `type`/`nfr_subtype`/`provenance` CHECKs); `002_coverage_items.sql` (`status`/`subtype` CHECKs, `in_scope DEFAULT TRUE` + the human-authored-flip trigger); `004_evidence_records.sql` (four-field `evidence_complete` CHECK + `output_hash` format CHECK + `actor_agent NOT NULL` + the `UNIQUE (requirement_id, commit_sha, test_name)` constraint); add the three required indexes.
2. **[Infrastructure]** Migration runner + eight-table integration test.
   - Subtasks: run all eight migrations (001–008) on a test Neon branch; assert all eight tables + CHECKs; assert `evidence_complete` rejects an incomplete record and `coverage_items.in_scope` defaults true; assert `app_role` lacks UPDATE/DELETE on `gate_audit_log`.
3. **[API]** `evidence_collector.py` → `evidence_records` storage integration.
   - Subtasks: implement `store_to_postgres(record, requirement_id, commit_sha)`; store the content-addressed blob keyed by `output_hash` with the record holding only the `sha256:` reference; degraded-evidence flag on hash-only DB-down fallback; Property-19 Phase-2 round-trip test (retrieve by `requirement_id`+`commit_sha`, all four fields intact).
4. **[Orchestration]** Phase-2 durable-state integration test — full store reconstructability.
   - Subtasks: against a test Neon branch, insert a complete evidence record and assert retrieval by `requirement_id`+`commit_sha`; assert coverage queries are answerable from Postgres alone (16.3); assert the file-canonical/DB-mirror split (acceptance_criteria/dependencies/priority canonical in `feature_list.json`).


# Epic E8 — Orchestration, Anti-Loopmaxxing & Human-in-the-Loop

**Plane project:** Agentic SDLC Control Plane (`ASCP`)
**Baseline blocks covered:** B12 (mid-flight steering), B13 (anti-loopmaxxing), B14 (orchestration), B17 (HITL), B18 (predictive routing, optional), B11 (reasoning-loop detection), B19 (omission/checklist epistemics), plus the cross-cutting NFR threshold registry.
**Assigned requirements:** REQ-13, 14, 15, 18, 19, 20, 21, 24, 26, 29 (the canonical `.kiro/specs/spec-to-evidence-control` Requirements 13, 14, 15, 18, 19, 20, 21, 24, 26, 29).

## Overview

E8 is the **steering and termination layer** of the control plane: the deterministic machinery that decides *when an agent may stop, when it must be handed to a human, and what a human must approve before code is written*. It is the single most load-bearing epic for the governing invariant — *deterministic gates (Claude Code hooks, CI, OPA) decide completion solely from verifiable facts; model self-assessment and predictions only inform, they never gate.*

Three guarantees anchor the epic:

1. **Hooks are the sole mid-flight intervention layer** (REQ-13). Not prompts, not `CLAUDE.md`. The `PreToolUse` hook is the only true prevention gate (exit 2 blocks before execution); `PostToolUse` is a next-turn forcing function that cannot undo. Command-type hooks fail closed; HTTP/MCP hooks (which fail open) are barred from hard policy.
2. **Runaway loops are impossible** (REQ-14, 21, 20). A hard iteration cap (25 turns/Slice), a token/cost budget (1,000,000 tokens/Slice), a retry budget (3/Slice), and a no-progress predicate each route to **HANDOFF — a terminal state distinct from `Done`** — and `evaluate_stop` evaluates HANDOFF triggers *before* the unproven-items block so the agent is never force-continued past its cap (the infinite-block defect that the canonical reconciliation explicitly fixed). HANDOFF **allows** termination (exit 0); only the unproven-items condition blocks (exit 2).
3. **A human gates the plan and the merge** (REQ-18). No implementation `Write`/`Edit` runs without a `plan-approved.json` marker whose `feature_list_sha` binds it to the exact coverage model; a required reviewer gates the merge to the protected branch.

Around these sit the inner-loop orchestrator (REQ-15: Claude Code subagents+hooks, Temporal/Inngest only when crash-safety is truly needed), the optional off-gate predictive router (REQ-19), the reasoning-loop detector (REQ-26: ≥ K=3 identical tool-call signatures on a `claude.span.kind="reasoning"` INTERNAL span), the checklist-approval + research-epistemic gate (REQ-24), and the structured omission-declaration gate (REQ-29: SubagentStop rejects any result whose `omission_declaration` is null/absent, exit 2). REQ-20 is the cross-cutting threshold registry that owns every numeric DEFAULT the others key on.

**State-flow.** Issues in this epic ride the canonical state machine. The HITL plan gate flips an issue from `Spec-Verified` → `Plan-Approved`. The implementer loop runs in `Agent-Executing`; verification in `In-Verification`; PR review in `Human-Review` → `Done`. Any cap/budget/no-progress event terminates to **`HANDOFF`** (cancelled group); any gate exit-2 block (unproven dependency, failed integrity/approval, unapproved checklist, missing omission declaration) lands in **`Blocked`** (cancelled group). `HANDOFF` and `Done` are mutually exclusive — a HANDOFF run is never `Done`.

---

## REQ-13 — Mid-Flight Steering (Baseline B12)

**Maps to:** canonical Requirement 13 (REQ-STEER-001..006), design Hook Wiring Table + Property 21 (exit-code contract) + Property 4 (prediction independence, criterion 13.6).
**State / role:** `Agent-Executing` · `agent_role = human` (platform owner authoring the gate layer) · `requirement_id = REQ-STEER-001` · `coverage_type = WIRING` (the hook layer is an architectural connection obligation) · labels: `gate:pretooluse`, `gate:stop`, `phase:0`, `type:wiring`, `priority:blocking`.

### EARS

- **Ubiquitous:** THE system shall treat Claude Code hooks — not prompts and not `CLAUDE.md` — as the sole deterministic mid-flight intervention layer.
- **Ubiquitous:** THE system shall use the `PreToolUse_Hook` as the only true prevention gate (exit 2 / deny blocks before execution) and shall treat the `PostToolUse_Hook` as a next-turn forcing function that cannot undo an already-executed action.
- **Event-Driven:** WHEN a tool call targets a protected artifact (`tests/`, coverage-model schema, CI config) or a destructive operation (`rm -rf`, `DROP TABLE`), the system shall block it at the `PreToolUse_Hook` command-type hook.
- **State-Driven:** WHILE enforcing hard policy, the system shall use command-type hooks (which fail closed) and shall not use HTTP or MCP hooks (which fail open).
- **Unwanted:** IF a gate decision would read a probabilistic prediction, THEN the system shall reject that design — gate outcomes shall depend only on verifiable facts (Z3 CHECK-5: a differing prediction cannot produce a differing gate decision).
- **Ubiquitous (exit-code contract):** THE system shall honor the hook exit-code contract — exit 0 = proceed, exit 2 = blocking error fed to the model via stderr, any non-zero other than 2 = non-blocking (exit 1 does NOT block).

### Acceptance criteria

1. `settings.json` registers all six hooks (`Stop`, `PreToolUse`, `PostToolUse`, `SubagentStop`, `SessionStart`, `PreCompact`) as `type: "command"`; the `tests/smoke/test_hook_config.py` smoke test asserts none are HTTP/MCP and that the four subagents are discoverable.
2. The `PreToolUse` artifact guard blocks any write to `feature_list.json` schema, `tests/` (except `actor_agent == verifier.md`), CI config, or any destructive Bash op, and emits exit 2.
3. A hook returning exit 1 never blocks; exit 2 blocks and routes stderr to the agent; exit 0 proceeds (Property 21 PBT passes ≥ 100 examples).
4. No gate decision reads a prediction variable: two evaluations with identical coverage state but different predicted outputs yield identical decisions (Property 4 / CHECK-5).

### Agent state-flow

Platform owner authors the hook layer in `Agent-Executing`; the layer itself does not flip a coverage item to `Done` — it is verified by the `tests/smoke/test_hook_config.py` + `tests/property/test_hooks.py` evidence, after which its WIRING coverage item moves `In-Verification` → `Done` with an integration-test Evidence_Record (the hook layer is a WIRING obligation, so its `evidence_kind` must be `integration`).

### Tasks

- **[Infrastructure] Author `.claude/settings.json` six-hook command registration** (tasks.md task 9.1)
  - Register `Stop`, `PreToolUse`, `PostToolUse` (matcher `Write|Edit|MultiEdit`), `SubagentStop`, `SessionStart`, `PreCompact` as `type: "command"`.
  - Confirm the four `.claude/agents/*.md` subagents auto-discover by frontmatter `name` (no explicit registration row).
  - Write `tests/smoke/test_hook_config.py`: assert every hook is command-type (not HTTP/MCP) and assert `initializer`/`implementer`/`verifier`/`research` are discoverable.
- **[Orchestration] Implement `pre_tool_use_hook.py` artifact + status guards** (tasks.md task 6.1)
  - `check_artifact_guard`: block writes to `feature_list.json` schema, `tests/` (carve-out keyed on `actor_agent == verifier.md`), CI config, destructive Bash; exit 2.
  - `check_status_transition` + `check_append_only`: permit only `{unproven→proven (+complete Evidence_Record), unproven→failed, failed→unproven, proven→unproven (amendment-gated only)}`; diff incoming `items[]` id-sequence/length against the prior committed `feature_list.json` and block any deletion/truncation/reorder.
  - Honor the exit-code contract: try/except wrapper exits 2 on unhandled exception (fail closed).
- **[API] Configure the GitHub repository ruleset as the merge-side complement** (tasks.md task 14.2)
  - Register required status checks so destructive merges cannot bypass the hook layer; document the canonical required-check list in `docs/github-ruleset.md`.
- **[Orchestration] Author `tests/property/test_hooks.py` exit-code + prediction-independence properties** (tasks.md tasks 39.3, 39.* for Property 21 / Property 4)
  - Property 21: exit 0 proceeds, exit 2 blocks with stderr fed back, exit 1 non-blocking — ≥ 100 Hypothesis examples.
  - Property 4: identical coverage state with differing prediction variables → identical gate decision (mirrors CHECK-5).

---

## REQ-14 — Anti-Loopmaxxing Controls (Baseline B13)

**Maps to:** canonical Requirement 14 (REQ-LOOP-001..004), design `evaluate_stop` + Anti-Loopmaxxing Circuit Breakers + run_state DDL (`iteration_count`, `token_cost_usd`, `no_progress_n`, `retry_count`), Z3 CHECK-3/8a/8b.
**State / role:** `Agent-Executing` → terminal `HANDOFF` · `agent_role = implementer` (owner of the retry + per-slice budget) · `requirement_id = REQ-LOOP-001` · `coverage_type = functional` · `run_state` field at HANDOFF = `handoff` · labels: `gate:stop`, `handoff`, `phase:0`, `type:functional`, `priority:blocking`.

### EARS

- **State-Driven:** WHILE a control loop runs, THE system shall enforce a hard iteration cap (DEFAULT = 25 turns per Slice) and a token/cost budget per Slice (DEFAULT = 1,000,000 tokens).
- **Unwanted:** IF the iteration cap OR the cost budget OR the no-progress condition is reached, THEN the system shall terminate the run to `HANDOFF` — a terminal state distinct from `Done` — and shall NOT mark the deliverable `Done` (Z3 CHECK-3).
- **Unwanted:** IF a Slice exhausts its retry budget (DEFAULT = 3 retries), THEN the system shall fail gracefully and hand off to a human rather than retrying indefinitely (REQ-LOOP-003).
- **Ubiquitous:** THE system shall trace-log agent reasoning and tool calls and retain human-readable evidence so a human can audit why the agent acted, bounding comprehension debt.

> **No-progress operationalization (canonical):** zero coverage items flipped `unproven → proven` AND zero commits produced, both true simultaneously across the last N consecutive Slices (DEFAULT N = 3) — `check_no_progress(run_state, feature_list)` (Z3 CHECK-8a/8b).

### Acceptance criteria

1. `iteration_count >= MAX_TURNS_PER_SLICE` (25) in the `implementation` phase routes to HANDOFF via `evaluate_stop`, setting `run_state.status = "handoff"` and emitting a HANDOFF summary (remaining unproven items, last N slice outputs, reason).
2. `token_cost_usd >= TOKEN_BUDGET` (1,000,000, a computed predicate — no stored `budget_exceeded` column) routes to HANDOFF.
3. `check_no_progress` (zero proven + zero commits across N=3 slices) routes to HANDOFF and lists the still-unproven item IDs.
4. `retry_count >= 3` on a slice routes to HANDOFF (REQ-LOOP-003), owned by the implementer loop.
5. On HANDOFF, `feature_list.json` is NOT modified (items remain `unproven`) and the run is not auto-retried — requires explicit operator restart.

### Agent state-flow

The implementer in `Agent-Executing` increments `run_state.iteration_count`, `token_cost_usd`, and `retry_count` per turn/slice. When any cap/budget/no-progress predicate trips, the `Stop` hook (`evaluate_stop`) writes `run_state.status = "handoff"`, emits the HANDOFF summary, and **allows** termination → the issue moves to `HANDOFF` (cancelled group, distinct from `Done`). A human picks it up; nothing auto-resumes.

### Tasks

- **[Orchestration] Implement HANDOFF triggers in `evaluate_stop` (`stop_hook.py`)** (tasks.md task 5.1)
  - Phase-discriminate the cap on `run_state.phase`: `spec` → `SPEC_COMPLETION_HARD_CAP=7` keyed on `spec_pass_count`; `implementation` → `MAX_TURNS_PER_SLICE=25` keyed on `iteration_count`.
  - Evaluate HANDOFF triggers (cap → budget → no-progress) BEFORE the unproven-items block; each returns `allow()` (exit 0) after writing `status="handoff"` and emitting `emit_handoff_summary(...)`.
  - Compute `budget_exceeded := token_cost_usd >= TOKEN_BUDGET` (config constant, not a column).
  - Implement `check_no_progress`: zero `unproven→proven` flips AND zero commits across `N_PROGRESS_WINDOW = 3` slices.
- **[Orchestration] Own the retry + per-slice token budget in `implementer.md`** (tasks.md task 10.2)
  - Increment `run_state.retry_count` on a failed slice; at `retry_count >= 3` stop and route to HANDOFF (REQ-LOOP-003).
  - Enforce the per-slice token/cost budget (REQ-LOOP-001) and its REQ-LOOP-002 HANDOFF trigger for the slice the loop owns.
- **[Infrastructure] Migrate the `run_state` counters** (tasks.md task 28.5, migration `005_run_state.sql`)
  - Add `iteration_count`, `spec_pass_count`, `token_cost_usd`, `no_progress_n`, `retry_count`, `prev_violation_count`, `status CHECK IN ('running','complete','handoff','blocked')`, `phase CHECK IN ('spec','implementation')`.
- **[API] Mirror HANDOFF onto the Plane issue via webhook** (Plane Webhooks/REST)
  - On `run_state.status = "handoff"`, transition the linked Plane issue to the `HANDOFF` state (cancelled group), set `run_state = handoff`, add the `handoff` label, and post the HANDOFF summary as an issue comment.
- **[Orchestration] Author HANDOFF/no-progress property + unit tests** (tasks.md tasks 39.3, 5.5)
  - PBT: cap/budget/no-progress each yield `allow()` (HANDOFF), never a block; reentrancy guard does not cascade.
  - Unit: `check_no_progress` boundary at N=3; HANDOFF summary contents.

---

## REQ-15 — Orchestration (Baseline B14)

**Maps to:** canonical Requirement 15 (REQ-ORCH-001..003), design Core Execution Loop + Component Inventory (four subagents), tasks.md task 43 (+ 43.1 optional Temporal/Inngest).
**State / role:** `Agent-Executing` · `agent_role = human` (architect wiring the inner loop) · `requirement_id = REQ-ORCH-001` · `coverage_type = WIRING` · labels: `agent:initializer`, `agent:coder`, `agent:tester`, `phase:0`, `type:wiring`, `priority:high`.

### EARS

- **Ubiquitous:** THE system shall use Claude Code subagents and hooks as the inner planner/implementer/verifier orchestrator and shall NOT introduce an external agent-reasoning framework for the inner loop by default.
- **Optional:** WHERE crash-safe multi-hour or multi-day runs are required, the system shall wrap the loop in Temporal/Inngest invoking `claude -p` as a durable step, with each tool call as a separate activity.
- **State-Driven:** WHILE Agent_Teams (experimental peer-to-peer) remains experimental, the system shall keep it off the delivery-gating path until the feature exits experimental status and supports session resumption.

### Acceptance criteria

1. The inner loop is driven solely by `.claude/agents/{initializer,implementer,verifier,research}.md` + the six hooks — no external reasoning framework is on the default delivery path.
2. The optional Temporal/Inngest durable outer loop is behind a flag (Phase 5), invoking `claude -p` as a durable step with each tool call as a separate activity; it is OFF by default.
3. Agent_Teams is absent from the delivery-gating path; CI/grep gate asserts no Agent_Teams primitive is wired into a gate decision.

### Agent state-flow

The architect wires the subagent/hook inner loop in `Agent-Executing`. Each subagent advances the canonical flow: `initializer` (`Spec-Compiling` → `Spec-Verified`), human (`Plan-Approved`), `implementer` (`Agent-Executing`), `verifier` (`In-Verification` → `Done`/`Failed`). The orchestration WIRING item is proven `In-Verification` → `Done` via the integration test that exercises one full intent→evidence pass.

### Tasks

- **[Orchestration] Wire the subagent/hook inner loop** (tasks.md task 43)
  - Wire `initializer → (human plan approval) → implementer → verifier` driven by `PreToolUse`/`PostToolUse`/`Stop`/`SubagentStop`/`SessionStart`/`PreCompact`; assert no external agent-reasoning framework on the default path.
  - Author the integration test exercising one full slice loop end-to-end (initializer emits `feature_list.json` → implementer slice in a worktree → verifier captures evidence → Stop allows on all-proven).
- **[Orchestration] Optional Temporal/Inngest durable stub behind a flag** (tasks.md task 43.1, Phase 5)
  - `claude -p` as a durable step; each tool call a separate activity; OFF by default; only enabled when multi-hour crash pain is felt.
- **[Infrastructure] Keep Agent_Teams off the gating path** (CI/grep gate)
  - Add a grep gate asserting no Agent_Teams peer-to-peer primitive appears in any hook/gate decision path.
- **[API] Expose the inner-loop topology in Plane** (Plane Webhooks/REST)
  - On each subagent transition, drive the linked Plane issue through the canonical states via REST; stamp `agent_role`, `worktree_branch`, and `agent_run_id` (the traceability triple: issue ↔ branch ↔ run).

---

## REQ-18 — Human-in-the-Loop Approval (Baseline B17)

**Maps to:** canonical Requirement 18 (REQ-HITL-001..003), design `plan-approved.json` (SHA-bound) + PreToolUse plan gate + repository ruleset, Property 6 (validates 7.4/18.1/18.4).
**State / role:** `Spec-Verified` → `Plan-Approved` (plan gate); `In-Verification` → `Human-Review` → `Done` (PR gate) · `agent_role = human` · `requirement_id = REQ-HITL-001` · `coverage_type = functional` · labels: `human:review`, `gate:pretooluse`, `phase:0`, `type:functional`, `priority:blocking`.

### EARS

- **Unwanted:** IF no `plan-approved.json` approval marker exists, THEN the `PreToolUse_Hook` shall block all implementation `Write` and `Edit` tools (exit 2).
- **Event-Driven:** WHEN the validated spec and `feature_list.json` are ready, the system shall present them in plan mode for human approval and missing-context injection before unlocking implementation; the `plan-approved.json.notes` free-text field carries the human's missing-context injection, which the Initializer reads on the next session and injects into `run_state`.
- **Ubiquitous:** THE system shall require a human PR review (a required reviewer configured in a repository ruleset) before merge to the protected branch.
- **Unwanted:** IF `plan-approved.json` exists BUT its `feature_list_sha` does not equal the canonical SHA-256 of the current `feature_list.json`, THEN the `PreToolUse_Hook` shall block all implementation `Write`/`Edit`/`MultiEdit` tools and require re-approval.

### Acceptance criteria

1. With no `plan-approved.json`, every implementation `Write`/`Edit` is blocked at `PreToolUse` (CHECK-4f UNSAT: no code-write without approved plan).
2. The Initializer enters plan mode presenting the validated spec + `feature_list.json`; only the human writes `plan-approved.json` (the Initializer never does).
3. On the next session the Initializer reads `plan-approved.json.notes` and injects it into `run_state` for the Implementer's context.
4. A mutated `feature_list.json` (whose SHA ≠ the marker's `feature_list_sha`) re-blocks implementation until re-approval (Property 6).
5. The GitHub repository ruleset requires a human reviewer before merge to the protected branch (`tests/smoke/test_repo_ruleset.py` asserts it).

### Agent state-flow

`initializer` reaches `Spec-Verified` (violation_count == 0, `feature_list.json` all-unproven) and enters plan mode. The human writes `plan-approved.json` (SHA-bound) → issue flips `Spec-Verified` → `Plan-Approved`, unlocking the `PreToolUse` plan gate so the implementer may write in `Agent-Executing`. After verification (`In-Verification`), the PR opens and the issue moves to `Human-Review`; a required reviewer approves → `Done`. A SHA mismatch at any point re-blocks → `Blocked`.

### Tasks

- **[Orchestration] Implement the `PreToolUse` plan gate (`check_plan_approval`)** (tasks.md task 6.1)
  - Block all implementation `Write`/`Edit`/`MultiEdit` when `plan-approved.json` is absent (exit 2).
  - Block when `plan-approved.json.feature_list_sha` ≠ canonical SHA-256 of the current `feature_list.json` (require re-approval).
  - Handle missing/corrupt marker as fail-closed with an operator-facing re-run-Initializer message.
- **[Orchestration] Wire missing-context injection through the Initializer** (tasks.md task 10.1 / Initializer key behaviors)
  - On session start, read `plan-approved.json.notes` and inject into `run_state` so the Implementer's context receives the human's missing-context.
  - Ensure the Initializer enters plan mode and NEVER writes `plan-approved.json` itself.
- **[API] Configure the required-reviewer repository ruleset** (tasks.md task 14.2; Plane Webhooks/REST)
  - Configure a GitHub repository ruleset requiring a human reviewer on the protected branch; document in `docs/github-ruleset.md`.
  - On PR open, transition the Plane issue to `Human-Review` via REST; on reviewer approval + merge, transition to `Done`.
  - Write `tests/smoke/test_repo_ruleset.py` asserting the ruleset requires a reviewer.
- **[Infrastructure] Define and validate the `plan-approved.json` marker** (Phase-0 artifact)
  - Author the marker schema (`feature_list_sha`, `notes`); add the Z3 fixture for CHECK-4f (no code-write without approved plan) and the Property 6 PBT (SHA-bound re-block).

---

## REQ-19 — Predictive Routing (Optional) (Baseline B18)

**Maps to:** canonical Requirement 19 (REQ-PRED-001..003), design Phase 6 (optional, off-gate) + Property 4 (prediction independence) + CHECK-5, tasks.md task 53.
**State / role:** `Agent-Executing` (advisory only) · `agent_role = research` (advisory context provider) · `requirement_id = REQ-PRED-001` · `coverage_type = NFR` · labels: `phase:3`, `type:nfr`, `priority:normal` (OPTIONAL — Phase 6, never on the gate).

### EARS

- **Optional:** WHERE predictive next-step routing is enabled, the system shall inject predictions only as advisory context (via a `UserPromptSubmit` or `SessionStart` context-injection hook, or an MCP retrieve tool).
- **Unwanted:** IF a design routes a prediction into a block or allow gate decision, THEN the system shall reject that design — predictions shall NOT emit gate decisions and gates shall NOT read predictions (Z3 CHECK-5).
- **Optional:** WHERE predictive routing is enabled, the system shall tag predicted-routing spans distinctly and measure prediction acceptance and accuracy so routing can be disabled on drift.

### Acceptance criteria

1. Predictions are injected ONLY as advisory context through a context-injection hook or MCP retrieve tool — never into a gate.
2. Any design routing a prediction into an allow/block decision is rejected; CHECK-5 / Property 4 hold (gate decisions are prediction-independent).
3. Predicted-routing spans are tagged distinctly; prediction acceptance + accuracy are measured so routing can be disabled on drift.
4. The feature is OFF by default (Phase 6) and is built only after the spine is proven; it is built on battle-tested primitives (Speculative Actions / semantic-router / Claude memory tool), not pre-product services.

### Agent state-flow

Predictive routing never changes a coverage item's state. While enabled in `Agent-Executing`, it only seeds advisory context for the implementer/research subagents; the `Stop`/`PreToolUse` gates ignore it entirely. If drift is detected via the acceptance/accuracy spans, routing is disabled with no effect on any gate or terminal state.

### Tasks

- **[Orchestration] Implement off-gate advisory prediction injection** (tasks.md task 53, Phase 6, optional)
  - Inject predictions via a `UserPromptSubmit`/`SessionStart` context-injection hook or MCP retrieve tool; build on Speculative Actions / semantic-router / Claude memory tool.
  - Assert no prediction value ever reaches an allow/block gate (enforce the Property 4 / CHECK-5 independence design-time).
- **[Infrastructure] Tag and measure predicted-routing spans** (Phase 3 observability)
  - Tag predicted-routing spans distinctly; emit prediction-acceptance and prediction-accuracy metrics; wire a drift threshold that disables routing.
- **[API] Surface a Plane toggle for predictive routing** (Plane Webhooks/REST)
  - Expose an operator-controlled enable/disable property on the project (default OFF); on drift, auto-disable and post a comment — never alter a gate or terminal state.

---

## REQ-20 — Execution Bounds and Quality Thresholds (cross-cutting NFR)

**Maps to:** canonical Requirement 20 (NFR threshold registry), design run_state DDL + threshold owners table, tasks.md task 44.
**State / role:** `Agent-Executing` (config module) · `agent_role = human` (operator owns overrides) · `requirement_id = REQ-NFR-020` · `coverage_type = NFR` · labels: `phase:0`, `type:nfr`, `priority:high`.

### EARS

- **Ubiquitous:** THE system shall enforce the DEFAULT numeric thresholds: line coverage on touched files ≥ 85%; 0 HIGH/CRITICAL SAST findings; ≤ 15 minutes per Slice; iteration cap of 25 turns per Slice; retry budget of 3 per Slice; spec-completion loop cap of 7 passes; hook validator timeout of 60 seconds; telemetry export interval ≤ 5 seconds.
- **Ubiquitous:** THE system shall treat all numeric thresholds as configurable DEFAULTs, with changes requiring an explicit operator override.
- **Ubiquitous:** THE system shall register the additional DEFAULT thresholds — cost/token budget = 1,000,000 tokens/Slice; reasoning-loop K = 3; retry budget = 3/Slice; the vague-adjective reject-set `{fast, secure, scalable, optimized, efficient, reliable, performant}`; audit-log live-retention = 365 days; eval faithfulness = 0.8; eval answer-relevancy = 0.7; kill-switch flag-propagation interval ≤ 30 s — each with a named owner.
- **Unwanted:** IF a threshold is changed without an explicit operator override, THEN the system shall reject the change.

### Acceptance criteria

1. A single config module centralizes every numeric DEFAULT and exposes an explicit operator-override path; an unauthorized change is rejected.
2. Each registered threshold carries a named OWNER (quality owner, implementer loop, Spec_Compiler, Delivery Owner/Operator) per the canonical registry.
3. The loop/budget/cap thresholds consumed by `evaluate_stop`, the implementer loop, and the reasoning-loop detector all read from this registry (no hard-coded constants).
4. The vague-adjective reject-set is requirement-backed (consumed by `spec_validator.py` / Property 17), not test-backed only.

### Agent state-flow

The threshold registry is consumed across the whole flow but mutates no coverage state directly: `evaluate_stop` reads caps/budgets in `Agent-Executing`; the verifier reads coverage/perf/a11y bars in `In-Verification`; the reasoning-loop detector reads K. An operator override is the only authorized mutation; it is itself recorded.

### Tasks

- **[Infrastructure] Build the execution-bounds config module** (tasks.md task 44)
  - Centralize: coverage 85%, slice ≤ 15 min, iteration cap 25, retries 3, spec loop 7, validator timeout 60 s, export ≤ 5 s, token budget 1,000,000, reasoning-loop K=3, retention 365 d, faithfulness 0.8, answer-relevancy 0.7, kill-switch ≤ 30 s.
  - Implement explicit operator-override checks (reject any change lacking an authorized override).
  - Register the vague-adjective reject-set as a configurable DEFAULT consumed by `spec_validator.py`.
- **[Orchestration] Wire consumers to the registry**
  - Point `evaluate_stop` (caps/budget/no-progress), `implementer.md` (retry/token budget), the reasoning-loop detector (K), and the verifier (coverage/perf/a11y) at the central registry — no duplicated constants.
- **[API] Expose thresholds + owners in Plane** (Plane Webhooks/REST)
  - Mirror each threshold + its owner as project properties; require an operator role to change a value; record every override as an issue comment / audit entry.

---

## REQ-21 — HANDOFF Termination Semantics (Baseline B13)

**Maps to:** canonical Requirement 21 (REQ-LOOP-005), design `evaluate_stop` HANDOFF-before-block ordering + Property 5 (HANDOFF carve-out) + the spec-completion lex-specialis tiebreak, Z3 CHECK-5b/5c/8c.
**State / role:** `Agent-Executing` → `HANDOFF` · `agent_role = implementer` · `requirement_id = REQ-LOOP-005` · `coverage_type = functional` · `run_state = handoff` at termination · labels: `gate:stop`, `handoff`, `phase:0`, `type:functional`, `priority:blocking`.

### EARS

- **Unwanted:** IF the iteration cap, cost budget, or no-progress predicate is reached, THEN the `Stop_Hook` shall set `run_state.status = handoff`, emit a HANDOFF summary, and ALLOW termination (exit 0) — it shall NOT return exit 2 for these conditions (which would force continuation).
- **Ubiquitous:** THE system shall block (exit 2) ONLY on the unproven-items condition; HANDOFF conditions never block.
- **Unwanted (lex specialis):** IF the spec-completion HARD pass cap (`SPEC_COMPLETION_HARD_CAP = 7`, keyed on `run_state.spec_pass_count`) is reached WHILE `violation_count > 0`, THEN the REQ-LOOP-005 HANDOFF (exit 0) shall take precedence over the criterion-4.2 Stop-block (exit 2); the exit-2 block applies ONLY on passes before the cap.
- **Ubiquitous:** THE system shall treat `HANDOFF` and `Done` as mutually exclusive terminal states — a HANDOFF run is never `Done` (Z3 CHECK-3).

### Acceptance criteria

1. `evaluate_stop` evaluates HANDOFF triggers (cap → budget → no-progress) BEFORE the unproven-items completion gate; each returns `allow()`.
2. At HANDOFF, in-scope items are EXPECTED unproven and the `Stop` hook ALLOWS — reproducing the infinite-block defect (checking unproven first) is forbidden (Property 5 carve-out).
3. At `spec_pass_count >= 7` with `violation_count > 0`, HANDOFF (exit 0) wins over the REQ-SPEC-021 exit-2 block (CHECK-5b/5c).
4. `run_state.status = "handoff"` and the HANDOFF summary (remaining unproven items, last N slice outputs, reason) are emitted; `feature_list.json` is unmodified.
5. The `stop_hook_active` reentrancy guard prevents the Stop hook from re-triggering itself during a blocking cycle (REQ-GATE-004).

### Agent state-flow

When a HANDOFF trigger fires in `Agent-Executing` (implementation phase) or `Spec-Compiling` (spec phase at the 7-pass cap), `evaluate_stop` writes `run_state.status = "handoff"`, allows termination, and the issue flips to `HANDOFF` (cancelled group) — never `Done`. The spec-phase cap keys on `spec_pass_count`; the implementation-phase cap on `iteration_count`. The `with_reentrancy_guard` composition wraps `evaluate_stop` so a block does not cascade.

### Tasks

- **[Orchestration] Implement HANDOFF-before-block ordering in `evaluate_stop`** (tasks.md task 5.1)
  - Place the cap → budget → no-progress HANDOFF checks (each `return allow()` after `write_run_state(status="handoff")` + `emit_handoff_summary`) BEFORE the `violation_count`/empty-model/unproven-items blocking gates.
  - Phase-discriminate the cap (`spec` → `spec_pass_count`/7; `implementation` → `iteration_count`/25).
- **[Orchestration] Encode the spec-completion lex-specialis tiebreak** (tasks.md task 5.1 + design "Spec-Completion Loop Error Handling")
  - At `spec_pass_count >= SPEC_COMPLETION_HARD_CAP` with `violation_count > 0`, ensure the cap-HANDOFF (exit 0) has already returned before the `violation_count > 0` block can fire.
  - Keep the `violation_count > 0` exit-2 block on passes strictly before the cap; fail closed on `violation_count < 0` (validator error).
- **[Orchestration] Implement the reentrancy guard composition** (tasks.md tasks 5.1, 5.5)
  - `with_reentrancy_guard(evaluate_stop)` via `run_state.stop_hook_active`; release the flag only when the blocking condition clears; unit test asserts no cascade.
- **[Infrastructure] Add the HANDOFF Z3 fixtures** (formal_verification_merged.py)
  - Reproduce CHECK-3 (cap → `Done` under unproven is UNSAT), CHECK-5b/5c (block-on-cap UNSAT), CHECK-8c (block-on-no-progress UNSAT).
- **[API] Drive the Plane `HANDOFF` terminal state** (Plane Webhooks/REST)
  - On `status="handoff"`, transition the issue to `HANDOFF`, set `run_state = handoff`, apply the `handoff` label, and post the HANDOFF summary; never allow a HANDOFF issue to reach `Done`.

---

## REQ-24 — Checklist-Approval Gate + Research Epistemic Integrity (Baseline B19)

**Maps to:** canonical Requirement 24 (REQ-SPEC-016, REQ-SPEC-017), design PreToolUse checklist-approval guard + `research_claim_validator.py` + Property 27 (CHECK-12a/12b) + Property 29, tasks.md task 50 (+ 50.1).
**State / role:** `Spec-Compiling` (discovery uses the checklist) · `agent_role = research` · `requirement_id = REQ-SPEC-016` · `coverage_type = functional` · `gate = pretooluse` · labels: `agent:research`, `gate:pretooluse`, `phase:3`, `type:functional`, `priority:high`.

### EARS

- **Unwanted:** IF a `Domain_Baseline_Checklist` is in DRAFT (not human-approved — `approved_at` is NULL in `domain_baseline_checklists`), THEN it shall NOT be used for discovery; the `PreToolUse` checklist-approval guard shall block any discovery `Write` that references it (exit 2, CHECK-12a/12b).
- **Event-Driven:** WHEN the `Research_Sub_Agent` drafts a checklist or any sourced claim, THEN every external claim shall carry a source URL, each source shall be labeled by authority tier (primary/standard/peer-reviewed vs blog/vendor/social), and an independent fact-check pass (`research_claim_validator.py`) shall flag unverifiable or low-authority-only claims before human review.
- **State-Driven:** WHILE proactive discovery is active, the system shall run it ONLY against a checklist that is BOTH human-approved AND whose claims are source-URL- and authority-tier-labeled and have passed the fact-check.

### Acceptance criteria

1. A discovery `Write` referencing a `DRAFT` (NULL `approved_at`) checklist is blocked at `PreToolUse` (`check_checklist_approval`, exit 2); CHECK-12a UNSAT / CHECK-12b SAT.
2. `research_claim_validator.py` rejects any draft claim lacking a source URL or authority-tier label, or failing the fact-check, before the draft is presented for human review (Property 29).
3. The Initializer consumes a checklist for discovery ONLY when it is approved AND epistemically clean (the Req 24.2 precondition), beyond the bare DRAFT/approved bit.
4. The checklist version + SHA used are recorded and linked to `feature_list.json.checklist_ref` for auditable derivation.

### Agent state-flow

`research` drafts a checklist in `Agent-Triaged`/`Spec-Compiling`; the draft is fact-checked + authority-labeled (`research_claim_validator.py`) before human review. The human approves (sets `approved_at`) → the checklist becomes usable. The `PreToolUse` checklist-approval guard blocks any `Spec-Compiling` discovery write that references an unapproved checklist → `Blocked`. Only an approved-and-clean checklist lets discovery proceed toward `Spec-Verified`.

### Tasks

- **[Orchestration] Add `check_checklist_approval` to `pre_tool_use_hook.py`** (tasks.md task 50.1)
  - Block any Initializer/discovery `Write` referencing a checklist whose `approved_at` is NULL in `domain_baseline_checklists`; chain it with the plan/scope/artifact/status checks and the 49.1 integrity guard in the order pinned at task 6.1.
- **[Orchestration] Implement `tools/research_claim_validator.py`** (tasks.md task 50)
  - Validate that every external claim carries a source URL + authority-tier label and passes the independent fact-check before human review; reject unlabeled/unverified claims (Property 29).
  - Validate draft claims against `schema/checklist_item.schema.json` (`claim`, `source_url`, `authority_tier` enum, `fact_checked`).
  - Gate the research-invocation path so research is NOT invoked on an un-gated product class until this task lands (phase-ordering deferral).
- **[Infrastructure] Migrate the checklist version-history table** (tasks.md task 28.6, migration `006_domain_baseline_checklists.sql`)
  - Create `domain_baseline_checklists` (`product_class`, `version`, `sha`, `file_path`, `approved_at`, `approved_by`); add the CHECK-12 Z3 fixtures and the Property 27 PBT.
- **[API] Surface checklist approval in Plane** (Plane Webhooks/REST)
  - Represent a DRAFT checklist as an issue requiring `human:review`; on human approval write `approved_at` + `approved_by` and flip the issue out of review; link `checklist_ref` (path/version/sha) onto the discovery issue for auditable derivation.

---

## REQ-26 — Reasoning-Loop Detection (Baseline B11)

**Maps to:** canonical Requirement 26 (REQ-OBS-006), design Phase-3 REASONING-span loop detection + reasoning-loop K (=3) in the threshold registry, tasks.md task 52 (reasoning-loop leg).
**State / role:** `Agent-Executing` / `In-Verification` (telemetry analysis) · `agent_role = verifier` (observability/audit reading the trace) · `requirement_id = REQ-OBS-006` · `coverage_type = NFR` · labels: `phase:3`, `type:nfr`, `priority:normal`.

### EARS

- **Event-Driven:** WHEN telemetry is analyzed, the system shall mark reasoning spans with a custom span ATTRIBUTE `claude.span.kind="reasoning"` on an OTel INTERNAL span (NOT a new `SpanKind` enum value — `SpanKind` is the closed enum `{INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER}`).
- **Event-Driven:** WHEN ≥ K identical tool-call signatures occur (DEFAULT K = 3, from the Requirement-20 threshold registry), the system shall flag the repeated-action / reasoning-loop pattern as a first-class signal, complementing the slice-level no-progress watchdog.
- **Ubiquitous:** THE system shall treat the reasoning-loop signal as complementary to (not a replacement for) the no-progress predicate.

### Acceptance criteria

1. Reasoning spans are emitted as OTel INTERNAL spans carrying the `claude.span.kind="reasoning"` attribute — no new `SpanKind` enum value is introduced.
2. A run with ≥ 3 identical tool-call signatures is flagged as a reasoning loop; the threshold K reads from the Requirement-20 registry.
3. The reasoning-loop signal is emitted as a first-class observable signal (and forwarded to the same trace endpoint as gate decisions), complementing the N=3 slice-level no-progress watchdog without replacing it.

### Agent state-flow

The reasoning-loop detector reads the live trace during `Agent-Executing`/`In-Verification` and emits a first-class signal; it does not itself change a coverage item's state. The signal complements the no-progress predicate — if the loop also satisfies the no-progress predicate, the existing `evaluate_stop` HANDOFF path (REQ-14/21) terminates the run to `HANDOFF`. The detector's own correctness is verified `In-Verification` → `Done`.

### Tasks

- **[Infrastructure] Emit the REASONING span attribute** (tasks.md task 52, REASONING leg; Phase 3)
  - Mark reasoning spans as OTel INTERNAL spans carrying `claude.span.kind="reasoning"` (attribute, not a SpanKind value); pin the OTel SDK + GenAI semconv versions.
- **[Orchestration] Implement the repeated-action detector** (tasks.md task 52)
  - Compute tool-call signatures; flag ≥ K (DEFAULT 3, from the Req-20 registry) identical signatures as a reasoning loop; emit the first-class signal.
- **[Infrastructure] Forward the signal to the trace endpoint** (tasks.md task 36.1)
  - Forward the reasoning-loop signal to the same OTLP endpoint as hook gate-decision events; assert it complements (does not replace) the no-progress watchdog.
- **[API] Surface reasoning-loop alerts in Plane** (Plane Webhooks/REST)
  - On a reasoning-loop flag, post a comment on the linked issue and apply a `priority:high` label; if the loop also trips no-progress, reflect the resulting `HANDOFF` transition.

---

## REQ-29 — Structured Omission Declaration (Baseline B01/B19)

**Maps to:** canonical Requirement 29 (REQ-SPEC-018), design `omission_guard` (in `subagent_stop_hook.py`) + `schema/subagent_output.schema.json` + Property 30 (CHECK-13a/13b), tasks.md task 54 (+ 39.20).
**State / role:** `In-Verification` (SubagentStop acceptance) · `agent_role = verifier` (the SubagentStop gate; the guard also fires on initializer/research results) · `requirement_id = REQ-SPEC-018` · `coverage_type = functional` · `gate = subagentstop` · labels: `gate:completion`, `gate:subagentstop`, `phase:0`, `type:functional`, `priority:blocking`.

### EARS

- **Event-Driven:** WHEN a subagent (initializer, research, verifier) completes a discovery, research, or verification pass, THEN its output shall include a non-null `omission_declaration` field listing, by EARS scenario category (Primary / Alternate / Exception / Recovery / Non-Functional / Edge-Case), every scenario class it did NOT cover, using a `[Gap]` marker per omitted class.
- **Unwanted:** IF a subagent result's `omission_declaration` field is absent or null, THEN the `SubagentStop_Hook` shall reject acceptance of that result with exit 2 (Z3 CHECK-13a/13b; Property 30).
- **Ubiquitous:** THE JSON schema for each subagent output type (initializer, research, verifier) shall include `omission_declaration` as a required, non-nullable field.

> **Scope note (canonical):** the Implementer is EXEMPT — it produces a commit, not evidence, and hands off to the Verifier (REQ-VERIFY-005). The omission gate checks presence/non-null ONLY; empty-but-non-null (`""`/`{}`/`[]`) is intentionally accepted, and the per-category `[Gap]` content is a human-reviewed authoring convention, not a harness-checked constraint.

### Acceptance criteria

1. `schema/subagent_output.schema.json` declares `omission_declaration` as a REQUIRED, non-nullable envelope field validated for initializer/research/verifier roles.
2. The `omission_guard` in `subagent_stop_hook.py` rejects (exit 2) any subagent result whose `omission_declaration` is null or absent; CHECK-13a UNSAT / CHECK-13b SAT (Property 30).
3. The Implementer→Verifier handoff carries no `omission_declaration` and is not rejected (Implementer exemption).
4. The guard runs end-to-end alongside the base `subagent_stop_hook.py` evidence-schema validator before Phase 1.

### Agent state-flow

When `verifier` (or `initializer`/`research`) returns a result in `In-Verification`, the `SubagentStop` evidence-schema gate validates the four-field Evidence_Record (verifier-only), and the `omission_guard` independently rejects any result whose `omission_declaration` is null/absent → `Blocked` (exit 2). A result that declares its gaps (non-null `omission_declaration`) is accepted, letting the coverage item proceed toward `Done`. The Implementer result is exempt from both checks.

### Tasks

- **[Infrastructure] Author the subagent-output schema** (tasks.md task 54, schema leg)
  - Add `omission_declaration` as a REQUIRED, non-nullable field to `schema/subagent_output.schema.json` (the single envelope validated for all roles); keep `evidence[]` present only for the verifier role.
- **[Orchestration] Implement the `omission_guard` in `subagent_stop_hook.py`** (tasks.md task 54)
  - Reject (exit 2) any initializer/research/verifier result whose `omission_declaration` is null/absent; exempt the Implementer; ensure it ships runnable alongside task 8's base evidence-schema validator before Phase 1.
  - Wire `audit_log.append(...)` on both the allow and block paths of the omission guard (Phase-2 addition via task 52.3).
- **[Infrastructure] Add the omission-gate Z3 + property tests** (tasks.md task 39.20)
  - Encode CHECK-13a/13b; author the Property 30 PBT (null/absent → reject; non-null → accept; Implementer exempt).
- **[API] Surface omission declarations in Plane** (Plane Webhooks/REST)
  - On acceptance, render the `omission_declaration` (`[Gap]` markers by EARS category) as a structured issue comment so a human reviewer sees the declared gaps; on a null/absent rejection, transition the issue to `Blocked` and label `blocked`.

---

## Epic coverage gates (E8 exit criteria)

- **HANDOFF/Done mutual exclusion** proven (CHECK-3); `evaluate_stop` HANDOFF-before-block ordering proven (CHECK-5b/5c/8a/8b/8c) — no infinite-block defect.
- **No code-write without an approved, SHA-bound plan** (CHECK-4f); required-reviewer ruleset live (`tests/smoke/test_repo_ruleset.py`).
- **Hook exit-code contract** (Property 21) and **prediction independence** (Property 4 / CHECK-5) green.
- **Checklist-approval-before-use** (CHECK-12a/12b, Property 27) and **omission-declaration gate** (CHECK-13a/13b, Property 30) green.
- **Threshold registry** owns every numeric DEFAULT with a named owner; no hard-coded caps remain in `evaluate_stop`, `implementer.md`, or the reasoning-loop detector.
- Every E8 WIRING coverage item is `proven` with an `integration` Evidence_Record; every functional item with its appropriate evidence; the `Stop` hook allows termination only when all in-scope items are `proven` OR a HANDOFF trigger is active.


---

## 5. Supporting Documentation & System Architecture · Completeness Gates


## Architecture & Environment — Plane Self-Host (the ASCP PM Control Plane)

This section documents the **actual** fetched Plane community Docker Compose deployment that runs the **Agentic SDLC Control Plane (ASCP)** Plane workspace — the PM control plane for the autonomous Spec-to-Evidence delivery engine. Every service, port, connection string, and environment variable below is read verbatim from the two committed files:

- `/Users/danielmanzela/Agentic-Driven SDLC Platform/plane-selfhost/docker-compose.yml`
- `/Users/danielmanzela/Agentic-Driven SDLC Platform/plane-selfhost/plane.env`

The control plane's autonomous loop (initializer → implementer → verifier subagents, six Claude-Code hooks, the fail-closed `evaluate_stop` gate, the 8-table Postgres traceability graph) treats this Plane instance as the **human-facing PM surface**: ASCP issues carry the shared control vocabulary (states `Backlog … Done / HANDOFF / Blocked / Failed`, fields `agent_role`, `requirement_id`, `evidence_status`, `worktree_branch`, `agent_run_id`, `output_hash`, etc.). Plane is therefore an **operational dependency of the gate**, not decorative — the traceability triple `issue ↔ branch ↔ run` is anchored on Plane issue IDs. Its availability and durability characteristics matter to the control plane, which is why the volume/backup/upgrade discipline below is treated as first-class.

---

### 1. Service Topology — 13 services

The compose file defines exactly **13 services**. Eight are first-party Plane images, four are stateful infrastructure backends, one is the edge proxy. All images are pinned via `${APP_RELEASE:-stable}` (set to `APP_RELEASE=stable` in `plane.env`); the four infra images are version-pinned directly in the compose file.

| # | Service | Image | Role | Replicas (env var) | Depends on |
|---|---------|-------|------|--------------------|------------|
| 1 | `web` | `makeplane/plane-frontend:${APP_RELEASE:-stable}` | Main Next.js app (the ASCP workspace UI) | `${WEB_REPLICAS:-1}` | `api`, `worker` |
| 2 | `space` | `makeplane/plane-space:${APP_RELEASE:-stable}` | Public "Spaces" / shared views frontend | `${SPACE_REPLICAS:-1}` | `api`, `worker`, `web` |
| 3 | `admin` | `makeplane/plane-admin:${APP_RELEASE:-stable}` | God-mode / instance admin console | `${ADMIN_REPLICAS:-1}` | `api`, `web` |
| 4 | `live` | `makeplane/plane-live:${APP_RELEASE:-stable}` | Real-time collaboration (HocusPocus/websocket) | `${LIVE_REPLICAS:-1}` | `api`, `web` |
| 5 | `api` | `makeplane/plane-backend:${APP_RELEASE:-stable}` | Django/DRF REST API (Gunicorn). Entrypoint `./bin/docker-entrypoint-api.sh` | `${API_REPLICAS:-1}` | `plane-db`, `plane-redis`, `plane-mq` |
| 6 | `worker` | `makeplane/plane-backend:${APP_RELEASE:-stable}` | Celery async worker. Entrypoint `./bin/docker-entrypoint-worker.sh` | `${WORKER_REPLICAS:-1}` | `api`, `plane-db`, `plane-redis`, `plane-mq` |
| 7 | `beat-worker` | `makeplane/plane-backend:${APP_RELEASE:-stable}` | Celery beat scheduler. Entrypoint `./bin/docker-entrypoint-beat.sh` | `${BEAT_WORKER_REPLICAS:-1}` | `api`, `plane-db`, `plane-redis`, `plane-mq` |
| 8 | `migrator` | `makeplane/plane-backend:${APP_RELEASE:-stable}` | One-shot DB migration job. Entrypoint `./bin/docker-entrypoint-migrator.sh`; `restart_policy: on-failure`, `replicas: 1` | fixed `1` | `plane-db`, `plane-redis` |
| 9 | `plane-db` | `postgres:15.7-alpine` | PostgreSQL 15.7, started with `postgres -c 'max_connections=1000'` | fixed `1` | — |
| 10 | `plane-redis` | `valkey/valkey:7.2.11-alpine` | Redis-compatible cache/broker (Valkey 7.2.11) | fixed `1` | — |
| 11 | `plane-mq` | `rabbitmq:3.13.6-management-alpine` | RabbitMQ 3.13.6 (Celery broker / message queue) | fixed `1` | — |
| 12 | `plane-minio` | `minio/minio:latest` | S3-compatible object store. `server /export --console-address ":9090"` | fixed `1` | — |
| 13 | `proxy` | `makeplane/plane-proxy:${APP_RELEASE:-stable}` | Caddy-based edge reverse proxy + ACME/TLS. **The only service publishing host ports.** | fixed `1` | `web`, `api`, `space`, `admin`, `live` |

**Restart policy:** all long-running services use `restart_policy.condition: any`; only `migrator` uses `on-failure` (it is expected to exit `0` after migrations complete).

```mermaid
graph TB
    subgraph Edge
        PROXY["proxy (Caddy)\n:8090 HTTP / :8453 HTTPS\nACME TLS"]
    end
    subgraph Frontends
        WEB["web (plane-frontend)"]
        SPACE["space (plane-space)"]
        ADMIN["admin (plane-admin)"]
        LIVE["live (plane-live / ws)"]
    end
    subgraph Backend
        API["api (Django/Gunicorn)"]
        WORKER["worker (Celery)"]
        BEAT["beat-worker (Celery beat)"]
        MIG["migrator (one-shot)"]
    end
    subgraph Stateful["Stateful backends (StatefulSet candidates)"]
        DB[("plane-db\npostgres:15.7")]
        REDIS[("plane-redis\nvalkey:7.2.11")]
        MQ[("plane-mq\nrabbitmq:3.13.6")]
        MINIO[("plane-minio\nMinIO")]
    end

    PROXY --> WEB & SPACE & ADMIN & LIVE & API
    WEB --> API
    SPACE --> API
    ADMIN --> API
    LIVE --> API
    API --> DB & REDIS & MQ & MINIO
    WORKER --> DB & REDIS & MQ & MINIO
    BEAT --> DB & REDIS & MQ
    MIG --> DB & REDIS
    LIVE -.->|REDIS_URL| REDIS
```

---

### 2. Host-Port Mapping — 8090 HTTP / 8453 HTTPS

Only the `proxy` service publishes host ports. The mapping is parameterized in the compose file and bound to non-default values in `plane.env`:

```yaml
# docker-compose.yml — proxy service
ports:
  - target: 80
    published: ${LISTEN_HTTP_PORT:-80}     # → 8090 (from plane.env)
    protocol: tcp
    mode: host
  - target: 443
    published: ${LISTEN_HTTPS_PORT:-443}    # → 8453 (from plane.env)
    protocol: tcp
    mode: host
```

```ini
# plane.env
APP_DOMAIN=localhost:8090
LISTEN_HTTP_PORT=8090
LISTEN_HTTPS_PORT=8453
WEB_URL=http://${APP_DOMAIN}            # → http://localhost:8090
CORS_ALLOWED_ORIGINS=http://${APP_DOMAIN}  # → http://localhost:8090
```

| Host port | Container port | Purpose |
|-----------|----------------|---------|
| **8090** | proxy `:80` | Plane UI / API over HTTP — the ASCP workspace at `http://localhost:8090` |
| **8453** | proxy `:443` | Plane UI / API over HTTPS (ACME-managed when `CERT_EMAIL`/`CERT_ACME_DNS` are set) |

The non-standard ports (8090/8453 rather than 80/443) avoid collisions with other services on the host and keep this Plane instance addressable as `http://localhost:8090`. Internal service ports (`api:8000`, `plane-minio:9000`/console `:9090`, `plane-db:5432`, `plane-redis:6379`, `plane-mq:5672` + management `:15672`) are **not** published to the host — they are reachable only on the compose default network by service name.

> **Operational note for the control plane:** `APP_DOMAIN`, `WEB_URL`, and `CORS_ALLOWED_ORIGINS` are all derived from `localhost:8090`. Any agent/MCP client (or the ASCP issue-sync tooling) that calls the Plane API must target `http://localhost:8090`; a mismatch surfaces as a CORS rejection because `CORS_ALLOWED_ORIGINS` is pinned to exactly that origin.

---

### 3. Backend Connection Strings & Environment Variables

All backend services (`api`, `worker`, `beat-worker`, `migrator`) merge the YAML anchor sets `*app-env, *db-env, *redis-env, *minio-env, *aws-s3-env, *proxy-env`. The effective values come from `plane.env`.

#### 3.1 PostgreSQL (`plane-db`)

```ini
# plane.env — DB SETTINGS
PGHOST=plane-db
PGDATABASE=plane
POSTGRES_USER=plane
POSTGRES_PASSWORD=plane
POSTGRES_DB=plane
POSTGRES_PORT=5432
PGDATA=/var/lib/postgresql/data
DATABASE_URL=          # empty in env → falls back to compose default
```

The compose `*app-env` anchor supplies the effective DSN default when `DATABASE_URL` is blank:

```
DATABASE_URL = postgresql://plane:plane@plane-db/plane
```

- `plane-db` runs `postgres:15.7-alpine` with `postgres -c 'max_connections=1000'` — sized so the multi-replica Gunicorn/Celery fleet plus the ASCP traceability-graph writers do not exhaust connections.
- Data persists on the **`pgdata`** volume mounted at `/var/lib/postgresql/data` (`PGDATA`).

#### 3.2 Redis / Valkey (`plane-redis`)

```ini
# plane.env — REDIS SETTINGS
REDIS_HOST=plane-redis
REDIS_PORT=6379
REDIS_URL=            # empty in env → falls back to compose default
```

Compose `*redis-env` default when `REDIS_URL` is blank:

```
REDIS_URL = redis://plane-redis:6379/
```

The image is **`valkey/valkey:7.2.11-alpine`** — a drop-in, BSD-licensed Redis fork. Used as Django cache and Celery result/coordination backend, and by the `live` service for real-time fan-out. Data persists on the **`redisdata`** volume at `/data`. The `live` service receives `*live-env` + `*redis-env` (so it shares `REDIS_URL`).

#### 3.3 RabbitMQ (`plane-mq`)

```ini
# plane.env — RabbitMQ Settings
RABBITMQ_HOST=plane-mq
RABBITMQ_PORT=5672
RABBITMQ_USER=plane
RABBITMQ_PASSWORD=plane
RABBITMQ_VHOST=plane
AMQP_URL=             # empty in env → falls back to compose default
```

Compose `*mq-env` sets `RABBITMQ_DEFAULT_USER/PASS/VHOST=plane`; the `*app-env` AMQP default when `AMQP_URL` is blank:

```
AMQP_URL = amqp://plane:plane@plane-mq:5672/plane
```

Image **`rabbitmq:3.13.6-management-alpine`** (management plugin on `:15672`, not host-published). This is the Celery broker for `worker` + `beat-worker`. Durable queue/exchange state persists on the **`rabbitmq_data`** volume at `/var/lib/rabbitmq`.

#### 3.4 MinIO / S3 (`plane-minio`)

```ini
# plane.env — DATA STORE SETTINGS
USE_MINIO=1
AWS_REGION=
AWS_ACCESS_KEY_ID=access-key
AWS_SECRET_ACCESS_KEY=secret-key
AWS_S3_ENDPOINT_URL=http://plane-minio:9000
AWS_S3_BUCKET_NAME=uploads
FILE_SIZE_LIMIT=5242880        # 5 MiB upload cap
MINIO_ENDPOINT_SSL=0
```

The compose `*minio-env` anchor wires `MINIO_ROOT_USER ← AWS_ACCESS_KEY_ID` and `MINIO_ROOT_PASSWORD ← AWS_SECRET_ACCESS_KEY` (so the bucket credentials and the MinIO root credentials are the same `access-key` / `secret-key` pair). Object data (attachments, exports — including any ASCP evidence artifacts or screenshots attached to issues) persists on the **`uploads`** volume at `/export`. `USE_MINIO=1` selects the bundled MinIO; to switch to external S3, set `USE_MINIO=0`, populate `AWS_REGION` + real credentials + endpoint, and comment out the `plane-minio` service (per the compose comment).

#### 3.5 Application / security / web env (`*app-env`, `*proxy-env`, `*live-env`)

```ini
# plane.env — app / security
SECRET_KEY=a411f976b0dadd0a87f6c922a78dd04cf8d707997e63d8b351ebc6212374b80b
DEBUG=0
GUNICORN_WORKERS=1
API_BASE_URL=http://api:8000
API_KEY_RATE_LIMIT=60/minute
LIVE_SERVER_SECRET_KEY=         # empty in env → compose default below
WEBHOOK_ALLOWED_IPS=
WEBHOOK_ALLOWED_HOSTS=

# proxy / TLS
CERT_ACME_CA=https://acme-v02.api.letsencrypt.org/directory
TRUSTED_PROXIES=0.0.0.0/0
SITE_ADDRESS=:80
CERT_EMAIL=
CERT_ACME_DNS=
```

| Variable | Effective value | Notes |
|----------|-----------------|-------|
| `SECRET_KEY` | `a411f976…74b80b` (64-hex) | Django signing key. **Must be rotated for any non-local deployment** (the bundled value is a fixed sample). |
| `APP_DOMAIN` | `localhost:8090` | Drives `WEB_URL` + `CORS_ALLOWED_ORIGINS`. |
| `WEB_URL` | `http://localhost:8090` | Public base URL of the workspace. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:8090` | Single allowed browser origin. |
| `API_BASE_URL` | `http://api:8000` | Internal API target used by `live`. |
| `DEBUG` | `0` | Production mode. |
| `GUNICORN_WORKERS` | `1` | Single Gunicorn worker per `api` replica. |
| `API_KEY_RATE_LIMIT` | `60/minute` | API-key throttle — relevant to ASCP automation hitting the Plane API. |
| `LIVE_SERVER_SECRET_KEY` | blank in env → compose default `2FiJk1U2aiVPEQtzLehYGlTSnTnrs7LW` | **Must be set to a secure value in production** (the compose default is a sample; `plane.env` carries the production warning inline). |
| `FILE_SIZE_LIMIT` | `5242880` | 5 MiB attachment cap (proxy + app). |
| `TRUSTED_PROXIES` | `0.0.0.0/0` | Caddy trusts all upstream proxy headers (acceptable behind a single host edge; tighten if fronted). |
| `WEBHOOK_ALLOWED_IPS` / `WEBHOOK_ALLOWED_HOSTS` | empty | SSRF allowlist for webhook targets — empty means only public IPs are reachable. Populate with the ASCP control-plane host/CIDR if Plane webhooks must reach an internal `silo`-style service. |
| `CERT_EMAIL` / `CERT_ACME_DNS` | empty | TLS stays self-signed/HTTP-only until set; `CERT_ACME_CA` already points at Let's Encrypt production. |

---

### 4. Bring-Up

The deployment is brought up with a single command from the `plane-selfhost/` directory, explicitly passing the env file (the compose file reads `${VAR}` interpolations that the env file must supply):

```bash
docker compose --env-file plane.env up -d
```

**Ordering is handled by `depends_on`** (compose start-order only, not health-gated): infra (`plane-db`, `plane-redis`, `plane-mq`, `plane-minio`) starts first, then `migrator` runs the Django migrations against `plane-db` and exits `0`, then `api` → `worker`/`beat-worker` → frontends → `proxy`. Because `depends_on` here is start-order (no `condition: service_healthy` is declared), the backend retries its DB/broker connections until they accept — the `restart_policy: any` on the long-running services covers the startup race.

Useful operational variants:

```bash
# Tail logs for the whole stack
docker compose --env-file plane.env logs -f

# Status of all 13 services
docker compose --env-file plane.env ps

# Re-run migrations only (after an image bump)
docker compose --env-file plane.env up -d migrator

# Stop everything but KEEP volumes (state preserved)
docker compose --env-file plane.env down

# DESTRUCTIVE: also delete pgdata/redisdata/uploads/rabbitmq_data
docker compose --env-file plane.env down -v
```

---

### 5. Health & Readiness

The compose file **does not declare `healthcheck:` blocks** — readiness is established operationally rather than via container health gates. Recommended readiness probes for this exact stack:

| Target | Readiness probe | Ready signal |
|--------|-----------------|--------------|
| Edge (proxy) | `curl -fsS http://localhost:8090/` | HTTP 200 from the workspace shell |
| API liveness | `docker compose exec api curl -fsS http://localhost:8000/` (internal) | API responding on `:8000` |
| `migrator` completed | `docker compose ps migrator` | Container `Exited (0)` — migrations applied |
| Postgres | `docker compose exec plane-db pg_isready -U plane -d plane` | `accepting connections` |
| Valkey | `docker compose exec plane-redis redis-cli ping` | `PONG` |
| RabbitMQ | `docker compose exec plane-mq rabbitmq-diagnostics -q ping` | `Ping succeeded` |
| MinIO | `docker compose exec plane-minio mc ready local` (or `curl :9000/minio/health/ready`) | `ready` / HTTP 200 |

**Composite readiness gate** (e.g. for the ASCP control plane to treat its PM surface as live):

```bash
# Block until the workspace answers on the published port
until curl -fsS http://localhost:8090/ >/dev/null; do sleep 2; done
# Confirm migrations actually applied (migrator exited 0, not crash-looping)
docker compose --env-file plane.env ps migrator | grep -q 'Exited (0)'
```

---

### 6. Backup & Restore — `pgdata`, `uploads`, `redisdata`

There are **10 named volumes** declared in the compose file. The three that hold durable, non-reconstructable state are `pgdata` (the relational source of truth — issues, states, the ASCP control-vocabulary fields), `uploads` (object store — attachments/evidence blobs), and `rabbitmq_data` (durable queue state). `redisdata` is cache/coordination (largely reconstructable but backed up for completeness); the four `logs_*` volumes and `proxy_config`/`proxy_data` (TLS material/ACME state) are operational.

| Volume | Mount | Service | Backup priority | Reconstructable? |
|--------|-------|---------|-----------------|------------------|
| `pgdata` | `/var/lib/postgresql/data` | `plane-db` | **Critical** | No — primary state |
| `uploads` | `/export` | `plane-minio` | **Critical** | No — attachments/evidence |
| `rabbitmq_data` | `/var/lib/rabbitmq` | `plane-mq` | High | Partly (in-flight jobs lost) |
| `redisdata` | `/data` | `plane-redis` | Medium | Mostly (cache) |
| `proxy_config`, `proxy_data` | `/config`, `/data` | `proxy` | Medium | TLS certs re-issuable via ACME |
| `logs_api`, `logs_worker`, `logs_beat-worker`, `logs_migrator` | `/code/plane/logs` | backend | Low | Yes |

**Postgres — logical backup (preferred; portable across PG patch versions):**

```bash
# Backup
docker compose --env-file plane.env exec -T plane-db \
  pg_dump -U plane -d plane --format=custom > plane-$(date +%F).dump

# Restore (into a clean plane-db)
docker compose --env-file plane.env exec -T plane-db \
  pg_restore -U plane -d plane --clean --if-exists < plane-2026-06-16.dump
```

**MinIO `uploads` — mirror the bucket out:**

```bash
docker compose --env-file plane.env exec plane-minio \
  sh -c 'mc alias set local http://localhost:9000 access-key secret-key && \
         mc mirror --overwrite local/uploads /export-backup'
# then copy /export-backup off the host, or back up the `uploads` volume directly (below)
```

**Volume-level snapshot (any volume — works for `pgdata`/`uploads`/`redisdata`/`rabbitmq_data`):**

```bash
# Stop writers first for a consistent pgdata snapshot
docker compose --env-file plane.env stop plane-db
docker run --rm \
  -v plane-selfhost_pgdata:/data:ro \
  -v "$PWD":/backup alpine \
  tar czf /backup/pgdata-$(date +%F).tar.gz -C /data .
docker compose --env-file plane.env start plane-db

# Restore: untar into the (empty) target volume
docker run --rm \
  -v plane-selfhost_pgdata:/data \
  -v "$PWD":/backup alpine \
  sh -c 'rm -rf /data/* && tar xzf /backup/pgdata-2026-06-16.tar.gz -C /data'
```

> The volume name is prefixed by the compose **project name** (the directory, `plane-selfhost`), e.g. `plane-selfhost_pgdata`, `plane-selfhost_uploads`, `plane-selfhost_redisdata`. Confirm with `docker volume ls`. For a consistent multi-store snapshot, `down` (without `-v`) the stack, snapshot all four stateful volumes, then `up -d`.

---

### 7. Upgrade Path

Images are pinned by the `${APP_RELEASE:-stable}` tag (`stable` per `plane.env`). To upgrade:

```bash
# 1. BACKUP FIRST — at minimum pgdata + uploads (section 6)

# 2. Pin a new release (recommended: a concrete version tag, not floating 'stable')
#    edit plane.env:  APP_RELEASE=<new-version>

# 3. Pull the new first-party images
docker compose --env-file plane.env pull

# 4. Run migrations on the new backend image, THEN roll the rest
docker compose --env-file plane.env up -d migrator
docker compose --env-file plane.env ps migrator   # expect Exited (0)
docker compose --env-file plane.env up -d          # recreate changed services

# 5. Verify readiness (section 5) at http://localhost:8090
```

Notes:
- The four infra images are **independently pinned** in the compose file (`postgres:15.7-alpine`, `valkey/valkey:7.2.11-alpine`, `rabbitmq:3.13.6-management-alpine`, `minio/minio:latest`). A **Postgres major-version** bump (e.g. 15 → 16) is **not** an in-place upgrade — `pgdata` is not forward-compatible across majors; do a `pg_dump` (logical) restore into a fresh PG-16 `plane-db`. `minio:latest` floats — pin it to a digest for reproducible upgrades.
- `migrator` runs forward-only Django migrations. **There is no automatic down-migration** — roll back by restoring the pre-upgrade `pgdata` backup and reverting `APP_RELEASE`.
- `restart_policy: any` means stale containers are replaced cleanly on `up -d`; only services whose image/config changed are recreated.
- For the ASCP control plane: pause any agent loop that writes to Plane (or that depends on the `issue ↔ branch ↔ run` traceability triple) during the upgrade window, since the API and websocket (`live`) briefly cycle.

---

### 8. Kubernetes Translation Note

The compose topology maps cleanly onto Kubernetes by splitting on the stateful/stateless boundary already visible in the file (the four backends with their own volumes vs. the stateless app fleet vs. the single edge).

| Compose service | K8s workload | Storage / networking |
|-----------------|--------------|----------------------|
| `plane-db` | **StatefulSet** (1 replica) | `volumeClaimTemplate` → PVC for `pgdata` at `/var/lib/postgresql/data`; headless `Service`. Carry over `max_connections=1000`. |
| `plane-redis` | **StatefulSet** (1) | PVC for `redisdata` at `/data`; headless `Service`. |
| `plane-mq` | **StatefulSet** (1) | PVC for `rabbitmq_data` at `/var/lib/rabbitmq`; headless `Service` (+ `:5672`/`:15672`). |
| `plane-minio` | **StatefulSet** (1) | PVC for `uploads` at `/export`; `Service` on `:9000` (+ console `:9090`). Or replace with managed S3 (`USE_MINIO=0`). |
| `migrator` | **Job** (`backoffLimit` ≈ `on-failure`) | Run-to-completion; gate the app rollout on Job success (init-container or Argo/Helm hook). |
| `api` | **Deployment** | Scale via `API_REPLICAS`→`replicas`; `Service` `:8000`; readiness probe on `/`. |
| `worker` | **Deployment** | No inbound `Service` (Celery consumer); HPA on queue depth. |
| `beat-worker` | **Deployment** (strictly 1) | Singleton scheduler — `replicas: 1`, `Recreate` strategy to avoid duplicate beats. |
| `web` | **Deployment** | `Service` + `Ingress` host/path routing. |
| `space` | **Deployment** | `Service`, routed under its path/host via Ingress. |
| `admin` | **Deployment** | `Service`, routed via Ingress (lock down to admins). |
| `live` | **Deployment** | `Service` `:8000` ws; Ingress with websocket/sticky-session annotations. |
| `proxy` | replace with **Ingress** | The Caddy proxy's host-port publish (`8090`/`8453`) becomes an `Ingress` (+ `cert-manager` `ClusterIssuer` for the ACME/`CERT_ACME_*` role). Or keep `plane-proxy` as a Deployment behind a `Service`/LoadBalancer if you want Plane's bundled routing. |

Translation specifics:
- **Config split:** move `*db-env / *redis-env / *mq-env / *minio-env / *aws-s3-env / *proxy-env / *app-env` into a `ConfigMap`; move secrets (`SECRET_KEY`, `POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD`, `AWS_SECRET_ACCESS_KEY`, `LIVE_SERVER_SECRET_KEY`) into a `Secret`. Connection strings reference **K8s Service DNS** instead of compose service names — e.g. `postgresql://plane:plane@plane-db.<ns>.svc.cluster.local/plane`, `redis://plane-redis.<ns>.svc.cluster.local:6379/`, `amqp://plane:plane@plane-mq.<ns>.svc.cluster.local:5672/plane`.
- **Ingress hosts/ports:** the `8090`/`8453` host-port mapping is an Ingress concern; set `APP_DOMAIN`/`WEB_URL`/`CORS_ALLOWED_ORIGINS` to the real Ingress hostname (not `localhost:8090`) and let `cert-manager` own TLS in place of `CERT_EMAIL`/`CERT_ACME_DNS`.
- **Health gating:** add real `readinessProbe`/`livenessProbe` (section 5 probes) on the Deployments and StatefulSets — Kubernetes makes the readiness that compose left implicit explicit, and lets the app Deployments depend on Postgres/RabbitMQ being `Ready` rather than relying on restart loops.
- **Ordering:** the compose `depends_on` chain becomes a Helm/Argo wave order — StatefulSets `Ready` → `migrator` Job complete → app Deployments → Ingress.

---

### 9. Why this matters to the Spec-to-Evidence control plane

Plane is the **PM control plane** for ASCP, so its environment is part of the gate's operating substrate:

- The Plane Postgres (`plane-db` / `pgdata`) holds the human-facing projection of the same lifecycle the control plane gates internally — issues moving `Backlog → Agent-Triaged → … → Done`, with `HANDOFF`/`Blocked`/`Failed` as the distinct terminal states the fail-closed `evaluate_stop` gate produces. Losing `pgdata` without a backup breaks the `issue ↔ branch (worktree_branch) ↔ run (agent_run_id)` traceability triple.
- `uploads` (MinIO) is where issue-attached evidence artifacts and screenshots live; it is the human-readable mirror of the content-addressed `output_hash` evidence the verifier captures.
- `CORS_ALLOWED_ORIGINS`, `API_KEY_RATE_LIMIT`, and `WEBHOOK_ALLOWED_IPS/HOSTS` directly govern how ASCP automation (MCP clients, hook-driven sync) talks to Plane: the API origin must be `http://localhost:8090`, automation must stay under `60/minute` per API key, and any inbound webhook from Plane to an internal control-plane service must be allow-listed.

This deployment is therefore treated with the same backup/upgrade/health rigor as any other stateful dependency of the gate — it is the operator's window into an otherwise headless autonomous loop.


## Integration Payloads — Plane ⇄ Spec-to-Evidence Control Plane

This section specifies the wire contract between **Plane** (the PM control plane, project `Agentic SDLC Control Plane` / identifier `ASCP`) and the **Spec-to-Evidence Coverage Control System** (the autonomous SDLC control plane running on Claude Code). Every payload here uses the **real Plane shapes** — the webhook envelope assembled in Plane's `webhook_send_task`, the `X-Plane-*` headers, the HMAC-SHA256 signing over `json.dumps(payload)`, and the Plane v1 REST surface (`/api/v1/workspaces/{ws}/projects/{proj}/work-items/`, `X-Api-Key` auth, `external_id` + `external_source` idempotent linkage).

Two directions:

| Direction | Trigger | Who consumes | Carrier |
|-----------|---------|--------------|---------|
| **(a) Inbound** — Plane → control plane | Human edits an `ASCP` work-item (creates a story, drags a card to a new state, comments, creates a cycle) | A FastAPI/Flask receiver (the *Plane ingress*) that translates a card event into a control-plane intent or `run_state` update | Plane webhook POST with `X-Plane-Event` / `X-Plane-Delivery` / `X-Plane-Signature` |
| **(b) Outbound** — control plane → Plane | A subagent or hook makes a deterministic state change (Initializer compiles a spec, Verifier flips `unproven → proven`, Stop hook blocks, HANDOFF) | Plane (the live PM board the human watches) | Plane v1 REST `POST`/`PATCH`/comment with `X-Api-Key` + `external_id`/`external_source` |

The **traceability triple** `issue ↔ branch ↔ run` (Req 6 / the `worktree_branch` + `agent_run_id` fields) is realized on the wire by stamping `external_id = <requirement_id>` and `external_source = "ascp-control-plane"` on every outbound work-item, so the same Plane card is the durable join key for a `feature_list.json` item, its git worktree branch, and its LLM `agent_run_id`.

---

### (a) Inbound webhook — Plane → control plane

#### Headers (exactly as Plane emits them)

Plane's `webhook_send_task` sets these headers on every delivery (verified against `apps/api/plane/bgtasks/webhook_task.py`):

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Type` | `application/json` | — |
| `User-Agent` | `Autopilot` | Plane's fixed UA string |
| `X-Plane-Event` | the event name, e.g. `issue`, `issue_comment`, `cycle` | top-level resource type |
| `X-Plane-Delivery` | a fresh `uuid4` per delivery | **idempotency key** — dedupe retries (Plane retries up to 5× with 600 s backoff) |
| `X-Plane-Signature` | `hmac_sha256(secret_key, json.dumps(payload)).hexdigest()` — present **only if** the webhook has a `secret_key` | authenticity / tamper-evidence |

> **Signing detail (load-bearing):** Plane signs `json.dumps(payload)` — Python's **default** separators (`", "` / `": "`) and **insertion order** of the payload dict, *not* a sorted-key canonical form. The verifier MUST recompute the HMAC over the **raw request body bytes as received**, never over a re-serialized dict, or the signature will not match.

#### Webhook envelope (the real `payload` dict)

Plane assembles exactly this envelope. The `event` is the resource, `action ∈ {create, update, delete}` (Plane maps `POST→create`, `PATCH/PUT→update`, `DELETE→delete`), `data` is the DRF-serialized resource, and `activity` carries the actor and the field-level diff.

```json
{
  "event": "issue",
  "action": "update",
  "webhook_id": "b3f1c0e2-9a44-4f7e-8c21-2d9e7a1b6f30",
  "workspace_id": "7c2e9a10-4d33-4b8a-9f51-1a6c8e2b4d77",
  "workspace_slug": "ascp",
  "data": { "...serialized resource...": "..." },
  "activity": {
    "id": "f0a9b8c7-1234-4abc-9def-001122334455",
    "actor": {
      "id": "9e8d7c6b-5a40-4031-8b22-aa11bb22cc33",
      "display_name": "Daniel Manzela",
      "email": "danielq1603@gmail.com"
    },
    "verb": "updated",
    "field": "state",
    "old_value": "Agent-Executing",
    "new_value": "In-Verification",
    "old_identifier": "5a1b...",
    "new_identifier": "6b2c...",
    "comment": "updated the state to In-Verification"
  }
}
```

#### Python HMAC-SHA256 verify snippet (raw-body verification, constant-time)

```python
# plane_ingress/verify.py
# Verifies an inbound Plane webhook exactly the way Plane signs it:
#   X-Plane-Signature == hmac_sha256(secret_key, RAW_REQUEST_BODY).hexdigest()
# Plane signs json.dumps(payload) (Python default separators + dict insertion
# order), so we MUST hash the raw bytes as received — never a re-serialized dict.

import hashlib
import hmac
import os

PLANE_WEBHOOK_SECRET = os.environ["PLANE_WEBHOOK_SECRET"]  # the webhook's secret_key


def verify_plane_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Return True iff the X-Plane-Signature header authenticates raw_body.

    raw_body          : the exact request body bytes (await request.body()).
    signature_header  : the value of the X-Plane-Signature header (hex digest).
    """
    if not signature_header:
        # A webhook with no secret_key sends no signature. Fail CLOSED:
        # the ASCP ingress REQUIRES a signed webhook (REQ-GATE-005 fail-closed).
        return False

    expected = hmac.new(
        PLANE_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,                       # raw bytes, NOT json.dumps(parsed_dict)
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison defeats timing attacks.
    return hmac.compare_digest(expected, signature_header)


# --- FastAPI receiver wiring (the Plane ingress endpoint) -------------------
# from fastapi import FastAPI, Request, Header, HTTPException
#
# app = FastAPI()
#
# @app.post("/webhooks/plane")
# async def plane_webhook(
#     request: Request,
#     x_plane_event: str = Header(...),
#     x_plane_delivery: str = Header(...),       # dedupe key (idempotency)
#     x_plane_signature: str | None = Header(default=None),
# ):
#     raw = await request.body()
#     if not verify_plane_signature(raw, x_plane_signature):
#         raise HTTPException(status_code=401, detail="bad signature")
#     if already_processed(x_plane_delivery):    # idempotent on X-Plane-Delivery
#         return {"status": "duplicate-ignored"}
#     payload = json.loads(raw)
#     route_event(x_plane_event, payload)        # dispatch by event+action
#     mark_processed(x_plane_delivery)
#     return {"status": "accepted"}
```

#### Mock inbound payloads

All four are complete deliveries (envelope + the real `data` serialization Plane produces). `workspace_slug` is `ascp`; the project is `ASCP`.

**1. `issue.created`** — a human creates a story on the `ASCP` board. The control plane reads `agent_role` + `requirement_id` custom fields and routes it to the Initializer for triage (`Backlog → Agent-Triaged`).

```json
{
  "event": "issue",
  "action": "create",
  "webhook_id": "b3f1c0e2-9a44-4f7e-8c21-2d9e7a1b6f30",
  "workspace_id": "7c2e9a10-4d33-4b8a-9f51-1a6c8e2b4d77",
  "workspace_slug": "ascp",
  "data": {
    "id": "11112222-3333-4444-5555-666677778888",
    "name": "Stop hook blocks termination while any in-scope item is unproven",
    "description_html": "<p>REQ-GATE-002 — fail-closed completion gate.</p>",
    "priority": "urgent",
    "state": "0a1b2c3d-4e5f-6071-8293-a4b5c6d7e8f0",
    "sequence_id": 42,
    "project": "c0ffee00-1111-2222-3333-444455556666",
    "workspace": "7c2e9a10-4d33-4b8a-9f51-1a6c8e2b4d77",
    "label_ids": ["aa11bb22-cc33-dd44-ee55-ff6600778899"],
    "assignee_ids": [],
    "external_id": null,
    "external_source": null,
    "created_at": "2026-06-16T09:14:03.221Z",
    "updated_at": "2026-06-16T09:14:03.221Z"
  },
  "activity": {
    "id": "a1a1a1a1-b2b2-4c3c-9d4d-e5e5e5e5e5e5",
    "actor": {
      "id": "9e8d7c6b-5a40-4031-8b22-aa11bb22cc33",
      "display_name": "Daniel Manzela",
      "email": "danielq1603@gmail.com"
    },
    "verb": "created",
    "field": null,
    "old_value": null,
    "new_value": null,
    "comment": "created the work item"
  }
}
```

**2. `issue.updated` (state change `Agent-Executing → In-Verification`)** — the human (or an outbound control-plane PATCH echoed back) drags the card. The diff lives in `activity` (`field: "state"`, `old_value`/`new_value` are the human-readable state names; `old_identifier`/`new_identifier` are the state UUIDs). The ingress maps `new_value` to a `run_state` phase and may invoke the Verifier subagent.

```json
{
  "event": "issue",
  "action": "update",
  "webhook_id": "b3f1c0e2-9a44-4f7e-8c21-2d9e7a1b6f30",
  "workspace_id": "7c2e9a10-4d33-4b8a-9f51-1a6c8e2b4d77",
  "workspace_slug": "ascp",
  "data": {
    "id": "11112222-3333-4444-5555-666677778888",
    "name": "Stop hook blocks termination while any in-scope item is unproven",
    "priority": "urgent",
    "state": "6b2c0d1e-2f30-4415-9a6b-7c8d9e0f1a2b",
    "sequence_id": 42,
    "project": "c0ffee00-1111-2222-3333-444455556666",
    "workspace": "7c2e9a10-4d33-4b8a-9f51-1a6c8e2b4d77",
    "external_id": "REQ-GATE-002",
    "external_source": "ascp-control-plane",
    "updated_at": "2026-06-16T11:02:51.880Z"
  },
  "activity": {
    "id": "f0a9b8c7-1234-4abc-9def-001122334455",
    "actor": {
      "id": "9e8d7c6b-5a40-4031-8b22-aa11bb22cc33",
      "display_name": "Daniel Manzela",
      "email": "danielq1603@gmail.com"
    },
    "verb": "updated",
    "field": "state",
    "old_value": "Agent-Executing",
    "new_value": "In-Verification",
    "old_identifier": "5a1b9c8d-7e6f-4051-8243-1a2b3c4d5e6f",
    "new_identifier": "6b2c0d1e-2f30-4415-9a6b-7c8d9e0f1a2b",
    "comment": "updated the state to In-Verification"
  }
}
```

**3. `issue_comment.created`** — a human posts a review note (or injects missing context). The ingress can parse a `/handoff`, `/amend`, or `notes:` directive out of `comment_html` and write it into `plan-approved.json.notes` or trigger a `requirement_versions` amendment (Req 18.2 / Req 22).

```json
{
  "event": "issue_comment",
  "action": "create",
  "webhook_id": "b3f1c0e2-9a44-4f7e-8c21-2d9e7a1b6f30",
  "workspace_id": "7c2e9a10-4d33-4b8a-9f51-1a6c8e2b4d77",
  "workspace_slug": "ascp",
  "data": {
    "id": "dddd1111-eeee-2222-ffff-333344445555",
    "comment_html": "<p>Confirm the HANDOFF carve-out: at cap with violation_count&gt;0 the Stop hook must ALLOW (exit 0). /amend REQ-GATE-002</p>",
    "comment_stripped": "Confirm the HANDOFF carve-out... /amend REQ-GATE-002",
    "issue": "11112222-3333-4444-5555-666677778888",
    "project": "c0ffee00-1111-2222-3333-444455556666",
    "workspace": "7c2e9a10-4d33-4b8a-9f51-1a6c8e2b4d77",
    "actor": "9e8d7c6b-5a40-4031-8b22-aa11bb22cc33",
    "external_id": null,
    "external_source": null,
    "created_at": "2026-06-16T11:18:09.402Z"
  },
  "activity": {
    "id": "c3c3c3c3-d4d4-4e5e-9f6f-707070707070",
    "actor": {
      "id": "9e8d7c6b-5a40-4031-8b22-aa11bb22cc33",
      "display_name": "Daniel Manzela",
      "email": "danielq1603@gmail.com"
    },
    "verb": "created",
    "field": "comment",
    "old_value": null,
    "new_value": "Confirm the HANDOFF carve-out...",
    "comment": "created a comment"
  }
}
```

**4. `cycle.created`** — a human opens a delivery phase as a Plane cycle (e.g. `Phase 0 — Spine`). The ingress maps the cycle to a control-plane phase boundary and may seed `feature_list.json` filtering / scope for that phase.

```json
{
  "event": "cycle",
  "action": "create",
  "webhook_id": "b3f1c0e2-9a44-4f7e-8c21-2d9e7a1b6f30",
  "workspace_id": "7c2e9a10-4d33-4b8a-9f51-1a6c8e2b4d77",
  "workspace_slug": "ascp",
  "data": {
    "id": "9999aaaa-8888-bbbb-7777-ccccdddd6666",
    "name": "Phase 0 — Spine",
    "description": "feature_list.json + Stop hook + verifier subagent + worktrees + OPA gate + Playwright",
    "start_date": "2026-06-16",
    "end_date": "2026-06-30",
    "project": "c0ffee00-1111-2222-3333-444455556666",
    "workspace": "7c2e9a10-4d33-4b8a-9f51-1a6c8e2b4d77",
    "owned_by": "9e8d7c6b-5a40-4031-8b22-aa11bb22cc33",
    "external_id": "PHASE-0",
    "external_source": "ascp-control-plane",
    "created_at": "2026-06-16T08:00:00.000Z"
  },
  "activity": {
    "id": "e7e7e7e7-f8f8-4949-8a0a-1b1b1b1b1b1b",
    "actor": {
      "id": "9e8d7c6b-5a40-4031-8b22-aa11bb22cc33",
      "display_name": "Daniel Manzela",
      "email": "danielq1603@gmail.com"
    },
    "verb": "created",
    "field": null,
    "old_value": null,
    "new_value": null,
    "comment": "created the cycle"
  }
}
```

---

### (b) Outbound REST — control plane → Plane

The control plane writes back to the live `ASCP` board over the Plane **v1 API**. Every call authenticates with the `X-Api-Key` header (Plane's API-token auth, header name `X-Api-Key`, verified in `api/middleware/api_authentication.py`) and uses `external_id` + `external_source` for **idempotent linkage** so re-runs never duplicate cards.

#### Endpoints, auth, and the idempotency contract

| Operation | Method + path (`<host>` = your self-host, e.g. `https://plane.ascp.internal`) |
|-----------|-------------------------------------------------------------------------------|
| Create a work-item | `POST  /api/v1/workspaces/{ws}/projects/{proj}/work-items/` |
| Update a work-item | `PATCH /api/v1/workspaces/{ws}/projects/{proj}/work-items/{pk}/` |
| Upsert by external id | `PUT   /api/v1/workspaces/{ws}/projects/{proj}/work-items/` (body carries `external_id`+`external_source`) |
| Resolve pk from external id | `GET   /api/v1/workspaces/{ws}/projects/{proj}/work-items/?external_id=...&external_source=...` |
| Post a comment | `POST  /api/v1/workspaces/{ws}/projects/{proj}/work-items/{issue_id}/comments/` |

**Headers on every call:**

```
X-Api-Key: plane_api_<your-token>
Content-Type: application/json
```

**Idempotent linkage (real Plane behavior, verified in `api/views/issue.py`):**

- On `POST` with `external_id` + `external_source`, if a work-item with that **pair already exists** Plane returns **`409 Conflict`** with body `{"error": "Issue with the same external id and external source already exists", "id": "<existing-uuid>"}`. The control plane treats 409 as **"already linked"**, reads `id`, and switches to `PATCH` — so a replayed slice never creates a duplicate card.
- `GET ?external_id=&external_source=` resolves the Plane `pk` from the control-plane key (`requirement_id`) without storing the UUID locally.
- Canonical key for ASCP: `external_source = "ascp-control-plane"`, `external_id = <requirement_id>` (e.g. `REQ-GATE-002`) for work-items; `external_id = "<requirement_id>:evidence:<output_hash_short>"` for Evidence_Record comments (so the same evidence is posted once).

#### Mock outbound JSON

**1. Create a story (Initializer emits a coverage item → a `Backlog` card).**

```http
POST /api/v1/workspaces/ascp/projects/c0ffee00-1111-2222-3333-444455556666/work-items/
X-Api-Key: plane_api_7Qx...redacted
Content-Type: application/json
```
```json
{
  "name": "REQ-GATE-002 — Stop hook blocks termination while any in-scope item is unproven",
  "description_html": "<p><b>EARS (Unwanted):</b> IF the agent attempts to terminate as COMPLETE WHILE any in-scope requirement is unproven, THEN the Stop_Hook SHALL block termination.</p><p>Acceptance: with one unproven in-scope item and no HANDOFF trigger active, the Stop hook exits 2.</p>",
  "priority": "urgent",
  "state": "0a1b2c3d-4e5f-6071-8293-a4b5c6d7e8f0",
  "labels": ["aa11bb22-cc33-dd44-ee55-ff6600778899", "bb22cc33-dd44-ee55-ff66-007788990011"],
  "external_id": "REQ-GATE-002",
  "external_source": "ascp-control-plane"
}
```
*`state` UUID = the `Backlog` state in this project; `labels` = the resolved UUIDs of `agent:initializer` + `gate:stop`. On a replayed run this same POST returns `409` with the existing card id — the control plane then PATCHes instead.*

**2. Transition state (`Spec-Verified → Plan-Approved`, after the human writes `plan-approved.json`).**

```http
PATCH /api/v1/workspaces/ascp/projects/c0ffee00-1111-2222-3333-444455556666/work-items/11112222-3333-4444-5555-666677778888/
X-Api-Key: plane_api_7Qx...redacted
Content-Type: application/json
```
```json
{
  "state": "7c3d1e2f-3041-4526-ab7c-8d9e0f1a2b3c"
}
```
*`state` UUID = the `Plane`-side state whose name is `Plan-Approved`. State transitions are a single `state` field PATCH; Plane validates the target state belongs to the project (else `400 "State is not valid please pass a valid state_id"`).*

**3. Post an `Evidence_Record` comment (Verifier captures proof on `unproven → proven`).**

```http
POST /api/v1/workspaces/ascp/projects/c0ffee00-1111-2222-3333-444455556666/work-items/11112222-3333-4444-5555-666677778888/comments/
X-Api-Key: plane_api_7Qx...redacted
Content-Type: application/json
```
```json
{
  "comment_html": "<h4>Evidence_Record — REQ-GATE-002 → proven</h4><ul><li><b>test_file:</b> tests/hooks/test_stop_hook.py</li><li><b>test_name:</b> test_blocks_when_unproven_and_no_handoff</li><li><b>output_hash:</b> sha256:3b1f9a0c5e2d4471a8c6f0d2e9b7a13c4d5e6f708192a3b4c5d6e7f8091a2b3c4</li><li><b>collected_at:</b> 2026-06-16T11:40:12Z</li><li><b>actor_agent:</b> verifier.md</li><li><b>evidence_kind:</b> unit</li><li><b>worktree_branch:</b> slice/REQ-GATE-002</li><li><b>agent_run_id:</b> run_01JA8Z3K7M2QF4WX</li></ul>",
  "external_id": "REQ-GATE-002:evidence:3b1f9a0c",
  "external_source": "ascp-control-plane"
}
```
*The four required Evidence_Record fields (`test_file`, `test_name`, `output_hash`, `collected_at`) plus the provenance fields (`actor_agent`, `evidence_kind`) are rendered into the comment. `external_id` carries the `output_hash` prefix so the same evidence is posted exactly once. The `worktree_branch` + `agent_run_id` complete the traceability triple on the card.*

**4. Attach labels (classification — type + agent owner + gate).**

Labels are set on the work-item by their UUIDs (resolve names → UUIDs once via `GET .../labels/`, then PATCH the full desired set; Plane replaces the label set on update):

```http
PATCH /api/v1/workspaces/ascp/projects/c0ffee00-1111-2222-3333-444455556666/work-items/11112222-3333-4444-5555-666677778888/
X-Api-Key: plane_api_7Qx...redacted
Content-Type: application/json
```
```json
{
  "labels": [
    "aa11bb22-cc33-dd44-ee55-ff6600778899",
    "bb22cc33-dd44-ee55-ff66-007788990011",
    "cc33dd44-ee55-ff66-0077-889900112233"
  ]
}
```
*Resolved set = `agent:tester` (the Verifier writes evidence) + `gate:stop` + `type:functional`. To CREATE a label idempotently, `POST .../labels/` with `{"name": "gate:stop", "color": "#E11D48", "external_id": "label:gate:stop", "external_source": "ascp-control-plane"}` — the label serializer accepts `external_id`/`external_source`, so label provisioning is also replay-safe.*

---

### (c) Agent → Plane state-transition contract

This is the **authoritative map of which `agent_role` is permitted to drive which Plane state transition**, derived from the subagent permission model (design.md Subagent Definitions), the hook wiring, and the shared control vocabulary. Every outbound transition is a `state` PATCH (section b.2). The control plane is the **only** writer of agent-driven transitions; a human may move a card freely, and the inbound webhook (section a) echoes that back.

Legend for `agent_role` (shared vocabulary): `initializer | implementer | verifier | research | human`.

| # | Transition (state → state) | Plane `state` group | Driven by `agent_role` | Trigger / gate condition | Labels stamped on transition |
|---|----------------------------|---------------------|------------------------|--------------------------|------------------------------|
| 1 | `Backlog` → `Agent-Triaged` | backlog → unstarted | **initializer** | Card classified; `agent_role` + `requirement_id` assigned | `agent:initializer`, `phase:0` |
| 2 | `Agent-Triaged` → `Spec-Compiling` | unstarted → started | **initializer** | EARS compiled; `spec_validator.py` (Z3) running | `agent:initializer` |
| 3 | `Spec-Compiling` → `Spec-Verified` | started → started | **initializer** | `violation_count == 0`; `feature_list.json` emitted (all `unproven`) | `agent:initializer` |
| 4 | `Spec-Compiling` → `HANDOFF` | started → cancelled | **initializer** | Spec pass cap (7) hit OR `violation_count` did not strictly decrease (Property 15) | `handoff`, `priority:blocking` |
| 5 | `Spec-Verified` → `Plan-Approved` | started → started | **human** | Human writes `plan-approved.json` (SHA-bound to `feature_list.json`); the control plane PATCHes the card on the `plan-approved.json` write event | `human:review` |
| 6 | `Plan-Approved` → `Agent-Executing` | started → started | **implementer** | PreToolUse plan-gate passes; Implementer creates the slice worktree (`worktree_branch` set) | `agent:coder`, `priority:high` |
| 7 | `Agent-Executing` → `In-Verification` | started → started | **implementer** → **verifier** | Implementer returns its one atomic commit (NO Evidence_Record); Verifier is invoked | `agent:tester` |
| 8 | `In-Verification` → `Human-Review` | started → started | **verifier** | All 5 layers pass; Evidence_Record captured; item flipped `unproven → proven`; PR opened | `agent:tester`, `human:review` |
| 9 | `In-Verification` → `Failed` | started → cancelled | **verifier** | Verification failed OR a `WIRING` symbol is unreachable → item `unproven → failed`; evidence withheld | `failed`, `type:wiring` (when WIRING) |
| 10 | `Human-Review` → `Done` | started → completed | **human** (gate: Stop + OPA + CI) | PR approved AND Stop hook allows (all in-scope `proven`) AND OPA zero-evidence query returns 0 rows AND CI green | `gate:completion` |
| 11 | *any started* → `Blocked` | started → cancelled | **implementer / verifier** | A gate blocked (exit 2): unproven dependency, failed integrity/approval, secret detected, append-only violation | `blocked`, `priority:blocking` |
| 12 | *any* → `HANDOFF` | * → cancelled | **implementer** | Iteration cap (25 turns) OR token budget (1,000,000) OR no-progress (N=3) OR retry budget (3) reached | `handoff`, `priority:blocking` |
| 13 | `research` draft cycle | (no work-item state change) | **research** | New product class detected; drafts `baselines/<class>.md`; comment-only on the linked card until human-approved | `agent:research` |
| 14 | `proven` → re-entry (`Done`/`Human-Review` → `Agent-Executing`) | completed/started → started | **human** then **implementer** | Requirement amendment (Req 22): a `requirement_versions` insert gates the `proven → unproven` flip; card re-enters execution | `agent:coder` (human authors the amendment) |

#### Writer-authority invariants (mirroring the deterministic-gate model)

These are the non-negotiable rules the outbound writer enforces — they mirror the control plane's own gates so the Plane board can never assert a state the gates would reject:

1. **Only the `verifier` may drive a card into `Human-Review` or `Failed`.** The `implementer` never self-verifies (Property 24 / SubagentStop blocks an evidence-bearing result whose `actor_agent == implementer.md`). An outbound `In-Verification → Human-Review` PATCH whose originating `agent_role` is `implementer` is refused by the writer.
2. **`Done` is never written by an agent.** Transition #10 is gated by the *conjunction* Stop hook (exit 0) ∧ OPA zero-evidence (0 rows) ∧ CI required check. The writer posts the `Done` PATCH **only** after it observes all three pass; ambiguous state resolves to `Blocked`, never `Done` (REQ-GATE-005 fail-closed).
3. **`HANDOFF` ≠ `Done`.** Both are Plane `cancelled`-group states with distinct names. A card at `HANDOFF` has in-scope items still `unproven` *by design* (cap/budget/no-progress reached) and is **never** marked `Done` — they are mutually exclusive terminal states (Z3 CHECK-3).
4. **Human-only edges are never agent-written.** `Spec-Verified → Plan-Approved` (#5) and the amendment re-entry (#14) require a human artifact (`plan-approved.json` / a `requirement_versions` insert). The writer only echoes these to Plane *after* the artifact exists; it never originates them.
5. **Every transition is idempotent and audited.** Each PATCH targets the card resolved by `external_id = <requirement_id>` + `external_source = "ascp-control-plane"`; the corresponding gate decision is appended to `gate_audit_log` (REQ-AUDIT-001) with `actor_agent` + `requirement_id`, so the Plane state and the tamper-evident audit chain agree.

---

### Source grounding

All Plane shapes above are verified against the upstream `makeplane/plane` source, not invented:

- **Webhook envelope + headers + HMAC** — `apps/api/plane/bgtasks/webhook_task.py` (`webhook_send_task`): the `payload` dict is exactly `{event, action, webhook_id, workspace_id, workspace_slug, data, activity}`; headers `X-Plane-Delivery` (`uuid4`), `X-Plane-Event`, `X-Plane-Signature = hmac.new(secret_key, json.dumps(payload), sha256).hexdigest()`; `action` mapped `POST→create / PATCH,PUT→update / DELETE→delete`.
- **v1 REST routes** — `apps/api/plane/api/urls/work_item.py`: the modern `.../work-items/` prefix, including `.../work-items/{issue_id}/comments/`.
- **Auth header** — `apps/api/plane/api/middleware/api_authentication.py`: `auth_header_name = "X-Api-Key"`.
- **Idempotent linkage** — `apps/api/plane/api/views/issue.py`: `external_id` + `external_source` POST returns `409 Conflict` (`"Issue with the same external id and external source already exists"`, with the existing `id`); `GET ?external_id=&external_source=` lookup; PUT upsert-by-external-id. `external_id`/`external_source` accepted on issue, comment (`api/serializers/issue.py` comment serializer), and label serializers.
- **State validation** — `IssueSerializer.validate`: a `state` that is not in the project raises `"State is not valid please pass a valid state_id"`; `labels` are replaced by UUID list on update.

The 12 ASCP states, the 10 custom fields, and the 22 labels referenced above are the **shared control vocabulary** verbatim; only their per-project UUIDs (illustrative here) are assigned at workspace-provisioning time.


> **Grounding.** Authored against the canonical reconciled spec — `requirements.md` (32 EARS requirements), `design.md` (32 correctness properties, 8 Postgres tables, 6 Claude-Code hooks, 4 subagents, `evaluate_stop`), `tasks.md` (57 tasks). Every trigger, guard, and side-effect below traces to a named hook, table, or requirement in those files. The 12 custom states are the canonical Plane workflow states; `agent_role` ∈ {`initializer`, `implementer`, `verifier`, `research`, `human`}; the governing invariant is **fail-closed: deterministic gates (hooks/CI/OPA) decide completeness from verifiable facts; ambiguous states resolve to blocked, never passed (REQ-GATE-005).**

---

## 1. STATE-TRANSITION COVERAGE

### 1.1 State-group key

The 12 Plane states map to the run lifecycle as follows. `Done` = canonical `COMPLETE` (all in-scope items `proven` + all gates pass). `HANDOFF` is a **terminal state distinct from `Done`** (cap/budget/no-progress; `run_state.status='handoff'`). `Blocked` is a gate exit-2 deny (recoverable). `Failed` is verification-failed with evidence withheld (`status='failed'`; recoverable via amendment/retry).

| Plane state | Plane category | `run_state` / coverage correlate |
|---|---|---|
| Backlog | backlog | no `run_state` row yet; intent only |
| Agent-Triaged | unstarted | `agent_role` + `requirement_id` assigned; `phase='spec'` |
| Spec-Compiling | started | `phase='spec'`, `spec_pass_count` advancing, `violation_count` recomputed each pass |
| Spec-Verified | started | `violation_count==0`; `feature_list.json` emitted (all `unproven`) |
| Plan-Approved | started | `plan-approved.json` present, `feature_list_sha`-bound; `phase→'implementation'` |
| Agent-Executing | started | one slice in an isolated git worktree; `iteration_count`/`retry_count` advancing |
| In-Verification | started | Verifier running 5-layer checks; assembling `Evidence_Record` |
| Human-Review | started | PR open + required human reviewer gate |
| Done | completed | `status='complete'`; Stop+OPA+CI all green |
| HANDOFF | cancelled | `status='handoff'`; cap/budget/no-progress |
| Blocked | cancelled | gate exit 2 (unproven dep / integrity / approval / secret) |
| Failed | cancelled | coverage item `status='failed'`; evidence withheld |

### 1.2 Allowed transitions — full table

Each row is one legal edge. **Side-effect** names the concrete Plane field write **and** the agent/Postgres/hook consequence. **EARS** gives the governing requirement in EARS form; unwanted-behaviour EARS rows are flagged **[UNWANTED]**.

| # | From → To | Trigger | Acting `agent_role` | Plane + agent/Postgres side-effect | EARS requirement |
|---|---|---|---|---|---|
| T1 | Backlog → Agent-Triaged | Operator drops intent into the run; `initializer` classifies it | initializer | Set `agent_role`, `requirement_id`; `run_state` row created (`status='running'`, `phase='spec'`); label `phase:0` | **Ubiquitous (REQ-SPEC-001):** THE initializer SHALL classify intake into atomic requirements, each with a unique `requirement_id`, an EARS-pattern statement, a priority, and ≥1 machine-checkable acceptance criterion. |
| T2 | Agent-Triaged → Spec-Compiling | initializer begins an elaboration pass; runs `spec_validator.py` (Z3) | initializer | `run_state.phase='spec'`; `spec_pass_count += 1`; `violation_count := validate_spec(...)['violation_count']`; `prev_violation_count := prior`; label `gate:stop` | **Event-driven (REQ-SPEC-020 / 4.1):** WHEN a requirement is authored/modified, THE initializer SHALL validate it with the non-LLM `spec_validator.py` returning `{contradictions, ambiguities, uncovered, violation_count}`; the authoring agent SHALL have no vote in the verdict. |
| T3 | Spec-Compiling → Spec-Compiling (loop) | A pass completes with `violation_count > 0` AND strictly less than `prev_violation_count` AND `spec_pass_count < 7` | initializer | Stop hook blocks termination (exit 2), returns enumerated violations; `spec_pass_count += 1`; loop re-enters | **Unwanted [UNWANTED] (REQ-SPEC-021 / 4.2):** WHEN the spec agent attempts to end its turn AND `violation_count > 0`, THEN THE Stop_Hook SHALL block termination (exit 2) and return the enumerated violations — on passes *before* the hard cap only. |
| T4 | Spec-Compiling → Spec-Verified | An elaboration pass yields `violation_count == 0` | initializer | Emit validated spec + `feature_list.json` (every item `status='unproven'`, `in_scope=true`); request human plan approval; Stop hook ALLOWS (exit 0); label `type:functional`/`type:nfr`/`type:wiring` per item | **Event-driven (REQ-SPEC-024 / 4.5):** WHEN `violation_count == 0`, THE System SHALL emit the validated spec and `feature_list.json` and request human plan approval before any implementation begins. |
| T5 | Spec-Verified → Plan-Approved | Human reviews spec+coverage model in plan mode and writes `plan-approved.json` | human | Write `plan-approved.json` (`feature_list_sha`-bound, `notes` missing-context injection); `phase→'implementation'`; initializer reads `notes` into `run_state` next session; label `human:review` cleared, `phase:1` | **Event-driven (REQ-HITL-002 / 18.2):** WHEN the validated spec and `feature_list.json` are ready, THE System SHALL present them in plan mode for human approval and missing-context injection before unlocking implementation. |
| T6 | Plan-Approved → Agent-Executing | PreToolUse plan-gate passes (`plan-approved.json` exists AND its `feature_list_sha` == canonical projection SHA) AND PreToolUse scope-gate passes (no prior-slice item `unproven`) | implementer | `git worktree add` for the slice (`worktree_branch` set); select lowest-`priority` `unproven` item whose deps are all `proven`; `iteration_count` resets; `agent_run_id` recorded (issue↔branch↔run triple) | **State-driven (REQ-EXEC-001/004):** WHILE a `plan-approved.json` with a matching `feature_list_sha` exists AND no prior-slice item is `unproven`, THE PreToolUse_Hook SHALL permit implementation Write/Edit on exactly one highest-priority `unproven` item in a dedicated worktree. |
| T7 | Agent-Executing → In-Verification | implementer produces one atomic commit (requirement ID in trailer) and hands off; PostToolUse feedback clean enough to proceed | implementer → verifier | Atomic commit with `requirement_id` trailer; `traceability_links` rows (commit/implementation) inserted; implementer returns with **no** `Evidence_Record`; `verifier` invoked as a separate subagent | **Event-driven (REQ-EXEC-003 / REQ-VERIFY-002):** WHEN a slice's atomic commit is produced, THE System SHALL invoke the independent verifier (which did not write the code) to evaluate it; the implementer SHALL NOT verify its own output. |
| T8 | In-Verification → Human-Review | All 5 verification layers pass; complete `Evidence_Record` assembled; item flipped `unproven → proven` | verifier | Flip `feature_list.json` item `status='proven'` + attach 4-field `Evidence_Record` (`test_file`, `test_name`, `output_hash=sha256:<64hex>`, `collected_at`); `evidence_records` row (`actor_agent='verifier.md'`); SubagentStop validates schema (exit 0); open PR | **State-driven (REQ-VERIFY-003 / 5.3):** WHILE all five verification layers pass AND a complete 4-field Evidence_Record is attached, THE verifier SHALL set the item `proven` and the System SHALL advance the slice to human PR review. |
| T9 | Human-Review → Done | Human reviewer approves PR; Stop hook sees zero `unproven` in-scope items; OPA zero-evidence query returns 0 rows; all required CI checks green | human (+ verifier/gates) | Merge to protected branch; `run_state.status='complete'`; SLSA provenance signed; `gate_audit_log` allow entry; label `gate:completion` satisfied | **State-driven (REQ-GATE-001):** WHILE zero in-scope items are `unproven` AND all tests pass AND every Evidence_Record is present AND a human PR review is recorded, THE Completion_Gate SHALL permit `Done`; the verdict is computed solely from verifiable facts. |
| T10 | Agent-Executing → Failed | A verification check is dead/unreachable, or a WIRING symbol is unreachable from any real execution path | verifier | Flip item `unproven → failed` in `feature_list.json`; evidence **withheld** (no Evidence_Record); `coverage_items.status='failed'`; label `failed`, `type:wiring` (if WIRING) | **Unwanted [UNWANTED] (REQ-EXEC-011 / 8.2):** IF a handler, route, job, or callback exists but is unreachable from any real execution path, THEN THE verifier SHALL mark the corresponding WIRING item `failed` and SHALL NOT emit `proven`. |
| T11 | In-Verification → Failed | A layer (structural/semantic/behavioral/security/perf+a11y) fails; verification cannot produce passing evidence | verifier | Flip item `unproven → failed`; withhold evidence; return specific failures to the implementer loop; label `failed` | **Unwanted [UNWANTED] (REQ-VERIFY-001):** IF any of the five verification layers fails for a slice, THEN THE verifier SHALL withhold the Evidence_Record and mark the item `failed` rather than `proven`. |
| T12 | Failed → Agent-Executing | implementer retries the slice (within retry budget) | implementer | Flip item `failed → unproven` (no Evidence_Record required for this edge); `retry_count += 1`; new attempt in the worktree | **Event-driven (REQ-COV-008 / 5.8):** WHEN a slice is retried after a failed check, THE System SHALL permit `failed → unproven` and re-attempt; only a transition *into* `proven` requires a complete Evidence_Record. |
| T13 | Human-Review → Agent-Executing | Human reviewer **rejects** the PR (change requested) | human → implementer | PR left unmerged; item remains `unproven` (evidence not accepted as final); implementer re-enters the slice; `retry_count += 1`; label `human:review` retained | **Unwanted [UNWANTED] (REQ-HITL-003):** IF the human PR reviewer rejects the change, THEN THE System SHALL return the slice to `Agent-Executing` for rework and SHALL NOT merge to the protected branch until a required reviewer approves. |
| T14 | Agent-Executing → HANDOFF | `iteration_count >= 25` (per-slice turn cap) | implementer (Stop hook decides) | `run_state.status='handoff'`, `reason='cap-reached'`; Stop hook ALLOWS termination (exit 0); emit HANDOFF summary; label `handoff` | **Unwanted [UNWANTED] (REQ-LOOP-001/005):** IF the per-slice iteration cap (DEFAULT 25 turns) is reached, THEN THE System SHALL terminate to HANDOFF (exit 0, ALLOW) — a terminal state distinct from `Done` — and SHALL NOT mark the deliverable complete. |
| T15 | Agent-Executing → HANDOFF | `token_cost_usd >= TOKEN_BUDGET` (DEFAULT 1,000,000 tokens/slice) | implementer (Stop hook decides) | `run_state.status='handoff'`, `reason='budget-exceeded'`; exit 0; HANDOFF summary; label `handoff` | **Unwanted [UNWANTED] (REQ-LOOP-002):** IF the per-slice cost/token budget is reached, THEN THE System SHALL terminate to HANDOFF and SHALL NOT mark the deliverable complete. |
| T16 | Agent-Executing → HANDOFF | No-progress predicate true: zero items flipped `unproven→proven` AND zero commits across the last N=3 consecutive slices | implementer (Stop hook decides) | `run_state.status='handoff'`, `reason='no-progress'`; `no_progress_n >= 3`; exit 0; HANDOFF summary; label `handoff` | **Unwanted [UNWANTED] (REQ-LOOP-002 no-progress):** IF zero coverage items are proven AND zero commits are produced across N=3 consecutive slices simultaneously, THEN THE System SHALL terminate to HANDOFF, never `COMPLETE`. |
| T17 | Spec-Compiling → HANDOFF | At hard pass cap (`spec_pass_count >= 7`) with `violation_count > 0`, OR a pass fails to strictly reduce `violation_count` | initializer (Stop hook decides) | `run_state.status='handoff'`; Stop hook ALLOWS (exit 0) — **lex specialis** overriding the T3 exit-2 block at the cap; surface remaining violations; label `handoff` | **Unwanted [UNWANTED] (REQ-LOOP-005 / 4.3/4.4/4.6):** IF the spec-completion loop reaches its 7-pass cap with `violation_count > 0`, OR a pass does not strictly reduce `violation_count`, THEN THE System SHALL halt to human HANDOFF (exit 0) — this HANDOFF takes precedence over the criterion-4.2 Stop-block at the cap. |
| T18 | Agent-Executing → HANDOFF | `retry_count >= 3` (per-slice retry budget exhausted) | implementer | `run_state.status='handoff'`, `reason='retry-exhausted'`; graceful failure; HANDOFF summary; label `handoff` | **Unwanted [UNWANTED] (REQ-LOOP-003 / 14.3):** IF a slice exhausts its retry budget (DEFAULT 3), THEN THE System SHALL fail gracefully and hand off to a human rather than retrying indefinitely. |
| T19 | Plan-Approved → Blocked | First Write/Edit of a **resumed** session while `run_state.resume_integrity_ok == false` (recorded vs recomputed state-hash mismatch) | implementer (PreToolUse integrity guard) | PreToolUse exit 2; `run_state.status` effectively blocked at first write; require operator reconciliation; `gate_audit_log` block entry; label `blocked` | **Unwanted [UNWANTED] (REQ-STATE-005 / 23.1):** IF a session resumes AND the resumed-state hash does not match the durable recorded hash, THEN THE System SHALL block the run from proceeding (exit 2) and require operator reconciliation. |
| T20 | Agent-Executing → Blocked | A PreToolUse gate denies: missing/stale `plan-approved.json` (SHA mismatch), prior-slice item `unproven`, protected-artifact/destructive op, or a secret in prompt/span/URL/arg | implementer (PreToolUse sub-gates) | PreToolUse exit 2; write prevented before execution; `gate_audit_log` block entry (event/tool/reason/`requirement_id`/`actor_agent`); label `blocked`, `gate:security` (secret case) | **Unwanted [UNWANTED] (REQ-STEER-002/003, REQ-EXEC-005, REQ-HITL-001, REQ-SEC-005):** IF a tool call lacks an approved plan, targets a protected/destructive artifact, starts a slice while a prior item is `unproven`, or would carry a secret, THEN THE PreToolUse_Hook SHALL block it before execution (exit 2). |
| T21 | In-Verification → Blocked | OPA/Conftest zero-evidence query returns ≥1 row at merge, OR audit-chain verify fails, OR a required CI check (SAST/secrets/coverage/DAST/eval) fails | verifier/CI gates | Merge denied; `run_state` not advanced to `complete`; ambiguous → blocked (fail-closed); `gate_audit_log` / check-run history records the block; label `blocked` | **Unwanted [UNWANTED] (REQ-GATE-003/005):** IF a merge is attempted WHILE any approved requirement has zero passing evidence OR any required gate is red, THEN the OPA/CI gate SHALL fail the merge; ambiguous states SHALL resolve to blocked, not passed. |
| T22 | Blocked → Agent-Executing | Blocking condition cleared (operator reconciliation, fresh approval, removed secret, prior item proven) | human / implementer | `resume_integrity_ok→true` via `state_integrity.py --reconcile` (integrity case) or new `plan-approved.json` (approval case); guard releases; `gate_audit_log` allow entry on re-attempt | **Event-driven (REQ-STATE-005 / 23.2 reconcile):** WHEN the operator performs reconciliation (re-records the durable hash / re-approves / removes the violation), THE System SHALL flip the blocking flag true and release the PreToolUse gate for the next write. |
| T23 | Failed → Agent-Executing (amendment) | Requirement amended after approval; `requirement_versions` row inserted; item re-entered `unproven` | human (+ initializer) | `requirement_versions` insert (prior text, new text, author, timestamp, rationale); item `proven→unproven` permitted **only** with the amendment row; `feature_list.json` item evidence cleared; if id/type/AC changed, `feature_list_sha` re-blocks → re-approval | **Event-driven (REQ-COV-007 / 22.1):** WHEN a requirement is amended after approval, THE System SHALL record a `requirement_versions` row, re-enter the coverage item as `unproven`, and SHALL NOT permit COMPLETE while any amended item is un-reproven. |
| T24 | HANDOFF → Agent-Triaged / Agent-Executing | Operator resumes a handed-off run after manual intervention | human | New session; `is_resume=true`; SessionStart recomputes state hash; integrity guard governs first write (→ T19/T22 path); `run_state.status='running'` restored | **Event-driven (REQ-STATE-003 / 21.1):** WHEN an operator resumes a HANDOFF run, THE SessionStart_Hook SHALL restore git status, progress file, and coverage model so the resumed session re-orients deterministically. |
| T25 | (any active state) → Blocked | Operator sets a `kill.<capability>` flag, OR `flagd` is unreachable | human (Delivery Owner / Operator) | Gated capability **disabled within ≤30 s** without process restart (fail-closed if `flagd` unreachable); `gate_audit_log` entry (operator, reason, `requirement_id`) + OTel gate-decision event; label `blocked`, `gate:security` | **Event-driven (REQ-CTRL-001 / 32.2):** WHEN a kill-switch flag is set (or `flagd` is unreachable), THEN the affected agent capability SHALL be disabled within the polling interval (≤30 s) without a process restart; an unreachable flag source fails closed (disabled). |

### 1.3 Illegal transitions and the guard that prevents each

Every row is a transition that MUST be impossible. **Guard** is the concrete deterministic mechanism (hook exit-2, schema `allOf`, DB CHECK/REVOKE/trigger, or OPA query) that makes it UNSAT.

| # | Illegal edge / action | Why forbidden | Guard that prevents it |
|---|---|---|---|
| X1 | Agent-Executing → Done while any in-scope item is `unproven` | "Done" must be impossible while work is unproven (governing invariant) | **Stop hook** (`stop_hook.py`/`evaluate_stop`): counts in-scope `unproven`; blocks termination as COMPLETE (exit 2). *Z3 CHECK-1/CHECK-3 UNSAT.* (REQ-GATE-002) |
| X2 | Spec-Verified → Agent-Executing without `plan-approved.json` | No code-write without an approved plan | **PreToolUse plan-gate**: blocks all Write/Edit/MultiEdit when `plan-approved.json` is absent (exit 2). *Z3 CHECK-4f UNSAT.* (REQ-HITL-001 / 18.1) |
| X3 | Plan-Approved → Agent-Executing after `feature_list.json` was mutated post-approval | Approval is SHA-bound to the coverage model; a mutated model must not silently authorize writes | **PreToolUse plan-gate**: blocks when `plan-approved.json.feature_list_sha` ≠ canonical-projection SHA of current `feature_list.json` → requires re-approval. (REQ-HITL / 18.4, Property 6) |
| X4 | Start a new worktree/slice while a prior-slice item is `unproven` | No forward progress past an unverified slice | **PreToolUse scope-gate**: blocks new worktree/slice assignment while any prior item is `unproven` (exit 2). *Z3 CHECK-6a UNSAT.* (REQ-EXEC-005) |
| X5 | `unproven → proven` (or `*→proven`) with a missing/empty Evidence_Record field | An item cannot be proven without all four evidence fields | **PreToolUse status-guard** + **schema `allOf`** (`if status=proven then required:[evidence]`) + **DB `evidence_complete` CHECK** (`output_hash ~ '^sha256:[a-f0-9]{64}$'`, non-empty fields). *Z3 CHECK-7a/7c UNSAT.* (REQ-COV-003/006) |
| X6 | implementer flips an item to `proven` / writes an Evidence_Record (self-verification) | The system never grades its own homework | **SubagentStop role-separation check (Property 24)**: blocks (exit 2) any evidence-bearing result whose `actor_agent == implementer.md`; backed by `evidence_records.actor_agent NOT NULL` (must be `verifier.md`). (REQ-VERIFY-002 / 9.2) |
| X7 | Delete, reorder, truncate, or change `id`/`type`/`acceptance_criteria` of an existing coverage item | `feature_list.json` is append-only; identity is immutable | **PreToolUse status-guard `check_append_only`**: diffs incoming `items[]` id-sequence + length vs prior committed file; blocks any deletion/reorder/identity-change (exit 2). *Property 3.* (REQ-COV-002) |
| X8 | Any status transition outside {`unproven→proven`, `unproven→failed`, `failed→unproven`, `proven→unproven`(amendment-only)} — e.g. `proven→failed`, `failed→proven` directly, or a bare `proven→unproven` | Only the four permitted edges are legal; `proven→unproven` needs an amendment row | **PreToolUse status-guard**: rejects any non-permitted edge; permits `proven→unproven` ONLY when accompanied by a `requirement_versions` insert. (REQ-COV-002/007, Property 3/25) |
| X9 | Cap/budget/no-progress condition → Done (terminating as COMPLETE) | Cap/budget/no-progress must terminate to HANDOFF only; the two terminal states are mutually exclusive | **Stop hook**: on these conditions sets `status='handoff'` and ALLOWS (exit 0); COMPLETE requires zero `unproven` in-scope items, which is false at HANDOFF. *Z3 CHECK-3/CHECK-8b UNSAT.* (REQ-LOOP-002/005 / 21.1) |
| X10 | Stop hook returns exit 2 (force-continuation) on a cap/budget/no-progress HANDOFF | A HANDOFF must allow termination, not infinitely block | **Req 21 correction in `evaluate_stop`**: only the unproven-items condition blocks (exit 2); cap/budget/no-progress emit `status='handoff'` + exit 0. *(Load-bearing infinite-block fix.)* (REQ-LOOP-005 / 21.1) |
| X11 | Advance Agent-Triaged → Spec-Verified while a domain-baseline item is `UNMAPPED` | An UNMAPPED baseline item blocks advancement to implementation | **`spec_validator.py` / discovery gate**: flags zero-requirement baseline items `UNMAPPED` and refuses advancement. *Z3 CHECK-9a UNSAT.* (REQ-SPEC-011 / 2.2) |
| X12 | Use a `DRAFT` (unapproved) domain-baseline checklist for discovery | Discovery may only use a human-approved checklist | **PreToolUse checklist-approval guard**: requires non-null `approved_at` in `domain_baseline_checklists`; blocks DRAFT use (exit 2). *Z3 CHECK-12a/12b.* (REQ-SPEC-016 / 24.1) |
| X13 | Accept a subagent result (initializer/research/verifier) whose `omission_declaration` is null/absent | Every declaration-producing subagent must declare its omissions | **SubagentStop omission-declaration guard (`omission_guard`)**: rejects null/absent `omission_declaration` (exit 2); validates against `schema/subagent_output.schema.json`. *Z3 CHECK-13a/13b, Property 30.* (REQ-SPEC-018 / 29.2) |
| X14 | A gate decision reading a probabilistic prediction (prediction routed into allow/block) | Gates depend only on verifiable facts; predictions only inform | **Design rejection rule + Z3 CHECK-5 (UNSAT)**: predictions inject only as advisory context; a differing prediction cannot produce a differing gate decision. (REQ-PRED-002 / 13.6) |
| X15 | UPDATE or DELETE a `gate_audit_log` or `requirement_versions` row (mutate history) | Audit log and amendment history are append-only and tamper-evident | **DB `REVOKE UPDATE, DELETE ... FROM app_role` + BEFORE-UPDATE/DELETE trigger** (`RAISE EXCEPTION ... is append-only`); hash-chain `entry_hash = sha256(canonical_row‖prev_hash)` detects any tamper. (REQ-AUDIT-001/002 / 27, Property 25/28) |
| X16 | Flip `coverage_items.in_scope = FALSE` by an agent (drop a requirement from gates) | Leaving scope is human-authored only; an unattributed flip silently drops a gate | **DB BEFORE-UPDATE trigger** requiring non-empty actor + justification on any `in_scope→FALSE`; the hook layer logs every flip to `gate_audit_log`. (REQ-COV / 5.7) |
| X17 | Prove a WIRING item with unit-test (non-integration) evidence | A WIRING obligation needs an integration test exercising the real path | **Schema `allOf`** (WIRING+proven ⇒ `evidence.evidence_kind == 'integration'`) enforced at SubagentStop acceptance. (REQ-EXEC-012 / 8.3) |
| X18 | A non-Verifier actor writes to `tests/`, or any actor performs a destructive op (`rm -rf`, `DROP TABLE`) | Only the Verifier may write `tests/`; destructive ops are always blocked | **PreToolUse artifact-guard**: allows `tests/` write only when `actor_agent == verifier.md`; blocks the implementer and all destructive Bash (exit 2). (REQ-STEER-003) |
| X19 | A `verifier`/`design`/`platform`/`reliability` extension role granted verifier *write* access to implementation, or a capability-extension role bypassing the verifier-independence rule | Independence is non-negotiable; no extension role may hold verifier write access | **REQ-ORCH-004 / Req 28 permission-scope rule**: each bounded extension role carries an explicit permission scope; **none** has verifier write access (design-enforced via subagent `tools` allowlist). (REQ-ORCH-004 / 28.1) |

---

## 2. CRUD MATRIX

Actors: **initializer**, **implementer**, **verifier**, **research**, **human** (the five `agent_role` values). Each entity is one block of four rows (Create / Read / Update / Delete) × actor. **Permission constraint** states the *exact* gate, column rule, or schema constraint — not a generality. Hard invariants enforced throughout: **agents never DELETE issues/work-items; only a human may DELETE; only the verifier may set `evidence_status=proven`; the implementer may never write evidence (Property 24).**

> Mapping note: Plane **Issue/Work-item** ≙ a `feature_list.json` CoverageItem + its `requirements`/`coverage_items` Postgres rows; **Project** ≙ the `ASCP` Plane workspace (`Agentic SDLC Control Plane`); **State** ≙ the 12-state workflow definition; **Webhook** ≙ the Plane→control-plane event sink that also fronts the append-only `gate_audit_log`/CI check-run record.

### 2.1 Project (the ASCP Plane workspace)

| Op | Actor | Permission constraint |
|---|---|---|
| Create | initializer | ✗ — agents do not create the workspace; the project (`identifier=ASCP`) is human/operator-provisioned. |
| Create | implementer | ✗ |
| Create | verifier | ✗ |
| Create | research | ✗ |
| Create | **human** | ✓ — Delivery Owner provisions the `ASCP` workspace; sole creator. |
| Read | initializer | ✓ — reads project config to detect `product_class` and select the baseline checklist. |
| Read | implementer | ✓ — reads project to resolve repo root / worktree base. |
| Read | verifier | ✓ — reads project to locate `feature_list.json` and CI config. |
| Read | research | ✓ — reads `product_class` to scope checklist sourcing. |
| Read | **human** | ✓ — full read. |
| Update | initializer | △ — may update project *description*/metadata tied to spec compilation; MUST NOT alter security/CI settings (PreToolUse artifact-guard protects CI config). |
| Update | implementer | ✗ — no project-settings write. |
| Update | verifier | ✗ — no project-settings write (read-only on implementation/config). |
| Update | research | ✗ |
| Update | **human** | ✓ — sole authority over CI config, rulesets, required reviewers, kill-switch (`kill.<capability>`) toggles (REQ-CTRL-001 restricts toggles to Delivery Owner). |
| Delete | initializer / implementer / verifier / research | ✗ — **agents never delete the project.** |
| Delete | **human** | ✓ — only a human may delete the workspace. |

### 2.2 Issue / Work-item (CoverageItem + `requirements`/`coverage_items`)

| Op | Actor | Permission constraint |
|---|---|---|
| Create | **initializer** | ✓ — sole agent creator: seeds `feature_list.json` (via `feature_list_init.py`) and populates items with `status='unproven'`, `in_scope=true`, `requirement_id` matching `^[A-Z]+-[A-Z]+-[0-9]{3}$`; the initial seed write is exempt from the artifact/status guards (creation only). |
| Create | implementer | ✗ — implements existing items only; cannot mint new coverage items. |
| Create | verifier | ✗ — verifies; cannot create items. |
| Create | research | ✗ — produces checklists, not coverage items. |
| Create | **human** | ✓ — may add items via the Initializer flow / amendment; human-authored items also legal. |
| Read | all agent roles + human | ✓ — every role reads `feature_list.json` (implementer selects the lowest-`priority` `unproven` item with all-`proven` deps; verifier reads status; gates read in-scope counts). |
| Update (status `unproven→proven` + set `evidence_status=proven`) | **verifier** | ✓ — **ONLY the verifier may set `evidence_status=proven`**, and only with a complete 4-field `Evidence_Record` (`actor_agent='verifier.md'`); SubagentStop+schema+DB CHECK enforce. |
| Update (status `unproven→proven`) | implementer | ✗ — **Property 24: the implementer may never write evidence / set `proven`.** SubagentStop blocks any evidence-bearing result with `actor_agent==implementer.md`. |
| Update (status `unproven→failed`, `failed→unproven`) | verifier (→failed) / implementer (failed→unproven on retry) | ✓ — these edges require no Evidence_Record; PreToolUse status-guard permits exactly these. |
| Update (`proven→unproven`) | **human** (+ initializer) | △ — permitted ONLY accompanied by a `requirement_versions` amendment insert; a bare flip is blocked (REQ-COV-007). |
| Update (`in_scope→false`) | **human** | ✓ — **human-authored only**; DB BEFORE-UPDATE trigger requires actor + justification; agents cannot flip scope. |
| Update (other CoverageItem fields: `id`/`type`/`acceptance_criteria`/`dependencies` of an *existing* item) | any agent | ✗ — PreToolUse status-guard `check_append_only` blocks identity/shape mutation of existing items. |
| Delete | initializer / implementer / verifier / research | ✗ — **agents never delete issues/work-items;** `feature_list.json` is append-only (items are never removed, only `in_scope`-toggled). |
| Delete | **human** | △ — even the human does not hard-delete a coverage item in-band; scope removal is the human-authored `in_scope=false` transition (preserves the append-only audit trail). Hard DB delete only via out-of-band migration, never through a gate. |

### 2.3 Comment (Plane issue comment ≙ Evidence_Record / decision annotation)

| Op | Actor | Permission constraint |
|---|---|---|
| Create | initializer | ✓ — may post spec-compilation notes / `omission_declaration` summaries; output gated by SubagentStop omission guard. |
| Create | implementer | ✓ — may post slice progress; produces **no** Evidence_Record comment (Property 24). |
| Create | **verifier** | ✓ — posts the authoritative Evidence_Record (`test_file`, `test_name`, `output_hash=sha256:<64hex>`, `collected_at`, `actor_agent='verifier.md'`); the only role whose comment can carry proving evidence. |
| Create | research | ✓ — posts checklist-sourcing provenance (source URL + authority tier); fact-check pass required pre-review. |
| Create | **human** | ✓ — review comments, plan-approval `notes`, amendment rationale. |
| Read | all roles | ✓ — comments are world-readable within the workspace; SessionStart loads progress context. |
| Update | author role only | △ — an agent may amend only its own non-evidentiary comments; an **Evidence_Record comment is immutable once accepted** (mirrored into append-only `evidence_records`); the verifier cannot rewrite a captured `output_hash` (content-addressed). |
| Update | **human** | ✓ — may annotate but not rewrite a captured Evidence_Record (audit integrity). |
| Delete | initializer / implementer / verifier / research | ✗ — **agents never delete comments** (evidentiary trail). |
| Delete | **human** | △ — may delete a *non-evidentiary* comment; an Evidence_Record-backed comment is retained (append-only) — only a human, never an agent, and never for evidence. |

### 2.4 Cycle (sprint/iteration container)

| Op | Actor | Permission constraint |
|---|---|---|
| Create | initializer | △ — may create a cycle mapping to a phase wave (`phase:0..4`) as part of planning; subordinate to human plan approval. |
| Create | implementer / verifier / research | ✗ — no cycle authoring. |
| Create | **human** | ✓ — full authority. |
| Read | all roles | ✓ — read to scope which slice belongs to the active wave. |
| Update | initializer | △ — may move planned items into a cycle pre-approval; locked after `plan-approved.json`. |
| Update | implementer / verifier / research | ✗ |
| Update | **human** | ✓ — sole authority post-approval. |
| Delete | initializer / implementer / verifier / research | ✗ — **agents never delete cycles.** |
| Delete | **human** | ✓ — only a human may delete. |

### 2.5 Module (feature grouping ≙ baseline block B01–B19)

| Op | Actor | Permission constraint |
|---|---|---|
| Create | initializer | ✓ — maps each baseline block to a module during discovery; flags `UNMAPPED` modules (blocks advancement, REQ-SPEC-011). |
| Create | research | △ — proposes module groupings from the domain-baseline checklist; advisory until human-approved. |
| Create | implementer / verifier | ✗ |
| Create | **human** | ✓ — full authority. |
| Read | all roles | ✓ — read to resolve which baseline block a slice serves. |
| Update | initializer | ✓ — updates module↔requirement mapping during spec compilation. |
| Update | implementer / verifier / research | ✗ — read-only. |
| Update | **human** | ✓ — sole authority over final module membership. |
| Delete | initializer / implementer / verifier / research | ✗ — **agents never delete modules.** |
| Delete | **human** | ✓ — only a human may delete. |

### 2.6 Label (control-vocabulary labels: `agent:*`, `gate:*`, `type:*`, `phase:*`, `handoff`, `blocked`, `failed`)

| Op | Actor | Permission constraint |
|---|---|---|
| Create | initializer | △ — may apply (attach) existing canonical labels (`type:functional/nfr/wiring`, `phase:*`) during triage; SHOULD NOT mint new label definitions (vocabulary is fixed). |
| Create (new label *definition*) | any agent | ✗ — the label taxonomy is a fixed control vocabulary; new definitions are human-curated. |
| Create | **human** | ✓ — sole curator of new label definitions. |
| Read | all roles | ✓. |
| Update (attach/detach on an issue) | initializer / verifier | ✓ — initializer attaches `type:*`/`phase:*`; verifier attaches/detaches `failed`, `gate:*` on verdict; Stop hook attaches `handoff`, PreToolUse attaches `blocked`. |
| Update (attach/detach) | implementer | △ — may attach `priority:*` / progress labels on its own slice only. |
| Update (rename/redefine a label) | any agent | ✗ — vocabulary names are load-bearing (gates key on them); only human may rename. |
| Update | **human** | ✓ — sole authority over label definitions/renames. |
| Delete | initializer / implementer / verifier / research | ✗ — **agents never delete label definitions** (would break gate keying). |
| Delete | **human** | ✓ — only a human may delete a label definition. |

### 2.7 State (the 12-state workflow definition)

| Op | Actor | Permission constraint |
|---|---|---|
| Create / add a workflow state | any agent | ✗ — the 12-state set is fixed and load-bearing for the Stop/OPA gates; agents cannot add states. |
| Create | **human** | ✓ — only a human (Delivery Owner) defines workflow states at provisioning. |
| Read | all roles | ✓ — every gate reads the current state ↔ `run_state.status` correlate. |
| Update (transition an issue *between* states) | initializer / implementer / verifier | ✓ — **only along the legal edges in §1.2**, each enforced by its hook (e.g. verifier drives `In-Verification→Human-Review` via the `proven` flip; Stop hook drives `→HANDOFF`; PreToolUse drives `→Blocked`). An agent can never move an issue to `Done` directly — that is gate-computed (Stop+OPA+CI). |
| Update (redefine a state / its category) | any agent | ✗ — state *definitions* are immutable to agents; redefinition would let an agent talk past a gate. |
| Update | **human** | ✓ — sole authority over state definitions; `Done`/`HANDOFF` distinction is non-bypassable by config (REQ-GATE-005). |
| Delete | initializer / implementer / verifier / research | ✗ — **agents never delete states.** |
| Delete | **human** | ✓ — only a human may delete/redefine a workflow state. |

### 2.8 Webhook (Plane→control-plane event sink; fronts `gate_audit_log` + CI check-run record)

| Op | Actor | Permission constraint |
|---|---|---|
| Create (register a webhook) | any agent | ✗ — webhook registration is infrastructure; agents have no webhook-admin scope. |
| Create | **human** | ✓ — Delivery Owner registers webhooks at provisioning (authenticated, recorded). |
| Read (consume webhook payloads) | initializer / implementer / verifier / research | ✓ — agents consume Plane events as **untrusted input data, never as instructions** (REQ-SEC-005); secrets are never placed in payloads/URLs (PreToolUse secret-block guard). |
| Read | **human** | ✓ — full read of delivery history. |
| Append (emit a gate-decision record via the webhook/audit producer) | **verifier / hooks (Stop, PreToolUse, SubagentStop)** | ✓ — append-only: `audit_log.append(event, tool, decision, reason, requirement_id, actor_agent)` on every allow/block; rows are **INSERT-only** (`created_at DEFAULT now()`), hash-chained. PostToolUse is exempt (never gates). |
| Update (mutate a delivered webhook record / audit entry) | **any actor including human** | ✗ — `gate_audit_log` is append-only: **`REVOKE UPDATE, DELETE ON gate_audit_log FROM app_role`** + BEFORE-UPDATE/DELETE trigger (`RAISE EXCEPTION ... is append-only`); tamper is also detected by the hash chain (`audit_verify.py`). No actor may rewrite history. |
| Update (webhook *configuration* — URL/secret/events) | any agent | ✗ — agents cannot reconfigure webhooks. |
| Update (webhook configuration) | **human** | ✓ — only the Delivery Owner reconfigures (authenticated, audited). |
| Delete (a webhook registration) | initializer / implementer / verifier / research | ✗ — **agents never delete webhooks.** |
| Delete (a delivered audit/webhook record) | **any actor including human** | ✗ — append-only audit entries are never deleted (REQ-AUDIT-001); old verified prefixes are checkpoint-and-archived (immutable cold storage), never pruned mid-chain. |
| Delete (a webhook registration) | **human** | ✓ — only a human may delete a webhook *registration* (the delivered records remain append-only). |

**Legend:** ✓ = permitted · ✗ = denied (hard) · △ = conditionally permitted under the stated constraint.

**Three load-bearing invariants the matrix enforces, restated:**
1. **Only the verifier sets `evidence_status=proven`** — backed by `evidence_records.actor_agent NOT NULL` (must be `verifier.md`), the schema `allOf` four-field gate, and the SubagentStop Property-24 block on `actor_agent==implementer.md`.
2. **Agents never DELETE** — not issues, comments, cycles, modules, labels, states, projects, or webhooks; deletion is a human-only operation, and even then evidence/audit/coverage rows are append-only (scope-removal is `in_scope=false`, not delete).
3. **Only a human** creates/deletes the workspace, defines states/labels/CI config, toggles the kill-switch, approves plans, and reviews PRs — the deterministic human-in-the-loop boundary (REQ-HITL-001/002/003, REQ-CTRL-001/32.4).


These two sections extend the canonical reconciled spec (`/Users/danielmanzela/Agentic-Driven SDLC Platform/.kiro/specs/spec-to-evidence-control/`) with the Plane PM control-plane integration surface that the 32-requirement core did not yet cover. They are authored to the same conventions: numbered EARS requirements continuing from Requirement 32, `REQ-*` PRD labels, IF/WHEN/WHILE EARS form, threshold-registry ties (Requirement 20), and tasks in the `tasks.md` wave/`_Requirements:_` style. Every value is concrete and grounded in the existing durable spine: the eight Postgres tables (`requirements`, `coverage_items`, `traceability_links`, `evidence_records`, `run_state`, `domain_baseline_checklists`, `requirement_versions`, `gate_audit_log`), the hash-chained audit log (`entry_hash = sha256(canonical_row ‖ prev_hash)`), `audit_verify.py`, `state_integrity.py`, the N-25 never-fail-open fallback, the `Evidence_Record.output_hash` (`sha256:<64hex>`) semantics, and the SHARED CONTROL VOCABULARY custom fields `worktree_branch` and `agent_run_id`.

---

# Requirement 33: Failure-Mode & Resilience (Plane ↔ Control-Plane Integration)

**User Story:** As an operator running the autonomous control plane against the **Agentic SDLC Control Plane (ASCP)** Plane workspace, I want every transport between Plane and the engine — webhooks inbound, REST outbound, and the durable stores beneath them — to fail closed, dedupe, replay, and reconcile, so that a dropped delivery, a model context blow-up mid-sync, a Plane `429`, or a Redis/MQ/DB outage never silently corrupts the coverage model, the traceability triple, or the completion verdict.

**Baseline block:** B10 / B14 / B16 (extends Session-Continuity, Orchestration, Security/Control) | **PRD references:** REQ-RESIL-001..009

**Governing invariant (inherits the core posture):** *Resilience never relaxes a gate.* Every degraded path resolves to the **more conservative (blocking) outcome**, mirroring the N-25 "never fail-open" rule (`design.md` Postgres-unavailable row). A retry, a replay, or a reconciliation poll may restore lost facts; none may manufacture a `proven` transition or an `allow` decision that the un-degraded path would not have produced.

## 33.1 — Webhook drop / timeout: delivery dedup + replay + reconciliation poll

### Acceptance Criteria

1. **WHEN** Plane emits a webhook to the engine's ingest endpoint (`POST /plane/webhooks`), **THE System SHALL** extract the `X-Plane-Delivery` UUID header and the `X-Plane-Event` type, and **SHALL** persist the delivery into a `webhook_deliveries` dedup ledger keyed on `delivery_id` (UNIQUE) **before** any handler side-effect runs. *(Event-driven.)*
2. **IF** a webhook handler does not return `2xx` within the **ingest ACK budget = 10 s** (DEFAULT, configurable; Plane retries non-2xx/timeout deliveries), **THEN THE System SHALL** return `202 Accepted` after the durable ledger write and process the body **asynchronously off the request thread**, so a slow coverage-model mutation cannot cause Plane to mark the delivery failed and re-fan-out. *(Unwanted-behaviour: a slow consumer must not amplify deliveries.)*
3. **WHEN** the engine has not received any webhook for a Plane project within the **reconciliation idle window = 120 s** (DEFAULT, configurable), **THE System SHALL** run a reconciliation poll against the Plane REST list endpoints (`GET /api/v1/workspaces/{slug}/projects/{id}/issues/?updated_at__gte=<watermark>`) and converge any issue whose `updated_at` advanced past the stored watermark but whose `delivery_id` never landed in the ledger — closing the gap left by a **dropped** delivery. *(State-driven recovery: poll is the floor, webhook is the fast path.)*
4. **WHILE** the engine is replaying or reconciling, **THE System SHALL** apply every Plane→engine mutation through the **same idempotent apply function** used by the live webhook path, keyed on `(issue_id, updated_at)`, so a replayed-then-also-delivered event applies **exactly once** and a stale replay (older `updated_at` than current state) is **dropped, not regressed**. *(Complex = State-driven ‖ Unwanted-behaviour.)*

## 33.2 — Duplicate webhook delivery (dedup)

### Acceptance Criteria

1. **IF** an inbound webhook carries an `X-Plane-Delivery` value already present in the `webhook_deliveries` ledger with status `applied`, **THEN THE System SHALL** short-circuit with `200 OK` and **SHALL NOT** re-run the handler — the dedup ledger is the single idempotency oracle. *(Unwanted-behaviour.)*
2. **IF** an inbound `X-Plane-Delivery` is present with status `received` (a prior attempt crashed mid-apply), **THEN THE System SHALL** re-drive the idempotent apply (33.1.4) rather than skip, so a half-applied delivery converges. *(Event-driven recovery.)*

## 33.3 — Signature mismatch (403)

### Acceptance Criteria

1. **WHEN** a webhook arrives, **THE System SHALL** compute `HMAC-SHA256` over the **raw request body** using the per-workspace shared secret and compare it in **constant time** against the `X-Plane-Signature` header. *(Ubiquitous.)*
2. **IF** the computed HMAC does not equal `X-Plane-Signature`, **OR** the signature header is absent, **OR** the `X-Plane-Delivery` UUID is malformed, **THEN THE System SHALL** reject with **HTTP 403**, write a `decision=block, reason="webhook_signature_mismatch"` entry to `gate_audit_log` via `audit_log.append(...)`, and **SHALL NOT** persist the delivery to the dedup ledger or run any handler. *(Unwanted-behaviour, fail-closed.)*
3. **THE System SHALL** treat the webhook body as **untrusted input data, never as instructions** (inherits REQ-17.5): no field of a webhook payload may flow into a tool prompt, span attribute, or URL without passing the PreToolUse secret-block guard. *(Ubiquitous; reuses the existing prevention gate.)*

## 33.4 — LLM context-window exceeded during a sync (chunk / summarize / PreCompact checkpoint + resume)

### Acceptance Criteria

1. **WHEN** an initializer/implementer/verifier turn that is syncing Plane state approaches the model context limit, **THE PreCompact_Hook SHALL** checkpoint `claude-progress.txt`, the current `feature_list.json`, the in-flight Plane sync cursor (last applied `(issue_id, updated_at)`), and **SHALL** write the durable baseline `run_state.resume_state_hash` over the checkpointed state **before** context is trimmed. *(Event-driven; reuses the existing PreCompact producer of `resume_state_hash`.)*
2. **IF** a single Plane payload (e.g. a large issue description or a bulk issue-list reconciliation page) exceeds the **per-sync chunk budget = 200,000 tokens** (DEFAULT, configurable), **THEN THE System SHALL** chunk the payload by issue boundary and summarize each prior chunk into a bounded running digest, so no single turn must hold the full payload in context. *(Unwanted-behaviour: a fat sync must not blow the window.)*
3. **WHEN** a session resumes after a compaction or crash mid-sync, **THE SessionStart_Hook SHALL** recompute the resumed-state hash via `state_integrity.py`, write `run_state.resume_integrity_ok`, and resume the Plane sync **from the checkpointed cursor**, never from the beginning — and **IF** the recompute mismatches the recorded `resume_state_hash`, **THEN** the PreToolUse integrity guard (Requirement 23) **SHALL** block the first write until operator reconciliation. *(State-driven; reuses Requirement 23 verbatim — a context-window resume is just another resume.)*

## 33.5 — Plane REST rate-limit (429 backoff + token-bucket + queue)

### Acceptance Criteria

1. **THE System SHALL** rate-limit all outbound Plane REST calls through a client-side **token bucket** sized at the **DEFAULT capacity = 60 requests / 60 s per workspace** (configurable; conservative under Plane's documented limits), so the engine self-throttles **before** Plane returns `429`. *(Ubiquitous.)*
2. **IF** Plane returns **HTTP 429**, **THEN THE System SHALL** honor the `Retry-After` header when present, else apply **exponential backoff with full jitter** (base 1 s, factor 2, cap 60 s) up to the **DEFAULT REST retry budget = 5 attempts**, and **SHALL** enqueue the call on the durable outbound queue rather than dropping it. *(Unwanted-behaviour.)*
3. **IF** a write call (status flip, custom-field set, comment) exhausts its 5-attempt retry budget, **THEN THE System SHALL** persist it to the durable outbound queue in state `pending` and route to HANDOFF **only if** the call is on the critical completion path (a `Done`/`Blocked`/`Failed` state write); a non-critical write (telemetry comment) **SHALL** be retried on the next drain without HANDOFF. *(Complex.)*
4. **WHILE** outbound calls are queued, **THE System SHALL** preserve **per-issue FIFO ordering** so that a `Spec-Verified → Plan-Approved → Agent-Executing` state progression cannot be reordered by retry, which would corrupt the Plane-visible lifecycle. *(State-driven.)*

## 33.6 — DB / Redis / MQ outage

### Acceptance Criteria

1. **IF** the durable **Postgres** store is unavailable, **THEN** every gate (Stop, PreToolUse sub-gates, SubagentStop, OPA at merge) **SHALL** fall back to file-backed state (`feature_list.json` + `claude-progress.txt`) and reach the **same allow/block decision**, taking the **more conservative (blocking)** result on any divergence — it **SHALL NEVER fail open** (inherits N-25). *(Unwanted-behaviour; reuses the existing Postgres-unavailable contract.)*
2. **IF** **Redis** (the webhook async-dispatch / token-bucket coordination cache) is unavailable, **THEN THE System SHALL** degrade the token bucket to an **in-process per-replica bucket** at a **reduced DEFAULT = 20 req/60 s** (configurable) and continue serving webhooks synchronously within the 10 s ACK budget, so a cache outage throttles rather than halts the engine. *(State-driven graceful degradation.)*
3. **IF** the durable **message queue / outbound queue** is unavailable, **THEN THE System SHALL** spill queued Plane writes to a **file-backed outbound segment** (mirroring the `gate_audit_log` file-backed-segment fallback) and **SHALL** replay-and-reconcile the segment in FIFO order on reconnect, so no Plane state write is lost across an MQ outage. *(Unwanted-behaviour.)*
4. **WHILE** any of Postgres / Redis / MQ is degraded, **THE System SHALL** emit an OTel span `infra.degraded{component, mode}` and **SHALL** append a `gate_audit_log` note when a degraded path changes a gate's effective conservatism, so the degradation is observable and tamper-evidently recorded. *(State-driven observability.)*

## 33.7 — Threshold-registry additions (extends Requirement 20.3)

| Threshold | DEFAULT | Configurable | Owner | Enforced by |
|---|---|---|---|---|
| Webhook ingest ACK budget | 10 s | yes | Operator | 33.1.2 async-off-thread cutover |
| Reconciliation idle window | 120 s | yes | Operator | 33.1.3 reconciliation poll trigger |
| Per-sync chunk budget | 200,000 tokens | yes | Operator | 33.4.2 chunk/summarize cutover |
| Plane REST token-bucket capacity | 60 req / 60 s / workspace | yes | Operator | 33.5.1 outbound limiter |
| REST 429 retry budget | 5 attempts | yes | Operator | 33.5.2 backoff loop |
| REST backoff (base / factor / cap) | 1 s / 2× / 60 s | yes | Operator | 33.5.2 full-jitter backoff |
| Redis-degraded bucket capacity | 20 req / 60 s | yes | Operator | 33.6.2 in-process fallback |

## 33.8 — New durable artifact: `webhook_deliveries` (migration `009`)

Adds the **ninth** migration to the existing eight (`001`–`008`), applied in numeric order under the migration role; `app_role` gets `INSERT`/`SELECT`/`UPDATE(status)` only.

```sql
-- 009_webhook_deliveries.sql — inbound dedup + replay ledger (REQ-RESIL-001/002)
CREATE TABLE webhook_deliveries (
    delivery_id   UUID PRIMARY KEY,                 -- X-Plane-Delivery header (idempotency oracle)
    event_type    TEXT NOT NULL,                    -- X-Plane-Event (issue.updated, issue.created, ...)
    issue_id      TEXT,                             -- Plane issue UUID (external_id linkage, Req 34)
    payload_sha   TEXT NOT NULL CHECK (payload_sha ~ '^sha256:[a-f0-9]{64}$'),  -- same output_hash format
    source_updated_at TIMESTAMPTZ,                  -- Plane issue.updated_at; the (issue_id, updated_at) idempotency key
    status        TEXT NOT NULL CHECK (status IN ('received','applied','rejected'))
                  DEFAULT 'received',
    received_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    applied_at    TIMESTAMPTZ
);
CREATE INDEX idx_webhook_deliveries_issue ON webhook_deliveries (issue_id, source_updated_at);
```

```sql
-- 010_outbound_queue.sql — durable outbound Plane-write queue (REQ-RESIL-005/006)
CREATE TABLE plane_outbound_queue (
    id            BIGSERIAL PRIMARY KEY,            -- monotonic; preserves per-issue FIFO
    issue_id      TEXT NOT NULL,
    op            TEXT NOT NULL,                    -- 'set_state' | 'set_field' | 'comment'
    payload       JSONB NOT NULL,
    attempts      INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL CHECK (status IN ('pending','sent','dead')) DEFAULT 'pending',
    next_retry_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_outbound_issue_fifo ON plane_outbound_queue (issue_id, id);
```

## 33.9 — Resilience tasks (tasks.md style)

> Phase placement: **Phase 2** (durable-state wave) for the ledgers/queue + DB/Redis/MQ fallback; the webhook signature/dedup ingest and the REST limiter ride the Phase-0/1 transport. `[ ]*` = optional property/unit test, matching the canonical convention.

- [ ] **58. Plane webhook ingest — signature, dedup, async ACK** (**REQ-RESIL-001/002/008**)
  - [ ] 58.1 Implement `tools/plane_webhook.py`: `POST /plane/webhooks` handler. Compute constant-time `HMAC-SHA256(raw_body, workspace_secret)`; compare to `X-Plane-Signature`; on mismatch/absent/malformed-`X-Plane-Delivery` → **403** + `audit_log.append(decision="block", reason="webhook_signature_mismatch", tool="plane_webhook")`. On valid → upsert `webhook_deliveries(delivery_id) status='received'` BEFORE any side-effect; return `202` and dispatch async.
    - _Requirements: 33.2, 33.3 (REQ-RESIL-002, REQ-RESIL-008), REQ-AUDIT-001_
  - [ ] 58.2 Implement `apply_issue_update(issue_id, updated_at, payload)` — the **single idempotent apply** keyed on `(issue_id, updated_at)`; drop stale (`updated_at <= stored`), apply once, flip ledger `status='applied'`, set `applied_at`. Shared by live + replay + reconciliation paths.
    - _Requirements: 33.1 (REQ-RESIL-001), 34.x (traceability-triple writes)_
  - [ ]* 58.3 **Property RESIL-1: Webhook Idempotence.** Generate arbitrary interleavings of `(delivery_id, issue_id, updated_at)` with duplicates and out-of-order replays; assert each `(issue_id, updated_at)` applies **exactly once** and no apply regresses a newer state. `# Feature: spec-to-evidence-control, Property RESIL-1`
    - _Requirements: 33.1, 33.2_

- [ ] **59. Reconciliation poll — dropped-delivery floor** (**REQ-RESIL-003**)
  - [ ] 59.1 Implement `tools/plane_reconcile.py`: on the 120 s idle window, `GET .../issues/?updated_at__gte=<watermark>`; for any issue advanced past the watermark with no `applied` ledger row, drive `apply_issue_update(...)`; advance the watermark transactionally.
    - _Requirements: 33.1 (REQ-RESIL-003)_
  - [ ]* 59.2 Integration test: drop a delivery (skip 58.1 for one event), advance Plane `updated_at`, run reconcile → assert the coverage-model mutation converges and the ledger gains an `applied` row.
    - _Requirements: 33.1_

- [ ] **60. Outbound REST resilience — token bucket + 429 backoff + durable queue** (**REQ-RESIL-005/006**)
  - [ ] 60.1 Implement `tools/plane_client.py`: token bucket (60 req/60 s/workspace via Redis, in-process 20 req/60 s fallback); on `429` honor `Retry-After` else full-jitter backoff (1 s/2×/60 s, 5 attempts); on exhaustion enqueue to `plane_outbound_queue` (`status='pending'`).
    - _Requirements: 33.5 (REQ-RESIL-005), 33.6.2 (Redis fallback)_
  - [ ] 60.2 Implement `drain_outbound_queue()`: FIFO per `issue_id` (order by `id`); critical-path state writes that go `dead` route to HANDOFF; non-critical retry next drain.
    - _Requirements: 33.5.3, 33.5.4_
  - [ ]* 60.3 **Property RESIL-2: Per-Issue FIFO Under Retry.** Generate state-progression sequences with injected 429s; assert the Plane-visible state order is never reordered by retry. `# Feature: spec-to-evidence-control, Property RESIL-2`
    - _Requirements: 33.5.4_

- [ ] **61. Context-window resilience during sync — chunk/summarize + checkpoint/resume** (**REQ-RESIL-004**)
  - [ ] 61.1 Extend `pre_compact_hook.py`: checkpoint the Plane sync cursor `(issue_id, updated_at)` alongside the existing `feature_list.json`/progress checkpoint; ride the existing `resume_state_hash` producer.
    - _Requirements: 33.4.1, REQ-STATE-002_
  - [ ] 61.2 Implement chunk/summarize in `plane_reconcile.py` / `plane_webhook.py`: split payloads > 200,000 tokens by issue boundary; bounded running digest; resume from checkpointed cursor on SessionStart.
    - _Requirements: 33.4.2, 33.4.3, REQ-STATE-005_
  - [ ]* 61.3 Integration test: force a mid-sync compaction; assert resume continues from the cursor (no re-apply, no skip) and the integrity guard fires only on a genuine `resume_state_hash` mismatch.
    - _Requirements: 33.4.3, REQ-STATE-005_

- [ ] **62. Infra-outage fallbacks — DB / Redis / MQ** (**REQ-RESIL-006/007**)
  - [ ] 62.1 Wire `webhook_deliveries` + `plane_outbound_queue` into the **N-25 file-backed fallback**: when Postgres is down, dedup against a file-backed ledger segment and spill the outbound queue to a file segment; reconcile (replay + re-chain, mirroring the `gate_audit_log` reconnect path) on reconnect.
    - _Requirements: 33.6.1, 33.6.3, REQ-AUDIT (file-segment reconcile)_
  - [ ] 62.2 Emit `infra.degraded{component, mode}` OTel spans + `gate_audit_log` notes on any conservatism-changing degradation.
    - _Requirements: 33.6.4, REQ-OBS-003_
  - [ ]* 62.3 Migrations `009_webhook_deliveries.sql`, `010_outbound_queue.sql` apply in order; `app_role` lacks `DELETE` on either ledger (append/converge only).
    - _Requirements: 33.8, REQ-STORE-001_

---

# Requirement 34: Data-Integrity & Traceability (The Immutable Triple, kept consistent and tamper-evident)

**User Story:** As an auditor of the **ASCP** workspace, I want the immutable triple **Plane-issue-id ↔ git-branch ↔ agent-run-id** bound once, mirrored across `feature_list.json`, the eight Postgres tables, and Plane's custom fields, and made tamper-evident by the audit-log hash chain plus the `Evidence_Record.output_hash`, so that every `Done` issue is reconstructable end-to-end and any divergence is detected and reconciled rather than silently accepted.

**Baseline block:** B05 / B09 / B15 (extends Traceability, Completion-Gate audit, Durable-Storage) | **PRD references:** REQ-TRIPLE-001..008

## 34.1 — The immutable triple and where each leg lives

The triple is one identity carried in three mirrors. All three legs are written **once at slice-start** and never re-pointed for the life of the slice (only `proven` evidence is appended later).

| Leg | Plane mirror (custom field) | `feature_list.json` mirror | Postgres mirror |
|---|---|---|---|
| **Plane-issue-id** | the issue itself, addressed via `external_id` + `external_source` | `CoverageItem.id` ⇄ `requirement_id` (the `^[A-Z]+-[A-Z]+-[0-9]{3}$` ID) | `requirements.id` (PK); `coverage_items.requirement_id` |
| **git-branch** | `worktree_branch` (text custom field) | the slice's `slice/{item_id}` branch produced by `worktree_manager.create_worktree` | `traceability_links(link_type='commit', target_ref=<sha on branch>)`; `run_state.last_commit_sha` |
| **agent-run-id** | `agent_run_id` (text custom field) | n/a (run-scoped, not coverage-scoped) | `run_state.session_id`; `evidence_records.actor_agent` + commit_sha join; `gate_audit_log.actor_agent` |

**The `external_id`/`external_source` binding.** The engine owns requirement IDs; Plane owns issue UUIDs. The two are bound by Plane's `external_id` + `external_source` import keys: the engine writes `external_source = "ascp-control-plane"` and `external_id = <CoverageItem.id>` (e.g. `REQ-GATE-002`) onto the Plane issue at provisioning time. This makes the mapping **bidirectional and idempotent**: a re-provision or a reconciliation poll resolves the same Plane issue by `(external_source, external_id)` instead of creating a duplicate.

### Acceptance Criteria

1. **WHEN** a slice begins (the implementer takes the highest-priority `unproven` item and `worktree_manager` creates `slice/{item_id}`), **THE System SHALL** bind the triple atomically: write `worktree_branch=slice/{item_id}` and `agent_run_id=<run_state.session_id>` to the Plane issue's custom fields, and insert the corresponding `traceability_links` / `run_state.current_item_id` rows — **all three legs in one transaction**. *(Event-driven.)*
2. **IF** any one leg of the triple cannot be written (Plane custom-field write fails, or the `traceability_links` insert fails), **THEN THE System SHALL** roll back the other two legs and route to the resilient outbound queue (Requirement 33.5), so the engine **never** runs a slice with a partial triple. *(Unwanted-behaviour, all-or-nothing.)*
3. **THE System SHALL** treat the triple as **immutable for the slice lifetime**: the PreToolUse status guard / artifact guard **SHALL** block any write that re-points `worktree_branch` or `agent_run_id` of an in-flight issue (a re-point is an identity mutation, already blocked by Property 3 / REQ-COV-002). *(Unwanted-behaviour.)*

## 34.2 — Consistency across the lifecycle (the twelve states)

The triple must read identically from all three mirrors at every state from `Agent-Triaged` through `Done`/`HANDOFF`/`Blocked`/`Failed`.

### Acceptance Criteria

1. **WHILE** an issue progresses through its states (`Backlog → Agent-Triaged → Spec-Compiling → Spec-Verified → Plan-Approved → Agent-Executing → In-Verification → Human-Review → Done`, or any terminal `HANDOFF`/`Blocked`/`Failed`), **THE System SHALL** keep `(external_id, worktree_branch, agent_run_id)` byte-identical across the Plane custom fields, the `feature_list.json`/`traceability_links` mirror, and `run_state`. *(State-driven.)*
2. **WHEN** the Verifier flips an item `unproven → proven`, **THE System SHALL** require the attached `Evidence_Record` to reference the **same** `commit_sha` reachable from the bound `worktree_branch`, and the `evidence_records.actor_agent` to be `verifier.md` (never `implementer.md`, Property 24) — so the proof is provably on the slice's own branch by the independent evaluator. *(Event-driven; reuses the role-separation column.)*
3. **IF** an issue reaches `Done` **THEN** every leg of its triple **SHALL** resolve to a non-null mirror in all three stores **AND** the OPA zero-evidence query **SHALL** find a complete four-field `Evidence_Record` — otherwise the completion gate resolves to `Blocked`, not `Done` (fail-closed, inherits REQ-GATE-005). *(Unwanted-behaviour.)*

## 34.3 — Tamper-evidence: audit log + Evidence_Record output_hash

Two independent tamper-evidence layers protect the triple's history.

**Layer 1 — the hash-chained `gate_audit_log`.** Every gate allow/block on a triple-bearing issue (state flip, custom-field set, status transition) is appended by `audit_log.append(...)` with `entry_hash = sha256(canonical_row ‖ prev_hash)` over the canonical tuple `(seq, event_name, tool_name, decision, reason, requirement_id, actor_agent, created_at)`; genesis `prev_hash = sha256("")`. `app_role` holds **no `UPDATE`/`DELETE`** on `gate_audit_log`. `audit_verify.py::verify_chain(rows)` recomputes the chain and **fails at the first** `prev_hash` or `entry_hash` mismatch — so a retroactively rewritten history (e.g. forging an approval, hiding a `Failed`) is detected.

**Layer 2 — the `Evidence_Record.output_hash`.** Each proof carries `output_hash = sha256:<64hex>` over the **canonicalized verification artifact** (volatile fields stripped, deterministic serialization, per `evidence_collector.py` semantics). Re-verification recomputes the canonical artifact and asserts equality against the stored reference — so a fabricated or swapped proof for a triple does not rehash to its claimed `output_hash`.

### Acceptance Criteria

1. **WHEN** any gate decides allow/block on a triple-bearing issue, **THE System SHALL** append a `gate_audit_log` entry carrying the issue's `requirement_id` and the deciding `actor_agent`, hash-chained per the canonical form above. *(Event-driven; reuses the existing producer set: Stop / PreToolUse / SubagentStop.)*
2. **IF** `audit_verify.py` finds any `prev_hash`-mismatch or `entry_hash`-mismatch, **THEN** the merge-time `audit-chain-verify` REQUIRED CI check **SHALL** fail the merge (fail-closed; an unreadable chain also fails, never passes). *(Unwanted-behaviour.)*
3. **IF** a re-verification of a `proven` item recomputes an `output_hash` that does not equal the stored `sha256:<64hex>` reference, **THEN THE System SHALL** transition the item `proven → unproven` **only** through the amendment-gated path (a `requirement_versions` insert, Requirement 22 / Property 25) and re-open the issue — a hash divergence is treated as a tampered/regenerated proof, never silently re-accepted. *(Unwanted-behaviour; reuses the amendment re-entry edge.)*

## 34.4 — Reconciliation on divergence

### Acceptance Criteria

1. **WHEN** the reconciliation poll (Requirement 33.1.3) or a scheduled triple-audit detects that a leg diverges across mirrors — e.g. Plane's `worktree_branch` ≠ the `traceability_links` branch, or `agent_run_id` ≠ `run_state.session_id`, or a Plane state ahead of the `coverage_items.status` — **THE System SHALL** compute the divergence and resolve by the **canonical-source precedence**: for `acceptance_criteria`/`dependencies`/`priority` and coverage status, **`feature_list.json` is canonical** (REQ-16.3 file-canonical rule); for the durable traceability graph and evidence, **Postgres is canonical**; Plane custom fields are a **projection** and are re-pushed to match. *(State-driven.)*
2. **IF** a divergence cannot be resolved by re-projection because the **authoritative stores themselves disagree** (e.g. `feature_list.json` says `proven` but `evidence_records` has no complete four-field row for that `requirement_id`), **THEN THE System SHALL** take the **more conservative result** (treat as `unproven`/`Blocked`), write a `decision=block, reason="triple_divergence"` audit entry, and route to HANDOFF for operator reconciliation — it **SHALL NEVER** auto-resolve toward `proven`. *(Unwanted-behaviour; inherits never-fail-open.)*
3. **WHEN** an operator reconciles a triple divergence, **THE System SHALL** record the re-baseline as a `gate_audit_log` entry (so the reconciliation is itself tamper-evident) and, if the divergence touched durable resume state, re-run `state_integrity.py --reconcile --session <id>` to re-record `run_state.resume_state_hash` (Requirement 23 unblock path). *(Event-driven; reuses the existing operator-reconciliation entry point.)*

## 34.5 — Orphan & triple-completeness gate

### Acceptance Criteria

1. **IF** any `requirement_id` present in `feature_list.json` has **no** corresponding Plane issue resolvable by `(external_source, external_id)`, **OR** any Plane issue carrying `external_source="ascp-control-plane"` has **no** matching `CoverageItem`, **THEN** `orphan_detector.py` (extended) **SHALL** flag a **triple orphan** and the `traceability-gate` REQUIRED CI check **SHALL** block the merge (extends REQ-6.3 "block the run"). *(Unwanted-behaviour.)*
2. **THE System SHALL** stamp the active `requirement.id` onto every telemetry span via the existing W3C_Baggage span processor (REQ-OBS-004) **and additionally** stamp `worktree_branch` and `agent_run_id` as span attributes on triple-mutating spans, so the live trace reconstructs the full triple. *(Ubiquitous; additive to existing Baggage propagation.)*

## 34.6 — Integrity tasks (tasks.md style)

> Phase placement: **Phase 2** (durable traceability graph wave) for the triple binding + Postgres mirrors; **Phase 3** for the audit-chain triple coverage and the divergence reconciler.

- [ ] **63. Triple binding at slice-start** (**REQ-TRIPLE-001/002/003**)
  - [ ] 63.1 Extend `worktree_manager.create_worktree(item_id)`: in one transaction, write Plane custom fields `worktree_branch=slice/{item_id}`, `agent_run_id=<session_id>`, set Plane `external_id=<item_id>` / `external_source="ascp-control-plane"`, and insert `traceability_links` + set `run_state.current_item_id`. Roll back all legs on any failure; route the Plane write through the resilient outbound client (task 60.1).
    - _Requirements: 34.1.1, 34.1.2, 34.1.3, REQ-TRACE-001_
  - [ ]* 63.2 **Property TRIPLE-1: All-or-Nothing Triple.** Inject a failure on each leg in turn; assert no slice runs with a partial triple and the other two legs are rolled back. `# Feature: spec-to-evidence-control, Property TRIPLE-1`
    - _Requirements: 34.1.2_
  - [ ]* 63.3 **Property TRIPLE-2: Triple Immutability.** Generate re-point attempts on `worktree_branch`/`agent_run_id` of in-flight issues; assert the PreToolUse guard blocks all (reuses Property 3). `# Feature: spec-to-evidence-control, Property TRIPLE-2`
    - _Requirements: 34.1.3, REQ-COV-002_

- [ ] **64. Lifecycle consistency + evidence-on-branch** (**REQ-TRIPLE-004/005**)
  - [ ] 64.1 In `verifier.md` / `evidence_collector.store_to_feature_list`: assert the `Evidence_Record.commit_sha` is reachable from the bound `worktree_branch` and `actor_agent=='verifier.md'` before the `unproven → proven` flip; on mismatch, refuse the flip.
    - _Requirements: 34.2.2, REQ-VERIFY-002, Property 24_
  - [ ] 64.2 Extend the OPA `coverage_query.rego` / completion gate: a `Done`-bound issue requires all three triple legs non-null across the three stores AND a complete four-field Evidence_Record; otherwise resolve `Blocked`.
    - _Requirements: 34.2.1, 34.2.3, REQ-GATE-001/005_
  - [ ]* 64.3 Integration test: walk an issue through all twelve states; assert the triple reads byte-identical from Plane, file, and Postgres at each state.
    - _Requirements: 34.2.1_

- [ ] **65. Tamper-evidence coverage for the triple** (**REQ-TRIPLE-006**)
  - [ ] 65.1 Ensure every triple-mutating gate decision (state flip, custom-field set, status transition) flows through `audit_log.append(...)` carrying `requirement_id` + `actor_agent` (extends the existing producer wiring, task 52.3).
    - _Requirements: 34.3.1, REQ-AUDIT-001_
  - [ ] 65.2 Add a re-verification path: recompute `output_hash` on a sampled `proven` item; on divergence, drive the amendment-gated `proven → unproven` re-entry (requires a `requirement_versions` insert) and re-open the Plane issue.
    - _Requirements: 34.3.3, REQ-COV-007, Property 25_
  - [ ]* 65.3 **Property TRIPLE-3: Audit-Chain Detects Triple Rewrite.** Tamper a `gate_audit_log` row's `decision`/`requirement_id`; assert `audit_verify.verify_chain` fails at that `seq` and the `audit-chain-verify` CI check blocks merge. `# Feature: spec-to-evidence-control, Property TRIPLE-3`
    - _Requirements: 34.3.2, REQ-AUDIT-002_

- [ ] **66. Divergence reconciler + triple-orphan gate** (**REQ-TRIPLE-007/008**)
  - [ ] 66.1 Implement `tools/triple_reconcile.py`: detect per-leg divergence across mirrors; resolve by canonical-source precedence (file-canonical for AC/deps/priority/status per REQ-16.3, Postgres-canonical for the traceability graph/evidence, Plane as projection); on authoritative-store disagreement take the conservative `unproven`/`Blocked` result, audit `reason="triple_divergence"`, route to HANDOFF.
    - _Requirements: 34.4.1, 34.4.2, 34.4.3_
  - [ ] 66.2 Extend `orphan_detector.py`: add the `(external_source, external_id)` ⇄ `CoverageItem` bidirectional triple-orphan check; non-zero exit consumed by the REQUIRED `traceability-gate` CI check.
    - _Requirements: 34.5.1, REQ-6.3_
  - [ ] 66.3 Extend the W3C_Baggage span processor to additionally stamp `worktree_branch` + `agent_run_id` on triple-mutating spans.
    - _Requirements: 34.5.2, REQ-OBS-004_
  - [ ]* 66.4 **Property TRIPLE-4: Divergence Never Resolves To Proven.** Generate mirror states where the authoritative stores disagree; assert the reconciler always takes the conservative (`unproven`/`Blocked`) result and never auto-resolves toward `proven`/`Done`. `# Feature: spec-to-evidence-control, Property TRIPLE-4`
    - _Requirements: 34.4.2_

---

## Cross-references / grounding (file paths, absolute)

- Canonical requirements (32 EARS): `/Users/danielmanzela/Agentic-Driven SDLC Platform/.kiro/specs/spec-to-evidence-control/requirements.md`
- Canonical design (8-table Postgres DDL `design.md:562–676`; hash-chain `audit_verify.py` `design.md:1336–1358`; resumed-state integrity `design.md:1323–1332`; Error-Handling / N-25 never-fail-open `design.md:1362–1379`; `output_hash` semantics `design.md:531–539`): `/Users/danielmanzela/Agentic-Driven SDLC Platform/.kiro/specs/spec-to-evidence-control/design.md`
- Canonical tasks (57 tasks, 49 waves; audit-log task 52, migrations 28.x): `/Users/danielmanzela/Agentic-Driven SDLC Platform/.kiro/specs/spec-to-evidence-control/tasks.md`
- Plane self-host env (target deployment): `/Users/danielmanzela/Agentic-Driven SDLC Platform/plane-selfhost/plane.env`

## What these sections inherit vs. add

- **Inherits unchanged:** the fail-closed posture (REQ-GATE-005), N-25 never-fail-open fallback, the hash-chained `gate_audit_log` + `audit_verify.py`, `Evidence_Record.output_hash` canonicalization, the amendment-gated `proven → unproven` re-entry (Req 22 / Property 25), the `evidence_records.actor_agent` role-separation (Property 24), the PreCompact `resume_state_hash` producer + Requirement 23 resume integrity, and the W3C_Baggage `requirement.id` propagation.
- **Adds (net-new, no stubs):** two migrations (`009_webhook_deliveries.sql`, `010_outbound_queue.sql`); the `external_id`/`external_source` ⇄ `CoverageItem.id` binding; the `worktree_branch`/`agent_run_id` Plane custom-field legs of the triple; the inbound dedup/replay/reconcile path; the outbound token-bucket/429/queue path; the chunk-summarize-checkpoint sync path; the triple-divergence reconciler; and seven threshold-registry entries extending Requirement 20.3.

## Assumptions documented

- Webhook auth modeled as `X-Plane-Signature` = `HMAC-SHA256(raw_body, workspace_secret)` and dedup on `X-Plane-Delivery` (UUID) — the standard Plane webhook contract; if the self-hosted build exposes a different header casing, only the header constant in `plane_webhook.py` changes, not the EARS.
- Plane REST limits are not fixed in the self-host env, so the token-bucket DEFAULT (60 req/60 s/workspace) is set conservatively and registered as an operator-overridable threshold (Requirement 20.2 invariant honored).
- New requirements are numbered **33–34** and new properties tagged `RESIL-*` / `TRIPLE-*` to avoid colliding with the canonical 32 requirements / 30 properties / 34 Z3 checks; these are runtime/CI-verified (Hypothesis + integration), not added to the Z3 harness, so the **34/34** machine-checked count is unchanged (stated honestly, mirroring the spec's Property 26/28 "no Z3 check — runtime/CI verified" captions).

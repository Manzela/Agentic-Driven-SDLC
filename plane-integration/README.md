# Agentic SDLC Control Plane — Plane Integration

Self-hosted Plane (open-source Jira alternative) as the **PM control plane** for the
autonomous Spec-to-Evidence delivery engine. The reconciled `.kiro` spec (32 EARS
requirements / 32 properties / 8 tables / 57 tasks) is materialized as a live Plane
workspace, and agents drive work items through a 12-state agent workflow over the REST
API + webhooks.

## Layout

| File | Role |
|---|---|
| `../docs/plane/PLANE_BLUEPRINT.md` | The full blueprint: project config, 8 epics, 49 EARS user stories, 186 tasks, architecture, webhook/API payloads, completeness gates (state-transition, CRUD, failure-mode, traceability). |
| `../docs/plane/plane_backlog.json` | Structured backlog consumed by the provisioner. |
| `../plane-selfhost/docker-compose.yml` | Plane v1.3.1 community stack (13 services). |
| `provision_plane.py` | Idempotent REST provisioner (states/labels/epics/stories/tasks via `external_id`). |
| `plane_client.py` | Agent→Plane write-back; enforces the actor-authority model (only verifier sets `Done`). |
| `webhook_handler.py` | Plane→agent receiver; HMAC-SHA256 verify + `X-Plane-Delivery` dedup → dispatch queue. |
| `the_loop.py` | PM interface: `status` / `next` / `advance` / `prove` / `handoff` (completion-gate ordered). |

## Deploy

```bash
cd ../plane-selfhost
# plane.env already configured: LISTEN_HTTP_PORT=8090, APP_DOMAIN=localhost:8090, fresh SECRET_KEY
docker compose --env-file plane.env up -d        # 13 services; web on http://localhost:8090
```

Bootstrap (admin + workspace `ascp` + project `ASCP` + API token) is done headlessly via
the api container's Django ORM; credentials live in `../plane-selfhost/credentials.env`
(gitignored). Re-bootstrap by re-running the `manage.py shell` snippet in the session log.

## Provision

```bash
cd ../plane-integration
python3 provision_plane.py all     # idempotent; safe to re-run (external_id-keyed, 409-adopt)
python3 the_loop.py status         # 243 work items across the 12 states
```

## The autonomous loop

`the_loop.py next` returns the highest-priority actionable item; an agent does the real
`.kiro` work, then `prove <id> <test_file> <test_name> <output_hash>` attaches the 4-field
Evidence_Record and sets `Done` — **only** via the verifier with complete evidence.
cap/budget/no-progress route to `handoff` (terminal, distinct from `Done`), mirroring
`evaluate_stop`. Webhooks (event-driven) are the alternative trigger; from Docker, register
the webhook URL as `http://host.docker.internal:8099/plane-webhook`.

## Control vocabulary

12 states (`Backlog → Agent-Triaged → Spec-Compiling → Spec-Verified → Plan-Approved →
Agent-Executing → In-Verification → Human-Review → Done`, plus `HANDOFF` / `Blocked` /
`Failed`), 10 custom fields, 22 labels. See `PLANE_BLUEPRINT.md §1`.

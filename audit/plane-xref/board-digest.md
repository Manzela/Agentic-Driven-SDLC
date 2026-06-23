# Plane board digest — full item inventory (256 items)
Counts: {'states': 12, 'labels': 22, 'modules': 8, 'cycles': 7, 'work_items': 256}
States: Backlog, Done, Agent-Triaged, Spec-Compiling, Spec-Verified, Plan-Approved, Agent-Executing, In-Verification, Human-Review, HANDOFF, Blocked, Failed
Modules(epics): 8 | Cycles(phases): 7 | Labels: 22


================================================================================
[8] «Agent-Triaged» {priority:high} epic:E1
   [E1] Core Plane Infrastructure & Self-Hosting
   ↳ Core Plane Infrastructure & Self-Hosting
  [16] «Plan-Approved» {phase:0,priority:blocking,type:wiring,human:review} story:REQ-INFRA-001
     REQ-INFRA-001: Self-Hosted Docker Topology Stand-Up
     ↳ EARS requirements [ubiquitous] THE system shall define every long-lived Plane service (web, space, admin, live, api, worker, beat-worker, plane-db, plane-redis, plane-mq, plane-minio, proxy) in docker-compose.yml with restart_policy.condition: any, and the one-shot migrator with …
    [65] «Backlog» {phase:0} task:REQ-INFRA-001#0
       REQ-INFRA-001.1 Validate and bring up the full compose topology
       ↳ Category: Infrastructure Subtasks Run docker compose --env-file plane.env config and resolve all x-* anchors docker compose up -d and confirm all 12 long-lived services running plus migrator Exited(0) via docker compose ps Verify the ten named volumes are created and bound to the…
    [66] «Backlog» {phase:0} task:REQ-INFRA-001#1
       REQ-INFRA-001.2 Verify dependency ordering and restart resilience
       ↳ Category: Infrastructure Subtasks Stop plane-db and observe api reconnect attempts in logs_api Full restart and confirm all-running recovery Confirm restart_policy:any on long-lived services and on-failure on migrator; pin APP_RELEASE and backing-store image tags
    [67] «Backlog» {phase:2} task:REQ-INFRA-001#2
       REQ-INFRA-001.3 Create the E1 tracking issue in Plane
       ↳ Category: Orchestration Subtasks Create ASCP issue 'REQ-INFRA-001 Topology stand-up' Set requirement_id=REQ-INFRA-001, agent_role=human, coverage_type=WIRING; apply labels priority:blocking, phase:0, type:wiring Advance Backlog -> Agent-Triaged -> Plan-Approved
  [17] «Plan-Approved» {phase:0,priority:blocking,type:wiring,gate:security,human:review} story:REQ-INFRA-002
     REQ-INFRA-002: Reverse Proxy & Port-8090 Ingress
     ↳ EARS requirements [ubiquitous] THE system shall publish the proxy service container port 80 on host port LISTEN_HTTP_PORT set to 8090, and container port 443 on host port LISTEN_HTTPS_PORT set to 8453, in host mode. [event-driven] WHEN a request arrives at http://localhost:8090, …
    [68] «Backlog» {phase:0} task:REQ-INFRA-002#0
       REQ-INFRA-002.1 Configure proxy ingress on 8090/8453
       ↳ Category: Infrastructure Subtasks Set LISTEN_HTTP_PORT=8090 and LISTEN_HTTPS_PORT=8453 Confirm proxy publishes only 8090->80 and 8453->443 in host mode and no internal port is host-published Confirm proxy_config/proxy_data persist across restart
    [69] «Backlog» {phase:0} task:REQ-INFRA-002#1
       REQ-INFRA-002.2 Wire origin/CORS to the 8090 ingress
       ↳ Category: Infrastructure Subtasks Set APP_DOMAIN=localhost:8090, WEB_URL=http://localhost:8090, CORS_ALLOWED_ORIGINS=http://localhost:8090 Verify CORS accepts the 8090 origin and rejects others Optionally wire CERT_EMAIL/CERT_ACME_CA or CERT_ACME_DNS for HTTPS on 8453
    [70] «Backlog» {phase:1} task:REQ-INFRA-002#2
       REQ-INFRA-002.3 Verify proxied routes
       ↳ Category: API Subtasks curl -sf http://localhost:8090/ returns 200 curl -sf http://localhost:8090/api/instances/ returns JSON from api:8000 Confirm /spaces, /god-mode, /live route to space/admin/live
  [18] «Plan-Approved» {phase:0,priority:blocking,type:nfr,gate:security,human:review} story:REQ-INFRA-003
     REQ-INFRA-003: Environment-Driven Configuration & Secrets
     ↳ EARS requirements [ubiquitous] THE system shall resolve all service configuration from plane.env via the compose ${VAR:-default} mechanism and the x-* anchor blocks, with no credential or secret literal embedded in docker-compose.yml beyond a clearly-marked dev default. [event-dr…
    [71] «Backlog» {phase:0} task:REQ-INFRA-003#0
       REQ-INFRA-003.1 Externalize and rotate secrets
       ↳ Category: Infrastructure Subtasks Confirm all credentials sourced from plane.env Rotate SECRET_KEY, LIVE_SERVER_SECRET_KEY, POSTGRES_PASSWORD, RABBITMQ_PASSWORD, AWS_SECRET_ACCESS_KEY off shipped defaults Verify overrides propagate to api effective env; set DEBUG=0
    [72] «Backlog» {phase:0} task:REQ-INFRA-003#1
       REQ-INFRA-003.2 Prove no secret leakage (REQ-17.5 substrate guard)
       ↳ Category: Infrastructure Subtasks Grep running-container env + proxy/app access logs for any password/SECRET_KEY in a URL or log line; assert clean Verify DATABASE_URL/AMQP_URL/REDIS_URL resolve both blank-defaulted and explicitly set
    [73] «Backlog» {phase:1} task:REQ-INFRA-003#2
       REQ-INFRA-003.3 Configure webhook egress allowlists
       ↳ Category: API Subtasks Set WEBHOOK_ALLOWED_IPS/WEBHOOK_ALLOWED_HOSTS Confirm a non-allowlisted private-IP webhook target is refused (SSRF guard) and an allowlisted target is permitted
  [19] «Plan-Approved» {phase:0,priority:blocking,type:functional,human:review} story:REQ-INFRA-004
     REQ-INFRA-004: Durable Storage Tier (Postgres + MinIO + RabbitMQ + Redis)
     ↳ EARS requirements [ubiquitous] THE system shall back plane-db with the pgdata volume, plane-redis with redisdata, plane-mq with rabbitmq_data, and plane-minio with the uploads volume, so all durable state outlives any container restart or recreation. [event-driven] WHEN an eviden…
    [74] «Backlog» {phase:0} task:REQ-INFRA-004#0
       REQ-INFRA-004.1 Provision the four durable tiers on named volumes
       ↳ Category: Infrastructure Subtasks Confirm pgdata/redisdata/rabbitmq_data/uploads bind to their services pg_isready + max_connections=1000 on plane-db; PING on Valkey; RabbitMQ plane user/vhost reachable on 5672 Create/confirm the MinIO uploads bucket
    [75] «Backlog» {phase:0} task:REQ-INFRA-004#1
       REQ-INFRA-004.2 Prove volume durability across recreate
       ↳ Category: Infrastructure Subtasks Write a marker Postgres row and marker MinIO object docker compose down (no -v) then up -d Confirm both survive and capture survival as the Evidence_Record
    [76] «Backlog» {phase:1} task:REQ-INFRA-004#2
       REQ-INFRA-004.3 Verify evidence-blob content-addressing round-trip
       ↳ Category: API Subtasks Put an object into uploads keyed by a sha256: hash via the S3 endpoint Get it back and assert byte-identical (REQ-16.2 content-addressed-reference contract)
  [20] «Spec-Verified» {phase:0,type:wiring} story:REQ-INFRA-005
     REQ-INFRA-005: Database Migration & Version Upgrade
     ↳ True-up: AC#4 previously claimed a companion migration set (eight .kiro migrations 001-008) exists and applies; ZERO *.sql files exist. Reframe AC#4 to depend on NEW-12 authoring the migrations; do not assert applied state until the files exist.
    [77] «Backlog» {phase:0} task:REQ-INFRA-005#0
       REQ-INFRA-005.1 Run and verify first-deploy migrations
       ↳ Category: Infrastructure Subtasks Confirm migrator applies Plane schema and exits 0 Assert api starts with no missing-relation errors Assert re-run is idempotent (no-op migration, exit 0)
    [78] «Backlog» {phase:0} task:REQ-INFRA-005#1
       REQ-INFRA-005.2 Execute and verify a version upgrade
       ↳ Category: Infrastructure Subtasks Bump APP_RELEASE and pull new makeplane/plane-* images Run migrator against existing pgdata; confirm the REQ-INFRA-004 marker row survives the upgrade Verify a deliberately-broken migration exits non-zero and holds the app tier
    [79] «Backlog» {phase:0} task:REQ-INFRA-005#2
       REQ-INFRA-005.3 Apply the companion eight-table .kiro migrations idempotently
       ↳ Category: Infrastructure Subtasks Adopt a tracked forward-only runner with schema_migrations bookkeeping; apply 001-008 Assert all eight tables exist (requirements, coverage_items, traceability_links, evidence_records, run_state, domain_baseline_checklists, requirement_versions, …
  [21] «Plan-Approved» {phase:0,priority:high,type:nfr,human:review} story:REQ-INFRA-006
     REQ-INFRA-006: Backup & Restore of the Durable Tier
     ↳ EARS requirements [ubiquitous] THE system shall produce a consistent logical backup of the plane database (pg_dump) and a complete mirror of the MinIO uploads bucket, both written to a location outside the Docker volumes. [event-driven] WHEN a backup job runs, the system shall ca…
    [80] «Backlog» {phase:0} task:REQ-INFRA-006#0
       REQ-INFRA-006.1 Build the backup jobs
       ↳ Category: Infrastructure Subtasks Schedule pg_dump of the plane database to an out-of-volume location Mirror the MinIO uploads bucket; record each backup's timestamp + integrity checksum Optionally archive Postgres WAL for PITR
    [81] «Backlog» {phase:0} task:REQ-INFRA-006#1
       REQ-INFRA-006.2 Prove a full destroy-and-restore round-trip
       ↳ Category: Infrastructure Subtasks Seed a marker row + evidence object and back up docker compose down -v, restore into fresh volumes, up -d Confirm marker row + object + schema recovered; assert a corrupted backup is rejected
    [82] «Backlog» {phase:2} task:REQ-INFRA-006#2
       REQ-INFRA-006.3 Document the restore runbook and retention
       ↳ Category: Orchestration Subtasks Write the end-to-end restore procedure State retention >= the 365-day audit-log window Link the runbook from the E1 issue; advance to Done only with the round-trip Evidence_Record attached
  [22] «Plan-Approved» {phase:0,priority:normal,type:nfr,human:review} story:REQ-INFRA-007
     REQ-INFRA-007: Horizontal Scaling via Replicas
     ↳ EARS requirements [ubiquitous] THE system shall honor WEB_REPLICAS, SPACE_REPLICAS, ADMIN_REPLICAS, API_REPLICAS, WORKER_REPLICAS, BEAT_WORKER_REPLICAS, and LIVE_REPLICAS from plane.env as the replica count for each corresponding service's deploy.replicas. [event-driven] WHEN API…
    [83] «Backlog» {phase:0} task:REQ-INFRA-007#0
       REQ-INFRA-007.1 Exercise stateless-tier replica scaling
       ↳ Category: Infrastructure Subtasks Set API_REPLICAS=2, re-apply, confirm two api containers running and proxy load-balancing Set WORKER_REPLICAS=2, confirm two RabbitMQ consumers and distributed tasks Scale back down gracefully
    [84] «Backlog» {phase:0} task:REQ-INFRA-007#1
       REQ-INFRA-007.2 Enforce stateful-tier single-instance invariant
       ↳ Category: Infrastructure Subtasks Confirm plane-db/plane-redis/plane-mq/plane-minio stay replicas:1 Confirm beat-worker defaults to one replica Verify scaling worker does not duplicate scheduled (beat) tasks
    [85] «Backlog» {phase:2} task:REQ-INFRA-007#2
       REQ-INFRA-007.3 Record scaling envelope on the issue
       ↳ Category: Orchestration Subtasks Document the per-tier replica knobs and the stateful single-instance constraint Set coverage_type=NFR Attach the multi-replica running-state evidence
  [23] «Plan-Approved» {phase:0,priority:blocking,type:wiring,gate:completion,human:review} story:REQ-INFRA-008
     REQ-INFRA-008: Health, Readiness & Liveness Verification
     ↳ EARS requirements [ubiquitous] THE system shall expose a readiness verification that checks in one pass: plane-db accepts connections, plane-redis answers PING, plane-mq is reachable, plane-minio serves its health endpoint, migrator has exited 0, and the proxy serves http://local…
    [86] «Backlog» {phase:0} task:REQ-INFRA-008#0
       REQ-INFRA-008.1 Build the one-pass readiness check
       ↳ Category: Infrastructure Subtasks Script checks for plane-db connect, Valkey PING, RabbitMQ reachable, MinIO health, migrator Exited(0), proxy serving / Exit 0 only on all-healthy Optionally add container healthcheck blocks surfaced in ps
    [87] «Backlog» {phase:0} task:REQ-INFRA-008#1
       REQ-INFRA-008.2 Verify failure detection
       ↳ Category: Infrastructure Subtasks Kill each backing store in turn; assert readiness flips to FAIL naming that tier Assert a proxy 5xx identifies the unhealthy upstream from logs
    [88] «Backlog» {phase:1} task:REQ-INFRA-008#2
       REQ-INFRA-008.3 Verify the REST/Webhook surface is live and gate the downstream epic
       ↳ Category: API Subtasks curl http://localhost:8090/api/instances/ returns 200/JSON Confirm webhook egress allowlist target is configured Capture readiness PASS as the gating Evidence_Record that unblocks the workspace-provisioning epic; advance the readiness issue to Done

================================================================================
[9] «Agent-Triaged» {priority:high} epic:E2
   [E2] Agentic Workspace & Governance Model
   ↳ Agentic Workspace & Governance Model
  [24] «Spec-Verified» {phase:0,type:wiring} story:E2-S1
     E2-S1: Inner-loop orchestration run by Claude Code primitives, mirrored as one issue per inner loop
     ↳ Contradiction fix (C2): AC4 claims the inner loop ('one Plane issue = 4 subagents + 6 hooks') is reachable with integration-test evidence — false as-on-disk (no .claude/settings.json; .claude/agents/ is .gitkeep-only). Add the explicit dependency on E8-13 (A1) + NEW-05 (A7); refr…
    [89] «Backlog» {phase:0} task:E2-S1#0
       E2-S1.1 Provision the ASCP workflow, fields & labels
       ↳ Category: Infrastructure Subtasks Create project 'Agentic SDLC Control Plane' (identifier ASCP) with the exact description. Create the 12 custom states mapped to correct Plane state-groups, with HANDOFF/Blocked/Failed distinct cancelled-group terminals. Create the 10 custom prope…
    [90] «Backlog» {phase:2} task:E2-S1#1
       E2-S1.2 Wire the single-inner-loop projection
       ↳ Category: Orchestration Subtasks Bind one Plane issue = one inner loop (4 subagents + 6 hooks); no external reasoning framework on the default path. Stamp worktree_branch + agent_run_id on Plan-Approved -> Agent-Executing; reject the transition if either is empty. Model Temporal/…
    [91] «Backlog» {phase:1} task:E2-S1#2
       E2-S1.3 Transition-authorization webhook
       ↳ Category: API Subtasks Subscribe to issue state-change webhooks; resolve actor agent_role against the role/transition matrix and reverse unauthorized transitions via PATCH. Reject any transition originating from a prediction/Agent_Teams/external framework; record the blocking rea…
  [25] «Spec-Verified» {phase:0,type:wiring} story:E2-S2
     E2-S2: Capability-role taxonomy maps to Plane roles/permissions and authorizes state transitions
     ↳ Contradiction fix (C4): AC2's verifier carve-out keyed on actor_agent == verifier.md works only if the verifier frontmatter name is verifier.md AND CLAUDE_AGENT_NAME carries that suffix. As-on-disk no .claude/agents/*.md exist. Add a hard dependency on NEW-05 (COH-1 reconciliatio…
    [92] «Backlog» {phase:0} task:E2-S2#0
       E2-S2.1 Map agent_role -> Plane roles/permissions
       ↳ Category: Infrastructure Subtasks Create Plane workspace members for each role; map agent roles to Member-level, human to Admin. Encode the role/transition-authority matrix as the canonical config consumed by the authorization webhook.
    [93] «Backlog» {phase:2} task:E2-S2#1
       E2-S2.2 Optional bounded-role scaffolding
       ↳ Category: Orchestration Subtasks Define optional design/platform/reliability agent markdown templates with explicit tools allowlists granting no impl-source write and no verifier write. Add a smoke test that parses each role markdown and asserts no verifier write access; keep the…
    [94] «Backlog» {phase:1} task:E2-S2#2
       E2-S2.3 Role-scoped transition + write-scope enforcement
       ↳ Category: API Subtasks On state-change and field-write webhooks, enforce that only verifier writes evidence_status=proven / tests/ / evidence; block implementer self-verification (mirror SubagentStop Property 24). Stamp agent_role + requirement_id automatically on Backlog -> Agen…
  [26] «Spec-Verified» {phase:0,type:functional,gate:completion,human:review} story:E2-S3
     E2-S3: Human-in-the-Loop approval gates are deterministic and human-only
     ↳ Contradiction + redundancy fix (C3/R3): AC3 lists deepeval-gate among required completion checks — directly contradicts intent-model 2.5 and the charter's 'predictions never gate' (deepeval is QUALITY-only). It also hardcodes a static 7-check list (violates CH-15 'lists from a re…
    [95] «Backlog» {phase:0} task:E2-S3#0
       E2-S3.1 Human-only gate configuration
       ↳ Category: Infrastructure Subtasks Restrict Spec-Verified -> Plan-Approved and Human-Review -> Done to Admin (human) in Plane; configure the GitHub ruleset required reviewer + required-status-checks list (single-sourced from tasks.md task 14.2). Configure the flagd kill-switch fla…
    [96] «Backlog» {phase:2} task:E2-S3#1
       E2-S3.2 Plan-approval SHA-binding gate
       ↳ Category: Orchestration Subtasks On Plan-Approved -> Agent-Executing, verify plan-approved.json exists AND feature_list_sha matches current feature_list.json SHA-256; on mismatch/missing, route to Blocked with gate:completion. On the next session, ensure the Initializer consumes …
    [97] «Backlog» {phase:1} task:E2-S3#2
       E2-S3.3 HITL + kill-switch audit/observability webhook
       ↳ Category: API Subtasks On the two human-only transitions and every kill-switch toggle, append a gate_audit_log entry (event, actor, decision, reason, requirement_id, created_at) and emit an OTel gate-decision event; reflect the result in the issue run_state/gate field. Gate Human…

================================================================================
[10] «Agent-Triaged» {priority:high} epic:E3
   [E3] Intent→Spec Compilation & Coverage Model
   ↳ Intent→Spec Compilation & Coverage Model
  [27] «Spec-Compiling» {phase:0,type:functional} story:ASCP-E3-1
     ASCP-E3-1: Spec Compilation — terse intent to atomic EARS requirements
     ↳ Precondition block added (C5): execution-ready only AFTER NEW-08 (spec_validator.py) + NEW-12 (migrations) + the spine (E8-13). Reframe the EARS/vague-adjective work as consuming tools/spec_validator.py, not re-authoring it.
    [98] «Backlog» {phase:0} task:ASCP-E3-1#0
       ASCP-E3-1.1 EARS schema + spec.json/requirements.md artifact format
       ↳ Category: Infrastructure Subtasks Define schema/feature_list.schema.json CoverageItem id pattern ^[A-Z]+-[A-Z]+-[0-9]{3}$ and the five-value ears_pattern enum (task 2.1) Pin the on-disk compiled-requirements artifacts: specs/<feature>/spec.json (validator input contract) + .kiro/…
    [99] «Backlog» {phase:2} task:ASCP-E3-1#1
       ASCP-E3-1.2 spec_validator.py EARS encoder + vague-adjective scanner
       ↳ Category: Orchestration Subtasks Implement tools/spec_validator.py EARS pattern encoder mapping each of the five patterns to a Z3 Boolean formula (task 4.1) Implement the vague-adjective scanner over {fast,secure,scalable,optimized,efficient,reliable,performant} with +/-6-token n…
    [100] «Backlog» {phase:1} task:ASCP-E3-1#2
       ASCP-E3-1.3 Plane triage + state sync on spec compilation
       ↳ Category: API Subtasks Configure ASCP Plane states Backlog/Agent-Triaged/Spec-Compiling and the agent_role + requirement_id + ears_pattern custom fields via the Plane REST API Wire the initializer to set requirement_id, agent_role=initializer, and ears_pattern on the issue via Pl…
  [28] «Spec-Compiling» {phase:0,type:functional} story:ASCP-E3-2
     ASCP-E3-2: Proactive Discovery — infer implied baseline requirements; UNMAPPED blocks advancement
     ↳ Precondition block (C5): execution-ready only after NEW-08 + NEW-12 + spine. UNMAPPED completeness + provenance rejection consume tools/spec_validator.py.
    [101] «Backlog» {phase:2} task:ASCP-E3-2#0
       ASCP-E3-2.1 UNMAPPED detection + advancement block
       ↳ Category: Orchestration Subtasks Implement spec_validator.py completeness check (UNMAPPED detection) over the baseline-checklist expansion (task 4.1) Author initializer.md discovery step (c): expand intent against the approved checklist and flag UNMAPPED baseline items (task 10.1…
    [102] «Backlog» {phase:2} task:ASCP-E3-2#1
       ASCP-E3-2.2 Provenance marking + per-inferred human confirmation
       ↳ Category: Orchestration Subtasks Author initializer.md step (d): mark provenance (stated/inferred) and gate each inferred item on per-item human confirmation before it enters feature_list.json (Req 2.3, task 10.1) Make spec_validator.py reject any inferred requirement lacking a p…
    [103] «Backlog» {phase:1} task:ASCP-E3-2#2
       ASCP-E3-2.3 Plane discovery board + UNMAPPED blocking label
       ↳ Category: API Subtasks Create Plane sub-issues per inferred requirement with provenance reflected in a label (type:functional + an inferred/stated marker) via REST Apply the priority:blocking label to any UNMAPPED baseline item issue and prevent the parent epic moving to Plan-App…
  [29] «Spec-Compiling» {phase:0,priority:high,type:functional,agent:research,gate:completion} story:ASCP-E3-3
     ASCP-E3-3: Domain-Baseline Checklist Sourcing — researched, version-controlled, approval-gated
     ↳ EARS requirements [event-driven] WHEN a new product class is encountered for the first time, the system shall run the research subagent to query competitive analysis, industry standards, and OSS reference implementations and draft a Domain_Baseline_Checklist, presenting the draft…
    [104] «Backlog» {phase:2} task:ASCP-E3-3#0
       ASCP-E3-3.1 research.md subagent + web-tool grant + checklist persistence
       ↳ Category: Orchestration Subtasks Author .claude/agents/research.md with frontmatter (name/description/model/tools) granting a web-search/fetch tool plus baselines/ read-write (task 10.4) Implement: triggered by Initializer on a new product class; query competitive analysis + stan…
    [105] «Backlog» {phase:0} task:ASCP-E3-3#1
       ASCP-E3-3.2 Checklist version-history table + approval gate + claim validator
       ↳ Category: Infrastructure Subtasks Write migration db/migrations/006_domain_baseline_checklists.sql with UNIQUE(product_class, version), nullable approved_at, approved_by, sha, file_path (task 28.6) Implement check_checklist_approval(event) in pre_tool_use_hook.py: block discovery…
    [106] «Backlog» {phase:1} task:ASCP-E3-3#2
       ASCP-E3-3.3 Plane research workflow + human approval handoff
       ↳ Category: API Subtasks Create a Plane research issue assigned to agent:research with gate:completion label representing the checklist-approval gate On draft completion, transition to a human:review assignee and require human approval (writing approved_at) before the parent discov…
  [30] «Spec-Compiling» {phase:0,type:functional} story:ASCP-E3-4
     ASCP-E3-4: Spec-Completion Loop — bounded, Z3-judged, fail-closed to HANDOFF
     ↳ Precondition block (C5) + contradiction fix (C6): AC-3 named the Initializer as producer of run_state.violation_count/prev_violation_count, partially contradicting D3 (no populator). Reconcile: the initializer EMITS via the D3 populator (NEW-02), it does not write run_state direc…
    [107] «Backlog» {phase:2} task:ASCP-E3-4#0
       ASCP-E3-4.1 spec_validator.py structured verdict + timeout sentinel
       ↳ Category: Orchestration Subtasks Implement validate_spec(requirements) -> {contradictions, ambiguities, uncovered, violation_count} with consistency/completeness/vacuity/independence checks (task 4.1) Set the Z3 solver timeout to DEFAULT 60s; return {violation_count: -1, error: v…
    [108] «Backlog» {phase:2} task:ASCP-E3-4#1
       ASCP-E3-4.2 Stop-hook block + strict-decrease/cap HANDOFF tiebreak
       ↳ Category: Orchestration Subtasks Implement stop_hook.py evaluate_stop Check 1: violation_count > 0 before cap -> exit 2 (block, force continuation) with enumerated IDs (task 5.1) Implement the lex-specialis cap path: at spec_pass_count >= 7 with violation_count > 0 -> write statu…
    [109] «Backlog» {phase:2} task:ASCP-E3-4#2
       ASCP-E3-4.3 feature_list.json emission + plan-mode handoff
       ↳ Category: Orchestration Subtasks On violation_count == 0, emit the validated spec.json + feature_list.json (all items unproven) and enter plan mode (initializer step g, task 10.1) Ensure the initializer does NOT write plan-approved.json (human-only) and surfaces remaining violati…
    [110] «Backlog» {phase:1} task:ASCP-E3-4#3
       ASCP-E3-4.4 Plane Spec-Verified transition + HANDOFF state
       ↳ Category: API Subtasks On violation_count == 0, transition the Plane issue Spec-Compiling -> Spec-Verified and set run_state field complete via REST On cap/no-progress HANDOFF, transition the Plane issue to the HANDOFF state, apply the handoff label, set run_state=handoff, and as…
  [31] «Spec-Compiling» {phase:0,type:functional} story:ASCP-E3-5
     ASCP-E3-5: Coverage Model — feature_list.json, default unproven, four-field evidence, append-only guard
     ↳ Redundancy reframe (R2): schema/feature_list.schema.json ALREADY implements the four-field EvidenceRecord (additionalProperties:false), the WIRING->integration evidence_kind allOf, and the nfr_subtype/subtype/declared_states allOf. Reframe E3-5's schema task as verify-and-extend,…
    [111] «Backlog» {phase:0} task:ASCP-E3-5#0
       ASCP-E3-5.1 feature_list.schema.json + four-field Evidence_Record + allOf clauses
       ↳ Category: Infrastructure Subtasks Implement schema/feature_list.schema.json: CoverageItem (id, type enum, priority, dependencies, acceptance_criteria minItems 1, status enum {unproven,proven,failed} default unproven, in_scope default true) (task 2.1) Implement EvidenceRecord with…
    [112] «Backlog» {phase:2} task:ASCP-E3-5#1
       ASCP-E3-5.2 PreToolUse status guard + append-only (check_append_only)
       ↳ Category: Orchestration Subtasks Implement check_status_transition(event) in pre_tool_use_hook.py: permit only {unproven->proven, unproven->failed, failed->unproven}; only *->proven requires complete evidence (task 6.1) Implement check_append_only: diff incoming items[] id-sequen…
    [113] «Backlog» {phase:2} task:ASCP-E3-5#2
       ASCP-E3-5.3 WIRING/NFR first-class emission + in_scope gate counting
       ↳ Category: Orchestration Subtasks Author initializer.md step (e): emit WIRING and NFR coverage items as first-class entries (not comments) per Property 1 (Req 5.4, task 10.1) Ensure all completion/Stop/OPA gates count ONLY in_scope items and that in_scope=false is a human-authored…
    [114] «Backlog» {phase:1} task:ASCP-E3-5#3
       ASCP-E3-5.4 Plane coverage-item mirror + evidence_status field
       ↳ Category: API Subtasks Mirror each feature_list.json item into a Plane issue with coverage_type (functional/NFR/WIRING) and evidence_status=unproven via REST on emission Configure the evidence_status (unproven/proven/failed) and coverage_type custom fields and the type:functional…
  [32] «Spec-Compiling» {phase:0,type:functional} story:ASCP-E3-22
     ASCP-E3-22: Requirement-Amendment Versioning — re-enter unproven, block COMPLETE until reproven
     ↳ Precondition block (C5): assumes a live webhook board + firing initializer/research/SubagentStop hooks; research_claim_validator.py, amendment_handler.py, migrations 005/006/007, baselines/ are ALL ABSENT. Add the explicit DEFERRED-prereq dependency list.
    [115] «Backlog» {phase:0} task:ASCP-E3-22#0
       ASCP-E3-22.1 requirement_versions table (append-only) + handler
       ↳ Category: Infrastructure Subtasks Write migration 007_requirement_versions.sql: requirement_id FK, version INTEGER (monotonic), prior_text, new_text NOT NULL, author NOT NULL, rationale NOT NULL, created_at DEFAULT now(), UNIQUE(requirement_id, version) (task 28.7) Add append-onl…
    [116] «Backlog» {phase:2} task:ASCP-E3-22#1
       ASCP-E3-22.2 Status-guard amendment edge + feature_list.json flip
       ↳ Category: Orchestration Subtasks Extend the PreToolUse status guard to permit proven->unproven ONLY when accompanied by a requirement_versions insert; block a bare flip (Property 3/25, design status-guard row) Make the amendment writer also flip the corresponding feature_list.jso…
    [117] «Backlog» {phase:2} task:ASCP-E3-22#2
       ASCP-E3-22.3 Amendment-monotonicity verification
       ↳ Category: Orchestration Subtasks Add Property 25 test (task 39.15): each amended item re-enters unproven and COMPLETE is blocked while any amended item is un-reproven; assert monotonic re-proof Bind to Z3 CHECK-10a (amended-but-unproven cannot be COMPLETE, UNSAT) and CHECK-10b (r…
    [118] «Backlog» {phase:1} task:ASCP-E3-22#3
       ASCP-E3-22.4 Plane amendment re-entry + COMPLETE block
       ↳ Category: API Subtasks On a human amendment, transition the Plane issue Done -> Spec-Compiling, flip evidence_status proven->unproven, and record author/rationale in a comment via REST Restrict the amendment action to the human:review actor (named accountable operator), not an au…

================================================================================
[11] «Agent-Triaged» {priority:high} epic:E4
   [E4] Verification Engine & Evidence
   ↳ Verification Engine & Evidence
  [33] «Spec-Verified» {phase:0,type:wiring,gate:completion} story:ASCP-E4-S1
     ASCP-E4-S1: Force one bounded slice at a time in an isolated worktree, scope-sequenced behind deterministic gates
     ↳ Contradiction fix (C15): ACs reference hooks firing (PreToolUse exit 2, SubagentStop exit 2/0) as if the spine is registered; no settings.json exists. Also: evidence_collector.collect() on disk is collect(test_file, test_name, output) with NO evidence_kind/actor_agent params — S1…
    [119] «Backlog» {phase:0} task:ASCP-E4-S1#0
       ASCP-E4-S1.1 Author .claude/agents/implementer.md coding subagent
       ↳ Category: Infrastructure Subtasks Write frontmatter (name: implementer, model: claude-opus-4-8, tools: [Read, Grep, Glob, Edit, Write, Bash]) and permission scope (worktree-only; no tests/, schema/, CI, other worktrees) Write key behaviors: highest-priority-unproven selection pre…
    [120] «Backlog» {phase:0} task:ASCP-E4-S1#1
       ASCP-E4-S1.2 Implement tools/worktree_manager.py
       ↳ Category: Infrastructure Subtasks Implement create_worktree(item_id), remove_worktree(item_id), list_active_worktrees() Enforce one worktree per active slice; fail if a worktree already exists for item_id Write integration tests: create -> list shows one entry; remove -> delisted…
    [121] «Backlog» {phase:0} task:ASCP-E4-S1#2
       ASCP-E4-S1.3 Sandbox & worktree isolation enforcement (REQ-17.4)
       ↳ Category: Infrastructure Subtasks Confine agent-executed filesystem writes to the per-slice git worktree mounted into the sandbox (devcontainer local / E2B CI) Deny network egress by default Tie the confinement to the one-slice/one-worktree implementer discipline
    [122] «Backlog» {phase:1} task:ASCP-E4-S1#3
       ASCP-E4-S1.4 PreToolUse plan-approval gate (check_plan_approval)
       ↳ Category: API Subtasks Block any Write/Edit/MultiEdit when plan-approved.json is missing OR feature_list_sha mismatches current feature_list.json SHA-256 Write property test Property 6 (Plan Approval Gate) Emit a Plane REST/webhook update mapping the block to gate=pretooluse and …
    [123] «Backlog» {phase:1} task:ASCP-E4-S1#4
       ASCP-E4-S1.5 PreToolUse scope-sequencing gate (check_scope_sequencing)
       ↳ Category: API Subtasks Block git worktree add / worktree_manager.create_worktree / slice-assign when any prior-slice item is unproven; cover bypass forms Write bypass-form property test Property 7 (Scope Sequencing Gate) Pin guard chain order (integrity -> plan -> scope -> artifa…
    [124] «Backlog» {phase:2} task:ASCP-E4-S1#5
       ASCP-E4-S1.6 Phase-0 spine smoke + e2e for the gates
       ↳ Category: Orchestration Subtasks Write tests/smoke/test_spine_e2e.py: no plan-approved.json -> Write exits 2; valid marker -> exits 0; worktree-create while prior unproven -> exits 2 Write tests/integration/test_phase0_integration.py covering the same gate paths Assert stderr nam…
  [34] «Spec-Verified» {phase:0,type:wiring} story:ASCP-E4-S2
     ASCP-E4-S2: Detect compile-but-unwired handlers/routes/jobs/callbacks and require integration-test evidence to prove WIRING items
     ↳ Redundancy reframe (R1+R2): E4-S2's A6 wiring leg now EXTENDS the unified hook (NEW-10), not re-registers it. The 'Enforce WIRING->integration at the CoverageItem allOf' task is reframed verify-and-extend — schema/feature_list.schema.json already implements it.
    [125] «Backlog» {phase:0} task:ASCP-E4-S2#0
       ASCP-E4-S2.1 Implement tools/wiring_checker.py
       ↳ Category: Infrastructure Subtasks Accept changed files as argv (one path per positional arg) Build per-file Python AST call/usage graphs and MERGE into one repo-wide reachability graph Seed entry points (CLI __main__, decorators, registered hook commands, registered callbacks); e…
    [126] «Backlog» {phase:0} task:ASCP-E4-S2#1
       ASCP-E4-S2.2 Write tools/semgrep_rules/wiring_dead_code.yml
       ↳ Category: Infrastructure Subtasks Rule for route/handler decorators never imported/called from a non-test entry point Rule for callbacks registered in a dict/list but never invoked Test rules against tests/fixtures/semgrep/ and de-duplicate by symbol against wiring_checker.py
    [127] «Backlog» {phase:1} task:ASCP-E4-S2#2
       ASCP-E4-S2.3 PostToolUse changed-files handoff to wiring_checker.py
       ↳ Category: API Subtasks Derive the changed-file list from the hook payload (tool_input.file_path for Write/Edit; full edited-path set for MultiEdit) Pass changed files as argv to wiring_checker.py and collect findings Emit structured feedback; exit 1 (never exit 2); exception -> e…
    [128] «Backlog» {phase:2} task:ASCP-E4-S2#3
       ASCP-E4-S2.4 WIRING-candidate ingestion into feature_list.json
       ↳ Category: Orchestration Subtasks Implementer/initializer adds a type: WIRING CoverageItem on receiving a PostToolUse WIRING candidate Default status unproven, in_scope true, >=1 acceptance criterion (Property 1 conformance) Write via the PreToolUse status-guard-permitted creation…
    [129] «Backlog» {phase:2} task:ASCP-E4-S2#4
       ASCP-E4-S2.5 Verifier WIRING handling (consume findings, fail/prove)
       ↳ Category: Orchestration Subtasks Verifier consumes (or re-runs) wiring_checker findings on each slice For any unreachable WIRING symbol, perform unproven -> failed (permitted by the status guard) For a provable WIRING item, require and attach an integration-test Evidence_Record (…
    [130] «Backlog» {phase:2} task:ASCP-E4-S2#5
       ASCP-E4-S2.6 Phase-1 wiring integration test
       ↳ Category: Orchestration Subtasks Write the wiring leg of tests/integration/test_phase1_integration.py: defined-but-never-called function -> WIRING finding Assert the finding contains type: WIRING and the symbol name Assert a Plane WIRING issue is created with coverage_type = WIRI…
  [35] «Spec-Verified» {phase:0,type:wiring} story:ASCP-E4-S3
     ASCP-E4-S3: Verify each slice across five independent layers and capture a complete Evidence_Record; the implementer never grades its own homework
     ↳ Redundancy reframe (R1): E4-S3's five-layer leg EXTENDS the unified A6 hook (NEW-10). Also reframe the evidence/schema tasks verify-and-extend (R2) and add the spine precondition (C15). verifier.md frontmatter authored under NEW-05.
    [131] «Backlog» {phase:0} task:ASCP-E4-S3#0
       ASCP-E4-S3.1 Author .claude/agents/verifier.md independent evaluator
       ↳ Category: Infrastructure Subtasks Write frontmatter (name: verifier, model: claude-opus-4-8, tools: [Read, Grep, Glob, Bash]) and permission scope (read-only src/; tests/ + feature_list.json status+evidence via artifact-guard carve-out) Write layers 1-4 behavior prose (structural…
    [132] «Backlog» {phase:0} task:ASCP-E4-S3#1
       ASCP-E4-S3.2 Implement tools/evidence_collector.py
       ↳ Category: Infrastructure Subtasks collect(test_file, test_name, output_bytes): sha256:<hex>, tz-aware ISO-8601 collected_at (+00:00 offset) validate_evidence_record(record): 4 fields present+non-empty AND output_hash matches ^sha256:[a-f0-9]{64}$ AND parseable collected_at store_…
    [133] «Backlog» {phase:1} task:ASCP-E4-S3#2
       ASCP-E4-S3.3 PostToolUse five-layer feedback hook
       ↳ Category: API Subtasks Run ruff + mypy + semgrep --config auto (HIGH/CRITICAL filter) + wiring_checker.py on changed files Emit structured feedback to stdout; exit 1 (non-blocking, never exit 2); exception -> exit 1 Post a Plane comment with the findings on the slice issue
    [134] «Backlog» {phase:1} task:ASCP-E4-S3#3
       ASCP-E4-S3.4 SubagentStop Evidence_Record + role-separation gate
       ↳ Category: API Subtasks Parse the Subagent-Result Envelope from stdin (actor_agent, requirement_id, omission_declaration, optional evidence[]) Run the omission-declaration guard first, then role-separation block (actor_agent == implementer.md -> exit 2) Run the four-field evidence…
    [135] «Backlog» {phase:1} task:ASCP-E4-S3#4
       ASCP-E4-S3.5 CI security + quality gates
       ↳ Category: API Subtasks Add the SonarQube AI Code Assurance step (fail on new HIGH/CRITICAL or coverage drop < 85%) Add CodeQL github/codeql-action/analyze for Python (fail on HIGH/CRITICAL) Add the Playwright CI step uploading the trace artifact on failure Register all three as r…
    [136] «Backlog» {phase:2} task:ASCP-E4-S3#5
       ASCP-E4-S3.6 Verification property suite
       ↳ Category: Orchestration Subtasks Write tests/property/test_evidence.py covering Property 2 (four-field gate), Property 19 (round-trip), Property 23 (coverage >= 85%), Property 24 (role separation) Run with --hypothesis-seed=0 for deterministic CI Assert proven is emitted only whe…
  [36] «Spec-Verified» {phase:0,type:nfr} story:ASCP-E4-S4
     ASCP-E4-S4: Verify performance budgets, accessibility, and UI-screen render-completeness as first-class NFR evidence
     ↳ Redundancy reframe (R2): 'Add nfr_subtype/subtype/declared_states' duplicates already-realized on-disk work — schema/feature_list.schema.json already carries the nfr_subtype/subtype/declared_states allOf. Reframe verify-and-extend.
    [137] «Backlog» {phase:0} task:ASCP-E4-S4#0
       ASCP-E4-S4.1 Amend .claude/agents/verifier.md with the perf_a11y_verifier fifth layer
       ↳ Category: Infrastructure Subtasks Add subtype dispatch: performance -> k6/Lighthouse, accessibility -> axe-core, ui-screen -> Playwright render over declared_states Read perf budgets + a11y bar from the Requirement-20 threshold registry (the verifier reads, does not own the thres…
    [138] «Backlog» {phase:0} task:ASCP-E4-S4#1
       ASCP-E4-S4.2 CoverageItem schema fields for NFR/UI routing
       ↳ Category: Infrastructure Subtasks Add nfr_subtype enum {performance, accessibility, reliability, security} required when type == NFR via allOf Add subtype enum {performance, accessibility, ui-screen} and declared_states array (at least empty/loading/error/ready) Mirror nfr_subtyp…
    [139] «Backlog» {phase:1} task:ASCP-E4-S4#2
       ASCP-E4-S4.3 Perf/a11y CI execution step
       ↳ Category: API Subtasks Extend coverage-gate.yml (or add a dedicated perf-a11y job) to install + run k6, Lighthouse/Core-Web-Vitals, axe-core (@axe-core/playwright), and per-screen render checks for NFR-subtype items Upload k6/Lighthouse/axe result artifacts (the NFR Evidence_Reco…
    [140] «Backlog» {phase:2} task:ASCP-E4-S4#3
       ASCP-E4-S4.4 Property 31 perf/a11y/ui-screen evidence test
       ↳ Category: Orchestration Subtasks Write tests/property/test_perf_a11y.py: a proven perf/a11y item must carry a perf/a11y Evidence_Record Assert a ui-screen item carries a render-assertion Evidence_Record for every declared_state Run with --hypothesis-seed=0 and tag # Feature: spec…
    [141] «Backlog» {phase:2} task:ASCP-E4-S4#4
       ASCP-E4-S4.5 evidence_collector.py NFR/render artifact assembly
       ↳ Category: Orchestration Subtasks collect() accepts k6/Lighthouse/axe report bytes (perf/a11y) and Playwright trace bytes (ui-screen render) as output_bytes, selecting by evidence_kind Canonicalize JSON reports before hashing so re-runs reproduce the same output_hash Add a round-t…

================================================================================
[12] «Agent-Triaged» {priority:high} epic:E5
   [E5] Completion &amp; Quality-Gate Automation
   ↳ Completion &amp; Quality-Gate Automation
  [37] «Spec-Verified» {phase:0,type:wiring,gate:stop} story:ASCP-E5-S10
     ASCP-E5-S10: Fail-Closed Completion Gate (Stop hook + OPA/Conftest + GitHub ruleset)
     ↳ Contradiction fix (C8): specifies the Stop completion gate internals but assumes the spine is wired — names neither the settings.json registration precondition (E8-13), the ralph-loop disable, nor the COH-1 verifier.md reconciliation; references check_no_progress N=3 counters tha…
    [142] «Backlog» {phase:2} task:ASCP-E5-S10#0
       ASCP-E5-S10.1 stop_hook.py evaluate_stop completion gate + reentrancy guard
       ↳ Category: Orchestration Subtasks Implement evaluate_stop with the exact gate ordering: HANDOFF triggers (cap/budget/no-progress, all allow()/exit 0) -> spec-completion violation gate (violation_count<0 fail-closed; >0 block) -> empty-coverage gate (in_scope_items==[] block) -> co…
    [143] «Backlog» {phase:0} task:ASCP-E5-S10#1
       ASCP-E5-S10.2 coverage_query.rego full zero-evidence merge policy
       ↳ Category: Infrastructure Subtasks Author .github/policies/coverage_query.rego (package coverage) with the three deny rules: not-proven in-scope, proven-without-complete-evidence, zero-in-scope-items (INIT). Implement complete_evidence(item) checking all four Evidence_Record field…
    [144] «Backlog» {phase:1} task:ASCP-E5-S10#2
       ASCP-E5-S10.3 coverage-gate.yml workflow + GitHub ruleset registration
       ↳ Category: API Subtasks Create .github/workflows/coverage-gate.yml: install OPA/Conftest; run conftest test feature_list.json --policy .github/policies/; treat ANY non-zero Conftest exit as a merge BLOCK. Register coverage-gate as a REQUIRED status check in the GitHub repository r…
    [145] «Backlog» {phase:2} task:ASCP-E5-S10#3
       ASCP-E5-S10.4 Completion-gate property/Z3 verification + Plane gate mirroring
       ↳ Category: Orchestration Subtasks Wire Property 4 (test_completion_gate.py prediction independence), Property 5 (unproven blocks termination, asserting exit 0 on HANDOFF path), Property 22 (OPA zero-evidence at merge) into tests/property/. Assert CHECK-1/CHECK-3/CHECK-5 pass in fo…
  [38] «In-Verification» {phase:1,phase:2,priority:blocking,type:nfr,gate:security} story:ASCP-E5-S17
     ASCP-E5-S17: Supply-Chain & Security Gates (SAST + secrets + SLSA + sandbox)
     ↳ EARS requirements [event-driven] WHEN code is changed, the system shall run Semgrep_CodeQL in CI and fail the run on any HIGH or CRITICAL severity finding (the CI gate is the enforcing 0-HIGH/CRITICAL gate; the in-loop PostToolUse hook runs Semgrep for next-turn feedback only). […
    [146] «Backlog» {phase:0} task:ASCP-E5-S17#0
       ASCP-E5-S17.1 CI SAST gate (Semgrep + CodeQL)
       ↳ Category: Infrastructure Subtasks Stand up codeql.yml (CodeQL) and the Semgrep CI workflow; fail the run on any HIGH/CRITICAL finding (Req 20.1 threshold). Confirm division of labor: PostToolUse runs Semgrep-only for feedback (exit 1); CI runs Semgrep + CodeQL as the enforcing ga…
    [147] «Backlog» {phase:0} task:ASCP-E5-S17#1
       ASCP-E5-S17.2 Secrets-detection gate (secrets-scan.yml)
       ↳ Category: Infrastructure Subtasks Author .github/workflows/secrets-scan.yml: on pull_request + protected-branch pushes; run gitleaks (pinned) on the PR diff; emit SARIF; fail on any secret. Add .gitleaks.toml (ruleset + false-positive allowlist for example/test fixtures). Add the…
    [148] «Backlog» {phase:2} task:ASCP-E5-S17#2
       ASCP-E5-S17.3 PreToolUse secret-block prevention guard
       ↳ Category: Orchestration Subtasks Add check_secret_block(event) to .claude/hooks/pre_tool_use_hook.py: scan prompt/span-attrs/URL/Bash-args against secret regexes; block (exit 2) on a match; chain into the pinned guard order. Wire Property 20 (test_secret_free_output) into tests/p…
    [149] «Backlog» {phase:0} task:ASCP-E5-S17#3
       ASCP-E5-S17.4 Sandbox & worktree isolation (REQ-17.4)
       ↳ Category: Infrastructure Subtasks Implement the sandbox boundary: devcontainer locally / E2B for ephemeral CI; network egress DENIED by default with an explicit audited allowlist; filesystem writes confined to the per-slice git worktree mounted in. Compose with git worktree add (…
    [150] «Backlog» {phase:0} task:ASCP-E5-S17#4
       ASCP-E5-S17.5 SLSA build provenance on merge
       ↳ Category: Infrastructure Subtasks Add actions/attest-build-provenance to the release/merge workflow (task 32.1) to generate signed SLSA provenance on artifact build. Verify with gh attestation verify; document the joint REQ-AUDIT-003 satisfaction (provenance + audit-chain verifie…
    [151] «Backlog» {phase:1} task:ASCP-E5-S17#5
       ASCP-E5-S17.6 Required-check registration + Plane security-gate mirroring
       ↳ Category: API Subtasks Register secrets-scan (and confirm SAST checks) as REQUIRED in the GitHub repository ruleset; document in docs/github-ruleset.md referencing the canonical task-14.2 list. Subscribe a webhook consumer mapping security-gate failures (SAST/secrets) to Plane is…
  [39] «Human-Review» {phase:3,priority:high,type:nfr} story:ASCP-E5-S30
     ASCP-E5-S30: DeepEval Eval-Gating in CI (faithfulness + answer relevancy)
     ↳ EARS requirements [ubiquitous] The system shall include a DeepEval eval-gating step in CI using the pytest-native assert_test() API for LLM-output quality assertions. [event-driven] WHEN a CI run includes LLM output to evaluate, THEN the eval step shall gate on the configured DEF…
    [152] «Backlog» {phase:2} task:ASCP-E5-S30#0
       ASCP-E5-S30.1 deepeval_gate.py module + pinned judge
       ↳ Category: Orchestration Subtasks Implement tools/deepeval_gate.py calling DeepEval assert_test() on faithfulness >= 0.8 and answer relevancy >= 0.7, reading thresholds from the task-44 registry. Pin the judge: claude-opus-4-8 (Anthropic on Vertex AI), temperature=0, fixed seed, p…
    [153] «Backlog» {phase:0} task:ASCP-E5-S30#1
       ASCP-E5-S30.2 Golden-set eval fixtures
       ↳ Category: Infrastructure Subtasks Create the versioned tests/eval/ dataset; each case supplies LLMTestCase input/actual_output/retrieval_context, seeded from Verifier-run evidence. Implement the vacuous-pass path (zero applicable cases -> green).
    [154] «Backlog» {phase:1} task:ASCP-E5-S30#2
       ASCP-E5-S30.3 deepeval-gate.yml workflow + ruleset registration
       ↳ Category: API Subtasks Create .github/workflows/deepeval-gate.yml: on pull_request; run pytest tools/deepeval_gate.py (or deepeval test run). Register deepeval-gate as a REQUIRED status check (Phase-4 task 40.6) in the GitHub ruleset; document in docs/github-ruleset.md (canonical…
    [155] «Backlog» {phase:2} task:ASCP-E5-S30#3
       ASCP-E5-S30.4 Eval-gate smoke test + Plane mirroring
       ↳ Category: Orchestration Subtasks Write the smoke/integration test asserting a below-threshold metric fails the build (the named verification mechanism, no Z3 oracle). Subscribe a webhook consumer mapping deepeval-gate pass/fail to the Plane issue (gate=ci, state Blocked on fail; …
  [40] «Spec-Verified» {phase:4,type:nfr} story:ASCP-E5-S31
     ASCP-E5-S31: OWASP ZAP DAST Baseline Security Scan
     ↳ Contradiction fix (C9): contradictory phase claims — label phase:2 vs AC 'Phase-4 task 40.5'. Reconcile to Phase-4 per the AC: move the cycle to 'Phase 4 — Property-Based Test Suite' and set the label to phase:4.
    [156] «Backlog» {phase:0} task:ASCP-E5-S31#0
       ASCP-E5-S31.1 zap-baseline.yml DAST workflow + CI app stand-up
       ↳ Category: Infrastructure Subtasks Author .github/workflows/zap-baseline.yml: on pull_request; a job step boots the app/service at http://localhost:<port>; run zaproxy/action-baseline@v0.12.0 with fail_action: true against that target. Constrain to the baseline passive scan (no ac…
    [157] «Backlog» {phase:1} task:ASCP-E5-S31#1
       ASCP-E5-S31.2 zap-baseline required-check registration
       ↳ Category: API Subtasks Register zap-baseline as a REQUIRED status check (Phase-4 task 40.5) in the GitHub repository ruleset; add to dependency-graph wave 33. Document in docs/github-ruleset.md referencing the canonical task-14.2 list.
    [158] «Backlog» {phase:2} task:ASCP-E5-S31#2
       ASCP-E5-S31.3 DAST gate mirroring to Plane
       ↳ Category: Orchestration Subtasks Subscribe a webhook consumer mapping zap-baseline pass/fail to the Plane issue (gate=ci, label gate:security, state Blocked on fail; contributes to Done on pass) via the Plane REST API. Document the v1 baseline-only scope and the post-v1 authentic…
  [41] «Human-Review» {phase:2,priority:blocking,type:nfr,gate:security,human:review} story:ASCP-E5-S32
     ASCP-E5-S32: OpenFeature/flagd Agent Code Kill-Switch
     ↳ EARS requirements [ubiquitous] The system shall implement an agent-capability kill-switch using OpenFeature + flagd (Apache 2.0, self-hosted, CNCF Incubating), with no SaaS dependency. [event-driven] WHEN a kill-switch flag (kill.<capability> or kill.all) is set, THEN the affecte…
    [159] «Backlog» {phase:0} task:ASCP-E5-S32#0
       ASCP-E5-S32.1 Self-hosted flagd service + flag schema
       ↳ Category: Infrastructure Subtasks Create the flagd/ directory: flagd.json flag-definitions, provider config, self-hosted deployment manifest (Apache 2.0, CNCF Incubating). Define the kill-switch flag schema enumerating kill.initializer/kill.implementer/kill.verifier/kill.research…
    [160] «Backlog» {phase:2} task:ASCP-E5-S32#1
       ASCP-E5-S32.2 OpenFeature SDK wiring into agent entry points
       ↳ Category: Orchestration Subtasks Wire the OpenFeature client into all four agent start-of-turn entry points (initializer/implementer/verifier/research); read kill.<capability> and kill.all; HARD-REFUSE the gated capability when either is true. Implement fail-closed: unreachable f…
    [161] «Backlog» {phase:2} task:ASCP-E5-S32#2
       ASCP-E5-S32.3 Toggle authority, authentication & audit/OTel wiring
       ↳ Category: Orchestration Subtasks Restrict flag toggles to the Delivery Owner / Operator role; authenticate and record each toggle. On set/clear and on each start-of-turn kill-refusal, call tools/audit_log.append(event, tool, decision, reason, requirement_id, actor_agent) AND emit…
    [162] «Backlog» {phase:1} task:ASCP-E5-S32#3
       ASCP-E5-S32.4 Kill-switch verification + Plane operator control
       ↳ Category: API Subtasks Add the <= 30 s propagation test and the unreachable-flagd fail-closed test (runtime/CI-verified; no Z3 oracle); document the kill-switch invariant. Expose operator toggle authority through Plane: a human:review issue action (or webhook->REST mapping) that,…

================================================================================
[13] «Agent-Triaged» {priority:high} epic:E6
   [E6] Agent Integration Layer — Plane ⇄ Agent (Bidirectional)
   ↳ Agent Integration Layer — Plane ⇄ Agent (Bidirectional)
  [42] «Agent-Triaged» {phase:0,priority:blocking,type:wiring,gate:security} story:E6-S1
     E6-S1: Inbound webhook ingestion: HMAC-SHA256 verification + delivery idempotency
     ↳ EARS requirements [ubiquitous] THE system SHALL expose a single webhook ingestion endpoint that accepts Plane event deliveries carrying the X-Plane-Signature, X-Plane-Event, and X-Plane-Delivery headers. [event-driven] WHEN a Plane webhook delivery is received, THE system SHALL c…
    [163] «Backlog» {phase:1} task:E6-S1#0
       E6-S1.1 Webhook receiver endpoint + HMAC-SHA256 constant-time verifier
       ↳ Category: API Subtasks Expose a single ingestion route reading X-Plane-Signature / X-Plane-Event / X-Plane-Delivery headers and the raw (unparsed) request body Compute HMAC-SHA256(secret, raw_body) and compare constant-time (hmac.compare_digest); reject with 401 on mismatch befor…
    [164] «Backlog» {phase:0} task:E6-S1#1
       E6-S1.2 Durable delivery-idempotency ledger
       ↳ Category: Infrastructure Subtasks Add webhook_deliveries Postgres table (delivery_id PRIMARY KEY, event_type, received_at, dispatch_id) Insert delivery_id and dispatch intent in one transaction; treat a duplicate delivery_id as a 200 no-op Add migration + migration-runner bookkee…
    [165] «Backlog» {phase:2} task:E6-S1#2
       E6-S1.3 Reject/replay gate-decision telemetry
       ↳ Category: Orchestration Subtasks Emit a hook.decision-style OTel span (event, allow|block, reason, requirement_id) on HMAC reject and on replay-noop Wire the receiver as a WIRING coverage item in feature_list.json and bind its integration-test Evidence_Record Add the integration …
  [43] «Spec-Verified» {phase:0,type:wiring,gate:completion} story:E6-S2
     E6-S2: Webhook-driven agent-run dispatch (state to subagent)
     ↳ Contradiction fix (C10): 'mirrors the PreToolUse scope gate (REQ-7.5)', dispatches initializer/implementer subagents, reads plan-approved.json+feature_list_sha and the flagd kill-switch — but A1/A7 are staged-not-applied, scope-sequencing is D11 (DEFERRED), plan-approval is D10 (…
    [166] «Backlog» {phase:2} task:E6-S2#0
       E6-S2.1 State-to-subagent dispatcher
       ↳ Category: Orchestration Subtasks Map Agent-Triaged to initializer dispatch and Agent-Executing to implementer (one slice) dispatch Resolve the target item by the implementer.md selection predicate (lowest priority among unproven with all-proven deps, id-lexical tiebreak) Record a…
    [167] «Backlog» {phase:2} task:E6-S2#1
       E6-S2.2 Pre-dispatch deterministic precondition checks
       ↳ Category: Orchestration Subtasks Refuse Agent-Executing dispatch while any prior-slice item is unproven (mirror PreToolUse scope gate REQ-7.5) Refuse dispatch while plan-approved.json absent or feature_list_sha mismatched (REQ-18.1/18.4) Check the flagd kill-switch capability fla…
    [168] «Backlog» {phase:1} task:E6-S2#2
       E6-S2.3 Refusal write-back wiring
       ↳ Category: API Subtasks Write back Blocked with run_state=blocked and the specific refusal reason via the E6-S3 REST path Emit an audited block decision (not a silent drop) for each refused dispatch Add integration tests for each refusal branch (prior-unproven, no-plan, kill-switc…
  [44] «Spec-Verified» {phase:0,type:wiring,gate:completion} story:E6-S3
     E6-S3: REST write-back of agent state transitions via external_id
     ↳ Contradiction fix (C11): 'Done is written only after Stop hook + OPA zero-evidence query + GitHub required status check all pass' — the Stop hook is unregistered (Pattern-1), OPA/Conftest is D17 (absent), GitHub required checks are D17-D18 (absent). Reframe the AC to the in-scope…
    [169] «Backlog» {phase:1} task:E6-S3#0
       E6-S3.1 external_id-keyed Plane REST write-back client
       ↳ Category: API Subtasks Resolve the target issue by external_id == requirement_id and PATCH the mirrored state via Plane REST Set evidence_status, run_state, coverage_type, and output_hash fields from the durable store on each transition Make every write-back idempotent (same exte…
    [170] «Backlog» {phase:2} task:E6-S3#1
       E6-S3.2 Completion-gate-bound Done/HANDOFF/Blocked routing
       ↳ Category: Orchestration Subtasks Write Done only after Stop hook + OPA zero-evidence query + GitHub required check all pass Route cap/budget/no-progress to HANDOFF (run_state=handoff) and keep HANDOFF and Done mutually exclusive Reflect a gate-rejected Done as Blocked (fail-close…
    [171] «Backlog» {phase:0} task:E6-S3#2
       E6-S3.3 State-mapping coverage tests
       ↳ Category: Infrastructure Subtasks Add an integration test asserting each requirement_id-status to Plane-state mapping across all 12 states Add a fixture (one unproven in-scope item) proving Done is unreachable and Blocked is reflected Add a double-apply idempotency test for the w…
  [45] «Spec-Verified» {phase:0,type:wiring,agent:initializer,agent:coder,agent:tester,agent:research} story:E6-S4
     E6-S4: Provisioning the Plane workspace from the coverage model
     ↳ Latent COH-1 fix (C12): E6-S4 seeds agent_role as suffix-less dropdown values (initializer|implementer|verifier|research) and labels agent:coder/agent:tester, while the gates require byte-consistent .md actor literals (verifier.md/implementer.md). Document the mapping so the boar…
    [172] «Backlog» {phase:1} task:E6-S4#0
       E6-S4.1 Workspace skeleton provisioner (states/fields/labels)
       ↳ Category: API Subtasks Create the ASCP project with all 12 states mapped to backlog/unstarted/started/completed/cancelled groups Create the 10 custom fields with exact types and dropdown option sets from the shared vocabulary Create the 22 labels and apply role/type/phase/gate la…
    [173] «Backlog» {phase:2} task:E6-S4#1
       E6-S4.2 Coverage-model-to-issue seeding
       ↳ Category: Orchestration Subtasks Read feature_list.json + reconciled spec and create one issue per in-scope item with external_id = requirement_id Set initial state (Backlog or Agent-Triaged) and the item's ears_pattern/coverage_type Make seeding idempotent: update by external_id…
    [174] «Backlog» {phase:0} task:E6-S4#2
       E6-S4.3 Provisioning verification + dry-run
       ↳ Category: Infrastructure Subtasks Add a read-back diff test asserting the provisioned states/fields/labels match the shared-vocabulary spec exactly Add an idempotency test (run provisioning twice, diff for zero duplicates) Implement the dry-run flag emitting the planned create/up…
  [46] «Done» {phase:3,priority:blocking,type:functional,gate:completion} story:E6-S5
     E6-S5: Bidirectional state-mirror and traceability-triple sync
     ↳ EARS requirements [ubiquitous] THE system SHALL keep each Plane issue's state an eventually-consistent, idempotent projection of its requirement_id's durable coverage status in Postgres. [event-driven] WHEN an agent run produces a slice, THE system SHALL write the traceability tr…
    [175] «Backlog» {phase:2} task:E6-S5#0
       E6-S5.1 Postgres-authoritative state projection
       ↳ Category: Orchestration Subtasks Project durable coverage status to the mirrored Plane state for every in-scope requirement_id On drift, reconcile Plane toward Postgres (never the reverse) and record the repair Revert + log any manual Plane edit that sets an unsupported state (e.…
    [176] «Backlog» {phase:1} task:E6-S5#1
       E6-S5.2 Traceability-triple stamping
       ↳ Category: API Subtasks Write worktree_branch + agent_run_id + Plane issue id onto the issue so the triple is reconstructable from Plane alone (REQ-6) Surface the slice commit SHA on the issue and assert the commit trailer carries requirement_id (REQ-6.2) Add an integration test r…
    [177] «Backlog» {phase:0} task:E6-S5#2
       E6-S5.3 Periodic reconciliation sweep
       ↳ Category: Infrastructure Subtasks Implement a sweep recomputing each in-scope issue state from Postgres and repairing drift Make the sweep idempotent (no-op on already-consistent state) Add a drift-injection test asserting repair toward Postgres
  [47] «In-Verification» {phase:3,priority:normal,type:nfr} story:E6-S6
     E6-S6: Integration-layer observability: OTel spans + requirement.id Baggage
     ↳ EARS requirements [ubiquitous] THE system SHALL emit an OTel span for every webhook receipt, every dispatch decision, and every REST write-back, attributed with plane.event, plane.delivery_id, plane.external_id, and the mirrored state. [event-driven] WHEN the integration layer be…
    [178] «Backlog» {phase:2} task:E6-S6#0
       E6-S6.1 Integration-span instrumentation
       ↳ Category: Orchestration Subtasks Emit OTel spans for webhook receipt, dispatch decision, and REST write-back with plane.event/delivery_id/external_id/state attributes Set requirement.id into W3C Baggage at delivery-processing start so all child spans carry it (REQ-12.4) Tag gate-…
    [179] «Backlog» {phase:0} task:E6-S6#1
       E6-S6.2 Streaming export wiring
       ↳ Category: Infrastructure Subtasks Configure the OTLP exporter to stream each integration span as it closes (export interval <=5s, not batched) Point exports at the same trace endpoint as agent spans (REQ-12.3) with the platform-pinned SDK + GenAI semconv versions Document the Lan…
    [180] «Backlog» {phase:0} task:E6-S6#2
       E6-S6.3 Trace-continuity assertions
       ↳ Category: Infrastructure Subtasks Add a trace-assertion test verifying one webhook-dispatch-writeback flow shares a single requirement.id Baggage value Assert reject/dedupe/refuse each produce a distinct allow|block gate-decision span Assert spans export within <=5s against a moc…
  [48] «Spec-Verified» {phase:0,type:nfr} story:E6-S7
     E6-S7: Plane-as-advisory, gates-as-authority (anti-Plane-gating guard)
     ↳ Vacuous-pass fix (C13): the static check 'no gate function imports or reads Plane state' presumes gate functions exist to scan, but the Stop/PreToolUse/OPA gates are unapplied/absent — until they are built the check passes vacuously (no gate functions -> none read Plane state -> …
    [181] «Backlog» {phase:2} task:E6-S7#0
       E6-S7.1 Advisory-context injection path
       ↳ Category: Orchestration Subtasks Surface Plane labels/comments to the agent as injected advisory context (mirror REQ-19.1) without changing any gate outcome Realize halt intent through the flagd kill-switch + existing hooks and reflect it in Plane as Blocked/HANDOFF Tag advisory-…
    [182] «Backlog» {phase:0} task:E6-S7#1
       E6-S7.2 Anti-Plane-gating static + property guard
       ↳ Category: Infrastructure Subtasks Add a static check proving no gate function imports or reads Plane state (gates depend only on feature_list.json + evidence + OPA) Add a Property-style test that a Plane manual Done on an unproven item cannot produce a proven coverage transition …

================================================================================
[14] «Agent-Triaged» {priority:high} epic:E7
   [E7] Observability, Audit & Traceability
   ↳ Observability, Audit & Traceability
  [49] «In-Verification» {phase:2,phase:3,priority:high,type:wiring,agent:tester,gate:completion} story:ASCP-E7-REQ6
     ASCP-E7-REQ6: Bidirectional Traceability (requirement ↔ code ↔ test ↔ evidence ↔ commit ↔ owner)
     ↳ EARS requirements [ubiquitous] The system shall maintain bidirectional links requirement ↔ implementation ↔ test ↔ evidence ↔ commit ↔ owner in the durable Postgres traceability_links store. [ubiquitous] The system shall stamp the active requirement.id onto every telemetry span v…
    [183] «Backlog» {phase:0} task:ASCP-E7-REQ6#0
       ASCP-E7-REQ6.1 Migration 003_traceability_links.sql + per-requirement index
       ↳ Category: Infrastructure Subtasks Write db/migrations/003_traceability_links.sql with link_type IN ('implementation','test','evidence','commit','owner') and direction IN ('forward','backward') CHECKs Add idx_traceability_links_requirement_id Run on a test Neon branch; assert tabl…
    [184] «Backlog» {phase:0} task:ASCP-E7-REQ6#1
       ASCP-E7-REQ6.2 Shared requirement-ID scanner tools/req_id_scan.py
       ↳ Category: Infrastructure Subtasks Implement the [A-Z]+-[A-Z]+-[0-9]{3} trailer/comment/docstring extractor Import it from both traceability_writer.py and orphan_detector.py Unit-test it matches REQ-TRACE-001-form IDs and NOT dotted EARS criterion numbers (e.g. 6.3)
    [185] «Backlog» {phase:1} task:ASCP-E7-REQ6#2
       ASCP-E7-REQ6.3 tools/traceability_writer.py commit-trailer parser + link writer
       ↳ Category: API Subtasks Implement parse_commit_trailers(commit_sha) Implement write_traceability_link(req_id, link_type, target_ref, direction) inserting into traceability_links Implement assert_commit_has_req_id(commit_sha) raising TraceabilityError Property-10 PBT test_commit_tr…
    [186] «Backlog» {phase:1} task:ASCP-E7-REQ6#3
       ASCP-E7-REQ6.4 tools/orphan_detector.py bidirectional orphan check
       ↳ Category: API Subtasks Scan full-repo Python source for requirement-ID refs with documented exclude list Read feature_list.json + Postgres evidence_records/traceability_links for known IDs Report forward + backward orphans per canonical definition; honor # orphan-exempt/allowlist…
    [187] «Backlog» {phase:2} task:ASCP-E7-REQ6#4
       ASCP-E7-REQ6.5 traceability-gate REQUIRED CI check (.github/workflows/traceability-gate.yml)
       ↳ Category: Orchestration Subtasks Invoke orphan_detector.py and block merge on non-zero exit Fold in assert_commit_has_req_id over the PR's commits Register traceability-gate in the GitHub ruleset (canonical list in docs/github-ruleset.md) Integration test asserting a missing-ref …
    [188] «Backlog» {phase:1} task:ASCP-E7-REQ6#5
       ASCP-E7-REQ6.6 RequirementBaggageProcessor in tools/telemetry.py
       ↳ Category: API Subtasks Implement SpanProcessor.on_start setting requirement.id Baggage Assert non-empty for any active-requirement span Property-12 PBT test_w3c_baggage_propagation
  [50] «Agent-Executing» {phase:0,phase:1,phase:2,priority:high,type:functional,human:review} story:ASCP-E7-REQ11
     ASCP-E7-REQ11: Session Continuity and Durable State
     ↳ EARS requirements [ubiquitous] The system shall persist all mutable run state outside model context — in files (claude-progress.txt, feature_list.json), git history, and the durable Postgres run_state store. [ubiquitous] The system shall record an incremental commit per completed…
    [189] «Backlog» {phase:0} task:ASCP-E7-REQ11#0
       ASCP-E7-REQ11.1 Migration 005_run_state.sql durable per-session execution state
       ↳ Category: Infrastructure Subtasks Create run_state with status CHECK {running,complete,handoff,blocked}, phase CHECK {spec,implementation}, stop_hook_active, no_progress_n, iteration_count, spec_pass_count, violation_count, prev_violation_count, retry_count, resume_integrity_ok, …
    [190] «Backlog» {phase:0} task:ASCP-E7-REQ11#1
       ASCP-E7-REQ11.2 session_start_hook.py Phase-0 git/progress/coverage loader
       ↳ Category: Infrastructure Subtasks Read git status --porcelain; read/create claude-progress.txt; read/stub feature_list.json Emit structured-JSON summary (git_status, unproven_count, proven_count) try/except → exit 0; unit tests for first-run + populated cases
    [191] «Backlog» {phase:0} task:ASCP-E7-REQ11#2
       ASCP-E7-REQ11.3 pre_compact_hook.py checkpoint writer + baseline-hash producer
       ↳ Category: Infrastructure Subtasks Checkpoint claude-progress.txt + evidence state + feature_list.json to MAIN-worktree git Write durable run_state.resume_state_hash over the checkpointed state try/except → exit 0; unit + integration test
    [192] «Backlog» {phase:1} task:ASCP-E7-REQ11#3
       ASCP-E7-REQ11.4 tools/run_state_store.py persistence with file-backed duplicate
       ↳ Category: API Subtasks Implement load_run_state() / save_run_state(run_state) upsert Write claude-progress.txt duplicate including resume_integrity_ok + resume_state_hash Integration test that DB-down fallback reads the file duplicate and reaches the same decision (Note N-25)
    [193] «Backlog» {phase:2} task:ASCP-E7-REQ11#4
       ASCP-E7-REQ11.5 Per-slice commit trail wiring
       ↳ Category: Orchestration Subtasks Ensure the Implementer's per-slice commit records last_commit_sha in run_state Integration test that a completed slice advances last_commit_sha and leaves a rollback point
  [51] «Agent-Executing» {phase:3,priority:normal,type:functional,gate:stop,human:review} story:ASCP-E7-REQ12
     ASCP-E7-REQ12: Observability (live requirement-tagged trace + gate-decision forwarding)
     ↳ EARS requirements [ubiquitous] The system shall emit OTel spans for every model call, tool invocation, and subagent task. [ubiquitous] The system shall propagate the active requirement.id to all child spans via a W3C Baggage span processor. [state-driven] WHILE a run is in progre…
    [194] «Backlog» {phase:0} task:ASCP-E7-REQ12#0
       ASCP-E7-REQ12.1 OTel setup + OTLP exporter (tools/telemetry.py init)
       ↳ Category: Infrastructure Subtasks Configure CLAUDE_CODE_ENABLE_TELEMETRY=1 + OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental in .env.example/CI Pin opentelemetry-sdk + GenAI semconv in requirements.txt Implement init_tracer(service) with a ≤5s-interval streaming exporter…
    [195] «Backlog» {phase:1} task:ASCP-E7-REQ12#1
       ASCP-E7-REQ12.2 RequirementBaggageProcessor requirement.id propagation (shared with REQ-6)
       ↳ Category: API Subtasks Implement on_start Baggage set Assert non-empty for active-requirement spans Property-12 PBT
    [196] «Backlog» {phase:2} task:ASCP-E7-REQ12#2
       ASCP-E7-REQ12.3 Hook decision forwarding — extend all six hooks to emit OTel events
       ↳ Category: Orchestration Subtasks Gate-making hooks (Stop/PreToolUse/SubagentStop) emit hook.decision with hook.event/tool.name/decision/reason/requirement.id/actor_agent Non-gating hooks (SessionStart/PreCompact) emit informational spans with decision=n/a Integration test asserti…
    [197] «Backlog» {phase:0} task:ASCP-E7-REQ12#3
       ASCP-E7-REQ12.4 Langfuse backend connection + license docs
       ↳ Category: Infrastructure Subtasks Add commented OTLP_ENDPOINT example in .env.example Document Langfuse MIT / SigNoz MIT-Expat / Phoenix EL2 licenses Integration test asserting the collector receives a span with the Baggage attribute present
  [52] «Human-Review» {phase:2,phase:3,priority:high,type:functional,gate:completion,human:review} story:ASCP-E7-REQ27
     ASCP-E7-REQ27: Tamper-Evident Gate-Decision Audit Log (hash-chained)
     ↳ EARS requirements [ubiquitous] The system shall append every gate decision (event, tool, allow/block, reason, requirement ID, actor agent, created_at) to an append-only, hash-chained audit log where each entry stores the hash of the prior entry. [ubiquitous] The system shall reta…
    [198] «Backlog» {phase:0} task:ASCP-E7-REQ27#0
       ASCP-E7-REQ27.1 Migration 008_gate_audit_log.sql append-only hash-chained table
       ↳ Category: Infrastructure Subtasks Create the table with the full column set Emit REVOKE UPDATE,DELETE + BEFORE UPDATE OR DELETE RAISE trigger Document genesis sentinel prev_hash = sha256('') and entry_hash canonical form Specify DB-down seq reconciliation rule (client-generated m…
    [199] «Backlog» {phase:1} task:ASCP-E7-REQ27#1
       ASCP-E7-REQ27.2 Audit-log producer tools/audit_log.py with chain linearization
       ↳ Category: API Subtasks Implement append(event, tool, decision, reason, requirement_id, actor_agent) computing entry_hash over the canonical tuple Serialize prev_hash-read + insert under pg_advisory_xact_lock in one transaction File-backed fallback on DB-down (Note N-25) Write-sid…
    [200] «Backlog» {phase:1} task:ASCP-E7-REQ27#2
       ASCP-E7-REQ27.3 Audit-chain verifier tools/audit_verify.py recompute + tamper report
       ↳ Category: API Subtasks Recompute the chain and fail on any broken link Merged DB+file-backed chain verification with the seam rule Structured JSON break report Property-28 PBT test_audit_verify.py (broken-link fail + intact-chain producer-contract reproduction including seq/creat…
    [201] «Backlog» {phase:2} task:ASCP-E7-REQ27#3
       ASCP-E7-REQ27.4 Wire producer into the three hooks (52.3 producer wiring)
       ↳ Category: Orchestration Subtasks Modify stop_hook.py, pre_tool_use_hook.py, subagent_stop_hook.py to call audit_log.append(...) on every allow/block decision Invoke BEFORE the exit, wrapped to fall back to the file-backed log Unit test that an append raise still records to the fi…
    [202] «Backlog» {phase:2} task:ASCP-E7-REQ27#4
       ASCP-E7-REQ27.5 audit-chain-verify REQUIRED CI check (.github/workflows/audit-chain-verify.yml)
       ↳ Category: Orchestration Subtasks Create the workflow running audit_verify.py SPLIT the registration leg so required/merge-blocking registration is gated until 52.2/52.3 land Register in the GitHub ruleset (canonical list in docs/github-ruleset.md)
    [203] «Backlog» {phase:0} task:ASCP-E7-REQ27#5
       ASCP-E7-REQ27.6 Retention & archival policy — live window + cross-boundary re-verification
       ↳ Category: Infrastructure Subtasks Implement 365-day live-window checkpoint-and-archive of verified prefixes to write-once cold storage, recording the prefix tip entry_hash Ensure the next live entry's prev_hash equals the archived tip so audit_verify re-verifies across the bounda…
  [53] «Blocked» {phase:2,priority:blocking,type:functional,human:review} story:ASCP-E7-REQ23
     ASCP-E7-REQ23: Resumed-State Integrity
     ↳ EARS requirements [event-driven] WHEN a session resumes, the SessionStart_Hook shall compute the resumed-state hash and write run_state.resume_integrity_ok (bool) without itself blocking. [unwanted] IF a session resumes AND the resumed-state hash does not match the durable store'…
    [204] «Backlog» {phase:0} task:ASCP-E7-REQ23#0
       ASCP-E7-REQ23.1 tools/state_integrity.py resumed-state hash computation
       ↳ Category: Infrastructure Subtasks Implement compute_hash() over the canonical projection of in-scope feature_list.json items + named run_state fields Document the canonical-form spec matching Property 26 Add resume_state_hash/is_resume/first_write_done/resume_integrity_ok columns…
    [205] «Backlog» {phase:1} task:ASCP-E7-REQ23#1
       ASCP-E7-REQ23.2 SessionStart compute/write extension (task 49.2)
       ↳ Category: API Subtasks Extend session_start_hook.py to import state_integrity.py, call compute_hash(), compare to durable resume_state_hash, write resume_integrity_ok Remain exit 0 (non-blocking) DB-down → write the flag+hash to claude-progress.txt Add the resume-write assertion …
    [206] «Backlog» {phase:2} task:ASCP-E7-REQ23#2
       ASCP-E7-REQ23.3 PreToolUse integrity guard (task 49.1 enforcement point)
       ↳ Category: Orchestration Subtasks Add check_resume_integrity(event) reading run_state.resume_integrity_ok, blocking the first resumed-session write (exit 2) when false Scope on (is_resume AND NOT first_write_done); NULL-baseline → allow Chain it first in the PreToolUse guard order…
  [54] «Backlog» {phase:3,type:nfr} story:ASCP-E7-REQ16
     ASCP-E7-REQ16: Durable Storage (single source of truth)
     ↳ Contradiction fix (C16) + §4.4 status incoherences: E7 stories carry advanced states (Done, In-Verification, Human-Review, Agent-Executing, Blocked) while their underlying tools/migrations/telemetry are absent on disk — status claims outrun on-disk reality. True-up each to Backlo…
    [207] «Backlog» {phase:0} task:ASCP-E7-REQ16#0
       ASCP-E7-REQ16.1 Migrations 001/002/004 — requirements, coverage_items, evidence_records
       ↳ Category: Infrastructure Subtasks Write 001_requirements.sql (identity/EARS/provenance, type/nfr_subtype/provenance CHECKs) Write 002_coverage_items.sql (status/subtype CHECKs, in_scope DEFAULT TRUE + human-authored-flip trigger) Write 004_evidence_records.sql (four-field evidenc…
    [208] «Backlog» {phase:0} task:ASCP-E7-REQ16#1
       ASCP-E7-REQ16.2 Migration runner + eight-table integration test
       ↳ Category: Infrastructure Subtasks Run all eight migrations (001–008) on a test Neon branch Assert all eight tables + CHECKs; assert evidence_complete rejects an incomplete record and coverage_items.in_scope defaults true Assert app_role lacks UPDATE/DELETE on gate_audit_log
    [209] «Backlog» {phase:1} task:ASCP-E7-REQ16#2
       ASCP-E7-REQ16.3 evidence_collector.py → evidence_records storage integration
       ↳ Category: API Subtasks Implement store_to_postgres(record, requirement_id, commit_sha) Store the content-addressed blob keyed by output_hash with the record holding only the sha256: reference Degraded-evidence flag on hash-only DB-down fallback Property-19 Phase-2 round-trip test…
    [210] «Backlog» {phase:2} task:ASCP-E7-REQ16#3
       ASCP-E7-REQ16.4 Phase-2 durable-state integration test — full store reconstructability
       ↳ Category: Orchestration Subtasks Against a test Neon branch, insert a complete evidence record and assert retrieval by requirement_id+commit_sha Assert coverage queries are answerable from Postgres alone (16.3) Assert the file-canonical/DB-mirror split (acceptance_criteria/depend…

================================================================================
[15] «Agent-Triaged» {priority:high} epic:E8
   [E8] Orchestration, Anti-Loopmaxxing & Human-in-the-Loop
   ↳ Orchestration, Anti-Loopmaxxing & Human-in-the-Loop
  [55] «Spec-Verified» {phase:0,type:wiring,gate:stop,human:review} story:ASCP-E8-13
     ASCP-E8-13: Mid-Flight Steering via Deterministic Hooks
     ↳ Master registration fix (A1 -> .claude/settings.json). Wires SessionStart / PreToolUse / PostToolUse / SubagentStop / Stop into the runtime and sets enabledPlugins."ralph-loop@…": false for governed sessions. This is the precondition for every other gate. Contradiction fixed (C1)…
    [211] «Backlog» {phase:0} task:ASCP-E8-13#0
       ASCP-E8-13.1 Author .claude/settings.json six-hook command registration
       ↳ Category: Infrastructure Subtasks Register Stop, PreToolUse, PostToolUse (matcher Write|Edit|MultiEdit), SubagentStop, SessionStart, PreCompact as type:command (task 9.1). Confirm the four .claude/agents/*.md subagents auto-discover by frontmatter name. Write tests/smoke/test_hoo…
    [212] «Backlog» {phase:2} task:ASCP-E8-13#1
       ASCP-E8-13.2 Implement pre_tool_use_hook.py artifact + status guards
       ↳ Category: Orchestration Subtasks check_artifact_guard: block feature_list.json schema, tests/ (verifier carve-out), CI config, destructive Bash; exit 2 (task 6.1). check_status_transition + check_append_only: permit only the four edges, block deletion/truncation/reorder of items[…
    [213] «Backlog» {phase:1} task:ASCP-E8-13#2
       ASCP-E8-13.3 Configure GitHub repository ruleset as merge-side complement
       ↳ Category: API Subtasks Register required status checks so destructive merges cannot bypass hooks (task 14.2). Document the canonical required-check list in docs/github-ruleset.md.
    [214] «Backlog» {phase:2} task:ASCP-E8-13#3
       ASCP-E8-13.4 Author exit-code + prediction-independence property tests
       ↳ Category: Orchestration Subtasks Property 21 PBT: exit 0 proceeds, exit 2 blocks with stderr fed back, exit 1 non-blocking (>=100 examples, task 39.3). Property 4 PBT: identical coverage state + differing prediction variables -> identical gate decision (mirrors CHECK-5).
  [56] «Spec-Verified» {phase:0,type:wiring} story:ASCP-E8-14
     ASCP-E8-14: Anti-Loopmaxxing Controls (Caps, Budget, No-Progress)
     ↳ Scope clarification: E8-14 owns ONLY the 005_run_state.sql column migration — it does NOT populate the counters. The populator is NEW-02. Cross-link both so the consume/populate split is explicit (this was the audit's #1 deferred-prereq confusion). ALSO (R5): E8-14 and E8-21 BOTH…
    [215] «Backlog» {phase:2} task:ASCP-E8-14#0
       ASCP-E8-14.1 Implement HANDOFF triggers in evaluate_stop (stop_hook.py)
       ↳ Category: Orchestration Subtasks Phase-discriminate cap on run_state.phase: spec->SPEC_COMPLETION_HARD_CAP=7 (spec_pass_count); implementation->MAX_TURNS_PER_SLICE=25 (iteration_count) (task 5.1). Evaluate cap->budget->no-progress BEFORE the unproven-items block; each returns all…
    [216] «Backlog» {phase:2} task:ASCP-E8-14#1
       ASCP-E8-14.2 Own the retry + per-slice token budget in implementer.md
       ↳ Category: Orchestration Subtasks Increment run_state.retry_count on a failed slice; at >=3 stop and route to HANDOFF (task 10.2). Enforce the per-slice token/cost budget (REQ-LOOP-001) and its REQ-LOOP-002 HANDOFF trigger.
    [217] «Backlog» {phase:0} task:ASCP-E8-14#2
       ASCP-E8-14.3 Migrate the run_state counters
       ↳ Category: Infrastructure Subtasks Add iteration_count, spec_pass_count, token_cost_usd, no_progress_n, retry_count, prev_violation_count to migration 005_run_state.sql (task 28.5). Add status CHECK IN (running,complete,handoff,blocked) and phase CHECK IN (spec,implementation).
    [218] «Backlog» {phase:1} task:ASCP-E8-14#3
       ASCP-E8-14.4 Mirror HANDOFF onto the Plane issue via webhook
       ↳ Category: API Subtasks On run_state.status=handoff, transition the linked Plane issue to the HANDOFF state (cancelled group) via REST. Set run_state=handoff, apply the handoff label, and post the HANDOFF summary as an issue comment.
    [219] «Backlog» {phase:2} task:ASCP-E8-14#4
       ASCP-E8-14.5 Author HANDOFF/no-progress property + unit tests
       ↳ Category: Orchestration Subtasks PBT: cap/budget/no-progress each yield allow() (HANDOFF), never a block (task 39.3). Unit: check_no_progress boundary at N=3; HANDOFF summary contents (task 5.5).
  [57] «Agent-Executing» {phase:0,priority:high,type:wiring,agent:initializer,agent:coder,agent:tester} story:ASCP-E8-15
     ASCP-E8-15: Inner-Loop Orchestration (Subagents + Hooks)
     ↳ EARS requirements [ubiquitous] THE system shall use Claude Code subagents and hooks as the inner planner/implementer/verifier orchestrator and shall NOT introduce an external agent-reasoning framework for the inner loop by default. [optional] WHERE crash-safe multi-hour or multi-…
    [220] «Backlog» {phase:2} task:ASCP-E8-15#0
       ASCP-E8-15.1 Wire the subagent/hook inner loop
       ↳ Category: Orchestration Subtasks Wire initializer->(human plan approval)->implementer->verifier driven by the six hooks; assert no external agent-reasoning framework on the default path (task 43). Author the integration test exercising one full slice loop end-to-end (initializer-…
    [221] «Backlog» {phase:2} task:ASCP-E8-15#1
       ASCP-E8-15.2 Optional Temporal/Inngest durable stub behind a flag
       ↳ Category: Orchestration Subtasks claude -p as a durable step; each tool call a separate activity; OFF by default (task 43.1, Phase 5). Enable only when multi-hour crash pain is felt.
    [222] «Backlog» {phase:0} task:ASCP-E8-15#2
       ASCP-E8-15.3 Keep Agent_Teams off the gating path
       ↳ Category: Infrastructure Subtasks Add a grep/CI gate asserting no Agent_Teams peer-to-peer primitive appears in any hook/gate decision path.
    [223] «Backlog» {phase:1} task:ASCP-E8-15#3
       ASCP-E8-15.4 Expose the inner-loop topology in Plane
       ↳ Category: API Subtasks On each subagent transition, drive the linked issue through the canonical states via REST. Stamp agent_role, worktree_branch, and agent_run_id (traceability triple: issue<->branch<->run).
  [58] «Spec-Verified» {phase:0,type:wiring,gate:completion,human:review} story:ASCP-E8-18
     ASCP-E8-18: Human-in-the-Loop Plan Approval & PR Review
     ↳ Latent contradiction fix (C14): asserts the plan-approval PreToolUse gate as a working exit-2 block (CHECK-4f UNSAT), but D10 is DEFERRED and verification 3 notes A7's plan-approval is 'prose-only/unenforced until D10 lands'. Mark the enforcement leg DEFERRED; do not assume it is…
    [224] «Backlog» {phase:2} task:ASCP-E8-18#0
       ASCP-E8-18.1 Implement the PreToolUse plan gate (check_plan_approval)
       ↳ Category: Orchestration Subtasks Block all implementation Write/Edit/MultiEdit when plan-approved.json is absent, exit 2 (task 6.1). Block when plan-approved.json.feature_list_sha != canonical SHA-256 of the current feature_list.json (require re-approval). Handle missing/corrupt …
    [225] «Backlog» {phase:2} task:ASCP-E8-18#1
       ASCP-E8-18.2 Wire missing-context injection through the Initializer
       ↳ Category: Orchestration Subtasks On session start, read plan-approved.json.notes and inject into run_state so the Implementer's context receives it (task 10.1). Ensure the Initializer enters plan mode and NEVER writes plan-approved.json itself.
    [226] «Backlog» {phase:1} task:ASCP-E8-18#2
       ASCP-E8-18.3 Configure the required-reviewer repository ruleset
       ↳ Category: API Subtasks Configure a GitHub repository ruleset requiring a human reviewer on the protected branch; document in docs/github-ruleset.md (task 14.2). On PR open, transition the Plane issue to Human-Review via REST; on reviewer approval + merge, transition to Done. Writ…
    [227] «Backlog» {phase:0} task:ASCP-E8-18#3
       ASCP-E8-18.4 Define and validate the plan-approved.json marker
       ↳ Category: Infrastructure Subtasks Author the marker schema (feature_list_sha, notes). Add the Z3 fixture for CHECK-4f and the Property 6 PBT (SHA-bound re-block).
  [59] «Agent-Executing» {phase:3,priority:normal,type:nfr} story:ASCP-E8-19
     ASCP-E8-19: Predictive Routing (Optional, Off-Gate)
     ↳ EARS requirements [optional] WHERE predictive next-step routing is enabled, the system shall inject predictions only as advisory context (via a UserPromptSubmit or SessionStart context-injection hook, or an MCP retrieve tool). [unwanted] IF a design routes a prediction into a blo…
    [228] «Backlog» {phase:2} task:ASCP-E8-19#0
       ASCP-E8-19.1 Implement off-gate advisory prediction injection
       ↳ Category: Orchestration Subtasks Inject predictions via a UserPromptSubmit/SessionStart context-injection hook or MCP retrieve tool (task 53, Phase 6, optional). Build on Speculative Actions / semantic-router / Claude memory tool. Assert no prediction value ever reaches an allow/…
    [229] «Backlog» {phase:0} task:ASCP-E8-19#1
       ASCP-E8-19.2 Tag and measure predicted-routing spans
       ↳ Category: Infrastructure Subtasks Tag predicted-routing spans distinctly (Phase 3 observability). Emit prediction-acceptance and prediction-accuracy metrics; wire a drift threshold that disables routing.
    [230] «Backlog» {phase:1} task:ASCP-E8-19#2
       ASCP-E8-19.3 Surface a Plane toggle for predictive routing
       ↳ Category: API Subtasks Expose an operator-controlled enable/disable property on the project (default OFF) via REST. On drift, auto-disable and post a comment — never alter a gate or terminal state.
  [60] «Spec-Verified» {phase:0,type:wiring} story:ASCP-E8-20
     ASCP-E8-20: Execution Bounds & Quality Threshold Registry
     ↳ Expand E8-20 to OWN authoring tools/execution_bounds (PREFERRED over a standalone item). It is the operator-overridable threshold/role registry holding SPEC_COMPLETION_HARD_CAP=7, the Z3 60s timeout, the vague-adjective proximity window, BLOCK_ESCALATION_CAP, and VERIFIER_ROLE. E…
    [231] «Backlog» {phase:0} task:ASCP-E8-20#0
       ASCP-E8-20.1 Build the execution-bounds config module
       ↳ Category: Infrastructure Subtasks Centralize coverage 85%, slice <=15m, iteration cap 25, retries 3, spec loop 7, validator timeout 60s, export <=5s, token budget 1,000,000, reasoning-loop K=3, retention 365d, faithfulness 0.8, answer-relevancy 0.7, kill-switch <=30s (task 44). I…
    [232] «Backlog» {phase:2} task:ASCP-E8-20#1
       ASCP-E8-20.2 Wire consumers to the registry
       ↳ Category: Orchestration Subtasks Point evaluate_stop (caps/budget/no-progress), implementer.md (retry/token budget), the reasoning-loop detector (K), and the verifier (coverage/perf/a11y) at the central registry. Remove duplicated constants from those consumers.
    [233] «Backlog» {phase:1} task:ASCP-E8-20#2
       ASCP-E8-20.3 Expose thresholds + owners in Plane
       ↳ Category: API Subtasks Mirror each threshold + its owner as project properties via REST. Require an operator role to change a value; record every override as an issue comment / audit entry.
  [61] «Spec-Verified» {phase:0,type:wiring,gate:stop} story:ASCP-E8-21
     ASCP-E8-21: HANDOFF Termination Semantics (Exit-0, Distinct from Done)
     ↳ Consumes run_state counters (block_streak, external_blocker, subagent_block_repeat_n) that are inert until the D3 populator (NEW-02). Add the NEW-02 dependency and the COH-3 accept-value note (A4 approve->allow; update lockstep test). R5 scope contract: E8-21 owns the escalation/…
    [234] «Backlog» {phase:2} task:ASCP-E8-21#0
       ASCP-E8-21.1 Implement HANDOFF-before-block ordering in evaluate_stop
       ↳ Category: Orchestration Subtasks Place cap->budget->no-progress HANDOFF checks (each return allow() after write status=handoff + emit_handoff_summary) BEFORE the violation_count/empty-model/unproven-items blocks (task 5.1). Phase-discriminate the cap (spec->spec_pass_count/7; imp…
    [235] «Backlog» {phase:2} task:ASCP-E8-21#1
       ASCP-E8-21.2 Encode the spec-completion lex-specialis tiebreak
       ↳ Category: Orchestration Subtasks At spec_pass_count>=SPEC_COMPLETION_HARD_CAP with violation_count>0, ensure the cap-HANDOFF (exit 0) returns before the violation_count>0 block can fire (task 5.1). Keep the violation_count>0 exit-2 block on passes strictly before the cap; fail cl…
    [236] «Backlog» {phase:2} task:ASCP-E8-21#2
       ASCP-E8-21.3 Implement the reentrancy guard composition
       ↳ Category: Orchestration Subtasks with_reentrancy_guard(evaluate_stop) via run_state.stop_hook_active; release the flag only when the blocking condition clears (tasks 5.1, 5.5). Unit test asserts no cascade during a blocking cycle.
    [237] «Backlog» {phase:0} task:ASCP-E8-21#3
       ASCP-E8-21.4 Add the HANDOFF Z3 fixtures
       ↳ Category: Infrastructure Subtasks Reproduce CHECK-3 (cap->Done under unproven is UNSAT) in formal_verification_merged.py. Reproduce CHECK-5b/5c (block-on-cap UNSAT) and CHECK-8c (block-on-no-progress UNSAT).
    [238] «Backlog» {phase:1} task:ASCP-E8-21#4
       ASCP-E8-21.5 Drive the Plane HANDOFF terminal state
       ↳ Category: API Subtasks On status=handoff, transition the issue to HANDOFF, set run_state=handoff, apply the handoff label, and post the HANDOFF summary via REST. Enforce that a HANDOFF issue can never reach Done.
  [62] «Spec-Compiling» {phase:3,priority:high,type:functional,agent:research} story:ASCP-E8-24
     ASCP-E8-24: Checklist-Approval Gate + Research Epistemic Integrity
     ↳ EARS requirements [unwanted] IF a Domain_Baseline_Checklist is in DRAFT (approved_at is NULL in domain_baseline_checklists), THEN it shall NOT be used for discovery; the PreToolUse checklist-approval guard shall block any discovery Write that references it (exit 2, CHECK-12a/12b)…
    [239] «Backlog» {phase:2} task:ASCP-E8-24#0
       ASCP-E8-24.1 Add check_checklist_approval to pre_tool_use_hook.py
       ↳ Category: Orchestration Subtasks Block any Initializer/discovery Write referencing a checklist whose approved_at is NULL in domain_baseline_checklists (task 50.1). Chain it with the plan/scope/artifact/status checks and the 49.1 integrity guard in the order pinned at task 6.1.
    [240] «Backlog» {phase:2} task:ASCP-E8-24#1
       ASCP-E8-24.2 Implement tools/research_claim_validator.py
       ↳ Category: Orchestration Subtasks Validate that every external claim carries a source URL + authority-tier label and passes the independent fact-check before human review; reject unlabeled/unverified claims (task 50, Property 29). Validate draft claims against schema/checklist_ite…
    [241] «Backlog» {phase:0} task:ASCP-E8-24#2
       ASCP-E8-24.3 Migrate the checklist version-history table
       ↳ Category: Infrastructure Subtasks Create domain_baseline_checklists (product_class, version, sha, file_path, approved_at, approved_by) in migration 006_domain_baseline_checklists.sql (task 28.6). Add the CHECK-12 Z3 fixtures and the Property 27 PBT.
    [242] «Backlog» {phase:1} task:ASCP-E8-24#3
       ASCP-E8-24.4 Surface checklist approval in Plane
       ↳ Category: API Subtasks Represent a DRAFT checklist as an issue requiring human:review; on human approval write approved_at + approved_by and flip the issue out of review via REST. Link checklist_ref (path/version/sha) onto the discovery issue for auditable derivation.
  [63] «In-Verification» {phase:3,priority:normal,type:nfr} story:ASCP-E8-26
     ASCP-E8-26: Reasoning-Loop Detection (REASONING span, K=3)
     ↳ EARS requirements [event-driven] WHEN telemetry is analyzed, the system shall mark reasoning spans with a custom span ATTRIBUTE claude.span.kind=reasoning on an OTel INTERNAL span (NOT a new SpanKind enum value). [event-driven] WHEN >=K identical tool-call signatures occur (DEFAU…
    [243] «Backlog» {phase:0} task:ASCP-E8-26#0
       ASCP-E8-26.1 Emit the REASONING span attribute
       ↳ Category: Infrastructure Subtasks Mark reasoning spans as OTel INTERNAL spans carrying claude.span.kind=reasoning (attribute, not a SpanKind value) (task 52, REASONING leg). Pin the OTel SDK + GenAI semconv versions.
    [244] «Backlog» {phase:2} task:ASCP-E8-26#1
       ASCP-E8-26.2 Implement the repeated-action detector
       ↳ Category: Orchestration Subtasks Compute tool-call signatures; flag >=K (DEFAULT 3, from the Req-20 registry) identical signatures as a reasoning loop (task 52). Emit the first-class signal.
    [245] «Backlog» {phase:0} task:ASCP-E8-26#2
       ASCP-E8-26.3 Forward the signal to the trace endpoint
       ↳ Category: Infrastructure Subtasks Forward the reasoning-loop signal to the same OTLP endpoint as hook gate-decision events (task 36.1). Assert it complements (does not replace) the no-progress watchdog.
    [246] «Backlog» {phase:1} task:ASCP-E8-26#3
       ASCP-E8-26.4 Surface reasoning-loop alerts in Plane
       ↳ Category: API Subtasks On a reasoning-loop flag, post a comment on the linked issue and apply a priority:high label via REST. If the loop also trips no-progress, reflect the resulting HANDOFF transition.
  [64] «In-Verification» {phase:0,priority:blocking,type:functional,gate:completion} story:ASCP-E8-29
     ASCP-E8-29: Structured Omission Declaration Gate
     ↳ EARS requirements [event-driven] WHEN a subagent (initializer, research, verifier) completes a discovery, research, or verification pass, THEN its output shall include a non-null omission_declaration field listing, by EARS scenario category (Primary/Alternate/Exception/Recovery/N…
    [247] «Backlog» {phase:0} task:ASCP-E8-29#0
       ASCP-E8-29.1 Author the subagent-output schema
       ↳ Category: Infrastructure Subtasks Add omission_declaration as a REQUIRED, non-nullable field to schema/subagent_output.schema.json (the single envelope validated for all roles) (task 54, schema leg). Keep evidence[] present only for the verifier role.
    [248] «Backlog» {phase:2} task:ASCP-E8-29#1
       ASCP-E8-29.2 Implement the omission_guard in subagent_stop_hook.py
       ↳ Category: Orchestration Subtasks Reject (exit 2) any initializer/research/verifier result whose omission_declaration is null/absent; exempt the Implementer (task 54). Ensure it ships runnable alongside task 8's base evidence-schema validator before Phase 1. Wire audit_log.append(…
    [249] «Backlog» {phase:0} task:ASCP-E8-29#2
       ASCP-E8-29.3 Add the omission-gate Z3 + property tests
       ↳ Category: Infrastructure Subtasks Encode CHECK-13a/13b in formal_verification_merged.py. Author the Property 30 PBT: null/absent->reject; non-null->accept; Implementer exempt (task 39.20).
    [250] «Backlog» {phase:1} task:ASCP-E8-29#3
       ASCP-E8-29.4 Surface omission declarations in Plane
       ↳ Category: API Subtasks On acceptance, render the omission_declaration ([Gap] markers by EARS category) as a structured issue comment via REST so a reviewer sees the declared gaps. On a null/absent rejection, transition the issue to Blocked and label blocked.

================================================================================
[251] «Spec-Verified» {phase:0,type:wiring} ascp-audit-reorg:NEW-14
   Board-integrity: add explicit blocked-by dependency edges on E8-13 (settings.json) + the ralph-loop disable from every hook-consuming story
   ↳ The board-integrity edge that makes the systemic inert-spine assumption explicit. Across E2-E7 the per-story analysis returned !CONTRA:NONE on substance — no story logically contradicts the audit — but every gate-bearing AC is written AS IF the hooks fire (e.g. E4-S1 AC4/AC5 desc…

================================================================================
[252] «Spec-Verified» {phase:0,type:wiring,gate:stop} ascp-audit-reorg:NEW-01
   SessionStart Spine Canary & Resume Re-Orientation (A5 — build 05-session_start_hook.py)
   ↳ The load-bearing canary (A5). Asserts the governance hooks are registered and emits a LOUD warning when the spine is unwired/partial. It is the fix for the silent-inertness root of all P0s and the resume-integrity half of A-AMBIG-01. E8-13 registers SessionStart as a hook type bu…

================================================================================
[253] «Spec-Verified» {phase:0,type:wiring,gate:completion} ascp-audit-reorg:NEW-10
   Unify the A6 PostToolUse forcing-function as one hook both stories extend (06-post_tool_use_hook.py)
   ↳ One A6 PostToolUse hook (A6). Currently split across ASCP-E4-S2 (wiring leg) and ASCP-E4-S3 (five-layer leg) with NO item owning the unified hook — a redundancy/convergence gap (R1). This story builds the one hook both stories extend. The .json leg is LIVE: tools/feature_list_che…

================================================================================
[254] «Spec-Verified» {phase:0,type:wiring,agent:initializer,agent:coder,agent:tester,agent:research} ascp-audit-reorg:NEW-05
   Author the four canonical subagent base-prompts (A7) + COH-1 actor-name reconciliation
   ↳ The four base-prompts A7 + the COH-1 byte-for-byte name convention. .claude/agents/ holds only .gitkeep. Authoring is scattered across E3/E4 tasks with NO single item owning all four canonical A7 base-prompts as a unit. CRITICAL: the COH-1 'name: <role>.md' frontmatter convention…

================================================================================
[255] «Spec-Verified» {phase:0,type:functional} ascp-audit-reorg:NEW-04
   Root CLAUDE.md Durable-Invariant Anchor + 4 P2 Doctrines (A9)
   ↳ The CH-11 durable-invariant anchor (A9). No root CLAUDE.md exists on disk. A3/A4/A7/A8 reason strings dereference it by short name (actor-independence, human-owned artifacts, canonical-source pin, verifier-only flips). It also carries the four P2 doctrines that are otherwise whol…

================================================================================
[256] «Backlog» {phase:0,type:wiring} ascp-audit-reorg:NEW-09
   tools/execution_bounds threshold + role registry (standalone — ONLY if E8-20 stays numerics-scoped)
   ↳ Conditional create. Only instantiate if UPD-E8-20 is NOT taken (i.e. E8-20 remains scoped to numerics). Authors tools/execution_bounds with the same AC set as UPD-E8-20. Default-disabled: executor should prefer the E8-20 fold and skip this create unless that fold is rejected.

================================================================================
[257] «Spec-Verified» {phase:0,type:functional} ascp-audit-reorg:NEW-08
   Author tools/spec_validator.py (Z3 EARS encoder + vague-adjective scanner + UNMAPPED + provenance + validate_spec verdict)
   ↳ The single named shared prerequisite (remediation §7.1/§7.2) underpinning E3-1/-2/-4. Built piecemeal across three stories' tasks with NO single owning item and ABSENT on disk, so none of E3-1/-2/-4 is execution-ready.

================================================================================
[258] «Spec-Verified» {phase:0,type:wiring,gate:stop} ascp-audit-reorg:NEW-02
   Loop Driver / run_state Populator + BLOCKED-ON sentinel parser (D3)
   ↳ The audit's #1 DEFERRED prerequisite (D3). A2/A4 (E8-14/E8-21), E5-S10, E3-4, E4-S1, and E6-S2/S3/S5 all CONSUME run_state counters but NOTHING populates them — cap/budget/no-progress HANDOFF is inert until a driver writes them. E8-14 owns only the 005_run_state.sql column migrat…

================================================================================
[259] «Spec-Verified» {phase:0,type:functional} ascp-audit-reorg:NEW-03
   Bounded-Autonomy Goal Directive (A8 — HANDOFF via BLOCKED-ON sentinel)
   ↳ The canonical bounded-autonomy contract (A8). No owning story. Authorizes self-continuation only when in-scope AND objectively checkable, converts blockers into surface-and-HANDOFF (killing the idle 'standing by' loop), pins the canonical source, pairs anti-fabrication with its t…

================================================================================
[260] «Spec-Verified» {phase:1,type:functional} ascp-audit-reorg:NEW-13
   Author the 00-charter tier-1 base-prompt engineering standard (CH-01/06/07/08) as a formal deliverable
   ↳ The tier-1 charter standard (00-charter, CH-01/06/07/08) as a FORMAL board deliverable. The charter principles (single-source-of-truth, predictions-never-gate, located-oracle-before-claim, escalate-don't-re-inject) are applied piecemeal across many items (E8-15/29 base-prompts, E…

================================================================================
[261] «Spec-Verified» {phase:1,type:nfr,gate:completion} ascp-audit-reorg:NEW-06
   Add a checkable success-oracle for disable / teardown tasks (kill-switch & ralph-disable)
   ↳ The teardown-specific success-oracle (A-LOOP-01). A-LOOP-01 was a 3-round teardown with no checkable success oracle for the disable scenario. A generic checkable-success-oracle doctrine exists (NEW-04 AC2 / E8-20) but no CONCRETE oracle exists for the specific disable/teardown pa…

================================================================================
[262] «Backlog» {phase:2,type:wiring} ascp-audit-reorg:NEW-11
   PreCompact resume_state_hash checkpoint hook (D7)
   ↳ The producer of resume_state_hash for A5's drift compare (D7). Its absence keeps A-AMBIG-01's integrity half permanently PARTIAL (the only remaining PARTIAL finding in the audit). Named as a prereq the SessionStart canary (NEW-01) depends on (COH-2). Likely E7 durable-state/obser…

================================================================================
[263] «Backlog» {phase:2,type:wiring,gate:completion,human:review} ascp-audit-reorg:NEW-07
   (Deferred) PreToolUse plan-approval HITL gate as enforced exit-2 block (D10) + scope-sequencing (D11)
   ↳ Scope decision tracker (D10/D11). E2-S3 AC2, E4-S1 AC4/AC5, E6-S2, and E8-18 all PRESUPPOSE the plan-approval SHA-binding gate (and scope-sequencing) as a working exit-2 block, but the audit explicitly classes D10/D11 as DEFERRED/out-of-scope for the steering-string remediation. …

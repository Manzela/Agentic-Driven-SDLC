# Plane MCP server — Claude Code ⇄ Plane (read + write, both ways)

`plane_mcp_server.py` is a [Model Context Protocol](https://modelcontextprotocol.io) stdio
server that lets Claude Code (or any MCP client) read **and** write the live ASCP Plane board
directly as tool calls. It is the **agent → board** half of the E6 bidirectional contract.

> The **board → agent** half (a webhook receiver that dispatches Plane events to agents) is a
> separate always-on daemon. As of this commit the receiver writes a queue
> (`webhook_handler.py` → `.agent_queue.jsonl`) but **no consumer exists yet** — that
> dispatcher is the next build (see the roadmap in the PR description / `audit/`).

## Tools (14)

| Tool | R/W | Purpose |
|---|---|---|
| `plane_context` | R | Connected workspace/project, **redacted** token, state names |
| `plane_list_states` | R | The 12 workflow states |
| `plane_list_issues` | R | Work-items (filter by state/search) |
| `plane_get_issue` | R | One work-item |
| `plane_list_cycles` / `plane_list_modules` | R | Sprints/phases · epics/feature-groups |
| `plane_create_issue` | W | New work-item |
| `plane_update_issue` | W | Edit name/description/priority/state |
| `plane_transition` | W | Drive the 12-state agent workflow — **enforces actor authority** |
| `plane_add_comment` | W | HTML comment |
| `plane_post_evidence` | W | 4-field `Evidence_Record` (the proof trail) |
| `plane_assign_cycle` / `plane_assign_module` | W | Bucket work-items |
| `plane_request` | R/W | Escape hatch: call **any** Plane REST endpoint (settings, members, views, pages) |

## Security model

- **Token is never committed or printed.** It is loaded lazily from `PLANE_API_KEY` (env) or a
  gitignored creds file (`PLANE_CREDS_FILE`, default `../plane-selfhost/credentials.env`).
  `plane_context` only ever returns the first 10 chars + `…redacted`.
- **The completion gate cannot be bypassed via MCP.** `plane_transition` enforces the same
  `TRANSITION_AUTH` actor model as `plane_client.py`: only the **verifier** may set `Done`;
  cap/budget/no-progress route to `HANDOFF`. An unauthorized transition is rejected with
  `PermissionError` and performs **no write**. (Verified: `implementer → Done` ⇒ rejected.)
- **No secrets in `.mcp.json`.** The committed template is `.mcp.json.example`; the real
  `.mcp.json` is gitignored and only carries a *path* to the creds file, never the token.
- Rate-limited (≥1.1 s between calls) with retry/backoff on 429/5xx.
- `plane_request` is a deliberate full-coverage escape hatch — it can write settings. The
  token's own Plane permissions are the outer bound; scope the token to least privilege.

## Wire it into Claude Code

```bash
cp .mcp.json.example .mcp.json
# then set the creds-file path (this machine):
export PLANE_CREDS_FILE="/Users/danielmanzela/Agentic-Driven SDLC Platform/plane-selfhost/credentials.env"
```

`.mcp.json` (already created locally, gitignored) points `command: python3` at this server with
`PLANE_CREDS_FILE` set. Restart Claude Code in this repo; approve the project MCP server when
prompted; then the `plane-ascp` tools are callable. The server is **pure stdlib** — no install.

### Smoke test (no MCP client needed)

```bash
PLANE_CREDS_FILE="/abs/path/credentials.env" \
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
 '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"plane_context","arguments":{}}}' \
 | python3 plane-integration/plane_mcp_server.py
```

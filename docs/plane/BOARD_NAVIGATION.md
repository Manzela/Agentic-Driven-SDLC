# ASCP Plane Board — Navigation Guide

The board is organized along the two axes every mature SDLC backlog needs — the
**WHAT** (Epics → Stories → Tasks) and the **WHEN** (Phases 0→6) — plus priority and
agent-ownership lenses. Open the **Views** tab in the project to jump straight to any
lens below; each is a saved, public view (no filtering required).

## Structure

| Layer | Plane object | Count | Notes |
|-------|--------------|-------|-------|
| **Epic** | Issue (top-level) + **Module** | 8 (E1–E8) | The feature axis. Each epic is also a Module. |
| **User Story** | Issue, `parent` = Epic | 49 | Carries EARS requirements + acceptance criteria. |
| **Task** | Issue, `parent` = Story | 186 | Inherits its story's **priority**. |
| **Subtask** | checklist inside the Task description | — | Kept as in-task checklists (can be promoted to real sub-issues on request). |
| **Phase** | **Cycle** | 7 (Phase 0–6) | The time axis; each item is scheduled into one phase window. |
| **Workflow** | **State** | 12 | Backlog → Agent-Triaged → … → Done (+ Blocked/Failed/Handoff). |

Expand any Epic or Story (the ▸ caret / "Sub-issues") to drill **Epic → Story → Task**
inline. Priority is set on every item, so any view can be ordered/grouped by it.

## Curated Views (Views tab, in order)

| View | Layout | Use it to… |
|------|--------|-----------|
| 🎯 **Active Sprint — Phase 0** | Kanban by state | See only the current sprint (Phase 0 — Spine) and what's in flight right now. |
| 🗺️ **Roadmap — Phases 0→6** | Gantt by cycle | See the whole delivery timeline; every item is dated into its phase window. |
| 🚦 **Workflow Board** | Kanban by state | Run the day-to-day board; drag items across the 12 workflow states. |
| 📍 **By Phase (Sprint Plan)** | List by cycle | Plan/scope each phase 0→6 with its full item list. |
| 🏛️ **By Epic (Feature Map)** | List by module | Browse the 8 epics; expand to drill Epic → Story → Task. |
| 🔥 **Priority Triage** | Spreadsheet by priority | Re-prioritise fast in a dense grid (Urgent → None). |
| 🤖 **By Agent / Ownership** | List by label | See `agent:*` ownership, `gate:*` and `human:review` handoffs. |
| 📥 **Backlog Grooming** | Spreadsheet by priority | Groom only unstarted/backlog items for upcoming phases. |

The native **Cycles** and **Modules** tabs complement these with built-in progress
burndown per phase and per epic.

## Reproducing / re-running

Views are not exposed by Plane's community public REST API, so they're provisioned
through the Django ORM in the backend container:

```bash
docker exec -i <plane-api-container> python manage.py shell \
  < plane-integration/organize_plane_views.py
```

The script is idempotent: it cascades task priority, fills phase-derived start/target
dates (without clobbering manual edits), and upserts the eight views by name.

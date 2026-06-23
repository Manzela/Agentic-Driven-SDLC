#!/usr/bin/env python3
"""
Organize the live ASCP Plane board for fast navigation — "Tier-1 PM" layout.

Plane's community public REST API does NOT expose saved Views (the /views/ endpoint
404s), so curated Views must be created through the Django ORM inside the backend
container. This script is therefore designed to be piped into the API container:

    docker exec -i <plane-api-container> python manage.py shell < organize_plane_views.py

It performs three idempotent passes:

  1. Priority cascade — every Task (external_id "task:*") inherits its parent Story's
     priority (Epics=high, Stories from labels). Without this the 186 tasks are
     priority:none and "order by priority" is meaningless.
  2. Scheduling — every work item is given start/target dates from the phase-cycle it
     belongs to (via CycleIssue), so the Gantt "Roadmap" view renders real bars and
     the calendar/timeline layouts work. Only fills blanks (never clobbers manual edits).
  3. Curated Views — eight project Views covering the standard SDLC lenses:
       Active Sprint · Roadmap (Gantt) · Workflow Kanban · By Phase · By Epic ·
       Priority Triage · By Agent/Ownership · Backlog Grooming.
     Upsert by name, so re-runs update in place.

Config: edit PROJ_ID / OWNER_ID below (OWNER_ID must be a project member's user id;
the Views are attributed to them). Everything else is derived from the project.
"""
import collections
import os

# ---- config (project + owner: set via env; placeholders MUST be overridden) ----
PROJ_ID = os.environ.get("PLANE_PROJ", "YOUR_PROJECT_UUID")
OWNER_ID = os.environ.get("PLANE_OWNER_ID", "YOUR_OWNER_UUID")

from plane.db.models import IssueView, Project, Issue, Cycle, CycleIssue  # noqa: E402

proj = Project.objects.get(id=PROJ_ID)
ws = proj.workspace

# ---- 1) priority cascade onto tasks ----
issues = list(Issue.objects.filter(project=proj))
by_id = {i.id: i for i in issues}
pf = 0
for i in issues:
    if (i.external_id or "").startswith("task:") and (i.priority in (None, "none", "")):
        st = by_id.get(i.parent_id)
        i.priority = st.priority if (st and st.priority not in (None, "none", "")) else "medium"
        i.save(update_fields=["priority"])
        pf += 1
print("PRIORITY_CASCADE_TASKS", pf)


# ---- 2) schedule items from their phase-cycle window ----
def asdate(d):
    return d.date() if hasattr(d, "date") else d


dated = 0
for ci in CycleIssue.objects.filter(cycle__project_id=PROJ_ID).select_related("cycle", "issue"):
    iss, cy, ch = ci.issue, ci.cycle, []
    if iss.start_date is None and cy.start_date:
        iss.start_date = asdate(cy.start_date); ch.append("start_date")
    if iss.target_date is None and cy.end_date:
        iss.target_date = asdate(cy.end_date); ch.append("target_date")
    if ch:
        iss.save(update_fields=ch); dated += 1
print("DATED_ISSUES", dated)

ph0 = Cycle.objects.filter(project=proj, name__startswith="Phase 0").first()
ph0_id = str(ph0.id) if ph0 else None

# ---- 3) curated views ----
DP = {"key": True, "priority": True, "state": True, "labels": True, "assignee": True,
      "due_date": True, "sub_issue_count": True, "cycle": True, "module": True,
      "start_date": True, "link": False, "attachment_count": False, "estimate": False,
      "created_on": False, "updated_on": False}


def df(layout, group_by=None, order_by="sort_order", sub_group_by=None):
    return {"layout": layout, "group_by": group_by, "sub_group_by": sub_group_by,
            "order_by": order_by, "show_empty_groups": True, "type": None,
            "calendar": {"show_weekends": True, "layout": "month"}}


VIEWS = [
    ("🎯 Active Sprint — Phase 0",
     "Current sprint only (Phase 0 — Spine), as a Kanban across workflow states. What the agents are executing right now.",
     ({"cycle": [ph0_id]} if ph0_id else {}), df("kanban", group_by="state"), 5000),
    ("🗺️ Roadmap — Phases 0→6",
     "Gantt timeline of the whole delivery, grouped by phase-cycle (the WHEN axis). Pair with the native Cycles tab for sprint progress.",
     {}, df("gantt_chart", group_by="cycle"), 10000),
    ("🚦 Workflow Board",
     "Kanban across the 12-state agent workflow (Backlog to Done). Drag items to advance state.",
     {}, df("kanban", group_by="state"), 20000),
    ("📍 By Phase (Sprint Plan)",
     "Every work item grouped by its phase-cycle 0 to 6. Sprint-planning lens.",
     {}, df("list", group_by="cycle"), 30000),
    ("🏛️ By Epic (Feature Map)",
     "Work grouped by the 8 epics (modules E1-E8) — the WHAT axis. Expand items to drill Epic > Story > Task.",
     {}, df("list", group_by="module"), 40000),
    ("🔥 Priority Triage",
     "All work in a dense grid grouped by priority (Urgent to None). Triage and re-prioritisation.",
     {}, df("spreadsheet", group_by="priority"), 50000),
    ("🤖 By Agent / Ownership",
     "Grouped by label — surfaces agent ownership, gates and human review handoffs.",
     {}, df("list", group_by="labels"), 60000),
    ("📥 Backlog Grooming",
     "Unstarted and backlog items only, grouped by priority, for grooming upcoming work.",
     {"state_group": ["backlog", "unstarted"]}, df("spreadsheet", group_by="priority"), 70000),
]

created = updated = 0
for name, desc, filters, disp, so in VIEWS:
    vals = dict(description=desc, filters=filters, display_filters=disp,
                display_properties=DP, access=1, sort_order=so, query={},
                rich_filters={}, is_locked=False, owned_by_id=OWNER_ID, updated_by_id=OWNER_ID)
    obj = IssueView.objects.filter(project=proj, name=name).first()
    if obj:
        for k, v in vals.items():
            setattr(obj, k, v)
        obj.save(); updated += 1
    else:
        IssueView.objects.create(workspace=ws, project=proj, name=name,
                                 created_by_id=OWNER_ID, **vals); created += 1
print("VIEWS_CREATED", created, "UPDATED", updated)
for so, nm in IssueView.objects.filter(project=proj).order_by("sort_order").values_list("sort_order", "name"):
    print("VIEW", so, nm)

"""materialize_feature_list.py — compile the website spec into the coverage model.

Parses docs/website/autonomous-agent.dev/requirements.md (205 EARS requirements)
and emits the 209-item apps/web/feature_list.json coverage model:
  * 205 materialized requirements (two-segment spec IDs remapped to the canonical
    three-segment pattern ^[A-Z]+-[A-Z]+-[0-9]{3}$, source_ears_id preserved),
  * + 4 Bucket-A / supply-chain items (security-header matrix, privacy-safe RUM,
    whole-site visual-regression, SBOM/SCA).
All items default to status="unproven". priority is the schema's integer form
(P0->1 .. P3->4). PERF/A11Y items are typed NFR with the routing subtype the
schema requires; the rest are functional. Schema-valid against
schema/feature_list.schema.json. Pure stdlib.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HEADER = re.compile(r"^### ([A-Z0-9]+)-(\d+)\s+—\s+(.*?)\s+·\s+(P[0-3])\s+·\s+EARS:\s+(\S+)", re.M)

# domain -> (canonical-prefix, family) ; all-alpha so ids match ^[A-Z]+-[A-Z]+-NNN$
DOMAIN_MAP = {
    "DS": ("DS", "TOK"), "IA": ("IA", "NAV"), "HOME": ("HOME", "HOM"),
    "LOOP": ("LOOP", "LUP"), "CONTENT": ("CONTENT", "CNT"), "PAGE": ("PAGE", "PAG"),
    "TECH": ("TECH", "TEC"), "TOOL": ("TOOL", "TUL"), "PERF": ("PERF", "PRF"),
    "A11Y": ("AYY", "WCAG"), "SEO": ("SEO", "MTA"), "PRIV": ("PRIV", "SEC"),
}
PRIORITY_MAP = {"P0": 1, "P1": 2, "P2": 3, "P3": 4}
# domains that are wholly NFR, with their routing subtype
NFR_DOMAIN = {"PERF": "performance", "A11Y": "accessibility"}
# spec EARS pattern -> schema enum (omit when it does not map, e.g. 'complex')
EARS_MAP = {"ubiquitous": "ubiquitous", "event": "event-driven", "state": "state-driven",
            "unwanted": "unwanted", "optional": "optional"}

EXTRAS = [
    ("REQ-SEC-001", "NFR", "security", 1,
     "Full security-header matrix (HSTS preload, Referrer-Policy, Permissions-Policy, frame-ancestors/COOP/CORP) as a tested header set"),
    ("REQ-RUM-001", "NFR", "performance", 2,
     "Privacy-safe Real-User Monitoring (web-vitals RUM, PII-free) for real-world CWV + client errors"),
    ("REQ-VIS-001", "NFR", "reliability", 2,
     "Whole-site visual-regression gate across routes x breakpoints x reduced-motion"),
    ("REQ-SCA-001", "NFR", "security", 1,
     "SBOM (CycloneDX) + dependency-CVE software-composition-analysis required check"),
]


def materialize(requirements_md: Path) -> dict:
    text = Path(requirements_md).read_text()
    items: list[dict] = []
    for dom, num, title, prio, ears in HEADER.findall(text):
        if dom not in DOMAIN_MAP:
            continue
        prefix, fam = DOMAIN_MAP[dom]
        item: dict = {
            "id": f"{prefix}-{fam}-{int(num):03d}",
            "type": "NFR" if dom in NFR_DOMAIN else "functional",
            "priority": PRIORITY_MAP.get(prio, 4),
            "title": title.strip(),
            "source_ears_id": f"{dom}-{int(num):02d}",
            "dependencies": [],
            "acceptance_criteria": [
                f"See docs/website/autonomous-agent.dev/requirements.md {dom}-{int(num):02d} for the full EARS statement and objective acceptance criteria."
            ],
            "in_scope": True,
            "status": "unproven",
        }
        if dom in NFR_DOMAIN:
            item["nfr_subtype"] = NFR_DOMAIN[dom]
        if ears in EARS_MAP:
            item["ears_pattern"] = EARS_MAP[ears]
        items.append(item)

    for _id, _type, subtype, prio, title in EXTRAS:
        items.append({
            "id": _id, "type": _type, "nfr_subtype": subtype, "priority": prio,
            "title": title, "source_ears_id": "Bucket-A",
            "dependencies": [], "acceptance_criteria": [title],
            "in_scope": True, "status": "unproven",
        })

    return {
        "schema_version": "1.0.0",
        "product_class": "public-marketing-website",
        "checklist_ref": {"path": "baselines/public-marketing-website.json", "version": "0.1.0", "sha": ""},
        "items": items,
    }


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[1]
    model = materialize(root / "docs/website/autonomous-agent.dev/requirements.md")
    out = root / "apps/web/feature_list.json"
    out.write_text(json.dumps(model, indent=2) + "\n")
    print(f"materialized {len(model['items'])} items -> {out}")
    sys.exit(0)

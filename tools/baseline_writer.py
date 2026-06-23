"""baseline_writer.py — the dispatcher (TCB) records the in-scope item set it
dispatched, as the TRUSTED baseline the merge gate checks the payload against.
Phase A.5: trusted JSON. Phase B: signed. Pure stdlib.

TRUST BOUNDARY: This file is part of the Trusted Computing Base (dispatcher).
The baseline it writes MUST be delivered to CI out-of-band — via a protected
CI artifact, a protected branch, or an environment secret — and NEVER read
from the PR payload alongside feature_list.json. An agent controlling the PR
payload cannot tamper with a baseline written here. Phase B adds a cryptographic
signature over this output; Phase A.5 trusts it by delivery path alone.
"""
from __future__ import annotations

import json
from pathlib import Path


def write_baseline(*, required_in_scope: list[str], out_path) -> dict:
    doc = {"required_in_scope": [str(x) for x in required_in_scope]}
    Path(out_path).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc

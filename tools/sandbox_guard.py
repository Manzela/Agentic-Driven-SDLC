"""sandbox_guard.py — sandbox / worktree-isolation primitives (REQ-17.4, task 46).

Phase-1 component for the **Sandbox & Worktree Isolation** subsection of
design.md (REQ-17.4): "All agent-executed code runs inside a sandbox. The
sandbox is the security boundary; the per-slice git worktree is the unit of
isolation mounted into it." This module realizes the two host-side checks that
back that boundary as importable, deterministic predicates:

- **Network egress** is **DENIED by default**; any required egress is an
  explicit, audited allowlist exception (design.md table row "Network":
  "Egress DENIED by default"). `egress_allowed` is the host-side admission
  check — only hosts on the allowlist may be reached.
- **Filesystem writes** are confined to the **per-slice git worktree mounted
  into the sandbox**; the rest of the host FS is read-only or absent (design.md
  table row "Filesystem"). `check_worktree_confinement` is the host-side
  path-resolution check — a path must resolve INSIDE the allowed worktree root,
  blocking `../` traversal, absolute-outside paths, and symlink escape.

Together these "mean an agent can only modify files in its own slice's worktree,
and cannot reach the network unless an exception is granted — satisfying
REQ-17.4's isolation requirement while preserving the one-slice/one-worktree
discipline" (design.md, REQ-17.4).

Both predicates are **default-deny / default-confine**: ambiguous or
unparseable input resolves to BLOCKED, never to ALLOW — consistent with
REQ-GATE-005 ("ambiguous states SHALL resolve to blocked, not passed") and the
"never fail-open" rule the rest of the platform's guards follow.

PURE STDLIB (``urllib.parse``, ``os.path``). No network or filesystem mutation
is performed — these are admission predicates a sandbox launcher / policy layer
consults, not enforcers themselves.

Public surface:

    egress_allowed(url, allowlist) -> bool
    check_worktree_confinement(path, allowed_root) -> bool
    build_sandbox_policy(allowed_hosts, worktree_root) -> dict
"""
from __future__ import annotations

import os.path
from urllib.parse import urlsplit


def _host_of(url: str) -> str | None:
    """Extract the lowercase hostname from ``url``, or ``None`` if absent.

    Uses ``urllib.parse.urlsplit`` so userinfo (``user:pass@``), an explicit
    ``:port``, and the path/query are stripped — only the bare host is compared,
    which prevents allowlist-bypass tricks like ``evil.test@trusted.example`` or
    ``trusted.example.attacker.test``. A scheme-relative / hostless URL (e.g.
    ``"/local/path"`` or ``""``) yields ``None`` so the caller default-denies.
    """
    try:
        parts = urlsplit(url)
    except (ValueError, AttributeError):
        return None
    host = parts.hostname  # already lowercased, userinfo/port stripped by urlsplit
    if not host:
        return None
    return host.rstrip(".").lower()  # drop FQDN trailing dot, normalize case


def egress_allowed(url: str, allowlist: list[str]) -> bool:
    """Return ``True`` iff ``url``'s host is on ``allowlist`` (default-deny).

    Egress is DENIED by default (design.md "Network" row); only hosts that
    appear as an explicit, audited allowlist exception may be reached. The
    comparison is on the parsed *hostname* alone — scheme, userinfo, port,
    path, and query are ignored — so neither a crafted userinfo segment
    (``https://trusted.example@evil.test/``) nor a path (``https://evil.test/
    trusted.example``) can spoof an allowed host.

    Default-deny edge cases (all return ``False``):
      * empty / ``None`` / non-string ``url``,
      * a URL with no parseable host (relative path, hostless),
      * an empty or ``None`` allowlist,
      * a host that does not exactly match an allowlist entry.

    Matching is EXACT on the normalized host (case-insensitive, trailing-dot
    stripped). No suffix/wildcard matching: ``api.trusted.example`` is NOT
    admitted by an allowlist entry of ``trusted.example`` — admitting subdomains
    silently would widen the audited exception, so each reachable host must be
    listed explicitly.
    """
    if not url or not isinstance(url, str):
        return False
    if not allowlist:
        return False
    host = _host_of(url)
    if host is None:
        return False
    allowed = {
        h.rstrip(".").lower()
        for h in allowlist
        if isinstance(h, str) and h.strip()
    }
    return host in allowed


def check_worktree_confinement(path: str, allowed_root: str) -> bool:
    """Return ``True`` iff ``path`` resolves INSIDE ``allowed_root`` (default-confine).

    Filesystem writes are confined to the per-slice worktree root (design.md
    "Filesystem" row). This predicate answers: does ``path``, once fully
    resolved, live within ``allowed_root``?

    Resolution defends against every escape vector:
      * **``../`` traversal** — ``os.path.realpath`` normalizes ``..`` segments
        before the prefix check, so ``<root>/../etc/passwd`` resolves outside
        and is blocked.
      * **absolute-outside** — an absolute path that does not sit under the root
        (``/etc/passwd``) resolves outside and is blocked.
      * **symlink escape** — ``realpath`` follows symlinks on BOTH ``path`` and
        ``allowed_root``, so a symlink inside the worktree that points out of it
        is resolved to its real target before comparison and cannot smuggle a
        write past the boundary.

    The containment test compares real, normalized paths and is anchored on a
    path separator (the root is suffixed with ``os.sep``) so a *sibling* whose
    name merely shares the root's prefix — e.g. root ``/wt/slice`` vs
    ``/wt/slice-evil`` — is NOT treated as contained. The root resolving to
    itself counts as confined (a write *to* the root directory is permitted).

    Default-confine edge cases (all return ``False``):
      * empty / ``None`` / non-string ``path`` or ``allowed_root``,
      * anything that raises during resolution (treated as ambiguous → blocked).
    """
    if not path or not isinstance(path, str):
        return False
    if not allowed_root or not isinstance(allowed_root, str):
        return False
    try:
        real_path = os.path.realpath(path)
        real_root = os.path.realpath(allowed_root)
    except (ValueError, OSError):
        # Ambiguous resolution → blocked, never fail-open (REQ-GATE-005).
        return False
    if real_path == real_root:
        return True
    # Anchor on the separator so /wt/slice does not contain /wt/slice-evil.
    return real_path.startswith(real_root + os.sep)


def build_sandbox_policy(allowed_hosts, worktree_root) -> dict:
    """Assemble the declarative sandbox policy for one slice execution.

    Encodes the design.md REQ-17.4 defaults — **egress default-deny**,
    **filesystem default-confine to the worktree** — as a serializable policy
    document a sandbox launcher (devcontainer locally; E2B for ephemeral CI)
    consults. Inputs are normalized but NOT trusted to be safe: the returned
    policy is the audited record of which egress exceptions were granted and
    which single worktree root is writable.

    Returns a dict of shape::

        {
          "version": 1,
          "requirement": "REQ-17.4",
          "egress": {
            "default": "deny",            # egress DENIED by default
            "allowlist": [<host>, ...],   # explicit, audited exceptions
          },
          "filesystem": {
            "default": "confine",         # writes confined to the worktree
            "writable_root": <abs worktree root or None>,
            "host_fs": "read-only",       # rest of host FS read-only/absent
          },
        }

    ``allowed_hosts`` is normalized to a de-duplicated, sorted list of lowercase
    hosts (empty/non-string entries dropped); an empty/``None`` value yields an
    empty allowlist — i.e. pure default-deny with no exceptions. ``worktree_root``
    is resolved to an absolute real path so the confinement check operates on a
    canonical anchor; a falsy/non-string root yields ``None`` ("no writable
    root" → everything is denied by `check_worktree_confinement`, preserving
    default-confine).
    """
    if allowed_hosts:
        hosts = sorted(
            {
                h.rstrip(".").lower()
                for h in allowed_hosts
                if isinstance(h, str) and h.strip()
            }
        )
    else:
        hosts = []

    if worktree_root and isinstance(worktree_root, str):
        writable_root = os.path.realpath(worktree_root)
    else:
        writable_root = None

    return {
        "version": 1,
        "requirement": "REQ-17.4",
        "egress": {
            "default": "deny",
            "allowlist": hosts,
        },
        "filesystem": {
            "default": "confine",
            "writable_root": writable_root,
            "host_fs": "read-only",
        },
    }

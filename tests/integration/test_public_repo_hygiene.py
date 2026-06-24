"""Post-public-repo hygiene oracle (Task 17): clean-by-absence over TRACKED files.

Acceptance oracle (spec §17): "no real secret AND no over-broad mask AND no live infra
fingerprint" in the committed tree. NOTE: this test must NOT embed the sensitive literals
themselves (that would re-introduce the fingerprint into a tracked file) — so it checks the
REDACTION landed (secrets.* references, no raw public-IP literals) rather than grepping for
the redacted value. gitleaks is skip-guarded; CI installs it.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _tracked() -> set[str]:
    return set(subprocess.run(["git", "ls-files"], cwd=ROOT,
                              capture_output=True, text=True).stdout.split())


@pytest.mark.skipif(shutil.which("gitleaks") is None,
                    reason="gitleaks not installed; the diff-scan gate runs in CI (secrets-scan.yml)")
def test_gitleaks_clean_on_tracked_files():
    """gitleaks must find 0 secrets in TRACKED files. (--no-git scans the working tree incl.
    untracked build artifacts like apps/web/.next/**, which are gitignored and not committed;
    those are filtered out — only a TRACKED finding is a real hygiene failure.)"""
    with tempfile.TemporaryDirectory() as td:
        report = Path(td) / "gl.json"
        subprocess.run(
            ["gitleaks", "detect", "--no-git", "--report-format", "json",
             "--report-path", str(report)],
            cwd=ROOT, capture_output=True, text=True)
        findings = json.loads(report.read_text()) if report.exists() else []
    tracked = _tracked()

    def _rel(f):
        p = f.get("File", "")
        return p.split("agentic-sdlc-optimization/")[-1] if "agentic-sdlc-optimization/" in p else p

    tracked_findings = [_rel(f) for f in findings if _rel(f) in tracked]
    assert tracked_findings == [], f"gitleaks found secrets in TRACKED files: {tracked_findings}"


def test_vm_host_redaction_landed():
    """The VM origin IP was redacted to secrets.VM_HOST — confirm the deploy workflows
    reference the secret (the redaction landed), without embedding the IP here."""
    refs = subprocess.run(["git", "grep", "-l", "secrets.VM_HOST", "--", ".github/workflows/"],
                          cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert refs, "expected deploy workflows to reference secrets.VM_HOST"


def test_no_raw_public_ipv4_literal_in_workflows():
    """No raw public-IPv4 literal in any workflow (infra fingerprints are redacted to secrets)."""
    ipv4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    offenders = []
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        for ln in wf.read_text().splitlines():
            for m in ipv4.findall(ln):
                octs = [int(o) for o in m.split(".")]
                # ignore private/loopback/version-like and netmask 0.0.0.0
                if octs[0] in (0, 10, 127) or (octs[0] == 192 and octs[1] == 168) \
                        or (octs[0] == 172 and 16 <= octs[1] <= 31) or all(o <= 9 for o in octs):
                    continue
                offenders.append(f"{wf.name}: {m}")
    assert not offenders, f"raw public IPv4 literal(s) in workflows (should be a secret): {offenders}"


def test_gitleaks_config_not_over_broad():
    """The 'no over-broad mask' clause of the oracle: PR #31 removed the blanket
    `(^|/)docs/.*\\.md$` path allowlist (which hid EVERY tracked doc line from the scanner)
    and switched to precise value-matching (`regexTarget = "match"`). Assert neither has
    regressed — an over-broad mask is as dangerous as a leaked secret (it hides future ones)."""
    toml = (ROOT / ".gitleaks.toml").read_text()
    active = [ln for ln in toml.splitlines() if not ln.lstrip().startswith("#")]
    assert not any(re.search(r"docs/\.\*\\?\.md", ln) for ln in active), \
        "over-broad docs/*.md gitleaks path allowlist re-introduced (hides every doc line)"
    assert 'regexTarget = "match"' in toml, "precise value-match allowlisting must be in place"


def test_checklist_doc_present_and_flags_owner_actions():
    """The checklist doc exists and names the two outstanding OWNER actions (not autonomously
    resolvable): OCI ingress lock + the a411f976 SECRET_KEY confirmation."""
    doc = (ROOT / "docs" / "github-public-repo-checklist.md").read_text().lower()
    assert "owner action" in doc
    assert "oci" in doc and "cloudflare" in doc           # ingress lock
    assert "secret_key" in doc or "a411f976" in doc        # the doc-sample SECRET_KEY confirmation

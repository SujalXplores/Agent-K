"""Automated evidence-link checker (LAW1-05, code half).

check_links(urls) issues an HTTP request per URL and reports whether it resolves
(2xx/3xx). This is the reusable function a future Phase-7 eval harness is expected
to call across every claim's evidence link produced during an evaluation run.
Confirming 100% actually resolve requires a live SigNoz instance - that live run is
this requirement's human-verification half (paired with the MCP-01/LAW1-04
live-verification gaps already flagged in Phases 4/5). The checker itself is fully
offline-testable (tests/test_check_evidence_links.py uses an httpx MockTransport,
no real network access).

CLI usage:
  python scripts/check_evidence_links.py <url> [<url> ...]
  python scripts/check_evidence_links.py --investigations
    (checks every evidence link across every currently in-process investigation -
    only meaningful when imported into the same process that ran them, e.g. a
    future Phase-7 eval harness; running this file as a fresh subprocess starts
    with an empty investigation store.)
"""

from __future__ import annotations

import sys

import httpx


def check_links(urls: list[str], timeout: float = 5.0) -> list[dict]:
    """One result dict per URL: link, resolved (2xx/3xx), status, error."""
    results = []
    with httpx.Client(timeout=timeout) as client:
        for url in urls:
            try:
                response = client.get(url)
                results.append(
                    {
                        "link": url,
                        "resolved": 200 <= response.status_code < 400,
                        "status": response.status_code,
                        "error": None,
                    }
                )
            except httpx.HTTPError as exc:
                results.append({"link": url, "resolved": False, "status": None, "error": str(exc)})
    return results


def collect_links_from_investigations() -> list[str]:
    """Every evidence link across every claim of every in-process investigation."""
    from app.investigation import list_investigations

    return [
        evidence.link
        for inv in list_investigations()
        for claim in inv.claims
        for evidence in claim.evidence
    ]


def main(urls: list[str]) -> int:
    results = check_links(urls)
    resolved = sum(1 for r in results if r["resolved"])
    for r in results:
        status = "OK" if r["resolved"] else "FAIL"
        print(f"[{status}] {r['link']} (status={r['status']}, error={r['error']})")
    total = len(results)
    pct = (resolved / total * 100) if total else 0
    print(f"\n{resolved}/{total} links resolved ({pct:.0f}%)")
    return 0 if resolved == total else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/check_evidence_links.py <url> [<url> ...]", file=sys.stderr)
        print("       python scripts/check_evidence_links.py --investigations", file=sys.stderr)
        sys.exit(1)
    link_args = collect_links_from_investigations() if sys.argv[1] == "--investigations" else sys.argv[1:]
    sys.exit(main(link_args))

"""
Script: report_to_jira.py
Purpose: Reads Playwright JSON test results and posts a structured comment to Jira.

In a real-world setup this script POSTs to:
    POST /rest/api/3/issue/{issueKey}/comment  (Jira REST API)
or uses a test management plugin API (Xray, Zephyr) to create/update test executions.

Dry-runs (prints only) when Jira credentials are not set.

Usage:
    python agentic-ai/report_to_jira.py
    JIRA_ISSUE_KEY=LOGIN-123 python agentic-ai/report_to_jira.py

Required .env vars (for real Jira): JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
Optional:                           JIRA_ISSUE_KEY (default: SCRUM-1)
                                    RESULTS_FILE   (default: tests/ai-generated/test-results/generated-login.json)
"""

import base64
import json
import os
import ssl
import sys
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ROOT         = Path(__file__).parent.parent
RESULTS_FILE = Path(os.getenv("RESULTS_FILE", str(ROOT / "tests/ai-generated/test-results/generated-login.json")))
JIRA_KEY     = os.getenv("JIRA_ISSUE_KEY", "SCRUM-1")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def collect_tests(suites: list) -> list:
    """Flatten the Playwright JSON suite tree into a list of test result dicts."""
    results = []
    for suite in suites:
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                r = test.get("results", [{}])[0]
                results.append({
                    "title":    spec.get("title", ""),
                    "status":   r.get("status", "unknown"),
                    "duration": r.get("duration", 0),
                    "error":    r.get("error", {}).get("message") if r.get("error") else None,
                })
        results.extend(collect_tests(suite.get("suites", [])))
    return results


def collect_screenshots(suites: list) -> list:
    """Collect screenshot file paths from Playwright JSON suite attachments."""
    paths = []
    for suite in suites:
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                for result in test.get("results", []):
                    for att in result.get("attachments", []):
                        if att.get("contentType") == "image/png" and att.get("path"):
                            p = Path(att["path"])
                            if p.exists():
                                paths.append(p)
        paths.extend(collect_screenshots(suite.get("suites", [])))
    return paths


def upload_attachments(paths: list) -> None:
    jira_url   = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    jira_email = os.getenv("JIRA_EMAIL", "")
    jira_token = os.getenv("JIRA_API_TOKEN", "")

    if not all([jira_url, jira_email, jira_token]):
        print(f"No Jira credentials — skipping screenshot upload ({len(paths)} file(s)).")
        return

    auth = base64.b64encode(f"{jira_email}:{jira_token}".encode()).decode()
    url  = f"{jira_url}/rest/api/3/issue/{JIRA_KEY}/attachments"
    ctx  = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE

    for path in paths:
        boundary = uuid.uuid4().hex
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization":     f"Basic {auth}",
                "X-Atlassian-Token": "no-check",
                "Content-Type":      f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                resp.read()
            print(f"📎 Uploaded screenshot: {path.name}")
        except urllib.error.HTTPError as exc:
            print(f"⚠️  Screenshot upload failed: {exc.code} {exc.reason}", file=sys.stderr)


def build_comment(stats: dict, tests: list) -> str:
    passed  = sum(1 for t in tests if t["status"] == "passed")
    failed  = sum(1 for t in tests if t["status"] != "passed")
    overall = "✅ PASSED" if failed == 0 else "❌ FAILED"

    start = stats.get("startTime", 0)
    if isinstance(start, str):
        run_date = start[:19].replace("T", " ") + " UTC"
    else:
        run_date = datetime.fromtimestamp(
            start / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = []
    for t in tests:
        icon = "✅" if t["status"] == "passed" else "❌"
        err  = f"\n      Error: {t['error'].splitlines()[0]}" if t["error"] else ""
        lines.append(f"  {icon} {t['title']} ({t['duration']}ms){err}")

    return (
        f"🤖 *Agentic AI Test Report* — {JIRA_KEY}\n\n"
        f"*Overall:* {overall}\n"
        f"*Run Date:* {run_date}\n"
        f"*Duration:* {stats.get('duration', 0) / 1000:.2f}s\n"
        f"*Tests:* {passed} passed, {failed} failed\n\n"
        f"*Results:*\n"
        + "\n".join(lines)
        + "\n\n_Generated automatically by the agentic CI workflow._"
    )


def post_to_jira(comment_body: str) -> None:
    jira_url   = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    jira_email = os.getenv("JIRA_EMAIL", "")
    jira_token = os.getenv("JIRA_API_TOKEN", "")

    if not all([jira_url, jira_email, jira_token]):
        print("No Jira credentials set — skipping API call (dry run only).")
        return

    auth    = base64.b64encode(f"{jira_email}:{jira_token}".encode()).decode()
    url     = f"{jira_url}/rest/api/3/issue/{JIRA_KEY}/comment"
    payload = json.dumps({
        "body": {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment_body}]}],
        }
    }).encode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())
        print(f"✅ Comment posted to Jira {JIRA_KEY}: id={data.get('id')}")
    except urllib.error.HTTPError as exc:
        print(f"❌ Jira API error: {exc.code} {exc.reason}", file=sys.stderr)
        sys.exit(1)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not RESULTS_FILE.exists():
        print(f"❌ Results file not found: {RESULTS_FILE}", file=sys.stderr)
        sys.exit(1)

    data   = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    stats  = data.get("stats", {})
    suites = data.get("suites", [])
    tests  = collect_tests(suites)

    comment_body = build_comment(stats, tests)

    print("\n─── Jira Comment (Dry Run) ─────────────────────────────────────────────\n")
    print(comment_body)
    print("\n────────────────────────────────────────────────────────────────────────\n")

    post_to_jira(comment_body)

    screenshots = collect_screenshots(suites)
    print(f"📸 Screenshots found: {len(screenshots)}")
    if screenshots:
        upload_attachments(screenshots)


if __name__ == "__main__":
    main()

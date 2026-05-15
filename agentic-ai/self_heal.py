"""
Script: self_heal.py
Purpose: Agentic self-healing loop.

Flow:
  1. Run the generated Playwright test
  2. If it passes → nothing to heal, report results
  3. If it fails → launch a headless browser, navigate to the page,
     inspect the DOM for flash/alert elements, find the correct selector
  4. Patch the test file with the healed selector
  5. Re-run the tests to confirm the fix
  6. Post the full report (failure + fix + passing results) to Jira

Usage:
    python agentic-ai/self_heal.py

Required .env vars (for Jira reporting): JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
Optional:                                JIRA_ISSUE_KEY (default: SCRUM-1)
"""

import asyncio
import base64
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ROOT      = Path(__file__).parent.parent
JIRA_KEY  = (
    sys.argv[1] if len(sys.argv) > 1
    else os.getenv("STORY_KEY", os.getenv("JIRA_ISSUE_KEY", "SCRUM-1"))
).strip().upper()
TEST_FILE    = ROOT / "tests" / "ai-generated" / f"{JIRA_KEY}.spec.ts"
RESULTS_FILE = ROOT / "tests" / "ai-generated" / "test-results" / f"{JIRA_KEY}-results.json"


# ─── Logging ─────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"\n[self-heal] {msg}")


# ─── Test Runner ──────────────────────────────────────────────────────────────

def run_tests() -> bool:
    """Run the generated Playwright spec. Returns True if all tests pass."""
    log("Running Playwright tests...")
    result = subprocess.run(
        ["npx", "playwright", "test",
         str(TEST_FILE.relative_to(ROOT)),
         "--reporter=json"],
        cwd=ROOT,
        env={**os.environ,
             "PLAYWRIGHT_JSON_OUTPUT_NAME": str(RESULTS_FILE)},
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def read_results() -> dict:
    return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))


# ─── Failure Inspector ────────────────────────────────────────────────────────

def find_failure(suites: list) -> dict | None:
    """Walk the Playwright JSON suite tree and return the first failed test."""
    for suite in suites:
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                r = test.get("results", [{}])[0]
                if r.get("status") == "failed":
                    return {
                        "title": spec.get("title", ""),
                        "error": r.get("error", {}).get("message", ""),
                    }
        nested = find_failure(suite.get("suites", []))
        if nested:
            return nested
    return None


def extract_broken_selector(error_msg: str, test_source: str) -> str | None:
    """Extract the broken selector from the Playwright error message or the test file."""
    # Playwright errors include:  locator('...')
    m = re.search(r"locator\(['\"]([^'\"]+)['\"]\)", error_msg)
    if m:
        return m.group(1)
    # Fallback: first locator() call in the test file
    m = re.search(r"locator\(['\"]([^'\"]+)['\"]\)", test_source)
    return m.group(1) if m else None


# ─── DOM Inspector ────────────────────────────────────────────────────────────

async def find_correct_selector() -> str | None:
    """
    Launch a headless Playwright browser, perform a login, then inspect the DOM
    for any flash/alert elements and return the best CSS selector.
    """
    from playwright.async_api import async_playwright

    log("Launching headless browser to inspect live DOM...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page()

        await page.goto("https://the-internet.herokuapp.com/login")
        await page.fill("#username", "tomsmith")
        await page.fill("#password", "SuperSecretPassword!")
        await page.click("button[type=submit]")
        await page.wait_for_load_state("domcontentloaded")

        candidates = await page.evaluate("""() => {
            const els = document.querySelectorAll('[class*="flash"], [id*="flash"], [class*="alert"]');
            return Array.from(els).map(el => ({
                tag:     el.tagName.toLowerCase(),
                id:      el.id,
                classes: Array.from(el.classList),
                text:    (el.textContent || '').trim().slice(0, 80),
            }));
        }""")

        await browser.close()

    log(f"DOM candidates found:\n{json.dumps(candidates, indent=2)}")

    # Priority 1: class exactly named "success"
    for c in candidates:
        if "success" in [cls.lower() for cls in c["classes"]]:
            return "." + ".".join(c["classes"])

    # Priority 2: class containing "success" as substring
    for c in candidates:
        if any("success" in cls.lower() for cls in c["classes"]):
            return "." + ".".join(c["classes"])

    # Priority 3: text signals successful login
    for c in candidates:
        text_lower = c["text"].lower()
        if "secure area" in text_lower or "logged in" in text_lower:
            if c["classes"]:
                return "." + ".".join(c["classes"])
            if c["id"]:
                return f"#{c['id']}"

    # Fallback: first candidate
    if candidates and candidates[0]["classes"]:
        return "." + ".".join(candidates[0]["classes"])

    return None


# ─── File Patcher ─────────────────────────────────────────────────────────────

def patch_test_file(broken: str, healed: str) -> bool:
    log(f'Patching test file: "{broken}" → "{healed}"')
    source  = TEST_FILE.read_text(encoding="utf-8")
    updated = source.replace(broken, healed)
    if source == updated:
        log("WARNING: selector not found in file — patch skipped.")
        return False
    TEST_FILE.write_text(updated, encoding="utf-8")
    log("File patched successfully.")
    return True


# ─── Jira Reporter ────────────────────────────────────────────────────────────

def post_to_jira(comment_body: str) -> None:
    jira_url   = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    jira_email = os.getenv("JIRA_EMAIL", "")
    jira_token = os.getenv("JIRA_API_TOKEN", "")

    if not all([jira_url, jira_email, jira_token]):
        log("No Jira credentials set — skipping post.")
        return

    auth    = base64.b64encode(f"{jira_email}:{jira_token}".encode()).decode()
    url     = f"{jira_url}/rest/api/3/issue/{JIRA_KEY}/comment"
    payload = json.dumps({
        "body": {
            "type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment_body}]}],
        }
    }).encode()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        url, data=payload,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())
        log(f"✅ Jira comment posted to {JIRA_KEY}: id={data.get('id')}")
    except urllib.error.HTTPError as exc:
        log(f"❌ Jira post failed: {exc.code} {exc.reason}")


# ─── Main Agentic Loop ────────────────────────────────────────────────────────

async def main() -> None:
    # ── Round 1: initial run ──
    first_run_passed = run_tests()

    if first_run_passed:
        log("All tests passed on first run — nothing to heal. 🎉")
        post_to_jira(
            f"🤖 Agentic AI — {JIRA_KEY}\n\n"
            "✅ All tests passed on first run. No self-healing required."
        )
        return

    # ── Failure detected ──
    results1  = read_results()
    failure   = find_failure(results1.get("suites", []))
    log(f"Failure detected in: \"{failure['title']}\"")
    log(f"Error: {failure['error'].splitlines()[0]}")

    test_source     = TEST_FILE.read_text(encoding="utf-8")
    broken_selector = extract_broken_selector(failure["error"], test_source)
    log(f"Broken selector identified: \"{broken_selector}\"")

    if not broken_selector:
        log("Could not identify broken selector — manual intervention needed.")
        sys.exit(1)

    # ── DOM inspection → find correct selector ──
    healed_selector = await find_correct_selector()
    if not healed_selector:
        log("DOM inspection found no matching element — manual intervention needed.")
        sys.exit(1)
    log(f"Healed selector: \"{healed_selector}\"")

    # ── Patch the file ──
    if not patch_test_file(broken_selector, healed_selector):
        sys.exit(1)

    # ── Round 2: rerun after fix ──
    log("Re-running tests after patch...")
    second_run_passed = run_tests()
    results2          = read_results()

    def collect_tests(suites: list) -> list:
        out = []
        for suite in suites:
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    r = test.get("results", [{}])[0]
                    out.append({
                        "title":    spec.get("title", ""),
                        "status":   r.get("status", "unknown"),
                        "duration": r.get("duration", 0),
                    })
            out.extend(collect_tests(suite.get("suites", [])))
        return out

    tests      = collect_tests(results2.get("suites", []))
    test_lines = "\n".join(
        f"  {'✅' if t['status'] == 'passed' else '❌'} {t['title']} ({t['duration']}ms)"
        for t in tests
    )

    comment_body = (
        f"🤖 *Agentic Self-Healing Report* — {JIRA_KEY}\n\n"
        f"*Broken selector detected:* `{broken_selector}`\n"
        f"*Healed selector applied:*  `{healed_selector}`\n"
        f"*Second run result:* {'✅ ALL PASSED' if second_run_passed else '❌ STILL FAILING'}\n\n"
        f"*Test Results after fix:*\n{test_lines}\n\n"
        "_Self-healed automatically by the agentic CI workflow._"
    )

    print("\n─── Self-Heal Report ───────────────────────────────────────────────────\n")
    print(comment_body)
    print("\n────────────────────────────────────────────────────────────────────────\n")

    post_to_jira(comment_body)

    if not second_run_passed:
        log("Tests still failing after patch — review manually.")
        sys.exit(1)

    log("Self-healing complete. Tests green. Jira updated. ✅")


if __name__ == "__main__":
    asyncio.run(main())

"""
Script: smart_heal.py
Chapter 11 — LLM-powered Smart Self-Healing

Unlike Chapter 10's self_heal.py which used hardcoded DOM logic to find selectors,
this script sends the Playwright error + the live DOM HTML to an LLM (Claude or OpenAI)
and asks IT to reason about the fix. The LLM produces a precise patch diff.

Flow:
  1. Run the Playwright spec — if it passes, nothing to do
  2. Extract the failure: error message + broken selector + file location
  3. Launch headless browser, navigate to the failing URL, capture the live DOM HTML
  4. Send error + DOM to Claude/OpenAI with a structured fix prompt
  5. Apply the LLM-proposed patch to the test file
  6. Re-run to confirm the fix passes
  7. Post a detailed comment to Jira (failure + LLM reasoning + fix + pass confirmation)
  8. If a new failure appears after healing, auto-create a Jira Bug ticket

Usage:
    python agentic-ai/smart_heal.py SCRUM-1
    STORY_KEY=SCRUM-1 python agentic-ai/smart_heal.py

Required (at least one LLM key):
    ANTHROPIC_API_KEY   sk-ant-...
    OPENAI_API_KEY      sk-...

Optional:
    JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN   — for real Jira posting
    JIRA_PROJECT_KEY                               — for auto bug creation
    APP_URL                                        — default: https://the-internet.herokuapp.com
"""

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))
from jira_client import create_bug, post_comment  # noqa: E402

ROOT     = Path(__file__).parent.parent
APP_URL  = os.getenv("APP_URL", "https://the-internet.herokuapp.com")
JIRA_KEY = (
    sys.argv[1] if len(sys.argv) > 1
    else os.getenv("STORY_KEY", os.getenv("JIRA_ISSUE_KEY", "SCRUM-1"))
).strip().upper()

TEST_FILE    = ROOT / "tests" / "ai-generated" / f"{JIRA_KEY}.spec.ts"
RESULTS_FILE = ROOT / "tests" / "ai-generated" / "test-results" / f"{JIRA_KEY}-results.json"


# ─── Logging ─────────────────────────────────────────────────────────────────

def log(msg: str)  -> None: print(f"\n[smart-heal] {msg}")
def ok(msg: str)   -> None: print(f"\n[smart-heal] ✅ {msg}")
def fail(msg: str) -> None: print(f"\n[smart-heal] ❌ {msg}", file=sys.stderr)


# ─── Test runner ──────────────────────────────────────────────────────────────

def _pw_cmd() -> list[str]:
    """Use node cli.js directly — avoids npx hanging on paths with spaces (Google Drive)."""
    cli = ROOT / "node_modules" / "@playwright" / "test" / "cli.js"
    return ["node", str(cli)] if cli.exists() else ["npx", "playwright"]


def run_tests() -> bool:
    """Run the Playwright spec. Returns True if all tests pass."""
    log(f"Running: {TEST_FILE.relative_to(ROOT)}")
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        _pw_cmd() + ["test", str(TEST_FILE.relative_to(ROOT)), "--reporter=json"],
        cwd=ROOT,
        env={**os.environ, "PLAYWRIGHT_JSON_OUTPUT_NAME": str(RESULTS_FILE)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode == 0


def read_results() -> dict:
    return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))


# ─── Failure extraction ───────────────────────────────────────────────────────

def _walk_suites(suites: list) -> list[dict]:
    """Flatten Playwright JSON suite tree into a list of test result dicts."""
    out = []
    for suite in suites:
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                r = (test.get("results") or [{}])[0]
                out.append({
                    "title":  spec.get("title", ""),
                    "file":   spec.get("file", ""),
                    "status": r.get("status", "unknown"),
                    "error":  (r.get("error") or {}).get("message", ""),
                    "duration": r.get("duration", 0),
                })
        out.extend(_walk_suites(suite.get("suites", [])))
    return out


def find_first_failure(results: dict) -> dict | None:
    tests = _walk_suites(results.get("suites", []))
    for t in tests:
        if t["status"] == "failed":
            return t
    return None


def extract_broken_selector(error_msg: str, source: str) -> str | None:
    """Pull the broken selector from the Playwright error or test source."""
    # Playwright error message often includes: locator('...')
    m = re.search(r"locator\(['\"]([^'\"]+)['\"]\)", error_msg)
    if m:
        return m.group(1)
    m = re.search(r"locator\(['\"]([^'\"]+)['\"]\)", source)
    return m.group(1) if m else None


def extract_failing_url(source: str) -> str:
    """Find the first page.goto() URL in the test source."""
    m = re.search(r"page\.goto\(['\"]([^'\"]+)['\"]\)", source)
    if m:
        url = m.group(1)
        # If it's a relative path, prepend APP_URL
        if url.startswith("/"):
            return APP_URL.rstrip("/") + url
        return url
    return APP_URL + "/login"


# ─── Live DOM capture ─────────────────────────────────────────────────────────

async def _capture_dom(url: str) -> str:
    """
    Navigate to the URL in a headless Chromium browser, perform login if the URL
    is a login page, then return the full body innerHTML.
    """
    from playwright.async_api import async_playwright

    log(f"Capturing live DOM from: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")

        # Auto-login if we landed on a login form
        if await page.locator("#username").count() > 0:
            await page.fill("#username", "tomsmith")
            await page.fill("#password", "SuperSecretPassword!")
            await page.click("button[type=submit]")
            await page.wait_for_load_state("domcontentloaded")

        html = await page.evaluate("() => document.body.innerHTML")
        await browser.close()

    # Trim to keep token count reasonable (~8k chars)
    return html[:8000]


def capture_dom(url: str) -> str:
    return asyncio.run(_capture_dom(url))


# ─── LLM fix prompt ───────────────────────────────────────────────────────────

def _build_fix_prompt(error_msg: str, broken_selector: str | None, dom_html: str, source: str) -> str:
    selector_hint = f'The broken selector appears to be: "{broken_selector}"' if broken_selector else ""
    return f"""\
A Playwright TypeScript test is failing. Your job is to identify the correct fix
and return it as a structured JSON object.

## Playwright Error
```
{error_msg[:1500]}
```

{selector_hint}

## Test Source (failing file)
```typescript
{source[:3000]}
```

## Live DOM HTML (captured from the app after login)
```html
{dom_html[:5000]}
```

## Instructions
1. Analyse the error and the DOM to find the correct CSS selector or assertion.
2. Identify the EXACT string in the test source that must be changed.
3. Return ONLY a valid JSON object in this exact shape:
{{
  "reasoning": "<1-3 sentence explanation of why the test failed and what the fix is>",
  "broken":    "<the exact string to find in the test source>",
  "fixed":     "<the replacement string>",
  "confidence": "high" | "medium" | "low"
}}

No prose outside the JSON. No markdown fences.
"""


def _call_claude(prompt: str) -> dict:
    try:
        import anthropic
    except ImportError:
        raise ImportError("Run: pip install anthropic")

    model  = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    log(f"Asking Claude ({model}) to diagnose the failure...")
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg    = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0,
        system="You are an expert Playwright debugger. Respond only with the JSON object requested.",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def _call_openai(prompt: str) -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Run: pip install openai")

    model  = os.getenv("OPENAI_MODEL", "gpt-4o")
    log(f"Asking OpenAI ({model}) to diagnose the failure...")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp   = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are an expert Playwright debugger. Respond only with the JSON object requested."},
            {"role": "user",   "content": prompt},
        ],
    )
    return json.loads(resp.choices[0].message.content)


def ask_llm_for_fix(error_msg: str, broken_selector: str | None, dom_html: str, source: str) -> dict:
    """Call Claude (preferred) or OpenAI and return the structured fix dict."""
    prompt = _build_fix_prompt(error_msg, broken_selector, dom_html, source)

    if os.getenv("ANTHROPIC_API_KEY"):
        return _call_claude(prompt)
    if os.getenv("OPENAI_API_KEY"):
        return _call_openai(prompt)

    raise EnvironmentError(
        "No LLM key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env"
    )


# ─── Patch applier ────────────────────────────────────────────────────────────

def apply_patch(fix: dict) -> bool:
    """Apply the LLM-proposed fix to the test file. Returns True if patched."""
    broken = fix.get("broken", "")
    fixed  = fix.get("fixed", "")

    if not broken or not fixed or broken == fixed:
        log("LLM returned no actionable patch.")
        return False

    source  = TEST_FILE.read_text(encoding="utf-8")
    updated = source.replace(broken, fixed, 1)

    if source == updated:
        fail(f'Could not find "{broken}" in test file — patch skipped.')
        return False

    TEST_FILE.write_text(updated, encoding="utf-8")
    log(f'Patched: "{broken}"  →  "{fixed}"')
    return True


# ─── Jira reporting ───────────────────────────────────────────────────────────

def post_heal_report(failure: dict, fix: dict, healed: bool, post_run_passed: bool) -> None:
    status_line = "✅ HEALED — post-fix run passed." if (healed and post_run_passed) else (
        "⚠️ PATCH APPLIED — post-fix run still failing." if healed else
        "❌ COULD NOT HEAL — no patch was applied."
    )

    comment = (
        f"🤖 Smart Self-Heal Report — {JIRA_KEY}\n\n"
        f"Status: {status_line}\n\n"
        f"Failing test: {failure['title']}\n"
        f"Error: {failure['error'][:300]}\n\n"
        f"LLM Reasoning:\n{fix.get('reasoning', 'N/A')}\n\n"
        f"Fix applied:\n"
        f"  Before: {fix.get('broken', 'N/A')}\n"
        f"  After:  {fix.get('fixed',  'N/A')}\n"
        f"Confidence: {fix.get('confidence', 'N/A')}\n\n"
        f"Generated automatically by smart_heal.py"
    )
    post_comment(JIRA_KEY, comment)


def create_bug_if_needed(failure: dict, fix: dict) -> None:
    """Auto-create a Jira Bug when healing fails or confidence is low."""
    project = os.getenv("JIRA_PROJECT_KEY", "").strip()
    if not project:
        log("JIRA_PROJECT_KEY not set — skipping auto bug creation.")
        return

    confidence = fix.get("confidence", "high")
    if confidence == "high":
        return  # Don't create a bug if LLM is confident and fix was applied

    summary = f"[Auto] Smart-heal LOW confidence fix — {JIRA_KEY}: {failure['title'][:60]}"
    description = (
        f"The smart self-heal agent attempted to fix a failing test but had low confidence.\n\n"
        f"Story: {JIRA_KEY}\n"
        f"Failing test: {failure['title']}\n"
        f"Error:\n{failure['error'][:500]}\n\n"
        f"LLM Reasoning:\n{fix.get('reasoning', 'N/A')}\n\n"
        f"Proposed fix:\n"
        f"  Before: {fix.get('broken', 'N/A')}\n"
        f"  After:  {fix.get('fixed',  'N/A')}\n\n"
        f"Manual review required."
    )
    create_bug(
        summary=summary,
        description=description,
        parent_key=JIRA_KEY,
        labels=["auto-generated", "smart-heal", "needs-review"],
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TEST_FILE.exists():
        fail(f"Test file not found: {TEST_FILE.relative_to(ROOT)}")
        fail("Run automate_story.py first to generate the test.")
        sys.exit(1)

    log(f"Starting smart self-heal for {JIRA_KEY}")
    log(f"Test file: {TEST_FILE.relative_to(ROOT)}")

    # ── Round 1: initial test run ─────────────────────────────────────────────
    passed = run_tests()
    if passed:
        ok("All tests already passing — nothing to heal.")
        sys.exit(0)

    log("Tests failed — starting LLM-powered diagnosis...")

    results  = read_results()
    failure  = find_first_failure(results)

    if not failure:
        fail("Could not find failure details in JSON results.")
        sys.exit(1)

    log(f"Failing test: \"{failure['title']}\"")
    log(f"Error: {failure['error'][:200]}")

    source          = TEST_FILE.read_text(encoding="utf-8")
    broken_selector = extract_broken_selector(failure["error"], source)
    failing_url     = extract_failing_url(source)

    # ── Capture live DOM ──────────────────────────────────────────────────────
    try:
        dom_html = capture_dom(failing_url)
        log(f"DOM captured ({len(dom_html)} chars)")
    except Exception as exc:
        log(f"DOM capture failed ({exc}) — proceeding with error-only context")
        dom_html = "<dom capture failed>"

    # ── Ask LLM for fix ───────────────────────────────────────────────────────
    try:
        fix = ask_llm_for_fix(failure["error"], broken_selector, dom_html, source)
        log(f"LLM reasoning: {fix.get('reasoning', '')}")
        log(f"Confidence: {fix.get('confidence', 'unknown')}")
    except Exception as exc:
        fail(f"LLM call failed: {exc}")
        fix = {"reasoning": str(exc), "broken": "", "fixed": "", "confidence": "low"}

    # ── Apply patch ───────────────────────────────────────────────────────────
    healed = apply_patch(fix)

    # ── Round 2: re-run after patch ───────────────────────────────────────────
    post_run_passed = False
    if healed:
        log("Re-running tests after patch...")
        post_run_passed = run_tests()
        if post_run_passed:
            ok("Post-fix run PASSED ✅")
        else:
            fail("Post-fix run still failing ❌")

    # ── Jira reporting ────────────────────────────────────────────────────────
    post_heal_report(failure, fix, healed, post_run_passed)

    # ── Auto-create bug if confidence is low ──────────────────────────────────
    create_bug_if_needed(failure, fix)

    if healed and post_run_passed:
        ok(f"Smart self-heal complete for {JIRA_KEY}")
        sys.exit(0)
    else:
        fail(f"Smart self-heal could not fully resolve the failure for {JIRA_KEY}")
        sys.exit(1)


if __name__ == "__main__":
    main()

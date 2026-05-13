"""
Script: mcp_server.py
Purpose: Step 7 (Python) — MCP server exposing all agentic tools to VS Code Copilot agent mode.

Tools exposed:
  fetch_jira_story        — read a Jira story from local mock JSON or the real Jira REST API
  generate_test_from_story — generate a Playwright test from the story's acceptance criteria (template)
  automate_jira_story     — full pipeline: fetch story → LLM → write test (requires OPENAI_API_KEY)
  run_playwright_tests    — run a Playwright spec file and return a pass/fail summary
  self_heal               — detect broken selector, inspect DOM, patch test, rerun, report to Jira
  report_to_jira          — post test-result comment to a Jira issue

VS Code discovers this server via .vscode/mcp.json.
Run manually: python agentic-ai/mcp_server.py
"""

import base64
import json
import os
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).parent.parent / ".env")

ROOT = Path(__file__).parent.parent
mcp  = FastMCP("playwright-agentic")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _run_script(script_path: str, extra_env: dict | None = None, args: list | None = None) -> dict:
    """Run a Python script in the project root. Returns {ok, output}."""
    env = {**os.environ, **(extra_env or {})}
    result = subprocess.run(
        [sys.executable, script_path, *(args or [])],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    combined = (result.stdout + result.stderr).strip()
    return {
        "ok":     result.returncode == 0,
        "output": combined,
    }


def _run_playwright(spec_file: str, json_output_name: str) -> dict:
    """Run `npx playwright test` for a given spec. Returns {ok, stdout, stderr}."""
    result = subprocess.run(
        ["npx", "playwright", "test", spec_file, "--reporter=json"],
        cwd=ROOT,
        env={**os.environ, "PLAYWRIGHT_JSON_OUTPUT_NAME": json_output_name},
        capture_output=True,
        text=True,
    )
    return {
        "ok":     result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _summarise_playwright_results(json_output_path: str) -> str:
    results_path = ROOT / json_output_path
    if not results_path.exists():
        return "Could not find JSON results file."
    try:
        data   = json.loads(results_path.read_text(encoding="utf-8"))
        stats  = data.get("stats", {})
        total  = stats.get("expected", 0) + stats.get("unexpected", 0)
        passed = stats.get("expected", 0)
        failed = stats.get("unexpected", 0)
        duration = stats.get("duration", 0) / 1000
        return f"Results: {passed}/{total} passed, {failed} failed.\nDuration: {duration:.2f}s"
    except Exception:
        return "Could not parse JSON results."


# ─── Tool 1: fetch_jira_story ─────────────────────────────────────────────────

@mcp.tool()
def fetch_jira_story(story_key: str = "LOGIN-123") -> str:
    """
    Fetch a Jira user story and its acceptance criteria.
    Uses the local mock JSON first; reads from the real Jira REST API when
    JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN env vars are present.

    Args:
        story_key: Jira issue key, e.g. "LOGIN-123". Defaults to LOGIN-123.
    """
    local_path = Path(__file__).parent / "data" / f"jira-story.{story_key}.json"
    if local_path.exists():
        return local_path.read_text(encoding="utf-8")

    jira_url   = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    jira_email = os.getenv("JIRA_EMAIL", "")
    jira_token = os.getenv("JIRA_API_TOKEN", "")

    if not all([jira_url, jira_email, jira_token]):
        return (
            f"No local mock found for {story_key} and Jira credentials are not set.\n"
            "Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in your .env file."
        )

    import base64, urllib.request
    auth = base64.b64encode(f"{jira_email}:{jira_token}".encode()).decode()
    url  = f"{jira_url}/rest/api/3/issue/{story_key}"
    req  = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})

    try:
        import base64, urllib.request, ssl
        auth = base64.b64encode(f"{jira_email}:{jira_token}".encode()).decode()
        url  = f"{jira_url}/rest/api/3/issue/{story_key}"
        req  = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
        ctx  = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())
        return json.dumps(data, indent=2)
    except Exception as exc:
        return f"Jira API error: {exc}"


# ─── Tool 2: generate_test_from_story ────────────────────────────────────────

@mcp.tool()
def generate_test_from_story() -> str:
    """
    Generate a Playwright TypeScript test file from the Jira story's acceptance criteria
    using a hardcoded template. Runs generate_test.py.
    The first test intentionally uses a broken selector (.flash-success) for the self-heal demo.
    """
    r      = _run_script("agentic-ai/generate_test.py")
    if r["ok"]:
        return f"Test generated successfully.\n\n{r['output']}"
    return f"Generator failed.\n\n{r['output']}"


# ─── Tool 3: automate_jira_story ─────────────────────────────────────────────

@mcp.tool()
def automate_jira_story(story_key: str) -> str:
    """
    Full agentic pipeline: fetch a Jira story by key, call an LLM (OpenAI) to generate
    a Playwright TypeScript test from its Gherkin acceptance criteria, and write the test
    to tests/ai-generated/{storyKey}.spec.ts.

    Requires OPENAI_API_KEY in .env.
    Uses local mock JSON if agentic-ai/data/jira-story.{storyKey}.json exists.

    Args:
        story_key: Jira issue key to automate, e.g. "LOGIN-123" or "SCRUM-1".
    """
    r = _run_script("agentic-ai/automate_story.py", args=[story_key])
    if r["ok"]:
        return f"✅ Playwright test generated for {story_key}.\n\n{r['output']}"
    return f"❌ Automation failed for {story_key}.\n\n{r['output']}"


# ─── Tool 4: run_playwright_tests ────────────────────────────────────────────

@mcp.tool()
def run_playwright_tests(
    spec_file: str = "tests/ai-generated/generated-login.spec.ts"
) -> str:
    """
    Run a Playwright spec file and return a pass/fail summary with error details.

    Args:
        spec_file: Workspace-relative path to the spec file.
                   Defaults to tests/ai-generated/generated-login.spec.ts.
    """
    stem        = Path(spec_file).stem.replace(".spec", "")
    json_output = f"tests/ai-generated/test-results/{stem}-results.json"
    (ROOT / "tests" / "ai-generated" / "test-results").mkdir(parents=True, exist_ok=True)
    r           = _run_playwright(spec_file, json_output)
    summary     = _summarise_playwright_results(json_output)
    status      = "✅ All tests passed." if r["ok"] else "❌ Tests failed."
    raw         = r["stdout"] or r["stderr"]
    return f"{status}\n\n{summary}\n\nRaw output:\n{raw}"


# ─── Tool 5: full_pipeline ──────────────────────────────────────────────────

@mcp.tool()
def full_pipeline(story_key: str) -> str:
    """
    One-shot agentic pipeline — no prompts, no interaction:
      1. Fetch the Jira story and generate a Playwright test via GPT-4o
      2. Run the tests and capture JSON results
      3. Post a test report comment back to Jira

    Args:
        story_key: Jira issue key, e.g. "SCRUM-4".
    """
    r = _run_script("agentic-ai/pipeline.py", args=[story_key])
    if r["ok"]:
        return f"✅ Pipeline complete for {story_key}.\n\n{r['output']}"
    return f"❌ Pipeline failed for {story_key}.\n\n{r['output']}"


# ─── Tool 6: self_heal ────────────────────────────────────────────────────────

@mcp.tool()
def self_heal() -> str:
    """
    Run the self-healing agent:
      1. Run the generated Playwright test
      2. If failing — inspect the live DOM to find the correct selector
      3. Patch the test file
      4. Rerun to confirm the fix
      5. Post the report to Jira
    """
    r           = _run_script("agentic-ai/self_heal.py")
    if r["ok"]:
        return f"Self-heal completed successfully.\n\n{r['output']}"
    return f"Self-heal encountered an error.\n\n{r['output']}"


# ─── Tool 6: report_to_jira ───────────────────────────────────────────────────

@mcp.tool()
def report_to_jira(issue_key: str = "", results_file: str = "") -> str:
    """
    Read the latest Playwright JSON test results and post a structured comment to Jira.
    Dry-runs (prints only) when JIRA credentials are not set.

    Args:
        issue_key:    Jira issue key to comment on, e.g. "SCRUM-1".
        results_file: Path to the Playwright JSON results file.
                      Defaults to tests/ai-generated/test-results/{issue_key}-results.json.
    """
    if not results_file and issue_key:
        results_file = f"tests/ai-generated/test-results/{issue_key}-results.json"
    extra: dict = {}
    if issue_key:    extra["JIRA_ISSUE_KEY"] = issue_key
    if results_file: extra["RESULTS_FILE"]   = results_file
    r = _run_script("agentic-ai/report_to_jira.py", extra)
    if r["ok"]:
        return f"Jira report posted successfully.\n\n{r['output']}"
    return f"Jira reporter encountered an error.\n\n{r['output']}"


# ─── Start ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(
        "\n╔══════════════════════════════════════════════════════╗\n"
        "║  playwright-agentic MCP server  —  stdio transport   ║\n"
        "╚══════════════════════════════════════════════════════╝\n"
        "Tools: fetch_jira_story · generate_test_from_story · automate_jira_story\n"
        "       full_pipeline · run_playwright_tests · self_heal · report_to_jira\n"
        "Tip:   python agentic-ai/mcp_server.py\n",
        file=sys.stderr,
    )
    mcp.run()

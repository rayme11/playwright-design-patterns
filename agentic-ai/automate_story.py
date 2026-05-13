"""
Script: automate_story.py
Purpose: Steps 8+9 — Full agentic pipeline:
  1. Accept a Jira story key (CLI arg or STORY_KEY env var)
  2. Fetch the story from local mock JSON or the real Jira REST API
  3. Call OpenAI to generate a Playwright TypeScript test from the Gherkin acceptance criteria
  4. Write the test to tests/ai-generated/{storyKey}.spec.ts

Usage:
    python agentic-ai/automate_story.py LOGIN-123
    STORY_KEY=LOGIN-123 python agentic-ai/automate_story.py

Required .env vars for real Jira:   JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
Required .env vars for LLM:         OPENAI_API_KEY
Optional:                           OPENAI_MODEL (default: gpt-4o), APP_URL
"""

import json
import os
import re
import ssl
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

ROOT     = Path(__file__).parent.parent
APP_URL  = os.getenv("APP_URL", "https://the-internet.herokuapp.com")


# ─── Logging ────────────────────────────────────────────────────────────────

def log(msg: str)  -> None: print(f"[automate] {msg}")
def ok(msg: str)   -> None: print(f"[automate] ✅ {msg}")
def fail(msg: str) -> None: print(f"[automate] ❌ {msg}", file=sys.stderr)


# ─── Step 1: Fetch Jira story ─────────────────────────────────────────────────

def _adf_to_text(node: dict) -> str:
    """Recursively extract plain text from an Atlassian Document Format node."""
    if not node:
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    return " ".join(_adf_to_text(child) for child in node.get("content", []))


def fetch_story(key: str) -> dict:
    local_path = Path(__file__).parent / "data" / f"jira-story.{key}.json"
    if local_path.exists():
        log(f"Using local mock: agentic-ai/data/jira-story.{key}.json")
        return json.loads(local_path.read_text(encoding="utf-8"))

    jira_url   = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    jira_email = os.getenv("JIRA_EMAIL", "")
    jira_token = os.getenv("JIRA_API_TOKEN", "")

    if not all([jira_url, jira_email, jira_token]):
        raise EnvironmentError(
            f'No local mock found for "{key}" and Jira credentials are missing.\n'
            f"Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in your .env file,\n"
            f"or create agentic-ai/data/jira-story.{key}.json as a local mock."
        )

    import base64
    import urllib.request

    log(f"Fetching {key} from Jira API...")
    auth  = base64.b64encode(f"{jira_email}:{jira_token}".encode()).decode()
    url   = f"{jira_url}/rest/api/3/issue/{key}"
    req   = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    ctx   = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        data = json.loads(resp.read().decode())

    full_description = _adf_to_text(data["fields"].get("description") or {})
    ac_lines = [
        line.strip()
        for line in re.split(r"[\n.]+", full_description)
        if re.match(r"^AC\d+:", line.strip(), re.IGNORECASE)
    ]

    return {
        "key":                data["key"],
        "summary":            data["fields"]["summary"],
        "description":        full_description[:400],
        "acceptanceCriteria": ac_lines if ac_lines else [f"AC1: {full_description[:200]}"],
        "testCaseLink":       data["fields"].get("customfield_10016", ""),
    }


# ─── Step 2: LLM-powered test generation ─────────────────────────────────────

def _build_prompt(story: dict) -> str:
    ac_list = "\n\n".join(
        f"--- Scenario {i + 1} ---\n{ac}"
        for i, ac in enumerate(story["acceptanceCriteria"])
    )
    key     = story["key"]
    summary = story["summary"]

    return f"""\
You are automating tests for a web app at: {APP_URL}

Generate a complete, runnable Playwright TypeScript test file from this Jira user story.
The acceptance criteria are written in Gherkin (Given/When/Then). Map each Gherkin Scenario to one test() block.

Jira Key:    {key}
Summary:     {summary}
User Story:  {story["description"]}

Acceptance Criteria (Gherkin):
{ac_list}

Rules:
- Use "import {{ test, expect }} from '@playwright/test';"
- Wrap all tests in a test.describe block named: "[{key}] {summary}"
- Each Gherkin Scenario becomes one test() — use the Scenario title as the test name
- Map Given steps to page.goto() / page setup
- Map When steps to page interactions (fill, click, etc.)
- Map Then steps to expect() assertions
- Use realistic CSS selectors for the app at {APP_URL} (e.g. #username, #password, button[type=submit], .flash.success, .flash.error, #flash, a[href="/logout"])
- Add a JSDoc comment block at the top listing: Jira key, summary, and each scenario title
- Output ONLY valid TypeScript — no markdown code fences, no prose, no explanations"""


def generate_test_with_llm(story: dict) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set in .env — required for LLM test generation.\n"
            "Add it to your .env file: OPENAI_API_KEY=sk-..."
        )

    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    log(f"Calling OpenAI ({model}) to generate Playwright test for {story['key']}...")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert Playwright test engineer who writes clean, idiomatic TypeScript tests. "
                    "You output ONLY runnable TypeScript code — no markdown, no prose."
                ),
            },
            {"role": "user", "content": _build_prompt(story)},
        ],
    )
    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences that the LLM sometimes adds despite instructions
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


# ─── Step 3: Write test file ──────────────────────────────────────────────────

def write_test_file(story_key: str, code: str) -> Path:
    out_dir  = ROOT / "tests" / "ai-generated"
    out_path = out_dir / f"{story_key}.spec.ts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(code, encoding="utf-8")
    return out_path


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    story_key = sys.argv[1] if len(sys.argv) > 1 else os.getenv("STORY_KEY", "LOGIN-123")

    log(f"🚀 Starting automation for Jira story: {story_key}")
    log(f"App under test: {APP_URL}\n")

    # 1. Fetch story
    story = fetch_story(story_key)
    log(f"Story fetched: \"{story['summary']}\"")
    log(f"Acceptance criteria: {len(story['acceptanceCriteria'])} item(s)")
    for i, ac in enumerate(story["acceptanceCriteria"]):
        log(f"  {i + 1}. {ac[:80]}...")

    # 2. Generate test
    code = generate_test_with_llm(story)

    # 3. Write file
    out_path = write_test_file(story_key, code)
    rel_path = out_path.relative_to(ROOT)
    ok(f"Test written to: {rel_path}")

    print("\n─── Generated test ─────────────────────────────────────────\n")
    print(code)
    print("\n────────────────────────────────────────────────────────────")
    print(f"\nRun it with:\n  npx playwright test {rel_path}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(str(exc))
        sys.exit(1)

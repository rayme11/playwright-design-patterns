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

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Use jira_client for all Jira operations
sys.path.insert(0, str(Path(__file__).parent))
from jira_client import fetch_story  # noqa: E402

ROOT    = Path(__file__).parent.parent
APP_URL = os.getenv("APP_URL", "https://the-internet.herokuapp.com")


# ─── Logging ────────────────────────────────────────────────────────────────

def log(msg: str)  -> None: print(f"[automate] {msg}")
def ok(msg: str)   -> None: print(f"[automate] ✅ {msg}")
def fail(msg: str) -> None: print(f"[automate] ❌ {msg}", file=sys.stderr)


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


def _strip_fences(text: str) -> str:
    """Strip markdown code fences that LLMs sometimes add despite instructions."""
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _generate_with_claude(prompt: str, story_key: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package not installed. Run: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    model   = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    log(f"Calling Claude ({model}) to generate Playwright test for {story_key}...")

    client   = anthropic.Anthropic(api_key=api_key)
    message  = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0.2,
        system=(
            "You are an expert Playwright test engineer who writes clean, idiomatic TypeScript tests. "
            "You output ONLY runnable TypeScript code — no markdown fences, no prose."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return _strip_fences(message.content[0].text)


def _generate_with_openai(prompt: str, story_key: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package not installed. Run: pip install openai")

    api_key = os.getenv("OPENAI_API_KEY")
    model   = os.getenv("OPENAI_MODEL", "gpt-4o")
    log(f"Calling OpenAI ({model}) to generate Playwright test for {story_key}...")

    client   = OpenAI(api_key=api_key)
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
            {"role": "user", "content": prompt},
        ],
    )
    return _strip_fences(response.choices[0].message.content)


def generate_test_with_llm(story: dict) -> str:
    """Generate a Playwright TypeScript test using Claude (preferred) or OpenAI."""
    prompt = _build_prompt(story)

    if os.getenv("ANTHROPIC_API_KEY"):
        return _generate_with_claude(prompt, story["key"])

    if os.getenv("OPENAI_API_KEY"):
        return _generate_with_openai(prompt, story["key"])

    raise EnvironmentError(
        "No LLM API key found. Set one of:\n"
        "  ANTHROPIC_API_KEY=sk-ant-...   (preferred — Claude)\n"
        "  OPENAI_API_KEY=sk-...           (fallback — GPT-4o)\n"
        "Add it to your .env file."
    )


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

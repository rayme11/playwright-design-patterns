"""
Script: pipeline.py
Purpose: Full end-to-end pipeline — no prompts, no interaction:
  1. Fetch the Jira story (real API or local mock)
  2. Generate a Playwright TypeScript test via GPT-4o
  3. Run the tests and write JSON results
  4. Post a test report comment to Jira

Usage:
    python agentic-ai/pipeline.py SCRUM-4
    STORY_KEY=SCRUM-4 python agentic-ai/pipeline.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ROOT = Path(__file__).parent.parent


def log(msg: str)  -> None: print(f"[pipeline] {msg}")
def ok(msg: str)   -> None: print(f"[pipeline] ✅ {msg}")
def fail(msg: str) -> None: print(f"[pipeline] ❌ {msg}", file=sys.stderr)


def run(cmd: list[str], env: dict | None = None, capture: bool = False):
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=merged_env,
        capture_output=capture,
        text=True,
    )
    if result.returncode != 0:
        if capture:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def main():
    story_key = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("STORY_KEY", "")).strip().upper()
    if not story_key:
        fail("Usage: python agentic-ai/pipeline.py <STORY-KEY>")
        sys.exit(1)

    results_dir  = ROOT / "tests" / "ai-generated" / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / f"{story_key}-results.json"
    spec_file    = ROOT / "tests" / "ai-generated" / f"{story_key}.spec.ts"

    # ── Step 1 + 2: Fetch story → generate test ──────────────────────────────
    log(f"Step 1/3 — Generating test for {story_key}...")
    run([sys.executable, "agentic-ai/automate_story.py", story_key])
    ok(f"Test written → {spec_file.relative_to(ROOT)}")

    # ── Step 3: Run Playwright tests, write JSON results ─────────────────────
    log("Step 2/3 — Running Playwright tests...")
    run(
        ["npx", "playwright", "test", str(spec_file.relative_to(ROOT)), "--reporter=json"],
        env={"PLAYWRIGHT_JSON_OUTPUT_NAME": str(results_file)},
    )
    ok(f"Tests passed → {results_file.relative_to(ROOT)}")

    # ── Step 4: Report results to Jira ───────────────────────────────────────
    log("Step 3/3 — Reporting results to Jira...")
    run(
        [sys.executable, "agentic-ai/report_to_jira.py"],
        env={
            "JIRA_ISSUE_KEY": story_key,
            "RESULTS_FILE":   str(results_file),
        },
    )
    ok(f"Done — results posted to Jira {story_key}")


if __name__ == "__main__":
    main()

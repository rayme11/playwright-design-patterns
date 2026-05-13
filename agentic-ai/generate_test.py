"""
Script: generate_test.py
Purpose: Reads a Jira user story JSON and generates a Playwright TypeScript test file
         using a hardcoded template. Intentionally includes a broken selector (.flash-success)
         on the first AC so the self-healing agent can detect and fix it.

Usage:
    python agentic-ai/generate_test.py
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT       = Path(__file__).parent.parent
STORY_PATH = Path(__file__).parent / "data" / "jira-story.LOGIN-123.json"
OUT_PATH   = ROOT / "tests" / "ai-generated" / "generated-login.spec.ts"


def generate_test(story: dict) -> str:
    key                = story["key"]
    summary            = story["summary"]
    description        = story["description"]
    acceptance_criteria = story["acceptanceCriteria"]
    test_case_link     = story.get("testCaseLink", "")

    ac_comment = "\n".join(f" *   - {ac}" for ac in acceptance_criteria)

    test_blocks = []
    for i, ac in enumerate(acceptance_criteria):
        # Extract only the first line (the Scenario title) — ignore the Given/When/Then body
        first_line = ac.splitlines()[0].strip()
        # Strip leading "Scenario:", "AC1:", etc.
        title = re.sub(r"^(Scenario|AC\d+)\s*:\s*", "", first_line, flags=re.IGNORECASE).strip().rstrip(".")
        if i == 0:
            # Intentionally broken selector — self-heal will fix this
            block = (
                f"  test('AC{i+1}: {title}', async ({{ page }}) => {{\n"
                f"    await page.goto('https://the-internet.herokuapp.com/login');\n"
                f"    await page.fill('#username', 'tomsmith');\n"
                f"    await page.fill('#password', 'SuperSecretPassword!');\n"
                f"    await page.click('button[type=submit]');\n"
                f"    await expect(page).toHaveURL(/secure/);\n"
                f"    await expect(page.locator('.flash-success')).toBeVisible(); // broken — self-heal will fix this\n"
                f"  }});"
            )
        else:
            block = (
                f"  test('AC{i+1}: {title}', async ({{ page }}) => {{\n"
                f"    await page.goto('https://the-internet.herokuapp.com/login');\n"
                f"    await page.fill('#username', 'invalid');\n"
                f"    await page.fill('#password', 'invalid');\n"
                f"    await page.click('button[type=submit]');\n"
                f"    await expect(page.locator('.flash.error')).toBeVisible();\n"
                f"  }});"
            )
        test_blocks.append(block)

    tests_str = "\n\n".join(test_blocks)

    return f"""\
/**
 * Jira Key:  {key}
 * Summary:   {summary}
 * Description: {description}
 * Acceptance Criteria:
{ac_comment}
 * Test Case Link: {test_case_link}
 */
import {{ test, expect }} from '@playwright/test';

test.describe('[Jira: {key}] {summary}', () => {{
{tests_str}
}});
"""


def main() -> None:
    story = json.loads(STORY_PATH.read_text(encoding="utf-8"))
    test_code = generate_test(story)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(test_code, encoding="utf-8")
    print(f"Generated Playwright test at: {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

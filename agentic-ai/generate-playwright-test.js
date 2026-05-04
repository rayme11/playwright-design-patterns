// Script: generate-playwright-test.js
// Purpose: Reads a mock Jira user story and generates a Playwright test file based on acceptance criteria.

const fs = require('fs');
const path = require('path');

const storyPath = path.join(__dirname, 'jira-story.LOGIN-123.json');
const outputTestPath = path.join(__dirname, '../tests/ai-generated/generated-login.spec.ts');

function generateTest({ key, summary, description, acceptanceCriteria, testCaseLink }) {
  return `/**
 * Jira Key: ${key}
 * Summary: ${summary}
 * Description: ${description}
 * Acceptance Criteria: ${acceptanceCriteria.map((ac, i) => `\n *   - ${ac}`).join('')}
 * Test Case Link: ${testCaseLink}
 */
import { test, expect } from '@playwright/test';

test.describe('[Jira: ${key}] ${summary}', () => {
${acceptanceCriteria.map((ac, i) => {
  const title = ac.replace(/^AC\d+: /, '').replace(/\.$/, '');
  if (i === 0) {
    return `  test('AC${i+1}: ${title}', async ({ page }) => {\n    // TODO: Implement valid login scenario\n    // Example:\n    // await page.goto('https://the-internet.herokuapp.com/login');\n    // await page.fill('#username', 'tomsmith');\n    // await page.fill('#password', 'SuperSecretPassword!');\n    // await page.click('button[type=submit]');\n    // await expect(page).toHaveURL(/secure/);\n    // await expect(page.locator('.flash.success')).toBeVisible();\n  });`;
  } else {
    return `  test('AC${i+1}: ${title}', async ({ page }) => {\n    // TODO: Implement invalid login scenario\n    // Example:\n    // await page.goto('https://the-internet.herokuapp.com/login');\n    // await page.fill('#username', 'invalid');\n    // await page.fill('#password', 'invalid');\n    // await page.click('button[type=submit]');\n    // await expect(page.locator('.flash.error')).toBeVisible();\n  });`;
  }
}).join('\n\n')}
});
`;
}

function main() {
  const story = JSON.parse(fs.readFileSync(storyPath, 'utf-8'));
  const testCode = generateTest(story);
  fs.writeFileSync(outputTestPath, testCode);
  console.log(`Generated Playwright test at: ${outputTestPath}`);
}

if (require.main === module) {
  main();
}

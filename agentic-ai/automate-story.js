// Script: automate-story.js
// Purpose: Step 8+9 — Full agentic pipeline:
//   1. Accept a Jira story key (CLI arg or STORY_KEY env var)
//   2. Fetch the story from local mock JSON or the real Jira REST API
//   3. Call an LLM (OpenAI) to generate a Playwright TypeScript test from acceptance criteria
//   4. Write the test to tests/ai-generated/{storyKey}.spec.ts
//
// Usage:
//   node agentic-ai/automate-story.js LOGIN-123
//   STORY_KEY=LOGIN-123 node agentic-ai/automate-story.js
//
// Required .env vars for real Jira:
//   JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
// Required .env vars for LLM generation:
//   OPENAI_API_KEY
// Optional:
//   OPENAI_MODEL  (default: gpt-4o)
//   APP_URL       (default: https://the-internet.herokuapp.com)

const fs   = require('fs');
const path = require('path');

require('dotenv').config({ path: path.join(__dirname, '../.env') });

const STORY_KEY = process.argv[2] || process.env.STORY_KEY || 'LOGIN-123';
const ROOT      = path.join(__dirname, '..');
const APP_URL   = process.env.APP_URL || 'https://the-internet.herokuapp.com';

// ─── Logging ────────────────────────────────────────────────────────────────

function log(msg)  { console.log(`[automate] ${msg}`); }
function ok(msg)   { console.log(`[automate] ✅ ${msg}`); }
function fail(msg) { console.error(`[automate] ❌ ${msg}`); }

// ─── Step 1: Fetch Jira story ────────────────────────────────────────────────

/**
 * Recursively extract plain text from an Atlassian Document Format (ADF) node.
 */
function adfToText(node) {
  if (!node) return '';
  if (node.type === 'text') return node.text || '';
  return (node.content || []).map(adfToText).join(' ');
}

async function fetchStory(key) {
  // Local mock takes priority — great for demos and offline work
  const localPath = path.join(__dirname, `data/jira-story.${key}.json`);
  if (fs.existsSync(localPath)) {
    log(`Using local mock: agentic-ai/data/jira-story.${key}.json`);
    return JSON.parse(fs.readFileSync(localPath, 'utf-8'));
  }

  // Fall back to real Jira REST API
  const { JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN } = process.env;
  if (!JIRA_BASE_URL || !JIRA_EMAIL || !JIRA_API_TOKEN) {
    throw new Error(
      `No local mock found for "${key}" and Jira credentials are missing.\n` +
      `Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in your .env file,\n` +
      `or create agentic-ai/data/jira-story.${key}.json as a local mock.`
    );
  }

  log(`Fetching ${key} from Jira API...`);
  const auth = Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64');
  const url  = `${JIRA_BASE_URL}/rest/api/3/issue/${key}`;

  const res = await fetch(url, {
    headers: { Authorization: `Basic ${auth}`, Accept: 'application/json' },
  });

  if (!res.ok) {
    throw new Error(`Jira API responded with ${res.status} ${res.statusText} for ${key}`);
  }

  const data = await res.json();
  const fullDescription = adfToText(data.fields.description);

  // Extract AC lines (lines starting with "AC1:", "AC2:", etc.)
  const acLines = fullDescription
    .split(/[\n.]+/)
    .map(l => l.trim())
    .filter(l => /^AC\d+:/i.test(l));

  return {
    key:                data.key,
    summary:            data.fields.summary,
    description:        fullDescription.slice(0, 400),
    acceptanceCriteria: acLines.length > 0 ? acLines : [`AC1: ${fullDescription.slice(0, 200)}`],
    testCaseLink:       data.fields['customfield_10016'] || '',
  };
}

// ─── Step 2: LLM-powered test generation ────────────────────────────────────

function buildPrompt(story) {
  const acList = story.acceptanceCriteria
    .map((ac, i) => `--- Scenario ${i + 1} ---\n${ac}`)
    .join('\n\n');

  return `You are automating tests for a web app at: ${APP_URL}

Generate a complete, runnable Playwright TypeScript test file from this Jira user story.
The acceptance criteria are written in Gherkin (Given/When/Then). Map each Gherkin Scenario to one test() block.

Jira Key:    ${story.key}
Summary:     ${story.summary}
User Story:  ${story.description}

Acceptance Criteria (Gherkin):
${acList}

Rules:
- Use "import { test, expect } from '@playwright/test';"
- Wrap all tests in a test.describe block named: "[${story.key}] ${story.summary}"
- Each Gherkin Scenario becomes one test() — use the Scenario title as the test name
- Map Given steps to page.goto() / page setup
- Map When steps to page interactions (fill, click, etc.)
- Map Then steps to expect() assertions
- Use realistic CSS selectors for the app at ${APP_URL} (e.g. #username, #password, button[type=submit], .flash.success, .flash.error, #flash, a[href="/logout"])
- Add a JSDoc comment block at the top listing: Jira key, summary, and each scenario title
- Output ONLY valid TypeScript — no markdown code fences, no prose, no explanations`;
}

async function generateTestWithLLM(story) {
  const { OPENAI_API_KEY } = process.env;
  if (!OPENAI_API_KEY) {
    throw new Error(
      'OPENAI_API_KEY is not set in .env — required for LLM test generation.\n' +
      'Add it to your .env file: OPENAI_API_KEY=sk-...'
    );
  }

  const model = process.env.OPENAI_MODEL || 'gpt-4o';
  log(`Calling OpenAI (${model}) to generate Playwright test for ${story.key}...`);

  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      Authorization:  `Bearer ${OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model,
      temperature: 0.2,
      messages: [
        {
          role: 'system',
          content:
            'You are an expert Playwright test engineer who writes clean, idiomatic TypeScript tests. ' +
            'You output ONLY runnable TypeScript code — no markdown, no prose.',
        },
        {
          role: 'user',
          content: buildPrompt(story),
        },
      ],
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`OpenAI API error: ${res.status} — ${errText}`);
  }

  const data = await res.json();
  return data.choices[0].message.content.trim();
}

// ─── Step 3: Write test file ─────────────────────────────────────────────────

function writeTestFile(storyKey, code) {
  const outDir  = path.join(ROOT, 'tests/ai-generated');
  const outPath = path.join(outDir, `${storyKey}.spec.ts`);
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(outPath, code, 'utf-8');
  return outPath;
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main() {
  log(`🚀 Starting automation for Jira story: ${STORY_KEY}`);
  log(`App under test: ${APP_URL}\n`);

  // 1. Fetch story
  const story = await fetchStory(STORY_KEY);
  log(`Story fetched: "${story.summary}"`);
  log(`Acceptance criteria: ${story.acceptanceCriteria.length} item(s)`);
  story.acceptanceCriteria.forEach((ac, i) => log(`  ${i + 1}. ${ac}`));

  // 2. Generate test
  const code = await generateTestWithLLM(story);

  // 3. Write file
  const outPath = writeTestFile(STORY_KEY, code);
  const relPath = path.relative(ROOT, outPath);
  ok(`Test written to: ${relPath}`);

  // Print generated code so the LLM / user can see it
  console.log('\n─── Generated test ─────────────────────────────────────────\n');
  console.log(code);
  console.log('\n────────────────────────────────────────────────────────────');
  console.log(`\nRun it with:\n  npx playwright test ${relPath}\n`);
}

main().catch(err => {
  fail(err.message);
  process.exit(1);
});

module.exports = { fetchStory, generateTestWithLLM, writeTestFile };

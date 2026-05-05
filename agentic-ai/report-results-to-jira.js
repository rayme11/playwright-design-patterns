// Script: report-results-to-jira.js
// Purpose: Reads Playwright JSON test results and simulates reporting them back to Jira.
//
// In a real-world setup this script would POST to:
//   POST /rest/api/3/issue/{issueKey}/comment    (Jira REST API)
// or use a test management plugin API (Xray, Zephyr) to create/update test executions.
//
// For demo purposes it reads the results, builds the comment body,
// and either prints it (dry-run) or sends it to the real Jira API
// when JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN env vars are present.

const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../.env') });

const RESULTS_FILE = path.join(__dirname, '../tests/ai-generated/test-results', 'generated-login.json');
const JIRA_KEY = process.env.JIRA_ISSUE_KEY || 'SCRUM-1'; // override with JIRA_ISSUE_KEY env var

// ─── Load results ───────────────────────────────────────────────────────────
const results = JSON.parse(fs.readFileSync(RESULTS_FILE, 'utf-8'));
const { stats, suites } = results;

// ─── Flatten all tests ───────────────────────────────────────────────────────
function collectTests(suites = []) {
  const tests = [];
  for (const suite of suites) {
    for (const spec of suite.specs ?? []) {
      for (const test of spec.tests ?? []) {
        tests.push({
          title: spec.title,
          status: test.results?.[0]?.status ?? 'unknown',
          duration: test.results?.[0]?.duration ?? 0,
          error: test.results?.[0]?.error?.message ?? null,
        });
      }
    }
    if (suite.suites) tests.push(...collectTests(suite.suites));
  }
  return tests;
}

const tests = collectTests(suites);
const passed = tests.filter(t => t.status === 'passed').length;
const failed = tests.filter(t => t.status === 'failed').length;
const overall = failed === 0 ? '✅ PASSED' : '❌ FAILED';

// ─── Build Jira comment body ─────────────────────────────────────────────────
const testLines = tests.map(t => {
  const icon = t.status === 'passed' ? '✅' : '❌';
  const err = t.error ? `\n      Error: ${t.error.split('\n')[0]}` : '';
  return `  ${icon} ${t.title} (${t.duration}ms)${err}`;
}).join('\n');

const runDate = new Date(stats.startTime).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';

const commentBody = `
🤖 *Agentic AI Test Report* — ${JIRA_KEY}

*Overall:* ${overall}
*Run Date:* ${runDate}
*Duration:* ${(stats.duration / 1000).toFixed(2)}s
*Tests:* ${passed} passed, ${failed} failed

*Results:*
${testLines}

_Generated automatically by the agentic CI workflow._
`.trim();

console.log('\n─── Jira Comment (Dry Run) ─────────────────────────────────────────────\n');
console.log(commentBody);
console.log('\n────────────────────────────────────────────────────────────────────────\n');

// ─── Real Jira API call (only when credentials are available) ────────────────
const { JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN } = process.env;

if (JIRA_BASE_URL && JIRA_EMAIL && JIRA_API_TOKEN) {
  const auth = Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64');
  const baseUrl = JIRA_BASE_URL.replace(/\/$/, ''); // strip trailing slash
  const url = `${baseUrl}/rest/api/3/issue/${JIRA_KEY}/comment`;

  fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Basic ${auth}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      body: {
        type: 'doc',
        version: 1,
        content: [{
          type: 'paragraph',
          content: [{ type: 'text', text: commentBody }]
        }]
      }
    })
  })
    .then(res => res.json())
    .then(data => console.log(`✅ Comment posted to Jira ${JIRA_KEY}:`, data.id))
    .catch(err => console.error('❌ Failed to post Jira comment:', err.message));
} else {
  console.log('ℹ️  No Jira credentials found in environment. Running in dry-run mode.');
  console.log('   To post real comments, set: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN');
}

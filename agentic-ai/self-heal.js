// Script: self-heal.js
// Purpose: Agentic self-healing loop for Step 5.
//
// Flow:
//   1. Run the generated Playwright test
//   2. If it passes → nothing to heal, report results
//   3. If it fails → launch a headless browser, navigate to the page,
//      inspect the DOM for flash/alert elements, find the correct selector
//   4. Patch the test file with the healed selector
//   5. Re-run the tests to confirm the fix
//   6. Post the full report (failure + fix + passing results) to Jira SCRUM-1

const { execSync, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test/reporter');

require('dotenv').config({ path: path.join(__dirname, '../.env') });

const TEST_FILE   = path.join(__dirname, '../tests/ai-generated/generated-login.spec.ts');
const RESULTS_FILE = path.join(__dirname, '../tests/ai-generated/test-results/generated-login.json');
const JIRA_KEY    = process.env.JIRA_ISSUE_KEY || 'SCRUM-1';

// ─── Helpers ────────────────────────────────────────────────────────────────

function log(msg) { console.log(`\n[self-heal] ${msg}`); }

function runTests() {
  log('Running Playwright tests...');
  const result = spawnSync('npx', [
    'playwright', 'test',
    'tests/ai-generated/generated-login.spec.ts',
    '--reporter=json',
  ], {
    cwd: path.join(__dirname, '..'),
    env: {
      ...process.env,
      PLAYWRIGHT_JSON_OUTPUT_NAME: 'tests/ai-generated/test-results/generated-login.json',
    },
    encoding: 'utf-8',
  });
  return result.status === 0; // true = all passed
}

function readResults() {
  return JSON.parse(fs.readFileSync(RESULTS_FILE, 'utf-8'));
}

// Walk the suite tree and find the first failed test + its error message
function findFailure(suites = []) {
  for (const suite of suites) {
    for (const spec of suite.specs ?? []) {
      for (const test of spec.tests ?? []) {
        const r = test.results?.[0];
        if (r?.status === 'failed') {
          return {
            title: spec.title,
            error: r.error?.message ?? '',
          };
        }
      }
    }
    const nested = findFailure(suite.suites ?? []);
    if (nested) return nested;
  }
  return null;
}

// Extract the broken selector from the error message or scan the test file
function extractBrokenSelector(errorMsg, testSource) {
  // Playwright errors contain "locator('...')" in the call frame
  const fromError = errorMsg.match(/locator\(['"]([^'"]+)['"]\)/);
  if (fromError) return fromError[1];

  // Fallback: scan the test file for locator() calls
  const fromFile = testSource.match(/locator\(['"]([^'"]+)['"]\)/g);
  if (fromFile) return fromFile[0].match(/locator\(['"]([^'"]+)['"]\)/)[1];

  return null;
}

// ─── DOM Inspector ──────────────────────────────────────────────────────────
// Uses Playwright directly (not the test runner) to load the page and
// inspect what flash/alert classes actually exist after login.

async function findCorrectSelector() {
  log('Launching headless browser to inspect live DOM...');
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto('https://the-internet.herokuapp.com/login');
  await page.fill('#username', 'tomsmith');
  await page.fill('#password', 'SuperSecretPassword!');
  await page.click('button[type=submit]');
  await page.waitForLoadState('domcontentloaded');

  // Get all classes on every .flash* or #flash element
  const candidates = await page.evaluate(() => {
    const els = document.querySelectorAll('[class*="flash"], [id*="flash"], [class*="alert"]');
    return Array.from(els).map(el => ({
      tag:     el.tagName.toLowerCase(),
      id:      el.id,
      classes: Array.from(el.classList),
      text:    el.textContent?.trim().slice(0, 80),
    }));
  });

  await browser.close();
  log('DOM candidates found:\n' + JSON.stringify(candidates, null, 2));

  // Priority 1: element whose classes contain "success" explicitly
  const bySuccessClass = candidates.find(c =>
    c.classes.some(cls => cls.toLowerCase() === 'success')
  );
  if (bySuccessClass && bySuccessClass.classes.length > 0) {
    return '.' + bySuccessClass.classes.join('.');
  }

  // Priority 2: element whose classes contain "success" as substring
  const bySuccessSubstr = candidates.find(c =>
    c.classes.some(cls => cls.toLowerCase().includes('success'))
  );
  if (bySuccessSubstr && bySuccessSubstr.classes.length > 0) {
    return '.' + bySuccessSubstr.classes.join('.');
  }

  // Priority 3: element whose text signals a successful login
  const success = candidates.find(c =>
    c.text?.toLowerCase().includes('secure area') ||
    c.text?.toLowerCase().includes('logged in')
  );
  if (success) {
    if (success.classes.length > 0) return '.' + success.classes.join('.');
    if (success.id) return `#${success.id}`;
  }

  // Fallback: return the first candidate's classes
  if (candidates[0]?.classes.length > 0) {
    return '.' + candidates[0].classes.join('.');
  }

  return null;
}

// ─── File Patcher ───────────────────────────────────────────────────────────

function patchTestFile(brokenSelector, healedSelector) {
  log(`Patching test file: "${brokenSelector}" → "${healedSelector}"`);
  let source = fs.readFileSync(TEST_FILE, 'utf-8');
  const escaped = brokenSelector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const updated = source.replace(new RegExp(escaped, 'g'), healedSelector);
  if (source === updated) {
    log('WARNING: selector not found in file — patch skipped.');
    return false;
  }
  fs.writeFileSync(TEST_FILE, updated, 'utf-8');
  log('File patched successfully.');
  return true;
}

// ─── Jira Reporter ──────────────────────────────────────────────────────────

function postToJira(commentBody) {
  const { JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN } = process.env;
  if (!JIRA_BASE_URL || !JIRA_EMAIL || !JIRA_API_TOKEN) {
    log('No Jira credentials — skipping post.');
    return;
  }
  const auth = Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64');
  const baseUrl = JIRA_BASE_URL.replace(/\/$/, '');
  const url = `${baseUrl}/rest/api/3/issue/${JIRA_KEY}/comment`;

  fetch(url, {
    method: 'POST',
    headers: { 'Authorization': `Basic ${auth}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      body: {
        type: 'doc', version: 1,
        content: [{ type: 'paragraph', content: [{ type: 'text', text: commentBody }] }],
      },
    }),
  })
    .then(r => r.json())
    .then(d => log(`✅ Jira comment posted to ${JIRA_KEY}: id=${d.id}`))
    .catch(e => log(`❌ Jira post failed: ${e.message}`));
}

// ─── Main Agentic Loop ───────────────────────────────────────────────────────

(async () => {
  // ── Round 1: initial run ──
  const firstRunPassed = runTests();

  if (firstRunPassed) {
    log('All tests passed on first run — nothing to heal. 🎉');
    const results = readResults();
    postToJira(`🤖 Agentic AI — ${JIRA_KEY}\n\n✅ All tests passed on first run. No self-healing required.`);
    return;
  }

  // ── Failure detected ──
  const results1 = readResults();
  const failure = findFailure(results1.suites);
  log(`Failure detected in: "${failure?.title}"`);
  log(`Error: ${failure?.error?.split('\n')[0]}`);

  const testSource = fs.readFileSync(TEST_FILE, 'utf-8');
  const brokenSelector = extractBrokenSelector(failure?.error ?? '', testSource);
  log(`Broken selector identified: "${brokenSelector}"`);

  if (!brokenSelector) {
    log('Could not identify broken selector — manual intervention needed.');
    process.exit(1);
  }

  // ── DOM inspection → find correct selector ──
  const healedSelector = await findCorrectSelector();
  if (!healedSelector) {
    log('DOM inspection found no matching element — manual intervention needed.');
    process.exit(1);
  }
  log(`Healed selector: "${healedSelector}"`);

  // ── Patch the file ──
  const patched = patchTestFile(brokenSelector, healedSelector);
  if (!patched) process.exit(1);

  // ── Round 2: rerun after fix ──
  log('Re-running tests after patch...');
  const secondRunPassed = runTests();
  const results2 = readResults();

  const tests = [];
  function collectTests(suites = []) {
    for (const suite of suites) {
      for (const spec of suite.specs ?? []) {
        for (const test of spec.tests ?? []) {
          const r = test.results?.[0];
          tests.push({ title: spec.title, status: r?.status, duration: r?.duration ?? 0 });
        }
      }
      collectTests(suite.suites ?? []);
    }
  }
  collectTests(results2.suites);

  const testLines = tests.map(t =>
    `  ${t.status === 'passed' ? '✅' : '❌'} ${t.title} (${t.duration}ms)`
  ).join('\n');

  const commentBody = `
🤖 *Agentic Self-Healing Report* — ${JIRA_KEY}

*Broken selector detected:* \`${brokenSelector}\`
*Healed selector applied:*  \`${healedSelector}\`
*Second run result:* ${secondRunPassed ? '✅ ALL PASSED' : '❌ STILL FAILING'}

*Test Results after fix:*
${testLines}

_Self-healed automatically by the agentic CI workflow._
`.trim();

  console.log('\n─── Self-Heal Report ───────────────────────────────────────────────────\n');
  console.log(commentBody);
  console.log('\n────────────────────────────────────────────────────────────────────────\n');

  postToJira(commentBody);

  if (!secondRunPassed) {
    log('Tests still failing after patch — review manually.');
    process.exit(1);
  }

  log('Self-healing complete. Tests green. Jira updated. ✅');
})();

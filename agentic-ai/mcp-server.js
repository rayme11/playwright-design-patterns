// Script: mcp-server.js
// Purpose: Step 7 — MCP (Model Context Protocol) server that exposes agentic tools
//          to VS Code Copilot agent mode.
//
// Tools exposed:
//   fetch_jira_story        — read a Jira story from the local mock JSON (or real Jira API)
//   generate_test_from_story — generate a Playwright test from the story's acceptance criteria
//   run_playwright_tests    — run a Playwright spec file and return a summary
//   self_heal               — detect selector failures, inspect live DOM, patch the test, rerun
//   report_to_jira          — post a test-result comment to a Jira issue
//
// VS Code discovers this server via .vscode/mcp.json.
// Run manually: node agentic-ai/mcp-server.js

const { McpServer } = require('@modelcontextprotocol/sdk/server/mcp.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { z } = require('zod');
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

require('dotenv').config({ path: path.join(__dirname, '../.env') });

const ROOT = path.join(__dirname, '..');

// ─── Helpers ────────────────────────────────────────────────────────────────

/** Run a node script in the project root and return { ok, stdout, stderr }. */
function runScript(scriptPath, extraEnv = {}) {
  const result = spawnSync('node', [scriptPath], {
    cwd: ROOT,
    encoding: 'utf-8',
    env: { ...process.env, ...extraEnv },
  });
  return {
    ok: result.status === 0,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
    status: result.status,
  };
}

/** Run `npx playwright test` for a given spec and return { ok, stdout, stderr }. */
function runPlaywright(specFile, jsonOutputName) {
  const result = spawnSync(
    'npx',
    ['playwright', 'test', specFile, '--reporter=json'],
    {
      cwd: ROOT,
      encoding: 'utf-8',
      env: {
        ...process.env,
        PLAYWRIGHT_JSON_OUTPUT_NAME: jsonOutputName,
      },
    }
  );
  return {
    ok: result.status === 0,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
  };
}

// ─── Logger ─────────────────────────────────────────────────────────────────

const RESET  = '\x1b[0m';
const BOLD   = '\x1b[1m';
const CYAN   = '\x1b[36m';
const GREEN  = '\x1b[32m';
const RED    = '\x1b[31m';
const YELLOW = '\x1b[33m';
const DIM    = '\x1b[2m';

function ts() {
  return new Date().toISOString().replace('T', ' ').slice(0, 23);
}

function mcpLog(level, msg) {
  const colour = level === 'CALL' ? CYAN : level === 'OK' ? GREEN : level === 'ERR' ? RED : YELLOW;
  process.stderr.write(`${DIM}[${ts()}]${RESET} ${colour}${BOLD}[MCP ${level}]${RESET} ${msg}\n`);
}

/**
 * Wraps a tool handler to log the call, args, duration, and result/error to stderr.
 * stdout is reserved for the JSON-RPC protocol stream — never write there.
 */
function logTool(name, handler) {
  return async (args) => {
    const argsStr = Object.keys(args ?? {}).length
      ? JSON.stringify(args)
      : '(no args)';
    mcpLog('CALL', `${BOLD}${name}${RESET}  args=${argsStr}`);
    const start = Date.now();
    try {
      const result = await handler(args);
      const ms = Date.now() - start;
      const isError = result?.isError === true;
      mcpLog(
        isError ? 'ERR' : 'OK',
        `${BOLD}${name}${RESET}  ${isError ? '❌ isError=true' : '✅ success'}  ${DIM}(${ms}ms)${RESET}`
      );
      return result;
    } catch (err) {
      const ms = Date.now() - start;
      mcpLog('ERR', `${BOLD}${name}${RESET}  threw: ${err.message}  ${DIM}(${ms}ms)${RESET}`);
      throw err;
    }
  };
}

// ─── MCP Server ─────────────────────────────────────────────────────────────

const server = new McpServer({
  name: 'playwright-agentic',
  version: '1.0.0',
});

// ── Tool 1: fetch_jira_story ─────────────────────────────────────────────────
server.tool(
  'fetch_jira_story',
  'Fetch a Jira user story and its acceptance criteria. Uses the local mock JSON by default; reads from the real Jira REST API when JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN env vars are present.',
  {
    storyKey: z
      .string()
      .optional()
      .describe('Jira issue key, e.g. "LOGIN-123". Defaults to LOGIN-123.'),
  },
  logTool('fetch_jira_story', async ({ storyKey = 'LOGIN-123' }) => {
    // Try local mock first
    const localPath = path.join(__dirname, `data/jira-story.${storyKey}.json`);
    if (fs.existsSync(localPath)) {
      const story = JSON.parse(fs.readFileSync(localPath, 'utf-8'));
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(story, null, 2),
          },
        ],
      };
    }

    // Fall back to real Jira API
    const { JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN } = process.env;
    if (!JIRA_BASE_URL || !JIRA_EMAIL || !JIRA_API_TOKEN) {
      return {
        content: [
          {
            type: 'text',
            text: `No local mock found for ${storyKey} and Jira credentials are not set.\nSet JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in your .env file.`,
          },
        ],
        isError: true,
      };
    }

    const auth = Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64');
    const url = `${JIRA_BASE_URL}/rest/api/3/issue/${storyKey}`;
    const res = await fetch(url, {
      headers: { Authorization: `Basic ${auth}`, Accept: 'application/json' },
    });

    if (!res.ok) {
      return {
        content: [{ type: 'text', text: `Jira API error: ${res.status} ${res.statusText}` }],
        isError: true,
      };
    }

    const data = await res.json();
    const story = {
      key: data.key,
      summary: data.fields.summary,
      description: data.fields.description?.content?.[0]?.content?.[0]?.text ?? '',
      acceptanceCriteria:
        data.fields['customfield_10016'] ??
        data.fields.description?.content
          ?.flatMap((b) => b.content ?? [])
          .filter((n) => n.type === 'text')
          .map((n) => n.text)
          .filter((t) => t.trim().startsWith('AC')) ?? [],
    };
    return { content: [{ type: 'text', text: JSON.stringify(story, null, 2) }] };
  })
);

// ── Tool 2: generate_test_from_story ────────────────────────────────────────
server.tool(
  'generate_test_from_story',
  "Generate a Playwright test file from the Jira story's acceptance criteria. Runs generate-playwright-test.js.",
  logTool('generate_test_from_story', async () => {
    const { ok, stdout, stderr } = runScript('agentic-ai/generate-playwright-test.js');
    const output = stdout || stderr;
    return {
      content: [{ type: 'text', text: ok ? `Test generated successfully.\n\n${output}` : `Generator failed.\n\n${output}` }],
      isError: !ok,
    };
  })
);

// ── Tool 3: run_playwright_tests ─────────────────────────────────────────────
server.tool(
  'run_playwright_tests',
  'Run a Playwright spec file and return a pass/fail summary with error details for any failures.',
  {
    specFile: z
      .string()
      .optional()
      .describe(
        'Workspace-relative path to the spec file. Defaults to tests/ai-generated/generated-login.spec.ts'
      ),
  },
  logTool('run_playwright_tests', async ({ specFile = 'tests/ai-generated/generated-login.spec.ts' } = {}) => {
    const jsonOutput = 'tests/ai-generated/test-results/generated-login.json';
    const { ok, stdout, stderr } = runPlaywright(specFile, jsonOutput);

    // Try to parse and summarise the JSON results
    const resultsPath = path.join(ROOT, jsonOutput);
    let summary = '';
    if (fs.existsSync(resultsPath)) {
      try {
        const results = JSON.parse(fs.readFileSync(resultsPath, 'utf-8'));
        const stats = results.stats ?? {};
        const total = (stats.expected ?? 0) + (stats.unexpected ?? 0);
        const passed = stats.expected ?? 0;
        const failed = stats.unexpected ?? 0;
        summary = `Results: ${passed}/${total} passed, ${failed} failed.\nDuration: ${((stats.duration ?? 0) / 1000).toFixed(2)}s`;
      } catch {
        summary = 'Could not parse JSON results.';
      }
    }

    return {
      content: [
        {
          type: 'text',
          text: `${ok ? '✅ All tests passed.' : '❌ Tests failed.'}\n\n${summary}\n\nRaw output:\n${stdout || stderr}`,
        },
      ],
      isError: !ok,
    };
  })
);

// ── Tool 4: self_heal ────────────────────────────────────────────────────────
server.tool(
  'self_heal',
  'Run the self-healing agent: detect a broken selector, inspect the live DOM, patch the test file, rerun, and post the fix report to Jira.',
  logTool('self_heal', async () => {
    const { ok, stdout, stderr } = runScript('agentic-ai/self-heal.js');
    const output = stdout || stderr;
    return {
      content: [{ type: 'text', text: ok ? `Self-heal completed successfully.\n\n${output}` : `Self-heal encountered an error.\n\n${output}` }],
      isError: !ok,
    };
  })
);

// ── Tool 5: report_to_jira ───────────────────────────────────────────────────
server.tool(
  'report_to_jira',
  'Read the latest Playwright JSON test results and post a structured comment to the Jira issue. Dry-runs when JIRA credentials are not set.',
  {
    issueKey: z
      .string()
      .optional()
      .describe('Jira issue key to comment on, e.g. "SCRUM-1". Overrides JIRA_ISSUE_KEY env var.'),
  },
  logTool('report_to_jira', async ({ issueKey } = {}) => {
    const env = issueKey ? { JIRA_ISSUE_KEY: issueKey } : {};
    const { ok, stdout, stderr } = runScript('agentic-ai/report-results-to-jira.js', env);
    const output = stdout || stderr;
    return {
      content: [
        {
          type: 'text',
          text: ok
            ? `Jira report posted successfully.\n\n${output}`
            : `Jira reporter encountered an error.\n\n${output}`,
        },
      ],
      isError: !ok,
    };
  })
);

// ─── Start ───────────────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // MCP servers must not write to stdout after connecting (stdout is the protocol channel)
  process.stderr.write(
    `\n${CYAN}${BOLD}╔══════════════════════════════════════════════════════╗${RESET}\n` +
    `${CYAN}${BOLD}║  playwright-agentic MCP server  —  stdio transport   ║${RESET}\n` +
    `${CYAN}${BOLD}╚══════════════════════════════════════════════════════╝${RESET}\n` +
    `${DIM}Tools: fetch_jira_story · generate_test_from_story · run_playwright_tests · self_heal · report_to_jira${RESET}\n` +
    `${DIM}Tip:   npx @modelcontextprotocol/inspector node agentic-ai/mcp-server.js${RESET}\n\n`
  );
}

main().catch((err) => {
  process.stderr.write(`[mcp-server] Fatal error: ${err.message}\n`);
  process.exit(1);
});

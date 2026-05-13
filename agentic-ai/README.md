# Agentic AI — MCP Server & Workflow

This folder contains the **agentic AI layer** of the project: Python scripts that orchestrate a full Jira → generate → run → self-heal → report loop, plus the MCP server that exposes those scripts as tools to VS Code Copilot agent mode.

All orchestration is in **Python 3**. All Playwright tests stay in **TypeScript**.

---

## Table of Contents

- [What is MCP?](#what-is-mcp)
- [Architecture](#architecture)
- [Scripts Reference](#scripts-reference)
- [MCP Tools Reference](#mcp-tools-reference)
- [Setup](#setup)
- [Running the Pipeline](#running-the-pipeline)
- [How to Launch the MCP Server](#how-to-launch-the-mcp-server)
- [Real-Life Usage in VS Code](#real-life-usage-in-vs-code)
- [The JSON-RPC Wire Protocol](#the-json-rpc-wire-protocol)
- [Key Rules](#key-rules)

---

## What is MCP?

**Model Context Protocol (MCP)** is an open standard (by Anthropic) that lets AI assistants — like VS Code Copilot in agent mode — call external tools via a structured JSON-RPC protocol over stdio.

Think of it as a **plugin system for AI agents**:

- Your server declares **tools** with names, descriptions, and parameter schemas.
- The AI reads those descriptions and decides autonomously when and how to call each tool.
- You write natural language goals; the AI chains tool calls to fulfil them.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  VS Code                                                         │
│                                                                  │
│  ┌─────────────────────┐        ┌──────────────────────────┐    │
│  │  Copilot Agent Mode │        │   .vscode/mcp.json       │    │
│  │  (the AI / LLM)     │◄──────►│   "playwright-agentic"   │    │
│  └────────┬────────────┘  auto- │   type: stdio            │    │
│           │               disco-│   command: python3        │    │
│           │               very  │   args: [mcp_server.py]  │    │
│           │                     └──────────────────────────┘    │
└───────────┼──────────────────────────────────────────────────────┘
            │  JSON-RPC 2.0 over stdio (stdout ↔ stdin)
            ▼
┌──────────────────────────────────────────────────────────────────┐
│  agentic-ai/mcp_server.py   (FastMCP server)                    │
│                                                                  │
│  7 registered tools:                                            │
│  • full_pipeline          ← one-shot end-to-end                 │
│  • automate_jira_story    ← fetch + GPT-4o → spec file         │
│  • run_playwright_tests   ← npx playwright test                 │
│  • report_to_jira         ← post results comment                │
│  • fetch_jira_story       ← read story from Jira API            │
│  • generate_test_from_story ← template generator                │
│  • self_heal              ← DOM inspect → patch → rerun         │
│                                    │                             │
│                                    ▼  subprocess                 │
│                    ┌───────────────────────────────────┐        │
│                    │  Python orchestration scripts     │        │
│                    │  pipeline.py                      │        │
│                    │  automate_story.py  (+ OpenAI)    │        │
│                    │  generate_test.py                 │        │
│                    │  self_heal.py      (+ Playwright) │        │
│                    │  report_to_jira.py                │        │
│                    └───────────────┬───────────────────┘        │
│                                    │                             │
│                                    ▼  npx playwright test        │
│                    ┌───────────────────────────────────┐        │
│                    │  tests/ai-generated/{KEY}.spec.ts │        │
│                    │  (TypeScript — untouched by AI)   │        │
│                    └───────────────────────────────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

### Data flow

```
Jira Story (Gherkin AC)
        │
        ▼
automate_story.py ──► OpenAI GPT-4o ──► tests/ai-generated/{KEY}.spec.ts
                                                  │
                                                  ▼
                                   test-results/{KEY}-results.json
                                                  │
                    ┌─────────────────────────────┤
                    │                             ▼
             self_heal.py               report_to_jira.py ──► Jira comment
     (DOM inspect → patch → rerun)
```

---

## Scripts Reference

| File | Purpose |
|------|---------|
| `pipeline.py` | **One-shot pipeline** — fetch → generate → run → report, no interaction |
| `automate_story.py` | Fetch Jira story + call GPT-4o → write `tests/ai-generated/{KEY}.spec.ts` |
| `generate_test.py` | Template-based generator (self-heal demo; AC1 uses broken selector `.flash-success`) |
| `self_heal.py` | Run tests → detect broken selector → headless DOM inspect → patch file → rerun → report |
| `report_to_jira.py` | Read Playwright JSON results → POST structured comment to Jira REST API |
| `mcp_server.py` | FastMCP stdio server — exposes 7 tools to VS Code Copilot agent mode |
| `data/jira-story.LOGIN-123.json` | Local mock story with Gherkin ACs (used when no real Jira creds) |

---

## MCP Tools Reference

| Tool | Args | What it does |
|------|------|-------------|
| `full_pipeline` | `story_key` | One-shot: fetch → GPT-4o → run tests → report to Jira |
| `automate_jira_story` | `story_key` | Fetch story + GPT-4o → write spec file |
| `run_playwright_tests` | `spec_file` | Run a spec and return pass/fail summary |
| `report_to_jira` | `issue_key`, `results_file` | Post results to Jira |
| `fetch_jira_story` | `story_key` | Fetch and return a Jira story |
| `generate_test_from_story` | — | Template-based test generation (self-heal demo) |
| `self_heal` | — | Self-healing agent loop |

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

`requirements.txt`:
```
mcp>=1.0.0
python-dotenv>=1.0.0
openai>=1.0.0
playwright>=1.40.0
```

### 2. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env`:
```bash
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_token      # https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_PROJECT_KEY=SCRUM
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
APP_URL=https://the-internet.herokuapp.com
```

---

## Running the Pipeline

### One command — full pipeline

```bash
python3 agentic-ai/pipeline.py SCRUM-4
```

Output:
```
[pipeline] Step 1/3 — Generating test for SCRUM-4...
[automate] ✅ Test written to: tests/ai-generated/SCRUM-4.spec.ts
[pipeline] Step 2/3 — Running Playwright tests...
  3 passed (6.5s)
[pipeline] Step 3/3 — Reporting results to Jira...
✅ Comment posted to Jira SCRUM-4: id=10148
[pipeline] ✅ Done — results posted to Jira SCRUM-4
```

### Individual steps

```bash
# Fetch story → GPT-4o → write spec
python3 agentic-ai/automate_story.py SCRUM-4

# Run tests (write JSON directly to file — do NOT redirect stdout)
PLAYWRIGHT_JSON_OUTPUT_NAME=tests/ai-generated/test-results/SCRUM-4-results.json \
  npx playwright test tests/ai-generated/SCRUM-4.spec.ts --reporter=json

# Post results to Jira
JIRA_ISSUE_KEY=SCRUM-4 \
  RESULTS_FILE=tests/ai-generated/test-results/SCRUM-4-results.json \
  python3 agentic-ai/report_to_jira.py

# Self-healing demo
python3 agentic-ai/self_heal.py
```

> **Important:** Use `PLAYWRIGHT_JSON_OUTPUT_NAME` to write JSON results to a file. Do **not** use `> file.json` — the global setup prints to stdout and corrupts the JSON.

---


## How to Launch the MCP Server

### Option 1 — VS Code (automatic)

VS Code reads `.vscode/mcp.json` and starts the server automatically when you open the workspace in agent mode:

```json
{
  "servers": {
    "playwright-agentic": {
      "type": "stdio",
      "command": "python3",
      "args": ["${workspaceFolder}/agentic-ai/mcp_server.py"],
      "env": {}
    }
  }
}
```

To restart after code changes: `⌘⇧P` → **MCP: Restart Server**.

### Option 2 — MCP Inspector (debugging)

```bash
npx @modelcontextprotocol/inspector python3 agentic-ai/mcp_server.py
# → open http://localhost:6274
```

### Option 3 — Direct (sanity check)

```bash
python3 agentic-ai/mcp_server.py
# Banner logs to stderr; process waits on stdin for JSON-RPC input
```

---

## Real-Life Usage in VS Code

```
1. Open VS Code Chat → switch to Agent mode (⌘⇧P → "Chat: New Chat" → "Agent")

2. Type a goal:
   "Run full_pipeline for SCRUM-4"

3. Copilot chains tool calls autonomously:

   full_pipeline("SCRUM-4")
        │
        ├─► automate_story.py  → GPT-4o → SCRUM-4.spec.ts
        ├─► npx playwright test → 3/3 passed
        └─► report_to_jira.py  → comment posted to Jira SCRUM-4
```

### Tool chaining for fine-grained control

```
fetch_jira_story("SCRUM-4")            → read story + ACs
        ↓
automate_jira_story("SCRUM-4")         → GPT-4o → SCRUM-4.spec.ts
        ↓
run_playwright_tests("tests/ai-generated/SCRUM-4.spec.ts")  → 3/3 ✅
        ↓
report_to_jira("SCRUM-4")              → Jira comment posted
```

---

## The JSON-RPC Wire Protocol

Every message on stdout/stdin is a JSON-RPC 2.0 envelope.

**VS Code → server (stdin):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "full_pipeline",
    "arguments": { "story_key": "SCRUM-4" }
  }
}
```

**Server → VS Code (stdout):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{ "type": "text", "text": "✅ Pipeline complete for SCRUM-4..." }],
    "isError": false
  }
}
```

**Startup handshake:**
```
VS Code                         mcp_server.py
   │──── initialize ───────────────►│
   │◄─── initialized ───────────────│
   │──── tools/list ────────────────►│  ← AI reads all 7 tool descriptions
   │◄─── { tools: [...] } ──────────│
   │──── tools/call "full_pipeline" ►│
   │◄─── { content: [...] } ────────│
```

---

## Key Rules

| Rule | Why |
|------|-----|
| **Never write to `stdout`** | stdout is the JSON-RPC wire; any stray bytes corrupt the protocol |
| **All logging goes to `stderr`** | Use `print(..., file=sys.stderr)` — never bare `print()` inside the server |
| **Tool descriptions are your prompt** | The AI reads them verbatim to decide which tool to call and when |
| **SSL on macOS** | Python doesn't use the system keychain — use `ssl.CERT_NONE` context for Atlassian API calls |
| **`PLAYWRIGHT_JSON_OUTPUT_NAME`** | Write JSON results to a file; never redirect `--reporter=json` stdout |
| **Tool list locks per session** | New tools appear only in a new VS Code chat session after server restart |


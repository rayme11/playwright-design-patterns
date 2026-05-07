# Agentic AI — MCP Server & Workflow

This folder contains the **agentic AI layer** of the project: scripts that orchestrate a full Jira → generate → run → self-heal → report loop, plus the MCP server that exposes those scripts as tools to VS Code Copilot agent mode.

---

## Table of Contents

- [What is MCP?](#what-is-mcp)
- [Architecture](#architecture)
- [The JSON-RPC Wire Protocol](#the-json-rpc-wire-protocol)
- [How a Tool is Registered](#how-a-tool-is-registered)
- [How to Launch the MCP Server](#how-to-launch-the-mcp-server)
- [Real-Life Usage in VS Code](#real-life-usage-in-vs-code)
- [Agentic Scripts Reference](#agentic-scripts-reference)
- [Key Rules](#key-rules)

---

## What is MCP?

**Model Context Protocol (MCP)** is an open standard (by Anthropic) that lets AI assistants — like VS Code Copilot in agent mode — call external tools via a structured JSON-RPC protocol.

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
│           │               disco-│   command: node          │    │
│           │               very  │   args: [mcp-server.js]  │    │
│           │                     └──────────────────────────┘    │
└───────────┼──────────────────────────────────────────────────────┘
            │  JSON-RPC 2.0 over stdio (stdout ↔ stdin)
            │
            ▼
┌──────────────────────────────────────────────────────────────────┐
│  agentic-ai/mcp-server.js   (your MCP server process)           │
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────────────────────┐  │
│  │  McpServer (SDK)   │  │  5 registered tools:               │  │
│  │  StdioTransport    │  │  • fetch_jira_story                │  │
│  │                    │  │  • generate_test_from_story        │  │
│  │  reads stdin  ──►  │  │  • run_playwright_tests            │  │
│  │  writes stdout ◄── │  │  • self_heal                       │  │
│  │  logs → stderr     │  │  • report_to_jira                  │  │
│  └────────────────────┘  └────────────────────────────────────┘  │
│                                          │                        │
│                                          ▼  spawnSync()           │
│                          ┌───────────────────────────────────┐   │
│                          │  Agentic scripts (Node.js)        │   │
│                          │  generate-playwright-test.js      │   │
│                          │  self-heal.js                     │   │
│                          │  report-results-to-jira.js        │   │
│                          └───────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Why stdio?

The MCP server communicates with VS Code over **stdin / stdout**. This is the `"type": "stdio"` transport. VS Code spawns the server process, writes JSON-RPC requests to its stdin, and reads responses from its stdout. The server **must never write anything to stdout** except protocol messages — all human-readable logging goes to `stderr`.

---

## The JSON-RPC Wire Protocol

Every message on stdout/stdin is a JSON-RPC 2.0 envelope. Here is exactly what flows when Copilot calls a tool:

**VS Code → server (stdin):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "generate_test_from_story",
    "arguments": {}
  }
}
```

**Server → VS Code (stdout):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "Test generated successfully.\n..."
    }],
    "isError": false
  }
}
```

**The handshake sequence (happens once at startup):**
```
VS Code                          mcp-server.js
   │──── initialize ────────────────►│
   │◄─── initialized ────────────────│
   │──── tools/list ─────────────────►│   ← AI reads all tool names + descriptions
   │◄─── { tools: [...] } ───────────│
   │                                  │
   │──── tools/call "fetch_jira..." ──►│   ← triggered by user prompt
   │◄─── { content: [...] } ─────────│
   │──── tools/call "generate..." ───►│
   │◄─── { content: [...] } ─────────│
   │──── tools/call "self_heal" ─────►│   ← AI decided this after seeing test failure
   │◄─── { content: [...] } ─────────│
```

---

## How a Tool is Registered

Every tool has three parts: a **name**, a **description** (what the AI reads to decide when to call it), and a **handler** (what actually runs).

```js
// Tool with no parameters — 3-arg form
server.tool(
  'generate_test_from_story',          // name the AI calls
  'Generate a Playwright test file…',  // description the AI reads
  async () => {                        // handler that runs
    const { ok, stdout } = runScript('agentic-ai/generate-playwright-test.js');
    return {
      content: [{ type: 'text', text: stdout }],
      isError: !ok,
    };
  }
);

// Tool with parameters — 4-arg form, Zod schema as 3rd arg
server.tool(
  'fetch_jira_story',
  'Fetch a Jira story by key…',
  { storyKey: z.string().optional() },   // ← Zod schema → JSON Schema sent to the AI
  async ({ storyKey = 'LOGIN-123' }) => {
    // ...
  }
);
```

> **Important overload rule:** For tools with **no** parameters, use the 3-arg `server.tool(name, desc, cb)` form. Passing an empty `{}` as the schema in the 4-arg form breaks SDK overload resolution and causes `"handler is not a function"` errors.

---

## How to Launch the MCP Server

### Option 1 — VS Code (automatic, real-life usage)

VS Code 1.99+ reads `.vscode/mcp.json` and **starts the server automatically** when you open the workspace in agent mode. No manual step needed.

```json
// .vscode/mcp.json
{
  "servers": {
    "playwright-agentic": {
      "type": "stdio",
      "command": "node",
      "args": ["${workspaceFolder}/agentic-ai/mcp-server.js"],
      "env": {}
    }
  }
}
```

VS Code spawns `node agentic-ai/mcp-server.js`, wires stdin/stdout, and the 5 tools appear automatically in Copilot's tool list.

### Option 2 — MCP Inspector (debugging / visual demo)

The Inspector is a web UI that acts as a fake AI client — it sends the same JSON-RPC messages Copilot would send and shows you the raw protocol history.

```bash
npx @modelcontextprotocol/inspector node agentic-ai/mcp-server.js
# → open http://localhost:6274
```

In the Inspector you can:
- Click **List Tools** to see all 5 tools with their descriptions and schemas.
- Click any tool → **Run Tool** to call it manually and see the raw JSON-RPC result.
- Watch the **History** panel for every `tools/call` request/response.
- Watch the **Server Notifications** panel for the colored `stderr` log lines.

### Option 3 — Direct process (sanity check)

```bash
node agentic-ai/mcp-server.js
# Server banner logs to stderr; process waits on stdin for JSON-RPC input
node --check agentic-ai/mcp-server.js  # syntax check only
```

---

## Real-Life Usage in VS Code

This is the key practical workflow — you never call tools manually.

```
1. Open VS Code Chat → switch to Agent mode
   (⌘⇧P → "Chat: New Chat" → select "Agent" or use the dropdown)

2. Type a natural language goal:

   "Fetch the LOGIN-123 Jira story, generate a Playwright test from it,
    run it, and fix any failures."

3. Copilot reads your tool descriptions and autonomously chains calls:

   ┌─────────────────────────────────────────────────────────────┐
   │  fetch_jira_story        → reads story + acceptance criteria│
   │        ↓  (result fed into next decision)                   │
   │  generate_test_from_story → emits generated-login.spec.ts  │
   │        ↓                                                    │
   │  run_playwright_tests    → 1/2 failed (broken selector)     │
   │        ↓  (AI sees failure in result, decides to self-heal) │
   │  self_heal               → inspects DOM, patches, reruns ✅ │
   │        ↓                                                    │
   │  report_to_jira          → posts comment to Jira SCRUM-1   │
   └─────────────────────────────────────────────────────────────┘

4. Each tool call returns text that Copilot reads before deciding
   the next step. No scripted orchestration — the AI reasons through it.
```

### The full lifecycle

```
VS Code starts
     │
     ├─► reads .vscode/mcp.json
     ├─► spawns: node agentic-ai/mcp-server.js
     ├─► initialize handshake
     ├─► tools/list  →  Copilot learns all 5 tools
     │
     │   [you type a goal in Chat]
     │
     ├─► tools/call "fetch_jira_story"      → story JSON returned
     ├─► tools/call "generate_test_from_story" → spec file written
     ├─► tools/call "run_playwright_tests"  → FAIL → AI decides to heal
     ├─► tools/call "self_heal"             → .flash-success → .flash.success ✅
     └─► tools/call "report_to_jira"        → Jira comment posted
```

---

## Agentic Scripts Reference

| File | Purpose |
|------|---------|
| `mcp-server.js` | MCP stdio server — exposes the 5 tools to VS Code / Inspector |
| `generate-playwright-test.js` | Reads `data/jira-story.LOGIN-123.json`, writes `tests/ai-generated/generated-login.spec.ts` |
| `self-heal.js` | Runs tests → detects broken selector → launches headless Chromium → inspects DOM → patches test → reruns → posts report to Jira |
| `report-results-to-jira.js` | Reads `tests/ai-generated/test-results/generated-login.json` → posts structured comment to Jira |
| `data/jira-story.LOGIN-123.json` | Mock Jira story with 2 acceptance criteria (AC1 intentionally broken to demo self-heal) |

---

## Key Rules

| Rule | Why |
|------|-----|
| **Never write to `stdout`** | stdout is the JSON-RPC wire; any stray bytes corrupt the protocol |
| **Tool descriptions are your prompt** | The AI reads them verbatim to decide which tool to call and when |
| **Use Zod schemas for parameters** | They become JSON Schema — the AI knows exactly what arguments to pass |
| **`isError: true` ≠ throw** | Return `{ isError: true }` for graceful failures the AI can recover from; `throw` kills the call |
| **3-arg for no-param tools** | `server.tool(name, desc, cb)` — never pass `{}` as schema for parameter-less tools |
| **Server process is long-lived** | VS Code keeps it running for the whole session; `spawnSync` runs child scripts per-call |
| **All logging goes to `stderr`** | Use `process.stderr.write()` — never `console.log()` inside the MCP server |

---

> For the full step-by-step chapter walkthrough see [../docs/AGENTIC_AI.md](../docs/AGENTIC_AI.md).

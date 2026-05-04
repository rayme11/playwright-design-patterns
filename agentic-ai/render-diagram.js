// Script: render-diagram.js
// Purpose: Uses Playwright to render the Mermaid architecture diagram as a PNG image.

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const outputPath = path.join(__dirname, '../docs/pics/agentic-architecture.png');

const mermaidDefinition = `
flowchart TD
    subgraph JIRA["🟦 Jira Cloud"]
      J1["📋 User Stories &\nAcceptance Criteria"]
      J2["🧪 Test Management\n(Xray / Zephyr)"]
    end

    subgraph AGENTIC["🤖 Agentic AI / MCP Server"]
      A1["📥 Fetch Jira Stories"]
      A2["⚙️ Generate / Update\nPlaywright Tests"]
      A3["🔍 Analyze\nTest Failures"]
      A4["📤 Link Results\nBack to Jira"]
    end

    subgraph CODE["💻 Codebase (GitHub)"]
      C1["🧾 Playwright\nTest Code"]
      C2["🔀 Pull Requests"]
    end

    subgraph CI["🚀 CI Pipeline\n(GitHub Actions)"]
      CI1["▶️ Run\nPlaywright Tests"]
      CI2["📊 Publish\nReports"]
    end

    J1 -- "REST API" --> A1
    J2 -- "REST API" --> A1
    A1 --> A2
    A2 -- "Commits / PRs" --> C1
    C1 -- "Triggers CI" --> CI1
    CI1 -- "Results / Artifacts" --> CI2
    CI2 -- "Status / Reports" --> A3
    A3 --> A4
    A4 -- "REST API\n(update status)" --> J2
    CI2 -- "Links / Status" --> C2
    C2 -- "Traceability" --> J1
`;

const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    body {
      background: #ffffff;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 32px;
      font-family: sans-serif;
    }
    #diagram {
      width: 900px;
    }
    h2 {
      text-align: center;
      color: #1e293b;
      font-size: 20px;
      margin-bottom: 24px;
    }
  </style>
</head>
<body>
  <div>
    <h2>Agentic AI Test Orchestration: Jira + MCP + Playwright + CI</h2>
    <div id="diagram" class="mermaid">
${mermaidDefinition}
    </div>
  </div>
  <script>
    mermaid.initialize({ startOnLoad: true, theme: 'default', flowchart: { useMaxWidth: false } });
  </script>
</body>
</html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1400, height: 1200 });
  await page.setContent(html, { waitUntil: 'networkidle' });
  // Wait for mermaid to render
  await page.waitForTimeout(2000);
  await page.screenshot({ path: outputPath, fullPage: true });
  await browser.close();
  console.log(`Architecture diagram saved to: ${outputPath}`);
})();

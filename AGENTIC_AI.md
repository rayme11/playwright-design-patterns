### Step 4: Documenting Agentic Remediation and Real-Life Jira Workflow

#### Agentic Remediation (Summary)
1. The agent (script) generated Playwright tests from a Jira-style user story and acceptance criteria.
2. A test failure was detected due to an incorrect selector.
3. The agent analyzed the error, proposed, and applied a fix.
4. The test was rerun and passed, confirming the fix.

#### Real-Life Scenario in Jira
In a real-world setup:
- **Jira** is the source of truth for requirements, user stories, and acceptance criteria.
- The agent (or CI pipeline) fetches user stories and acceptance criteria from Jira using the REST API.
- Playwright tests are generated or updated to match the acceptance criteria.
- Test results (pass/fail, logs, links to reports) are pushed back to Jira, often as comments, status updates, or via test management plugins (e.g., Xray, Zephyr).
- This creates a closed loop: requirements → code/tests → results → traceability back to requirements.

**Example Workflow:**
1. Product Owner creates a user story in Jira with acceptance criteria.
2. Agent fetches the story, generates/updates Playwright tests.
3. Tests run in CI; failures are analyzed and fixed by the agent or developer.
4. Test results and links to reports are posted back to the Jira story for traceability.

---

### Architecture Diagram

```mermaid
flowchart TD
   A[Jira: User Stories & Acceptance Criteria] -->|REST API| B[Agentic AI / MCP Server]
   B -->|Generates/Updates| C[Playwright Test Code]
   C -->|Runs in| D[CI Pipeline (GitHub Actions)]
   D -->|Test Results| E[Jira (Status/Comments/Traceability)]
   D -->|Reports| F[GitHub Pull Request]
   B -->|Orchestrates| D
```

---

### Next Steps
1. Demonstrate linking test results back to Jira (mock or real API call).
2. Show traceability in both code and Jira.
3. Expand to more complex scenarios (multiple stories, test management plugins, etc.).
4. Continue updating this document as the workflow evolves.

---
#### Agentic Analysis and Fix Example

After running the generated test, the following failure was observed:

> Error: expect(locator).toBeVisible() failed
> Locator: locator('.flash-success')
> Error: element(s) not found

**Agentic Fix:**
- The agent detects that `.flash-success` is not a valid selector (should be `.flash.success`).
- The agent updates the test code to use the correct selector.
- The test is rerun to confirm the fix.

---

# Agentic AI Test Orchestration with MCP, Jira, and Playwright

This section demonstrates how to integrate agentic AI workflows into your Playwright project using the Model Context Protocol (MCP) server, with real-world orchestration across Jira (for user stories and test management) and Playwright (for automation). The goal is to enable AI-driven test analysis, self-healing, automated test/code generation, and traceability from requirements to code.


## What is MCP?
MCP (Model Context Protocol) is an open protocol and server for connecting AI agents to your codebase, tools, and workflows. It enables agents to:
- Analyze code and test failures
- Suggest or apply fixes
- Generate new tests from requirements (e.g., Jira user stories)
- Orchestrate multi-step workflows
- Learn from context and memory

## Real-World Orchestration: Jira + Playwright + MCP

- **Jira**: Source of truth for user stories, acceptance criteria, and test cases (using Jira Test Management or Xray).
- **Playwright**: Automation framework for E2E and integration tests.
- **MCP/Agentic AI**: Orchestrates the flow—fetches user stories from Jira, generates/updates Playwright tests, analyzes failures, and links results back to Jira for traceability.


## Step 1: Set Up MCP Server

### Step-by-Step: Installing and Running MCP Server Locally

**Why:**
Running the MCP server locally allows you to experiment with agentic workflows, code analysis, and test orchestration in a safe, private environment. This is the recommended first step before connecting to cloud or team-wide MCP instances.

#### 1. Prerequisites
- Node.js 18+ (for npm install)
- Docker (optional, for containerized run)

#### 2. Install MCP Server (npm method)
1. Open a terminal in your project or a dedicated folder.
2. Run:
   ```bash
   npx mcp-server
   ```
   - This will download and start the MCP server on port 8080 by default.
   - The first run may take a minute as dependencies are installed.

#### 3. (Alternative) Run MCP Server with Docker
1. If you prefer Docker, run:
   ```bash
   docker run -p 8080:8080 ghcr.io/modelcontext/mcp-server:latest
   ```
   - This pulls the latest MCP server image and runs it on port 8080.

#### 4. Verify MCP Server is Running
- Open your browser and go to: [http://localhost:8080](http://localhost:8080)
- You should see a welcome or status page for MCP server.

#### 5. Next Steps
- Leave the MCP server running in the background while you proceed with agentic workflows.
- You can now connect the MCP VS Code extension or other tools to your local MCP server.

---

2. **(Optional) MCP VS Code Extension**
   - As of this writing, the official Model Context Protocol (MCP) VS Code extension is not yet publicly available on the Visual Studio Marketplace.
   - If you have access via private preview or the Model Context team, follow their instructions for installation (usually via a `.vsix` file or private repo).
   - Otherwise, you can proceed with a script-based agentic workflow using the MCP server and API directly, as shown in the next steps.
   - This approach enables you to experiment with agentic orchestration even before the extension is released.


---

## Script-Based Agentic Workflow

If the VS Code extension is not available, you can still:
- Interact with the MCP server via its REST API or CLI
- Use scripts to fetch Jira user stories, generate Playwright tests, and orchestrate the workflow
- Document and automate the process for traceability

The following steps will demonstrate how to:

### Step 1: Simulate Fetching a Jira User Story

We use a mock Jira user story file in JSON format:

**File:** `agentic-ai/jira-story.LOGIN-123.json`

```json
{
   "key": "LOGIN-123",
   "summary": "User can log in with valid credentials",
   "description": "As a registered user, I want to log in so that I can access my account.",
   "acceptanceCriteria": [
      "AC1: Given I am on the login page, when I enter valid credentials and submit, then I should see the secure area.",
      "AC2: Given I am on the login page, when I enter invalid credentials and submit, then I should see an error message."
   ],
   "testCaseLink": "TEST-456"
}
```

---

### Step 2: Generate a Playwright Test from Acceptance Criteria
---

### Step 3: Simulate a Test Failure and Agentic Fix

In this step, we will:
1. Intentionally break one of the generated test cases (e.g., by changing an expected selector or assertion).
2. Run the test to observe the failure.
3. Demonstrate how an agent (or script) can analyze the failure, suggest a fix, and update the test code.

**Plan:**
- We will modify the generated test to use an incorrect selector for the success message.
- Run the test and capture the failure output.
- Script or document the agentic process for detecting the failure and proposing a fix.

---

We use a Node.js script to read the mock story and generate a Playwright test file:

**File:** `agentic-ai/generate-playwright-test.js`

**Usage:**

```bash
node agentic-ai/generate-playwright-test.js
```

This will create `tests/ai-generated/generated-login.spec.ts` with test cases for each acceptance criterion, including placeholders for implementation.

**Note:** All AI-generated tests are placed in the `tests/ai-generated/` folder for clarity and separation from hand-written tests.

---

---


4. **Connect Jira (for Real-World Integration)**
   - **Why:** Connecting to Jira allows the agent to fetch real user stories, acceptance criteria, and test cases, enabling true requirements-to-code traceability and automation.
   - **How:**
     1. **Create a Jira API Token:**
        - Go to https://id.atlassian.com/manage-profile/security/api-tokens
        - Click "Create API token", give it a name, and copy the token (store it securely).
     2. **Get Your Jira Cloud Domain:**
        - Example: `yourcompany.atlassian.net`
     3. **Set Up Environment Variables:**
        - Store your Jira credentials securely (never commit to source control):
          ```env
          JIRA_BASE_URL=https://yourcompany.atlassian.net
          JIRA_EMAIL=your.email@company.com
          JIRA_API_TOKEN=your_api_token_here
          ```
     4. **Permissions:**
        - The API token should be created by a user with access to the relevant Jira projects and issues.
        - For test management plugins (e.g., Xray, Zephyr), ensure the user has permission to view/manage test cases.
     5. **Agent/Script Configuration:**
        - The agent or integration script should use these credentials to authenticate with the Jira REST API.
        - Example (Node.js):
          ```js
          const auth = Buffer.from(`${process.env.JIRA_EMAIL}:${process.env.JIRA_API_TOKEN}`).toString('base64');
          fetch(`${process.env.JIRA_BASE_URL}/rest/api/3/issue/LOGIN-123`, {
            headers: { 'Authorization': `Basic ${auth}` }
          })
          ```
     6. **Security:**
        - Never commit API tokens or credentials to your repository.
        - Use environment variables or a secure secrets manager.
     7. **Fetching User Stories:**
        - The agent can now fetch user stories, acceptance criteria, and test cases from Jira using the REST API.
        - For example, to get a user story:
          ```http
          GET /rest/api/3/issue/LOGIN-123
          ```
        - To search for issues by JQL:
          ```http
          GET /rest/api/3/search?jql=project=LOGIN AND issuetype=Story
          ```
     8. **Test Management Integration:**
        - If using Xray, Zephyr, or similar, refer to their API docs for fetching/creating test cases and linking them to stories.

   - **Result:**
     - The agent can orchestrate the flow from Jira requirements to Playwright test generation and back, updating Jira with test results and links.

---


## Step 2: Agentic Test Orchestration Example (Jira-Driven)

We'll walk through a scenario where the agent:
- Fetches a user story and acceptance criteria from Jira
- Checks if a matching Playwright test exists (by tag, title, or Jira key)
- If missing, generates a new Playwright test and links it to the Jira story
- If failing, analyzes the error and code, suggests or applies a fix, and updates Jira with the result
- Documents all changes and maintains traceability

---


**Next steps:**
- [x] Step 1: Simulate a Jira user story and acceptance criteria
- [ ] Step 2: Show how the agent fetches this and generates a Playwright test
- [ ] Step 3: Simulate a test failure and agentic fix
- [ ] Step 4: Show how results are linked back to Jira

We will proceed step by step, documenting each phase here and in the codebase.

---

## Step 1: Simulate a Jira User Story and Acceptance Criteria

**Why:**
In a real-world agentic workflow, user stories and acceptance criteria are the source of truth for what needs to be built and tested. By simulating a Jira user story, we can demonstrate how an agent can:
- Fetch requirements from Jira
- Use them to generate or update Playwright tests
- Ensure traceability from requirements to automation

**How:**
We'll create a sample user story and acceptance criteria in a format similar to what you would find in Jira. This will serve as the input for the agentic workflow.

**Example (Jira-style):**

```
Jira Key: LOGIN-123
Summary: User can log in with valid credentials
Description: As a registered user, I want to log in so that I can access my account.
Acceptance Criteria:
   - AC1: Given I am on the login page, when I enter valid credentials and submit, then I should see the secure area.
   - AC2: Given I am on the login page, when I enter invalid credentials and submit, then I should see an error message.
Test Case Link: TEST-456
```

**What this enables:**
- The agent can fetch this story from Jira (or a mock API/file for demo purposes).
- The agent can generate Playwright tests that match the acceptance criteria.
- The agent can tag/link the generated test to the Jira key for traceability.

**Next:**
We will show how the agent fetches this user story and generates a Playwright test that covers the acceptance criteria.

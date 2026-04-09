# Playwright Design Patterns

A batteries-included Playwright automation framework skeleton that demonstrates common design patterns for scalable end-to-end testing.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [Design Patterns](#design-patterns)
- [Configuration](#configuration)

---

## Tech Stack

| Tool | Version | Purpose |
|------|---------|---------|
| [Playwright](https://playwright.dev) | ^1.59.1 | Browser automation & test runner |
| [TypeScript](https://www.typescriptlang.org) | ^5.8.3 | Type-safe test authoring |
| Node.js | ≥ 18 | Runtime |

---

## Project Structure

```
playwright-design-patterns/
├── fixtures/           # Custom Playwright test fixtures
│   └── index.ts        # Extended test object with page fixtures
├── pages/              # Page Object Models (POM pattern)
│   ├── BasePage.ts     # Shared base class for all page objects
│   ├── ExamplePage.ts  # Example page object
│   └── index.ts        # Barrel export
├── tests/              # Test specifications
│   └── example.spec.ts # Example test suite
├── utils/              # Shared test utilities & helpers
│   ├── helpers.ts      # randomString, uniqueEmail, formatDate, sleep
│   └── index.ts        # Barrel export
├── playwright.config.ts # Playwright configuration (browsers, base URL, retries…)
├── tsconfig.json        # TypeScript compiler options
└── package.json         # Dependencies & npm scripts
```

---

## Getting Started

### Prerequisites

- **Node.js ≥ 18** — [nodejs.org](https://nodejs.org)

### Install dependencies

```bash
npm install
```

### Install Playwright browsers

```bash
npx playwright install --with-deps
```

### Set the base URL (optional)

```bash
export BASE_URL=https://your-app.example.com
```

---

## Running Tests

| Command | Description |
|---------|-------------|
| `npm test` | Run all tests headlessly |
| `npm run test:headed` | Run tests with a visible browser |
| `npm run test:debug` | Run tests in Playwright Inspector |
| `npm run test:ui` | Open Playwright UI mode |
| `npm run report` | Open the last HTML report |

Run a single file:

```bash
npx playwright test tests/example.spec.ts
```

Run against a specific browser:

```bash
npx playwright test --project=chromium
```

---

## Design Patterns

### Page Object Model (POM)

Every page is represented by a dedicated class inside `pages/`. Each class:

- **Extends `BasePage`** for shared navigation and utility methods.
- **Declares locators** as `readonly` class properties in the constructor.
- **Exposes semantic methods** (e.g. `goto()`, `getHeadingText()`) so tests read like plain English.

```typescript
// pages/ExamplePage.ts
export class ExamplePage extends BasePage {
  readonly heading: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.locator('h1');
  }

  async goto() { await this.navigate('/'); }
}
```

### Custom Fixtures

Fixtures in `fixtures/index.ts` extend Playwright's built-in `test` object and automatically inject page objects into every test:

```typescript
// fixtures/index.ts
export const test = base.extend<CustomFixtures>({
  examplePage: async ({ page }, use) => {
    const examplePage = new ExamplePage(page);
    await use(examplePage);
  },
});
```

Import `test` and `expect` from `fixtures` in your spec files:

```typescript
import { test, expect } from '../fixtures';

test('heading is visible', async ({ examplePage }) => {
  await examplePage.goto();
  await expect(examplePage.heading).toBeVisible();
});
```

---

## Configuration

Key settings in `playwright.config.ts`:

| Option | Default | Description |
|--------|---------|-------------|
| `testDir` | `./tests` | Where test files live |
| `baseURL` | `$BASE_URL` or `https://example.com` | Root URL for `page.goto('/')` |
| `fullyParallel` | `true` | Run tests across files in parallel |
| `retries` | `2` (CI) / `0` (local) | Automatic retries on failure |
| `trace` | `on-first-retry` | Capture traces for debugging |
| `screenshot` | `only-on-failure` | Capture screenshots on failure |

Browsers configured out-of-the-box: **Chromium**, **Firefox**, **WebKit**, **Mobile Chrome (Pixel 5)**, **Mobile Safari (iPhone 13)**.


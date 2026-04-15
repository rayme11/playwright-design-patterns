/**
 * Data-Driven Login Tests
 *
 * Demonstrates loading test cases from an external JSON file and running
 * each case as a named Playwright test. This pattern separates test logic
 * from test data — add new scenarios by editing the JSON, not this file.
 *
 * Data file: tests/data/login.data.json
 * Page Object: tests/pages/LoginPage.ts
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import loginData from './data/login.data.json';

// ─── Valid user scenarios ─────────────────────────────────────────────────────

for (const user of loginData.validUsers) {
    test(`[valid] ${user.description}`, async ({ page }) => {
        const loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login(user.username, user.password);

        await expect(loginPage.flashSuccess).toBeVisible();
        await expect(loginPage.flashSuccess).toContainText(user.expectedMessage);
        await expect(page).toHaveURL(/secure/);
    });
}

// ─── Invalid user scenarios ───────────────────────────────────────────────────

for (const user of loginData.invalidUsers) {
    test(`[invalid] ${user.description}`, async ({ page }) => {
        const loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login(user.username, user.password);

        await expect(loginPage.flashError).toBeVisible();
        await expect(loginPage.flashError).toContainText(user.expectedMessage);
    });
}

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
import { UserFactory } from './factories/userFactory';

// ─── Valid user scenarios (JSON data) ───────────────────────────────────────

for (const user of loginData.validUsers) {
    test(`[valid] ${user.description} (json)`, async ({ page }) => {
        const loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login(user.username, user.password);
        await expect(loginPage.flashSuccess).toBeVisible();
        await expect(loginPage.flashSuccess).toContainText(user.expectedMessage);
        await expect(page).toHaveURL(/secure/);
    });
}

// ─── Invalid user scenarios (JSON data) ─────────────────────────────────────

for (const user of loginData.invalidUsers) {
    test(`[invalid] ${user.description} (json)`, async ({ page }) => {
        const loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login(user.username, user.password);
        await expect(loginPage.flashError).toBeVisible();
        await expect(loginPage.flashError).toContainText(user.expectedMessage);
    });
}

// ─── Valid user scenarios (with Factory) ────────────────────────────────────

for (const user of loginData.validUsers) {
    test(`[valid] ${user.description} (factory)`, async ({ page }) => {
        const loginPage = new LoginPage(page);
        // Use the factory to build the user object
        const userObj = new UserFactory()
            .withUsername(user.username)
            .withPassword(user.password)
            .withDescription(user.description)
            .withExpectedMessage(user.expectedMessage)
            .build();
        await loginPage.goto();
        await loginPage.login(userObj.username, userObj.password);
        await expect(loginPage.flashSuccess).toBeVisible();
        await expect(loginPage.flashSuccess).toContainText(userObj.expectedMessage);
        await expect(page).toHaveURL(/secure/);
    });
}

// ─── Invalid user scenarios (with Factory) ──────────────────────────────────

for (const user of loginData.invalidUsers) {
    test(`[invalid] ${user.description} (factory)`, async ({ page }) => {
        const loginPage = new LoginPage(page);
        const userObj = new UserFactory()
            .withUsername(user.username)
            .withPassword(user.password)
            .withDescription(user.description)
            .withExpectedMessage(user.expectedMessage)
            .build();
        await loginPage.goto();
        await loginPage.login(userObj.username, userObj.password);
        // Defensive check for expectedMessage
        if (!userObj.expectedMessage) {
            throw new Error(`Test data error: expectedMessage is missing for user: ${JSON.stringify(userObj)}`);
        }
        await expect(loginPage.flashError).toBeVisible();
        await expect(loginPage.flashError).toContainText(userObj.expectedMessage);
    });
}

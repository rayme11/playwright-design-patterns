import { test as base, expect } from '@playwright/test';
import loginData from '../data/login.data.json';

// ─── Types ────────────────────────────────────────────────────────────────────

export type LoginUser = {
    description: string;
    username: string;
    password: string;
    expectedMessage: string;
};

export type LoginDataFixture = {
    validUsers: LoginUser[];
    invalidUsers: LoginUser[];
};

// ─── Fixture ──────────────────────────────────────────────────────────────────

/**
 * loginDataFixture
 *
 * Loads login test cases from tests/data/login.data.json and makes them
 * available to any test that declares `{ loginDataFixture }`.
 * Swap the JSON file for an API call or DB query here without touching tests.
 */
const test = base.extend<{ loginDataFixture: LoginDataFixture }>({
    loginDataFixture: async ({}, use) => {
        await use(loginData);
    }
});

export { test, expect };

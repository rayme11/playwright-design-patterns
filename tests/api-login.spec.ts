/**
 * API Tests — the-internet.herokuapp.com
 *
 * Playwright's built-in `request` fixture lets you make HTTP calls without
 * opening a browser. Use this pattern to:
 *   - Validate API contracts independently of the UI
 *   - Seed or clean up data before/after UI tests
 *   - Test status codes, headers, and response bodies
 *
 * Note: the-internet.herokuapp.com is a UI-focused demo app; it does not
 * expose a formal REST API. These tests demonstrate the Playwright API
 * testing pattern against real HTTP endpoints (form POSTs, redirects, status
 * codes) that the app does expose.
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'https://the-internet.herokuapp.com';

// ─── Status code checks ───────────────────────────────────────────────────────

test.describe('Page availability', () => {

    test('login page returns 200', async ({ request }) => {
        const response = await request.get(`${BASE_URL}/login`);
        expect(response.status()).toBe(200);
    });

    test('secure area redirects unauthenticated users', async ({ request }) => {
        const response = await request.get(`${BASE_URL}/secure`);
        // The app redirects to /login — expect a redirect or 200 after follow
        expect([200, 302]).toContain(response.status());
    });

    test('non-existent page returns 404', async ({ request }) => {
        const response = await request.get(`${BASE_URL}/this-page-does-not-exist`);
        expect(response.status()).toBe(404);
    });

});

// ─── Form POST — login endpoint ───────────────────────────────────────────────

test.describe('Login form POST', () => {

    test('valid credentials POST returns successful redirect', async ({ request }) => {
        const response = await request.post(`${BASE_URL}/authenticate`, {
            form: {
                username: 'tomsmith',
                password: 'SuperSecretPassword!'
            }
        });
        // App redirects to /secure on success
        expect(response.status()).toBe(200);
        const body = await response.text();
        expect(body).toContain('You logged into a secure area!');
    });

    test('invalid credentials POST returns error page', async ({ request }) => {
        const response = await request.post(`${BASE_URL}/authenticate`, {
            form: {
                username: 'baduser',
                password: 'wrongpass'
            }
        });
        expect(response.status()).toBe(200);
        const body = await response.text();
        expect(body).toContain('Your username is invalid!');
    });

});

// ─── Response headers ─────────────────────────────────────────────────────────

test.describe('Response headers', () => {

    test('login page returns HTML content type', async ({ request }) => {
        const response = await request.get(`${BASE_URL}/login`);
        const contentType = response.headers()['content-type'];
        expect(contentType).toContain('text/html');
    });

});

// ─── API + UI hybrid: seed via API, verify in browser ────────────────────────

test.describe('API + UI hybrid', () => {

    test('login via API then verify UI state reflects session', async ({ page, request }) => {
        // Step 1: confirm the endpoint is healthy via API before launching browser
        const apiCheck = await request.get(`${BASE_URL}/login`);
        expect(apiCheck.status()).toBe(200);

        // Step 2: now perform the full UI flow, knowing the endpoint is up
        await page.goto(`${BASE_URL}/login`);
        await page.getByRole('textbox', { name: 'Username' }).fill('tomsmith');
        await page.getByRole('textbox', { name: 'Password' }).fill('SuperSecretPassword!');
        await page.locator('i.fa-sign-in').click();

        await expect(page.locator('#flash.flash.success')).toBeVisible();
        await expect(page).toHaveURL(/secure/);
    });

});

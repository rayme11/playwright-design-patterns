import { test, expect } from '@playwright/test';

test.use({ storageState: 'storageState.local.json' });

test('should reuse localStorage auth state', async ({ page }) => {
  // Must navigate to the same origin used in global-setup to access its localStorage
  await page.goto('https://the-internet.herokuapp.com');
  // Check that the auth token and user are present in localStorage
  const authToken = await page.evaluate(() => localStorage.getItem('auth_token'));
  const user = await page.evaluate(() => localStorage.getItem('user'));
  expect(authToken).toBe('demo-token-123');
  expect(user).toBe(JSON.stringify({ name: 'Demo User', role: 'admin' }));
  // Optionally, simulate a protected page
  // ...
});

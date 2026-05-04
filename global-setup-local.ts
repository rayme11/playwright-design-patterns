import { chromium } from '@playwright/test';

// This global setup simulates a login by setting a value in localStorage.
// This pattern works for apps that use localStorage/sessionStorage for auth (e.g., JWT, SPA, etc.)
async function globalSetup() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  // Go to a blank page or your app's root
  await page.goto('about:blank');
  // Simulate a login by setting a token in localStorage
  await page.evaluate(() => {
    localStorage.setItem('auth_token', 'demo-token-123');
    localStorage.setItem('user', JSON.stringify({ name: 'Demo User', role: 'admin' }));
  });
  // Save storage state (includes localStorage)
  await page.context().storageState({ path: 'storageState.local.json' });
  await browser.close();
}

export default globalSetup;

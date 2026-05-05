import { chromium } from '@playwright/test';

async function globalSetup() {
  const browser = await chromium.launch();

  // --- Session-cookie auth state (the-internet.herokuapp.com) ---
  const page = await browser.newPage();
  await page.goto('https://the-internet.herokuapp.com/login');
  await page.fill('input[name="username"]', 'tomsmith');
  await page.fill('input[name="password"]', 'SuperSecretPassword!');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/secure');
  await page.waitForSelector('a.button[href="/logout"]');
  console.log('Login successful, saving storage state...');
  await page.context().storageState({ path: 'storageState.json' });

  // --- localStorage auth state (SPA/JWT demo) ---
  // Note: localStorage is origin-scoped; about:blank is blocked on Linux/CI.
  // Use the same real origin that the test will navigate to.
  const localPage = await browser.newPage();
  await localPage.goto('https://the-internet.herokuapp.com');
  await localPage.evaluate(() => {
    localStorage.setItem('auth_token', 'demo-token-123');
    localStorage.setItem('user', JSON.stringify({ name: 'Demo User', role: 'admin' }));
  });
  await localPage.context().storageState({ path: 'storageState.local.json' });
  console.log('localStorage auth state saved.');

  await browser.close();
}

export default globalSetup;

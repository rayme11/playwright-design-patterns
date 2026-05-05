import { chromium } from '@playwright/test';

async function globalSetup() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('https://the-internet.herokuapp.com/login');
  await page.fill('input[name="username"]', 'tomsmith');
  await page.fill('input[name="password"]', 'SuperSecretPassword!');
  await page.click('button[type="submit"]');
  // Wait for navigation to the secure area to confirm login
  await page.waitForURL('**/secure');
  // Wait for the logout button to ensure login is complete
  await page.waitForSelector('a.button[href="/logout"]');
  console.log('Login successful, saving storage state...');
  // Save authentication state to file
  await page.context().storageState({ path: 'storageState.json' });
  await browser.close();
}

export default globalSetup;

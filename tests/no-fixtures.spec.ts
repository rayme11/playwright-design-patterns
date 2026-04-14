// Simple test to demonsrate that tests can run without fixtures. 
// But it is not recommended to do so, 
// as it will not work with the default configuration of Playwright Test, which expects a `page` fixture to be available.

import { test, expect, chromium } from '@playwright/test';

test('Sign In button is Visible', async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();


  await page.goto('https://the-internet.herokuapp.com/login');

  const loginButton = page.locator('i.fa-sign-in');
  await expect(loginButton).toBeVisible();

  await browser.close();
});
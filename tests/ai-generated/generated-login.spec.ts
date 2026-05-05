/**
 * Jira Key: LOGIN-123
 * Summary: User can log in with valid credentials
 * Description: As a registered user, I want to log in so that I can access my account.
 * Acceptance Criteria: 
 *   - AC1: Given I am on the login page, when I enter valid credentials and submit, then I should see the secure area.
 *   - AC2: Given I am on the login page, when I enter invalid credentials and submit, then I should see an error message.
 * Test Case Link: TEST-456
 */
import { test, expect } from '@playwright/test';

test.describe('[Jira: LOGIN-123] User can log in with valid credentials', () => {
  test('AC1: Given I am on the login page, when I enter valid credentials and submit, then I should see the secure area', async ({ page }) => {
    // TODO: Implement valid login scenario
    // Example:
      await page.goto('https://the-internet.herokuapp.com/login');
      await page.fill('#username', 'tomsmith');
      await page.fill('#password', 'SuperSecretPassword!');
      await page.click('button[type=submit]');
      await expect(page).toHaveURL(/secure/);
    // Intentionally broken selector — self-healing agent will detect and fix this:
    await expect(page.locator('.flash.success')).toBeVisible();
  });

  test('AC2: Given I am on the login page, when I enter invalid credentials and submit, then I should see an error message', async ({ page }) => {
    // TODO: Implement invalid login scenario
    // Example:
    // await page.goto('https://the-internet.herokuapp.com/login');
    // await page.fill('#username', 'invalid');
    // await page.fill('#password', 'invalid');
    // await page.click('button[type=submit]');
    // await expect(page.locator('.flash.error')).toBeVisible();
  });
});

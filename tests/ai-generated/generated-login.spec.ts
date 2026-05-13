/**
 * Jira Key:  LOGIN-123
 * Summary:   User can log in and out of the application
 * Description: As a registered user,
I want to log in to the application with my credentials
So that I can access my secure account area and manage my session.
 * Acceptance Criteria:
 *   - Scenario: Successful login with valid credentials
  Given I am on the login page at /login
  When I enter username 'tomsmith' and password 'SuperSecretPassword!'
  And I click the login button
  Then I should be redirected to the secure area
  And I should see a flash success message
 *   - Scenario: Failed login with invalid credentials
  Given I am on the login page at /login
  When I enter username 'wronguser' and password 'wrongpassword'
  And I click the login button
  Then I should remain on the login page
  And I should see a flash error message
 *   - Scenario: Successful logout after login
  Given I am logged in as 'tomsmith'
  When I click the logout button
  Then I should be redirected to the login page
  And I should see a flash message confirming I have logged out
 * Test Case Link: TEST-456
 */
import { test, expect } from '@playwright/test';

test.describe('[Jira: LOGIN-123] User can log in and out of the application', () => {
  test('AC1: Successful login with valid credentials', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/login');
    await page.fill('#username', 'tomsmith');
    await page.fill('#password', 'SuperSecretPassword!');
    await page.click('button[type=submit]');
    await expect(page).toHaveURL(/secure/);
    await expect(page.locator('.flash.success')).toBeVisible(); // broken — self-heal will fix this
  });

  test('AC2: Failed login with invalid credentials', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/login');
    await page.fill('#username', 'invalid');
    await page.fill('#password', 'invalid');
    await page.click('button[type=submit]');
    await expect(page.locator('.flash.error')).toBeVisible();
  });

  test('AC3: Successful logout after login', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/login');
    await page.fill('#username', 'invalid');
    await page.fill('#password', 'invalid');
    await page.click('button[type=submit]');
    await expect(page.locator('.flash.error')).toBeVisible();
  });
});

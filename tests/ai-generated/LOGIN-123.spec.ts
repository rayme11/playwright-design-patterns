import { test, expect } from '@playwright/test';

/**
 * Jira Key: LOGIN-123
 * Summary: User can log in and out of the application
 * Scenarios:
 * - Successful login with valid credentials
 * - Failed login with invalid credentials
 * - Successful logout after login
 */

test.describe('[LOGIN-123] User can log in and out of the application', () => {

  test('Successful login with valid credentials', async ({ page }) => {
    // Given I am on the login page at /login
    await page.goto('https://the-internet.herokuapp.com/login');

    // When I enter username 'tomsmith' and password 'SuperSecretPassword!'
    await page.fill('#username', 'tomsmith');
    await page.fill('#password', 'SuperSecretPassword!');
    // And I click the login button
    await page.click('button[type=submit]');

    // Then I should be redirected to the secure area
    await expect(page).toHaveURL('https://the-internet.herokuapp.com/secure');
    // And I should see a flash success message
    await expect(page.locator('.flash.success')).toBeVisible();
  });

  test('Failed login with invalid credentials', async ({ page }) => {
    // Given I am on the login page at /login
    await page.goto('https://the-internet.herokuapp.com/login');

    // When I enter username 'wronguser' and password 'wrongpassword'
    await page.fill('#username', 'wronguser');
    await page.fill('#password', 'wrongpassword');
    // And I click the login button
    await page.click('button[type=submit]');

    // Then I should remain on the login page
    await expect(page).toHaveURL('https://the-internet.herokuapp.com/login');
    // And I should see a flash error message
    await expect(page.locator('.flash.error')).toBeVisible();
  });

  test('Successful logout after login', async ({ page }) => {
    // Given I am logged in as 'tomsmith'
    await page.goto('https://the-internet.herokuapp.com/login');
    await page.fill('#username', 'tomsmith');
    await page.fill('#password', 'SuperSecretPassword!');
    await page.click('button[type=submit]');
    await expect(page).toHaveURL('https://the-internet.herokuapp.com/secure');

    // When I click the logout button
    await page.click('a[href="/logout"]');

    // Then I should be redirected to the login page
    await expect(page).toHaveURL('https://the-internet.herokuapp.com/login');
    // And I should see a flash message confirming I have logged out
    await expect(page.locator('#flash')).toContainText('You logged out of the secure area!');
  });

});
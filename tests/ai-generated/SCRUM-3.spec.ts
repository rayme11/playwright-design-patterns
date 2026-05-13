import { test, expect } from '@playwright/test';

/**
 * Jira Key: SCRUM-3
 * Summary: Checkboxes: users should be able to toggle checkbox state
 * Scenarios:
 * - AC1: Toggle unchecked checkbox 1 to checked state and verify it is checked
 * - AC2: Toggle checked checkbox 2 to unchecked state and verify it is unchecked
 */

test.describe('[SCRUM-3] Checkboxes: users should be able to toggle checkbox state', () => {

  test('AC1: Toggle unchecked checkbox 1 to checked state and verify it is checked', async ({ page }) => {
    // Given the user is on the checkboxes page
    await page.goto('https://the-internet.herokuapp.com/checkboxes');

    // When the user toggles checkbox 1 to checked state
    const checkbox1 = page.locator('input[type="checkbox"]').first();
    await checkbox1.check();

    // Then verify checkbox 1 is checked
    await expect(checkbox1).toBeChecked();
  });

  test('AC2: Toggle checked checkbox 2 to unchecked state and verify it is unchecked', async ({ page }) => {
    // Given the user is on the checkboxes page
    await page.goto('https://the-internet.herokuapp.com/checkboxes');

    // When the user toggles checkbox 2 to unchecked state
    const checkbox2 = page.locator('input[type="checkbox"]').nth(1);
    await checkbox2.uncheck();

    // Then verify checkbox 2 is unchecked
    await expect(checkbox2).not.toBeChecked();
  });

});
import { test, expect } from '@playwright/test';

/**
 * Jira Key: SCRUM-4
 * Summary: As a user, I want to select options from a dropdown so that I can choose between available values.
 * Scenarios:
 * - AC1: Select "Option 1" from the dropdown and verify it is the selected option
 * - AC2: Select "Option 2" from the dropdown and verify it is the selected option
 * - AC3: Verify the default placeholder option is disabled and cannot be selected
 */

test.describe('[SCRUM-4] As a user, I want to select options from a dropdown so that I can choose between available values.', () => {

  test('AC1: Select "Option 1" from the dropdown and verify it is the selected option', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/dropdown');
    await page.selectOption('#dropdown', '1');
    const selectedOption = await page.$eval('#dropdown', el => el.value);
    expect(selectedOption).toBe('1');
  });

  test('AC2: Select "Option 2" from the dropdown and verify it is the selected option', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/dropdown');
    await page.selectOption('#dropdown', '2');
    const selectedOption = await page.$eval('#dropdown', el => el.value);
    expect(selectedOption).toBe('2');
  });

  test('AC3: Verify the default placeholder option is disabled and cannot be selected', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/dropdown');
    const isDisabled = await page.$eval('#dropdown option[value=""]', el => el.disabled);
    expect(isDisabled).toBe(true);
  });

});
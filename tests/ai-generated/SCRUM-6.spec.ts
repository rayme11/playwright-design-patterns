/**
 * Jira Key: SCRUM-6
 * Summary: User can select options from a dropdown and see the selected value
 * 
 * Scenarios:
 * - Scenario 1: Select Option 1 from the dropdown
 * - Scenario 2: Select Option 2 from the dropdown
 * - Scenario 3: Dropdown has a default disabled option
 */

import { test, expect } from '@playwright/test';

test.describe('[SCRUM-6] User can select options from a dropdown and see the selected value', () => {
  test('Select Option 1 from the dropdown', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/dropdown');
    
    await page.selectOption('#dropdown', { label: 'Option 1' });
    
    const selectedValue = await page.locator('#dropdown').inputValue();
    expect(selectedValue).toBe('1');
    const selectedText = await page.locator('#dropdown option:checked').textContent();
    expect(selectedText).toBe('Option 1');
  });

  test('Select Option 2 from the dropdown', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/dropdown');
    
    await page.selectOption('#dropdown', { label: 'Option 2' });
    
    const selectedValue = await page.locator('#dropdown').inputValue();
    expect(selectedValue).toBe('2');
    const selectedText = await page.locator('#dropdown option:checked').textContent();
    expect(selectedText).toBe('Option 2');
  });

  test('Dropdown has a default disabled option', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/dropdown');
    
    const disabledOption = page.locator('#dropdown option[disabled]');
    await expect(disabledOption).toBeAttached();
    const disabledOptionText = await disabledOption.textContent();
    expect(disabledOptionText).toBe('Please select an option');
  });
});
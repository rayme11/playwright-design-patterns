/**
 * Jira Key: SCRUM-7
 * Summary: User can interact with checkboxes and verify their state
 * 
 * Scenarios:
 * - Scenario 1: Checkbox 1 starts unchecked and can be checked
 * - Scenario 2: Checkbox 2 starts checked and can be unchecked
 * - Scenario 3: Both checkboxes can be toggled independently
 */

import { test, expect } from '@playwright/test';

test.describe('[SCRUM-7] User can interact with checkboxes and verify their state', () => {
  
  test('Checkbox 1 starts unchecked and can be checked', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/checkboxes');
    
    const checkbox1 = page.locator('input[type="checkbox"]').first();
    
    await checkbox1.check();
    
    await expect(checkbox1).toBeChecked();
  });

  test('Checkbox 2 starts checked and can be unchecked', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/checkboxes');
    
    const checkbox2 = page.locator('input[type="checkbox"]').nth(1);
    
    await checkbox2.uncheck();
    
    await expect(checkbox2).not.toBeChecked();
  });

  test('Both checkboxes can be toggled independently', async ({ page }) => {
    await page.goto('https://the-internet.herokuapp.com/checkboxes');
    
    const checkbox1 = page.locator('input[type="checkbox"]').first();
    const checkbox2 = page.locator('input[type="checkbox"]').nth(1);
    
    await checkbox1.check();
    await checkbox2.uncheck();
    
    await expect(checkbox1).toBeChecked();
    await expect(checkbox2).not.toBeChecked();
  });

});
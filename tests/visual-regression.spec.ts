import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';

// Visual regression: full page screenshot

test('login page visual regression (full page)', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.goto();
	// Take a full-page screenshot and compare to baseline
	await expect(page).toHaveScreenshot('login-page.png', { fullPage: true });
});

// Visual regression: login form only

test('login form visual regression (element only)', async ({ page }) => {
	await page.goto('https://the-internet.herokuapp.com/login');
	const form = page.locator('form');
	await expect(form).toHaveScreenshot('login-form.png');
});

// Note: On first run, baseline images are created. On subsequent runs, Playwright will compare new screenshots to the baseline and fail if there are differences.

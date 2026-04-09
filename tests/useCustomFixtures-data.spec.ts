import { test, expect } from "./fixtures/customData";
import { LoginPage } from "./pages/LoginPage";

test('Sign in with bad credentials', async ({ customData, page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(customData.badData.username, customData.badData.password);

    await expect(loginPage.flashError).toBeVisible();
    await expect(loginPage.flashError).toContainText('Your username is invalid!');
});

test('Sign in with good credentials', async ({ customData, page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(customData.goodData.username, customData.goodData.password);

    await expect(loginPage.flashSuccess).toBeVisible();
    await expect(loginPage.flashSuccess).toContainText('You logged into a secure area!');
});
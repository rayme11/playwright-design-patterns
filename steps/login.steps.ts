import { Given, When, Then, Before, After } from '@cucumber/cucumber';
import { chromium, Browser, BrowserContext, Page } from '@playwright/test';
import { expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

let browser: Browser;
let context: BrowserContext;
let page: Page;
let loginPage: LoginPage;

Before(async () => {
  browser = await chromium.launch();
  context = await browser.newContext({
    baseURL: process.env['BASE_URL'] ?? 'http://localhost:3000',
  });
  page = await context.newPage();
  loginPage = new LoginPage(page);
});

After(async () => {
  await context.close();
  await browser.close();
});

Given('I am on the login page', async () => {
  await loginPage.goto();
});

When(
  'I enter username {string} and password {string}',
  async (username: string, password: string) => {
    await loginPage.usernameInput.fill(username);
    await loginPage.passwordInput.fill(password);
  },
);

When('I click the login button', async () => {
  await loginPage.submitButton.click();
});

Then('I should see a welcome message', async () => {
  await expect(loginPage.welcomeMessage).toBeVisible();
});

Then(
  'I should see an error message {string}',
  async (expectedMessage: string) => {
    await expect(loginPage.errorMessage).toBeVisible();
    const actualText = await loginPage.getErrorText();
    expect(actualText).toContain(expectedMessage);
  },
);

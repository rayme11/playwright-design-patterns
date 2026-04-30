import { test, expect } from '@playwright/test';
import { UserFactory } from './factories/userFactory';
import { LoginPage } from './pages/LoginPage';

// Example: Using the Factory/Builder for login test data

test('login with factory-generated valid user', async ({ page }) => {
  const user = new UserFactory().build();
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login(user.username, user.password);
  await expect(loginPage.flashSuccess).toBeVisible();
});

test('login with factory-generated invalid user', async ({ page }) => {
  const user = new UserFactory()
    .withUsername('baduser')
    .withPassword('wrongpass')
    .withDescription('invalid user')
    .withExpectedMessage('Your username is invalid!')
    .build();
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login(user.username, user.password);
  await expect(loginPage.flashError).toContainText(user.expectedMessage!);
});

import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import { ICustomWorld } from '../support/world';

// ─── Given ───────────────────────────────────────────────────────────────────

Given('the user is on the login page', async function () {
    // @ts-ignore: 'this' is not used
    await this.loginPage!.goto();
});

// ─── When ────────────────────────────────────────────────────────────────────

// username and password are injected from the Examples table in the .feature file
When('the user enters username {string} and password {string}', async function (username: string, password: string) {
    // @ts-ignore: 'this' is not used
    await this.loginPage!.login(username, password);
});

// ─── Then ────────────────────────────────────────────────────────────────────

Then('the user should be redirected to the dashboard', async function () {
    // @ts-ignore: 'this' is not used
    await expect(this.loginPage!.flashSuccess).toBeVisible();
    await expect(this.loginPage!.flashSuccess).toContainText('You logged into a secure area!');
});

Then('an error message should be displayed', async function () {
    // @ts-ignore: 'this' is not used
    await expect(this.loginPage!.flashError).toBeVisible();
    await expect(this.loginPage!.flashError).toContainText('Your username is invalid!');
});

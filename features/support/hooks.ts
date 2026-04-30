
import { Before, After } from '@cucumber/cucumber';
import { chromium } from '@playwright/test';
import process from 'process';

import { LoginPage } from '../../tests/pages/LoginPage';

// Launch a new browser + page before each scenario

Before(async function () {
    // @ts-ignore: 'this' is used by Cucumber runtime
    this.browser = await chromium.launch({ headless: process.env.HEADLESS !== 'false' });
    this.context = await this.browser.newContext();
    this.page = await this.context.newPage();
    this.loginPage = new LoginPage(this.page);
});

// Clean up after each scenario

After(async function () {
    // @ts-ignore: 'this' is used by Cucumber runtime
    await this.page?.close();
    await this.context?.close();
    await this.browser?.close();
});

import { Before, After } from '@cucumber/cucumber';
import { chromium } from '@playwright/test';
import { ICustomWorld } from './world';

import { LoginPage } from '../../tests/pages/LoginPage';

// Launch a new browser + page before each scenario
Before(async function (this: ICustomWorld) {
    this.browser = await chromium.launch({ headless: true });
    this.context = await this.browser.newContext();
    this.page = await this.context.newPage();
    this.loginPage = new LoginPage(this.page);
});

// Clean up after each scenario
After(async function (this: ICustomWorld) {
    await this.page?.close();
    await this.context?.close();
    await this.browser?.close();
});

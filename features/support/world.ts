import { setWorldConstructor, World, IWorldOptions } from '@cucumber/cucumber';
import { Browser, BrowserContext, Page } from '@playwright/test';
import { LoginPage } from '../../tests/pages/LoginPage';

// ICustomWorld extends Cucumber's World and adds Playwright browser/page instances
export interface ICustomWorld extends World {
    browser?: Browser;
    context?: BrowserContext;
    page?: Page;
    loginPage?: LoginPage;
}

export class CustomWorld extends World implements ICustomWorld {
    browser?: Browser;
    context?: BrowserContext;
    page?: Page;
    loginPage?: LoginPage;

    constructor(options: IWorldOptions) {
        super(options);
    }
}

setWorldConstructor(CustomWorld);

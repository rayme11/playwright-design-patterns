import { Page } from '@playwright/test';

export class LoginPage {
    private page: Page;

    constructor(page: Page) {
        this.page = page;
    }

    async goto() {
        await this.page.goto('https://the-internet.herokuapp.com/login');
    }

    async login(username: string, password: string) {
        await this.page.getByRole('textbox', { name: 'Username' }).fill(username);
        await this.page.getByRole('textbox', { name: 'Password' }).fill(password);
        await this.page.locator('i.fa-sign-in').click();
    }

    get flashError() {
        return this.page.locator('#flash.flash.error');
    }

    get flashSuccess() {
        return this.page.locator('#flash.flash.success');
    }
}

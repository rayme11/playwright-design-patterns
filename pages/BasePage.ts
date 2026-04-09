import { Page, Locator } from '@playwright/test';

/**
 * BasePage provides common methods shared across all page objects.
 * Every page-specific class should extend this base class.
 */
export abstract class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /** Navigate to the given path relative to the configured baseURL. */
  async navigate(path: string = '/'): Promise<void> {
    await this.page.goto(path);
  }

  /** Wait for a specific locator to become visible. */
  async waitForVisible(locator: Locator): Promise<void> {
    await locator.waitFor({ state: 'visible' });
  }

  /** Retrieve the current page title. */
  async getTitle(): Promise<string> {
    return this.page.title();
  }

  /** Take a screenshot and save it with the given name. */
  async takeScreenshot(name: string): Promise<void> {
    await this.page.screenshot({ path: `test-results/${name}.png` });
  }
}

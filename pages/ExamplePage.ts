import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * ExamplePage demonstrates the Page Object Model pattern.
 * Replace this with your own application-specific page objects.
 */
export class ExamplePage extends BasePage {
  readonly heading: Locator;
  readonly moreInfoLink: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.locator('h1');
    this.moreInfoLink = page.getByRole('link', { name: 'More information' });
  }

  /** Navigate to the example page. */
  async goto(): Promise<void> {
    await this.navigate('/');
  }

  /** Return the text content of the main heading. */
  async getHeadingText(): Promise<string | null> {
    return this.heading.textContent();
  }
}

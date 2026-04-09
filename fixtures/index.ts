import { test as base } from '@playwright/test';
import { ExamplePage } from '../pages';

/**
 * Custom fixture type declarations.
 * Add your own fixtures here and export them from this file.
 */
type CustomFixtures = {
  examplePage: ExamplePage;
};

/**
 * Extended test object with custom fixtures.
 * Import `test` and `expect` from this file in your spec files
 * to get access to all custom fixtures.
 */
export const test = base.extend<CustomFixtures>({
  examplePage: async ({ page }, use) => {
    const examplePage = new ExamplePage(page);
    await use(examplePage);
  },
});

export { expect } from '@playwright/test';

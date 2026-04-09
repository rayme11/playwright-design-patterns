import { test, expect } from '../fixtures';

test.describe('Example', () => {
  test('page has a title', async ({ examplePage }) => {
    await examplePage.goto();
    const title = await examplePage.getTitle();
    expect(title).toBeTruthy();
  });

  test('page has a heading', async ({ examplePage }) => {
    await examplePage.goto();
    await expect(examplePage.heading).toBeVisible();
  });
});

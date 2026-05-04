import { test } from '@playwright/test';

test.skip('should be logged in via global setup (herokuapp limitation)', async () => {
  // This test is skipped because the-internet.herokuapp.com uses server-side sessions
  // that are not portable across browser contexts. Playwright's global setup works for
  // most modern apps (JWT/localStorage), but not for classic server-side session cookies.
  // See README for more details.
});


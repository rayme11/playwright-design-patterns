import { test } from '@playwright/test';
import { Actor, Login, SeeLoginSuccess } from './screenplay';

test('actor logs in successfully (screenplay)', async ({ page }) => {
  const actor = Actor.named('Alice').whoCan(page);
  await actor.attemptsTo(Login.with('tomsmith', 'SuperSecretPassword!'));
  await actor.should(SeeLoginSuccess.message('You logged into a secure area!'));
});

// Minimal Screenplay Pattern abstractions for Playwright
// Minimal Screenplay Pattern abstractions for Playwright
// Minimal Screenplay Pattern abstractions for Playwright

// Screenplay Pattern abstractions for Playwright
// Minimal Screenplay Pattern abstractions for Playwright
import { Page, expect } from '@playwright/test';

export class Actor {
  name: string;
  page: Page;

  constructor(name: string, page: Page) {
    this.name = name;
    this.page = page;
  }

  static named(name: string) {
    return {
      whoCan: (page: Page) => new Actor(name, page)
    };
  }

  async attemptsTo(task: Task) {
    await task.performAs(this);
  }

  async should(question: Question) {
    await question.answeredBy(this);
  }
}

export interface Task {
  performAs: (...args: any[]) => Promise<void>;
}

export interface Question {
  answeredBy: (...args: any[]) => Promise<void>;
}

// Example Task: Login
export class Login implements Task {
  username: string;
  password: string;
  constructor(username: string, password: string) {
    this.username = username;
    this.password = password;
  }
  async performAs(actor: Actor) {
    await actor.page.goto('https://the-internet.herokuapp.com/login');
    await actor.page.getByRole('textbox', { name: 'Username' }).fill(this.username);
    await actor.page.getByRole('textbox', { name: 'Password' }).fill(this.password);
    await actor.page.locator('i.fa-sign-in').click();
  }
  static with(username: string, password: string) {
    return new Login(username, password);
  }
}

// Example Question: See login success message
export class SeeLoginSuccess implements Question {
  expected: string;
  constructor(expected: string) {
    this.expected = expected;
  }
  async answeredBy(actor: Actor) {
    await expect(actor.page.locator('#flash.flash.success')).toContainText(this.expected);
  }
  static message(expected: string) {
    return new SeeLoginSuccess(expected);
  }
}

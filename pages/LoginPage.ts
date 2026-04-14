import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * LoginPage encapsulates selectors and actions for the login page.
 */
export class LoginPage extends BasePage {
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;
  readonly welcomeMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.usernameInput = page.getByLabel('Username');
    this.passwordInput = page.getByLabel('Password');
    this.submitButton = page.getByRole('button', { name: /log in/i });
    this.errorMessage = page.locator('[data-testid="error-message"]');
    this.welcomeMessage = page.locator('[data-testid="welcome-message"]');
  }

  /** Navigate to the login page. */
  async goto(): Promise<void> {
    await this.navigate('/login');
  }

  /** Fill in credentials and submit the login form. */
  async login(username: string, password: string): Promise<void> {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  /** Return the text of the displayed error message. */
  async getErrorText(): Promise<string | null> {
    return this.errorMessage.textContent();
  }

  /** Return the text of the welcome message shown after successful login. */
  async getWelcomeText(): Promise<string | null> {
    return this.welcomeMessage.textContent();
  }
}

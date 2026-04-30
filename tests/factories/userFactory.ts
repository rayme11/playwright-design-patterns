// Factory/Builder for login user test data

export type LoginUser = {
  username: string;
  password: string;
  description?: string;
  expectedMessage?: string;
};

export class UserFactory {
  private user: LoginUser;

  constructor() {
    this.user = {
      username: 'tomsmith',
      password: 'SuperSecretPassword!',
      description: 'default valid user',
      expectedMessage: 'You logged into a secure area!'
    };
  }

  withUsername(username: string) {
    this.user.username = username;
    return this;
  }

  withPassword(password: string) {
    this.user.password = password;
    return this;
  }

  withDescription(description: string) {
    this.user.description = description;
    return this;
  }

  withExpectedMessage(msg: string) {
    this.user.expectedMessage = msg;
    return this;
  }

  build(): LoginUser {
    return { ...this.user };
  }
}

import { test as base, expect } from '@playwright/test';

type CustomFixtures = {
    customData: { badData: { username: string; password: string }; goodData: { username: string; password: string } };
};

const test = base.extend<CustomFixtures>({
    // Define a custom fixture named "customData"
    // eslint-disable-next-line no-empty-pattern
    customData: async ({}, use) => {
        // You can perform any setup here, such as fetching data from an API or reading from a file
        // data sample was taken from https://the-internet.herokuapp.com/login
        const badData = {
            username: 'testuser',
            password: 'password123'
        };

        const goodData = {
            username: 'tomsmith',
            password: 'SuperSecretPassword!'
        };

        // Use the fixture value in your tests
        await use({ badData, goodData });

        // You can also perform any teardown here if necessary
    }
});

export { test, expect };

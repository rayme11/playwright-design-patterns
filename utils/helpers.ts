/**
 * General-purpose helper utilities shared across tests.
 */

/** Pause execution for the given number of milliseconds. */
export const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

/** Generate a random alphanumeric string of exactly the given length. */
export const randomString = (length: number = 8): string => {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars[Math.floor(Math.random() * chars.length)];
  }
  return result;
};

/** Generate a unique e-mail address for use in test data. */
export const uniqueEmail = (domain: string = 'example.com'): string =>
  `test+${randomString()}@${domain}`;

/** Format a Date object as YYYY-MM-DD. */
export const formatDate = (date: Date = new Date()): string =>
  date.toISOString().split('T')[0];

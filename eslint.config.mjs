import js from '@eslint/js';
import ts from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';

export default [
  js.configs.recommended,
  {
    files: ['**/*.ts'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: './tsconfig.json',
      },
    },
    plugins: {
      '@typescript-eslint': ts,
    },
    rules: {
      // Allow unused variables if they start with _ (for parameters)
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { 'argsIgnorePattern': '^_' }
      ],
      'no-unused-vars': 'warn',
    },
  },
];

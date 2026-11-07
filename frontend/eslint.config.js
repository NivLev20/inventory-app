// ESLint settings for the dashboard (used by the "lint" stage of the CI pipeline)
export default [
  {
    files: ["**/*.js"],
    ignores: ["eslint.config.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        window: "readonly", document: "readonly", fetch: "readonly", FormData: "readonly",
        getComputedStyle: "readonly", setTimeout: "readonly", setInterval: "readonly",
        Chart: "readonly"
      }
    },
    rules: {
      "no-unused-vars": "error",
      "no-undef": "error",
      "eqeqeq": "error",
      "semi": ["error", "always"]
    }
  }
];

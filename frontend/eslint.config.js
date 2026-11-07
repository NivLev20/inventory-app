// ESLint = automatic code review for JavaScript/React.
// Used by "npm run lint" and by the Lint stage of the Jenkins pipeline.
import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";

export default [
  { ignores: ["dist", "node_modules"] },
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } }
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...js.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      // Components are used inside JSX, which core ESLint can't see - ignore Capitalized names
      "no-unused-vars": ["error", { varsIgnorePattern: "^[A-Z_]" }],
      eqeqeq: "error"
    }
  }
];

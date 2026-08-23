// Sostituisce l'eslint.configure di craco.config.js (che agganciava il
// lint al dev server webpack): con Vite il lint è uno step indipendente
// (script "lint" in package.json), non più parte del build tool. STESSO
// perimetro di prima (solo plugin:react-hooks/recommended, non
// plugin:react/recommended) — quest'ultimo introdurrebbe centinaia di
// avvisi mai applicati finora (es. no-unescaped-entities sugli apostrofi
// nei testi italiani), fuori dallo scopo di questa migrazione.
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default [
  { ignores: ["build/**", "node_modules/**"] },
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser, ...globals.node },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
];

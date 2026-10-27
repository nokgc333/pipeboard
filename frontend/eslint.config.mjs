import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      complexity: ["error", 10],
      "max-depth": ["error", 3],
      "max-params": ["error", 5],
    },
  },
  {
    ignores: [".next/**", "node_modules/**", "playwright-report/**", "coverage/**"],
  },
];

export default eslintConfig;

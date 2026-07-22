import nextPlugin from "@next/eslint-plugin-next";
import { defineConfig, globalIgnores } from "eslint/config";
import nextTypeScript from "eslint-config-next/typescript";

// eslint-plugin-react bundled by Next 16 has not adopted ESLint 10's rule context
// API yet. Keep Next's own Core Web Vitals rules and its TypeScript preset active;
// strict tsc covers semantic types and the UI is reviewed with semantic markup.
export default defineConfig([
  {
    name: "agent-k/next-core-web-vitals",
    files: ["**/*.{js,jsx,mjs,ts,tsx,mts,cts}"],
    plugins: { "@next/next": nextPlugin },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs["core-web-vitals"].rules,
    },
  },
  ...nextTypeScript,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);

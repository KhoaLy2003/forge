import path from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "json-summary"],
      exclude: [
        "src/main.tsx",
        "**/*.d.ts",
        "src/lib/api-client/types.ts",
        "src/lib/api-client/api-client.ts",
        "**/*.test.{ts,tsx}",
        "**/*.config.{ts,js}",
        "src/test/**",
        "node_modules/**",
        "dist/**",
      ],
      thresholds: {
        lines: 80,
      },
    },
  },
});

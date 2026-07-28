import { defineConfig } from "vitest/config";

// Kept separate from vite.config.ts: that one carries the dev server's basic
// auth plugin, which has no business running during tests.
export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
  },
});

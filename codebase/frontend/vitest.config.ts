import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Separate from vite.config.ts (which wires up the Tailwind v4 Vite plugin
// for the app build) so the test environment doesn't need to run the CSS
// pipeline at all - component tests assert on DOM structure/attributes,
// not computed styles.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    globals: false,
    restoreMocks: true,
  },
});

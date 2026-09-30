import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import "@testing-library/jest-dom/vitest";

// Vitest doesn't expose Jest's implicit global afterEach, so React Testing
// Library's automatic per-test unmount doesn't kick in unless we wire it up
// explicitly - without this, every render() in a file after the first one
// stacks up in the same jsdom document instead of replacing it.
afterEach(() => {
  cleanup();
});

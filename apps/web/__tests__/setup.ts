// jest-dom matchers must be registered through the vitest adapter: the plain
// `@testing-library/jest-dom` entry point calls a *global* `expect`, which
// vitest does not provide — that import breaks collection for every test file.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Testing Library only auto-registers cleanup when the test framework exposes
// `afterEach` as a global. This project runs vitest without `globals: true`, so
// each file would otherwise accumulate every previously rendered tree and
// `getByRole`/`getByText` queries would report duplicate elements.
afterEach(() => {
  cleanup();
});

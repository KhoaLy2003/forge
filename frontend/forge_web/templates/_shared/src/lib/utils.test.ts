import { describe, expect, it } from "vitest";

import { cn } from "./utils";

describe("cn", () => {
  it("merges plain class strings", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("resolves Tailwind conflicts via tailwind-merge", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("drops falsy inputs", () => {
    expect(cn("a", false, undefined, "b")).toBe("a b");
  });
});

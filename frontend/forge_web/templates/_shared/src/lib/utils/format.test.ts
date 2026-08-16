import { describe, expect, it } from "vitest";

import { formatCurrency, formatDate } from "./format";

describe("formatDate", () => {
  it("returns a non-empty string containing the year", () => {
    const result = formatDate("2026-01-05T10:00:00.000Z");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("2026");
  });
});

describe("formatCurrency", () => {
  it("formats a USD amount by default", () => {
    const result = formatCurrency(19.99);
    expect(result).toMatch(/\$?19\.99/);
  });

  it("honors the currency parameter", () => {
    const result = formatCurrency(10, "EUR");
    expect(result).toContain("10");
    expect(result).toMatch(/EUR|€/);
    expect(result).not.toContain("USD");
  });
});

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { userEvent } from "@/test/test-utils";

import { Input } from "./input";

describe("Input", () => {
  it("invokes onChange and updates its displayed value while typing", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Input aria-label="Name" onChange={handleChange} />);

    const input = screen.getByLabelText("Name") as HTMLInputElement;
    await user.type(input, "abc");

    expect(handleChange).toHaveBeenCalled();
    expect(input.value).toBe("abc");
  });

  it("is disabled and does not accept typed input", async () => {
    const user = userEvent.setup();
    render(<Input aria-label="Name" disabled />);

    const input = screen.getByLabelText("Name") as HTMLInputElement;
    expect(input).toBeDisabled();

    await user.type(input, "abc");

    expect(input.value).toBe("");
  });
});

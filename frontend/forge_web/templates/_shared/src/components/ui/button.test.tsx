import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { userEvent } from "@/test/test-utils";

import { Button } from "./button";

describe("Button", () => {
  it("invokes the click handler when clicked", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);

    await user.click(screen.getByRole("button", { name: "Click" }));

    expect(handleClick).toHaveBeenCalledOnce();
  });

  it("does not invoke the click handler when disabled, and renders as disabled", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(
      <Button disabled onClick={handleClick}>
        Click
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Click" });
    expect(button).toBeDisabled();

    await user.click(button);

    expect(handleClick).not.toHaveBeenCalled();
  });

  it("renders as its child element when asChild is set", () => {
    render(
      <Button asChild>
        <a href="/x">Link</a>
      </Button>,
    );

    const link = screen.getByRole("link", { name: "Link" });
    expect(link.tagName).toBe("A");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

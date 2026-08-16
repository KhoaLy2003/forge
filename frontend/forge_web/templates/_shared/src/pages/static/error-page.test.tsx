import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ErrorPage from "@/pages/static/error-page";

describe("ErrorPage", () => {
  const assignMock = vi.fn();
  const originalLocation = window.location;

  beforeEach(() => {
    assignMock.mockReset();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...originalLocation, assign: assignMock },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
    cleanup();
  });

  it("shows the default message when no message prop is given", () => {
    render(<ErrorPage />);

    expect(
      screen.getByText("An unexpected error occurred."),
    ).toBeInTheDocument();
  });

  it("shows the given message when provided", () => {
    render(<ErrorPage message="Custom failure" />);

    expect(screen.getByText("Custom failure")).toBeInTheDocument();
  });

  it("navigates home when 'Back to home' is clicked", async () => {
    const user = userEvent.setup();
    render(<ErrorPage />);

    await user.click(screen.getByRole("button", { name: "Back to home" }));

    expect(assignMock).toHaveBeenCalledWith("/");
  });
});

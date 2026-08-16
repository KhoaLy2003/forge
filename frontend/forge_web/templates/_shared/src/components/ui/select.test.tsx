import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "./select";

describe("Select", () => {
  it("shows the placeholder, opens options, and reports the selected value", async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();

    render(
      <Select onValueChange={onValueChange}>
        <SelectTrigger>
          <SelectValue placeholder="Pick one" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>,
    );

    expect(screen.getByText("Pick one")).toBeInTheDocument();

    await user.click(screen.getByRole("combobox"));

    const activeOption = await screen.findByText("Active");
    expect(activeOption).toBeInTheDocument();
    expect(screen.getByText("Archived")).toBeInTheDocument();

    await user.click(activeOption);

    expect(onValueChange).toHaveBeenCalledWith("active");
  });
});

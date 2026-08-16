import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "./dropdown-menu";
import { Button } from "./button";

describe("DropdownMenu", () => {
  it("opens on trigger click and invokes only the selected item's handler", async () => {
    const user = userEvent.setup();
    const onEditSelect = vi.fn();
    const onDeleteSelect = vi.fn();

    render(
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button>Actions</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onSelect={onEditSelect}>Edit</DropdownMenuItem>
          <DropdownMenuItem onSelect={onDeleteSelect}>Delete</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>,
    );

    await user.click(screen.getByText("Actions"));

    const editItem = await screen.findByText("Edit");
    expect(editItem).toBeInTheDocument();
    expect(screen.getByText("Delete")).toBeInTheDocument();

    await user.click(editItem);

    expect(onEditSelect).toHaveBeenCalledTimes(1);
    expect(onDeleteSelect).not.toHaveBeenCalled();
  });
});

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "./alert-dialog";
import { Button } from "./button";

describe("AlertDialog", () => {
  it("opens on trigger click and invokes the action handler on confirm", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();

    render(
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button>Delete</Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogTitle>Are you sure?</AlertDialogTitle>
          <AlertDialogAction onClick={onAction}>Confirm</AlertDialogAction>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
        </AlertDialogContent>
      </AlertDialog>,
    );

    await user.click(screen.getByText("Delete"));

    expect(await screen.findByText("Are you sure?")).toBeInTheDocument();

    await user.click(screen.getByText("Confirm"));

    expect(onAction).toHaveBeenCalledTimes(1);
  });
});

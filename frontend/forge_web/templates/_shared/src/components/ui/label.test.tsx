import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Label } from "./label";

describe("Label", () => {
  it("associates with its input via htmlFor/id", () => {
    render(
      <>
        <Label htmlFor="email">Email</Label>
        <input id="email" />
      </>,
    );

    expect(screen.getByLabelText("Email")).toBeInstanceOf(HTMLInputElement);
  });
});

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Avatar, AvatarFallback } from "./avatar";

describe("Avatar", () => {
  it("renders the fallback content", () => {
    render(
      <Avatar>
        <AvatarFallback>AB</AvatarFallback>
      </Avatar>,
    );
    expect(screen.getByText("AB")).toBeInTheDocument();
  });
});

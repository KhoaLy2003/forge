import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./card";

describe("Card", () => {
  it("renders a full composition with all slot text present", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
          <CardDescription>Card description text.</CardDescription>
        </CardHeader>
        <CardContent>Card body content.</CardContent>
        <CardFooter>Card footer content.</CardFooter>
      </Card>,
    );

    expect(screen.getByText("Card Title")).toBeInTheDocument();
    expect(screen.getByText("Card description text.")).toBeInTheDocument();
    expect(screen.getByText("Card body content.")).toBeInTheDocument();
    expect(screen.getByText("Card footer content.")).toBeInTheDocument();
  });
});

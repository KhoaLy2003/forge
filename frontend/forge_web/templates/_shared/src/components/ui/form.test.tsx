import { describe, expect, it } from "vitest";
import { useForm } from "react-hook-form";
import { render } from "@testing-library/react";

import { screen, userEvent } from "@/test/test-utils";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

interface ProbeFormValues {
  name: string;
}

function ProbeForm() {
  const form = useForm<ProbeFormValues>({ defaultValues: { name: "" } });

  const onSubmit = (values: ProbeFormValues) => {
    if (!values.name) {
      form.setError("name", { message: "Name is required" });
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <button type="submit">Submit</button>
      </form>
    </Form>
  );
}

describe("Form", () => {
  it("shows a validation error when the manually-set field error fires", async () => {
    const user = userEvent.setup();
    render(<ProbeForm />);

    await user.click(screen.getByRole("button", { name: "Submit" }));

    expect(await screen.findByText("Name is required")).toBeInTheDocument();
  });

  it("does not show a validation error when the field is filled in", async () => {
    const user = userEvent.setup();
    render(<ProbeForm />);

    await user.type(screen.getByLabelText("Name"), "Ada Lovelace");
    await user.click(screen.getByRole("button", { name: "Submit" }));

    expect(screen.queryByText("Name is required")).not.toBeInTheDocument();
  });
});

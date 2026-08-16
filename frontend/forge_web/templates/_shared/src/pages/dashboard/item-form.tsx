import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateItem, useUpdateItem } from "@/lib/hooks/use-items";
import type { Item } from "@/lib/api-client";

const itemFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  status: z.enum(["active", "archived"]),
});

type ItemFormValues = z.infer<typeof itemFormSchema>;

interface ItemFormProps {
  item?: Item;
  onSuccess: () => void;
}

export function ItemForm({ item, onSuccess }: ItemFormProps) {
  const createItem = useCreateItem();
  const updateItem = useUpdateItem();

  const form = useForm<ItemFormValues>({
    resolver: zodResolver(itemFormSchema),
    defaultValues: {
      name: item?.name ?? "",
      status: item?.status ?? "active",
    },
  });

  const isSubmitting = createItem.isPending || updateItem.isPending;

  async function onSubmit(values: ItemFormValues) {
    if (item) {
      await updateItem.mutateAsync({ id: item.id, input: values });
    } else {
      await createItem.mutateAsync({ name: values.name });
    }
    onSuccess();
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-base">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="Item name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="status"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Status</FormLabel>
              <Select value={field.value} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a status" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={isSubmitting}>
          {item ? "Save changes" : "Create item"}
        </Button>
      </form>
    </Form>
  );
}

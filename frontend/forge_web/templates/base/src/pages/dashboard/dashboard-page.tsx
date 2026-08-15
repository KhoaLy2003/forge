import { useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { ItemForm } from "@/pages/dashboard/item-form";
import { EmptyState } from "@/pages/static/empty-state";
import ErrorPage from "@/pages/static/error-page";
import { useDeleteItem, useItems } from "@/lib/hooks/use-items";
import { formatDate } from "@/lib/utils/format";
import type { Item } from "@/lib/api-client";

export default function DashboardPage() {
  const { data: items, isLoading, isError, error } = useItems();
  const deleteItem = useDeleteItem();
  const [dialogItem, setDialogItem] = useState<Item | undefined>(undefined);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  function openCreateDialog() {
    setDialogItem(undefined);
    setIsDialogOpen(true);
  }

  function openEditDialog(item: Item) {
    setDialogItem(item);
    setIsDialogOpen(true);
  }

  if (isError) {
    return (
      <ErrorPage
        message={error instanceof Error ? error.message : "Failed to load items."}
      />
    );
  }

  const columns: ColumnDef<Item>[] = [
    {
      accessorKey: "name",
      header: "Name",
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={row.original.status === "active" ? "default" : "outline"}>
          {row.original.status}
        </Badge>
      ),
    },
    {
      accessorKey: "createdAt",
      header: "Created",
      cell: ({ row }) => formatDate(row.original.createdAt),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal className="size-4" />
              <span className="sr-only">Open actions</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => openEditDialog(row.original)}>
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() => deleteItem.mutate(row.original.id)}
              className="text-error-text"
            >
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-lg">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-display-sm font-semibold text-ink">Items</h1>
          <p className="text-body-sm text-muted">
            A sample dataset wired through the mock/real API client.
          </p>
        </div>
        <Button onClick={openCreateDialog}>
          <Plus className="size-4" />
          New Item
        </Button>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-sm">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : items && items.length > 0 ? (
        <DataTable columns={columns} data={items} />
      ) : (
        <EmptyState
          title="No items yet"
          description="Create your first item to get started."
          action={<Button onClick={openCreateDialog}>New Item</Button>}
        />
      )}

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialogItem ? "Edit item" : "New item"}</DialogTitle>
          </DialogHeader>
          <ItemForm item={dialogItem} onSuccess={() => setIsDialogOpen(false)} />
        </DialogContent>
      </Dialog>
    </div>
  );
}

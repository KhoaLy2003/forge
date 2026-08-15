import type { ColumnDef } from "@tanstack/react-table";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface ShowcaseRow {
  name: string;
  status: "active" | "archived";
  date: string;
}

const showcaseColumns: ColumnDef<ShowcaseRow>[] = [
  { accessorKey: "name", header: "Name" },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={row.original.status === "active" ? "default" : "outline"}>
        {row.original.status}
      </Badge>
    ),
  },
  { accessorKey: "date", header: "Date" },
];

const showcaseRows: ShowcaseRow[] = [
  { name: "Welcome kit", status: "active", date: "Jan 5, 2026" },
  { name: "Q1 onboarding checklist", status: "active", date: "Feb 12, 2026" },
  { name: "Legacy migration notes", status: "archived", date: "Nov 20, 2025" },
];

function StaticFormExample() {
  const form = useForm({ defaultValues: { email: "" } });

  return (
    <Form {...form}>
      <form className="flex max-w-[24rem] flex-col gap-base">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input placeholder="you@example.com" {...field} />
              </FormControl>
              <FormDescription>We&apos;ll only use this to send receipts.</FormDescription>
              <FormMessage>Enter a valid email address.</FormMessage>
            </FormItem>
          )}
        />
      </form>
    </Form>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-base border-b border-hairline-soft pb-xl">
      <h2 className="text-display-sm font-semibold text-ink">{title}</h2>
      <div className="flex flex-wrap items-center gap-base">{children}</div>
    </section>
  );
}

export default function ComponentShowcasePage() {
  return (
    <div className="flex flex-col gap-xl">
      <div>
        <h1 className="text-display-sm font-semibold text-ink">Component showcase</h1>
        <p className="text-body-sm text-muted">
          Every generated UI primitive rendered against the theme in one place.
        </p>
      </div>

      <Section title="Buttons">
        <Button variant="default">Default</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="outline">Outline</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="default" disabled>
          Disabled
        </Button>
      </Section>

      <Section title="Inputs">
        <div className="flex flex-col gap-xs">
          <Label htmlFor="showcase-input">Name</Label>
          <Input id="showcase-input" placeholder="Jane Doe" />
        </div>
        <div className="flex flex-col gap-xs">
          <Label htmlFor="showcase-input-disabled">Disabled</Label>
          <Input id="showcase-input-disabled" placeholder="Disabled" disabled />
        </div>
      </Section>

      <Section title="Cards">
        <Card className="w-full max-w-[24rem]">
          <CardHeader>
            <CardTitle>Card title</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-body-sm text-body">
              Placeholder copy showing the card&apos;s content area.
            </p>
          </CardContent>
        </Card>
      </Section>

      <Section title="Badges">
        <Badge variant="default">Active</Badge>
        <Badge variant="outline">Archived</Badge>
      </Section>

      <Section title="Skeleton">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="size-10 rounded-full" />
        <Skeleton className="h-24 w-48" />
      </Section>

      <Section title="Table / DataTable">
        <div className="w-full">
          <DataTable columns={showcaseColumns} data={showcaseRows} />
        </div>
      </Section>

      <Section title="Tabs">
        <Tabs defaultValue="one" className="w-full max-w-[28rem]">
          <TabsList>
            <TabsTrigger value="one">One</TabsTrigger>
            <TabsTrigger value="two">Two</TabsTrigger>
            <TabsTrigger value="three">Three</TabsTrigger>
          </TabsList>
          <TabsContent value="one">Placeholder content for panel one.</TabsContent>
          <TabsContent value="two">Placeholder content for panel two.</TabsContent>
          <TabsContent value="three">Placeholder content for panel three.</TabsContent>
        </Tabs>
      </Section>

      <Section title="Select">
        <Select>
          <SelectTrigger className="w-56">
            <SelectValue placeholder="Choose an option" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="one">Option one</SelectItem>
            <SelectItem value="two">Option two</SelectItem>
            <SelectItem value="three">Option three</SelectItem>
            <SelectItem value="four">Option four</SelectItem>
          </SelectContent>
        </Select>
      </Section>

      <Section title="Dialog">
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="secondary">Open dialog</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Placeholder title</DialogTitle>
              <DialogDescription>
                Placeholder description explaining what this dialog does.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="secondary">Cancel</Button>
              <Button>Confirm</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Section>

      <Section title="AlertDialog">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="secondary">Delete item</Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently remove the item.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction>Continue</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </Section>

      <Section title="DropdownMenu">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="secondary">Open menu</Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Edit</DropdownMenuItem>
            <DropdownMenuItem>Duplicate</DropdownMenuItem>
            <DropdownMenuItem>Delete</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </Section>

      <Section title="Sonner (toast)">
        <Button
          variant="secondary"
          onClick={() => toast("This is a sample notification")}
        >
          Show toast
        </Button>
      </Section>

      <Section title="Form">
        <StaticFormExample />
      </Section>

      <Section title="Avatar">
        <Avatar>
          <AvatarImage src="https://i.pravatar.cc/80" alt="Sample user" />
          <AvatarFallback>JD</AvatarFallback>
        </Avatar>
        <Avatar>
          <AvatarFallback>AB</AvatarFallback>
        </Avatar>
      </Section>
    </div>
  );
}

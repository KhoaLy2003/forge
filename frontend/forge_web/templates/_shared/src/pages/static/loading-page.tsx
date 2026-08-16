import { Skeleton } from "@/components/ui/skeleton";
import { AppShell } from "@/components/common/app-shell";

export default function LoadingPage() {
  return (
    <AppShell>
      <div className="flex flex-col gap-base">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
        <div className="flex flex-col gap-sm">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </div>
    </AppShell>
  );
}

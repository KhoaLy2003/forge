import { Button } from "@/components/ui/button";

interface ErrorPageProps {
  message?: string;
}

export default function ErrorPage({ message }: ErrorPageProps) {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-base bg-canvas px-base text-center">
      <p className="text-caption font-medium text-error-text">Something went wrong</p>
      <h1 className="text-display-sm font-semibold text-ink">
        {message ?? "An unexpected error occurred."}
      </h1>
      <p className="max-w-[24rem] text-body-md text-muted">
        Try reloading the page. If the problem persists, contact support.
      </p>
      <Button onClick={() => window.location.assign("/")}>Back to home</Button>
    </div>
  );
}

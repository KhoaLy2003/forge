import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-base bg-canvas px-base text-center">
      <p className="text-caption font-medium text-muted">404</p>
      <h1 className="text-display-sm font-semibold text-ink">Page not found</h1>
      <p className="max-w-[24rem] text-body-md text-muted">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Button asChild>
        <Link to="/">Back to home</Link>
      </Button>
    </div>
  );
}

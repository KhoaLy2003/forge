import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-base rounded-md bg-surface-soft p-xxl text-center">
      <div className="flex flex-col gap-xs">
        <h3 className="text-display-sm font-semibold text-ink">{title}</h3>
        <p className="text-body-md text-muted">{description}</p>
      </div>
      {action}
    </div>
  );
}

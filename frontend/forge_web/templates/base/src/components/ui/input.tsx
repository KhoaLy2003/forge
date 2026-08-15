import * as React from "react";

import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-14 w-full rounded-sm border border-hairline bg-canvas px-base py-md text-body-md text-ink placeholder:text-muted transition-colors box-border",
          "focus-visible:outline-none focus-visible:border-2 focus-visible:border-ink",
          "disabled:cursor-not-allowed disabled:bg-surface-soft disabled:text-muted-soft",
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { Input };

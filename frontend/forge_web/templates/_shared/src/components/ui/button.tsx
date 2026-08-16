import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-sm whitespace-nowrap rounded-sm text-button-md font-medium transition-colors disabled:pointer-events-none disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-on-primary hover:bg-primary-active active:bg-primary-active disabled:bg-primary-disabled disabled:text-on-primary",
        secondary:
          "bg-canvas text-ink border border-ink hover:bg-surface-soft disabled:border-border-strong disabled:text-muted-soft",
        outline:
          "bg-canvas text-ink border border-ink hover:bg-surface-soft disabled:border-border-strong disabled:text-muted-soft",
        ghost:
          "bg-transparent text-ink hover:underline disabled:text-muted-soft",
      },
      size: {
        default: "h-12 px-lg text-button-md",
        sm: "h-10 px-base text-button-sm",
        icon: "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };

import type { ComponentProps } from "react";
import { Toaster as Sonner } from "sonner";

type ToasterProps = ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      className="toaster group"
      {% raw %}toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-canvas group-[.toaster]:text-ink group-[.toaster]:border-hairline group-[.toaster]:shadow-1 group-[.toaster]:rounded-md",
          description: "group-[.toast]:text-muted",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-on-primary",
          cancelButton:
            "group-[.toast]:bg-surface-soft group-[.toast]:text-muted",
        },
      }}{% endraw %}
      {...props}
    />
  );
};

export { Toaster };

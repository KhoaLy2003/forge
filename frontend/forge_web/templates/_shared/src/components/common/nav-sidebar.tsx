import { NavLink } from "react-router-dom";
{% if include_data_fetching %}
import { House, LayoutGrid, SquareStack } from "lucide-react";
{% else %}
import { House, SquareStack } from "lucide-react";
{% endif %}

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Home", icon: House, end: true },
{% if include_data_fetching %}
  { to: "/dashboard", label: "Dashboard", icon: LayoutGrid, end: false },
{% endif %}
  { to: "/components", label: "Components", icon: SquareStack, end: false },
] as const;

export function NavSidebar() {
  return (
    <nav className="flex w-56 shrink-0 flex-col gap-xs border-r border-hairline bg-canvas p-base">
      {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-sm rounded-sm border-l-2 border-transparent px-base py-sm text-body-sm font-medium text-muted transition-colors",
              "hover:text-ink",
              isActive && "border-l-primary bg-surface-soft text-ink",
            )
          }
        >
          <Icon className="size-4" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

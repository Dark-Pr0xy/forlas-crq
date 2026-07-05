import * as React from "react";
import { cn } from "@/lib/cn";

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <div className="relative">
    <select
      ref={ref}
      className={cn(
        "h-8 w-full appearance-none rounded-sm border bg-surface px-2 pr-7 text-sm text-ink transition focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </select>
    <svg
      aria-hidden
      className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted"
      viewBox="0 0 12 12"
      fill="none"
    >
      <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  </div>
));
Select.displayName = "Select";

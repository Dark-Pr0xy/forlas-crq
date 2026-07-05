import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium",
  {
    variants: {
      tone: {
        neutral: "bg-[var(--c-border-2)] text-muted",
        accent: "bg-accent-soft text-accent",
        teal: "bg-teal-soft text-teal",
        plum: "bg-plum-soft text-plum",
        amber: "bg-amber-soft text-amber",
        rose: "bg-rose-soft text-rose",
        success: "bg-success-soft text-success",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

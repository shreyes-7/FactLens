import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground shadow",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-destructive text-destructive-foreground shadow-sm",
        outline: "text-foreground",
        // Relationship specific variants
        corroborates: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/25",
        contradicts: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/25",
        contextual: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/25",
        related: "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/25",
        uncertain: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/25",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

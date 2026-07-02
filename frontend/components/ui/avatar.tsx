import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Avatar({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex size-10 items-center justify-center rounded-full border border-slate-200 bg-white text-sm font-semibold text-slate-700 shadow-sm",
        className,
      )}
      {...props}
    />
  );
}

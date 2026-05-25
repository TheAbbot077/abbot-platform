import * as React from "react";

import { cn } from "@/lib/utils";

type BadgeTone = "locked" | "available" | "in_progress" | "passed" | "failed" | "neutral";

const toneClasses: Record<BadgeTone, string> = {
  locked: "border-slate-300 bg-slate-100 text-slate-700",
  available: "border-cyan-200 bg-cyan-50 text-cyan-800",
  in_progress: "border-amber-200 bg-amber-50 text-amber-800",
  passed: "border-emerald-200 bg-emerald-50 text-emerald-800",
  failed: "border-rose-200 bg-rose-50 text-rose-800",
  neutral: "border-slate-200 bg-white text-slate-700"
};

export function Badge({
  className,
  tone = "neutral",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium leading-none",
        "bg-[linear-gradient(180deg,rgba(255,255,255,0.78),rgba(255,255,255,0)_55%)] shadow-sm shadow-black/5",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}

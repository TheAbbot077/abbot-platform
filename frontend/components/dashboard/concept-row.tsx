import { CheckCircle2, Circle, LockKeyhole, RotateCcw, XCircle } from "lucide-react";

import { StatusBadge } from "@/components/dashboard/status-badge";
import type { DashboardConcept } from "@/lib/types";

const icons = {
  locked: LockKeyhole,
  available: Circle,
  in_progress: RotateCcw,
  passed: CheckCircle2,
  failed: XCircle
};

export function ConceptRow({ concept }: { concept: DashboardConcept }) {
  const Icon = icons[concept.status];

  return (
    <div className="grid grid-cols-[40px_1fr] gap-3 border-t py-3 first:border-t-0 sm:grid-cols-[40px_1fr_auto] sm:items-center">
      <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-sm font-medium">{concept.sequence_number}. {concept.title}</p>
          {!concept.is_required ? <span className="text-xs text-muted-foreground">Optional</span> : null}
        </div>
        {concept.last_score ? <p className="mt-1 text-xs text-muted-foreground">Last try: {concept.last_score}%</p> : null}
      </div>
      <div className="col-span-2 sm:col-span-1">
        <StatusBadge status={concept.status} />
      </div>
    </div>
  );
}

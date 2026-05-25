import { Badge } from "@/components/ui/badge";
import type { ConceptStatus } from "@/lib/types";

const labels: Record<ConceptStatus, string> = {
  locked: "Locked",
  available: "Available",
  in_progress: "In progress",
  passed: "Passed",
  failed: "Failed"
};

export function StatusBadge({ status }: { status: ConceptStatus }) {
  return <Badge tone={status}>{labels[status]}</Badge>;
}

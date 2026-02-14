import { Badge } from "@/components/ui/badge";
import { STATUS_COLORS, STATUS_LABELS } from "@/lib/utils/constants";
import type { Status } from "@/types/database";

interface StatusBadgeProps {
  status: Status;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge variant="secondary" className={STATUS_COLORS[status]}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}

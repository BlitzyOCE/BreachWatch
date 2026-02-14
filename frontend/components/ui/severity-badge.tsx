import { Badge } from "@/components/ui/badge";
import { SEVERITY_COLORS } from "@/lib/utils/constants";
import type { Severity } from "@/types/database";

interface SeverityBadgeProps {
  severity: Severity | null;
}

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  if (!severity) return null;

  return (
    <Badge variant="secondary" className={SEVERITY_COLORS[severity]}>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </Badge>
  );
}

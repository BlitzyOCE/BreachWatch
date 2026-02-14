import {
  Building2,
  Globe,
  MapPin,
  Calendar,
  Database,
  Swords,
  UserX,
  Activity,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatDate, formatRecordsAffected } from "@/lib/utils/formatting";
import { ATTACK_VECTOR_LABELS } from "@/lib/utils/constants";
import type { Breach } from "@/types/database";

interface BreachFactsProps {
  breach: Breach;
}

interface FactRowProps {
  icon: React.ElementType;
  label: string;
  value: string | React.ReactNode | null;
}

function FactRow({ icon: Icon, label, value }: FactRowProps) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3 py-2">
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <div className="text-sm font-medium">{value}</div>
      </div>
    </div>
  );
}

export function BreachFacts({ breach }: BreachFactsProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Key Facts</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <FactRow icon={Building2} label="Company" value={breach.company} />
        <FactRow icon={Globe} label="Industry" value={breach.industry} />
        <FactRow
          icon={MapPin}
          label="Location"
          value={
            breach.country
              ? `${breach.country}${breach.continent ? `, ${breach.continent}` : ""}`
              : null
          }
        />
        <FactRow
          icon={Calendar}
          label="Discovered"
          value={breach.discovery_date ? formatDate(breach.discovery_date) : null}
        />
        <FactRow
          icon={Calendar}
          label="Disclosed"
          value={breach.disclosure_date ? formatDate(breach.disclosure_date) : null}
        />
        <FactRow
          icon={Database}
          label="Records Affected"
          value={formatRecordsAffected(breach.records_affected)}
        />
        <FactRow
          icon={Swords}
          label="Attack Vector"
          value={
            breach.attack_vector
              ? ATTACK_VECTOR_LABELS[breach.attack_vector]
              : null
          }
        />
        <FactRow
          icon={UserX}
          label="Threat Actor"
          value={breach.threat_actor}
        />
        <FactRow
          icon={Activity}
          label="Status"
          value={<StatusBadge status={breach.status} />}
        />
      </CardContent>
    </Card>
  );
}

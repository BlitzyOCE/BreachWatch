import Link from "next/link";
import { Clock } from "lucide-react";
import { SeverityBadge } from "@/components/ui/severity-badge";
import type { BreachSummary } from "@/types/database";

interface RecentlyViewedProps {
  breaches: BreachSummary[];
}

export function RecentlyViewed({ breaches }: RecentlyViewedProps) {
  if (breaches.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-10 text-muted-foreground">
        <Clock className="h-8 w-8 opacity-40" />
        <p className="text-sm">No recently viewed breaches.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {breaches.map((breach) => (
        <Link
          key={breach.id}
          href={`/breach/${breach.id}`}
          className="flex items-center justify-between rounded-lg border bg-card px-4 py-3 hover:bg-accent/50 transition-colors"
        >
          <div className="min-w-0">
            <p className="truncate font-medium text-sm">
              {breach.title || breach.company}
            </p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {breach.company} · {breach.country ?? "Unknown"}
            </p>
          </div>
          {breach.severity && (
            <div className="ml-3 shrink-0">
              <SeverityBadge severity={breach.severity} />
            </div>
          )}
        </Link>
      ))}
    </div>
  );
}

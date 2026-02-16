import Link from "next/link";
import { Calendar, Database, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatRelativeDate, formatNumber, truncate } from "@/lib/utils/formatting";
import type { BreachSummary } from "@/types/database";

interface BreachCardProps {
  breach: BreachSummary;
}

export function BreachCard({ breach }: BreachCardProps) {
  return (
    <Link href={`/breach/${breach.id}`}>
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardHeader className="pb-1">
          <div>
              <h3 className="line-clamp-3 text-lg font-semibold leading-tight">
                {breach.title || breach.company}
              </h3>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                {breach.industry && <span className="capitalize">{breach.industry}</span>}
                {breach.industry && breach.country && (
                  <span className="text-border">|</span>
                )}
                {breach.country && <span>{breach.country}</span>}
              </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {breach.summary && (
            <p className="text-sm leading-relaxed text-muted-foreground">
              {truncate(breach.summary, 150)}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {formatRelativeDate(breach.created_at)}
            </span>
            {breach.records_affected && (
              <span className="flex items-center gap-1">
                <Database className="h-3.5 w-3.5" />
                {formatNumber(breach.records_affected)}
              </span>
            )}
            {breach.update_count > 0 && (
              <span className="flex items-center gap-1">
                <RefreshCw className="h-3.5 w-3.5" />
                {breach.update_count}{" "}
                {breach.update_count === 1 ? "update" : "updates"}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

import {
  Search,
  Info,
  Scale,
  Gavel,
  Shield,
  CheckCircle,
  FileSearch,
} from "lucide-react";
import { formatDate } from "@/lib/utils/formatting";
import { UPDATE_TYPE_LABELS } from "@/lib/utils/constants";
import type { BreachUpdate, UpdateType } from "@/types/database";

const UPDATE_TYPE_ICONS: Record<UpdateType, React.ElementType> = {
  discovery: Search,
  new_info: Info,
  class_action: Scale,
  regulatory_fine: Gavel,
  remediation: Shield,
  resolution: CheckCircle,
  investigation: FileSearch,
};

interface BreachTimelineProps {
  updates: BreachUpdate[];
}

export function BreachTimeline({ updates }: BreachTimelineProps) {
  if (updates.length === 0) return null;

  return (
    <section>
      <h2 className="text-xl font-semibold tracking-tight">
        Incident Timeline
      </h2>
      <div className="mt-4 space-y-0">
        {updates.map((update, index) => {
          const Icon = UPDATE_TYPE_ICONS[update.update_type] || Info;
          const isLast = index === updates.length - 1;

          return (
            <div key={update.id} className="relative flex gap-4 pb-6">
              {/* Timeline line */}
              {!isLast && (
                <div className="absolute left-[17px] top-10 h-[calc(100%-24px)] w-px bg-border" />
              )}
              {/* Icon */}
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border bg-background">
                <Icon className="h-4 w-4 text-muted-foreground" />
              </div>
              {/* Content */}
              <div className="flex-1 pt-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">
                    {UPDATE_TYPE_LABELS[update.update_type]}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(update.update_date)}
                  </span>
                </div>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                  {update.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

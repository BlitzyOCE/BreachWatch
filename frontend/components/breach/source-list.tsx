import { ExternalLink } from "lucide-react";
import { formatDate } from "@/lib/utils/formatting";
import type { Source } from "@/types/database";

interface SourceListProps {
  sources: Source[];
}

export function SourceList({ sources }: SourceListProps) {
  if (sources.length === 0) return null;

  return (
    <section>
      <h2 className="text-xl font-semibold tracking-tight">Sources</h2>
      <ul className="mt-4 space-y-2">
        {sources.map((source) => (
          <li key={source.id}>
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-2 rounded-md p-2 text-sm transition-colors hover:bg-accent"
            >
              <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0">
                <p className="font-medium leading-snug">
                  {source.title || source.url}
                </p>
                {source.published_date && (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {formatDate(source.published_date)}
                  </p>
                )}
              </div>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}

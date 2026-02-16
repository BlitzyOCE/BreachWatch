import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { SeverityBadge } from "@/components/ui/severity-badge";
import { BreachFacts } from "@/components/breach/breach-facts";
import { BreachTags } from "@/components/breach/breach-tags";
import { BreachTimeline } from "@/components/breach/breach-timeline";
import { SourceList } from "@/components/breach/source-list";
import { RelatedBreaches } from "@/components/breach/related-breaches";
import { formatRelativeDate } from "@/lib/utils/formatting";
import type { BreachDetail as BreachDetailType } from "@/types/database";
import type { BreachSummary } from "@/types/database";

interface BreachDetailProps {
  breach: BreachDetailType;
  relatedBreaches: BreachSummary[];
}

export function BreachDetail({ breach, relatedBreaches }: BreachDetailProps) {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Page Header */}
      <div className="mb-8">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            {breach.title || breach.company}
          </h1>
          <SeverityBadge severity={breach.severity} />
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Last updated {formatRelativeDate(breach.updated_at)}
        </p>
      </div>

      {/* Two-column layout */}
      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        {/* Main Content */}
        <div className="space-y-8">
          {/* Summary */}
          {breach.summary && (
            <section>
              <h2 className="text-xl font-semibold tracking-tight">Summary</h2>
              <div className="mt-3 space-y-4 leading-relaxed text-muted-foreground">
                {breach.summary.split("\n\n").map((paragraph, i) => (
                  <p key={i}>{paragraph}</p>
                ))}
              </div>
            </section>
          )}

          {/* Attack Method */}
          {breach.breach_method && (
            <section>
              <h2 className="text-xl font-semibold tracking-tight">
                Attack Method
              </h2>
              <p className="mt-3 leading-relaxed text-muted-foreground">
                {breach.breach_method}
              </p>
            </section>
          )}

          {/* Data Compromised */}
          {breach.data_compromised && breach.data_compromised.length > 0 && (
            <section>
              <h2 className="text-xl font-semibold tracking-tight">
                Data Compromised
              </h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {breach.data_compromised.map((type) => (
                  <Badge key={type} variant="secondary">
                    {type}
                  </Badge>
                ))}
              </div>
            </section>
          )}

          <Separator />

          {/* Timeline */}
          <BreachTimeline updates={breach.updates} />

          {/* Lessons Learned */}
          {breach.lessons_learned && (
            <>
              <Separator />
              <section>
                <h2 className="text-xl font-semibold tracking-tight">
                  Lessons Learned
                </h2>
                <p className="mt-3 leading-relaxed text-muted-foreground">
                  {breach.lessons_learned}
                </p>
              </section>
            </>
          )}

          <Separator />

          {/* Sources */}
          <SourceList sources={breach.sources} />

          {/* CVE References */}
          {breach.cve_references && breach.cve_references.length > 0 && (
            <section>
              <h2 className="text-xl font-semibold tracking-tight">
                CVE References
              </h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {breach.cve_references.map((cve) => (
                  <Badge key={cve} variant="outline">
                    {cve}
                  </Badge>
                ))}
              </div>
            </section>
          )}

          <Separator />

          {/* Related Breaches */}
          <RelatedBreaches breaches={relatedBreaches} />
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <BreachFacts breach={breach} />
          <BreachTags tags={breach.tags} />
        </div>
      </div>
    </div>
  );
}

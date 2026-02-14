import { BreachCard } from "@/components/breach/breach-card";
import type { BreachSummary } from "@/types/database";

interface RelatedBreachesProps {
  breaches: BreachSummary[];
}

export function RelatedBreaches({ breaches }: RelatedBreachesProps) {
  if (breaches.length === 0) return null;

  return (
    <section>
      <h2 className="text-xl font-semibold tracking-tight">
        Related Breaches
      </h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {breaches.map((breach) => (
          <BreachCard key={breach.id} breach={breach} />
        ))}
      </div>
    </section>
  );
}

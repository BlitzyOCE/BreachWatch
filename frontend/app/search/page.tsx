import type { Metadata } from "next";
import { Suspense } from "react";
import { BreachCard } from "@/components/breach/breach-card";
import { SearchBar } from "@/components/search/search-bar";
import { FilterSidebar } from "@/components/search/filter-sidebar";
import { FilterBar } from "@/components/search/filter-bar";
import { SortSelect } from "@/components/search/sort-select";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { SlidersHorizontal } from "lucide-react";
import { getFilteredBreaches } from "@/lib/queries/breaches";
import { getTagCounts } from "@/lib/queries/tags";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Search Breaches",
  description: "Search and filter data breach incidents.",
};

export const dynamic = "force-dynamic";

interface SearchPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

function toStringArray(value: string | string[] | undefined): string[] {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const query = typeof params.q === "string" ? params.q : "";
  const page = typeof params.page === "string" ? parseInt(params.page, 10) : 1;
  const sort = typeof params.sort === "string" ? params.sort : undefined;

  const industry = toStringArray(params.industry);
  const country = toStringArray(params.country);
  const attackVector = toStringArray(params.attack_vector);
  const threatActor = toStringArray(params.threat_actor);

  const [{ data: breaches, count }, industryCounts, countryCounts, attackVectorCounts, threatActorCounts] =
    await Promise.all([
      getFilteredBreaches({
        query: query || undefined,
        industry: industry.length ? industry : undefined,
        country: country.length ? country : undefined,
        attackVector: attackVector.length ? attackVector : undefined,
        threatActor: threatActor.length ? threatActor : undefined,
        sort,
        page,
      }),
      getTagCounts("industry"),
      getTagCounts("country"),
      getTagCounts("attack_vector"),
      getTagCounts("threat_actor"),
    ]);

  const perPage = 12;
  const totalPages = Math.ceil(count / perPage);
  const hasFilters =
    industry.length > 0 ||
    country.length > 0 ||
    attackVector.length > 0 ||
    threatActor.length > 0;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Search Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">
          {query ? `Results for "${query}"` : "All Breaches"}
        </h1>
        <div className="mt-4 max-w-lg">
          <SearchBar defaultValue={query} />
        </div>
      </div>

      {/* Filter Bar + Sort */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Suspense>
          <FilterBar />
        </Suspense>
        <div className="flex items-center gap-2">
          {/* Mobile filter trigger */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" size="sm" className="lg:hidden">
                <SlidersHorizontal className="mr-2 h-4 w-4" />
                Filters
                {hasFilters && (
                  <span className="ml-1 rounded-full bg-primary px-1.5 text-xs text-primary-foreground">
                    {industry.length +
                      country.length +
                      attackVector.length +
                      threatActor.length}
                  </span>
                )}
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-72 overflow-y-auto">
              <FilterSidebar
                industryCounts={industryCounts}
                countryCounts={countryCounts}
                attackVectorCounts={attackVectorCounts}
                threatActorCounts={threatActorCounts}
              />
            </SheetContent>
          </Sheet>
          <Suspense>
            <SortSelect />
          </Suspense>
        </div>
      </div>

      {/* Main content with sidebar */}
      <div className="flex gap-8">
        {/* Desktop filter sidebar */}
        <aside className="hidden w-56 shrink-0 lg:block">
          <Suspense>
            <FilterSidebar
              industryCounts={industryCounts}
              countryCounts={countryCounts}
              attackVectorCounts={attackVectorCounts}
              threatActorCounts={threatActorCounts}
            />
          </Suspense>
        </aside>

        {/* Results */}
        <div className="flex-1">
          <p className="mb-4 text-sm text-muted-foreground">
            {count} {count === 1 ? "result" : "results"} found
          </p>

          {breaches.length > 0 ? (
            <>
              <div className="grid gap-6 sm:grid-cols-2">
                {breaches.map((breach) => (
                  <BreachCard key={breach.id} breach={breach} />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-8 flex items-center justify-center gap-2">
                  {page > 1 && (
                    <Button variant="outline" size="sm" asChild>
                      <Link
                        href={`/search?${buildPageParams(params, page - 1)}`}
                      >
                        Previous
                      </Link>
                    </Button>
                  )}
                  <span className="px-3 text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </span>
                  {page < totalPages && (
                    <Button variant="outline" size="sm" asChild>
                      <Link
                        href={`/search?${buildPageParams(params, page + 1)}`}
                      >
                        Next
                      </Link>
                    </Button>
                  )}
                </div>
              )}
            </>
          ) : (
            <EmptyState />
          )}
        </div>
      </div>
    </div>
  );
}

function buildPageParams(
  currentParams: Record<string, string | string[] | undefined>,
  newPage: number
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(currentParams)) {
    if (key === "page") continue;
    if (Array.isArray(value)) {
      value.forEach((v) => params.append(key, v));
    } else if (value) {
      params.set(key, value);
    }
  }
  if (newPage > 1) params.set("page", String(newPage));
  return params.toString();
}

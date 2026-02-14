import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BreachCard } from "@/components/breach/breach-card";
import { StatCard } from "@/components/ui/stat-card";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchBar } from "@/components/search/search-bar";
import {
  getRecentBreaches,
  getBreachCount,
  getRecentBreachCount,
} from "@/lib/queries/breaches";

export const dynamic = "force-dynamic";

export default async function Home() {
  const [breaches, totalCount, recentCount] = await Promise.all([
    getRecentBreaches(12),
    getBreachCount(),
    getRecentBreachCount(7),
  ]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Data Breach Intelligence
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          AI-powered tracking and analysis of cybersecurity incidents as they
          unfold. Stay informed about the latest data breaches worldwide.
        </p>
        <div className="mx-auto mt-6 max-w-md">
          <SearchBar />
        </div>
      </div>

      {/* Stats */}
      <div className="mt-12 grid gap-4 sm:grid-cols-3">
        <StatCard label="Breaches Tracked" value={totalCount} />
        <StatCard label="This Week" value={recentCount} />
        <StatCard
          label="Sources Monitored"
          value={8}
        />
      </div>

      {/* Recent Breaches */}
      <div className="mt-12">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold tracking-tight">
            Recent Breaches
          </h2>
          <Button variant="ghost" asChild>
            <Link href="/search" className="gap-1">
              View all <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>

        {breaches.length > 0 ? (
          <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {breaches.map((breach) => (
              <BreachCard key={breach.id} breach={breach} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No breaches yet"
            description="Breach data will appear here once the scraper runs."
          />
        )}
      </div>
    </div>
  );
}

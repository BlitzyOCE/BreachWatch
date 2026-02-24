"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Pencil, Trash2, List } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { BreachCard } from "@/components/breach/breach-card";
import { WatchlistConditionBuilder } from "@/components/my-breachcase/watchlist-condition-builder";
import { useAuth } from "@/components/auth/auth-provider";
import {
  getWatchlists,
  createWatchlist,
  updateWatchlist,
  deleteWatchlist,
} from "@/lib/queries/watchlists";
import type {
  Watchlist,
  WatchlistFilters,
  BreachSummary,
  TagCount,
} from "@/types/database";

interface WatchlistTabsProps {
  industryCounts: TagCount[];
  countryCounts: TagCount[];
  attackVectorCounts: TagCount[];
  threatActorCounts: TagCount[];
}

interface FeedState {
  breaches: BreachSummary[];
  count: number;
  loading: boolean;
  page: number;
}

export function WatchlistTabs({
  industryCounts,
  countryCounts,
  attackVectorCounts,
  threatActorCounts,
}: WatchlistTabsProps) {
  const { user } = useAuth();
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("");
  const [feeds, setFeeds] = useState<Record<string, FeedState>>({});

  // Dialog state
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editingWatchlist, setEditingWatchlist] = useState<Watchlist | null>(null);

  useEffect(() => {
    if (!user) return;
    getWatchlists(user.id)
      .then((data) => {
        setWatchlists(data);
        if (data.length > 0) setActiveTab(data[0].id);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  const loadFeed = useCallback(
    async (watchlistId: string, filters: WatchlistFilters, page = 1) => {
      setFeeds((prev) => ({
        ...prev,
        [watchlistId]: {
          ...(prev[watchlistId] ?? { breaches: [], count: 0, page: 1 }),
          loading: true,
        },
      }));

      try {
        const res = await fetch("/api/watchlist-feed", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filters, page }),
        });
        if (!res.ok) throw new Error("Feed fetch failed");
        const result: { data: BreachSummary[]; count: number } = await res.json();
        setFeeds((prev) => ({
          ...prev,
          [watchlistId]: {
            breaches: result.data,
            count: result.count,
            loading: false,
            page,
          },
        }));
      } catch {
        setFeeds((prev) => ({
          ...prev,
          [watchlistId]: {
            ...(prev[watchlistId] ?? { breaches: [], count: 0, page: 1 }),
            loading: false,
          },
        }));
      }
    },
    []
  );

  // Load feed when active tab changes
  useEffect(() => {
    if (!activeTab) return;
    const wl = watchlists.find((w) => w.id === activeTab);
    if (!wl) return;
    // Only load if we haven't loaded yet
    if (!feeds[activeTab]) {
      loadFeed(activeTab, wl.filters);
    }
  }, [activeTab, watchlists, feeds, loadFeed]);

  function openCreate() {
    setEditingWatchlist(null);
    setBuilderOpen(true);
  }

  function openEdit(watchlist: Watchlist) {
    setEditingWatchlist(watchlist);
    setBuilderOpen(true);
  }

  async function handleSave(name: string, filters: WatchlistFilters) {
    if (!user) return;

    if (editingWatchlist) {
      await updateWatchlist(editingWatchlist.id, name, filters);
      setWatchlists((prev) =>
        prev.map((w) =>
          w.id === editingWatchlist.id ? { ...w, name, filters } : w
        )
      );
      // Refresh feed for the edited watchlist
      setFeeds((prev) => {
        const next = { ...prev };
        delete next[editingWatchlist.id];
        return next;
      });
      if (activeTab === editingWatchlist.id) {
        loadFeed(editingWatchlist.id, filters);
      }
    } else {
      const created = await createWatchlist(user.id, name, filters);
      setWatchlists((prev) => [created, ...prev]);
      setActiveTab(created.id);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteWatchlist(id);
      setWatchlists((prev) => prev.filter((w) => w.id !== id));
      setFeeds((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      if (activeTab === id) {
        const remaining = watchlists.filter((w) => w.id !== id);
        setActiveTab(remaining.length > 0 ? remaining[0].id : "");
      }
    } catch {
      // ignore
    }
  }

  const header = (
    <div className="flex w-full items-center justify-between py-3">
      <h2 className="text-lg font-semibold">
        Watchlists
        {!loading && watchlists.length > 0 && (
          <span className="ml-2 text-sm font-normal text-muted-foreground">
            ({watchlists.length})
          </span>
        )}
      </h2>
    </div>
  );

  if (loading) {
    return (
      <div className="space-y-4">
        {header}
        <div className="flex gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-9 w-28 rounded-md bg-muted animate-pulse" />
          ))}
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-40 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (watchlists.length === 0) {
    return (
      <>
        {header}
        <div className="flex flex-col items-center gap-3 rounded-lg border bg-card py-12 text-muted-foreground">
          <List className="h-10 w-10 opacity-40" />
          <div className="text-center">
            <p className="font-medium text-foreground">No watchlists yet.</p>
            <p className="mt-1 max-w-sm text-sm">
              Create a watchlist to track breaches matching specific conditions
              -- by industry, country, attack type, or keyword.
            </p>
          </div>
          <Button onClick={openCreate} className="mt-2">
            <Plus className="mr-1.5 h-4 w-4" />
            Create Your First Watchlist
          </Button>
        </div>

        <WatchlistConditionBuilder
          open={builderOpen}
          onOpenChange={setBuilderOpen}
          onSave={handleSave}
          title="New Watchlist"
          industryCounts={industryCounts}
          countryCounts={countryCounts}
          attackVectorCounts={attackVectorCounts}
          threatActorCounts={threatActorCounts}
        />
      </>
    );
  }

  const perPage = 12;

  return (
    <>
      {header}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center gap-2">
          <TabsList className="flex-wrap">
            {watchlists.map((wl) => (
              <TabsTrigger key={wl.id} value={wl.id}>
                {wl.name}
                {feeds[wl.id] && !feeds[wl.id].loading && (
                  <Badge variant="secondary" className="ml-1.5">
                    {feeds[wl.id].count}
                  </Badge>
                )}
              </TabsTrigger>
            ))}
          </TabsList>
          <Button variant="outline" size="icon" className="h-8 w-8 shrink-0" onClick={openCreate}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {watchlists.map((wl) => {
          const feed = feeds[wl.id];
          const totalPages = feed ? Math.ceil(feed.count / perPage) : 0;

          return (
            <TabsContent key={wl.id} value={wl.id}>
              {/* Watchlist actions */}
              <div className="mb-4 flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => openEdit(wl)}>
                  <Pencil className="mr-1.5 h-3.5 w-3.5" />
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={() => handleDelete(wl.id)}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  Delete
                </Button>
              </div>

              {/* Feed content */}
              {!feed || feed.loading ? (
                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="h-40 rounded-lg bg-muted animate-pulse" />
                  ))}
                </div>
              ) : feed.breaches.length === 0 ? (
                <div className="flex flex-col items-center gap-2 rounded-lg border py-12 text-muted-foreground">
                  <p className="text-sm">No breaches match this watchlist's conditions.</p>
                  <Button variant="outline" size="sm" onClick={() => openEdit(wl)}>
                    Edit Conditions
                  </Button>
                </div>
              ) : (
                <>
                  <p className="mb-4 text-sm text-muted-foreground">
                    {feed.count} {feed.count === 1 ? "match" : "matches"}
                  </p>
                  <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {feed.breaches.map((breach) => (
                      <BreachCard key={breach.id} breach={breach} />
                    ))}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="mt-6 flex items-center justify-center gap-2">
                      {feed.page > 1 && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => loadFeed(wl.id, wl.filters, feed.page - 1)}
                        >
                          Previous
                        </Button>
                      )}
                      <span className="px-3 text-sm text-muted-foreground">
                        Page {feed.page} of {totalPages}
                      </span>
                      {feed.page < totalPages && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => loadFeed(wl.id, wl.filters, feed.page + 1)}
                        >
                          Next
                        </Button>
                      )}
                    </div>
                  )}
                </>
              )}
            </TabsContent>
          );
        })}
      </Tabs>

      <WatchlistConditionBuilder
        open={builderOpen}
        onOpenChange={setBuilderOpen}
        onSave={handleSave}
        title={editingWatchlist ? "Edit Watchlist" : "New Watchlist"}
        initialName={editingWatchlist?.name}
        initialFilters={editingWatchlist?.filters}
        industryCounts={industryCounts}
        countryCounts={countryCounts}
        attackVectorCounts={attackVectorCounts}
        threatActorCounts={threatActorCounts}
      />
    </>
  );
}

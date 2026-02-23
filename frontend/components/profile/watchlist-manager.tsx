"use client";

import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, List } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useAuth } from "@/components/auth/auth-provider";
import {
  getWatchlists,
  createWatchlist,
  updateWatchlist,
  deleteWatchlist,
} from "@/lib/queries/watchlists";
import type { Watchlist, WatchlistFilters } from "@/types/database";

function filterSummary(filters: WatchlistFilters): string {
  const parts: string[] = [];
  if (filters.query) parts.push(`"${filters.query}"`);
  if (filters.industries?.length) parts.push(filters.industries.join(", "));
  if (filters.countries?.length) parts.push(filters.countries.join(", "));
  if (filters.attack_vectors?.length) parts.push(filters.attack_vectors.join(", "));
  if (filters.threat_actors?.length) parts.push(filters.threat_actors.join(", "));
  return parts.length ? parts.join(" · ") : "No filters";
}

export function WatchlistManager() {
  const { user } = useAuth();
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Watchlist | null>(null);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    getWatchlists(user.id)
      .then(setWatchlists)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  function openCreate() {
    setEditing(null);
    setName("");
    setDialogOpen(true);
  }

  function openEdit(watchlist: Watchlist) {
    setEditing(watchlist);
    setName(watchlist.name);
    setDialogOpen(true);
  }

  async function handleSave() {
    if (!user || !name.trim()) return;
    setSaving(true);
    try {
      if (editing) {
        await updateWatchlist(editing.id, name.trim(), editing.filters);
        setWatchlists((prev) =>
          prev.map((w) => (w.id === editing.id ? { ...w, name: name.trim() } : w))
        );
      } else {
        const created = await createWatchlist(user.id, name.trim(), {});
        setWatchlists((prev) => [created, ...prev]);
      }
      setDialogOpen(false);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteWatchlist(id);
      setWatchlists((prev) => prev.filter((w) => w.id !== id));
    } catch {
      // ignore
    }
  }

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="h-14 rounded-lg bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {watchlists.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
          <List className="h-8 w-8 opacity-40" />
          <p className="text-sm">No watchlists yet.</p>
        </div>
      ) : (
        watchlists.map((watchlist) => (
          <div
            key={watchlist.id}
            className="flex items-center justify-between rounded-lg border bg-card px-4 py-3"
          >
            <div className="min-w-0">
              <p className="font-medium">{watchlist.name}</p>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                {filterSummary(watchlist.filters)}
              </p>
            </div>
            <div className="flex shrink-0 gap-1 ml-2">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => openEdit(watchlist)}
                aria-label="Edit watchlist"
              >
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                onClick={() => handleDelete(watchlist.id)}
                aria-label="Delete watchlist"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ))
      )}

      <Button variant="outline" size="sm" onClick={openCreate} className="w-full">
        <Plus className="mr-1.5 h-4 w-4" />
        New Watchlist
      </Button>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editing ? "Rename Watchlist" : "New Watchlist"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="wl-name">Name</Label>
            <Input
              id="wl-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Healthcare alerts"
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={!name.trim() || saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

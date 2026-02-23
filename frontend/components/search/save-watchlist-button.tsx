"use client";

import { useState } from "react";
import { Bookmark } from "lucide-react";
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
import { createWatchlist } from "@/lib/queries/watchlists";
import type { WatchlistFilters } from "@/types/database";

interface SaveWatchlistButtonProps {
  filters: WatchlistFilters;
}

export function SaveWatchlistButton({ filters }: SaveWatchlistButtonProps) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  if (!user) return null;

  async function handleSave() {
    if (!user || !name.trim()) return;
    setSaving(true);
    try {
      await createWatchlist(user.id, name.trim(), filters);
      setSaved(true);
      setOpen(false);
      setName("");
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => { setSaved(false); setOpen(true); }}
      >
        <Bookmark className={`mr-1.5 h-4 w-4 ${saved ? "fill-current" : ""}`} />
        {saved ? "Watchlist saved" : "Save as Watchlist"}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save as Watchlist</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="watchlist-name">Watchlist name</Label>
            <Input
              id="watchlist-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Healthcare alerts"
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={!name.trim() || saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

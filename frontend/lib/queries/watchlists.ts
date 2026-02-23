import { createBrowserClient } from "@/lib/supabase/client";
import type { Watchlist, WatchlistFilters } from "@/types/database";

export async function getWatchlists(userId: string): Promise<Watchlist[]> {
  const supabase = createBrowserClient();
  const { data, error } = await supabase
    .from("watchlists")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });

  if (error) throw error;
  return (data as Watchlist[]) ?? [];
}

export async function createWatchlist(
  userId: string,
  name: string,
  filters: WatchlistFilters
): Promise<Watchlist> {
  const supabase = createBrowserClient();
  const { data, error } = await supabase
    .from("watchlists")
    .insert({ user_id: userId, name, filters })
    .select()
    .single();

  if (error) throw error;
  return data as Watchlist;
}

export async function updateWatchlist(
  id: string,
  name: string,
  filters: WatchlistFilters
): Promise<void> {
  const supabase = createBrowserClient();
  const { error } = await supabase
    .from("watchlists")
    .update({ name, filters })
    .eq("id", id);

  if (error) throw error;
}

export async function deleteWatchlist(id: string): Promise<void> {
  const supabase = createBrowserClient();
  const { error } = await supabase
    .from("watchlists")
    .delete()
    .eq("id", id);

  if (error) throw error;
}

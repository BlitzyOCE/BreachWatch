import { createServerClient } from "@/lib/supabase/server";
import type { BreachSummary } from "@/types/database";

// Server-only - safe to import from server components only
export async function getRecentlyViewed(
  userId: string,
  limit = 10
): Promise<BreachSummary[]> {
  const supabase = await createServerClient();

  const { data: viewData, error: viewError } = await supabase
    .from("breach_views")
    .select("breach_id, viewed_at")
    .eq("user_id", userId)
    .order("viewed_at", { ascending: false })
    .limit(limit * 3);

  if (viewError || !viewData?.length) return [];

  const seen = new Set<string>();
  const uniqueIds: string[] = [];
  for (const row of viewData) {
    if (!seen.has(row.breach_id)) {
      seen.add(row.breach_id);
      uniqueIds.push(row.breach_id);
      if (uniqueIds.length === limit) break;
    }
  }

  const { data: breaches, error: breachError } = await supabase
    .from("breach_summary")
    .select("*")
    .in("id", uniqueIds);

  if (breachError || !breaches) return [];

  return uniqueIds
    .map((id) => breaches.find((b: BreachSummary) => b.id === id))
    .filter(Boolean) as BreachSummary[];
}

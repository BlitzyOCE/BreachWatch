import { createServerClient } from "@/lib/supabase/server";
import type {
  BreachSummary,
  BreachDetail,
  BreachUpdate,
  BreachTag,
  Source,
} from "@/types/database";

export async function getRecentBreaches(
  limit = 12
): Promise<BreachSummary[]> {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from("breach_summary")
    .select("*")
    .order("last_update_date", { ascending: false, nullsFirst: false })
    .limit(limit);

  if (error) throw error;
  return data as BreachSummary[];
}

export async function getBreachById(
  id: string
): Promise<BreachDetail | null> {
  const supabase = createServerClient();

  const [breachResult, updatesResult, tagsResult, sourcesResult] =
    await Promise.all([
      supabase.from("breaches").select("*").eq("id", id).single(),
      supabase
        .from("breach_updates")
        .select("*")
        .eq("breach_id", id)
        .order("update_date", { ascending: true }),
      supabase.from("breach_tags").select("*").eq("breach_id", id),
      supabase
        .from("sources")
        .select("*")
        .eq("breach_id", id)
        .order("published_date", { ascending: false }),
    ]);

  if (breachResult.error || !breachResult.data) return null;

  return {
    ...breachResult.data,
    updates: (updatesResult.data as BreachUpdate[]) ?? [],
    tags: (tagsResult.data as BreachTag[]) ?? [],
    sources: (sourcesResult.data as Source[]) ?? [],
  } as BreachDetail;
}

export async function searchBreaches(
  query: string,
  limit = 20
): Promise<BreachSummary[]> {
  const supabase = createServerClient();
  const { data, error } = await supabase.rpc("search_breaches", {
    search_query: query,
  });

  if (error) throw error;
  return (data as BreachSummary[])?.slice(0, limit) ?? [];
}

export async function getRelatedBreaches(
  breachId: string,
  maxResults = 3
): Promise<BreachSummary[]> {
  const supabase = createServerClient();
  const { data, error } = await supabase.rpc("get_related_breaches", {
    breach_uuid: breachId,
    max_results: maxResults,
  });

  if (error) throw error;
  return (data as BreachSummary[]) ?? [];
}

export async function getBreachCount(): Promise<number> {
  const supabase = createServerClient();
  const { count, error } = await supabase
    .from("breaches")
    .select("*", { count: "exact", head: true });

  if (error) throw error;
  return count ?? 0;
}

export async function getRecentBreachCount(days = 7): Promise<number> {
  const supabase = createServerClient();
  const since = new Date();
  since.setDate(since.getDate() - days);

  const { count, error } = await supabase
    .from("breaches")
    .select("*", { count: "exact", head: true })
    .gte("created_at", since.toISOString());

  if (error) throw error;
  return count ?? 0;
}

interface FilterOptions {
  query?: string;
  industry?: string[];
  country?: string[];
  attackVector?: string[];
  threatActor?: string[];
  sort?: string;
  page?: number;
  perPage?: number;
}

export async function getFilteredBreaches(
  filters: FilterOptions
): Promise<{ data: BreachSummary[]; count: number }> {
  const supabase = createServerClient();
  const { page = 1, perPage = 12 } = filters;

  if (filters.query) {
    const results = await searchBreaches(filters.query, 100);
    // Apply client-side filtering on search results for tag filters
    let filtered = results;

    // For search results, we can't easily filter by tags server-side
    // since search_breaches returns breaches directly.
    // We return them as-is and let the UI handle pagination.
    const start = (page - 1) * perPage;
    return {
      data: filtered.slice(start, start + perPage),
      count: filtered.length,
    };
  }

  // No search query — use breach_summary view with tag-based filtering
  let query = supabase.from("breach_summary").select("*", { count: "exact" });

  // Apply tag-based filters by checking breach IDs against breach_tags
  if (
    filters.industry?.length ||
    filters.country?.length ||
    filters.attackVector?.length ||
    filters.threatActor?.length
  ) {
    const tagFilters: { type: string; values: string[] }[] = [];
    if (filters.industry?.length)
      tagFilters.push({ type: "industry", values: filters.industry });
    if (filters.country?.length)
      tagFilters.push({ type: "country", values: filters.country });
    if (filters.attackVector?.length)
      tagFilters.push({ type: "attack_vector", values: filters.attackVector });
    if (filters.threatActor?.length)
      tagFilters.push({ type: "threat_actor", values: filters.threatActor });

    for (const tf of tagFilters) {
      const { data: tagMatches } = await supabase
        .from("breach_tags")
        .select("breach_id")
        .eq("tag_type", tf.type)
        .in("tag_value", tf.values);

      if (tagMatches?.length) {
        const ids = tagMatches.map((t) => t.breach_id);
        query = query.in("id", ids);
      } else {
        return { data: [], count: 0 };
      }
    }
  }

  // Apply sorting
  switch (filters.sort) {
    case "updated":
      query = query.order("last_update_date", {
        ascending: false,
        nullsFirst: false,
      });
      break;
    case "records":
      query = query.order("records_affected", {
        ascending: false,
        nullsFirst: false,
      });
      break;
    default:
      query = query.order("created_at", { ascending: false });
  }

  // Pagination
  const from = (page - 1) * perPage;
  query = query.range(from, from + perPage - 1);

  const { data, error, count } = await query;
  if (error) throw error;

  return {
    data: (data as BreachSummary[]) ?? [],
    count: count ?? 0,
  };
}

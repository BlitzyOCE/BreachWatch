import { createBrowserClient } from "@/lib/supabase/client";
import type { BreachSummary } from "@/types/database";

export async function getSavedBreaches(
  userId: string
): Promise<(BreachSummary & { saved_at: string })[]> {
  const supabase = createBrowserClient();
  const { data, error } = await supabase
    .from("saved_breaches")
    .select("created_at, breach:breach_summary!inner(*)")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });

  if (error) throw error;

  return (data ?? []).map((row: { created_at: string; breach: unknown }) => ({
    ...(row.breach as BreachSummary),
    saved_at: row.created_at,
  }));
}

export async function isBreachSaved(breachId: string): Promise<boolean> {
  const supabase = createBrowserClient();
  const { data } = await supabase
    .from("saved_breaches")
    .select("id")
    .eq("breach_id", breachId)
    .maybeSingle();
  return !!data;
}

export async function saveBreach(
  breachId: string,
  userId: string
): Promise<void> {
  const supabase = createBrowserClient();
  const { error } = await supabase
    .from("saved_breaches")
    .insert({ breach_id: breachId, user_id: userId });
  if (error) throw error;
}

export async function unsaveBreach(
  breachId: string,
  userId: string
): Promise<void> {
  const supabase = createBrowserClient();
  const { error } = await supabase
    .from("saved_breaches")
    .delete()
    .eq("breach_id", breachId)
    .eq("user_id", userId);
  if (error) throw error;
}

import { createBrowserClient } from "@/lib/supabase/client";

// Browser-only - safe to import from client components
export async function recordBreachView(
  breachId: string,
  userId?: string
): Promise<void> {
  const supabase = createBrowserClient();
  await supabase.from("breach_views").insert({
    breach_id: breachId,
    user_id: userId ?? null,
  });
  // Intentionally ignore errors — view tracking is non-critical
}

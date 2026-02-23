import { NextResponse } from "next/server";
import { createServerClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

export async function POST() {
  try {
    // Verify the user is authenticated
    const supabase = await createServerClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const adminClient = createAdminClient();

    // 1. Anonymize comments (set user_id to NULL so they show "Deleted User")
    // The comments table may not exist yet (Build 4) - ignore errors
    await adminClient
      .from("comments")
      .update({ user_id: null })
      .eq("user_id", user.id);

    // 2. Delete the profile (cascades to saved_breaches, watchlists via FK)
    const { error: profileError } = await adminClient
      .from("profiles")
      .delete()
      .eq("id", user.id);

    if (profileError) {
      console.error("Profile deletion failed:", profileError);
      return NextResponse.json(
        { error: `Failed to delete profile: ${profileError.message}` },
        { status: 500 }
      );
    }

    // 3. Delete from auth.users via admin API
    const { error: authError } =
      await adminClient.auth.admin.deleteUser(user.id);

    if (authError) {
      console.error("Auth user deletion failed:", authError);
      return NextResponse.json(
        { error: `Failed to delete auth account: ${authError.message}` },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (err) {
    console.error("Account deletion error:", err);
    const message =
      err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

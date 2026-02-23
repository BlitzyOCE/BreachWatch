import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { createServerClient } from "@/lib/supabase/server";
import { getCurrentProfile } from "@/lib/queries/profile";
import { Separator } from "@/components/ui/separator";
import { CommentModerationQueue } from "@/components/admin/comment-moderation-queue";
import { UserManagementTable } from "@/components/admin/user-management-table";

export const metadata: Metadata = {
  title: "Admin Dashboard",
};

export default async function AdminPage() {
  const supabase = await createServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login?redirectTo=/admin");

  const profile = await getCurrentProfile();
  if (!profile || profile.role !== "admin") redirect("/");

  // Fetch basic stats server-side
  const [{ count: totalUsers }, { count: totalComments }, { count: flaggedComments }] =
    await Promise.all([
      supabase.from("profiles").select("*", { count: "exact", head: true }),
      supabase.from("comments").select("*", { count: "exact", head: true }),
      supabase
        .from("comments")
        .select("*", { count: "exact", head: true })
        .eq("status", "flagged"),
    ]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8 space-y-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Admin Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Moderation and user management.
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border bg-card p-5">
          <p className="text-sm text-muted-foreground">Total Users</p>
          <p className="mt-1 text-3xl font-bold">{totalUsers ?? 0}</p>
        </div>
        <div className="rounded-lg border bg-card p-5">
          <p className="text-sm text-muted-foreground">Total Comments</p>
          <p className="mt-1 text-3xl font-bold">{totalComments ?? 0}</p>
        </div>
        <div className="rounded-lg border bg-card p-5">
          <p className="text-sm text-muted-foreground">Flagged Comments</p>
          <p className={`mt-1 text-3xl font-bold ${(flaggedComments ?? 0) > 0 ? "text-destructive" : ""}`}>
            {flaggedComments ?? 0}
          </p>
        </div>
      </div>

      <Separator />

      {/* Comment moderation queue */}
      <section>
        <h2 className="text-lg font-semibold tracking-tight">
          Flagged Comments
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Review and action comments that have been reported.
        </p>
        <div className="mt-4">
          <CommentModerationQueue />
        </div>
      </section>

      <Separator />

      {/* User management */}
      <section>
        <h2 className="text-lg font-semibold tracking-tight">Users</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage user roles. The first admin must be set manually in Supabase.
        </p>
        <div className="mt-4">
          <UserManagementTable />
        </div>
      </section>
    </div>
  );
}

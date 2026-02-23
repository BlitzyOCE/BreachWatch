import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { createServerClient } from "@/lib/supabase/server";
import { getCurrentProfile } from "@/lib/queries/profile";
import { getRecentlyViewed } from "@/lib/queries/breach-views-server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ProfileHeader } from "@/components/profile/profile-header";
import { ProfileEditForm } from "@/components/profile/profile-edit-form";
import { SavedBreachesList } from "@/components/profile/saved-breaches-list";
import { WatchlistManager } from "@/components/profile/watchlist-manager";
import { RecentlyViewed } from "@/components/profile/recently-viewed";

export const metadata: Metadata = {
  title: "Profile",
};

export default async function ProfilePage() {
  const supabase = await createServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const [profile, recentlyViewed] = await Promise.all([
    getCurrentProfile(),
    getRecentlyViewed(user.id, 10),
  ]);

  if (!profile) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <p className="mt-4 text-muted-foreground">
          Your profile is being set up. Please refresh the page in a moment.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8 space-y-8">
      <ProfileHeader profile={profile} email={user.email ?? ""} />

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>Edit Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <ProfileEditForm profile={profile} />
        </CardContent>
      </Card>

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>Saved Breaches</CardTitle>
        </CardHeader>
        <CardContent>
          <SavedBreachesList />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Watchlists</CardTitle>
        </CardHeader>
        <CardContent>
          <WatchlistManager />
        </CardContent>
      </Card>

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>Recently Viewed</CardTitle>
        </CardHeader>
        <CardContent>
          <RecentlyViewed breaches={recentlyViewed} />
        </CardContent>
      </Card>
    </div>
  );
}

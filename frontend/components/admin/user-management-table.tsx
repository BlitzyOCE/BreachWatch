"use client";

import { useEffect, useState } from "react";
import { formatRelativeDate } from "@/lib/utils/formatting";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { createBrowserClient } from "@/lib/supabase/client";
import type { Profile } from "@/types/profile";

export function UserManagementTable() {
  const [users, setUsers] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = createBrowserClient();
    supabase
      .from("profiles")
      .select("*")
      .order("created_at", { ascending: false })
      .then(({ data }) => setUsers((data as Profile[]) ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function toggleRole(user: Profile) {
    const newRole = user.role === "admin" ? "user" : "admin";
    const supabase = createBrowserClient();
    try {
      await supabase.from("profiles").update({ role: newRole }).eq("id", user.id);
      setUsers((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, role: newRole } : u))
      );
    } catch {
      // ignore
    }
  }

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 rounded bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  if (users.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        No users found.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="pb-2 font-medium">User</th>
            <th className="pb-2 font-medium">Role</th>
            <th className="pb-2 font-medium">Joined</th>
            <th className="pb-2 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {users.map((user) => (
            <tr key={user.id}>
              <td className="py-3 pr-4">
                <p className="font-medium">{user.display_name ?? "—"}</p>
                {user.job_title && (
                  <p className="text-xs text-muted-foreground">{user.job_title}</p>
                )}
              </td>
              <td className="py-3 pr-4">
                <Badge
                  variant={user.role === "admin" ? "default" : "secondary"}
                  className="text-xs"
                >
                  {user.role}
                </Badge>
              </td>
              <td className="py-3 pr-4 text-muted-foreground">
                {formatRelativeDate(user.created_at)}
              </td>
              <td className="py-3 text-right">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleRole(user)}
                >
                  {user.role === "admin" ? "Revoke admin" : "Make admin"}
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

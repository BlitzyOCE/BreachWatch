import { createBrowserClient } from "@/lib/supabase/client";
import type { Comment } from "@/types/database";

type RawComment = Omit<Comment, "profile" | "replies"> & {
  profile: { display_name: string | null; avatar_url: string | null } | null;
};

export async function getComments(breachId: string): Promise<Comment[]> {
  const supabase = createBrowserClient();
  const { data, error } = await supabase
    .from("comments")
    .select("*, profile:profiles(display_name, avatar_url)")
    .eq("breach_id", breachId)
    .in("status", ["visible"])
    .order("created_at", { ascending: true });

  if (error) throw error;

  const rows = (data as RawComment[]) ?? [];

  // Separate top-level and replies, nest replies under parents
  const topLevel = rows.filter((c) => !c.parent_id);
  const replies = rows.filter((c) => !!c.parent_id);

  return topLevel.map((comment) => ({
    ...comment,
    replies: replies.filter((r) => r.parent_id === comment.id),
  }));
}

export async function getFlaggedComments(): Promise<Comment[]> {
  const supabase = createBrowserClient();
  const { data, error } = await supabase
    .from("comments")
    .select("*, profile:profiles(display_name, avatar_url)")
    .eq("status", "flagged")
    .order("created_at", { ascending: false });

  if (error) throw error;
  return (data as RawComment[]) ?? [];
}

export async function postComment(
  breachId: string,
  userId: string,
  body: string,
  parentId?: string
): Promise<Comment> {
  const supabase = createBrowserClient();
  const { data, error } = await supabase
    .from("comments")
    .insert({
      breach_id: breachId,
      user_id: userId,
      body,
      parent_id: parentId ?? null,
    })
    .select("*, profile:profiles(display_name, avatar_url)")
    .single();

  if (error) throw error;
  return data as Comment;
}

export async function editComment(id: string, body: string): Promise<void> {
  const supabase = createBrowserClient();
  const { error } = await supabase
    .from("comments")
    .update({ body, is_edited: true })
    .eq("id", id);
  if (error) throw error;
}

export async function deleteComment(id: string): Promise<void> {
  const supabase = createBrowserClient();
  const { error } = await supabase.from("comments").delete().eq("id", id);
  if (error) throw error;
}

export async function reportComment(id: string): Promise<void> {
  const supabase = createBrowserClient();
  const { error } = await supabase
    .from("comments")
    .update({ status: "flagged" })
    .eq("id", id);
  if (error) throw error;
}

export async function moderateComment(
  id: string,
  action: "approve" | "remove"
): Promise<void> {
  const supabase = createBrowserClient();
  const status = action === "approve" ? "visible" : "removed";
  const { error } = await supabase
    .from("comments")
    .update({ status })
    .eq("id", id);
  if (error) throw error;
}

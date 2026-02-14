import { createServerClient } from "@/lib/supabase/server";
import type { TagCount, TagType } from "@/types/database";

export async function getTagCounts(tagType: TagType): Promise<TagCount[]> {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from("tag_counts")
    .select("*")
    .eq("tag_type", tagType)
    .order("breach_count", { ascending: false });

  if (error) throw error;
  return (data as TagCount[]) ?? [];
}

export async function getAllTagCounts(): Promise<Record<TagType, TagCount[]>> {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from("tag_counts")
    .select("*")
    .order("breach_count", { ascending: false });

  if (error) throw error;

  const grouped: Record<string, TagCount[]> = {};
  for (const tag of (data as TagCount[]) ?? []) {
    if (!grouped[tag.tag_type]) grouped[tag.tag_type] = [];
    grouped[tag.tag_type].push(tag);
  }

  return grouped as Record<TagType, TagCount[]>;
}

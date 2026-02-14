import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { TagType } from "@/types/database";

interface TagBadgeProps {
  tagType: TagType;
  tagValue: string;
  clickable?: boolean;
}

export function TagBadge({ tagType, tagValue, clickable = true }: TagBadgeProps) {
  const badge = (
    <Badge variant="outline" className="text-xs">
      {tagValue}
    </Badge>
  );

  if (!clickable) return badge;

  return (
    <Link
      href={`/search?${tagType}=${encodeURIComponent(tagValue)}`}
      className="transition-opacity hover:opacity-80"
    >
      {badge}
    </Link>
  );
}

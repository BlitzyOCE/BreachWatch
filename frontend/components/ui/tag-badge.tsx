import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { ATTACK_VECTOR_LABELS } from "@/lib/utils/constants";
import type { AttackVector, TagType } from "@/types/database";

interface TagBadgeProps {
  tagType: TagType;
  tagValue: string;
  clickable?: boolean;
}

function formatTagValue(tagType: TagType, tagValue: string): string {
  if (tagType === "attack_vector" && tagValue in ATTACK_VECTOR_LABELS) {
    return ATTACK_VECTOR_LABELS[tagValue as AttackVector];
  }
  return tagValue.replace(/_/g, " ");
}

export function TagBadge({ tagType, tagValue, clickable = true }: TagBadgeProps) {
  const badge = (
    <Badge variant="outline" className="text-xs capitalize whitespace-normal h-auto">
      {formatTagValue(tagType, tagValue)}
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

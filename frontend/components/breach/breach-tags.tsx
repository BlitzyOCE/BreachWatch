import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TagBadge } from "@/components/ui/tag-badge";
import { TAG_TYPE_LABELS } from "@/lib/utils/constants";
import type { BreachTag, TagType } from "@/types/database";

interface BreachTagsProps {
  tags: BreachTag[];
}

export function BreachTags({ tags }: BreachTagsProps) {
  if (tags.length === 0) return null;

  // Group tags by type
  const grouped = tags.reduce(
    (acc, tag) => {
      if (!acc[tag.tag_type]) acc[tag.tag_type] = [];
      acc[tag.tag_type].push(tag);
      return acc;
    },
    {} as Record<TagType, BreachTag[]>
  );

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Tags</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {(Object.entries(grouped) as [TagType, BreachTag[]][]).map(
          ([type, typeTags]) => (
            <div key={type}>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                {TAG_TYPE_LABELS[type]}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {typeTags.map((tag) => (
                  <TagBadge
                    key={tag.id}
                    tagType={tag.tag_type}
                    tagValue={tag.tag_value}
                  />
                ))}
              </div>
            </div>
          )
        )}
      </CardContent>
    </Card>
  );
}

"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown } from "lucide-react";
import type { TagCount } from "@/types/database";

interface FilterSectionProps {
  title: string;
  paramKey: string;
  options: TagCount[];
}

function FilterSection({ title, paramKey, options }: FilterSectionProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeValues = searchParams.getAll(paramKey);

  const toggleFilter = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      const current = params.getAll(paramKey);

      // Remove all existing values for this key
      params.delete(paramKey);

      if (current.includes(value)) {
        // Remove the value
        current
          .filter((v) => v !== value)
          .forEach((v) => params.append(paramKey, v));
      } else {
        // Add the value
        [...current, value].forEach((v) => params.append(paramKey, v));
      }

      // Reset to page 1 when filters change
      params.delete("page");

      router.push(`/search?${params.toString()}`);
    },
    [router, searchParams, paramKey]
  );

  if (options.length === 0) return null;

  return (
    <Collapsible defaultOpen>
      <CollapsibleTrigger className="group flex w-full items-center justify-between py-2 text-sm font-medium hover:text-foreground">
        {title}
        <ChevronDown className="h-4 w-4 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="space-y-1 pb-3">
          {options.slice(0, 10).map((option) => (
            <label
              key={option.tag_value}
              className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
            >
              <Checkbox
                checked={activeValues.includes(option.tag_value)}
                onCheckedChange={() => toggleFilter(option.tag_value)}
              />
              <span className="flex-1 truncate">{option.tag_value}</span>
              <span className="text-xs text-muted-foreground">
                {option.breach_count}
              </span>
            </label>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

interface FilterSidebarProps {
  severityCounts: TagCount[];
  industryCounts: TagCount[];
  countryCounts: TagCount[];
  attackVectorCounts: TagCount[];
  threatActorCounts: TagCount[];
}

export function FilterSidebar({
  severityCounts,
  industryCounts,
  countryCounts,
  attackVectorCounts,
  threatActorCounts,
}: FilterSidebarProps) {
  return (
    <div className="space-y-1">
      <h3 className="mb-3 text-sm font-semibold">Filters</h3>
      <FilterSection
        title="Severity"
        paramKey="severity"
        options={severityCounts}
      />
      <FilterSection
        title="Industry"
        paramKey="industry"
        options={industryCounts}
      />
      <FilterSection
        title="Country"
        paramKey="country"
        options={countryCounts}
      />
      <FilterSection
        title="Attack Vector"
        paramKey="attack_vector"
        options={attackVectorCounts}
      />
      <FilterSection
        title="Threat Actor"
        paramKey="threat_actor"
        options={threatActorCounts}
      />
    </div>
  );
}

"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const FILTER_LABELS: Record<string, string> = {
  severity: "Severity",
  industry: "Industry",
  country: "Country",
  attack_vector: "Attack Vector",
};

export function FilterBar() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const activeFilters: { key: string; value: string }[] = [];
  for (const key of ["severity", "industry", "country", "attack_vector"]) {
    for (const value of searchParams.getAll(key)) {
      activeFilters.push({ key, value });
    }
  }

  if (activeFilters.length === 0) return null;

  function removeFilter(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    const current = params.getAll(key);
    params.delete(key);
    current
      .filter((v) => v !== value)
      .forEach((v) => params.append(key, v));
    params.delete("page");
    router.push(`/search?${params.toString()}`);
  }

  function clearAll() {
    const params = new URLSearchParams();
    const q = searchParams.get("q");
    if (q) params.set("q", q);
    router.push(`/search?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm text-muted-foreground">Active filters:</span>
      {activeFilters.map(({ key, value }) => (
        <Badge
          key={`${key}-${value}`}
          variant="secondary"
          className="cursor-pointer gap-1 pr-1"
          onClick={() => removeFilter(key, value)}
        >
          <span className="text-xs text-muted-foreground">
            {FILTER_LABELS[key]}:
          </span>{" "}
          {value}
          <X className="h-3 w-3" />
        </Badge>
      ))}
      <Button
        variant="ghost"
        size="sm"
        onClick={clearAll}
        className="h-6 text-xs"
      >
        Clear all
      </Button>
    </div>
  );
}

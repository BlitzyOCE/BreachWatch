"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
} from "@/components/ui/dropdown-menu";
import { ChevronDown } from "lucide-react";
import type { TagCount, WatchlistFilters } from "@/types/database";

interface ConditionBuilderProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (name: string, filters: WatchlistFilters) => Promise<void>;
  initialName?: string;
  initialFilters?: WatchlistFilters;
  title?: string;
  industryCounts: TagCount[];
  countryCounts: TagCount[];
  attackVectorCounts: TagCount[];
  threatActorCounts: TagCount[];
}

interface FilterSectionProps {
  title: string;
  options: TagCount[];
  selected: string[];
  onToggle: (value: string) => void;
}

function FilterSection({ title, options, selected, onToggle }: FilterSectionProps) {
  if (options.length === 0) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-between font-normal"
        >
          <span className="flex items-center gap-2 truncate">
            <span className="truncate">{title}</span>
            {selected.length > 0 && (
              <Badge variant="secondary" className="shrink-0 text-xs">
                {selected.length}
              </Badge>
            )}
          </span>
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="start">
        {options.map((option) => (
          <DropdownMenuCheckboxItem
            key={option.tag_value}
            checked={selected.includes(option.tag_value)}
            onCheckedChange={() => onToggle(option.tag_value)}
            onSelect={(e) => e.preventDefault()}
          >
            <span className="flex-1 truncate capitalize">{option.tag_value}</span>
            <span className="ml-auto text-xs text-muted-foreground">
              {option.breach_count}
            </span>
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function WatchlistConditionBuilder({
  open,
  onOpenChange,
  onSave,
  initialName = "",
  initialFilters = {},
  title = "New Watchlist",
  industryCounts,
  countryCounts,
  attackVectorCounts,
  threatActorCounts,
}: ConditionBuilderProps) {
  const [name, setName] = useState(initialName);
  const [query, setQuery] = useState(initialFilters.query ?? "");
  const [industries, setIndustries] = useState<string[]>(initialFilters.industries ?? []);
  const [countries, setCountries] = useState<string[]>(initialFilters.countries ?? []);
  const [attackVectors, setAttackVectors] = useState<string[]>(initialFilters.attack_vectors ?? []);
  const [threatActors, setThreatActors] = useState<string[]>(initialFilters.threat_actors ?? []);
  const [saving, setSaving] = useState(false);

  function toggleValue(arr: string[], value: string): string[] {
    return arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
  }

  function resetForm() {
    setName(initialName);
    setQuery(initialFilters.query ?? "");
    setIndustries(initialFilters.industries ?? []);
    setCountries(initialFilters.countries ?? []);
    setAttackVectors(initialFilters.attack_vectors ?? []);
    setThreatActors(initialFilters.threat_actors ?? []);
  }

  async function handleSave() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const filters: WatchlistFilters = {};
      if (query.trim()) filters.query = query.trim();
      if (industries.length) filters.industries = industries;
      if (countries.length) filters.countries = countries;
      if (attackVectors.length) filters.attack_vectors = attackVectors;
      if (threatActors.length) filters.threat_actors = threatActors;

      await onSave(name.trim(), filters);
      onOpenChange(false);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  }

  const filterCount =
    industries.length + countries.length + attackVectors.length + threatActors.length;

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) resetForm();
        onOpenChange(o);
      }}
    >
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="wl-name">Name</Label>
            <Input
              id="wl-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Healthcare alerts"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="wl-query">Keyword query</Label>
            <Input
              id="wl-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. ransomware hospital"
            />
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium">
              Filter conditions
              {filterCount > 0 && (
                <span className="ml-2 text-xs text-muted-foreground">
                  ({filterCount} selected)
                </span>
              )}
            </p>

            <div className="grid grid-cols-2 gap-2">
              <FilterSection
                title="Industries"
                options={industryCounts}
                selected={industries}
                onToggle={(v) => setIndustries(toggleValue(industries, v))}
              />
              <FilterSection
                title="Countries"
                options={countryCounts}
                selected={countries}
                onToggle={(v) => setCountries(toggleValue(countries, v))}
              />
              <FilterSection
                title="Attack Vectors"
                options={attackVectorCounts}
                selected={attackVectors}
                onToggle={(v) => setAttackVectors(toggleValue(attackVectors, v))}
              />
              <FilterSection
                title="Threat Actors"
                options={threatActorCounts}
                selected={threatActors}
                onToggle={(v) => setThreatActors(toggleValue(threatActors, v))}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!name.trim() || saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

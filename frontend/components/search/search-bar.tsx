"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface SearchBarProps {
  compact?: boolean;
  defaultValue?: string;
  onNavigate?: () => void;
}

export function SearchBar({ compact, defaultValue = "", onNavigate }: SearchBarProps) {
  const [query, setQuery] = useState(defaultValue);
  const router = useRouter();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    onNavigate?.();
  }

  return (
    <form onSubmit={handleSubmit} className="relative">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        placeholder="Search breaches..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className={compact ? "h-9 w-48 pl-9 text-sm" : "h-10 w-full pl-9"}
      />
    </form>
  );
}

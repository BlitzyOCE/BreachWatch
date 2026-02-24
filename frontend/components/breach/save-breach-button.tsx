"use client";

import { useState } from "react";
import { Bookmark } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { saveBreach, unsaveBreach } from "@/lib/queries/saved-breaches";

interface SaveBreachButtonProps {
  breachId: string;
  initialSaved?: boolean;
}

export function SaveBreachButton({ breachId, initialSaved = false }: SaveBreachButtonProps) {
  const { user } = useAuth();
  const router = useRouter();
  const [saved, setSaved] = useState(initialSaved);
  const [pending, setPending] = useState(false);

  async function handleToggle(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();

    if (!user) {
      router.push("/login");
      return;
    }
    if (pending) return;

    setPending(true);
    try {
      if (saved) {
        await unsaveBreach(breachId, user.id);
        setSaved(false);
      } else {
        await saveBreach(breachId, user.id);
        setSaved(true);
      }
    } catch {
      // ignore
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      onClick={handleToggle}
      disabled={pending}
      className="absolute right-2 top-2 z-10 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      aria-label={saved ? "Remove from saved" : "Save breach"}
    >
      <Bookmark
        className={`h-4 w-4 ${saved ? "fill-current text-foreground" : ""}`}
      />
    </button>
  );
}

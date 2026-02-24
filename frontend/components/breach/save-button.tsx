"use client";

import { useEffect, useState } from "react";
import { Bookmark } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { isBreachSaved, saveBreach, unsaveBreach } from "@/lib/queries/saved-breaches";

interface SaveButtonProps {
  breachId: string;
}

export function SaveButton({ breachId }: SaveButtonProps) {
  const { user } = useAuth();
  const router = useRouter();
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) return;
    isBreachSaved(breachId).then(setSaved).catch(() => {});
  }, [user, breachId]);

  async function toggle() {
    if (!user) {
      router.push("/login");
      return;
    }
    if (loading) return;
    setLoading(true);
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
      setLoading(false);
    }
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={toggle}
      disabled={loading}
      aria-label={saved ? "Unsave breach" : "Save breach"}
    >
      <Bookmark
        className={`mr-1.5 h-4 w-4 ${saved ? "fill-current" : ""}`}
      />
      {saved ? "Saved" : "Save"}
    </Button>
  );
}

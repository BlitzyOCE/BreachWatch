"use client";

import { useEffect, useRef } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { recordBreachView } from "@/lib/queries/breach-views";

interface ViewTrackerProps {
  breachId: string;
}

export function ViewTracker({ breachId }: ViewTrackerProps) {
  const { user, loading } = useAuth();
  const recorded = useRef(false);

  useEffect(() => {
    if (loading || recorded.current) return;
    recorded.current = true;
    recordBreachView(breachId, user?.id);
  }, [breachId, user, loading]);

  return null;
}

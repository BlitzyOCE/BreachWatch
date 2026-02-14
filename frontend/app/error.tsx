"use client";

import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <ShieldAlert className="h-16 w-16 text-muted-foreground" />
      <h1 className="text-2xl font-bold tracking-tight">
        Something went wrong
      </h1>
      <p className="max-w-md text-muted-foreground">
        An error occurred while loading this page. This might be a temporary
        issue — please try again.
      </p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}

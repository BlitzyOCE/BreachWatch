"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatRelativeDate } from "@/lib/utils/formatting";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getFlaggedComments, moderateComment } from "@/lib/queries/comments";
import type { Comment } from "@/types/database";

export function CommentModerationQueue() {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFlaggedComments()
      .then(setComments)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleAction(id: string, action: "approve" | "remove") {
    try {
      await moderateComment(id, action);
      setComments((prev) => prev.filter((c) => c.id !== id));
    } catch {
      // ignore
    }
  }

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  if (comments.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        No flagged comments — queue is clear.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {comments.map((comment) => (
        <div key={comment.id} className="rounded-lg border bg-card p-4 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm">
              <span className="font-medium">
                {comment.profile?.display_name ?? "Anonymous"}
              </span>
              <span className="mx-1 text-muted-foreground">·</span>
              <span className="text-muted-foreground">
                {formatRelativeDate(comment.created_at)}
              </span>
              <span className="mx-1 text-muted-foreground">·</span>
              <Link
                href={`/breach/${comment.breach_id}`}
                className="underline underline-offset-2 hover:text-foreground text-muted-foreground"
              >
                View breach
              </Link>
            </div>
            <Badge variant="destructive" className="text-xs">Flagged</Badge>
          </div>

          <p className="text-sm whitespace-pre-wrap break-words border-l-2 pl-3 text-muted-foreground">
            {comment.body}
          </p>

          <div className="flex gap-2 pt-1">
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleAction(comment.id, "approve")}
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => handleAction(comment.id, "remove")}
            >
              Remove
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

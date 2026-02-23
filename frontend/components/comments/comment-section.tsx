"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MessageSquare } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { CommentCard } from "@/components/comments/comment-card";
import { CommentInput } from "@/components/comments/comment-input";
import { getComments, postComment } from "@/lib/queries/comments";
import type { Comment } from "@/types/database";

interface CommentSectionProps {
  breachId: string;
}

export function CommentSection({ breachId }: CommentSectionProps) {
  const { user } = useAuth();
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getComments(breachId)
      .then(setComments)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [breachId]);

  async function handlePost(body: string) {
    if (!user) return;
    const newComment = await postComment(breachId, user.id, body);
    setComments((prev) => [...prev, { ...newComment, replies: [] }]);
  }

  async function handleReply(parentId: string, body: string) {
    if (!user) return;
    const reply = await postComment(breachId, user.id, body, parentId);
    setComments((prev) =>
      prev.map((c) =>
        c.id === parentId
          ? { ...c, replies: [...(c.replies ?? []), reply] }
          : c
      )
    );
  }

  function handleDelete(id: string) {
    setComments((prev) => {
      // Remove top-level comment or nested reply
      return prev
        .filter((c) => c.id !== id)
        .map((c) => ({
          ...c,
          replies: (c.replies ?? []).filter((r) => r.id !== id),
        }));
    });
  }

  return (
    <section>
      <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
        <MessageSquare className="h-5 w-5" />
        Discussion
        {comments.length > 0 && (
          <span className="text-sm font-normal text-muted-foreground">
            ({comments.length})
          </span>
        )}
      </h2>

      <div className="mt-4 space-y-6">
        {/* Comment input */}
        {user ? (
          <CommentInput onSubmit={handlePost} />
        ) : (
          <p className="text-sm text-muted-foreground">
            <Link href="/login" className="underline underline-offset-2 hover:text-foreground">
              Sign in
            </Link>{" "}
            to join the discussion.
          </p>
        )}

        {/* Comment list */}
        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex gap-3">
                <div className="h-8 w-8 rounded-full bg-muted animate-pulse shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-24 rounded bg-muted animate-pulse" />
                  <div className="h-12 rounded bg-muted animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        ) : comments.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No comments yet. Be the first to start the discussion.
          </p>
        ) : (
          <div className="space-y-6">
            {comments.map((comment) => (
              <div key={comment.id} className="space-y-4">
                <CommentCard
                  comment={comment}
                  currentUserId={user?.id}
                  onReply={handleReply}
                  onDelete={handleDelete}
                />
                {/* One level of replies */}
                {(comment.replies ?? []).map((reply) => (
                  <CommentCard
                    key={reply.id}
                    comment={reply}
                    currentUserId={user?.id}
                    onDelete={handleDelete}
                    indent
                  />
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

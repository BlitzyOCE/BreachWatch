"use client";

import { useState } from "react";
import { formatRelativeDate } from "@/lib/utils/formatting";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Flag, Reply, Pencil, Trash2 } from "lucide-react";
import { CommentInput } from "@/components/comments/comment-input";
import { editComment, deleteComment, reportComment } from "@/lib/queries/comments";
import type { Comment } from "@/types/database";

const EDIT_WINDOW_MS = 15 * 60 * 1000; // 15 minutes

interface CommentCardProps {
  comment: Comment;
  currentUserId?: string | null;
  onReply?: (parentId: string, body: string) => Promise<void>;
  onDelete?: (id: string) => void;
  indent?: boolean;
}

export function CommentCard({
  comment,
  currentUserId,
  onReply,
  onDelete,
  indent = false,
}: CommentCardProps) {
  const [showReplyInput, setShowReplyInput] = useState(false);
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(comment.body);
  const [reported, setReported] = useState(false);

  const isOwn = currentUserId === comment.user_id;
  const canEdit =
    isOwn && Date.now() - new Date(comment.created_at).getTime() < EDIT_WINDOW_MS;

  const displayName = comment.profile?.display_name ?? "Anonymous";
  const avatarUrl = comment.profile?.avatar_url ?? null;
  const initials = displayName.slice(0, 2).toUpperCase();

  if (comment.status === "removed") {
    return (
      <div className={`py-2 ${indent ? "ml-8" : ""}`}>
        <p className="text-xs italic text-muted-foreground">
          [This comment has been removed by a moderator]
        </p>
      </div>
    );
  }

  async function handleEdit(newBody: string) {
    await editComment(comment.id, newBody);
    setBody(newBody);
    comment.is_edited = true;
    setEditing(false);
  }

  async function handleDelete() {
    await deleteComment(comment.id);
    onDelete?.(comment.id);
  }

  async function handleReport() {
    await reportComment(comment.id);
    setReported(true);
  }

  async function handleReply(replyBody: string) {
    await onReply?.(comment.id, replyBody);
    setShowReplyInput(false);
  }

  return (
    <div className={`space-y-3 ${indent ? "ml-8 border-l pl-4" : ""}`}>
      <div className="flex gap-3">
        <Avatar className="h-8 w-8 shrink-0">
          {avatarUrl && <AvatarImage src={avatarUrl} alt={displayName} />}
          <AvatarFallback className="text-xs">{initials}</AvatarFallback>
        </Avatar>

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="text-sm font-medium">{displayName}</span>
            <span className="text-xs text-muted-foreground">
              {formatRelativeDate(comment.created_at)}
            </span>
            {comment.is_edited && (
              <span className="text-xs text-muted-foreground">(edited)</span>
            )}
          </div>

          {editing ? (
            <div className="mt-2">
              <CommentInput
                onSubmit={handleEdit}
                placeholder="Edit your comment…"
                submitLabel="Save"
                onCancel={() => setEditing(false)}
              />
            </div>
          ) : (
            <p className="mt-1 text-sm leading-relaxed whitespace-pre-wrap break-words">
              {body}
            </p>
          )}

          {!editing && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {!indent && onReply && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => setShowReplyInput((v) => !v)}
                >
                  <Reply className="mr-1 h-3 w-3" />
                  Reply
                </Button>
              )}
              {canEdit && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => setEditing(true)}
                >
                  <Pencil className="mr-1 h-3 w-3" />
                  Edit
                </Button>
              )}
              {isOwn && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs text-destructive hover:text-destructive"
                  onClick={handleDelete}
                >
                  <Trash2 className="mr-1 h-3 w-3" />
                  Delete
                </Button>
              )}
              {currentUserId && !isOwn && !reported && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={handleReport}
                >
                  <Flag className="mr-1 h-3 w-3" />
                  Report
                </Button>
              )}
              {reported && (
                <span className="text-xs text-muted-foreground px-2 py-1">
                  Reported
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {showReplyInput && (
        <div className="ml-11">
          <CommentInput
            onSubmit={handleReply}
            placeholder={`Reply to ${displayName}…`}
            submitLabel="Reply"
            onCancel={() => setShowReplyInput(false)}
          />
        </div>
      )}
    </div>
  );
}

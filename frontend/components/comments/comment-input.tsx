"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const MAX_CHARS = 2000;

interface CommentInputProps {
  onSubmit: (body: string) => Promise<void>;
  placeholder?: string;
  submitLabel?: string;
  onCancel?: () => void;
}

export function CommentInput({
  onSubmit,
  placeholder = "Write a comment…",
  submitLabel = "Post",
  onCancel,
}: CommentInputProps) {
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function validate(text: string): string | null {
    if (text.length > MAX_CHARS)
      return `Comment must be under ${MAX_CHARS} characters.`;
    const urlMatches = text.match(/https?:\/\//g) ?? [];
    if (urlMatches.length > 3)
      return "Comments may not contain more than 3 links.";
    if (text === text.toUpperCase() && text.trim().length > 10)
      return "Please avoid writing in all caps.";
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validate(body);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit(body.trim());
      setBody("");
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : (err as { message?: string })?.message ?? "Failed to post comment.";
      setError(
        msg.includes("rate") ? "You're posting too fast. Try again in a few minutes." : msg
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <Textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={placeholder}
        rows={3}
        maxLength={MAX_CHARS}
        className="resize-none"
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {body.length}/{MAX_CHARS}
        </span>
        <div className="flex gap-2">
          {onCancel && (
            <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" size="sm" disabled={submitting || body.trim().length === 0}>
            {submitting ? "Posting…" : submitLabel}
          </Button>
        </div>
      </div>
    </form>
  );
}

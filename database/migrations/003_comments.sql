-- Migration 003: comments table with threading, moderation, and rate limiting
-- Run this in Supabase Dashboard → SQL Editor

-- 1. Rate limit function (must exist before the RLS policy that references it)
CREATE OR REPLACE FUNCTION public.check_comment_rate_limit(p_user_id uuid)
RETURNS boolean AS $$
DECLARE
  recent_count integer;
BEGIN
  SELECT COUNT(*) INTO recent_count
  FROM public.comments
  WHERE user_id = p_user_id
    AND created_at > now() - interval '10 minutes';
  RETURN recent_count < 5;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Comments table
CREATE TABLE public.comments (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  breach_id uuid NOT NULL REFERENCES public.breaches(id) ON DELETE CASCADE,
  user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  parent_id uuid REFERENCES public.comments(id) ON DELETE CASCADE,
  body text NOT NULL CHECK (char_length(body) >= 1 AND char_length(body) <= 2000),
  status text NOT NULL DEFAULT 'visible' CHECK (status IN ('visible', 'flagged', 'removed')),
  is_edited boolean NOT NULL DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT comments_pkey PRIMARY KEY (id)
);

CREATE TRIGGER on_comments_updated
  BEFORE UPDATE ON public.comments
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;

-- Anyone can read visible comments; users can always see their own; admins see all
CREATE POLICY "Comments are readable"
  ON public.comments FOR SELECT
  USING (
    status = 'visible'
    OR auth.uid() = user_id
    OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- Authenticated users can insert their own comments (rate-limited)
CREATE POLICY "Authenticated users can insert comments"
  ON public.comments FOR INSERT
  WITH CHECK (
    auth.uid() = user_id
    AND check_comment_rate_limit(auth.uid())
  );

-- Users can update own comments; admins can update any
CREATE POLICY "Users can update own comments"
  ON public.comments FOR UPDATE
  USING (
    auth.uid() = user_id
    OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  )
  WITH CHECK (
    auth.uid() = user_id
    OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- Users can delete own comments; admins can delete any
CREATE POLICY "Users can delete own comments"
  ON public.comments FOR DELETE
  USING (
    auth.uid() = user_id
    OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- 3. Allow admins to update any profile (for role management in admin dashboard)
CREATE POLICY "Admins can update any profile"
  ON public.profiles FOR UPDATE
  USING (
    auth.uid() = id
    OR EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'admin')
  )
  WITH CHECK (
    auth.uid() = id
    OR EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'admin')
  );

-- Migration 004: Enable RLS on breach_views for authenticated view tracking
-- Run this in Supabase Dashboard → SQL Editor

ALTER TABLE public.breach_views ENABLE ROW LEVEL SECURITY;

-- Anyone (anon or authenticated) can insert a view record
CREATE POLICY "Anyone can insert breach views"
  ON public.breach_views FOR INSERT
  WITH CHECK (true);

-- Users can read their own view history (for Recently Viewed)
CREATE POLICY "Users can read own breach views"
  ON public.breach_views FOR SELECT
  USING (auth.uid() = user_id);

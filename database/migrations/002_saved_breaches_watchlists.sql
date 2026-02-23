-- Migration 002: saved_breaches and watchlists tables
-- Run this in Supabase Dashboard → SQL Editor

-- 1. saved_breaches table
CREATE TABLE public.saved_breaches (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  breach_id uuid NOT NULL REFERENCES public.breaches(id) ON DELETE CASCADE,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT saved_breaches_pkey PRIMARY KEY (id),
  CONSTRAINT saved_breaches_unique UNIQUE (user_id, breach_id)
);

ALTER TABLE public.saved_breaches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own saved breaches"
  ON public.saved_breaches FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 2. watchlists table
CREATE TABLE public.watchlists (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  name text NOT NULL,
  filters jsonb NOT NULL DEFAULT '{}',
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT watchlists_pkey PRIMARY KEY (id)
);

CREATE TRIGGER on_watchlists_updated
  BEFORE UPDATE ON public.watchlists
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

ALTER TABLE public.watchlists ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own watchlists"
  ON public.watchlists FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.breach_tags (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  breach_id uuid,
  tag_type text CHECK (tag_type = ANY (ARRAY['continent'::text, 'country'::text, 'industry'::text, 'attack_vector'::text, 'cve'::text, 'mitre_attack'::text, 'threat_actor'::text])),
  tag_value text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT breach_tags_pkey PRIMARY KEY (id),
  CONSTRAINT breach_tags_breach_id_fkey FOREIGN KEY (breach_id) REFERENCES public.breaches(id)
);
CREATE TABLE public.breach_updates (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  breach_id uuid,
  update_date date NOT NULL,
  update_type text CHECK (update_type = ANY (ARRAY['discovery'::text, 'new_info'::text, 'class_action'::text, 'regulatory_fine'::text, 'remediation'::text, 'resolution'::text, 'investigation'::text])),
  description text NOT NULL,
  source_url text,
  extracted_data jsonb,
  confidence_score numeric CHECK (confidence_score >= 0::numeric AND confidence_score <= 1::numeric),
  ai_reasoning text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT breach_updates_pkey PRIMARY KEY (id),
  CONSTRAINT breach_updates_breach_id_fkey FOREIGN KEY (breach_id) REFERENCES public.breaches(id)
);
CREATE TABLE public.breach_views (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  breach_id uuid,
  user_id uuid,
  ip_address inet,
  viewed_at timestamp with time zone DEFAULT now(),
  CONSTRAINT breach_views_pkey PRIMARY KEY (id),
  CONSTRAINT breach_views_breach_id_fkey FOREIGN KEY (breach_id) REFERENCES public.breaches(id)
);
CREATE TABLE public.breaches (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  company text NOT NULL,
  industry text,
  country text,
  continent text,
  discovery_date date,
  disclosure_date date,
  records_affected bigint,
  breach_method text,
  attack_vector text CHECK (attack_vector = ANY (ARRAY['phishing'::text, 'ransomware'::text, 'malware'::text, 'vulnerability_exploit'::text, 'credential_attack'::text, 'social_engineering'::text, 'insider'::text, 'supply_chain'::text, 'misconfiguration'::text, 'unauthorized_access'::text, 'scraping'::text, 'other'::text])),
  data_compromised jsonb DEFAULT '[]'::jsonb,
  severity text CHECK (severity = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text, 'critical'::text])),
  status text DEFAULT 'investigating'::text CHECK (status = ANY (ARRAY['investigating'::text, 'confirmed'::text, 'resolved'::text])),
  threat_actor text,
  cve_references jsonb DEFAULT '[]'::jsonb,
  mitre_techniques jsonb DEFAULT '[]'::jsonb,
  summary text,
  lessons_learned text,
  search_vector tsvector,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  title text,
  CONSTRAINT breaches_pkey PRIMARY KEY (id)
);
CREATE TABLE public.comments (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  breach_id uuid NOT NULL,
  user_id uuid,
  parent_id uuid,
  body text NOT NULL CHECK (char_length(body) >= 1 AND char_length(body) <= 2000),
  status text NOT NULL DEFAULT 'visible'::text CHECK (status = ANY (ARRAY['visible'::text, 'flagged'::text, 'removed'::text])),
  is_edited boolean NOT NULL DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT comments_pkey PRIMARY KEY (id),
  CONSTRAINT comments_breach_id_fkey FOREIGN KEY (breach_id) REFERENCES public.breaches(id),
  CONSTRAINT comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id),
  CONSTRAINT comments_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.comments(id)
);
CREATE TABLE public.company_aliases (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  breach_id uuid,
  alias text NOT NULL,
  is_primary boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT company_aliases_pkey PRIMARY KEY (id),
  CONSTRAINT company_aliases_breach_id_fkey FOREIGN KEY (breach_id) REFERENCES public.breaches(id)
);
CREATE TABLE public.profiles (
  id uuid NOT NULL,
  display_name text,
  avatar_url text,
  job_title text,
  company text,
  role text NOT NULL DEFAULT 'user'::text CHECK (role = ANY (ARRAY['user'::text, 'admin'::text])),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT profiles_pkey PRIMARY KEY (id),
  CONSTRAINT profiles_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id)
);
CREATE TABLE public.saved_breaches (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  breach_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT saved_breaches_pkey PRIMARY KEY (id),
  CONSTRAINT saved_breaches_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id),
  CONSTRAINT saved_breaches_breach_id_fkey FOREIGN KEY (breach_id) REFERENCES public.breaches(id)
);
CREATE TABLE public.sources (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  breach_id uuid,
  url text NOT NULL UNIQUE,
  title text,
  published_date date,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT sources_pkey PRIMARY KEY (id),
  CONSTRAINT sources_breach_id_fkey FOREIGN KEY (breach_id) REFERENCES public.breaches(id)
);
CREATE TABLE public.watchlists (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  name text NOT NULL,
  filters jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT watchlists_pkey PRIMARY KEY (id),
  CONSTRAINT watchlists_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id)
);
CREATE OR REPLACE VIEW public.breach_summary AS
SELECT b.id,
    b.company,
    b.industry,
    b.country,
    b.continent,
    b.discovery_date,
    b.disclosure_date,
    b.records_affected,
    b.breach_method,
    b.attack_vector,
    b.data_compromised,
    b.severity,
    b.status,
    b.threat_actor,
    b.cve_references,
    b.mitre_techniques,
    b.summary,
    b.lessons_learned,
    b.search_vector,
    b.created_at,
    b.updated_at,
    b.title,
    count(DISTINCT bu.id)::integer AS update_count,
    count(DISTINCT s.id)::integer AS source_count,
    max(bu.update_date) AS last_update_date,
    COALESCE(b.discovery_date, b.disclosure_date) AS effective_date
FROM breaches b
     LEFT JOIN breach_updates bu ON b.id = bu.breach_id
     LEFT JOIN sources s ON b.id = s.breach_id
GROUP BY b.id;
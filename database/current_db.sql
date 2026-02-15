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
  title text,
  industry text,
  country text,
  continent text,
  discovery_date date,
  disclosure_date date,
  records_affected bigint,
  breach_method text,
  attack_vector text CHECK (attack_vector = ANY (ARRAY['phishing'::text, 'ransomware'::text, 'api_exploit'::text, 'insider'::text, 'supply_chain'::text, 'misconfiguration'::text, 'malware'::text, 'ddos'::text, 'other'::text])),
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
  CONSTRAINT breaches_pkey PRIMARY KEY (id)
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
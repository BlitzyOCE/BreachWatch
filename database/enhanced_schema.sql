
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Table 1: breaches (main breach records)
-- =============================================================================
CREATE TABLE breaches (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company TEXT NOT NULL,
  industry TEXT,
  country TEXT,
  continent TEXT,
  discovery_date DATE,
  disclosure_date DATE,
  records_affected BIGINT,
  breach_method TEXT,
  attack_vector TEXT CHECK (attack_vector IN ('phishing', 'ransomware', 'api_exploit', 'insider', 'supply_chain', 'misconfiguration', 'other')),
  data_compromised JSONB DEFAULT '[]',
  severity TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  status TEXT CHECK (status IN ('investigating', 'confirmed', 'resolved')) DEFAULT 'investigating',
  threat_actor TEXT,
  cve_references JSONB DEFAULT '[]',
  mitre_techniques JSONB DEFAULT '[]',
  summary TEXT,
  lessons_learned TEXT,
  search_vector tsvector,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for breaches table
CREATE INDEX idx_breaches_company ON breaches(company);
CREATE INDEX idx_breaches_industry ON breaches(industry);
CREATE INDEX idx_breaches_country ON breaches(country);
CREATE INDEX idx_breaches_continent ON breaches(continent);
CREATE INDEX idx_breaches_discovery_date ON breaches(discovery_date);
CREATE INDEX idx_breaches_severity ON breaches(severity);
CREATE INDEX idx_breaches_status ON breaches(status);
CREATE INDEX idx_breaches_created_at ON breaches(created_at DESC);
CREATE INDEX idx_breaches_updated_at ON breaches(updated_at DESC);
CREATE INDEX idx_breaches_search ON breaches USING GIN(search_vector);

-- Trigger to automatically update search_vector for full-text search
CREATE OR REPLACE FUNCTION breaches_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', COALESCE(NEW.company, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(NEW.summary, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(NEW.breach_method, '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(NEW.lessons_learned, '')), 'D');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvector_update
BEFORE INSERT OR UPDATE ON breaches
FOR EACH ROW EXECUTE FUNCTION breaches_search_vector_update();

-- =============================================================================
-- Table 2: breach_updates (timeline updates for each breach)
-- =============================================================================
CREATE TABLE breach_updates (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  breach_id UUID REFERENCES breaches(id) ON DELETE CASCADE,
  update_date DATE NOT NULL,
  update_type TEXT CHECK (update_type IN ('discovery', 'new_info', 'class_action', 'fine', 'remediation', 'resolution')),
  description TEXT NOT NULL,
  source_url TEXT,
  extracted_data JSONB,
  confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
  ai_reasoning TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for breach_updates table
CREATE INDEX idx_breach_updates_breach_id ON breach_updates(breach_id);
CREATE INDEX idx_breach_updates_date ON breach_updates(update_date DESC);
CREATE INDEX idx_breach_updates_confidence ON breach_updates(confidence_score);

-- =============================================================================
-- Table 3: breach_tags (filterable tags for breaches)
-- =============================================================================
CREATE TABLE breach_tags (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  breach_id UUID REFERENCES breaches(id) ON DELETE CASCADE,
  tag_type TEXT CHECK (tag_type IN ('continent', 'country', 'industry', 'attack_vector', 'cve', 'mitre_attack', 'threat_actor')),
  tag_value TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(breach_id, tag_type, tag_value)
);

-- Indexes for breach_tags table
CREATE INDEX idx_breach_tags_breach_id ON breach_tags(breach_id);
CREATE INDEX idx_breach_tags_type_value ON breach_tags(tag_type, tag_value);
CREATE INDEX idx_breach_tags_value ON breach_tags(tag_value);
CREATE INDEX idx_breach_tags_type ON breach_tags(tag_type);

-- =============================================================================
-- Table 4: sources (article URLs and metadata)
-- =============================================================================
CREATE TABLE sources (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  breach_id UUID REFERENCES breaches(id) ON DELETE CASCADE,
  url TEXT NOT NULL UNIQUE,
  title TEXT,
  published_date DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for sources table
CREATE INDEX idx_sources_breach_id ON sources(breach_id);
CREATE INDEX idx_sources_url ON sources(url);
CREATE INDEX idx_sources_published_date ON sources(published_date DESC);

-- =============================================================================
-- Table 5: company_aliases (for breach deduplication)
-- =============================================================================
CREATE TABLE company_aliases (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  breach_id UUID REFERENCES breaches(id) ON DELETE CASCADE,
  alias TEXT NOT NULL,
  is_primary BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for company_aliases table
CREATE INDEX idx_company_aliases_alias ON company_aliases(LOWER(alias));
CREATE INDEX idx_company_aliases_breach_id ON company_aliases(breach_id);

-- =============================================================================
-- Table 6: breach_views (for analytics and recommendations - future)
-- =============================================================================
CREATE TABLE breach_views (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  breach_id UUID REFERENCES breaches(id) ON DELETE CASCADE,
  user_id UUID,
  ip_address INET,
  viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for breach_views table
CREATE INDEX idx_breach_views_breach_id ON breach_views(breach_id);
CREATE INDEX idx_breach_views_user_id ON breach_views(user_id);
CREATE INDEX idx_breach_views_viewed_at ON breach_views(viewed_at DESC);

-- =============================================================================
-- Triggers
-- =============================================================================

-- Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_breaches_updated_at
BEFORE UPDATE ON breaches
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Utility Views
-- =============================================================================

-- View: breach_summary (for homepage/listing pages)
CREATE OR REPLACE VIEW breach_summary AS
SELECT
  b.id,
  b.company,
  b.industry,
  b.country,
  b.continent,
  b.discovery_date,
  b.records_affected,
  b.severity,
  b.status,
  b.summary,
  b.created_at,
  b.updated_at,
  COUNT(DISTINCT bu.id) as update_count,
  COUNT(DISTINCT s.id) as source_count,
  MAX(bu.update_date) as last_update_date
FROM breaches b
LEFT JOIN breach_updates bu ON b.id = bu.breach_id
LEFT JOIN sources s ON b.id = s.breach_id
GROUP BY b.id;

-- View: tag_counts (for filter UI)
CREATE OR REPLACE VIEW tag_counts AS
SELECT
  tag_type,
  tag_value,
  COUNT(*) as breach_count
FROM breach_tags
GROUP BY tag_type, tag_value
ORDER BY tag_type, breach_count DESC;

-- =============================================================================
-- Utility Functions
-- =============================================================================

-- Function: search_breaches (for keyword search)
CREATE OR REPLACE FUNCTION search_breaches(search_query TEXT)
RETURNS TABLE (
  breach_id UUID,
  company TEXT,
  summary TEXT,
  rank REAL
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    b.id,
    b.company,
    b.summary,
    ts_rank(b.search_vector, plainto_tsquery('english', search_query)) AS rank
  FROM breaches b
  WHERE b.search_vector @@ plainto_tsquery('english', search_query)
  ORDER BY rank DESC;
END;
$$ LANGUAGE plpgsql;

-- Function: get_related_breaches (find similar breaches by tags)
CREATE OR REPLACE FUNCTION get_related_breaches(breach_uuid UUID, max_results INT DEFAULT 3)
RETURNS TABLE (
  related_breach_id UUID,
  shared_tag_count BIGINT,
  company TEXT,
  summary TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    bt2.breach_id,
    COUNT(*) as shared_tags,
    b.company,
    b.summary
  FROM breach_tags bt1
  JOIN breach_tags bt2 ON bt1.tag_value = bt2.tag_value AND bt1.tag_type = bt2.tag_type
  JOIN breaches b ON bt2.breach_id = b.id
  WHERE bt1.breach_id = breach_uuid
    AND bt2.breach_id != breach_uuid
  GROUP BY bt2.breach_id, b.company, b.summary
  ORDER BY shared_tags DESC, b.discovery_date DESC
  LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function: find_company_by_alias (for deduplication)
CREATE OR REPLACE FUNCTION find_company_by_alias(company_name TEXT)
RETURNS TABLE (
  breach_id UUID,
  primary_name TEXT,
  all_aliases TEXT[]
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    b.id,
    b.company,
    ARRAY_AGG(ca.alias) as aliases
  FROM company_aliases ca
  JOIN breaches b ON ca.breach_id = b.id
  WHERE LOWER(ca.alias) = LOWER(company_name)
  GROUP BY b.id, b.company;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Table Comments (Documentation)
-- =============================================================================

COMMENT ON TABLE breaches IS 'Main table storing all data breach incidents with full-text search support';
COMMENT ON TABLE breach_updates IS 'Timeline of updates for each breach (fines, lawsuits, remediation, etc.) with AI confidence scores';
COMMENT ON TABLE breach_tags IS 'Tags for filtering and categorizing breaches (supports continent, country, industry, attack vector, CVE, MITRE, threat actor)';
COMMENT ON TABLE sources IS 'Source articles and references for each breach';
COMMENT ON TABLE company_aliases IS 'Company name variations for deduplication (e.g., Qantas = Qantas Airways = QAN)';
COMMENT ON TABLE breach_views IS 'Analytics tracking for breach views (supports future personalization features)';

COMMENT ON COLUMN breaches.search_vector IS 'Auto-generated tsvector for full-text search (updated via trigger)';
COMMENT ON COLUMN breaches.cve_references IS 'JSONB array of CVE IDs (e.g., ["CVE-2024-1234", "CVE-2024-5678"])';
COMMENT ON COLUMN breaches.mitre_techniques IS 'JSONB array of MITRE ATT&CK technique IDs (e.g., ["T1078", "T1566"])';
COMMENT ON COLUMN breach_updates.confidence_score IS 'AI confidence score (0.0-1.0) for update classification';
COMMENT ON COLUMN breach_updates.ai_reasoning IS 'AI explanation for why this was classified as an update';
COMMENT ON COLUMN company_aliases.is_primary IS 'Whether this is the primary/canonical name for the company';

-- =============================================================================
-- Sample Data (Optional - for testing)
-- =============================================================================

-- Uncomment below to insert sample breach data for testing

/*
INSERT INTO breaches (company, industry, country, continent, discovery_date, records_affected, breach_method, attack_vector, severity, status, summary, lessons_learned, cve_references, mitre_techniques)
VALUES
(
  'Acme Healthcare',
  'Healthcare',
  'United States',
  'North America',
  '2024-01-15',
  2500000,
  'Ransomware attack exploiting unpatched VPN vulnerability',
  'ransomware',
  'critical',
  'confirmed',
  'Acme Healthcare suffered a ransomware attack affecting 2.5M patient records. Attackers gained access through an unpatched VPN server and deployed ransomware across the network.',
  'Organizations must maintain a rigorous patch management process, especially for internet-facing systems. Multi-factor authentication should be enforced on all VPN connections.',
  '["CVE-2023-1234"]',
  '["T1190", "T1486"]'
);

-- Get the breach ID for adding related data
DO $$
DECLARE
  breach_uuid UUID;
BEGIN
  SELECT id INTO breach_uuid FROM breaches WHERE company = 'Acme Healthcare';

  -- Add tags
  INSERT INTO breach_tags (breach_id, tag_type, tag_value) VALUES
    (breach_uuid, 'continent', 'North America'),
    (breach_uuid, 'country', 'United States'),
    (breach_uuid, 'industry', 'Healthcare'),
    (breach_uuid, 'attack_vector', 'ransomware'),
    (breach_uuid, 'cve', 'CVE-2023-1234'),
    (breach_uuid, 'mitre_attack', 'T1190'),
    (breach_uuid, 'mitre_attack', 'T1486');

  -- Add source
  INSERT INTO sources (breach_id, url, title, published_date) VALUES
    (breach_uuid, 'https://example.com/acme-breach', 'Acme Healthcare Suffers Major Ransomware Attack', '2024-01-16');

  -- Add company aliases
  INSERT INTO company_aliases (breach_id, alias, is_primary) VALUES
    (breach_uuid, 'Acme Healthcare', true),
    (breach_uuid, 'Acme', false),
    (breach_uuid, 'Acme Health', false);
END $$;
*/

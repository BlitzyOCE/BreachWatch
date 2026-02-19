# BreachCase Database Design Documentation
The current database structure is presented in current_db.sql

## Overview

The BreachCase database is designed to store and track data breach incidents as "living stories" that continuously evolve with new information. The schema supports AI-powered data extraction, breach deduplication, full-text search, and timeline tracking of updates.

**Database Type:** PostgreSQL (via Supabase)
**Last Updated:** 2024-02-04

---

## Database Architecture

### Core Principles

1. **Normalized Design**: Tags and related data in separate tables for flexibility
2. **AI-First**: Built-in confidence scoring and reasoning storage
3. **Search-Optimized**: Full-text search with weighted ranking
4. **Deduplication-Ready**: Company aliases for matching name variations
5. **Timeline-Based**: Breaches are updated over time, not static records

---

## Tables

### 1. `breaches` (Main Table)

**Purpose:**
Stores core information about each data breach incident. This is the central table that all other tables reference.

**Use Case:**
- Display breach cards on homepage
- Show breach detail pages
- Filter breaches by severity, country, industry
- Search for specific breaches
- Track breach lifecycle from discovery to resolution

**Key Columns:**
- `id` - Unique identifier for each breach
- `company` - Affected company name (primary identifier for users)
- `continent`, `country` - Geographic filtering
- `industry` - Sector filtering (Healthcare, Finance, etc.)
- `discovery_date`, `disclosure_date` - Timeline tracking
- `records_affected` - Scale of breach (used for severity assessment)
- `breach_method` - Human-readable explanation of how breach occurred
- `attack_vector` - Standardized attack type (phishing, ransomware, etc.)
- `data_compromised` - JSONB array of data types exposed
- `severity` - Calculated severity (low/medium/high/critical)
- `threat_actor` - Attribution if known
- `cve_references` - JSONB array of CVE IDs (e.g., ["CVE-2024-1234"])
- `mitre_techniques` - JSONB array of MITRE ATT&CK techniques (e.g., ["T1078"])
- `summary` - AI-generated 2-3 sentence overview
- `lessons_learned` - AI-generated recommendations
- `search_vector` - Auto-generated full-text search index
- `created_at`, `updated_at` - Timestamp tracking

**Why JSONB for CVE/MITRE?**
Each breach can have multiple CVEs and MITRE techniques. JSONB allows flexible storage without creating junction tables, while still enabling queries like "find all breaches with CVE-2024-1234".

**Example Query:**
```sql
-- Find all critical healthcare breaches in the US
SELECT * FROM breaches
WHERE severity = 'critical'
  AND industry = 'Healthcare'
  AND country = 'United States'
ORDER BY discovery_date DESC;
```

---

### 2. `breach_updates` (Timeline Table)

**Purpose:**
Tracks the evolution of each breach over time. Breaches are "living stories" that get updated with fines, lawsuits, remediation efforts, and resolutions.

**Use Case:**
- Display timeline visualization on breach detail pages
- Show "Recently Updated Breaches" section on homepage
- Track when new information emerges about old breaches
- Support manual review queue for AI-classified updates

**Key Columns:**
- `breach_id` - Links to parent breach (foreign key)
- `update_date` - When this update occurred (not when it was added to DB)
- `update_type` - Category: discovery, new_info, class_action, fine, remediation, resolution
- `description` - Human-readable update text
- `source_url` - Link to article reporting this update
- `extracted_data` - JSONB of raw AI-extracted data for this update
- `confidence_score` - AI's confidence (0.0-1.0) that this is an update vs new breach
- `ai_reasoning` - AI's explanation for classification (for review queue)

**Why Separate Table?**
A single breach can have 10+ updates over months/years. Storing updates in the main `breaches` table would create denormalized data and make timeline queries complex.

**Example Query:**
```sql
-- Get all fines issued for a specific breach
SELECT * FROM breach_updates
WHERE breach_id = 'abc-123-def'
  AND update_type = 'fine'
ORDER BY update_date;
```

---

### 3. `breach_tags` (Filtering Table)

**Purpose:**
Provides flexible, filterable categorization of breaches. Tags enable multi-dimensional filtering (by geography, industry, attack type, etc.) without rigid column structures.

**Use Case:**
- Power filter UI (show tag counts: "Healthcare (234), Finance (189)")
- Find related breaches (breaches with shared tags)
- Click-to-filter from breach detail page
- Support future tag types without schema changes

**Key Columns:**
- `breach_id` - Links to parent breach
- `tag_type` - Category: continent, country, industry, attack_vector, cve, mitre_attack, threat_actor
- `tag_value` - Actual tag value (e.g., "North America", "ransomware", "CVE-2024-1234")

**Why Tag Types?**
Allows grouping tags in UI (show all countries together, all industries together) and enables type-specific filtering logic.

**Unique Constraint:**
`UNIQUE(breach_id, tag_type, tag_value)` prevents duplicate tags on same breach.

**Example Query:**
```sql
-- Find all breaches tagged with ransomware
SELECT DISTINCT b.*
FROM breaches b
JOIN breach_tags bt ON b.id = bt.breach_id
WHERE bt.tag_type = 'attack_vector'
  AND bt.tag_value = 'ransomware';
```

**Normalized vs Denormalized Design:**
- ✅ **Chosen**: Separate `breach_tags` table (normalized)
- ❌ **Alternative**: JSONB `tags` column on `breaches` table (denormalized)
- **Reason**: Easier to count tags, join on tags, and build filter UI with normalized approach

---

### 4. `sources` (Attribution Table)

**Purpose:**
Tracks all source articles/reports for each breach. Provides transparency and allows users to verify claims.

**Use Case:**
- Display "Sources" section on breach detail pages
- Track which articles contributed to breach knowledge
- Detect if same article is being processed twice (URL uniqueness)
- Attribution for AI-extracted information

**Key Columns:**
- `breach_id` - Links to parent breach
- `url` - Article URL (UNIQUE - prevents duplicate processing)
- `title` - Article headline
- `published_date` - When article was published

**Why URL Unique Constraint?**
Prevents the scraper from processing the same article multiple times. The scraper checks this table before processing new articles.

**Example Query:**
```sql
-- Get all sources for a breach
SELECT * FROM sources
WHERE breach_id = 'abc-123-def'
ORDER BY published_date DESC;
```

---

### 5. `company_aliases` (Deduplication Table)

**Purpose:**
Handles company name variations to prevent creating duplicate breach records. AI can match "Qantas Airways", "Qantas", and "QAN" to the same breach.

**Use Case:**
- AI update detection (is "Acme Corp" an update to "Acme Corporation" breach?)
- Search functionality (user searches "Acme", finds "Acme Corporation" breach)
- Manual deduplication (admin can add aliases)
- Display alternative names on breach detail page

**Key Columns:**
- `breach_id` - Links to parent breach
- `alias` - Alternative name for the company
- `is_primary` - Whether this is the canonical/display name

**How It Works:**
1. AI extracts company name "Acme Corp" from new article
2. System calls `find_company_by_alias('Acme Corp')`
3. Function returns existing breach if alias matches
4. If match found, create update instead of new breach

**Example Query:**
```sql
-- Find breach by any company name variation
SELECT * FROM find_company_by_alias('Qantas');
-- Returns: breach_id, primary_name='Qantas Airways', aliases=['Qantas Airways', 'Qantas', 'QAN']
```

---

### 6. `breach_views` (Analytics Table)

**Purpose:**
Tracks user interactions with breach pages for analytics and future personalization features.

**Use Case:**
- Track most-viewed breaches
- Build "Trending Breaches" feature
- Personalized recommendations (user views healthcare breaches → recommend similar)
- Analytics dashboard (breach views over time)

**Key Columns:**
- `breach_id` - Which breach was viewed
- `user_id` - Who viewed it (NULL for anonymous users, UUID for logged-in users)
- `ip_address` - For anonymous analytics and anti-spam
- `viewed_at` - Timestamp

**Future Use:**
Currently populated but not displayed. In Phase 6+ can power:
- "Breaches similar to ones you've viewed"
- "Most viewed this week" section
- Browse history for logged-in users

**Example Query:**
```sql
-- Top 10 most viewed breaches this month
SELECT b.company, COUNT(bv.id) as view_count
FROM breach_views bv
JOIN breaches b ON bv.breach_id = b.id
WHERE bv.viewed_at >= NOW() - INTERVAL '30 days'
GROUP BY b.id, b.company
ORDER BY view_count DESC
LIMIT 10;
```

---

## Views

### 1. `breach_summary` (Listing View)

**Purpose:**
Pre-computed, optimized view for homepage and listing pages. Avoids repetitive joins.

**What It Does:**
Joins `breaches`, `breach_updates`, and `sources` to provide:
- All breach core fields
- Count of updates (`update_count`)
- Count of sources (`source_count`)
- Most recent update date (`last_update_date`)

**Use Case:**
- Homepage breach cards (shows "12 updates" badge)
- "Recently Updated Breaches" section (ORDER BY last_update_date)
- Breach listing pages with metadata

**Why a View?**
Avoids writing the same LEFT JOIN logic in every query. Frontend can simply `SELECT * FROM breach_summary`.

**Example Query:**
```sql
-- Recently updated breaches
SELECT * FROM breach_summary
ORDER BY last_update_date DESC NULLS LAST
LIMIT 20;
```

---

### 2. `tag_counts` (Filter UI View)

**Purpose:**
Pre-computed tag frequency counts for building filter UI.

**What It Does:**
Counts how many breaches have each tag value, grouped by tag type.

**Use Case:**
- Build filter sidebar: "Healthcare (234) ☐", "Finance (189) ☐"
- Show popular tags first
- Disable filters with 0 breaches

**Why a View?**
Tag counts change as breaches are added/updated. View always reflects current state without manual cache management.

**Example Query:**
```sql
-- Get all industry tags with counts
SELECT tag_value, breach_count
FROM tag_counts
WHERE tag_type = 'industry'
ORDER BY breach_count DESC;
```

---

## Functions

### 1. `search_breaches(search_query TEXT)`

**Purpose:**
Full-text search across company names, summaries, breach methods, and lessons learned.

**How It Works:**
1. Converts user query to PostgreSQL tsquery
2. Searches `search_vector` column (auto-updated via trigger)
3. Ranks results by relevance using `ts_rank()`
4. Returns matches ordered by rank

**Weighted Search:**
- Company name: Weight A (highest priority)
- Summary: Weight B
- Breach method: Weight C
- Lessons learned: Weight D (lowest priority)

**Use Case:**
Power the search bar on homepage. User types "ransomware healthcare", gets relevant breaches ranked by match quality.

**Example Usage:**
```sql
-- Search for "ransomware healthcare"
SELECT * FROM search_breaches('ransomware healthcare');
```

---

### 2. `get_related_breaches(breach_uuid UUID, max_results INT)`

**Purpose:**
Find breaches similar to a given breach by counting shared tags.

**How It Works:**
1. Get all tags for input breach
2. Find other breaches with same tags
3. Count shared tags per breach
4. Return top N most similar breaches

**Use Case:**
"Related Breaches" section on breach detail page. Shows 3 breaches with most shared tags (same industry, same attack vector, etc.).

**Example Usage:**
```sql
-- Find 3 breaches similar to breach 'abc-123'
SELECT * FROM get_related_breaches('abc-123', 3);
```

**Why Shared Tags?**
More shared tags = more similar breaches. A breach with tags [Healthcare, Ransomware, USA] is similar to another with [Healthcare, Ransomware, Canada].

---

### 3. `find_company_by_alias(company_name TEXT)`

**Purpose:**
Look up breach by any company name variation (for deduplication).

**How It Works:**
1. Searches `company_aliases` table (case-insensitive)
2. Returns breach ID, primary name, and all aliases
3. Used by AI to check if breach already exists

**Use Case:**
- AI extracts "Acme Corp" from article
- Call `find_company_by_alias('Acme Corp')`
- If match found, classify as UPDATE to existing breach
- If no match, create NEW breach

**Example Usage:**
```sql
-- Check if "Qantas" breach exists
SELECT * FROM find_company_by_alias('Qantas');
-- Returns: breach_id, primary_name, all_aliases[]
```

---

## Triggers

### 1. `tsvector_update` (Full-Text Search Trigger)

**Purpose:**
Automatically update `search_vector` column whenever breach data changes.

**How It Works:**
- Fires on INSERT or UPDATE to `breaches` table
- Concatenates company, summary, breach_method, lessons_learned into search vector
- Applies weights (company highest, lessons_learned lowest)

**Why Automatic?**
Ensures search index is always current without manual maintenance. Developers don't need to remember to update search vectors.

---

### 2. `update_breaches_updated_at` (Timestamp Trigger)

**Purpose:**
Automatically set `updated_at` timestamp whenever breach is modified.

**How It Works:**
- Fires on UPDATE to `breaches` table
- Sets `updated_at = NOW()`

**Why Automatic?**
Tracks when breach data last changed without requiring application code to set timestamps.

---

## Indexes

### Performance Strategy

**High-Priority Indexes** (frequently queried columns):
- `idx_breaches_company` - Search by company name
- `idx_breaches_severity` - Filter by severity
- `idx_breaches_country` - Geographic filtering
- `idx_breaches_industry` - Sector filtering
- `idx_breaches_updated_at` - Recently updated sorting
- `idx_breaches_search` - Full-text search (GIN index)

**Tag Indexes:**
- `idx_breach_tags_type_value` - Composite index for tag filtering
- `idx_breach_tags_value` - Tag autocomplete

**Relationship Indexes:**
- `idx_breach_updates_breach_id` - Join optimization
- `idx_sources_breach_id` - Join optimization
- `idx_company_aliases_alias` - Deduplication lookups

---

## Key Design Decisions

### 1. Why Separate `breach_tags` Table?

**Decision:** Normalized design with separate table
**Alternative:** JSONB `tags` column on `breaches` table

**Reasoning:**
- ✅ Easier to count tags (for filter UI: "Healthcare (234)")
- ✅ Easier to join on tags (find breaches with specific tag)
- ✅ Better query performance with indexes
- ✅ Standard SQL queries (no JSONB operators needed)
- ❌ Requires JOIN for tag-based queries (acceptable trade-off)

---

### 2. Why JSONB for CVE/MITRE?

**Decision:** Store as JSONB arrays
**Alternative:** Separate junction tables

**Reasoning:**
- ✅ Simpler schema (6 tables instead of 8+)
- ✅ CVEs/MITRE are read-heavy, write-once (don't need relational benefits)
- ✅ Can still query with `@>` operator: `cve_references @> '["CVE-2024-1234"]'`
- ✅ Flexible - can store metadata like `{"cve": "CVE-2024-1234", "cvss": 9.8}`
- ❌ Can't join on CVE (acceptable - not needed for UI)

---

### 3. Why `company_aliases` Table?

**Decision:** Dedicated table for name variations
**Alternative:** Fuzzy string matching on company name

**Reasoning:**
- ✅ Explicit mapping (no false positives from fuzzy matching)
- ✅ Human review possible (admin can add/remove aliases)
- ✅ Fast lookups (indexed)
- ✅ Supports abbreviations ("QAN" for "Qantas Airways")
- ❌ Requires initial alias population (acceptable - AI can generate)

---

### 4. Why Full-Text Search vs Simple LIKE?

**Decision:** PostgreSQL `tsvector` with GIN index
**Alternative:** `WHERE company LIKE '%search%'`

**Reasoning:**
- ✅ Handles word variations ("breach" matches "breached", "breaching")
- ✅ Relevance ranking (best matches first)
- ✅ Weighted fields (company name more important than lessons learned)
- ✅ Fast even with millions of records (GIN index)
- ❌ More complex setup (acceptable - worth the UX improvement)

---

## Relationships Diagram

```
breaches (1) ──┬──< breach_updates (many)
               ├──< breach_tags (many)
               ├──< sources (many)
               ├──< company_aliases (many)
               └──< breach_views (many)
```

All relationships use `ON DELETE CASCADE` - deleting a breach removes all related data.

---

## Future Enhancements

### Potential Additions (Not Yet Implemented)

1. **Users Table**
   - User authentication and profiles
   - Link to `breach_views.user_id`
   - Enable watchlists and saved breaches

2. **Watchlists Table**
   - User-defined alerts for specific industries/countries
   - Email notifications on new breaches

3. **Comments Table**
   - User comments on breach pages
   - Moderation system

4. **Breach Relationships Table**
   - Link related breaches (supply chain connections)
   - "Breach A led to Breach B"

---

## Maintenance Notes

### Regular Tasks

**Weekly:**
- Monitor `breach_views` table size (can grow large)
- Consider partitioning by date if > 10M rows

**Monthly:**
- Vacuum database (Supabase handles automatically)
- Review `company_aliases` for duplicates

**As Needed:**
- Add new `tag_type` values to CHECK constraint
- Add new `attack_vector` values to CHECK constraint
- Update `update_type` values to CHECK constraint

---

## Query Examples

### Common Operations

**1. Get full breach detail with all related data:**
```sql
SELECT
  b.*,
  json_agg(DISTINCT bu.*) as updates,
  json_agg(DISTINCT bt.*) as tags,
  json_agg(DISTINCT s.*) as sources
FROM breaches b
LEFT JOIN breach_updates bu ON b.id = bu.breach_id
LEFT JOIN breach_tags bt ON b.id = bt.breach_id
LEFT JOIN sources s ON b.id = s.breach_id
WHERE b.id = 'abc-123'
GROUP BY b.id;
```

**2. Filter breaches by multiple tags:**
```sql
SELECT DISTINCT b.*
FROM breaches b
JOIN breach_tags bt ON b.id = bt.breach_id
WHERE (bt.tag_type = 'industry' AND bt.tag_value = 'Healthcare')
   OR (bt.tag_type = 'attack_vector' AND bt.tag_value = 'ransomware');
```

**3. Find breaches updated in last 7 days:**
```sql
SELECT * FROM breach_summary
WHERE last_update_date >= NOW() - INTERVAL '7 days'
ORDER BY last_update_date DESC;
```

---

## Contact & Questions

For questions about database design decisions or schema changes, refer to:
- **Architecture Doc**: `docs/product.md`
- **Progress Tracking**: `docs/PROGRESS.md`
- **Schema File**: `database/enhanced_schema.sql`

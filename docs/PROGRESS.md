# BreachCase - Development Progress

## Project Status: 🟡 Phase 1 Complete - Building Backend

---

## ✅ Phase 1: Database Foundation (COMPLETED - 2024-02-04)

### What We Built
- **Supabase Project**: Created "BreachCase" production instance
- **Enhanced Database Schema**: 6 tables, 2 views, 3 utility functions
- **File**: `database/enhanced_schema.sql`

### Tables Created
1. ✅ `breaches` - Main breach records (with continent, CVE, MITRE, full-text search)
2. ✅ `breach_updates` - Timeline updates (with confidence scores & AI reasoning)
3. ✅ `breach_tags` - Filterable tags (continent, country, industry, attack vector, CVE, MITRE, threat actor)
4. ✅ `sources` - Article URLs and metadata
5. ✅ `company_aliases` - Company name variations for deduplication
6. ✅ `breach_views` - Analytics tracking for future personalization

### Utility Views
1. ✅ `breach_summary` - Pre-joined data for homepage/listing pages
2. ✅ `tag_counts` - Tag frequency counts for filter UI

### Utility Functions
1. ✅ `search_breaches(query)` - Full-text search with ranking
2. ✅ `get_related_breaches(id)` - Find similar breaches by shared tags
3. ✅ `find_company_by_alias(name)` - Deduplication lookup

### Key Features Implemented
- ✅ Full-text search with auto-updating search vector
- ✅ Continent support for geographic filtering
- ✅ CVE and MITRE ATT&CK technique storage
- ✅ Confidence scoring for AI-generated updates
- ✅ Company name deduplication system
- ✅ Analytics tracking infrastructure
- ✅ Automatic timestamp triggers
- ✅ Comprehensive indexes for performance

---

## [RUNNING] Phase 2: Python Scraper (BUILT & RUNNING - 2026-02-13)

### What We Built
- **Complete scraper system** with 6 Python modules + audit tool
- **8 RSS feed sources** configured (BleepingComputer, The Hacker News, etc.)
- **Two-Stage AI Processing** for cost optimization (2026-02-06)
- **Three-way update detection** (NEW_BREACH / GENUINE_UPDATE / DUPLICATE_SOURCE) (2026-02-13)
- **In-run fuzzy deduplication** to prevent same-run duplicate breaches (2026-02-13)
- **Local caching** with deduplication
- **Comprehensive logging** and error handling
- **Database audit tool** (`audit.py`) for data quality checks

### Key Features
- ✅ Stage 1: Fast classification to identify breach articles (saves 40-60% on API costs)
- ✅ Stage 2: Detailed extraction for confirmed breaches
- ✅ Three-way update detection: NEW_BREACH / GENUINE_UPDATE / DUPLICATE_SOURCE
- ✅ Parallel RSS feed fetching from 8 sources
- ✅ URL-based deduplication (across sources)
- ✅ In-run fuzzy company name deduplication (within a single run, pre-AI)
- ✅ Processed ID tracking to prevent reprocessing across runs
- ✅ Configurable confidence thresholds
- ✅ `audit.py` - data quality tool with duplicate detection, missing field analysis, CSV export


### Completed Setup Steps
- ✅ .env configured with DeepSeek + Supabase credentials
- ✅ Virtual environment and dependencies installed
- ✅ All modules tested and running
- ✅ Full scraper runs verified end-to-end
- ⬜ Set up daily cron job for automation

---

## ⬜ Phase 3: API Integration

### Planned
- Get Anthropic API key
- Implement ai_processor.py
- Extract structured data from articles
- Test with cached articles
- Implement retry logic

---

## ⬜ Phase 4: Next.js Website

### Planned
- Create Next.js app with TypeScript
- Set up Supabase client
- Build homepage with breach cards
- Build breach detail pages
- Implement basic filtering

---

## ⬜ Phase 5: UI Polish & Components

### Planned
- Install shadcn/ui
- Build BreachCard component
- Build BreachTimeline component
- Build FilterBar component
- Add search functionality

---

## ⬜ Phase 6: Advanced AI Features

### Planned
- Implement update detection
- Implement breach deduplication
- Add confidence scoring
- Build manual review queue

---

## ⬜ Phase 7: Automation & Deployment

### Planned
- Add cron scheduling
- Deploy website to Vercel
- Deploy scraper to Render/Railway
- Set up monitoring

---

## Key Decisions Made

### Database Design
- **Normalized approach**: Tags in separate table (better for filtering)
- **JSONB for flexibility**: CVE references, MITRE techniques, data_compromised
- **Full-text search**: Using PostgreSQL tsvector with GIN index
- **Deduplication strategy**: Company aliases table instead of fuzzy matching
- **Confidence scoring**: Added to breach_updates for manual review queue

### Tech Stack Confirmed
- ✅ Supabase (PostgreSQL + REST API)
- ✅ Python 3.11+ for scraper
- ✅ Claude API (Sonnet 4.5) for AI processing
- ✅ Next.js 14+ with TypeScript for frontend
- ✅ Tailwind CSS + shadcn/ui for styling

---

## Session Notes

### 2026-02-13 (QA) - Feed Cleanup + Audit Improvements

**SecurityWeek removed** (`config.py`):
- SecurityWeek feed was returning 403 errors consistently, removed from `RSS_SOURCES`
- Source count is now 8

**Audit improvements** (`audit.py`):
- `disclosure_date` added to `IMPORTANT_FIELDS` (was missing; articles report public disclosure dates, not internal discovery dates)
- Audit summary now prints both `discovery_date` and `disclosure_date` missing counts

**Test script fixes** (`test_scraper.py`):
- Timeout bumped from 5 min to 20 min to accommodate large backlogs
- `disclosure_date` added to extraction quality field coverage report
- Update detection counter split into three separate lines: `New breaches`, `Genuine updates`, `Duplicate sources skipped`

**Root cause identified - not fixed**: `ARTICLE_LOOKBACK_HOURS=50000` in `.env` causes all ~400+ feed articles to be treated as "recent" on any fresh-cache run, which always hits the 20-min timeout. Normal daily runs (with populated `processed_ids.txt`) process only 5-15 new articles and complete in ~2 minutes.

---

### 2026-02-13 - Three-Way Update Detection + In-Run Fuzzy Deduplication

**Root cause of Betterment duplicate**: two consecutive runs (19 min apart, different sources) both passed as NEW_BREACH because `detect_update()` only had a binary decision and no structured fields to compare against.

**Three-way update detection** (`config.py`, `ai_processor.py`, `db_writer.py`, `main.py`):
- Rewrote `UPDATE_DETECTION_PROMPT` to classify as `NEW_BREACH`, `GENUINE_UPDATE`, or `DUPLICATE_SOURCE`
- `DUPLICATE_SOURCE`: same incident, different outlet, no new facts -> skip DB write entirely
- `GENUINE_UPDATE`: same incident but adds revised record count, regulatory action, new attack detail, etc. -> `write_breach_update()`
- Added `records_affected` and `attack_vector` to `get_existing_breaches()` select so the AI has structured fields to compare
- Added `duplicates_skipped` counter to run stats

**In-run fuzzy deduplication** (`main.py`):
- Added `find_in_run_duplicate()` using `difflib.SequenceMatcher` (threshold 0.85) as a pre-AI fast check within a single run
- If matched, forces `is_update=True` with `confidence=1.0` and skips the AI call

**Feed fixes** (`config.py`):
- Replaced broken `cert_be` (`https://cert.be/en/rss` returned malformed XML) with `securityweek` (`https://www.securityweek.com/feed/`) - later removed, see 2026-02-13 (QA) session note

**Windows logging fix** (`main.py`):
- Console handler now wraps stdout with `io.TextIOWrapper(encoding='utf-8', errors='replace')` to prevent crashes on non-ASCII article titles

### 2026-02-06 - Two-Stage AI Classification Implementation
- Implemented two-stage AI approach for cost optimization
- Added CLASSIFICATION_PROMPT to config.py for fast breach detection
- Created classify_article() method in ai_processor.py
- Updated main.py with Stage 1 (classification) and Stage 2 (extraction) logic
- Added classification statistics tracking (classified_as_breach, classified_as_non_breach)
- Configured ENABLE_CLASSIFICATION and CLASSIFICATION_CONFIDENCE_THRESHOLD settings
- Updated documentation (README.md, .env.example)
- Expected cost savings: 40-60% through filtering non-breach articles before extraction

### 2024-02-04 - Database Foundation
- Created enhanced schema with 6 tables
- Added continent support for geographic filtering
- Implemented full-text search with weighted ranking
- Built deduplication system with company_aliases table
- Added confidence scoring for AI-generated updates
- Created utility views and functions for common queries
- Successfully deployed to Supabase production

---

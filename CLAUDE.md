# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BreachWatch is an AI-powered data breach intelligence platform that aggregates breach news from RSS feeds, extracts structured data using DeepSeek AI, and stores results in Supabase. Breaches are treated as "living stories" with timeline updates.

**Current Status**: Phase 2 complete (Python scraper built). Next.js frontend not yet implemented.

## Architecture

```
RSS Feeds -> feed_parser.py -> cache_manager.py -> ai_processor.py -> db_writer.py -> Supabase
```

**Three-Stage Article Processing** (in `main.py`):
1. **Classification** (`classify_article`): Fast/cheap yes/no - is this a breach article?
2. **Extraction** (`extract_breach_data`): Full structured data extraction for confirmed breaches
3. **Update detection** (`detect_update` + in-run fuzzy dedup): Is this a new breach, an update to existing, or a duplicate source?

**Duplicate Detection is Two-Layered**:
- In-run fuzzy match: `SequenceMatcher` on company name (threshold: `FUZZY_MATCH_THRESHOLD=0.85`) catches same-company articles in the same scraper run before DB lookup is possible
- AI-based: `detect_update()` compares article against last 90 days of DB breaches and returns `NEW_BREACH | GENUINE_UPDATE | DUPLICATE_SOURCE`

## Development Commands

### Scraper Setup (Windows)
```bash
cd scraper
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Edit scraper/.env with real API keys (DEEPSEEK_API_KEY, SUPABASE_URL, SUPABASE_KEY)
```

### Run Scraper
```bash
cd scraper
python main.py
```

### Test Individual Modules
```bash
# Run from repo root (not scraper/):
python scraper/feed_parser.py      # Test RSS fetching (no API keys needed)
python scraper/cache_manager.py    # Test caching (no API keys needed)
python scraper/ai_processor.py     # Test AI extraction (requires DEEPSEEK_API_KEY)
python scraper/db_writer.py        # Test database connection (requires SUPABASE credentials)
```

### Audit Database
```bash
cd scraper
python audit.py              # Full audit report (breaches, duplicates, missing fields)
python audit.py --duplicates # Show only potential duplicates
python audit.py --csv        # Export all data to CSV files in audit_export/
```

## Key Files

### Scraper Modules (`scraper/`)
- **main.py** - Orchestrator: 7-step workflow from RSS fetch to DB write, tracks per-run stats
- **config.py** - All configuration, RSS sources (8 feeds), AI prompts (`CLASSIFICATION_PROMPT`, `EXTRACTION_PROMPT`, `UPDATE_DETECTION_PROMPT`), and all env-overridable settings
- **feed_parser.py** - Parallel RSS fetching via `ThreadPoolExecutor`, date filtering, URL deduplication
- **cache_manager.py** - `scraper/cache/processed_ids.txt` persists processed URLs across runs; also caches raw articles and extraction results as JSON per-day
- **ai_processor.py** - DeepSeek API via OpenAI Python client with custom `base_url`; uses `@backoff.on_exception` for retries
- **db_writer.py** - Supabase writes: `write_new_breach()` inserts into `breaches` + `breach_tags` + `sources`; `write_breach_update()` inserts into `breach_updates` + `sources`
- **audit.py** - Data quality audit: duplicate detection, missing field analysis, CSV export

### Database (`database/`)
- **current_db.sql** - Full PostgreSQL schema for Supabase
- **DATABASE_DESIGN.md** - Detailed documentation of all tables, views, and functions

### Documentation (`docs/`)
- **product.md** - Technical architecture and data flow
- **PROGRESS.md** - Development status and session notes

## Database Schema Summary

Six tables with `ON DELETE CASCADE` from `breaches`:
- `breaches` - Core breach record; `attack_vector` has a CHECK constraint: `phishing|ransomware|api_exploit|insider|supply_chain|misconfiguration|malware|ddos|other`; `severity`: `low|medium|high|critical`; `status`: `investigating|confirmed|resolved`
- `breach_updates` - Timeline entries for each new development (fines, lawsuits, remediation)
- `breach_tags` - Normalized tags (type + value) for continent, country, industry, attack_vector, cve, mitre_attack, threat_actor
- `sources` - Source article URLs (UNIQUE constraint prevents duplicate processing)
- `company_aliases` - Name variations for deduplication
- `breach_views` - Analytics (not yet used in UI)

DB views: `breach_summary` (join with update/source counts), `tag_counts` (filter UI counts)
DB functions: `search_breaches()` (weighted full-text via tsvector), `get_related_breaches()` (shared tags), `find_company_by_alias()`

## Configuration Notes

All settings in `config.py` can be overridden via `.env` environment variables:
- `ARTICLE_LOOKBACK_HOURS` (default: 48) - How far back to fetch articles
- `ENABLE_CLASSIFICATION` (default: True) - Toggle Stage 1 classification
- `CLASSIFICATION_CONFIDENCE_THRESHOLD` (default: 0.6) - Minimum confidence to proceed
- `MAX_EXISTING_BREACHES_CONTEXT` (default: 50) - How many breaches to include in AI update-detection prompt
- `FUZZY_MATCH_THRESHOLD` (default: 0.85) - Company name similarity for in-run dedup

## Logs

Written to `scraper/logs/`:
- `scraper_YYYY-MM-DD.log` - Full execution log (DEBUG level)
- `errors_YYYY-MM-DD.log` - Errors only


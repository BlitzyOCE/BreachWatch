# CLAUDE.md

## Project

BreachWatch - AI-powered data breach intelligence platform. RSS feeds -> DeepSeek AI extraction -> Supabase -> Next.js frontend. Breaches are "living stories" with timeline updates.

## Architecture

```
RSS Feeds -> feed_parser.py -> cache_manager.py -> ai_processor.py -> db_writer.py -> Supabase <- Next.js frontend
```

**Scraper** (`scraper/`): 3-stage article processing in `main.py` - classify (breach yes/no) -> extract (structured data) -> detect update (new/update/duplicate via AI + fuzzy matching). Config in `config.py`, all settings env-overridable.

**Frontend** (`frontend/`): Next.js 16 + React 19 + Supabase + shadcn/ui + Tailwind v4. Pages: home (breach list), breach detail (`/breach/[id]`), search with filters, about. Components organized into `breach/`, `search/`, `layout/`, `ui/`.

**Database** (`database/`): PostgreSQL on Supabase. Six tables cascading from `breaches`: `breach_updates`, `breach_tags`, `sources`, `company_aliases`, `breach_views`. Schema in `current_db.sql`, docs in `DATABASE_DESIGN.md`.

## Commands

```bash
# Scraper
cd scraper && python main.py           # Run scraper
cd scraper && python audit.py          # Audit DB (--duplicates, --csv)
cd scraper && python test_scraper.py   # Test scraper

# Frontend
cd frontend && npm run dev             # Dev server
cd frontend && npm run build           # Production build
```

## Key Config

Scraper `.env`: `DEEPSEEK_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `ARTICLE_LOOKBACK_HOURS` (48), `FUZZY_MATCH_THRESHOLD` (0.85), `CLASSIFICATION_CONFIDENCE_THRESHOLD` (0.6).

Frontend `.env.local`: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

## Logs

`scraper/logs/scraper_YYYY-MM-DD.log` (debug), `errors_YYYY-MM-DD.log` (errors only).

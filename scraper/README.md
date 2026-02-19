# BreachCase Scraper

Python-based breach news aggregation scraper that fetches articles from 10 RSS feeds, uses DeepSeek AI for data extraction, and stores results in Supabase.

## Features

- **10 RSS Feed Sources**: BleepingComputer, The Hacker News, DataBreachToday, Dark Reading, Krebs, HelpNet Security, CERT.be, NCSC UK, Check Point Research, Have I Been Pwned
- **Two-Stage AI Processing**: Fast classification filter before expensive extraction (40-60% cost savings)
- **AI-Powered Extraction**: Uses DeepSeek API to extract structured breach data
- **Update Detection**: Automatically identifies if articles are updates to existing breaches
- **Local Caching**: Saves raw articles and prevents duplicate processing
- **Database Integration**: Writes to Supabase (PostgreSQL) with proper schema
- **Comprehensive Logging**: Daily logs with error tracking and classification metrics

## Architecture

```
RSS Feeds -> feed_parser.py -> cache_manager.py -> ai_processor.py -> db_writer.py -> Supabase
                                                    |
                                                    Stage 1: Classification (Fast & Cheap)
                                                    Stage 2: Extraction (Detailed & Expensive)
```

### Two-Stage AI Processing

The scraper uses a two-stage AI approach to optimize cost and performance:

**Stage 1: Classification**
- Quick yes/no: "Is this article about a data breach?"
- Uses fewer tokens (~100-200 vs 1000+)
- Filters out 40-60% of non-breach articles
- Configurable confidence threshold (default: 0.7)

**Stage 2: Full Extraction**
- Only runs on articles classified as breaches
- Extracts detailed structured data
- Performs update detection
- Writes to database

**Cost Savings**: Classification is ~90% cheaper than extraction, resulting in 40-60% overall cost reduction while maintaining accuracy.

**Configuration**: Set `ENABLE_CLASSIFICATION=False` in `.env` to disable and process all articles.

## Setup

### 1. Install Dependencies

```bash
cd scraper/
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required API Keys
DEEPSEEK_API_KEY=sk-your-deepseek-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Optional Configuration
ENABLE_CLASSIFICATION=True  # Enable two-stage AI (recommended)
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.7  # Minimum confidence for breach classification
ARTICLE_LOOKBACK_HOURS=48  # How far back to fetch articles
```

### 3. Test the Scraper

```bash
python main.py
```

## Usage

### Run Manually

```bash
python main.py
```

### Schedule Daily Runs

#### Linux/Mac (cron)

```bash
crontab -e
```

Add line:
```
0 8 * * * cd /path/to/BreachBase/scraper && /path/to/venv/bin/python main.py >> logs/cron.log 2>&1
```

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 8:00 AM
4. Action: Start a program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `main.py`
   - Start in: `C:\path\to\BreachBase\scraper`

## File Structure

```
scraper/
├── main.py                 # Main orchestrator
├── config.py               # Configuration & prompts
├── feed_parser.py          # RSS feed fetching
├── cache_manager.py        # Local caching
├── ai_processor.py         # DeepSeek AI integration
├── db_writer.py            # Supabase database writing
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment variables
├── .env                    # Your actual env vars (gitignored)
├── cache/                  # Article cache
│   ├── raw_2026-02-04.json
│   └── processed_ids.txt
└── logs/                   # Log files
    ├── scraper_2026-02-04.log
    └── errors_2026-02-04.log
```

## Modules

### feed_parser.py
Fetches and parses RSS feeds from 10 sources in parallel, filters recent articles (last 48 hours), and deduplicates by URL.

**Key Functions:**
- `fetch_all_feeds()` - Fetch from all sources
- `filter_recent_articles()` - Filter by date
- `deduplicate_by_url()` - Remove duplicates

### cache_manager.py
Manages local file cache, tracks processed article URLs, and prevents duplicate processing.

**Key Functions:**
- `get_new_articles()` - Filter already-processed
- `cache_articles()` - Save raw articles
- `save_processed_id()` - Mark as processed

### ai_processor.py
DeepSeek API integration for extracting structured breach data and detecting updates.

**Key Functions:**
- `extract_breach_data()` - Extract structured data
- `detect_update()` - Identify if article is update
- `call_api()` - API wrapper with retry logic

### db_writer.py
Supabase database integration for writing breaches, updates, tags, and sources.

**Key Functions:**
- `write_new_breach()` - Insert new breach
- `write_breach_update()` - Insert update
- `get_existing_breaches()` - Fetch for matching

## Configuration

Edit `config.py` to modify:

- RSS feed sources
- AI prompts for extraction
- Retry limits and timeouts
- Cache directory paths

## Logging

Logs are written to:
- `logs/scraper_YYYY-MM-DD.log` - Full log
- `logs/errors_YYYY-MM-DD.log` - Errors only
- Console output during execution

## Testing Individual Modules

Each module has a `if __name__ == '__main__'` section for standalone testing:

```bash
# Test RSS fetching
python feed_parser.py

# Test caching
python cache_manager.py

# Test AI extraction (requires DEEPSEEK_API_KEY)
python ai_processor.py

# Test database connection (requires SUPABASE credentials)
python db_writer.py
```

## Troubleshooting

### No articles fetched
- Check internet connection
- Verify RSS feed URLs are still valid
- Check logs for specific feed errors

### AI extraction fails
- Verify DEEPSEEK_API_KEY is set correctly
- Check DeepSeek API quota/limits
- Review logs for API errors

### Database errors
- Verify SUPABASE_URL and SUPABASE_KEY
- Check database schema matches enhanced_schema.sql
- Ensure tables exist in Supabase

### Duplicate processing
- Check `cache/processed_ids.txt` exists
- Verify file permissions
- Check for concurrent runs


## Future Enhancements

- [ ] Full article text fetching (beyond RSS summary)
- [ ] Additional non-English sources
- [ ] Webhook notifications for critical breaches
- [ ] Human review queue for low-confidence extractions
- [ ] Duplicate breach merging
- [ ] Source reliability scoring


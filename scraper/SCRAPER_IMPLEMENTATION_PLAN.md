# Python Scraper Implementation Plan

## Overview
Building a Python-based breach news aggregation scraper that fetches articles from 10 RSS feeds daily, uses DeepSeek AI to extract structured data, and stores results in Supabase.

## System Architecture

### Data Flow
```
RSS Feeds (10 sources)
    → feed_parser.py (fetch & parse)
    → cache_manager.py (deduplicate & cache)
    → ai_processor.py (DeepSeek extraction & update detection)
    → db_writer.py (Supabase storage)
    → Daily summary log
```

## Module Breakdown

### 1. config.py
**Purpose**: Central configuration management

**Contents**:
- RSS feed sources (10 feeds with names and URLs)
- DeepSeek API settings (endpoint, model, timeout)
- Supabase connection settings (URL, key)
- File paths (cache directory, processed IDs file)
- Extraction prompts (for AI processing)
- Constants (date ranges, retry limits)

**Key Constants**:
```python
RSS_SOURCES = {
    'bleepingcomputer': 'https://www.bleepingcomputer.com/feed/',
    'thehackernews': 'https://thehackernews.com/feeds/posts/default',
    # ... 8 more sources
}

DEEPSEEK_MODEL = 'deepseek-chat'
ARTICLE_LOOKBACK_HOURS = 48  # Only process articles from last 48h
MAX_RETRIES = 3
```

### 2. feed_parser.py
**Purpose**: Fetch and parse RSS feeds

**Functions**:
- `fetch_feed(source_name, url)` → Returns list of articles
- `parse_article(entry)` → Extracts: title, URL, published_date, summary
- `fetch_all_feeds()` → Fetches all 10 sources in parallel
- `filter_recent_articles(articles, hours=48)` → Filters by date

**Key Logic**:
- Use `feedparser` library for RSS parsing
- Parse different feed formats (RSS 2.0, Atom)
- Extract publication dates (handle various date formats)
- Return standardized article dictionaries

**Output Format**:
```python
{
    'source': 'bleepingcomputer',
    'url': 'https://...',
    'title': 'Company X Suffers Data Breach',
    'published': datetime object,
    'summary': 'Brief description...',
    'full_text': None  # Filled later if needed
}
```

### 3. cache_manager.py
**Purpose**: Local file caching and deduplication

**Functions**:
- `load_processed_ids()` → Load list of already-processed article URLs
- `save_processed_id(url)` → Append URL to processed list
- `is_processed(url)` → Check if article already processed
- `cache_articles(articles, date)` → Save raw articles to JSON
- `load_cached_articles(date)` → Load articles from cache
- `get_new_articles(articles)` → Filter out already-processed

**File Structure**:
```
cache/
├── raw_2026-02-04.json          # Daily raw articles
├── processed_ids.txt             # One URL per line
└── extraction_results_2026-02-04.json  # AI extraction results
```

**Key Logic**:
- Check article URL against processed_ids.txt before processing
- Save raw articles daily for debugging/replay
- Atomic writes to prevent corruption

### 4. ai_processor.py
**Purpose**: DeepSeek API integration for data extraction

**Functions**:
- `extract_breach_data(article)` → Extract structured data from article
- `detect_update(article, existing_breaches)` → Determine if NEW or UPDATE
- `call_deepseek_api(prompt, context)` → Generic API caller with retry
- `validate_extraction(data)` → Validate JSON schema

**AI Prompts** (from product.md):

**Extraction Prompt**:
```
You are a cybersecurity analyst extracting structured breach data.

Article Title: {title}
Article URL: {url}
Article Text: {text}

Extract the following information in JSON format:
{
  "company": "Company name",
  "industry": "Industry sector",
  "country": "Country/region",
  "discovery_date": "YYYY-MM-DD or null",
  "records_affected": number or null,
  "breach_method": "Description of how breach occurred",
  "attack_vector": "phishing|ransomware|api_exploit|insider|supply_chain|misconfiguration|other",
  "data_compromised": ["type1", "type2"],
  "severity": "low|medium|high|critical",
  "cve_references": ["CVE-XXXX-XXXXX"] or [],
  "mitre_attack_techniques": ["T1078", "T1566"] or [],
  "summary": "2-3 sentence executive summary",
  "lessons_learned": "What security controls failed and recommendations"
}

If information is not mentioned, use null. Be factual and avoid speculation.
```

**Update Detection Prompt**:
```
You are determining if this article is about a NEW breach or an UPDATE to an existing breach.

Article: {article_text}

Existing breaches in database (last 90 days):
{list_of_existing_breaches}

Analyze:
1. Does this article discuss any of the existing breaches?
2. Is this new information about a known incident?

Return JSON:
{
  "is_update": true|false,
  "related_breach_id": "uuid or null",
  "update_type": "new_info|class_action|fine|remediation|resolution|null",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}
```

**Error Handling**:
- Retry failed API calls up to 3 times with exponential backoff
- Log failures to separate error file
- Continue processing other articles if one fails
- Validate JSON schema before returning

### 5. db_writer.py
**Purpose**: Write data to Supabase

**Functions**:
- `init_supabase_client()` → Initialize Supabase connection
- `write_new_breach(breach_data, source_info)` → Insert new breach
- `write_breach_update(update_data, breach_id, source_info)` → Insert update
- `write_tags(breach_id, tags)` → Insert breach tags
- `write_source(source_info)` → Insert source article
- `get_existing_breaches(days=90)` → Fetch recent breaches for matching

**Database Tables** (from enhanced_schema.sql):
- `breaches` - Main breach records
- `breach_updates` - Timeline updates
- `breach_tags` - Tag associations
- `sources` - Article URLs and metadata
- `company_aliases` - For deduplication

**Transaction Logic**:
```python
# For NEW breach:
1. Insert into breaches → get breach_id
2. Insert tags into breach_tags
3. Insert source into sources
4. Commit transaction

# For UPDATE:
1. Insert into breach_updates
2. Update breaches.updated_at
3. Insert source into sources
4. Commit transaction
```

**Error Handling**:
- Use database transactions for atomicity
- Handle duplicate key errors gracefully
- Log database errors separately
- Rollback on failure

### 6. main.py
**Purpose**: Orchestrate the entire scraper workflow

**In-Run Deduplication (added 2026-02-13)**:

Before calling `detect_update()` via AI, `main.py` runs a fast Python-side check using `difflib.SequenceMatcher`:

```python
FUZZY_MATCH_THRESHOLD = 0.85

def find_in_run_duplicate(company, existing_breaches):
    for breach in existing_breaches:
        if _company_similarity(company, breach['company']) >= FUZZY_MATCH_THRESHOLD:
            return breach
    return None
```

If a match is found, the article is forced as an `update` with `confidence=1.0` and the DeepSeek API call is skipped entirely. This handles the case where two articles about the same company arrive in the same RSS run before either is in the database. `detect_update()` alone cannot catch this because it queries the DB, which has neither entry yet.

**Main Workflow**:
```python
def main():
    # 1. Initialization
    logger = setup_logging()
    config = load_config()

    # 2. Fetch RSS Feeds
    logger.info("Fetching RSS feeds from 10 sources...")
    raw_articles = feed_parser.fetch_all_feeds()
    logger.info(f"Fetched {len(raw_articles)} total articles")

    # 3. Filter Recent Articles
    recent_articles = feed_parser.filter_recent_articles(raw_articles, hours=48)
    logger.info(f"Filtered to {len(recent_articles)} recent articles")

    # 4. Deduplication Check
    cache_manager.cache_articles(raw_articles, date.today())
    new_articles = cache_manager.get_new_articles(recent_articles)
    logger.info(f"Found {len(new_articles)} new articles after deduplication")

    # 5. Fetch Existing Breaches (for update detection)
    existing_breaches = db_writer.get_existing_breaches(days=90)

    # 6. Process Each Article
    stats = {'breaches_created': 0, 'updates_created': 0, 'duplicates_skipped': 0, 'errors': 0}

    for article in new_articles:
        try:
            # Extract structured data
            extracted = ai_processor.extract_breach_data(article)

            # Fast in-run fuzzy check before AI call
            in_run_match = find_in_run_duplicate(extracted['company'], existing_breaches)
            if in_run_match:
                update_check = {'is_update': True, 'related_breach_id': in_run_match['id'], 'confidence': 1.0}
            else:
                # Three-way AI classification: NEW_BREACH / GENUINE_UPDATE / DUPLICATE_SOURCE
                update_check = ai_processor.detect_update(article, existing_breaches)

            is_duplicate = update_check.get('is_duplicate_source', False)
            is_genuine_update = update_check['is_update'] and update_check['confidence'] >= 0.7 and not is_duplicate

            if is_genuine_update:
                db_writer.write_breach_update(extracted, update_check['related_breach_id'], article)
                stats['updates_created'] += 1
            elif is_duplicate:
                # Different outlet, same facts -- skip DB write
                stats['duplicates_skipped'] += 1
            else:
                breach_id = db_writer.write_new_breach(extracted, article)
                existing_breaches.append({...})  # for in-run detection of subsequent articles
                stats['breaches_created'] += 1

            cache_manager.save_processed_id(article['url'])

        except Exception as e:
            logger.error(f"Error processing {article['url']}: {e}")
            stats['errors'] += 1
            continue

    # 7. Summary
    logger.info(f"Scraper completed: {stats['breaches_created']} new, "
                f"{stats['updates_created']} updates, {stats['duplicates_skipped']} duplicates skipped, "
                f"{stats['errors']} errors")

    return stats
```

**Logging**:
- Daily log file: `logs/scraper_2026-02-04.log`
- Console output for real-time monitoring
- Separate error log: `logs/errors_2026-02-04.log`

## File Structure

```
BreachBase/
├── scraper/
│   ├── main.py                    # Main orchestrator
│   ├── config.py                  # Configuration & constants
│   ├── feed_parser.py             # RSS fetching
│   ├── cache_manager.py           # Local caching
│   ├── ai_processor.py            # DeepSeek integration
│   ├── db_writer.py               # Supabase writing
│   ├── requirements.txt           # Dependencies
│   ├── .env.example               # Example env vars
│   ├── .env                       # Actual env vars (gitignored)
│   ├── cache/                     # Article cache
│   │   ├── raw_2026-02-04.json
│   │   └── processed_ids.txt
│   └── logs/                      # Log files
│       ├── scraper_2026-02-04.log
│       └── errors_2026-02-04.log
```

## Dependencies (requirements.txt)

```
feedparser==6.0.11          # RSS parsing
requests==2.31.0            # HTTP requests
httpx==0.27.0               # Alternative HTTP client (async capable)
supabase==2.3.4             # Supabase client
python-dotenv==1.0.0        # Environment variables
openai==1.12.0              # For DeepSeek API (OpenAI-compatible)
pydantic==2.6.1             # Data validation
python-dateutil==2.8.2      # Date parsing
schedule==1.2.1             # Job scheduling (optional)
```

## Environment Variables (.env)

```bash
# DeepSeek API
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Optional
LOG_LEVEL=INFO
CACHE_DIR=./cache
```

## Deployment & Scheduling

### Local Testing
```bash
cd scraper/
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with actual keys
python main.py
```

### Daily Scheduling

**Option 1: Cron (Linux/Mac)**
```bash
# Run daily at 8:00 AM UTC
0 8 * * * cd /path/to/BreachBase/scraper && /path/to/venv/bin/python main.py >> logs/cron.log 2>&1
```

**Option 2: Windows Task Scheduler**
- Create task to run `python main.py` daily at 8:00 AM
- Set working directory to scraper folder

**Option 3: Cloud Deployment** (Future)
- Render.com: Deploy as scheduled job
- Railway: Deploy with cron service
- AWS Lambda: Triggered by EventBridge

## Testing Strategy

### Phase 1: Module Testing
1. Test `feed_parser.py` - Fetch 1 feed, verify parsing
2. Test `cache_manager.py` - Write/read cache, check deduplication
3. Test `ai_processor.py` - Extract data from sample article
4. Test `db_writer.py` - Write test breach to Supabase

### Phase 2: Integration Testing
1. Run `main.py` with limited sources (1-2 feeds)
2. Verify end-to-end flow without errors
3. Check database for inserted records
4. Verify logs are created correctly

### Phase 3: Production Testing
1. Run with all 10 sources
2. Monitor for duplicates
3. Verify update detection works
4. Check AI extraction quality (manual review of 10 breaches)

## Success Metrics

- **Uptime**: Scraper runs successfully daily without manual intervention
- **Coverage**: Fetches 20-50 articles/day from 10 sources
- **Quality**: 80%+ AI extraction accuracy (manual spot check)
- **Deduplication**: <5% duplicate breach entries
- **Update Detection**: 70%+ accuracy in identifying updates vs new breaches

## Future Enhancements

1. **Full Article Fetching**: Currently uses RSS summary, could fetch full HTML
2. **Source Prioritization**: Mark certain sources as more authoritative
3. **Duplicate Merging**: Automatically merge duplicate breach entries
4. **Human Review Queue**: Flag low-confidence extractions for manual review
5. **Webhooks**: Send Slack/email notifications on new critical breaches
6. **Monitoring Dashboard**: Real-time scraper health monitoring
7. **A/B Testing**: Compare DeepSeek vs other AI models for extraction quality

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| RSS feed goes down | Continue processing other feeds, log error |
| DeepSeek API rate limits | Implement exponential backoff, queue articles |
| Invalid/malformed RSS | Graceful error handling, skip malformed entries |
| Database connection loss | Retry logic, cache failed writes for replay |
| Duplicate articles across sources | URL-based deduplication before AI processing |
| AI extraction errors | Validate JSON schema, log errors, continue processing |

## Timeline Estimate

- Day 1: Set up structure, config.py, feed_parser.py
- Day 2: cache_manager.py, basic main.py workflow
- Day 3: ai_processor.py (DeepSeek integration)
- Day 4: db_writer.py (Supabase integration)
- Day 5: Testing, bug fixes, documentation
- Day 6: Deploy, schedule cron job, monitor first run

**Total: ~6 days for MVP**

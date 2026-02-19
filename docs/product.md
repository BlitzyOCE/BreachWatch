# BreachCase - Product Overview & Technical Architecture

## Product Description

**BreachCase** is an AI-powered data breach intelligence platform that automatically aggregates, analyzes, and tracks cybersecurity incidents from across the web. Unlike traditional breach databases that only catalog incidents, BreachCase treats breaches as living stories—continuously updating as new information emerges, regulatory actions are taken, and legal consequences unfold.

### Key Differentiators
- **Timeline Tracking**: Each breach has a living timeline showing discovery, disclosure, fines, lawsuits, and remediation
- **AI-Powered Intelligence**: DeepSeek API extracts structured data from unstructured news articles automatically
- **Update Detection**: AI determines if new articles are updates to existing breaches or new incidents
- **Professional Intelligence**: Designed for CISOs, security analysts, and compliance teams who need breach intelligence for risk assessment


---

## Technical Architecture Draft

### System Components

#### 1. Data Collection Layer (Python Scraper)
**Purpose**: Fetch breach news from multiple sources automatically

**Components**:
- RSS feed aggregator (SecurityWeek, BleepingComputer, KrebsOnSecurity, etc.)
- Local file cache for raw articles (JSON storage)
- Scheduled execution via cron job (daily runs)
- Error handling and retry logic
- URL-based deduplication (across RSS sources, via processed_ids.txt)
- In-run fuzzy company name deduplication (within a single run, using SequenceMatcher with 0.85 threshold)

**Tech Stack**:
- Python 3.11+
- `feedparser` for RSS parsing
- `requests` or `httpx` for HTTP requests
- `schedule` or cron for automation
- `json` for local caching


```

#### 2. AI Processing Layer (DeepSeek API)
**Purpose**: Extract structured data from unstructured articles and detect updates

**Components**:
- Article-to-structured-data extraction
- Breach deduplication (matching company name variations)
- Update detection (NEW breach vs UPDATE to existing breach)
- Severity assessment and classification
- Lessons learned generation

**Tech Stack**:
- DeepSeek AI API (deepseek-chat or deepseek-reasoner)
- Prompt engineering for consistent extraction
- JSON schema validation for outputs
- Retry logic for API failures




#### 3. Data Storage Layer (Supabase)
**Purpose**: Store structured breach data and handle updates



**Tech Stack**:
- Supabase (PostgreSQL + REST API + Realtime)
- Row Level Security (RLS) for future user features
- Automatic timestamps via triggers
- Foreign key constraints for data integrity
- JSONB for flexible metadata storage

#### 4. Frontend Layer (Next.js Website)
**Purpose**: Display breaches and provide search/filtering interface

**Pages**:
- **Homepage** (`/`): Grid of breach cards, recently updated section, search bar
- **Breach Detail Page** (`/breach/[id]`): Full breach article with all sections and timeline
- **Search Results** (`/search`): Filtered breach list with active filters shown
- **About** (`/about`): Platform information and sources
- **(Future) Dashboard** (`/dashboard`): Analytics and trends
- **(Future) User Profile** (`/profile`): Watchlists and saved breaches

**Key Components**:
- `BreachCard` - Compact card view for lists (shows company, date, severity, brief summary)
- `BreachTimeline` - Vertical timeline visualization with icons for event types
- `FilterBar` - Tag-based filtering with chips/pills
- `SearchBar` - Text search with autocomplete
- `TagBadge` - Clickable colored badges for tags
- `SeverityBadge` - Color-coded severity indicator
- `BreachDetail` - Full breach article layout
- `RelatedBreaches` - Horizontal scrolling list of similar breaches

**Tech Stack**:
- Next.js 14+ (App Router)
- React 18+
- TypeScript (for type safety)
- Tailwind CSS for styling
- shadcn/ui for component library
- Supabase JS client for data fetching
- Server-side rendering (SSR) for SEO
- Static generation for performance where applicable
- Framer Motion for animations (optional)




## Data Flow

### End-to-End Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      RSS Feed Sources                        │
│  SecurityWeek, BleepingComputer, KrebsOnSecurity, etc.      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Scraper fetches daily (cron job)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python Scraper                            │
│  1. Fetch RSS feeds                                          │
│  2. Parse articles                                           │
│  3. Cache locally (JSON)                                     │
│  4. Check for duplicates                                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Send article text
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    DeepSeek AI (AI)                          │
│  1. Extract structured data                                  │
│  2. Detect if NEW breach or UPDATE                           │
│  3. Match to existing breaches                               │
│  4. Generate summary & lessons learned                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Structured JSON output
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Supabase Database                         │
│  1. Store new breaches in `breaches` table                   │
│  2. Store updates in `breach_updates` table                  │
│  3. Create tags in `breach_tags` table                       │
│  4. Record sources in `sources` table                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ REST API / Supabase Client
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Website                           │
│  1. Server-side fetch from Supabase                          │
│  2. Render breach cards and detail pages                     │
│  3. Handle search and filtering                              │
│  4. Display timelines and related breaches                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ HTTP/HTTPS
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      End Users                               │
│  CISOs, Security Analysts, Compliance Teams, Journalists    │
└─────────────────────────────────────────────────────────────┘
```

### Daily Scraper Example Workflow

1. **Initialization**
   - Load environment variables (API keys)
   - Connect to Supabase
   - Initialize DeepSeek API client

2. **RSS Fetching**
   - Fetch all configured RSS feeds in parallel
   - Parse XML to extract article URLs, titles, publish dates
   - Filter: only articles from last 48 hours
   - Total: ~20-50 articles/day

3. **Deduplication Check**
   - Load `processed_ids.txt` (articles already processed)
   - Compare article URLs against processed list
   - Skip already-processed articles
   - Remaining: ~10-30 new articles/day

4. **Article Fetching**
   - For each new article, fetch full HTML
   - Extract main text content (remove ads, navigation, etc.)
   - Save raw article to cache: `cache/raw_2024-02-02.json`

5. **AI Processing**
   - For each cached article:
     - Send to DeepSeek API with extraction prompt
     - Receive structured JSON response
     - Validate JSON schema
     - If extraction fails, log error and skip

6. **Update Detection**
   - Fetch list of existing breaches from Supabase (loaded once at run start; includes `records_affected` and `attack_vector` for structured comparison)
   - For each extracted breach:
     - First: fast Python-side fuzzy match on company name against breaches written earlier in this run (SequenceMatcher >= 0.85). If matched, force as update without an AI call.
     - Otherwise: send to DeepSeek API with three-way update detection prompt
     - DeepSeek classifies as one of: `NEW_BREACH`, `GENUINE_UPDATE`, or `DUPLICATE_SOURCE`

7. **Database Writing**
   - **If NEW_BREACH:**
     - Insert into `breaches` table
     - Insert tags into `breach_tags` table
     - Insert source into `sources` table
   - **If GENUINE_UPDATE** (confidence >= 0.7, adds new facts):
     - Insert into `breach_updates` table
     - Update `breaches.updated_at` timestamp
     - Insert source into `sources` table
   - **If DUPLICATE_SOURCE** (same facts, different outlet):
     - Mark URL as processed, log, skip DB write entirely

8. **Cleanup**
   - Append processed article IDs to `processed_ids.txt`
   - Log summary: X new breaches, Y updates, Z errors
   - Send notification (optional: email/Slack)

**Total Runtime: 5-10 minutes/day**

---

## Deployment Architecture

### Infrastructure Overview

```
┌──────────────────────────────────────────────────────────────┐
│                         GitHub Repository                     │
│                    github.com/user/breachcase               │
└────────────┬────────────────────────────┬────────────────────┘
             │                            │
             │ Push to main               │ Push to main
             ▼                            ▼
┌─────────────────────────┐   ┌──────────────────────────────┐
│   Vercel (Frontend)     │   │  Render/Railway (Scraper)    │
│   - Auto-deploy         │   │  - Manual/auto-deploy        │
│   - Edge functions      │   │  - Cron job (daily 8am UTC)  │
│   - CDN distribution    │   │  - Environment variables     │
│   - Custom domain       │   │  - Logging enabled           │
└────────────┬────────────┘   └──────────────┬───────────────┘
             │                                │
             │ Reads data                     │ Writes data
             ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    Supabase (Database)                       │
│  - PostgreSQL database                                       │
│  - REST API (auto-generated)                                 │
│  - Realtime subscriptions                                    │
│  - Connection pooling                                        │
└─────────────────────────────────────────────────────────────┘
             │
             │ AI processing
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    DeepSeek AI API                           │
│  - deepseek-chat or deepseek-reasoner model                  │
│  - Pay-per-use pricing                                       │
└─────────────────────────────────────────────────────────────┘
```



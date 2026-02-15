# Data Quality & Coverage Improvement Plan

## Current State Assessment

BreachWatch currently relies on **8 RSS feeds** (BleepingComputer, The Hacker News, DataBreachToday, Krebs on Security, HelpNet Security, NCSC UK, Check Point Research, Have I Been Pwned). Articles are fetched every 48 hours, classified by AI, and extracted into structured breach records.

### What works well
- Three-stage AI pipeline (classify -> extract -> dedup) is solid and cost-efficient
- DeepSeek extraction produces good structured data from unstructured articles
- In-run fuzzy dedup + AI-based update detection prevents most duplicates
- Cost is near-zero (~$1/month in LLM calls)

### Coverage gaps
| Gap | Impact |
|-----|--------|
| **No historical data** | Zero breaches before the scraper started running |
| **English-only, news-only** | Misses regulatory filings, SEC disclosures, court records, press releases |
| **No ransomware leak site monitoring** | Ransomware victims appear on leak sites days before news coverage |
| **No government database ingestion** | HHS alone has 6,000+ healthcare breaches since 2009 |
| **No structured data sources** | Relying entirely on AI extraction from prose when structured datasets exist |
| **RSS-only discovery** | If a breach isn't covered by one of 8 outlets, it doesn't exist in our system |

**Estimated current coverage: ~30-40% of publicly reported breaches (new only, no historical).**

---

## Goal

Cover **~90%+ of all publicly reported breaches from the past 10 years**, and maintain **near-real-time coverage** of new breaches going forward.

---

## Available Data Sources (Ranked by Value)

### Tier 1: Free, Structured, High-Value (Implement First)

#### 1. HHS OCR Breach Portal ("Wall of Shame")
- **URL:** https://ocrportal.hhs.gov/ocr/breach/breach_report.jsf
- **What:** All HIPAA breaches affecting 500+ individuals since 2009. ~6,000+ records.
- **Format:** Direct CSV download from the portal page. Fields: entity name, state, entity type, individuals affected, submission date, breach type, location of breached info, business associate involvement.
- **Integration:** Download CSV daily/weekly, diff against last snapshot, insert new rows. No API key needed. Map CSV fields to your `breaches` schema — most fields map directly. Use LLM only for generating the `summary` and `lessons_learned` fields.
- **Cost:** Free.
- **Coverage impact:** Adds the entire U.S. healthcare breach history (the single largest breach category). Massive historical backfill.

#### 2. RansomLook API
- **URL:** https://www.ransomlook.io/ | API docs: https://www.ransomlook.io/doc/
- **What:** Real-time monitoring of ransomware group leak sites. Tracks victim posts from all major groups (LockBit, ALPHV/BlackCat, Cl0p, Play, etc.). Many victims appear here days before news coverage.
- **Format:** Free public REST API, no auth required. CC BY 4.0 license.
  - `GET /api/recent` — recent victim posts across all groups
  - `GET /api/groups` — all tracked groups
  - `GET /api/posts/{group}` — posts for a specific group
- **Integration:** Poll `/api/recent` every few hours. Each entry includes victim name, sector, country, date, and responsible group. Map `group` to `threat_actor`, set `attack_vector = 'ransomware'`. Use LLM to generate summary from the post content.
- **Cost:** Free.
- **Coverage impact:** Catches ransomware breaches before they hit the news cycle. Ransomware accounts for ~25-30% of all breaches.

#### 3. SEC EDGAR — 8-K Cybersecurity Filings
- **URL:** https://efts.sec.gov/LATEST/search-index
- **What:** Since December 2023, public companies must file an 8-K (Item 1.05) within 4 business days of determining a cybersecurity incident is "material." ~55 filings in the first year of the rule.
- **Format:** Free REST API, no auth needed. Returns JSON with filing metadata and links to full filing text (HTML).
  - Search: `https://efts.sec.gov/LATEST/search-index?q=%22Item+1.05%22+%22cybersecurity%22&forms=8-K&dateRange=custom&startdt=2023-12-18`
  - Filing text: `https://www.sec.gov/Archives/edgar/data/{CIK}/{accession}.htm`
- **Integration:** Poll daily for new 8-K filings matching cybersecurity keywords. Fetch filing HTML, send to LLM for structured extraction. These filings contain high-quality first-party data (the company itself is disclosing).
- **Cost:** Free.
- **Coverage impact:** Catches all material breaches at U.S. public companies — often the largest and most impactful incidents. First-party data is more reliable than news reporting.

#### 4. Washington State AG Breach Notifications
- **URL:** https://data.wa.gov/Consumer-Protection/Data-Breach-Notifications-Affecting-Washington-Res/sb4j-ca4h
- **What:** All breach notifications submitted to Washington state since July 2015. The richest state-level structured dataset.
- **Format:** Socrata API — returns JSON, CSV, or XML. No API key required.
  - `https://data.wa.gov/resource/sb4j-ca4h.json`
- **Integration:** Poll the Socrata API weekly. Filter by date for new entries. Fields include organization name, date of breach, individuals affected, data types, notification date.
- **Cost:** Free.
- **Coverage impact:** Catches breaches affecting Washington residents that may not make national news. Many small/mid-size company breaches are only visible through state AG filings.

#### 5. HIBP Breach Catalog
- **URL:** https://haveibeenpwned.com/api/v3/breaches
- **What:** Metadata for every breach dataset indexed by Have I Been Pwned. Includes company, breach date, data types exposed, description, number of accounts.
- **Format:** Free JSON endpoint, no auth needed for the breach list. Returns array of all breaches.
- **Integration:** Poll daily. Compare against your database. Each new entry = a verified breach where credential data is circulating. Note: you already have HIBP as an RSS source, but the API gives structured metadata that the RSS feed doesn't.
- **Cost:** Free.
- **Coverage impact:** Adds breaches where data is confirmed circulating — a different signal than news coverage.

#### 6. Ransomware.live
- **URL:** https://www.ransomware.live/ | GitHub: https://github.com/JMousqueton/ransomware.live
- **What:** Complementary to RansomLook. Scrapes ransomware leak sites. Monitors slightly different sets of groups.
- **Format:** Open-source, public API documented on GitHub. Free.
- **Integration:** Use alongside RansomLook. Deduplicate across both sources by victim name + date.
- **Cost:** Free.

#### 7. CISA Known Exploited Vulnerabilities (KEV)
- **URL:** https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
- **What:** 1,484+ CVEs confirmed exploited in the wild. Not a breach database, but enrichment data.
- **Format:** JSON feed, free, no auth. Updated daily. Also mirrored at https://github.com/cisagov/kev-data.
- **Integration:** Cross-reference CVEs from your `cve_references` field against KEV. Add a flag like "known exploited vulnerability" to breach records. Useful for severity assessment.
- **Cost:** Free.

---

### Tier 2: Low Cost, Requires Some Scraping (~$70-100/month)

#### 8. Expanded RSS Feeds (20-30 sources)
Add these feeds to your existing RSS infrastructure:

| Feed | URL | Why |
|------|-----|-----|
| DataBreaches.net | https://databreaches.net/feed/ | Most comprehensive single-site breach aggregator. Catches breaches before mainstream media. |
| The Record (Recorded Future) | https://therecord.media/feed | High quality breach/ransomware coverage |
| Dark Web Informer | https://darkwebinformer.com/ (RSS available) | Aggregates dark web threat actor posts on clearnet |
| SC Magazine | https://www.scmagazine.com/feed | Broad security news with breach coverage |
| Globe Newswire (security) | https://www.globenewswire.com/RssFeed/subjectcode/25-Cybersecurity/feedTitle/GlobeNewswire | Company press releases about breaches |
| BusinessWire (cyber) | https://www.businesswire.com/portal/site/home/news/ (filterable RSS) | Company press releases |
| Infosecurity Magazine | https://www.infosecurity-magazine.com/rss/news/ | European breach coverage |
| CyberScoop | https://cyberscoop.com/feed/ | Policy-oriented, good for government breaches |
| TechCrunch Security | https://techcrunch.com/category/security/feed/ | Breaks major tech company breaches |

- **Cost:** Free (same infrastructure).
- **Coverage impact:** Expanding from 8 to 25+ feeds should roughly double the number of breaches caught via RSS.

#### 9. California AG Breach List
- **URL:** https://oag.ca.gov/privacy/databreach/list
- **What:** Breach notifications sent to 500+ California residents. California is the largest state, so this captures many breaches.
- **Format:** HTML paginated list of links to individual PDF sample notices. No API.
- **Integration:** Scrape the HTML index page for new entries. Download PDFs. Extract text with PyMuPDF/pdfminer. Send text to LLM for structured extraction.
- **Tool:** Firecrawl ($69.99/month Developer plan) handles JS rendering and returns clean markdown. Or use `requests` + `BeautifulSoup` if the pages are simple HTML.
- **Cost:** ~$0-70/month depending on approach.

#### 10. VCDB Historical Import (One-Time)
- **URL:** https://github.com/vz-risk/VCDB
- **What:** 8,000+ publicly reported security incidents coded in the VERIS framework (used by Verizon DBIR). Individual JSON files per incident with source URLs. Data goes back 10+ years.
- **Format:** GitHub repository of JSON files. Free. `git clone` and process.
- **Integration:** One-time bulk import. Each VERIS JSON file needs mapping to your schema (company, attack vector, records affected, etc.). The VERIS schema is different from yours — write a mapper. Use LLM to generate summaries from the VERIS description + source URLs.
- **Cost:** Free (one-time engineering effort).
- **Coverage impact:** This is likely the fastest path to your "10 years of history" goal. 8,000+ incidents immediately.

#### 11. Privacy Rights Clearinghouse — Data Breach Chronology
- **URL:** https://privacyrights.org/data-breaches
- **What:** 8,019 breach filings aggregated from state AGs and federal agencies, representing 4,080 unique breach events since 2005. 375M+ individuals affected.
- **Format:** Web search is free. Full download (SQLite/CSV/Excel) available at https://store.databreachchronology.org — pricing not public, contact required. Complimentary access for nonprofits/researchers.
- **Integration:** If you can get the dataset, it's a cleaned, deduplicated version of the same state AG + HHS data. Direct import into your schema.
- **Cost:** Likely $100-500/year for a small project. Free for qualifying researchers.
- **Coverage impact:** Overlaps heavily with HHS + state AG data, but pre-cleaned and deduplicated. Most valuable as a cross-reference to validate your own coverage.

---

### Tier 3: Moderate Cost, AI Agents (~$200-400/month)

#### 12. AI Agent-Based State AG Scraping
- **Problem:** ~15 U.S. states publish breach notification lists, but only Washington has a clean API. The rest are HTML tables, PDF archives, or JavaScript-rendered pages.
- **Approach:** Use an AI agent framework to autonomously navigate and extract from each state AG portal.
- **Tool options:**

| Tool | What It Does | Cost |
|------|-------------|------|
| **browser-use** (open source) | Python library that gives an LLM control of a Playwright browser. The LLM sees page elements, decides what to click/type, iterates until done. | Free (library). LLM costs only. ~$0.01-0.03/run with GPT-4o mini, ~$0.15-0.50/run with Claude Sonnet. |
| **Firecrawl** | Managed scraping service. Converts any URL to clean markdown or structured JSON. Handles JS rendering and anti-bot. `/extract` endpoint does LLM extraction in one call. | $69.99/month (250K credits). 1 credit = 1 page. JS rendering = 5 credits. |
| **Apify** | Cloud scraping platform with 5,000+ pre-built "Actors" for specific sites. Actors run on their infrastructure. | $39-49/month (Starter). Some actors have additional rental fees. |
| **Serper.dev** | Google Search API. Use for gap-filling: search for "{company name} data breach" to find coverage your RSS feeds missed. | 2,500 free searches/month. ~$0.30-1.00 per 1,000 additional searches. |

- **Recommended approach:** Use `browser-use` + GPT-4o mini for the state AG pages (cheapest per-run cost). Run weekly, not daily — these pages update slowly. Use Serper.dev for gap-filling searches.
- **Cost:** ~$5-15/month for browser-use LLM calls + $0-5/month for Serper.dev = ~$10-20/month for the agent layer itself. Add Firecrawl at $70/month if you want a more reliable, managed solution.
- **Coverage impact:** Adds breach disclosures from 10-15 state AGs that currently aren't captured at all.

#### 13. CourtListener / RECAP — Class Action Breach Details
- **URL:** https://www.courtlistener.com/ (Free Law Project)
- **What:** Full-text searchable federal court opinion database. Many data breach class action filings contain detailed breach timelines, affected record counts, and technical details not available elsewhere.
- **Format:** REST API, free. Search for "data breach" class action filings.
- **Integration:** Weekly search for new breach-related filings. Extract breach details from filing text using LLM.
- **Cost:** Free (CourtListener API). PACER itself charges $0.10/page but RECAP mirrors documents for free once anyone has purchased them.
- **Coverage impact:** Adds legal context (class actions, settlements, fines) as timeline updates to existing breaches. Also catches some breaches first disclosed in court filings.

---

### Tier 4: Higher Cost, Near-Complete Coverage (~$500-1,000/month)

#### 14. Dark Web Intelligence Feeds
- **What:** Commercial services that monitor dark web marketplaces, paste sites, and forums for breach data being sold or leaked.
- **Options:** Breachsense, SpyCloud, Flare, Recorded Future. These are enterprise products.
- **Cost:** $200-500+/month for the cheapest tiers. Many require annual contracts.
- **Coverage impact:** Catches breaches that are never publicly disclosed — data appears on dark web before (or instead of) news coverage. This is the gap between "publicly reported" and "actually happened."
- **Assessment:** Expensive but the only way to get near-100%. Consider this only after Tiers 1-3 are implemented and you want to push past 90%.

#### 15. International Coverage (Non-English Sources)
- **What:** Breach reporting in German, French, Japanese, Korean, Portuguese, etc. EU DPA enforcement decisions (27 separate authorities).
- **Approach:** Monitor DPA press release pages (scrape), use translation API (DeepL/Google Translate) before LLM extraction.
- **Cost:** ~$20-50/month for translation API + scraping infrastructure.
- **Coverage impact:** Adds 5-10% of global breaches currently invisible to English-only monitoring.

---

## Implementation Roadmap

### Phase 1: Free Structured Sources (Week 1-2)
**Goal:** Add all Tier 1 free sources. No new infrastructure needed — just new Python modules.

| Task | Source | Effort | Coverage Gain |
|------|--------|--------|---------------|
| HHS OCR CSV importer | CSV download + diff | 1-2 days | +15% (healthcare history) |
| RansomLook API poller | REST API | 0.5 days | +5% (ransomware early warning) |
| SEC EDGAR 8-K monitor | REST API | 1 day | +3% (public company disclosures) |
| WA State AG Socrata poller | REST API | 0.5 days | +2% (state-level) |
| HIBP catalog poller | REST API | 0.5 days | +2% (verified circulating data) |
| Ransomware.live poller | REST API | 0.5 days | +1% (redundancy) |
| CISA KEV enrichment | JSON feed | 0.5 days | Enrichment only |

**Architecture:** Each source becomes a new Python module in `scraper/sources/` with a common interface:
```
fetch_new_entries() -> list[dict]  # Returns entries in a normalized format
```
The existing `ai_processor.py` handles summary generation. The existing `db_writer.py` handles database writes. `main.py` orchestrates all sources in sequence.

**Monthly cost:** ~$0 additional.
**Estimated coverage after Phase 1:** ~55-65%

---

### Phase 2: Historical Backfill (Week 3-4)
**Goal:** Import 10 years of historical breach data.

| Task | Source | Effort | Coverage Gain |
|------|--------|--------|---------------|
| VCDB import script | 8,000+ JSON files from GitHub | 2-3 days | +20% historical |
| HHS historical load | Full CSV (2009-present) | 1 day (included in Phase 1 importer) | Included above |
| Privacy Rights Clearinghouse | License + import (if obtainable) | 1-2 days | +5% historical (deduplicated) |

**Architecture:** One-time import scripts in `scraper/importers/`. Each script maps the source schema to your `breaches` schema, handles deduplication against existing records, and generates LLM summaries where needed.

**Key challenge:** Deduplication across sources. The same breach (e.g., "Equifax 2017") will appear in HHS, VCDB, PRC, news articles, and state AG filings. Your existing fuzzy match + AI dedup pipeline handles this, but the sheer volume (potentially 10,000+ records to deduplicate) means you should:
1. Import in order of data quality (VCDB first, then HHS, then PRC)
2. Use batch processing with the LLM for dedup (cheaper via DeepSeek batch)
3. Run `audit.py` after each import to check for duplicates

**Monthly cost:** ~$5-10 in LLM calls for summary generation (one-time).
**Estimated coverage after Phase 2:** ~70-80% (including historical)

---

### Phase 3: Expanded RSS + Light Scraping (Week 5-6)
**Goal:** Double RSS coverage and add California AG scraping.

| Task | Effort | Coverage Gain |
|------|--------|---------------|
| Add 15-20 new RSS feeds | 1 day | +5-8% |
| California AG HTML + PDF scraper | 2-3 days | +3% |
| Massachusetts AG PDF scraper | 1-2 days | +1% |

**Architecture:** RSS feeds just need new entries in `config.py`. PDF scraping needs a new module using PyMuPDF for text extraction + LLM for structured extraction.

**Monthly cost:** ~$0-70/month (Firecrawl optional).
**Estimated coverage after Phase 3:** ~80-88%

---

### Phase 4: AI Agents for Gap-Filling (Week 7-10)
**Goal:** Use AI agents to cover sources that don't have APIs or simple scraping paths.

| Task | Tool | Effort | Coverage Gain |
|------|------|--------|---------------|
| State AG portal agents (10+ states) | browser-use + GPT-4o mini | 3-5 days | +3% |
| Company press release monitoring | Serper.dev + LLM | 2 days | +2% |
| CourtListener class action monitoring | REST API | 1-2 days | +1% (enrichment) |
| EU DPA enforcement monitoring | browser-use or Firecrawl | 3-5 days | +2% |

**Architecture decision — AI agents:**

The term "AI agent" here means an LLM that is given a tool (a web browser or search API) and autonomously decides how to use it to accomplish a goal. For BreachWatch, the agents don't need to be sophisticated — they perform the same task repeatedly on a schedule:

```
Agent task: "Go to [state AG URL], find all breach notifications
submitted in the last 7 days, extract: company name, date,
individuals affected, breach type. Return as JSON array."
```

**browser-use** is the recommended framework because:
- Open source (no platform lock-in)
- Works with any LLM (use GPT-4o mini for cost, switch to DeepSeek when they add vision)
- Handles JavaScript-rendered pages automatically
- Each run is stateless — no browser sessions to manage
- Cost per run is ~$0.01-0.03 with GPT-4o mini

**When NOT to use an AI agent:**
- If the source has a structured API (use direct API calls instead)
- If the source is simple HTML (use `requests` + `BeautifulSoup` instead)
- If the source is an RSS feed (use `feedparser` instead)

AI agents are specifically for sources that require interactive browser navigation — clicking through paginated results, handling dropdowns, navigating JavaScript-rendered content — where traditional scraping would be brittle and maintenance-heavy.

**Monthly cost:** ~$10-50/month (LLM calls + optional Serper.dev).
**Estimated coverage after Phase 4:** ~88-93%

---

### Phase 5: Premium Sources (Future)
**Goal:** Push past 90% for commercial-grade coverage.

| Task | Cost | Coverage Gain |
|------|------|---------------|
| Dark web intelligence feed | $200-500/month | +3-5% |
| Non-English source monitoring + translation | $20-50/month | +2-3% |
| PACER/RECAP court filing monitoring | $20-50/month | +1% (enrichment) |

**Monthly cost:** $240-600/month.
**Estimated coverage after Phase 5:** ~93-97%

---

## Cost Summary by Phase

| Phase | Monthly Cost | Cumulative Coverage | One-Time Effort |
|-------|-------------|-------------------|-----------------|
| Current (RSS only) | ~$1 | ~30-40% | — |
| Phase 1: Free APIs | ~$1 | ~55-65% | 5-6 days |
| Phase 2: Historical backfill | ~$1 (+$5-10 one-time) | ~70-80% | 4-6 days |
| Phase 3: Expanded RSS + scraping | ~$1-70 | ~80-88% | 5-7 days |
| Phase 4: AI agents | ~$15-120 | ~88-93% | 10-15 days |
| Phase 5: Premium sources | ~$255-720 | ~93-97% | 5-10 days |

**The sweet spot for a solo developer is Phase 1-3:** ~80-88% coverage for ~$1-70/month and 2-3 weeks of development. Phase 4 adds meaningful coverage but requires ongoing maintenance of agent scripts. Phase 5 is only justified if this becomes a commercial product.

---

## Architecture Changes Needed

### New directory structure
```
scraper/
├── sources/              # NEW: one module per data source type
│   ├── __init__.py
│   ├── rss.py           # Refactored from feed_parser.py
│   ├── hhs_ocr.py       # HHS breach portal CSV
│   ├── ransomlook.py    # RansomLook API
│   ├── sec_edgar.py     # SEC 8-K filings
│   ├── wa_state_ag.py   # Washington state Socrata API
│   ├── hibp_catalog.py  # HIBP breach list API
│   ├── ransomware_live.py
│   └── ca_state_ag.py   # California AG scraper
├── importers/            # NEW: one-time historical import scripts
│   ├── __init__.py
│   ├── vcdb_import.py   # VCDB GitHub JSON import
│   └── prc_import.py    # Privacy Rights Clearinghouse import
├── agents/               # NEW: AI agent tasks (Phase 4)
│   ├── __init__.py
│   ├── state_ag_agent.py
│   └── press_release_agent.py
├── main.py              # Updated to orchestrate all sources
├── ai_processor.py      # Mostly unchanged
├── db_writer.py         # Add batch write methods
├── cache_manager.py     # Extend for new source types
├── config.py            # Add new source configs
└── audit.py             # Add cross-source coverage metrics
```

### Database changes
- Add a `source_type` column to `sources` table to track where each breach originated (rss, hhs_ocr, ransomlook, sec_edgar, state_ag, vcdb, hibp, court_filing, etc.)
- This enables coverage analytics: "what percentage of our breaches come from each source?"

### Deduplication at scale
The current dedup approach (fuzzy match + AI) works for ~50 articles/run. With 10,000+ historical records being imported, you'll need:
1. A faster first-pass dedup: exact match on company name (normalized: lowercase, strip "Inc.", "LLC", "Corp.", etc.)
2. Fuzzy match only on the subset that passes exact match filtering
3. AI dedup only when fuzzy match is ambiguous (0.7-0.9 similarity range)

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Source websites change their structure | AI agents (browser-use) are more resilient than traditional scrapers because they adapt to layout changes. For critical sources, add monitoring alerts when extraction fails. |
| Deduplication errors at scale | Run `audit.py --duplicates` after each major import. Build a manual review queue for ambiguous matches (0.7-0.85 similarity). |
| LLM extraction quality degrades | Maintain test fixtures — a set of known articles with expected extraction output. Run as regression tests after prompt changes. |
| Rate limiting / IP blocking | For government sites: respect robots.txt, add delays between requests, use a single scheduled run per day. For news sites: RSS is inherently rate-limit-friendly. |
| Cost creep from AI agents | Set hard monthly budget caps. Use GPT-4o mini (not Sonnet/Opus) for agent tasks. Batch API where possible (50% discount). Monitor token usage. |
| Data quality varies across sources | Add a `data_quality_score` or `source_reliability` metric. HHS/SEC filings = high confidence. Ransomware leak posts = lower confidence. Weight accordingly in the UI. |

---

## Recommended Starting Point

If you want to maximize impact with minimum effort, do these three things first:

1. **Add RansomLook API polling** (0.5 days, free) — immediately starts catching ransomware breaches before news coverage
2. **Add HHS OCR CSV import** (1-2 days, free) — adds 6,000+ historical healthcare breaches overnight
3. **Add SEC EDGAR 8-K monitoring** (1 day, free) — catches all material public company breaches from the most authoritative source possible

These three sources alone would roughly double your coverage at zero additional cost.

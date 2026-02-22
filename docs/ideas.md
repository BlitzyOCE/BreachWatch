# Data Breach Aggregation Website - Feature Ideas

## Core Features (MVP)

### Data Collection & Processing
- [x] Python scraper fetches breach news from RSS feeds (BleepingComputer, The Hacker News, KrebsOnSecurity, etc.)
- [x] Local file cache stores raw articles before AI processing
- [x] DeepSeek API extracts structured data from articles
- [x] AI determines if article is NEW breach, UPDATE, or DUPLICATE SOURCE
- [x] Store all data in Supabase (PostgreSQL)

### Data Structure & Schema ✅ COMPLETED
- [x] Breaches table: company, industry, country, continent, breach method, attack vector, CVE references, MITRE ATT&CK techniques, severity score, initial discovery date, records affected, status
- [x] Breach updates table: linked to parent breach, update type, date, description, source URL, confidence score, AI reasoning
- [x] Tags system: continent, country, industry, attack vector, threat actor, CVE, MITRE
- [x] Sources table: article URLs, titles, published dates
- [x] Company aliases table: for deduplication (Qantas = Qantas Airways)
- [x] Breach views table: for analytics and recommendations
- [x] Full-text search support with auto-updating search vector
- [x] Utility views: breach_summary, tag_counts
- [x] Utility functions: search_breaches(), get_related_breaches(), find_company_by_alias()

### Frontend Display
- [x] Next.js website displays breaches as cards on homepage
- [x] Each card shows a title that helps the viewer identify the breach
- [x] Filter by tags (continent, country, industry, attack vector, threat actor)
- [x] Search by keyword functionality (help user find a breach in their mind)
- [ ] "Recently Updated Breaches" section on homepage

## Breach Detail Pages (called an "Article")

### Article Structure
By clicking on the card, it shows a breach detail page contains the following sections:
- [x] **AI High-level Summary**: 2-3 sentence executive overview at top
- [x] **Tags**: Country, industry, severity, attack vector, CVE, MITRE ATT&CK techniques (clickable filters)
- [x] **Key Facts**: Company name, industry, discovery date, disclosure date, records affected, current status
- [x] **Attack Method**: Technical explanation of how breach occurred
- [x] **Data Compromised**: Types and volume of exposed data
- [x] **Incident Timeline**: Vertical timeline showing key events (discovery, disclosure, milestones)
- [ ] **Impact Analysis**: Financial losses, operational disruption, reputational damage
- [ ] **Regulatory & Legal**: Fines, investigations, lawsuits, compliance violations
- [x] **Lessons Learned**: What security controls failed, preventive recommendations
- [x] **Update History**: Chronological list of all updates to this breach (separate dedicated section)
- [x] **Related Breaches**: 3 similar incidents matched by tags
- [x] **Sources**: Links to original articles and reports

### Timeline Features
- [x] Vertical timeline visualization on breach detail page
- [x] Update types displayed with icons: initial discovery, new information, class action, regulatory fine, remediation, resolution
- [x] Each timeline entry shows date, type, and description
- [ ] Color-coded by update type (e.g., red for fines, blue for new info, green for resolution)

## Intelligence & Matching

### AI Processing
- [x] Breach deduplication: AI matches variations (Qantas Airways = Qantas = QAN)
- [ ] Detect severity changes (track if impact increases from 1M to 5M records)
- [x] Handle false positives and duplicate updates across sources
- [ ] Review queue for manually approving AI's breach matching and update classifications

### Classification & Attribution
- [x] Attack vector taxonomy: phishing, ransomware, API exploit, insider threat, supply chain, misconfiguration
- [x] Threat actor attribution and tracking
- [x] CVE/vulnerability cross-reference
- [x] MITRE ATT&CK technique mapping
- [x] Severity scoring system (based on records affected, data sensitivity, industry impact)

## User Personalization
- [ ] User accounts and authentication
- [ ] User profiles with preferences
- [ ] Watchlists: track specific countries, industries, companies, or threat actors
- [ ] Save individual breaches and receive notifications on updates
- [ ] Comment system on breach articles (moderated)
- [ ] Customized email alerts based on watchlist criteria
- [ ] Browse history and personalized breach recommendations

## Analytics & Trends (Future)
- [ ] Breach statistics dashboard: charts by industry, country, attack vector, year
- [ ] Trend analysis: breach frequency over time, emerging attack patterns
- [ ] Heat map visualization by geography
- [ ] Most exploited vulnerabilities report
- [ ] Quarterly threat intelligence reports (AI-generated)

## Export & Integration (Future)
- [ ] Export individual breach reports to PDF
- [ ] Export filtered breach lists to CSV/JSON
- [ ] Public RSS feed of new breaches
- [ ] REST API for external access (authentication required)
- [ ] Webhook notifications for real-time alerts

## UI/UX Enhancements (Future)
- [x] Dark mode toggle
- [ ] Advanced filtering with boolean operators (AND/OR/NOT)
- [ ] Side-by-side breach comparison view
- [ ] Breach case studies (long-form deep dives)
- [ ] Interactive infographics for major breaches
- [ ] Keyboard shortcuts for power users
- [x] Mobile-responsive design

## Technical Infrastructure
- [ ] Daily cron job for scraper execution
- [x] Robust error handling for DeepSeek API failures (retry with backoff)
- [ ] Rate limiting for API calls (both DeepSeek and Supabase)
- [x] Logging and monitoring for scraper health (daily log files + error logs)
- [ ] Database backup strategy
- [ ] Frontend deployment to Vercel
- [ ] Scraper deployment to Render/Railway/VPS
- [x] Environment variables management (.env files)
- [x] Git version control with regular commits
- [ ] Supabase connection pooling and optimization
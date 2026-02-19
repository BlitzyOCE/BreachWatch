"""
Configuration settings for BreachCase scraper.

Contains RSS feed sources, API settings, file paths, and AI prompts.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
CACHE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# RSS Feed Sources (8 sources)
RSS_SOURCES = {
    'bleepingcomputer': {
        'name': 'BleepingComputer',
        'url': 'https://www.bleepingcomputer.com/feed/',
        'language': 'en'
    },
    'thehackernews': {
        'name': 'The Hacker News',
        'url': 'https://thehackernews.com/feeds/posts/default',
        'language': 'en'
    },
    'databreachtoday': {
        'name': 'DataBreachToday',
        'url': 'https://www.databreachtoday.co.uk/rss-feeds',
        'language': 'en'
    },
    'krebsonsecurity': {
        'name': 'Krebs on Security',
        'url': 'https://krebsonsecurity.com/feed/',
        'language': 'en'
    },
    'helpnetsecurity': {
        'name': 'HelpNet Security',
        'url': 'https://www.helpnetsecurity.com/feed',
        'language': 'en'
    },
    'ncsc_uk': {
        'name': 'NCSC UK',
        'url': 'https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml',
        'language': 'en'
    },
    'checkpoint': {
        'name': 'Check Point Research',
        'url': 'https://research.checkpoint.com/feed',
        'language': 'en'
    },
    'haveibeenpwned': {
        'name': 'Have I Been Pwned',
        'url': 'https://feeds.feedburner.com/HaveIBeenPwnedLatestBreaches',
        'language': 'en'
    }
}

# DeepSeek API Configuration
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
DEEPSEEK_TIMEOUT = int(os.getenv('DEEPSEEK_TIMEOUT', '60'))  # seconds
DEEPSEEK_MAX_TOKENS = int(os.getenv('DEEPSEEK_MAX_TOKENS', '8192'))

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Scraper Settings
ARTICLE_LOOKBACK_HOURS = int(os.getenv('ARTICLE_LOOKBACK_HOURS', '48'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))  # seconds
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))  # seconds
MAX_FEED_WORKERS = int(os.getenv('MAX_FEED_WORKERS', '10'))  # parallel RSS fetch threads
MAX_EXISTING_BREACHES_FETCH = int(os.getenv('MAX_EXISTING_BREACHES_FETCH', '100'))  # DB fetch cap
MAX_EXISTING_BREACHES_CONTEXT = int(os.getenv('MAX_EXISTING_BREACHES_CONTEXT', '50'))  # AI prompt context cap
FUZZY_MATCH_THRESHOLD = float(os.getenv('FUZZY_MATCH_THRESHOLD', '0.85'))  # in-run company name similarity

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# File Paths
PROCESSED_IDS_FILE = CACHE_DIR / "processed_ids.txt"

# AI Classification Prompt (Stage 1: Quick filter)
CLASSIFICATION_PROMPT = """You are a cybersecurity analyst determining if an article is about a DATA BREACH incident.

Article Title: {title}
Article Summary: {summary}

A DATA BREACH is an incident where:
- Unauthorized access to sensitive data occurred
- Data was stolen, leaked, exposed, or compromised
- A specific organization/company was victimized
- Personal information, credentials, or confidential data was affected

NOT a data breach:
- Vulnerability disclosures (CVEs without confirmed exploitation)
- Security tool/product announcements
- Threat intelligence reports without specific victim
- Malware analysis without confirmed data theft
- Security best practices or advice articles
- Policy/compliance updates
- Ransomware attacks WITHOUT data exfiltration mentioned

Return JSON:
{{
  "is_breach": true or false,
  "confidence": 0.0 to 1.0 (confidence in your classification),
  "reasoning": "Brief 1-sentence explanation of your decision"
}}

Be strict: Only classify as breach if there's clear evidence of data compromise.
"""

# AI Extraction Prompt (Stage 2: Detailed extraction)
EXTRACTION_PROMPT = """You are a cybersecurity analyst extracting structured breach data from news articles.

Article Title: {title}
Article URL: {url}
Article Summary: {summary}
Today's Date: {today}

Extract the following information in JSON format:

{{
  "company": "Name of the breached or affected organization. Infer from context if not explicitly stated (e.g., 'Microsoft' for a Microsoft Outlook add-in attack, 'US Government' for a campaign targeting US federal agencies). Use null ONLY if no organization can reasonably be identified.",
  "title": "Concise, descriptive breach headline (e.g., 'Qantas 2025 Customer Data Breach', 'Instagram 17M Profile Scraping Incident'). Must include company name, year, and nature of breach. Max 80 chars.",
  "industry": "Industry sector (e.g., healthcare, finance, retail, technology, government, education, null if unknown)",
  "country": "Country where the breached organization is headquartered or operates (ISO country name, null if unknown)",
  "continent": "Continent of the breached organization: Africa|Asia|Europe|North America|Oceania|South America (null if unknown)",
  "discovery_date": "Month and year the breach was internally discovered in YYYY-MM-DD format, always use 01 for the day (null if not clearly stated in the article)",
  "disclosure_date": "Month and year the breach was publicly disclosed or announced in YYYY-MM-DD format, always use 01 for the day (null if not clearly stated in the article)",
  "records_affected": number of records affected as integer (null if not specified),
  "breach_method": "Brief description of how the breach occurred (null if not specified)",
  "attack_vector": "One of: phishing|ransomware|api_exploit|insider|supply_chain|misconfiguration|malware|ddos|other (null if unclear)",
  "threat_actor": "Name of the threat actor, hacker group, or ransomware gang responsible (null if unknown)",
  "data_compromised": ["Array of data types exposed, e.g., emails, passwords, SSNs, credit cards"],
  "severity": "One of: low|medium|high|critical based on impact (null if cannot determine)",
  "cve_references": ["Array of CVE IDs mentioned, e.g., CVE-2024-1234"],
  "mitre_attack_techniques": ["Array of MITRE ATT&CK technique IDs if mentioned, e.g., T1078"],
  "summary": "500-600 word detailed summary of the breach, structured in 2-3 paragraphs separated by \\n\\n. First paragraph: what happened, who was affected, and the scale. Second paragraph: how it happened (technical details, attack vector, timeline). Third paragraph (if applicable): response, consequences, and current status.",
  "lessons_learned": "Brief analysis of what security controls failed and recommendations (null if cannot determine)"
}}

EXTRACTION GUIDELINES:

Country & Continent:
- Extract country from explicit mentions ("Spain's Ministry", "Italian university", "UK-based company")
- For well-known companies, use their headquarters country (e.g., Substack -> United States, Betterment -> United States)
- Derive continent from country (e.g., United States -> North America, Romania -> Europe, Netherlands -> Europe)
- Use null for both only if the company is completely unknown with no geographic context

Discovery Date vs Disclosure Date:
- discovery_date: when the breach was first detected/found internally
- disclosure_date: when it was publicly announced or reported
- Only populate these if the article explicitly states or clearly implies the date
- If only one date is mentioned and it is unclear which type it is, populate disclosure_date only
- Do NOT infer or guess dates from vague relative terms like "recently" or "last month"
- Always use YYYY-MM-01 format, dropping the exact day (e.g., "January 15, 2026" becomes "2026-01-01", "October 2025" becomes "2025-10-01")
- If only a year is given with no month, use null
- If dates are not clearly provided, use null

Threat Actor:
- Include the name of the ransomware gang, hacker group, or individual attacker if named
- Use null if no attribution is made

General:
- For records_affected, only include if a specific number is mentioned
- Be factual; do not speculate
- Ensure valid JSON format
"""

# Update Detection Prompt
UPDATE_DETECTION_PROMPT = """You are a cybersecurity intelligence analyst. Classify this article into exactly one of three categories:

NEW_BREACH      - A breach incident not already in the database.
GENUINE_UPDATE  - An existing breach in the database, but this article adds meaningfully new information:
                  revised/higher record counts, new legal or regulatory action, new technical attack details,
                  confirmation of previously unknown data types, remediation steps, or investigation findings.
DUPLICATE_SOURCE - An existing breach in the database, but this article adds no meaningfully new facts.
                  It re-reports the same incident from a different outlet with the same or very similar details
                  (same record count, same attack method, same discovery date, no new developments).

Article Title: {title}
Article URL: {url}
Article Summary: {summary}

Existing breaches in database (last 90 days):
{existing_breaches}

Classification rules:
- Match on company name first. If the company does not appear in the list, classify as NEW_BREACH.
- Once a company match is found, compare structured fields:
    - If records_affected, attack_vector, and discovery_date all match and the article adds no new details -> DUPLICATE_SOURCE
    - If any key field differs (record count revised, new attack detail revealed, legal/regulatory action, remediation) -> GENUINE_UPDATE
- When in doubt about whether new information is present, prefer DUPLICATE_SOURCE over GENUINE_UPDATE.
- When in doubt about whether the company matches at all, prefer NEW_BREACH over DUPLICATE_SOURCE.

Return JSON only:
{{
  "classification": "NEW_BREACH|GENUINE_UPDATE|DUPLICATE_SOURCE",
  "is_update": true if classification is GENUINE_UPDATE, false otherwise,
  "is_duplicate_source": true if classification is DUPLICATE_SOURCE, false otherwise,
  "related_breach_id": "UUID of the matching breach from the list above, or null if NEW_BREACH",
  "update_type": "One of: new_info|class_action|regulatory_fine|remediation|resolution|investigation|null",
  "confidence": 0.0 to 1.0 confidence score,
  "reasoning": "One sentence explanation citing the specific signal that drove your classification"
}}
"""

# Validation settings
MIN_SUMMARY_LENGTH = 50  # Minimum characters for summary
MAX_SUMMARY_LENGTH = 500  # Maximum characters for summary

# Classification settings (Two-Stage AI)
ENABLE_CLASSIFICATION = os.getenv('ENABLE_CLASSIFICATION', 'True').lower() in ('true', '1', 'yes')
CLASSIFICATION_CONFIDENCE_THRESHOLD = float(os.getenv('CLASSIFICATION_CONFIDENCE_THRESHOLD', '0.6'))
CLASSIFICATION_MAX_TOKENS = int(os.getenv('CLASSIFICATION_MAX_TOKENS', '300'))

# Rate limiting
REQUESTS_PER_MINUTE = 60

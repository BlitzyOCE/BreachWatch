"""
Configuration settings for BreachWatch scraper.

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

# RSS Feed Sources (10 sources)
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
    'darkreading': {
        'name': 'Dark Reading',
        'url': 'https://www.darkreading.com/rss_simple.asp',
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
    'cert_be': {
        'name': 'CERT.be',
        'url': 'https://cert.be/en/rss',
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
DEEPSEEK_MAX_TOKENS = int(os.getenv('DEEPSEEK_MAX_TOKENS', '4096'))

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Scraper Settings
ARTICLE_LOOKBACK_HOURS = int(os.getenv('ARTICLE_LOOKBACK_HOURS', '48'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))  # seconds
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))  # seconds

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# File Paths
PROCESSED_IDS_FILE = CACHE_DIR / "processed_ids.txt"

# AI Extraction Prompt
EXTRACTION_PROMPT = """You are a cybersecurity analyst extracting structured breach data from news articles.

Article Title: {title}
Article URL: {url}
Article Summary: {summary}

Extract the following information in JSON format. Be precise and only extract information that is explicitly stated in the article:

{{
  "company": "Exact company name mentioned (null if not specified)",
  "industry": "Industry sector (e.g., healthcare, finance, retail, technology, government, education, null if unknown)",
  "country": "Country or region (null if not specified)",
  "discovery_date": "Date breach was discovered in YYYY-MM-DD format (null if not specified)",
  "records_affected": number of records affected as integer (null if not specified),
  "breach_method": "Brief description of how the breach occurred (null if not specified)",
  "attack_vector": "One of: phishing|ransomware|api_exploit|insider|supply_chain|misconfiguration|malware|ddos|other (null if unclear)",
  "data_compromised": ["Array of data types exposed, e.g., emails, passwords, SSNs, credit cards"],
  "severity": "One of: low|medium|high|critical based on impact (null if cannot determine)",
  "cve_references": ["Array of CVE IDs mentioned, e.g., CVE-2024-1234"],
  "mitre_attack_techniques": ["Array of MITRE ATT&CK technique IDs if mentioned, e.g., T1078"],
  "summary": "2-3 sentence executive summary of the breach",
  "lessons_learned": "Brief analysis of what security controls failed and recommendations (null if cannot determine)"
}}

IMPORTANT:
- Use null for any field where information is not explicitly mentioned
- Do not speculate or infer information not stated in the article
- For records_affected, only include if a specific number is mentioned
- Be factual and concise
- Ensure valid JSON format
"""

# Update Detection Prompt
UPDATE_DETECTION_PROMPT = """You are determining if this article is about a NEW data breach or an UPDATE to an existing breach.

Article Title: {title}
Article URL: {url}
Article Summary: {summary}

Existing breaches in database (last 90 days):
{existing_breaches}

Analyze the article and determine:
1. Is this article discussing one of the existing breaches listed above?
2. Does it provide new information about a known incident (updates, fines, lawsuits, remediation)?
3. Or is this a completely new breach incident?

Return JSON:
{{
  "is_update": true or false,
  "related_breach_id": "UUID of the related breach from the list above, or null if this is a new breach",
  "update_type": "One of: new_info|class_action|regulatory_fine|remediation|resolution|investigation|null",
  "confidence": 0.0 to 1.0 confidence score,
  "reasoning": "Brief 1-2 sentence explanation of your decision"
}}

Guidelines:
- If the article mentions the same company AND similar timeframe as an existing breach, it's likely an update
- Updates often contain keywords like: lawsuit, fine, settlement, investigation, charges, remediation
- If in doubt, default to is_update: false (treat as new breach)
- Only set is_update: true if you are confident (confidence > 0.7)
"""

# Validation settings
MIN_SUMMARY_LENGTH = 50  # Minimum characters for summary
MAX_SUMMARY_LENGTH = 500  # Maximum characters for summary

# Rate limiting
REQUESTS_PER_MINUTE = 60

"""
BreachWatch Scraper - Main Orchestrator

Daily scraper that:
1. Fetches breach news from 10 RSS feeds
2. Extracts structured data using DeepSeek AI
3. Detects if articles are updates to existing breaches
4. Writes data to Supabase database
"""

import io
import logging
import sys
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

import feed_parser
from cache_manager import CacheManager
from ai_processor import AIProcessor
from db_writer import DatabaseWriter
from config import (
    LOG_LEVEL,
    LOGS_DIR,
    RSS_SOURCES,
    ARTICLE_LOOKBACK_HOURS,
    FUZZY_MATCH_THRESHOLD,
    ENABLE_CLASSIFICATION,
    CLASSIFICATION_CONFIDENCE_THRESHOLD
)


def _company_similarity(a: str, b: str) -> float:
    """Return similarity ratio between two company name strings (case-insensitive)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def find_in_run_duplicate(company: str, existing_breaches: list) -> dict | None:
    """
    Check if a company name closely matches any breach already written in this
    scraper run (identified by having no 'created_at' from the DB, i.e. appended
    during the current run).  Returns the matching breach dict or None.

    This guards against the case where two articles about the same breach are
    fetched in the same run before either is stored in the DB, which means
    detect_update() cannot catch the second one via database lookup.
    """
    for breach in existing_breaches:
        existing_company = breach.get('company') or ''
        if existing_company and _company_similarity(company, existing_company) >= FUZZY_MATCH_THRESHOLD:
            return breach
    return None


def setup_logging():
    """Configure logging to both file and console."""
    # Create logs directory
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Log file path with date
    log_file = LOGS_DIR / f"scraper_{date.today().isoformat()}.log"
    error_log_file = LOGS_DIR / f"errors_{date.today().isoformat()}.log"

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Clear any existing handlers
    logger.handlers = []

    # Console handler: use UTF-8 wrapper to avoid crashes on Windows (GBK) when
    # article titles contain non-ASCII characters (e.g. non-breaking hyphens).
    utf8_stdout = (
        io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stdout, 'buffer') else sys.stdout
    )
    console_handler = logging.StreamHandler(utf8_stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (detailed)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Error file handler
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)

    return logger


def main():
    """Main scraper workflow."""
    logger = setup_logging()

    logger.info("=" * 80)
    logger.info("BreachWatch Scraper Starting")
    logger.info(f"Date: {date.today().isoformat()}")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    # Statistics
    stats = {
        'articles_fetched': 0,
        'articles_recent': 0,
        'articles_new': 0,
        'classified_as_breach': 0,
        'classified_as_non_breach': 0,
        'breaches_created': 0,
        'updates_created': 0,
        'duplicates_skipped': 0,
        'errors': 0,
        'skipped': 0
    }

    try:
        # Initialize components
        logger.info("\n[1/7] Initializing components...")
        cache = CacheManager()
        ai_processor = AIProcessor()
        db = DatabaseWriter()
        logger.info("+ All components initialized")

        # Fetch RSS feeds
        logger.info(f"\n[2/7] Fetching RSS feeds from {len(RSS_SOURCES)} sources...")
        raw_articles = feed_parser.fetch_all_feeds(parallel=True)
        stats['articles_fetched'] = len(raw_articles)
        logger.info(f"+ Fetched {stats['articles_fetched']} total articles")

        if stats['articles_fetched'] == 0:
            logger.warning("No articles fetched from any source. Exiting.")
            return stats

        # Filter recent articles
        logger.info(f"\n[3/7] Filtering recent articles (last {ARTICLE_LOOKBACK_HOURS} hours)...")
        recent_articles = feed_parser.filter_recent_articles(raw_articles, hours=ARTICLE_LOOKBACK_HOURS)
        stats['articles_recent'] = len(recent_articles)
        logger.info(f"+ Filtered to {stats['articles_recent']} recent articles")

        # Deduplicate by URL across sources
        recent_articles = feed_parser.deduplicate_by_url(recent_articles)

        # Cache raw articles
        cache.cache_articles(raw_articles, date.today())

        # Check for new articles (not already processed)
        logger.info("\n[4/7] Checking for new articles...")
        new_articles = cache.get_new_articles(recent_articles)
        stats['articles_new'] = len(new_articles)
        logger.info(f"+ Found {stats['articles_new']} new articles to process")

        if stats['articles_new'] == 0:
            logger.info("No new articles to process. Exiting.")
            return stats

        # Fetch existing breaches for update detection
        logger.info("\n[5/7] Fetching existing breaches from database...")
        existing_breaches = db.get_existing_breaches(days=90)
        logger.info(f"+ Loaded {len(existing_breaches)} existing breaches")

        # Process each article
        logger.info(f"\n[6/7] Processing {stats['articles_new']} articles...")
        logger.info("-" * 80)

        extraction_results = []

        for idx, article in enumerate(new_articles, 1):
            logger.info(f"\n[{idx}/{stats['articles_new']}] Processing: {article['title'][:80]}...")
            logger.info(f"Source: {article['source_name']}")
            logger.info(f"URL: {article['url']}")

            try:
                # Stage 1: Is this an article about data breach or not?
                if ENABLE_CLASSIFICATION:
                    logger.info("  -> Stage 1: Classifying article...")
                    classification = ai_processor.classify_article(article)

                    if not classification['is_breach']:
                        logger.info(f"  X Not a breach (confidence: {classification['confidence']:.2%})")
                        logger.info(f"  Reason: {classification['reasoning']}")
                        stats['classified_as_non_breach'] += 1
                        stats['skipped'] += 1
                        cache.save_processed_id(article['url'])
                        continue

                    if classification['confidence'] < CLASSIFICATION_CONFIDENCE_THRESHOLD:
                        logger.info(f"  X Low confidence breach classification ({classification['confidence']:.2%} < {CLASSIFICATION_CONFIDENCE_THRESHOLD:.2%})")
                        logger.info(f"  Reason: {classification['reasoning']}")
                        stats['classified_as_non_breach'] += 1
                        stats['skipped'] += 1
                        cache.save_processed_id(article['url'])
                        continue

                    logger.info(f"  + Classified as BREACH (confidence: {classification['confidence']:.2%})")
                    stats['classified_as_breach'] += 1

                # Stage 2: Extract breach data using AI
                logger.info("  -> Stage 2: Extracting breach data with AI...")
                extracted = ai_processor.extract_breach_data(article)

                if not extracted:
                    logger.warning("  ✗ AI extraction failed, skipping article")
                    stats['errors'] += 1
                    continue

                logger.info(f"  ✓ Extracted: {extracted.get('company', 'Unknown')} - {extracted.get('severity', 'unknown')} severity")

                # Step 3: Detect if this is an update or new breach
                logger.info("  -> Detecting if update to existing breach...")

                # Fast in-run fuzzy check: if we already wrote a breach for this
                # company earlier in the same scraper run, skip the AI call and
                # treat this article as an update immediately.  This prevents
                # duplicates when two articles about the same company arrive in
                # the same run before either has been persisted to the DB.
                company_name = extracted.get('company', '')
                in_run_match = find_in_run_duplicate(company_name, existing_breaches) if company_name else None

                if in_run_match:
                    logger.info(
                        f"  + In-run duplicate detected: '{company_name}' matches "
                        f"'{in_run_match.get('company')}' (id: {in_run_match.get('id')}) "
                        f"- forcing as UPDATE without AI call"
                    )
                    update_check = {
                        'is_update': True,
                        'related_breach_id': in_run_match['id'],
                        'update_type': 'new_info',
                        'confidence': 1.0
                    }
                else:
                    update_check = ai_processor.detect_update(article, existing_breaches)

                if not update_check:
                    logger.warning("  X Update detection failed, treating as new breach")
                    update_check = {
                        'is_update': False,
                        'related_breach_id': None,
                        'update_type': None,
                        'confidence': 0.5
                    }

                # Step 4: Write to database
                is_duplicate = update_check.get('is_duplicate_source', False)
                is_genuine_update = (
                    update_check['is_update']
                    and update_check['confidence'] >= 0.7
                    and not is_duplicate
                )

                if is_genuine_update:
                    # Genuinely new information about an existing breach
                    logger.info(f"  + Identified as GENUINE UPDATE (confidence: {update_check['confidence']:.2%})")
                    logger.info(f"  Reason: {update_check.get('reasoning', '')}")
                    logger.info(f"  -> Writing update to breach {update_check['related_breach_id']}...")

                    update_id = db.write_breach_update(
                        extracted,
                        update_check['related_breach_id'],
                        article,
                        update_type=update_check.get('update_type', 'new_info'),
                        confidence=update_check['confidence']
                    )

                    if update_id:
                        logger.info(f"  + Update created: {update_id}")
                        stats['updates_created'] += 1
                    else:
                        logger.error("  X Failed to write update")
                        stats['errors'] += 1

                elif is_duplicate:
                    # Different source reporting the same facts — discard, no DB write
                    logger.info(
                        f"  ~ Duplicate source detected (confidence: {update_check['confidence']:.2%}): "
                        f"{update_check.get('reasoning', '')} -- skipping DB write"
                    )
                    stats['duplicates_skipped'] += 1

                else:
                    # This is a new breach
                    logger.info(f"  + Identified as NEW BREACH")
                    logger.info(f"  -> Writing new breach to database...")

                    breach_id = db.write_new_breach(extracted, article)

                    if breach_id:
                        logger.info(f"  + Breach created: {breach_id}")
                        stats['breaches_created'] += 1

                        # Add to existing breaches list for future update detection in this run
                        existing_breaches.append({
                            'id': breach_id,
                            'company': extracted.get('company'),
                            'discovery_date': extracted.get('discovery_date'),
                            'records_affected': extracted.get('records_affected'),
                            'attack_vector': extracted.get('attack_vector'),
                            'summary': extracted.get('summary'),
                            'created_at': datetime.now().isoformat()
                        })
                    else:
                        logger.error("  X Failed to write breach")
                        stats['errors'] += 1

                # Mark as processed
                cache.save_processed_id(article['url'])

                # Save extraction result for debugging
                extraction_results.append({
                    'article_url': article['url'],
                    'article_title': article['title'],
                    'extracted': extracted,
                    'update_check': update_check,
                    'processed_at': datetime.now().isoformat()
                })

            except Exception as e:
                logger.error(f"  X Error processing article: {e}")
                logger.exception(e)
                stats['errors'] += 1
                continue

        # Cache extraction results
        logger.info("\n[7/7] Caching extraction results...")
        cache.cache_extraction_results(extraction_results, date.today())

    except Exception as e:
        logger.error(f"\nX Fatal error in scraper: {e}")
        logger.exception(e)
        stats['errors'] += 1

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("Scraper Completed")
    logger.info("=" * 80)
    logger.info(f"Articles Fetched:        {stats['articles_fetched']}")
    logger.info(f"Recent Articles:         {stats['articles_recent']}")
    logger.info(f"New Articles:            {stats['articles_new']}")
    if ENABLE_CLASSIFICATION:
        logger.info(f"Classified as Breach:    {stats['classified_as_breach']}")
        logger.info(f"Classified as Non-Breach:{stats['classified_as_non_breach']}")
        logger.info(f"Skipped (Non-Breach):    {stats['skipped']}")
    logger.info(f"Breaches Created:        {stats['breaches_created']}")
    logger.info(f"Updates Created:         {stats['updates_created']}")
    logger.info(f"Duplicates Skipped:      {stats['duplicates_skipped']}")
    logger.info(f"Errors:                  {stats['errors']}")
    logger.info(f"Completion Time:         {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    return stats


if __name__ == '__main__':
    try:
        stats = main()
        sys.exit(0 if stats['errors'] == 0 else 1)
    except KeyboardInterrupt:
        print("\nScraper interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

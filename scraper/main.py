"""
BreachCase Scraper - Main Orchestrator

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
    FUZZY_CANDIDATE_THRESHOLD,
    ENABLE_CLASSIFICATION,
    CLASSIFICATION_CONFIDENCE_THRESHOLD
)


def _company_similarity(a: str, b: str) -> float:
    """Return similarity ratio between two company name strings (case-insensitive)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def get_fuzzy_candidates(company: str, all_stubs: list) -> list:
    """
    Return all breach stubs whose company name is similar enough to be a
    candidate match for the given company name.

    Uses FUZZY_CANDIDATE_THRESHOLD (default 0.6) as a wide net — lower than
    the high-confidence FUZZY_MATCH_THRESHOLD.  The returned candidates are
    passed to the AI which makes the final NEW_BREACH / GENUINE_UPDATE /
    DUPLICATE_SOURCE decision.

    Covers the full database with no date or count limit, so even breaches
    older than 90 days are never invisible to dedup.
    """
    if not company:
        return []
    return [
        stub for stub in all_stubs
        if _company_similarity(company, stub.get('company') or '') >= FUZZY_CANDIDATE_THRESHOLD
    ]


def _compute_match_signals(extracted: dict, candidates: list) -> dict:
    """
    Compute structural match signals between extracted article data and each candidate breach.

    Returns a dict keyed by breach UUID:
      {
        breach_id: {
            'records_match': bool | None,   # None if either value is missing
            'attack_vector_match': bool | None,
            'existing_records': int | None,
            'existing_attack_vector': str | None,
        }
      }
    """
    signals = {}
    extracted_records = extracted.get('records_affected')
    extracted_vector = extracted.get('attack_vector')

    for candidate in candidates:
        bid = candidate.get('id')
        if not bid:
            continue

        existing_records = candidate.get('records_affected')
        existing_vector = candidate.get('attack_vector')

        records_match = None
        if extracted_records and existing_records:
            larger = max(extracted_records, existing_records)
            records_match = abs(extracted_records - existing_records) / larger <= 0.10

        attack_vector_match = None
        if extracted_vector and existing_vector:
            attack_vector_match = extracted_vector == existing_vector

        signals[bid] = {
            'records_match': records_match,
            'attack_vector_match': attack_vector_match,
            'existing_records': existing_records,
            'existing_attack_vector': existing_vector,
        }

    return signals


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
    logger.info("BreachCase Scraper Starting")
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

        # Fetch all breach stubs for dedup pre-filter (no date limit)
        logger.info("\n[5/7] Fetching all breach stubs from database for dedup...")
        all_breach_stubs = db.get_all_breach_stubs()
        logger.info(f"+ Loaded {len(all_breach_stubs)} breach stubs")

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
                    logger.warning("  X AI extraction failed, skipping article")
                    stats['errors'] += 1
                    continue

                logger.info(f"  + Extracted: {extracted.get('company', 'Unknown')} - {extracted.get('severity', 'unknown')} severity")

                # Stage 3: Fuzzy pre-filter then AI update detection
                logger.info("  -> Stage 3: Dedup check...")

                company_name = extracted.get('company', '')
                candidates = get_fuzzy_candidates(company_name, all_breach_stubs)

                if not candidates:
                    # No plausible match anywhere in the full database - skip AI call
                    logger.info("  + No fuzzy candidates found - treating as new breach")
                    update_check = {
                        'is_update': False,
                        'is_duplicate_source': False,
                        'related_breach_id': None,
                        'update_type': None,
                        'confidence': 1.0,
                        'reasoning': 'No company name match found in full database'
                    }
                else:
                    logger.info(f"  + {len(candidates)} fuzzy candidate(s) found - asking AI to classify...")
                    candidate_ids = [c['id'] for c in candidates]
                    candidate_details = db.get_breaches_by_ids(candidate_ids)
                    match_signals = _compute_match_signals(extracted, candidate_details)
                    update_check = ai_processor.detect_update(article, candidate_details, match_signals)

                    if not update_check:
                        logger.warning("  X Update detection failed, treating as new breach")
                        update_check = {
                            'is_update': False,
                            'is_duplicate_source': False,
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
                        confidence=update_check['confidence'],
                        content=update_check.get('update_summary'),
                    )

                    if update_id:
                        logger.info(f"  + Update created: {update_id}")
                        stats['updates_created'] += 1
                    else:
                        logger.error("  X Failed to write update")
                        stats['errors'] += 1

                elif is_duplicate:
                    # Different source reporting the same facts - discard, no DB write
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

                        # Add to stub list so within-run articles about the same
                        # company are caught by the pre-filter on subsequent iterations.
                        # Only id + company needed - full details are fetched from DB
                        # via get_breaches_by_ids() if this becomes a candidate.
                        all_breach_stubs.append({
                            'id': breach_id,
                            'company': extracted.get('company'),
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

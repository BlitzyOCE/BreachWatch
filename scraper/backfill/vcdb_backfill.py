"""
VCDB GitHub Issues backfill orchestrator.

Imports historical breach data (2021+) from VCDB GitHub Issues by extracting
linked article URLs and feeding them through the existing AI pipeline:
  classify -> extract -> detect_update -> db_write

Each article URL is written to the shared processed_ids cache immediately after
processing, so the script can be safely interrupted and restarted - already-
processed URLs are skipped on the next run.

Usage:
    cd scraper && python backfill/vcdb_backfill.py [options]

Options:
    --dry-run          Fetch and parse issues, log what would be processed,
                       but skip AI calls and DB writes.
    --limit N          Process only the first N new articles (for testing).
    --since YYYY-MM-DD Override the default 2021-01-01 cutoff.

Required environment variables (in scraper/.env):
    DEEPSEEK_API_KEY   DeepSeek API key
    SUPABASE_URL       Supabase project URL
    SUPABASE_KEY       Supabase service key

Optional environment variables:
    GITHUB_TOKEN       GitHub personal access token (5k req/hour vs 60/hour)
    VCDB_SINCE_DATE    Default since date, overridden by --since flag
"""

import argparse
import io
import logging
import os
import sys
from datetime import date, datetime

# Add parent scraper directory to path so existing modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from vcdb_fetcher import fetch_all_issues, extract_article_urls, fetch_article
from cache_manager import CacheManager
from ai_processor import AIProcessor
from db_writer import DatabaseWriter
from config import (
    LOGS_DIR,
    LOG_LEVEL,
    ENABLE_CLASSIFICATION,
    CLASSIFICATION_CONFIDENCE_THRESHOLD,
)
# Fuzzy matching helpers live in main.py (not in a shared lib yet)
from main import get_fuzzy_candidates, _compute_match_signals


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    """Configure logging to console (INFO) and log files (DEBUG + ERROR)."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    log_file = LOGS_DIR / f"backfill_{today}.log"
    error_log_file = LOGS_DIR / f"backfill_errors_{today}.log"

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    root.handlers = []

    # UTF-8 console handler - avoids crashes on Windows when titles have non-ASCII chars
    stdout = (
        io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stdout, 'buffer') else sys.stdout
    )
    console = logging.StreamHandler(stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
    root.addHandler(console)

    file_h = logging.FileHandler(log_file, encoding='utf-8')
    file_h.setLevel(logging.DEBUG)
    file_h.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root.addHandler(file_h)

    err_h = logging.FileHandler(error_log_file, encoding='utf-8')
    err_h.setLevel(logging.ERROR)
    err_h.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root.addHandler(err_h)

    return logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='VCDB GitHub Issues backfill for BreachBase',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Print what would be processed without calling AI or writing to DB',
    )
    parser.add_argument(
        '--limit', type=int, default=None, metavar='N',
        help='Process only the first N new articles (useful for testing)',
    )
    parser.add_argument(
        '--since', type=str, default=None, metavar='YYYY-MM-DD',
        help='Override since date (default: VCDB_SINCE_DATE env var or 2021-01-01)',
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> dict:
    args = parse_args()
    logger = setup_logging()

    since = args.since or os.getenv('VCDB_SINCE_DATE', '2021-01-01')
    github_token = os.getenv('GITHUB_TOKEN')

    logger.info("=" * 80)
    logger.info("VCDB GitHub Issues Backfill")
    logger.info(f"Run date : {date.today().isoformat()}")
    logger.info(f"Since    : {since}")
    logger.info(f"Dry run  : {args.dry_run}")
    if args.limit:
        logger.info(f"Limit    : {args.limit} articles")
    if not github_token:
        logger.warning(
            "GITHUB_TOKEN not set - using unauthenticated API "
            "(60 req/hour limit; a token is strongly recommended)"
        )
    logger.info("=" * 80)

    stats = {
        'issues_fetched': 0,
        'urls_extracted': 0,
        'articles_new': 0,
        'articles_fetched': 0,
        'skipped_not_breach': 0,
        'breaches_created': 0,
        'updates_created': 0,
        'duplicates_skipped': 0,
        'errors': 0,
    }

    # ------------------------------------------------------------------
    # Step 1: Fetch VCDB issues
    # ------------------------------------------------------------------
    logger.info("\n[1/5] Fetching VCDB GitHub issues...")
    issues = fetch_all_issues(since=since, token=github_token)
    stats['issues_fetched'] = len(issues)
    logger.info(f"+ Fetched {len(issues)} issues")

    if not issues:
        logger.warning("No issues returned. Verify GITHUB_TOKEN and network access.")
        return stats

    # ------------------------------------------------------------------
    # Step 2: Extract candidate article URLs from issue bodies
    # ------------------------------------------------------------------
    logger.info("\n[2/5] Extracting article URLs from issue bodies...")
    candidate_articles = []
    for issue in issues:
        urls = extract_article_urls(issue['body'])
        if not urls:
            logger.debug(f"Issue #{issue['issue_number']}: no article URLs found")
            continue
        for url in urls:
            candidate_articles.append({'url': url, 'issue': issue})

    stats['urls_extracted'] = len(candidate_articles)
    logger.info(f"+ Extracted {len(candidate_articles)} candidate article URLs")

    # ------------------------------------------------------------------
    # Step 3: Filter already-processed URLs
    # ------------------------------------------------------------------
    logger.info("\n[3/5] Filtering already-processed URLs via cache...")
    cache = CacheManager()
    processed_ids = cache.load_processed_ids()
    new_candidates = [c for c in candidate_articles if c['url'] not in processed_ids]
    filtered_count = len(candidate_articles) - len(new_candidates)
    if filtered_count:
        logger.info(f"  Filtered out {filtered_count} already-processed URLs")
    stats['articles_new'] = len(new_candidates)
    logger.info(f"+ {len(new_candidates)} new URLs to process")

    if not new_candidates:
        logger.info("Nothing new to process. Exiting.")
        return stats

    # Apply --limit
    if args.limit:
        new_candidates = new_candidates[:args.limit]
        logger.info(f"  (limited to first {args.limit} articles by --limit)")

    # Dry-run: just log and exit
    if args.dry_run:
        logger.info("\n[DRY RUN] Would process the following URLs:")
        for i, c in enumerate(new_candidates, 1):
            issue = c['issue']
            logger.info(
                f"  {i:4d}. Issue #{issue['issue_number']} | {c['url']}"
            )
        logger.info(f"\n[DRY RUN] Total: {len(new_candidates)} articles")
        return stats

    # ------------------------------------------------------------------
    # Step 4: Initialise pipeline components
    # ------------------------------------------------------------------
    logger.info("\n[4/5] Initialising pipeline components...")
    ai = AIProcessor()
    db = DatabaseWriter()
    all_breach_stubs = db.get_all_breach_stubs()
    logger.info(f"+ Loaded {len(all_breach_stubs)} existing breach stubs")

    # ------------------------------------------------------------------
    # Step 5: Process each article through the pipeline
    # ------------------------------------------------------------------
    logger.info(f"\n[5/5] Processing {len(new_candidates)} articles...")
    logger.info("-" * 80)

    for idx, candidate in enumerate(new_candidates, 1):
        url = candidate['url']
        issue = candidate['issue']
        logger.info(
            f"\n[{idx}/{len(new_candidates)}] "
            f"Issue #{issue['issue_number']}: {issue['title'][:70]}"
        )
        logger.info(f"  URL: {url}")

        try:
            # --- Fetch article content ---
            article = fetch_article(url, issue)
            if not article:
                logger.warning("  Skipped: could not fetch / extract article content")
                continue

            stats['articles_fetched'] += 1
            logger.info(f"  + Fetched: '{article['title'][:60]}' ({len(article['summary'])} chars)")

            # --- Classify ---
            if ENABLE_CLASSIFICATION:
                classification = ai.classify_article(article)
                if (
                    not classification['is_breach']
                    or classification['confidence'] < CLASSIFICATION_CONFIDENCE_THRESHOLD
                ):
                    logger.info(
                        f"  X Not a breach / low confidence "
                        f"({classification['confidence']:.2%}): "
                        f"{classification.get('reasoning', '')}"
                    )
                    stats['skipped_not_breach'] += 1
                    continue
                logger.info(f"  + BREACH ({classification['confidence']:.2%})")

            # --- Extract structured breach data ---
            breach_data = ai.extract_breach_data(article)
            if not breach_data:
                logger.warning("  X AI extraction failed, skipping")
                stats['errors'] += 1
                continue

            logger.info(
                f"  + Extracted: {breach_data.get('company', 'Unknown')} "
                f"[{breach_data.get('severity', 'unknown')}]"
            )

            # --- Dedup: fuzzy pre-filter + AI update detection ---
            company_name = breach_data.get('company', '')
            candidates = get_fuzzy_candidates(
                company_name, breach_data.get('title', ''), all_breach_stubs
            )

            if not candidates:
                update_check = {
                    'is_update': False,
                    'is_duplicate_source': False,
                    'related_breach_id': None,
                    'update_type': None,
                    'confidence': 1.0,
                    'reasoning': 'No company name match in database',
                }
            else:
                logger.info(f"  + {len(candidates)} fuzzy candidate(s) - running AI dedup...")
                candidate_ids = [c['id'] for c in candidates]
                candidate_details = db.get_breaches_by_ids(candidate_ids)
                match_signals = _compute_match_signals(breach_data, candidate_details)
                update_check = ai.detect_update(article, candidate_details, match_signals)
                if not update_check:
                    update_check = {
                        'is_update': False,
                        'is_duplicate_source': False,
                        'related_breach_id': None,
                        'update_type': None,
                        'confidence': 0.5,
                        'reasoning': 'Update detection failed, defaulting to new breach',
                    }

            # --- Write to database ---
            is_duplicate = update_check.get('is_duplicate_source', False)
            is_genuine_update = (
                update_check['is_update']
                and update_check['confidence'] >= 0.7
                and not is_duplicate
            )

            if is_genuine_update:
                logger.info(
                    f"  + GENUINE UPDATE (confidence: {update_check['confidence']:.2%}) "
                    f"-> breach {update_check['related_breach_id']}"
                )
                update_id = db.write_breach_update(
                    breach_data,
                    update_check['related_breach_id'],
                    article,
                    update_type=update_check.get('update_type', 'new_info'),
                    confidence=update_check['confidence'],
                    content=update_check.get('update_summary'),
                )
                if update_id:
                    stats['updates_created'] += 1
                else:
                    logger.error("  X Failed to write update")
                    stats['errors'] += 1

            elif is_duplicate:
                logger.info(
                    f"  ~ DUPLICATE SOURCE ({update_check['confidence']:.2%}): "
                    f"{update_check.get('reasoning', '')}"
                )
                stats['duplicates_skipped'] += 1

            else:
                logger.info("  + NEW BREACH")
                breach_id = db.write_new_breach(breach_data, article)
                if breach_id:
                    logger.info(f"  + Breach created: {breach_id}")
                    stats['breaches_created'] += 1
                    # Add to in-memory stubs so same-company articles later in
                    # this run are caught by the fuzzy pre-filter
                    all_breach_stubs.append({
                        'id': breach_id,
                        'company': breach_data.get('company'),
                        'title': breach_data.get('title'),
                    })
                else:
                    logger.error("  X Failed to write breach")
                    stats['errors'] += 1

        except Exception as exc:
            logger.error(f"  X Unhandled error: {exc}")
            logger.exception(exc)
            stats['errors'] += 1

        finally:
            # Always mark as processed - prevents retrying dead links on restart
            cache.save_processed_id(url)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    logger.info("\n" + "=" * 80)
    logger.info("VCDB Backfill Complete")
    logger.info("=" * 80)
    logger.info(f"Issues fetched      : {stats['issues_fetched']}")
    logger.info(f"URLs extracted      : {stats['urls_extracted']}")
    logger.info(f"New URLs (uncached) : {stats['articles_new']}")
    logger.info(f"Articles fetched    : {stats['articles_fetched']}")
    logger.info(f"Skipped (not breach): {stats['skipped_not_breach']}")
    logger.info(f"Breaches created    : {stats['breaches_created']}")
    logger.info(f"Updates created     : {stats['updates_created']}")
    logger.info(f"Duplicates skipped  : {stats['duplicates_skipped']}")
    logger.info(f"Errors              : {stats['errors']}")
    logger.info("=" * 80)

    return stats


if __name__ == '__main__':
    try:
        result = main()
        sys.exit(0 if result['errors'] == 0 else 1)
    except KeyboardInterrupt:
        print("\nBackfill interrupted by user")
        sys.exit(1)
    except Exception as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)

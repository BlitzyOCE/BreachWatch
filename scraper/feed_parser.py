"""
RSS feed parsing and article fetching module.

Fetches articles from 10 RSS feeds, parses them, and filters by date.
"""

import feedparser
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from dateutil import parser as date_parser

from config import RSS_SOURCES, ARTICLE_LOOKBACK_HOURS, REQUEST_TIMEOUT, MAX_RETRIES, MAX_FEED_WORKERS

logger = logging.getLogger(__name__)

# HTTP headers to avoid being blocked by bot detection
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parse various date formats from RSS feeds.

    Args:
        date_string: Date string in various formats

    Returns:
        datetime object or None if parsing fails
    """
    if not date_string:
        return None

    try:
        # Try feedparser's parsed time first
        return date_parser.parse(date_string)
    except Exception as e:
        logger.warning(f"Failed to parse date '{date_string}': {e}")
        return None


def fetch_feed(source_key: str, source_config: Dict) -> List[Dict]:
    """
    Fetch and parse a single RSS feed.

    Args:
        source_key: Identifier for the source (e.g., 'bleepingcomputer')
        source_config: Configuration dict with 'name', 'url', 'language'

    Returns:
        List of article dictionaries
    """
    articles = []
    url = source_config['url']
    source_name = source_config['name']

    logger.info(f"Fetching feed: {source_name} ({url})")

    try:
        # Fetch the RSS feed with timeout and proper headers to avoid blocking
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # Parse the feed
        feed = feedparser.parse(response.content)

        if feed.bozo:
            logger.warning(f"Feed {source_name} has parsing issues: {feed.bozo_exception}")

        # Extract articles
        for entry in feed.entries:
            try:
                article = parse_article(entry, source_key, source_name)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.error(f"Error parsing entry from {source_name}: {e}")
                continue

        logger.info(f"Fetched {len(articles)} articles from {source_name}")

    except requests.Timeout:
        logger.error(f"Timeout fetching feed {source_name}")
    except requests.RequestException as e:
        logger.error(f"Error fetching feed {source_name}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching {source_name}: {e}")

    return articles


def parse_article(entry, source_key: str, source_name: str) -> Optional[Dict]:
    """
    Parse a single RSS feed entry into standardized article format.

    Args:
        entry: feedparser entry object
        source_key: Source identifier
        source_name: Human-readable source name

    Returns:
        Article dictionary or None if required fields missing
    """
    # Extract URL (required)
    url = entry.get('link') or entry.get('id')
    if not url:
        logger.warning(f"Entry from {source_name} missing URL, skipping")
        return None

    # Extract title (required)
    title = entry.get('title', '').strip()
    if not title:
        logger.warning(f"Entry from {source_name} missing title, skipping: {url}")
        return None

    # Extract published date
    published_date = None
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            published_date = datetime(*entry.published_parsed[:6])
        except Exception:
            pass

    if not published_date and 'published' in entry:
        published_date = parse_date(entry.published)

    if not published_date and 'updated' in entry:
        published_date = parse_date(entry.updated)

    # If still no date, use current time
    if not published_date:
        published_date = datetime.now()
        logger.warning(f"No date found for article '{title}', using current time")

    # Extract summary/description
    summary = ''
    if 'summary' in entry:
        summary = entry.summary
    elif 'description' in entry:
        summary = entry.description
    elif 'content' in entry and len(entry.content) > 0:
        summary = entry.content[0].get('value', '')

    # Clean HTML tags from summary if present
    import re
    summary = re.sub(r'<[^>]+>', '', summary).strip()

    article = {
        'source_key': source_key,
        'source_name': source_name,
        'url': url,
        'title': title,
        'published': published_date,
        'summary': summary[:1000],  # Limit summary length
        'full_text': None  # Could be filled later by fetching full article
    }

    return article


def filter_recent_articles(articles: List[Dict], hours: int = ARTICLE_LOOKBACK_HOURS) -> List[Dict]:
    """
    Filter articles to only include those published within the last N hours.

    Args:
        articles: List of article dictionaries
        hours: Number of hours to look back

    Returns:
        Filtered list of articles
    """
    cutoff_time = datetime.now() - timedelta(hours=hours)

    recent = [
        article for article in articles
        if article['published'] and article['published'] >= cutoff_time
    ]

    logger.info(f"Filtered {len(articles)} articles to {len(recent)} within last {hours} hours")

    return recent


def fetch_all_feeds(parallel: bool = True) -> List[Dict]:
    """
    Fetch articles from all configured RSS feeds.

    Args:
        parallel: Whether to fetch feeds in parallel (default: True)

    Returns:
        Combined list of articles from all sources
    """
    all_articles = []

    if parallel:
        # Fetch feeds in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=MAX_FEED_WORKERS) as executor:
            future_to_source = {
                executor.submit(fetch_feed, key, config): key
                for key, config in RSS_SOURCES.items()
            }

            for future in as_completed(future_to_source):
                source_key = future_to_source[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                except Exception as e:
                    logger.error(f"Error fetching {source_key}: {e}")
    else:
        # Fetch feeds sequentially
        for source_key, source_config in RSS_SOURCES.items():
            try:
                articles = fetch_feed(source_key, source_config)
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Error fetching {source_key}: {e}")

    logger.info(f"Total articles fetched from all sources: {len(all_articles)}")

    return all_articles


def deduplicate_by_url(articles: List[Dict]) -> List[Dict]:
    """
    Remove duplicate articles based on URL.

    Some articles may appear in multiple feeds with slight variations.

    Args:
        articles: List of article dictionaries

    Returns:
        Deduplicated list of articles
    """
    seen_urls = set()
    unique_articles = []

    for article in articles:
        url = article['url']
        if url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)

    duplicates_removed = len(articles) - len(unique_articles)
    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate articles (same URL)")

    return unique_articles


# For testing/debugging
if __name__ == '__main__':
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("Fetching all RSS feeds...")
    articles = fetch_all_feeds()
    print(f"\nTotal articles fetched: {len(articles)}")

    print("\nFiltering recent articles...")
    recent = filter_recent_articles(articles, hours=48)
    print(f"Recent articles (last 48h): {len(recent)}")

    print("\nDeduplicating...")
    unique = deduplicate_by_url(recent)
    print(f"Unique articles: {len(unique)}")

    if unique:
        print("\nSample article:")
        sample = unique[0]
        print(f"Title: {sample['title']}")
        print(f"Source: {sample['source_name']}")
        print(f"URL: {sample['url']}")
        print(f"Published: {sample['published']}")
        print(f"Summary: {sample['summary'][:200]}...")

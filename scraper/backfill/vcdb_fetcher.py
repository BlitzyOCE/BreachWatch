"""
VCDB GitHub Issues fetcher, URL parser, and article fetcher.

Three responsibilities:
  1. fetch_all_issues()     - Paginated GitHub Issues REST API client
  2. extract_article_urls() - Pull article URLs out of issue body text
  3. fetch_article()        - Download full article text via trafilatura
"""

import os
import re
import sys
import time
import logging
from datetime import datetime
from typing import Optional

import requests

# Add parent scraper directory to path so sibling modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/repos/vz-risk/VCDB/issues"

# Domains that are never article sources
_EXCLUDE_DOMAINS = {
    'github.com',
    'twitter.com',
    'x.com',
    'facebook.com',
    'linkedin.com',
    't.co',
    'youtube.com',
    'youtu.be',
}

# File extensions that indicate non-article resources
_EXCLUDE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.pdf'}


# ---------------------------------------------------------------------------
# Step 1: GitHub Issues fetcher
# ---------------------------------------------------------------------------

def _handle_rate_limit(response: requests.Response) -> None:
    """Sleep if the GitHub rate limit is nearly exhausted."""
    remaining = int(response.headers.get('X-RateLimit-Remaining', 999))
    if remaining <= 5:
        reset_ts = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
        sleep_secs = max(reset_ts - time.time(), 1) + 2  # +2s buffer
        logger.warning(
            f"GitHub rate limit low ({remaining} remaining), "
            f"sleeping {sleep_secs:.0f}s until reset..."
        )
        time.sleep(sleep_secs)


def fetch_all_issues(since: str = "2021-01-01", token: Optional[str] = None) -> list:
    """
    Paginate through all VCDB GitHub Issues created on or after `since`.

    The GitHub `since` parameter filters by *updated_at*, so issues updated
    recently but created before the cutoff are fetched and then discarded
    client-side by checking `created_at`.

    Args:
        since: ISO date string (YYYY-MM-DD). Only issues created >= this date
               are returned.
        token: GitHub personal access token. Required for the 5,000 req/hour
               rate limit - without it the 60 req/hour limit will be hit on
               large repos.

    Returns:
        List of issue dicts (pull requests excluded).
    """
    headers = {'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    since_dt = datetime.fromisoformat(since)
    since_iso = since_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    issues = []
    page = 1

    while True:
        params = {
            'state': 'all',
            'per_page': 100,
            'page': page,
            'since': since_iso,
        }
        logger.info(f"Fetching GitHub issues page {page}...")
        try:
            response = requests.get(
                GITHUB_API_URL, headers=headers, params=params, timeout=30
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error(f"GitHub API request failed on page {page}: {exc}")
            break

        _handle_rate_limit(response)

        batch = response.json()
        if not batch:
            break  # No more pages

        page_issues = 0
        for item in batch:
            # Skip pull requests - GitHub Issues API returns both
            if 'pull_request' in item:
                continue

            # Client-side filter: must be created on or after the since date
            created_at = item.get('created_at', '')
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if created_dt.date() < since_dt.date():
                        continue
                except ValueError:
                    pass

            issues.append({
                'issue_number': item['number'],
                'title': item.get('title', ''),
                'body': item.get('body') or '',
                'labels': [label['name'] for label in item.get('labels', [])],
                'created_at': item.get('created_at', ''),
                'state': item.get('state', 'open'),
                'html_url': item.get('html_url', ''),
            })
            page_issues += 1

        logger.info(
            f"  Page {page}: {len(batch)} items, "
            f"{page_issues} added, {len(issues)} total so far"
        )

        # Check for a next page via the Link header
        if 'rel="next"' not in response.headers.get('Link', ''):
            break
        page += 1

    logger.info(f"Finished fetching: {len(issues)} issues total")
    return issues


# ---------------------------------------------------------------------------
# Step 2: Issue body URL parser
# ---------------------------------------------------------------------------

def extract_article_urls(issue_body: str) -> list:
    """
    Extract article URLs from a VCDB issue body.

    Handles bare URLs, markdown links, and mixed content. Filters out GitHub
    URLs, image files, and social media links.

    Args:
        issue_body: Raw issue body text.

    Returns:
        Deduplicated list of candidate article URLs (insertion order preserved).
    """
    if not issue_body:
        return []

    raw_urls = re.findall(r'https?://[^\s\)\]\'"<>]+', issue_body)

    seen: set = set()
    result = []

    for url in raw_urls:
        # Strip trailing punctuation captured as part of the URL pattern
        url = url.rstrip('.,;:!?)')
        if not url or url in seen:
            continue
        seen.add(url)

        # Extract bare domain for filtering
        try:
            domain = url.split('//', 1)[1].split('/', 1)[0].lower().split(':')[0]
        except IndexError:
            continue

        # Exclude known non-article domains
        if any(domain == d or domain.endswith('.' + d) for d in _EXCLUDE_DOMAINS):
            continue

        # Exclude image and binary file extensions
        path_lower = url.split('?')[0].lower()
        if any(path_lower.endswith(ext) for ext in _EXCLUDE_EXTENSIONS):
            continue

        result.append(url)

    return result


# ---------------------------------------------------------------------------
# Step 3: Article fetcher (trafilatura)
# ---------------------------------------------------------------------------

def fetch_article(url: str, issue: dict) -> Optional[dict]:
    """
    Download and extract full article text from a URL using trafilatura.

    Produces an article dict in the same format as feed_parser.py so the
    existing AI pipeline (classify -> extract -> detect_update -> db_write)
    can consume it without modification.

    Args:
        url:   Article URL to fetch.
        issue: Parent VCDB issue dict, used as fallback for title and date.

    Returns:
        Article dict with keys: source_key, source_name, url, title,
        published (datetime), summary, full_text.
        Returns None if the article cannot be fetched or has too little content.
    """
    try:
        import trafilatura
    except ImportError:
        logger.error("trafilatura is not installed. Run: pip install 'trafilatura>=1.8'")
        raise

    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning(f"fetch_url returned None (dead link / timeout / bot block): {url}")
            return None

        extracted = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
        if not extracted:
            logger.warning(f"extract returned None (paywall / JS-rendered / empty page): {url}")
            return None

        # Require at least 100 chars - catches cookie walls and redirect-to-homepage cases
        if len(extracted) < 100:
            logger.warning(
                f"Article text too short ({len(extracted)} chars, need 100): {url}"
            )
            return None

        # Pull metadata for title and publication date
        meta = trafilatura.extract_metadata(downloaded)
        title = (meta.title if meta and meta.title else None) or issue['title']

        # Parse date into a datetime object - db_writer._write_source() calls .date() on it
        published: Optional[datetime] = None
        raw_date = meta.date if meta and meta.date else None
        if raw_date:
            try:
                published = datetime.strptime(raw_date[:10], '%Y-%m-%d')
            except ValueError:
                pass

        if published is None:
            # Fall back to the issue's creation date
            try:
                published = datetime.fromisoformat(
                    issue['created_at'].replace('Z', '+00:00')
                ).replace(tzinfo=None)
            except (ValueError, AttributeError):
                published = datetime.now()

        return {
            'source_key': 'vcdb_backfill',
            'source_name': 'VCDB Backfill',
            'url': url,
            'title': title,
            'published': published,
            'summary': extracted[:3000],  # cap to keep AI prompts manageable
            'full_text': None,
        }

    except Exception as exc:
        logger.error(f"Unexpected error fetching article {url}: {exc}")
        return None

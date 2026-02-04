"""
Local file cache management module.

Handles caching of raw articles, tracking processed IDs, and deduplication.
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Set
from filelock import FileLock

from config import CACHE_DIR, PROCESSED_IDS_FILE

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages local file cache for articles and processed IDs."""

    def __init__(self, cache_dir: Path = CACHE_DIR, processed_ids_file: Path = PROCESSED_IDS_FILE):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache files
            processed_ids_file: Path to file tracking processed article URLs
        """
        self.cache_dir = cache_dir
        self.processed_ids_file = processed_ids_file

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Ensure processed IDs file exists
        if not self.processed_ids_file.exists():
            self.processed_ids_file.touch()

        # Lock file for concurrent access
        self.lock_file = self.processed_ids_file.with_suffix('.lock')

    def load_processed_ids(self) -> Set[str]:
        """
        Load set of already-processed article URLs.

        Returns:
            Set of processed URLs
        """
        processed = set()

        try:
            with open(self.processed_ids_file, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url:
                        processed.add(url)

            logger.info(f"Loaded {len(processed)} processed article IDs")

        except FileNotFoundError:
            logger.info("No processed IDs file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading processed IDs: {e}")

        return processed

    def save_processed_id(self, url: str):
        """
        Append a URL to the processed IDs file.

        Uses file locking to prevent concurrent write issues.

        Args:
            url: Article URL to mark as processed
        """
        try:
            lock = FileLock(str(self.lock_file))
            with lock:
                with open(self.processed_ids_file, 'a', encoding='utf-8') as f:
                    f.write(f"{url}\n")

            logger.debug(f"Saved processed ID: {url}")

        except Exception as e:
            logger.error(f"Error saving processed ID: {e}")

    def save_processed_ids_batch(self, urls: List[str]):
        """
        Append multiple URLs to the processed IDs file in one batch.

        Args:
            urls: List of article URLs to mark as processed
        """
        if not urls:
            return

        try:
            lock = FileLock(str(self.lock_file))
            with lock:
                with open(self.processed_ids_file, 'a', encoding='utf-8') as f:
                    for url in urls:
                        f.write(f"{url}\n")

            logger.info(f"Saved {len(urls)} processed IDs in batch")

        except Exception as e:
            logger.error(f"Error saving processed IDs batch: {e}")

    def is_processed(self, url: str, processed_set: Set[str] = None) -> bool:
        """
        Check if an article URL has been processed.

        Args:
            url: Article URL to check
            processed_set: Optional pre-loaded set of processed IDs for efficiency

        Returns:
            True if URL was already processed
        """
        if processed_set is None:
            processed_set = self.load_processed_ids()

        return url in processed_set

    def get_new_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Filter out articles that have already been processed.

        Args:
            articles: List of article dictionaries

        Returns:
            List of articles that haven't been processed yet
        """
        processed_ids = self.load_processed_ids()

        new_articles = [
            article for article in articles
            if article['url'] not in processed_ids
        ]

        filtered_count = len(articles) - len(new_articles)
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} already-processed articles")

        logger.info(f"Found {len(new_articles)} new articles to process")

        return new_articles

    def cache_articles(self, articles: List[Dict], cache_date: date = None):
        """
        Save raw articles to a JSON cache file for debugging/replay.

        Args:
            articles: List of article dictionaries
            cache_date: Date for the cache file (default: today)
        """
        if cache_date is None:
            cache_date = date.today()

        cache_file = self.cache_dir / f"raw_{cache_date.isoformat()}.json"

        try:
            # Convert datetime objects to strings for JSON serialization
            articles_json = []
            for article in articles:
                article_copy = article.copy()
                if article_copy.get('published'):
                    article_copy['published'] = article_copy['published'].isoformat()
                articles_json.append(article_copy)

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(articles_json, f, indent=2, ensure_ascii=False)

            logger.info(f"Cached {len(articles)} articles to {cache_file}")

        except Exception as e:
            logger.error(f"Error caching articles: {e}")

    def load_cached_articles(self, cache_date: date = None) -> List[Dict]:
        """
        Load articles from a JSON cache file.

        Args:
            cache_date: Date of the cache file (default: today)

        Returns:
            List of article dictionaries
        """
        if cache_date is None:
            cache_date = date.today()

        cache_file = self.cache_dir / f"raw_{cache_date.isoformat()}.json"

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)

            # Convert ISO date strings back to datetime objects
            for article in articles:
                if article.get('published'):
                    article['published'] = datetime.fromisoformat(article['published'])

            logger.info(f"Loaded {len(articles)} articles from cache {cache_file}")

            return articles

        except FileNotFoundError:
            logger.warning(f"Cache file not found: {cache_file}")
            return []
        except Exception as e:
            logger.error(f"Error loading cached articles: {e}")
            return []

    def cache_extraction_results(self, results: List[Dict], cache_date: date = None):
        """
        Save AI extraction results to a JSON cache file.

        Args:
            results: List of extraction result dictionaries
            cache_date: Date for the cache file (default: today)
        """
        if cache_date is None:
            cache_date = date.today()

        cache_file = self.cache_dir / f"extraction_results_{cache_date.isoformat()}.json"

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"Cached {len(results)} extraction results to {cache_file}")

        except Exception as e:
            logger.error(f"Error caching extraction results: {e}")

    def cleanup_old_cache(self, days: int = 30):
        """
        Remove cache files older than N days.

        Args:
            days: Number of days to keep cache files
        """
        try:
            cutoff_date = date.today() - timedelta(days=days)

            for cache_file in self.cache_dir.glob("raw_*.json"):
                try:
                    # Extract date from filename: raw_2026-02-04.json
                    date_str = cache_file.stem.replace('raw_', '')
                    file_date = date.fromisoformat(date_str)

                    if file_date < cutoff_date:
                        cache_file.unlink()
                        logger.info(f"Deleted old cache file: {cache_file}")

                except Exception as e:
                    logger.warning(f"Error processing cache file {cache_file}: {e}")

            for cache_file in self.cache_dir.glob("extraction_results_*.json"):
                try:
                    date_str = cache_file.stem.replace('extraction_results_', '')
                    file_date = date.fromisoformat(date_str)

                    if file_date < cutoff_date:
                        cache_file.unlink()
                        logger.info(f"Deleted old extraction results: {cache_file}")

                except Exception as e:
                    logger.warning(f"Error processing cache file {cache_file}: {e}")

        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")


# For testing
if __name__ == '__main__':
    from datetime import timedelta

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    cache = CacheManager()

    # Test saving and loading processed IDs
    test_url = "https://example.com/test-article"
    print(f"Is processed before: {cache.is_processed(test_url)}")

    cache.save_processed_id(test_url)
    print(f"Is processed after: {cache.is_processed(test_url)}")

    # Test article caching
    test_articles = [
        {
            'source_key': 'test',
            'source_name': 'Test Source',
            'url': 'https://example.com/article1',
            'title': 'Test Article 1',
            'published': datetime.now(),
            'summary': 'This is a test article'
        }
    ]

    cache.cache_articles(test_articles)
    loaded = cache.load_cached_articles()
    print(f"Cached and loaded {len(loaded)} articles")

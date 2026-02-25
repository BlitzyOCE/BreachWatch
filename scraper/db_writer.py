"""
Database writer module for Supabase integration.

Handles writing breach data, updates, tags, and sources to the database.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from supabase import create_client, Client
import uuid

from config import SUPABASE_URL, SUPABASE_KEY, MAX_EXISTING_BREACHES_FETCH

logger = logging.getLogger(__name__)


class DatabaseWriter:
    """Handles writing breach data to Supabase database."""

    def __init__(self):
        """Initialize Supabase client."""
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Initialized DatabaseWriter with Supabase")

    def get_existing_breaches(self, days: int = 90) -> List[Dict]:
        """
        Fetch recent breaches from database for update detection.

        Args:
            days: Number of days to look back

        Returns:
            List of breach dictionaries
        """
        try:
            # Calculate cutoff date in Python (Supabase REST API can't interpret PostgreSQL functions)
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            # Query breaches from last N days
            response = (
                self.client
                .from_('breaches')
                .select('id, company, industry, country, discovery_date, records_affected, attack_vector, summary, created_at')
                .gte('created_at', cutoff_date)
                .order('created_at', desc=True)
                .limit(MAX_EXISTING_BREACHES_FETCH)
                .execute()
            )

            breaches = response.data if response.data else []
            logger.info(f"Fetched {len(breaches)} existing breaches from last {days} days")

            return breaches

        except Exception as e:
            logger.error(f"Error fetching existing breaches: {e}")
            return []

    def get_all_breach_stubs(self) -> List[Dict]:
        """
        Fetch id + company for ALL breaches in the database (no date filter).

        Intentionally lightweight - only the two fields needed for fuzzy
        company-name pre-filtering. Full details for matched candidates are
        fetched separately via get_breaches_by_ids().

        Returns:
            List of dicts with id and company only.
        """
        all_stubs = []
        page_size = 1000
        offset = 0

        try:
            while True:
                response = (
                    self.client
                    .from_('breaches')
                    .select('id, company')
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                batch = response.data or []
                all_stubs.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size

            logger.info(f"Fetched {len(all_stubs)} breach stubs for dedup pre-filter")
            return all_stubs

        except Exception as e:
            logger.error(f"Error fetching breach stubs: {e}")
            return []

    def get_breaches_by_ids(self, ids: List[str]) -> List[Dict]:
        """
        Fetch full dedup context fields for a specific list of breach IDs.

        Called after fuzzy pre-filtering to retrieve only the matched
        candidates before passing them to the AI update detection prompt.

        Returns:
            List of breach dicts with id, company, discovery_date,
            records_affected, attack_vector, summary.
        """
        if not ids:
            return []

        try:
            response = (
                self.client
                .from_('breaches')
                .select('id, company, discovery_date, records_affected, attack_vector, summary')
                .in_('id', ids)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.error(f"Error fetching breaches by ids: {e}")
            return []

    def write_new_breach(self, breach_data: Dict, article: Dict) -> Optional[str]:
        """
        Write a new breach to the database.

        Creates records in:
        - breaches table
        - breach_tags table
        - sources table

        Args:
            breach_data: Extracted breach data from AI
            article: Source article information

        Returns:
            Breach ID (UUID) if successful, None otherwise
        """
        try:
            # Prepare breach record
            breach_record = {
                'company': breach_data.get('company'),
                'title': breach_data.get('title'),
                'industry': breach_data.get('industry'),
                'country': breach_data.get('country'),
                'continent': breach_data.get('continent'),
                'discovery_date': breach_data.get('discovery_date'),
                'disclosure_date': breach_data.get('disclosure_date'),
                'records_affected': breach_data.get('records_affected'),
                'breach_method': breach_data.get('breach_method'),
                'attack_vector': breach_data.get('attack_vector'),
                'threat_actor': breach_data.get('threat_actor'),
                'data_compromised': breach_data.get('data_compromised', []),
                'severity': breach_data.get('severity'),
                'cve_references': breach_data.get('cve_references', []),
                'mitre_techniques': breach_data.get('mitre_attack_techniques', []),
                'summary': breach_data.get('summary'),
                'lessons_learned': breach_data.get('lessons_learned'),
            }

            # Remove None values
            breach_record = {k: v for k, v in breach_record.items() if v is not None}

            # Insert breach
            response = (
                self.client
                .from_('breaches')
                .insert(breach_record)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.error(f"Failed to insert breach: {response}")
                return None

            breach_id = response.data[0]['id']
            logger.info(f"Created new breach: {breach_id} - {breach_data.get('company', 'Unknown')}")

            # Write tags
            self._write_tags(breach_id, breach_data)

            # Write source
            self._write_source(breach_id, article)

            return breach_id

        except Exception as e:
            logger.error(f"Error writing new breach: {e}")
            logger.exception(e)
            return None

    def write_breach_update(
        self,
        update_data: Dict,
        breach_id: str,
        article: Dict,
        update_type: str = 'new_info',
        confidence: float = 0.8,
        content: Optional[str] = None,
    ) -> Optional[str]:
        """
        Write an update to an existing breach.

        Creates records in:
        - breach_updates table
        - sources table
        - Updates breaches.updated_at

        Args:
            update_data: Extracted update data from AI
            breach_id: UUID of the related breach
            article: Source article information
            update_type: Type of update (new_info, class_action, fine, etc.)
            confidence: Confidence score for this update

        Returns:
            Update ID (UUID) if successful, None otherwise
        """
        try:
            # Prepare update record
            update_record = {
                'breach_id': breach_id,
                'update_date': date.today().isoformat(),
                'update_type': update_type,
                'description': content or article.get('title', 'Update'),
                'source_url': article['url'],
                'extracted_data': update_data,
                'confidence_score': confidence,
                'ai_reasoning': f"Matched to existing breach with {confidence:.2%} confidence"
            }

            # Insert update
            response = (
                self.client
                .from_('breach_updates')
                .insert(update_record)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                logger.error(f"Failed to insert breach update: {response}")
                return None

            update_id = response.data[0]['id']
            logger.info(f"Created breach update: {update_id} for breach {breach_id}")

            # Update the breach's updated_at timestamp
            self.client.from_('breaches').update({
                'updated_at': datetime.now().isoformat()
            }).eq('id', breach_id).execute()

            # Write source (linked to original breach)
            self._write_source(breach_id, article)

            return update_id

        except Exception as e:
            logger.error(f"Error writing breach update: {e}")
            logger.exception(e)
            return None

    def _write_tags(self, breach_id: str, breach_data: Dict):
        """
        Write tags for a breach.

        Args:
            breach_id: UUID of the breach
            breach_data: Extracted breach data containing tag information
        """
        tags_to_insert = []

        # Continent tag
        if breach_data.get('continent'):
            tags_to_insert.append({
                'breach_id': breach_id,
                'tag_type': 'continent',
                'tag_value': breach_data['continent']
            })

        # Country tag
        if breach_data.get('country'):
            tags_to_insert.append({
                'breach_id': breach_id,
                'tag_type': 'country',
                'tag_value': breach_data['country']
            })

        # Industry tag
        if breach_data.get('industry'):
            tags_to_insert.append({
                'breach_id': breach_id,
                'tag_type': 'industry',
                'tag_value': breach_data['industry']
            })

        # Attack vector tag
        if breach_data.get('attack_vector'):
            tags_to_insert.append({
                'breach_id': breach_id,
                'tag_type': 'attack_vector',
                'tag_value': breach_data['attack_vector']
            })

        # Threat actor tag
        if breach_data.get('threat_actor'):
            tags_to_insert.append({
                'breach_id': breach_id,
                'tag_type': 'threat_actor',
                'tag_value': breach_data['threat_actor']
            })

        # CVE tags
        for cve in breach_data.get('cve_references', []):
            tags_to_insert.append({
                'breach_id': breach_id,
                'tag_type': 'cve',
                'tag_value': cve
            })

        # MITRE ATT&CK tags
        for technique in breach_data.get('mitre_attack_techniques', []):
            tags_to_insert.append({
                'breach_id': breach_id,
                'tag_type': 'mitre_attack',
                'tag_value': technique
            })

        # Insert all tags
        if tags_to_insert:
            try:
                response = (
                    self.client
                    .from_('breach_tags')
                    .insert(tags_to_insert)
                    .execute()
                )
                logger.info(f"Inserted {len(tags_to_insert)} tags for breach {breach_id}")
            except Exception as e:
                logger.error(f"Error inserting tags: {e}")

    def _write_source(self, breach_id: str, article: Dict):
        """
        Write source article information.

        Args:
            breach_id: UUID of the breach
            article: Article information
        """
        try:
            source_record = {
                'breach_id': breach_id,
                'url': article['url'],
                'title': article.get('title'),
                'published_date': article.get('published').date().isoformat() if article.get('published') else None
            }

            # Check if source URL already exists (avoid duplicates)
            existing = (
                self.client
                .from_('sources')
                .select('id')
                .eq('url', article['url'])
                .execute()
            )

            if existing.data and len(existing.data) > 0:
                logger.info(f"Source URL already exists: {article['url']}")
                return

            response = (
                self.client
                .from_('sources')
                .insert(source_record)
                .execute()
            )

            logger.info(f"Inserted source for breach {breach_id}: {article['url']}")

        except Exception as e:
            # Don't fail the whole operation if source insert fails (URL might be duplicate)
            logger.warning(f"Error inserting source (might be duplicate): {e}")

    def check_duplicate_by_url(self, url: str) -> Optional[str]:
        """
        Check if an article URL already exists as a source.

        Args:
            url: Article URL

        Returns:
            Breach ID if URL exists, None otherwise
        """
        try:
            response = (
                self.client
                .from_('sources')
                .select('breach_id')
                .eq('url', url)
                .execute()
            )

            if response.data and len(response.data) > 0:
                breach_id = response.data[0]['breach_id']
                logger.info(f"URL {url} already processed as part of breach {breach_id}")
                return breach_id

            return None

        except Exception as e:
            logger.error(f"Error checking duplicate URL: {e}")
            return None

    def find_breach_by_company(self, company_name: str, days: int = 90) -> Optional[Dict]:
        """
        Find a breach by company name (fuzzy match).

        Args:
            company_name: Company name to search for
            days: Number of days to look back

        Returns:
            Breach dict if found, None otherwise
        """
        try:
            # Calculate cutoff date in Python (Supabase REST API can't interpret PostgreSQL functions)
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            response = (
                self.client
                .from_('breaches')
                .select('*')
                .ilike('company', f'%{company_name}%')
                .gte('created_at', cutoff_date)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error finding breach by company: {e}")
            return None


# For testing
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        db = DatabaseWriter()

        # Test fetching existing breaches
        print("\n=== Testing Get Existing Breaches ===")
        breaches = db.get_existing_breaches(days=90)
        print(f"Found {len(breaches)} existing breaches")
        if breaches:
            print(f"Sample: {breaches[0]}")

    except ValueError as e:
        print(f"Error: {e}")
        print("Please set SUPABASE_URL and SUPABASE_KEY in your .env file")

"""
AI processing module using DeepSeek API.

Handles data extraction from articles and update detection.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any
from openai import OpenAI
import backoff

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT,
    DEEPSEEK_MAX_TOKENS,
    EXTRACTION_PROMPT,
    UPDATE_DETECTION_PROMPT,
    MAX_RETRIES
)

logger = logging.getLogger(__name__)


class AIProcessor:
    """Handles AI-powered data extraction and update detection using DeepSeek."""

    def __init__(self):
        """Initialize DeepSeek client."""
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY not set in environment variables")

        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            timeout=DEEPSEEK_TIMEOUT
        )

        self.model = DEEPSEEK_MODEL
        logger.info(f"Initialized AIProcessor with model: {self.model}")

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=MAX_RETRIES,
        giveup=lambda e: isinstance(e, ValueError)  # Don't retry on validation errors
    )
    def call_api(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        """
        Call DeepSeek API with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (lower = more deterministic)

        Returns:
            API response content as string

        Raises:
            Exception: If API call fails after retries
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=DEEPSEEK_MAX_TOKENS
            )

            content = response.choices[0].message.content
            logger.debug(f"API call successful, response length: {len(content)}")

            return content

        except Exception as e:
            logger.error(f"DeepSeek API call failed: {e}")
            raise

    def extract_json_from_response(self, response: str) -> Optional[Dict]:
        """
        Extract and parse JSON from API response.

        Handles cases where API returns markdown code blocks or extra text.

        Args:
            response: API response string

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Try to find JSON in code blocks first
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find standalone JSON object
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {e}")
            logger.debug(f"Response content: {response[:500]}")
            return None

    def extract_breach_data(self, article: Dict) -> Optional[Dict]:
        """
        Extract structured breach data from an article using AI.

        Args:
            article: Article dict with 'title', 'url', 'summary'

        Returns:
            Extracted breach data dict or None if extraction fails
        """
        logger.info(f"Extracting breach data from: {article['title'][:80]}...")

        # Format the extraction prompt
        prompt = EXTRACTION_PROMPT.format(
            title=article['title'],
            url=article['url'],
            summary=article['summary']
        )

        messages = [
            {
                "role": "system",
                "content": "You are a cybersecurity analyst expert at extracting structured data from breach news articles. Always respond with valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            response = self.call_api(messages, temperature=0.1)
            extracted_data = self.extract_json_from_response(response)

            if not extracted_data:
                logger.error(f"Failed to extract JSON from article: {article['url']}")
                return None

            # Validate required fields
            if not self.validate_extraction(extracted_data):
                logger.error(f"Extraction validation failed for: {article['url']}")
                return None

            # Add metadata
            extracted_data['_source_url'] = article['url']
            extracted_data['_source_name'] = article['source_name']
            extracted_data['_source_key'] = article['source_key']
            extracted_data['_article_title'] = article['title']
            extracted_data['_extracted_at'] = time.strftime('%Y-%m-%d %H:%M:%S')

            logger.info(f"Successfully extracted breach data: {extracted_data.get('company', 'Unknown')}")

            return extracted_data

        except Exception as e:
            logger.error(f"Error extracting breach data from {article['url']}: {e}")
            return None

    def validate_extraction(self, data: Dict) -> bool:
        """
        Validate extracted breach data has required fields and valid values.

        Args:
            data: Extracted data dictionary

        Returns:
            True if validation passes
        """
        # Check for summary (required)
        if not data.get('summary'):
            logger.warning("Extraction missing required field: summary")
            return False

        # Validate attack_vector if present
        valid_attack_vectors = [
            'phishing', 'ransomware', 'api_exploit', 'insider',
            'supply_chain', 'misconfiguration', 'malware', 'ddos', 'other'
        ]
        if data.get('attack_vector') and data['attack_vector'] not in valid_attack_vectors:
            logger.warning(f"Invalid attack_vector: {data['attack_vector']}")
            # Don't fail validation, just set to null
            data['attack_vector'] = None

        # Validate severity if present
        valid_severities = ['low', 'medium', 'high', 'critical']
        if data.get('severity') and data['severity'] not in valid_severities:
            logger.warning(f"Invalid severity: {data['severity']}")
            data['severity'] = None

        # Ensure arrays are lists
        if data.get('data_compromised') and not isinstance(data['data_compromised'], list):
            data['data_compromised'] = []

        if data.get('cve_references') and not isinstance(data['cve_references'], list):
            data['cve_references'] = []

        if data.get('mitre_attack_techniques') and not isinstance(data['mitre_attack_techniques'], list):
            data['mitre_attack_techniques'] = []

        return True

    def detect_update(self, article: Dict, existing_breaches: List[Dict]) -> Optional[Dict]:
        """
        Determine if article is a NEW breach or UPDATE to existing breach.

        Args:
            article: Article dict with 'title', 'url', 'summary'
            existing_breaches: List of existing breach dicts from database

        Returns:
            Update detection result dict or None if detection fails
        """
        logger.info(f"Detecting if update: {article['title'][:80]}...")

        # Format existing breaches for prompt
        breaches_list = []
        for breach in existing_breaches[:50]:  # Limit to 50 most recent to avoid token limits
            breach_summary = (
                f"- ID: {breach.get('id')}\n"
                f"  Company: {breach.get('company', 'Unknown')}\n"
                f"  Discovery Date: {breach.get('discovery_date', 'Unknown')}\n"
                f"  Summary: {breach.get('summary', '')[:150]}\n"
            )
            breaches_list.append(breach_summary)

        existing_breaches_str = '\n'.join(breaches_list) if breaches_list else "No existing breaches in database."

        # Format the update detection prompt
        prompt = UPDATE_DETECTION_PROMPT.format(
            title=article['title'],
            url=article['url'],
            summary=article['summary'],
            existing_breaches=existing_breaches_str
        )

        messages = [
            {
                "role": "system",
                "content": "You are a cybersecurity analyst expert at identifying whether news articles are about new breaches or updates to existing incidents. Always respond with valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            response = self.call_api(messages, temperature=0.2)
            update_data = self.extract_json_from_response(response)

            if not update_data:
                logger.error(f"Failed to extract JSON from update detection: {article['url']}")
                # Default to treating as new breach
                return {
                    'is_update': False,
                    'related_breach_id': None,
                    'update_type': None,
                    'confidence': 0.5,
                    'reasoning': 'Failed to parse AI response, defaulting to new breach'
                }

            logger.info(f"Update detection result: is_update={update_data.get('is_update')}, "
                       f"confidence={update_data.get('confidence')}")

            return update_data

        except Exception as e:
            logger.error(f"Error detecting update for {article['url']}: {e}")
            # Default to treating as new breach on error
            return {
                'is_update': False,
                'related_breach_id': None,
                'update_type': None,
                'confidence': 0.0,
                'reasoning': f'Error during detection: {str(e)}'
            }


# For testing
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test article
    test_article = {
        'source_key': 'test',
        'source_name': 'Test Source',
        'url': 'https://example.com/test',
        'title': 'Major Healthcare Provider Suffers Ransomware Attack',
        'summary': 'A major healthcare provider announced today that it suffered a ransomware attack affecting patient records. The breach impacted approximately 2 million patient records including names, addresses, and medical histories. The attack occurred last month and was discovered during routine security monitoring.'
    }

    try:
        processor = AIProcessor()

        print("\n=== Testing Breach Data Extraction ===")
        extracted = processor.extract_breach_data(test_article)
        if extracted:
            print(json.dumps(extracted, indent=2))

        print("\n=== Testing Update Detection ===")
        # Test with empty existing breaches
        update_result = processor.detect_update(test_article, [])
        if update_result:
            print(json.dumps(update_result, indent=2))

    except ValueError as e:
        print(f"Error: {e}")
        print("Please set DEEPSEEK_API_KEY in your .env file")

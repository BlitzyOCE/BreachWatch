"""
Database audit tool for BreachWatch.

Provides data quality checks, duplicate detection, and export capabilities.

Usage:
    python audit.py              # Full audit report
    python audit.py --csv        # Export to CSV
    python audit.py --duplicates # Show potential duplicates only
"""

import argparse
import csv
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional

from db_writer import DatabaseWriter

logging.basicConfig(level=logging.WARNING)


class DatabaseAuditor:
    """Audits breach database for quality issues."""

    REQUIRED_FIELDS = ['company', 'industry', 'country', 'severity', 'summary']
    IMPORTANT_FIELDS = ['discovery_date', 'disclosure_date', 'records_affected', 'attack_vector', 'breach_method']

    def __init__(self):
        self.db = DatabaseWriter()
        self.breaches = []
        self.sources = []
        self.tags = []
        self.updates = []

    def fetch_all_data(self):
        """Fetch all data from database."""
        print("Fetching data from Supabase...")

        self.breaches = (
            self.db.client.from_('breaches')
            .select('*')
            .order('created_at', desc=True)
            .execute()
        ).data or []

        self.sources = (
            self.db.client.from_('sources')
            .select('*')
            .order('created_at', desc=True)
            .execute()
        ).data or []

        self.tags = (
            self.db.client.from_('breach_tags')
            .select('*')
            .execute()
        ).data or []

        self.updates = (
            self.db.client.from_('breach_updates')
            .select('*')
            .execute()
        ).data or []

        print(f"  Breaches: {len(self.breaches)}")
        print(f"  Sources: {len(self.sources)}")
        print(f"  Tags: {len(self.tags)}")
        print(f"  Updates: {len(self.updates)}")

    def find_duplicates(self) -> List[Dict]:
        """Find potential duplicate breaches (same company within 7 days)."""
        duplicates = []
        by_company = defaultdict(list)

        for breach in self.breaches:
            company = (breach.get('company') or '').lower().strip()
            if company:
                by_company[company].append(breach)

        for company, entries in by_company.items():
            if len(entries) > 1:
                duplicates.append({
                    'company': company,
                    'count': len(entries),
                    'breaches': entries
                })

        return duplicates

    def analyze_missing_fields(self) -> Dict:
        """Analyze missing field statistics."""
        stats = {
            'required': defaultdict(int),
            'important': defaultdict(int),
            'total': len(self.breaches)
        }

        for breach in self.breaches:
            for field in self.REQUIRED_FIELDS:
                if not breach.get(field):
                    stats['required'][field] += 1

            for field in self.IMPORTANT_FIELDS:
                if not breach.get(field):
                    stats['important'][field] += 1

        return stats

    def print_breaches_table(self):
        """Print all breaches in a table format."""
        print("\n" + "=" * 100)
        print("BREACHES")
        print("=" * 100)

        for i, b in enumerate(self.breaches, 1):
            created = b.get('created_at', '')[:19] if b.get('created_at') else 'N/A'
            company = b.get('company') or 'Unknown'
            title = b.get('title') or ''
            industry = b.get('industry') or '-'
            country = b.get('country') or '-'
            severity = b.get('severity') or '-'
            records = b.get('records_affected')
            records_str = f"{records:,}" if records else '-'
            attack = b.get('attack_vector') or '-'

            print(f"\n[{i}] {company}")
            if title:
                print(f"    Title: {title}")
            print(f"    ID: {b['id']}")
            print(f"    Industry: {industry} | Country: {country} | Severity: {severity}")
            print(f"    Records: {records_str} | Attack: {attack}")
            print(f"    Created: {created}")

            # Show summary (truncated)
            summary = b.get('summary') or 'N/A'
            print(f"    Summary: {summary[:150]}{'...' if len(summary) > 150 else ''}")

            # Show data compromised
            data = b.get('data_compromised') or []
            if data:
                print(f"    Data Compromised: {', '.join(data[:5])}{'...' if len(data) > 5 else ''}")

    def print_duplicates_report(self):
        """Print potential duplicates."""
        duplicates = self.find_duplicates()

        print("\n" + "=" * 100)
        print("POTENTIAL DUPLICATES")
        print("=" * 100)

        if not duplicates:
            print("\nNo potential duplicates found.")
            return

        for dup in duplicates:
            print(f"\n[!] {dup['company'].title()} - {dup['count']} entries")
            for breach in dup['breaches']:
                created = breach.get('created_at', '')[:19]
                source_url = self._get_source_url(breach['id'])
                print(f"    - ID: {breach['id'][:8]}... | Created: {created}")
                print(f"      Source: {source_url[:70]}..." if source_url else "      Source: N/A")

    def _get_source_url(self, breach_id: str) -> Optional[str]:
        """Get source URL for a breach."""
        for source in self.sources:
            if source.get('breach_id') == breach_id:
                return source.get('url')
        return None

    def print_missing_fields_report(self):
        """Print missing field statistics."""
        stats = self.analyze_missing_fields()
        total = stats['total']

        print("\n" + "=" * 100)
        print("MISSING FIELD ANALYSIS")
        print("=" * 100)

        if total == 0:
            print("\nNo breaches to analyze.")
            return

        print(f"\nTotal breaches: {total}")

        print("\nRequired Fields (should always be populated):")
        for field in self.REQUIRED_FIELDS:
            missing = stats['required'][field]
            pct = (missing / total) * 100 if total else 0
            status = "OK" if missing == 0 else "MISSING"
            print(f"  {field:20} {missing:3}/{total} missing ({pct:5.1f}%) [{status}]")

        print("\nImportant Fields (nice to have):")
        for field in self.IMPORTANT_FIELDS:
            missing = stats['important'][field]
            pct = (missing / total) * 100 if total else 0
            print(f"  {field:20} {missing:3}/{total} missing ({pct:5.1f}%)")

    def print_sources_report(self):
        """Print sources summary."""
        print("\n" + "=" * 100)
        print("SOURCES")
        print("=" * 100)

        # Group by domain
        by_domain = defaultdict(int)
        for source in self.sources:
            url = source.get('url', '')
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                by_domain[domain] += 1
            except:
                by_domain['unknown'] += 1

        print(f"\nTotal sources: {len(self.sources)}")
        print("\nBy domain:")
        for domain, count in sorted(by_domain.items(), key=lambda x: -x[1]):
            print(f"  {domain:40} {count:3} articles")

    def print_updates_report(self):
        """Print updates summary."""
        print("\n" + "=" * 100)
        print("BREACH UPDATES")
        print("=" * 100)

        print(f"\nTotal updates: {len(self.updates)}")

        if self.updates:
            by_type = defaultdict(int)
            for update in self.updates:
                by_type[update.get('update_type', 'unknown')] += 1

            print("\nBy type:")
            for utype, count in sorted(by_type.items(), key=lambda x: -x[1]):
                print(f"  {utype:20} {count:3}")

    def export_to_csv(self, output_dir: Path = None):
        """Export all data to CSV files."""
        output_dir = output_dir or Path('audit_export')
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Export breaches
        breaches_file = output_dir / f'breaches_{timestamp}.csv'
        with open(breaches_file, 'w', newline='', encoding='utf-8') as f:
            if self.breaches:
                writer = csv.DictWriter(f, fieldnames=self.breaches[0].keys())
                writer.writeheader()
                writer.writerows(self.breaches)
        print(f"Exported breaches to: {breaches_file}")

        # Export sources
        sources_file = output_dir / f'sources_{timestamp}.csv'
        with open(sources_file, 'w', newline='', encoding='utf-8') as f:
            if self.sources:
                writer = csv.DictWriter(f, fieldnames=self.sources[0].keys())
                writer.writeheader()
                writer.writerows(self.sources)
        print(f"Exported sources to: {sources_file}")

        # Export duplicates report
        duplicates = self.find_duplicates()
        duplicates_file = output_dir / f'duplicates_{timestamp}.csv'
        with open(duplicates_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['company', 'breach_id', 'created_at', 'source_url', 'summary'])
            for dup in duplicates:
                for breach in dup['breaches']:
                    writer.writerow([
                        dup['company'],
                        breach['id'],
                        breach.get('created_at'),
                        self._get_source_url(breach['id']),
                        (breach.get('summary') or '')[:200]
                    ])
        print(f"Exported duplicates to: {duplicates_file}")

    def run_full_audit(self):
        """Run complete audit."""
        self.fetch_all_data()
        self.print_breaches_table()
        self.print_duplicates_report()
        self.print_missing_fields_report()
        self.print_sources_report()
        self.print_updates_report()

        # Summary
        duplicates = self.find_duplicates()
        missing = self.analyze_missing_fields()

        print("\n" + "=" * 100)
        print("AUDIT SUMMARY")
        print("=" * 100)
        print(f"\nTotal breaches: {len(self.breaches)}")
        print(f"Potential duplicates: {len(duplicates)} companies with multiple entries")
        print(f"Breaches missing 'country': {missing['required']['country']}/{missing['total']}")
        print(f"Breaches missing 'discovery_date': {missing['important']['discovery_date']}/{missing['total']}")
        print(f"Breaches missing 'disclosure_date': {missing['important']['disclosure_date']}/{missing['total']}")
        print(f"Total updates recorded: {len(self.updates)}")


def main():
    parser = argparse.ArgumentParser(description='Audit BreachWatch database')
    parser.add_argument('--csv', action='store_true', help='Export data to CSV files')
    parser.add_argument('--duplicates', action='store_true', help='Show only potential duplicates')
    args = parser.parse_args()

    auditor = DatabaseAuditor()
    auditor.fetch_all_data()

    if args.csv:
        auditor.export_to_csv()
    elif args.duplicates:
        auditor.print_duplicates_report()
    else:
        auditor.run_full_audit()


if __name__ == '__main__':
    main()

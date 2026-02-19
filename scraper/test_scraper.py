"""
Comprehensive scraper test workflow.

Runs the full scraper pipeline and generates a quality report.

Usage:
    python test_scraper.py           # Full test (scraper + audit)
    python test_scraper.py --audit   # Audit only (skip scraper run)
    python test_scraper.py --clear   # Clear cache and run fresh
"""

import argparse
import io
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows terminals (avoids GBK encode errors from
# replacement characters produced by errors='replace' in subprocess decoding)
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Paths
SCRAPER_DIR = Path(__file__).parent
VENV_PYTHON = SCRAPER_DIR / "venv" / "Scripts" / "python.exe"
MAIN_PY = SCRAPER_DIR / "main.py"
AUDIT_PY = SCRAPER_DIR / "audit.py"
LOGS_DIR = SCRAPER_DIR / "logs"
CACHE_DIR = SCRAPER_DIR / "cache"


def run_command(cmd, description):
    """Run a command and return output."""
    print(f"\n{'='*60}")
    print(f">> {description}")
    print('='*60)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=1200
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            # Filter out Unicode encoding errors from Windows console
            stderr_lines = [
                line for line in result.stderr.split('\n')
                if 'UnicodeEncodeError' not in line and 'gbk' not in line
            ]
            if stderr_lines:
                print('\n'.join(stderr_lines))

        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out after 20 minutes")
        return False, "", "Timeout"
    except Exception as e:
        print(f"ERROR: {e}")
        return False, "", str(e)


def clear_cache():
    """Clear processed URLs cache to allow re-processing."""
    processed_file = CACHE_DIR / "processed_ids.txt"
    if processed_file.exists():
        processed_file.write_text("")
        print("Cleared processed_ids.txt")
    else:
        print("No cache to clear")


def read_latest_log():
    """Read and summarize the latest log file."""
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = LOGS_DIR / f"scraper_{today}.log"
    error_file = LOGS_DIR / f"errors_{today}.log"

    print(f"\n{'='*60}")
    print(">> Log Summary")
    print('='*60)

    if log_file.exists():
        content = log_file.read_text(encoding='utf-8', errors='replace')
        lines = content.strip().split('\n')

        # Find the last run's summary
        summary_start = None
        for i, line in enumerate(lines):
            if 'Scraper Completed' in line:
                summary_start = i

        if summary_start:
            # Print last run summary
            print("\nLatest Run Summary:")
            for line in lines[summary_start:]:
                if line.strip():
                    # Extract just the message part
                    if ' - INFO - ' in line:
                        msg = line.split(' - INFO - ')[-1]
                        print(f"  {msg}")
                    elif ' - ERROR - ' in line:
                        msg = line.split(' - ERROR - ')[-1]
                        print(f"  [ERROR] {msg}")
    else:
        print(f"No log file found for today ({today})")

    # Check for errors
    if error_file.exists():
        content = error_file.read_text(encoding='utf-8', errors='replace')
        # Get only today's errors (last run)
        lines = content.strip().split('\n')
        today_errors = [l for l in lines if today in l]

        if today_errors:
            print(f"\nErrors from today ({len(today_errors)} total):")
            # Show unique error types
            error_types = set()
            for line in today_errors:
                if 'ERROR' in line:
                    # Extract error message
                    msg = line.split(' - ERROR - ')[-1] if ' - ERROR - ' in line else line
                    error_types.add(msg[:80])

            for err in list(error_types)[:5]:
                print(f"  - {err}")

            if len(error_types) > 5:
                print(f"  ... and {len(error_types) - 5} more unique errors")


def run_audit():
    """Run the audit tool."""
    success, stdout, stderr = run_command(
        [str(VENV_PYTHON), str(AUDIT_PY)],
        "Running Database Audit"
    )
    return success


def check_extraction_quality():
    """Check the latest extraction results."""
    print(f"\n{'='*60}")
    print(">> Extraction Quality Check")
    print('='*60)

    today = datetime.now().strftime('%Y-%m-%d')
    extraction_file = CACHE_DIR / f"extraction_results_{today}.json"

    if not extraction_file.exists():
        print("No extraction results found for today")
        return

    import json
    try:
        data = json.loads(extraction_file.read_text(encoding='utf-8'))

        if not data:
            print("No extractions performed")
            return

        print(f"\nExtractions: {len(data)}")

        # Check field coverage
        fields = ['country', 'discovery_date', 'disclosure_date', 'records_affected', 'severity', 'attack_vector']
        coverage = {f: 0 for f in fields}

        for item in data:
            extracted = item.get('extracted', {})
            for field in fields:
                if extracted.get(field) is not None:
                    coverage[field] += 1

        print("\nField Coverage:")
        for field, count in coverage.items():
            pct = (count / len(data)) * 100 if data else 0
            status = "OK" if pct >= 75 else "LOW" if pct >= 50 else "POOR"
            print(f"  {field:20} {count}/{len(data)} ({pct:5.1f}%) [{status}]")

        # Check update detection
        genuine_updates = sum(
            1 for d in data
            if d.get('update_check', {}).get('is_update')
            and not d.get('update_check', {}).get('is_duplicate_source')
        )
        duplicates_skipped = sum(1 for d in data if d.get('update_check', {}).get('is_duplicate_source'))
        new_breaches = len(data) - genuine_updates - duplicates_skipped
        print(f"\nUpdate Detection:")
        print(f"  New breaches: {new_breaches}")
        print(f"  Genuine updates: {genuine_updates}")
        print(f"  Duplicate sources skipped: {duplicates_skipped}")

    except json.JSONDecodeError as e:
        print(f"Error parsing extraction results: {e}")


def check_database_updates():
    """Check breach_updates table for new data quality."""
    print(f"\n{'='*60}")
    print(">> Database Updates Quality")
    print('='*60)

    try:
        sys.path.insert(0, str(SCRAPER_DIR))
        from dotenv import load_dotenv
        load_dotenv(SCRAPER_DIR / '.env')
        from db_writer import DatabaseWriter

        db = DatabaseWriter()

        # Get updates
        updates = db.client.from_('breach_updates').select('*').order('created_at', desc=True).limit(10).execute().data or []

        if not updates:
            print("No updates in database")
            return

        print(f"\nRecent Updates: {len(updates)}")

        # Check extracted_data quality in updates
        fields = ['country', 'discovery_date', 'records_affected', 'severity']
        for u in updates[:5]:
            extracted = u.get('extracted_data', {})
            breach_id = u.get('breach_id', '')[:8]
            filled = sum(1 for f in fields if extracted.get(f) is not None)
            print(f"  [{breach_id}...] {filled}/{len(fields)} fields | {u.get('update_type')}")

    except Exception as e:
        print(f"Error checking database: {e}")


def main():
    parser = argparse.ArgumentParser(description='Test BreachCase scraper')
    parser.add_argument('--audit', action='store_true', help='Run audit only (skip scraper)')
    parser.add_argument('--clear', action='store_true', help='Clear cache before running')
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  BREACHCASE SCRAPER TEST")
    print("  " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*60)

    if args.clear:
        clear_cache()

    if not args.audit:
        # Run the scraper
        success, _, _ = run_command(
            [str(VENV_PYTHON), str(MAIN_PY)],
            "Running Scraper (main.py)"
        )

        if not success:
            print("\nScraper encountered issues - check logs for details")

    # Read logs
    read_latest_log()

    # Check extraction quality
    check_extraction_quality()

    # Run audit
    run_audit()

    # Check database updates
    check_database_updates()

    print("\n" + "="*60)
    print("  TEST COMPLETE")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()

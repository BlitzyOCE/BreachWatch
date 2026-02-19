# Test Scraper

Run the complete BreachCase scraper test workflow.

## What This Does

1. **Run Scraper** - Execute `main.py` to fetch RSS feeds, classify articles, and extract breach data
2. **Check Logs** - Read and summarize today's scraper logs, highlighting any errors
3. **Run Audit** - Execute the database audit to check data quality
4. **Quality Report** - Show extraction field coverage and update detection stats

## Usage

```
/test-scraper           # Full test (scraper + audit)
/test-scraper --audit   # Audit only (skip running scraper)
/test-scraper --clear   # Clear cache first (re-process same articles)
```

## Instructions for Claude

When the user invokes this skill, run the test script:

```bash
cd d:\Eric\IT\code\BreachBase\scraper
venv\Scripts\python.exe test_scraper.py
```

If the user specifies `--audit`, add that flag:
```bash
venv\Scripts\python.exe test_scraper.py --audit
```

If the user specifies `--clear`, add that flag:
```bash
venv\Scripts\python.exe test_scraper.py --clear
```

After running, summarize the key findings:
- Number of articles processed
- Number of breaches created vs updates
- Any errors encountered
- Data quality metrics (field coverage percentages)
- Potential duplicates found

If there are issues, suggest fixes based on the error messages.

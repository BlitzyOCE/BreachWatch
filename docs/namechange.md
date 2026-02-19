# Name Change: BreachWatch -> BreachCase

All references to "BreachWatch" have been renamed to "BreachCase" across the project.

## Files Changed

### Root Documentation
- **CLAUDE.md** - Project description
- **README.md** - Project heading

### Database
- **database/DATABASE_DESIGN.md** - Title and overview text

### Docs
- **docs/PROGRESS.md** - Title and Supabase instance reference
- **docs/product.md** - Title, description text, and example GitHub URL (`breachwatch` -> `breachcase`)
- **docs/DATA_QUALITY_PLAN.md** - Two references in body text

### Frontend
- **frontend/app/layout.tsx** - Page title and title template metadata
- **frontend/app/about/page.tsx** - Meta description, heading, and two body paragraphs
- **frontend/components/layout/header.tsx** - Brand name in header nav
- **frontend/components/layout/footer.tsx** - Brand name in footer
- **frontend/components/layout/mobile-nav.tsx** - Brand name in mobile nav sheet
- **frontend/docs/BUILD_SUMMARY.md** - Title
- **frontend/docs/PLAN.md** - Title and context paragraph

### Scraper
- **scraper/config.py** - Module docstring
- **scraper/main.py** - Module docstring and startup log message
- **scraper/audit.py** - Module docstring and argparse description
- **scraper/test_scraper.py** - Argparse description and banner text (`BREACHWATCH` -> `BREACHCASE`)
- **scraper/README.md** - Title
- **scraper/requirements.txt** - Header comment

### Claude Commands
- **.claude/commands/start-dev.md** - Summary bullet point
- **.claude/commands/test-scraper.md** - Description text

## What Was NOT Changed
- Database table names, column names, and SQL schema (no "BreachWatch" references existed there)
- Environment variable names
- Package names or import paths
- Functional code logic or behavior
- File names and directory names

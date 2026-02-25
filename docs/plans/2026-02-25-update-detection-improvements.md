# Update Detection Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the scraper so that secondary sources re-reporting the same breach are correctly classified as `DUPLICATE_SOURCE`, and genuine update timeline entries store a short concise note rather than a full rehashed summary.

**Architecture:** Add a structured pre-check in `main.py` that computes field-level match signals (records count, attack vector) between the newly extracted article and each fuzzy-matched candidate. These signals are passed to `detect_update`, which annotates the candidates context string so the AI has explicit structural evidence. The `UPDATE_DETECTION_PROMPT` is strengthened with explicit rules for aggregators and data-type specificity. A new `update_summary` field in the AI response captures the 1–2 sentence "what changed" note, which is stored as the `breach_updates.description` instead of the full extracted summary.

**Tech Stack:** Python 3.13, DeepSeek API (OpenAI-compatible SDK), Supabase Python client. No test framework — verification is via the existing `test_scraper.py` and manual DB inspection.

---

### Task 1: Strengthen `UPDATE_DETECTION_PROMPT` in `config.py`

This is the highest-leverage change. Do it first so every subsequent test exercises the improved prompt.

**Files:**
- Modify: `scraper/config.py` (lines 185–220, the `UPDATE_DETECTION_PROMPT` string)

**Step 1: Read the current prompt**

Open `scraper/config.py` and locate `UPDATE_DETECTION_PROMPT` (~line 185). Read it in full before changing anything.

**Step 2: Replace `UPDATE_DETECTION_PROMPT` with the improved version**

Replace the entire string with:

```python
UPDATE_DETECTION_PROMPT = """You are a cybersecurity intelligence analyst. Classify this article into exactly one of three categories:

NEW_BREACH      - A breach incident not already in the database.
GENUINE_UPDATE  - An existing breach in the database, and this article adds meaningfully new information:
                  revised record count (>10% change), new legal or regulatory action, new CVE or root cause
                  identified, confirmation of previously unknown affected systems, or investigation findings.
DUPLICATE_SOURCE - An existing breach in the database, but this article adds no meaningfully new facts.
                  It re-reports the same incident from a different outlet with the same or very similar details.

Article Title: {title}
Article URL: {url}
Article Summary: {summary}

Candidate matching breaches from database (pre-filtered by company name similarity):
{existing_breaches}

Classification rules:
- Match on company name first. If the company does not appear in the list, classify as NEW_BREACH.
- Once a company match is found, compare structured fields using the candidate details and any
  structural signals provided.

DUPLICATE_SOURCE rules (all of these = duplicate):
- An aggregator source (Have I Been Pwned, data breach databases, breach notification services)
  listing the same incident with the same company and approximately the same record count.
- More specific enumeration of already-known data types (e.g. "email addresses, phone numbers"
  vs "personal information") — this is clarification, NOT new information.
- Same record count, same attack vector, no new legal/regulatory developments mentioned.

GENUINE_UPDATE rules (requires at least one of):
- Record count explicitly revised and differs by more than 10% from existing.
- New legal action: class action filed, regulatory investigation opened, GDPR/FTC fine issued.
- New technical detail: CVE identified, root cause confirmed, new affected systems named.
- New timeline fact: breach discovery date corrected, containment confirmed.

If structural signals show records and attack_vector already match, the bar for GENUINE_UPDATE
is very high. You must cite a specific new development from the article to justify it.

When in doubt between GENUINE_UPDATE and DUPLICATE_SOURCE, always prefer DUPLICATE_SOURCE.
When in doubt about whether the company matches at all, prefer NEW_BREACH over DUPLICATE_SOURCE.

Return JSON only:
{{
  "classification": "NEW_BREACH|GENUINE_UPDATE|DUPLICATE_SOURCE",
  "is_update": true if classification is GENUINE_UPDATE, false otherwise,
  "is_duplicate_source": true if classification is DUPLICATE_SOURCE, false otherwise,
  "related_breach_id": "UUID of the matching breach from the list above, or null if NEW_BREACH",
  "update_type": "One of: new_info|class_action|regulatory_fine|remediation|resolution|investigation|null",
  "update_summary": "1-2 sentence description of what specifically is new in this article (e.g. 'Record count revised from 5M to 8.2M after forensic investigation.' or 'FTC opened a formal investigation.'). Null if classification is DUPLICATE_SOURCE or NEW_BREACH.",
  "confidence": 0.0 to 1.0 confidence score,
  "reasoning": "One sentence explanation citing the specific signal that drove your classification"
}}
"""
```

**Step 3: Verify the file is valid Python**

```bash
cd scraper && python -c "import config; print('OK')"
```

Expected: `OK` with no errors.

**Step 4: Commit**

```bash
git add scraper/config.py
git commit -m "improve update detection prompt with explicit duplicate rules and update_summary field"
```

---

### Task 2: Add `_compute_match_signals()` to `main.py`

**Files:**
- Modify: `scraper/main.py`

**Step 1: Read `main.py` around the `_company_similarity` function (lines 37–60)**

Understand the existing helper pattern before adding the new one.

**Step 2: Add `_compute_match_signals` after `get_fuzzy_candidates`**

Insert the following function after `get_fuzzy_candidates` (~line 60), before `setup_logging`:

```python
def _compute_match_signals(extracted: dict, candidates: list) -> dict:
    """
    Compute structural match signals between extracted article data and each candidate breach.

    Returns a dict keyed by breach UUID with per-candidate signal dicts:
      {
        breach_id: {
            'records_match': bool | None,   # None if either value is missing
            'attack_vector_match': bool | None,
            'existing_records': int | None,
            'existing_attack_vector': str | None,
        }
      }
    """
    signals = {}
    extracted_records = extracted.get('records_affected')
    extracted_vector = extracted.get('attack_vector')

    for candidate in candidates:
        bid = candidate.get('id')
        if not bid:
            continue

        existing_records = candidate.get('records_affected')
        existing_vector = candidate.get('attack_vector')

        # Records match: both present and within 10% of each other
        records_match = None
        if extracted_records and existing_records:
            larger = max(extracted_records, existing_records)
            records_match = abs(extracted_records - existing_records) / larger <= 0.10

        # Attack vector match: both present and identical
        attack_vector_match = None
        if extracted_vector and existing_vector:
            attack_vector_match = extracted_vector == existing_vector

        signals[bid] = {
            'records_match': records_match,
            'attack_vector_match': attack_vector_match,
            'existing_records': existing_records,
            'existing_attack_vector': existing_vector,
        }

    return signals
```

**Step 3: Pass signals into `detect_update` at the call site**

Find the block starting with `candidate_details = db.get_breaches_by_ids(candidate_ids)` (~line 248). Replace it with:

```python
candidate_ids = [c['id'] for c in candidates]
candidate_details = db.get_breaches_by_ids(candidate_ids)
match_signals = _compute_match_signals(extracted, candidate_details)
update_check = ai_processor.detect_update(article, candidate_details, match_signals)
```

**Step 4: Pass `update_summary` to `write_breach_update` at the call site**

Find `db.write_breach_update(` (~line 275). Replace the call with:

```python
update_id = db.write_breach_update(
    extracted,
    update_check['related_breach_id'],
    article,
    update_type=update_check.get('update_type', 'new_info'),
    confidence=update_check['confidence'],
    content=update_check.get('update_summary'),
)
```

**Step 5: Verify the file is valid Python**

```bash
cd scraper && python -c "import main; print('OK')"
```

Expected: `OK`.

**Step 6: Commit**

```bash
git add scraper/main.py
git commit -m "compute structural match signals and pass update_summary to db writer"
```

---

### Task 3: Update `detect_update` in `ai_processor.py` to accept and use match signals

**Files:**
- Modify: `scraper/ai_processor.py` (lines 314–400, the `detect_update` method)

**Step 1: Read the current `detect_update` method (lines 314–400)**

Focus on how `breaches_list` is built (lines 328–340) — this is where signal annotations will be injected.

**Step 2: Update the method signature**

Change line 314 from:
```python
def detect_update(self, article: Dict, existing_breaches: List[Dict]) -> Optional[Dict]:
```
to:
```python
def detect_update(self, article: Dict, existing_breaches: List[Dict], match_signals: Optional[Dict] = None) -> Optional[Dict]:
```

**Step 3: Replace the `breaches_list` building block**

Find the loop that builds `breaches_list` (lines ~328–338). Replace it with:

```python
for breach in existing_breaches[:MAX_EXISTING_BREACHES_CONTEXT]:
    bid = breach.get('id')
    breach_summary = (
        f"- ID: {bid}\n"
        f"  Company: {breach.get('company', 'Unknown')}\n"
        f"  Discovery Date: {breach.get('discovery_date', 'Unknown')}\n"
        f"  Records Affected: {breach.get('records_affected', 'Unknown')}\n"
        f"  Attack Vector: {breach.get('attack_vector', 'Unknown')}\n"
        f"  Summary: {breach.get('summary', '')[:150]}\n"
    )

    # Append structural match signals if available for this candidate
    if match_signals and bid and bid in match_signals:
        sig = match_signals[bid]
        signal_parts = []

        if sig['records_match'] is True:
            signal_parts.append(
                f"records MATCH ({breach.get('records_affected')} ≈ extracted)"
            )
        elif sig['records_match'] is False:
            signal_parts.append(
                f"records DIFFER ({breach.get('records_affected')} vs extracted)"
            )

        if sig['attack_vector_match'] is True:
            signal_parts.append(f"attack_vector MATCH ({sig['existing_attack_vector']})")
        elif sig['attack_vector_match'] is False:
            signal_parts.append(
                f"attack_vector DIFFER ({sig['existing_attack_vector']} vs extracted)"
            )

        if signal_parts:
            breach_summary += f"  Structural signals: {', '.join(signal_parts)}\n"
            if sig['records_match'] is True and sig['attack_vector_match'] is True:
                breach_summary += (
                    "  → High prior for DUPLICATE_SOURCE — only classify as GENUINE_UPDATE "
                    "if you can cite a specific new development not in the existing summary.\n"
                )

    breaches_list.append(breach_summary)
```

**Step 4: Verify the file is valid Python**

```bash
cd scraper && python -c "import ai_processor; print('OK')"
```

Expected: `OK`.

**Step 5: Commit**

```bash
git add scraper/ai_processor.py
git commit -m "thread match signals into update detection candidates context"
```

---

### Task 4: Update `write_breach_update` in `db_writer.py` to accept concise content

**Files:**
- Modify: `scraper/db_writer.py` (lines 197–264, `write_breach_update`)

**Step 1: Read `write_breach_update` (lines 197–264)**

Note line 229: `'description': update_data.get('summary', article.get('title', 'Update'))` — this is what stores the 500-word rehash.

**Step 2: Add `content` parameter to the signature**

Change line 197–204 from:
```python
def write_breach_update(
    self,
    update_data: Dict,
    breach_id: str,
    article: Dict,
    update_type: str = 'new_info',
    confidence: float = 0.8
) -> Optional[str]:
```
to:
```python
def write_breach_update(
    self,
    update_data: Dict,
    breach_id: str,
    article: Dict,
    update_type: str = 'new_info',
    confidence: float = 0.8,
    content: Optional[str] = None,
) -> Optional[str]:
```

**Step 3: Use `content` for `description`**

Change line 229 from:
```python
'description': update_data.get('summary', article.get('title', 'Update')),
```
to:
```python
'description': content or article.get('title', 'Update'),
```

**Step 4: Verify the file is valid Python**

```bash
cd scraper && python -c "import db_writer; print('OK')"
```

Expected: `OK`.

**Step 5: Commit**

```bash
git add scraper/db_writer.py
git commit -m "use concise update_summary as breach update description instead of full summary"
```

---

### Task 5: Smoke test with `test_scraper.py`

**Files:**
- Read: `scraper/test_scraper.py`

**Step 1: Run the existing test scraper**

```bash
cd scraper && source venv/Scripts/activate && python test_scraper.py
```

Expected: Script runs without Python errors. Check output for any obvious failures.

**Step 2: Manually verify update detection logic with a quick inline test**

Run this to confirm `_compute_match_signals` works correctly:

```bash
cd scraper && source venv/Scripts/activate && python -c "
from main import _compute_match_signals

extracted = {'records_affected': 12400000, 'attack_vector': 'unauthorized_access'}
candidates = [
    {'id': 'abc', 'records_affected': 12461887, 'attack_vector': 'unauthorized_access'},
    {'id': 'def', 'records_affected': 50000000, 'attack_vector': 'phishing'},
    {'id': 'ghi', 'records_affected': None, 'attack_vector': None},
]
signals = _compute_match_signals(extracted, candidates)
for bid, sig in signals.items():
    print(bid, sig)
"
```

Expected output:
```
abc {'records_match': True, 'attack_vector_match': True, 'existing_records': 12461887, 'existing_attack_vector': 'unauthorized_access'}
def {'records_match': False, 'attack_vector_match': False, 'existing_records': 50000000, 'existing_attack_vector': 'phishing'}
ghi {'records_match': None, 'attack_vector_match': None, 'existing_records': None, 'existing_attack_vector': None}
```

**Step 3: Commit if any test file was modified**

If `test_scraper.py` was not modified, no commit needed here.

---

### Task 6: Final integration check

**Step 1: Import all scraper modules together**

```bash
cd scraper && source venv/Scripts/activate && python -c "
import config, ai_processor, db_writer, main
print('All modules import OK')
print('UPDATE_DETECTION_PROMPT length:', len(config.UPDATE_DETECTION_PROMPT))
print('update_summary in prompt:', 'update_summary' in config.UPDATE_DETECTION_PROMPT)
print('aggregator rule in prompt:', 'Have I Been Pwned' in config.UPDATE_DETECTION_PROMPT)
"
```

Expected:
```
All modules import OK
UPDATE_DETECTION_PROMPT length: [some number > 1500]
update_summary in prompt: True
aggregator rule in prompt: True
```

**Step 2: Final commit if anything was missed**

```bash
git status
```

If clean, no action. If any files were modified and not committed, commit them now.

# Design: Update Detection Improvements

**Date:** 2026-02-25
**Status:** Approved

## Problem

Two related bugs in the scraper's duplicate/update detection pipeline:

1. **False genuine updates** — secondary sources (especially HIBP) re-reporting the same breach with more specific data type detail (e.g. "email, phone number" vs "personal information") are incorrectly classified as `GENUINE_UPDATE` instead of `DUPLICATE_SOURCE`.

2. **Bloated update content** — when a genuine update IS written, the `description` stored in `breach_updates` is the full 500–600 word AI-extracted summary of the entire breach, not a concise note about what specifically changed.

### Root Cause (CarGurus example)

- BleepingComputer processed first → new breach created, `data_compromised: ['personal information']`
- HIBP processed second → HIBP enumerates specific data types (email, phone, dealer info, etc.) → AI sees this as "new information" → classifies `GENUINE_UPDATE`
- The full extracted summary from HIBP is stored as the update `description`, rehashing the whole incident

## Approach: Structured Pre-check + Prompt Improvements

4 files changed: `main.py`, `ai_processor.py`, `config.py`, `db_writer.py`

---

## Part 1 — `main.py`: Compute match signals

Add a `_compute_match_signals(extracted, candidates)` helper function after fetching `candidate_details`.

**Logic:**
- Iterate over each candidate breach
- For each candidate, check:
  - `records_match`: are `records_affected` values within 10% of each other? (handles None gracefully)
  - `attack_vector_match`: do `attack_vector` values match exactly?
- Return a `dict[breach_id → {records_match, attack_vector_match, existing_records, existing_attack_vector}]`

Pass the result into `ai_processor.detect_update()` as a new optional `match_signals` param.

---

## Part 2 — `ai_processor.py`: Thread signals into candidates context

**Signature change:**
```python
def detect_update(self, article, existing_breaches, match_signals=None)
```

When building `existing_breaches_str`, append match signal annotations inline for each candidate:
```
- ID: abc123
  Company: CarGurus
  Records: 12,461,887 | Attack Vector: unauthorized_access
  Structural signals: records MATCH (12.4M ≈ 12.4M), attack_vector MATCH
  → High prior for DUPLICATE_SOURCE — only classify as GENUINE_UPDATE if you can cite a specific new development
```

If `match_signals` is None or empty, the candidates context is built as before (no regression).

---

## Part 3 — `config.py`: Strengthen `UPDATE_DETECTION_PROMPT`

### New explicit rules to add:

1. **Aggregator rule**: "HIBP (Have I Been Pwned) and data breach aggregator listings are DUPLICATE_SOURCE if the company and record count match — they consolidate known incidents, they do not report new developments."

2. **Data types rule**: "More specific enumeration of already-known data types (e.g. 'email addresses, phone numbers' vs 'personal information') is NOT new information. It is clarification of already-known facts."

3. **Structural signals rule**: "If structural signals show records and attack_vector already match, the bar for GENUINE_UPDATE is very high. It must cite new legal/regulatory action, a newly identified CVE, a significantly revised record count (>10% change), or confirmed root cause."

### Update the genuine update examples to be explicit:
- Record count revised by >10%
- Class action lawsuit filed
- Regulatory fine or investigation opened
- New CVE or technical root cause identified
- Breach scope expanded to new systems or data types not previously known

### Add `update_summary` to JSON output:
```json
"update_summary": "1-2 sentence description of what specifically is new in this article. Null if classification is DUPLICATE_SOURCE or NEW_BREACH."
```

### Reinforce the tiebreaker:
"When in doubt between GENUINE_UPDATE and DUPLICATE_SOURCE, always prefer DUPLICATE_SOURCE."

---

## Part 4 — `db_writer.py`: Use concise update content

**Signature change:**
```python
def write_breach_update(self, update_data, breach_id, article, update_type='new_info', confidence=0.8, content=None)
```

**Logic change in `description` field:**
```python
'description': content or update_data.get('title') or article.get('title', 'Update')
```

`content` is `update_check.get('update_summary')` passed from `main.py` — the 1–2 sentence AI-generated "what changed" note. Falls back to the article title if `update_summary` is null (which shouldn't happen for genuine updates, but guards against it).

**`main.py` call site change:**
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

---

## Files Changed

| File | Change |
|------|--------|
| `scraper/main.py` | Add `_compute_match_signals()`, pass signals to `detect_update`, pass `update_summary` to `write_breach_update` |
| `scraper/ai_processor.py` | Add `match_signals` param to `detect_update`, annotate candidates context string |
| `scraper/config.py` | Strengthen `UPDATE_DETECTION_PROMPT`: aggregator rule, data types rule, structural signals section, `update_summary` field |
| `scraper/db_writer.py` | Add `content` param to `write_breach_update`, use it as `description` |

## Out of Scope

- No changes to the extraction stage or classification stage
- No schema changes to `breach_updates` table
- No frontend changes

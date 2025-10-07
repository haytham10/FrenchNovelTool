# Vocabulary Coverage Tool - User Guide

## Overview

The Vocabulary Coverage Tool helps language learners optimize their study by analyzing and filtering sentences based on high-frequency vocabulary. It supports two modes:

1. **Coverage Mode**: Select a minimal set of sentences that covers all words in your vocabulary list
2. **Filter Mode**: Find sentences with high vocabulary density (≥95% common words) for efficient drilling

## Getting Started

### 1. Manage Word Lists

Word lists define which vocabulary you want to focus on (e.g., "French 2K most common words").

**List available word lists:**
```bash
GET /api/v1/wordlists
```

**Create a new word list:**
```bash
POST /api/v1/wordlists
Content-Type: multipart/form-data

{
  "file": <CSV file with words>,
  "name": "My French 3K List",
  "fold_diacritics": true
}
```

Or with JSON:
```bash
POST /api/v1/wordlists
Content-Type: application/json

{
  "name": "Custom Word List",
  "source_type": "manual",
  "words": ["le", "chat", "manger", "dormir", ...],
  "fold_diacritics": true
}
```

**Response includes ingestion report:**
```json
{
  "wordlist": {
    "id": 1,
    "name": "My French 3K List",
    "normalized_count": 2987,
    "canonical_samples": ["le", "chat", "maison", ...]
  },
  "ingestion_report": {
    "original_count": 3000,
    "normalized_count": 2987,
    "duplicates": [...],
    "multi_token_entries": [...],
    "variants_expanded": 45
  }
}
```

### 2. Set Default Word List (Optional)

Update your user settings to set a default word list:

```bash
POST /api/v1/user/settings

{
  "default_wordlist_id": 1,
  "coverage_defaults": {
    "mode": "filter",
    "min_in_list_ratio": 0.95,
    "len_min": 4,
    "len_max": 8,
    "target_count": 500
  }
}
```

### 3. Run Coverage Analysis

**From a completed job:**
```bash
POST /api/v1/coverage/run

{
  "mode": "filter",
  "source_type": "job",
  "source_id": 123,
  "wordlist_id": 1,
  "config": {
    "min_in_list_ratio": 0.95,
    "len_min": 4,
    "len_max": 8,
    "target_count": 500
  }
}
```

**From a history entry:**
```bash
POST /api/v1/coverage/run

{
  "mode": "coverage",
  "source_type": "history",
  "source_id": 456,
  "wordlist_id": 1
}
```

If `wordlist_id` is omitted, uses your default word list (or global default).

**Response:**
```json
{
  "coverage_run": {
    "id": 789,
    "mode": "filter",
    "status": "pending",
    "progress_percent": 0,
    "created_at": "2024-01-15T12:00:00Z"
  },
  "task_id": "abc123-def456-..."
}
```

### 4. Check Run Status

```bash
GET /api/v1/coverage/runs/789?page=1&per_page=50
```

**Response (when completed):**
```json
{
  "coverage_run": {
    "id": 789,
    "mode": "filter",
    "status": "completed",
    "progress_percent": 100,
    "stats_json": {
      "total_sentences": 5000,
      "candidates_passed_filter": 1200,
      "selected_count": 500,
      "filter_acceptance_ratio": 0.24,
      "min_in_list_ratio": 0.95,
      "len_min": 4,
      "len_max": 8
    },
    "completed_at": "2024-01-15T12:05:00Z"
  },
  "assignments": [
    {
      "word_key": "chat",
      "sentence_index": 42,
      "sentence_text": "Le chat dort sur le tapis.",
      "sentence_score": 9.8,
      "in_list_ratio": 1.0
    },
    ...
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 500,
    "pages": 10
  }
}
```

### 5. Swap Assignments (Coverage Mode Only)

Manually reassign a word to a different sentence:

```bash
POST /api/v1/coverage/runs/789/swap

{
  "word_key": "chat",
  "new_sentence_index": 100
}
```

### 6. Export to Google Sheets

```bash
POST /api/v1/coverage/runs/789/export

{
  "sheet_name": "French Drilling - Week 1",
  "folder_id": "1ABC..."
}
```

## Modes Explained

### Coverage Mode

**Goal:** Ensure every word in your vocabulary list appears at least once in the selected sentences.

**Use Case:** Teachers creating comprehensive reading exercises, or learners ensuring complete vocabulary exposure.

**Algorithm:** Greedy set cover - selects the minimal set of sentences that collectively cover all target words.

**Example:**
- Word list: ["chat", "chien", "manger", "dormir"]
- Sentences: ["Le chat mange", "Le chien dort", "Un oiseau chante"]
- Result: Selects first two sentences (cover all 4 words)

### Filter Mode

**Goal:** Find high-quality sentences for drilling - short (4-8 words), high vocabulary density (≥95% common words).

**Use Case:** Language learners like Stan who want ~500 perfect sentences for auditory repetition drills.

**Algorithm (Multi-Pass Approach):** 
1. **Pass 1**: Scan all sentences for 4-word sentences with ≥95% in word list (prioritized)
2. **Pass 2**: If fewer than 500 found, scan for 3-word sentences to fill gap
3. **Pass 3**: If still not enough, use remaining sentences in configured range (5-8 words)
4. Each pass ranks by composite score (ratio + frequency + quality)
5. Select top N from combined passes (default 500)

**Why Multi-Pass?** 4-word sentences are ideal for language learning drills - long enough to be meaningful, short enough for easy memorization. The algorithm prioritizes these before falling back to shorter or longer alternatives.

**Example:**
- Word list: French 2K common words
- Input: 5,000 rewritten sentences
- Pass 1: Find 350 4-word sentences with ≥95% coverage
- Pass 2: Find 120 3-word sentences to reach 470 total
- Pass 3: Add 30 more sentences (5-8 words) to reach target of 500
- Result: 500 sentences prioritized by ideal length

**Typical Results:**
- Prioritized: "Le chat dort bien." (4 words, 100% match, score: 10.25)
- Fallback: "Chat dort." (3 words, 100% match, score: 10.33)
- Last Resort: "Le grand chien magnifique court." (5 words, 80% match)
- Rejected: "Le xylophone résonne." (≥95% threshold not met)

## Configuration Options

### Coverage Mode Config
```json
{
  "alpha": 0.5,           // Duplicate penalty weight
  "beta": 0.3,            // Quality weight
  "gamma": 0.2,           // Length penalty weight
  "target_sentence_length": 6,
  "max_sentences": 1000,
  "prefer_non_dialogue": true
}
```

### Filter Mode Config
```json
{
  "min_in_list_ratio": 0.95,    // Minimum 95% of words must be in list
  "len_min": 4,                  // Minimum sentence length
  "len_max": 8,                  // Maximum sentence length
  "target_count": 500,           // Number of sentences to select
  "frequency_weighting": true,   // Prefer higher-frequency words
  "diversity_penalty": 0.2       // Reduce near-duplicate sentences
}
```

### Normalization Config (shared)
```json
{
  "normalize_mode": "lemma",      // Use lemmatization
  "fold_diacritics": true,        // Remove accents (café → cafe)
  "handle_elisions": true         // Handle l', d', etc.
}
```

## Word List Format

### CSV Upload
Simple CSV with one word per line:
```
le
chat
manger
dormir
maison
```

### Variants
Use `|` or `/` to specify variants:
```
chat|chats
bon/bonne
```

### Multi-token Entries
Multi-word entries use first token by default:
```
un temps
de temps en temps
```
→ Extracts: "un", "de"

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/wordlists` | GET | List word lists |
| `/api/v1/wordlists` | POST | Create word list |
| `/api/v1/wordlists/:id` | GET | Get word list details |
| `/api/v1/wordlists/:id` | PATCH | Update word list |
| `/api/v1/wordlists/:id` | DELETE | Delete word list |
| `/api/v1/user/settings` | GET/POST | User settings (includes coverage defaults) |
| `/api/v1/coverage/run` | POST | Start coverage run |
| `/api/v1/coverage/runs/:id` | GET | Get run status & results |
| `/api/v1/coverage/runs/:id/swap` | POST | Swap assignment |
| `/api/v1/coverage/runs/:id/export` | POST | Export to Sheets |

## Rate Limits

- Word list creation: 10 per hour
- Coverage runs: 20 per hour
- Exports: 10 per hour

## Troubleshooting

**Problem:** "No word list specified and no global default found"
- **Solution:** Either specify `wordlist_id` in your request, or set `default_wordlist_id` in user settings

**Problem:** Low acceptance ratio in Filter mode (< 10%)
- **Solution:** Your vocabulary list may be too restrictive. Try:
  - Increasing word list size (2K → 5K)
  - Lowering `min_in_list_ratio` (0.95 → 0.85)
  - Expanding length range (4-8 → 3-10)

**Problem:** Coverage mode doesn't cover all words
- **Solution:** Some words may not appear in your source sentences. Check `stats_json.uncovered_words` for the list.

## Examples

### Stan's Daily Drill Workflow

1. **Setup (once):**
   ```bash
   # Upload French 2K word list
   POST /api/v1/wordlists
   # Set as default with Filter mode
   POST /api/v1/user/settings
   ```

2. **After processing a novel:**
   ```bash
   # Run filter mode on completed job
   POST /api/v1/coverage/run
   {
     "mode": "filter",
     "source_type": "job",
     "source_id": 123
   }
   ```

3. **Get results:**
   ```bash
   GET /api/v1/coverage/runs/789
   # Receives ~500 sentences, 4-8 words, ≥95% in 2K list
   ```

4. **Export for drilling:**
   ```bash
   POST /api/v1/coverage/runs/789/export
   # Creates Google Sheet: "French Drilling - Week 1"
   # Drill 50 sentences/day for 10 days
   ```

## Technical Notes

- **Lemmatization:** Uses spaCy `fr_core_news_md` model for French
- **Normalization:** Handles plurals, conjugations, elisions (l', d'), diacritics
- **Performance:** Typical run on 5K sentences with 2K word list: 5-15 seconds
- **Storage:** Full word lists stored; samples cached in WordList model

# Vocabulary Coverage Tool - API Documentation

## Overview
The Vocabulary Coverage Tool provides APIs for managing word lists, running vocabulary coverage analysis, and filtering sentences based on vocabulary density.

## Data Models

### WordList
Stores vocabulary word lists with normalized words.

**Fields:**
- `id` (Integer, PK): Unique identifier
- `owner_user_id` (Integer, FK, nullable): Owner user ID (NULL for global lists)
- `name` (String): Name of the word list
- `source_type` (String): Source type - 'csv', 'google_sheet', or 'manual'
- `source_ref` (String, nullable): Reference to source (file name, Sheet ID, etc.)
- `normalized_count` (Integer): Count of normalized unique words
- `canonical_samples` (JSON): Sample of normalized keys (first 20)
- `words_json` (JSON): Full normalized word list (array of strings)
- `is_global_default` (Boolean): Whether this is the global default list
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

### CoverageRun
Tracks vocabulary coverage analysis runs.

**Fields:**
- `id` (Integer, PK): Unique identifier
- `user_id` (Integer, FK): Owner user ID
- `mode` (String): Analysis mode - 'coverage' or 'filter'
- `source_type` (String): Source type - 'job' or 'history'
- `source_id` (Integer): ID of the source (job_id or history_id)
- `wordlist_id` (Integer, FK, nullable): Word list ID (uses default if NULL)
- `config_json` (JSON): Configuration for the run
- `status` (String): Run status - 'pending', 'processing', 'completed', 'failed', 'cancelled'
- `progress_percent` (Integer): Progress percentage (0-100)
- `stats_json` (JSON): Analysis statistics and results
- `created_at` (DateTime): Creation timestamp
- `completed_at` (DateTime, nullable): Completion timestamp
- `error_message` (String, nullable): Error message if failed
- `celery_task_id` (String, nullable): Celery task ID

**Config JSON Schema (Coverage Mode):**
```json
{
  "alpha": 0.5,          // Duplicate penalty weight
  "beta": 0.3,           // Quality weight
  "gamma": 0.2,          // Length penalty weight
  "normalize_mode": "lemma",
  "ignore_diacritics": true,
  "handle_elisions": true
}
```

**Config JSON Schema (Filter Mode):**
```json
{
  "min_in_list_ratio": 0.95,    // Minimum ratio of words in list
  "len_min": 4,                  // Minimum sentence length
  "len_max": 8,                  // Maximum sentence length
  "target_count": 500,           // Target number of sentences
  "normalize_mode": "lemma",
  "ignore_diacritics": true,
  "handle_elisions": true
}
```

### CoverageAssignment
Stores word-to-sentence assignments from coverage runs.

**Fields:**
- `id` (Integer, PK): Unique identifier
- `coverage_run_id` (Integer, FK): Associated coverage run
- `word_original` (String, nullable): Original word from list
- `word_key` (String): Normalized word key
- `lemma` (String, nullable): Lemmatized form
- `matched_surface` (String, nullable): Surface form found in sentence
- `sentence_index` (Integer): Index in source sentences
- `sentence_text` (Text): Full sentence text
- `sentence_score` (Float, nullable): Quality/ranking score
- `conflicts` (JSON, nullable): Conflict information
- `manual_edit` (Boolean): Whether manually edited
- `notes` (Text, nullable): User notes

## API Endpoints

### WordList Management

#### List Word Lists
`GET /api/v1/wordlists`

**Authentication:** Required (JWT)

**Query Parameters:**
- `page` (int, default: 1): Page number
- `per_page` (int, default: 20, max: 100): Results per page

**Response:**
```json
{
  "wordlists": [
    {
      "id": 1,
      "name": "French 2K Default",
      "source_type": "manual",
      "source_ref": "seed_script",
      "normalized_count": 200,
      "canonical_samples": ["le", "la", "les", ...],
      "is_global_default": true,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "pages": 1
  }
}
```

#### Create Word List
`POST /api/v1/wordlists`

**Authentication:** Required (JWT)

**Rate Limit:** 10 per hour

**Request (JSON):**
```json
{
  "name": "My Custom List",
  "source_type": "manual",
  "words": ["chat", "chien", "maison"],
  "fold_diacritics": true
}
```

**Request (File Upload):**
- Form field `file`: CSV file
- Form field `name` (optional): Name for the list
- Form field `fold_diacritics` (optional, default: "true"): Whether to fold diacritics

**Response:**
```json
{
  "wordlist": {
    "id": 2,
    "name": "My Custom List",
    ...
  },
  "ingestion_report": {
    "original_count": 3,
    "normalized_count": 3,
    "duplicates": [],
    "multi_token_entries": [],
    "variants_expanded": 0,
    "anomalies": []
  }
}
```

#### Get Word List
`GET /api/v1/wordlists/:id`

**Authentication:** Required (JWT)

**Response:**
```json
{
  "id": 1,
  "name": "French 2K Default",
  ...
}
```

#### Update Word List
`PATCH /api/v1/wordlists/:id`

**Authentication:** Required (JWT) - Owner only

**Request:**
```json
{
  "name": "Updated Name"
}
```

#### Refresh Word List
`POST /api/v1/wordlists/:id/refresh`

**Authentication:** Required (JWT)

Refreshes/populates `words_json` from the original source (e.g., Google Sheets).

#### Delete Word List
`DELETE /api/v1/wordlists/:id`

**Authentication:** Required (JWT) - Owner only

### Coverage Run Management

#### Create Coverage Run
`POST /api/v1/coverage/run`

**Authentication:** Required (JWT)

**Rate Limit:** 20 per hour

**Request:**
```json
{
  "mode": "coverage",
  "source_type": "history",
  "source_id": 123,
  "wordlist_id": 1,
  "config": {
    "alpha": 0.5,
    "beta": 0.3,
    "gamma": 0.2
  }
}
```

**Response:**
```json
{
  "coverage_run": {
    "id": 1,
    "status": "pending",
    ...
  },
  "task_id": "celery-task-id-123"
}
```

#### Get Coverage Run
`GET /api/v1/coverage/runs/:id`

**Authentication:** Required (JWT)

**Query Parameters:**
- `page` (int, default: 1): Page for assignments
- `per_page` (int, default: 50, max: 100): Assignments per page

**Response:**
```json
{
  "coverage_run": {
    "id": 1,
    "mode": "coverage",
    "status": "completed",
    "stats_json": {
      "words_total": 2000,
      "words_covered": 1850,
      "words_uncovered": 150,
      "selected_sentence_count": 425
    },
    ...
  },
  "assignments": [
    {
      "word_key": "chat",
      "sentence_text": "Le chat dort sur le canapé.",
      "sentence_index": 42,
      ...
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 1850,
    "pages": 37
  }
}
```

#### Swap Assignment
`POST /api/v1/coverage/runs/:id/swap`

**Authentication:** Required (JWT)

**Request:**
```json
{
  "word_key": "chat",
  "new_sentence_index": 55
}
```

#### Export Coverage Run
`POST /api/v1/coverage/runs/:id/export`

**Authentication:** Required (JWT)

**Rate Limit:** 10 per hour

**Request:**
```json
{
  "sheet_name": "Vocabulary Coverage Results",
  "folder_id": "google-drive-folder-id"
}
```

**Response:**
```json
{
  "message": "Export successful",
  "spreadsheet_id": "google-sheet-id",
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/..."
}
```

#### Download Coverage Run (CSV)
`GET /api/v1/coverage/runs/:id/download`

**Authentication:** Required (JWT)

Returns CSV file with coverage results.

### Monitoring

#### Prometheus Metrics
`GET /api/v1/metrics`

**Authentication:** None (public endpoint for monitoring)

Returns Prometheus metrics in text format:

**Metrics:**
- `coverage_runs_total{mode, status}`: Total coverage runs
- `coverage_build_duration_seconds{mode}`: Build duration histogram
- `wordlists_total{source_type, is_global}`: Total word lists
- `wordlists_created_total{source_type}`: Total created
- `coverage_assignments_total{mode}`: Total assignments
- `wordlist_ingestion_errors_total{source_type, error_type}`: Ingestion errors

## Word List Ingestion Policy

### Normalization Pipeline

1. **Trim whitespace** from input words
2. **Remove zero-width characters** (U+200B to U+200F, UFEFF)
3. **Split variants** on `|` and `/` separators
4. **Unicode casefold** for case-insensitive matching
5. **Fold diacritics** (optional, default: true) - removes accents
6. **Handle elisions** - extract lexical head from l', d', j', n', s', t', c', qu'
7. **Multi-token handling** - extract head lexical token, flag in report
8. **Lemmatize** using spaCy `fr_core_news_sm` model
9. **Deduplicate** by normalized key

### Ingestion Report

The ingestion report provides detailed information:

```json
{
  "original_count": 250,
  "normalized_count": 200,
  "duplicates": [
    {"word": "chats", "normalized": "chat"}
  ],
  "multi_token_entries": [
    {"original": "bon jour", "head_token": "bon"}
  ],
  "variants_expanded": 15,
  "anomalies": [
    {"word": "   ", "issue": "empty_after_normalization"}
  ]
}
```

## Coverage Modes

### Coverage Mode

**Goal:** Select minimal set of sentences that cover all words in the word list.

**Algorithm:** Greedy set cover
1. Build sentence index with word matches
2. Select sentence covering most uncovered words
3. Repeat until all words covered or no progress

**Output:** Word-to-sentence assignments

### Filter Mode

**Goal:** Select high-quality sentences with high vocabulary density.

**Algorithm:** Multi-pass filtering
1. **Pass 1:** 4-word sentences with ratio ≥ 0.95
2. **Pass 2:** 3-word sentences with ratio ≥ 0.95 (if needed)
3. **Pass 3:** Other lengths in range with ratio ≥ 0.95 (if needed)

**Scoring:** `ratio * 10.0 + (1.0 / token_count) * 0.5`

**Output:** Ranked sentences with scores

## Error Handling

All endpoints return standard error responses:

**422 Unprocessable Entity:**
```json
{
  "errors": {
    "field_name": ["validation error message"]
  }
}
```

**500 Internal Server Error:**
```json
{
  "error": "Error message",
  "details": "Detailed error information"
}
```

## Linguistics Processing

### French Text Processing

The system uses spaCy's `fr_core_news_sm` model for:
- **Tokenization**: Split text into tokens
- **Lemmatization**: Reduce words to base form
- **POS tagging**: Part-of-speech identification

### Elision Handling

French elisions are handled automatically:
- l'homme → homme
- d'abord → abord
- j'ai → ai
- qu'il → il

### Diacritic Folding

When enabled (default):
- café → cafe
- élève → eleve
- être → etre

## Best Practices

1. **Word Lists**: Use normalized, deduplicated lists for best results
2. **Coverage Mode**: Ideal for creating comprehensive teaching materials
3. **Filter Mode**: Best for selecting practice sentences
4. **Config Tuning**: Adjust ratios and lengths based on learner level
5. **Metrics**: Monitor via `/api/v1/metrics` for production health

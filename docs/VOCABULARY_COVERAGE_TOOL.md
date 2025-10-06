# Vocabulary Coverage Tool — Design & Implementation Plan

Status: Planning
Priority: High
Estimated Effort: 4–7 days (backend 2–4, frontend 1–2, QA 1)

## Executive Summary

Build a new tool that, given a “2000 Most Commonly Used French Words” list, selects a minimal set of sentences produced by the French Novel Automation Tool such that:
- Every target word appears in at least one selected sentence.
- Each target word appears in at most one selected sentence, as far as possible.
- The selected set is small (target: < 600 sentences), prioritizing sentence quality and readability.
- Morphology-aware matching:
  - Nouns: singular and plural map to the same lemma and are considered covered by the same target entry.
  - Verbs: any conjugation (any tense/person/number) maps to the verb lemma and is considered covered by the same target entry.

This is a constrained Set Cover optimization with uniqueness and quality heuristics. The tool must integrate seamlessly with our existing async pipeline, History data, Google Sheets, UI patterns, and deployment strategy.

Word list sources (provided by product):
- Google Sheet (primary): [2000 Most Commonly Used French Words](https://docs.google.com/spreadsheets/d/15BL8bFX5KTbXguLzF44wZ8NXluoKXdGfYSc4cHBuEj0/edit?usp=sharing)
- CSV (snapshot file name): 2000 French Words with Parts of Speech - 2000 Words With Parts of Speech.csv

---

## Goals

1. Import the 2,000-word list from Google Sheets or CSV and normalize it (case, diacritics, elisions, hyphens, lemma).
2. Perform lemma-based matching by default so singular/plural and verb conjugations are recognized as the same target word.
3. Build an efficient coverage from the normalized sentences of a selected History (or Job) output.
4. Optimize for:
   - Full coverage with minimal selected sentences (< 600 when feasible).
   - Avoid reusing words across multiple selected sentences where possible.
   - Prefer sentences aligned with product quality heuristics (length band, clarity, optionally non-dialogue).
5. Provide interactive UI to review assignments, swap sentences for a word, re-run local improvements, export to Google Sheets.
6. Integrate with async tasks, WebSocket progress updates, History, and Google Sheets Service.

---

## Word List: Schema, Normalization, and Data Quality

### Schema (CSV row format)

Each CSV line follows:
- Column 1: Index (1..2000). Note: some lines include hidden/zero-width characters; sanitize to integer.
- Column 2: French forms (string). May contain:
  - Multiple alternatives separated by pipes `|` (e.g., `Le|La`, `Celui|Celle`)
  - Sometimes slash variants (e.g., `Jusque/Jusqu’`)
  - Multi-token entries (e.g., `Un temps`, `Le monde`, `Une raison`)
- Column 3: English gloss (string). May include a pipe `|` between alternatives (e.g., `A|An`).
- Column 4: Part of Speech (string): Determiner, Preposition, Noun, Verb, Adjective, Adverb, Pronoun, Conjunction, Number, Interjection, etc.

Examples:
- `1,Un|Une,A|An,Determiner`
- `6,Être,Be,Verb`
- `65,Un temps,A time, Noun`
- `132,Jusque/Jusqu’,Until/Until,Preposition`

Note: There are entries with capitalization inconsistencies, typos, duplicate lexemes (e.g., “Bien” appears as #48 and #2000), and POS/gloss mismatches (e.g., “Suffire” listed as Adverb). Do not rely on POS for lemmatization; use actual NLP tooling.

### Normalization rules (targets)

To create canonical “word keys” for matching:

- Casefold entire entry: `casefold()`
- Diacritics: fold accents (é→e, ç→c) using Unicode normalization/unidecode
- Elisions: strip leading clitics (l’, d’, j’, n’, s’, t’, c’, qu’) so `l’amour` → `amour`
- Hyphens: split and keep lexical head components as tokens; also keep original form for reference
- Lemmatization (default): use spaCy French model (`fr_core_news_md` preferred; `sm` fallback) to derive lemma for each variant form
- Alternatives: for `Le|La`, `Celui|Celle`, or slash variants, produce the union of normalized keys and map them to a single canonical lemma where linguistically appropriate
- Multi-token entries (e.g., `Un temps`, `La vie`): in v1, derive the head lexical token as the target (e.g., `temps`, `vie`), while preserving the original string; determiners/prepositions are dropped from target keys by default
  - If an entry is truly multiword content (rare), flag for review; optional v2 support for multiword coverage

We will store for each entry:
- original: as in list (“Être”, “Un temps”)
- surface_variants: split by `|` and `/`
- key: canonical normalized key (lemma-based token)
- lemma: the spaCy-derived lemma for the head token
- pos_hint: the POS from the sheet for reference only (not authoritative)

Deduplication:
- Deduplicate by `key` (canonical lemma) across the full list
- Keep the lowest index row as the primary; record alias-to-primary mapping
- Produce a `wordlist_report` in the run stats with:
  - duplicates found, alias chains, corrections applied
  - typos/unknown tokens flagged by NLP (optional)

Data anomalies (to be handled or flagged):
- Duplicates (e.g., Bien #48 and #2000)
- Mis-typed entries (e.g., “Un disours” → “Un discours”)
- POS mismatches (e.g., “Suffire” marked as Adverb)
- Mixed casing in ENG glosses, irrelevant for matching
- Numbering anomalies (e.g., line `1​772` with zero-width character)

We will:
- Sanitize index column
- Normalize French forms as above
- Ignore English gloss for matching (kept for export only)
- Do not fail hard on anomalies; warn and continue with best-effort normalization

---

## Matching Requirements (Confirmed)

- Singular/plural nouns both satisfy the same target word (lemma-level match).
- Any verb conjugation in any tense/person/number satisfies the verb entry (lemma-level match).
- Determiners, pronouns, prepositions, conjunctions in the list are single-token targets; they will match identically normalized tokens in sentences (lemma or surface-mode if more appropriate).
- Default mode: lemma-based matching to meet morphology acceptance; surface-only mode remains available via config if desired.

---

## Architecture Overview

- Backend: Flask + Celery, SQLAlchemy models, Marshmallow schemas
- Frontend: Next.js 15 (App Router) + React Query v5 + MUI
- Data Source: Sentences from an existing History entry (preferred) or completed Job
- Word Source: Google Sheet URL/ID (primary) or CSV upload (fallback)
- Processing: Async Celery task with WebSocket progress events
- Output: CoverageRun + CoverageAssignment; export to Google Sheets

New/Updated Components:
- WordListService (new): imports & normalizes the 2,000 words
- CoverageService (new): indexing, scoring, greedy cover, uniqueness post-process
- Linguistics utils (new): tokenization + lemmatization + normalization rules
- GoogleSheets integration (existing): read sheet (readonly), export results

---

## Data Model

1) CoverageRun
- id (PK), user_id (FK)
- source_type: 'history' | 'job'; source_id
- wordlist_source: 'google_sheet' | 'csv'
- wordlist_ref: string (sheet URL/ID or uploaded file name)
- config_json: JSON (normalize_mode='lemma' default, ignore_diacritics=true, handle_elisions=true, target_sentence_length, max_sentences, alpha, beta, gamma, prefer_non_dialogue, multiword_policy='headword', etc.)
- status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
- progress_percent: int
- stats_json: JSON
  - words_total, words_deduped, duplicates_detected
  - words_covered, words_uncovered
  - sentences_selected, runtime_ms
  - wordlist_report (anomalies, aliases)
- timestamps, error_message

2) CoverageAssignment
- id (PK), coverage_run_id (FK, indexed)
- word_original: string
- word_key: string (canonical key; lemma-based)
- lemma: string (lemma; typically equals `word_key` unless policy differs)
- matched_surface: string (actual surface token found, e.g., “étais” for lemma “être”)
- sentence_index: int
- sentence_text: text (snapshot)
- sentence_score: float
- conflicts: JSON (other target words in same sentence; diagnostic)
- notes: text
- UNIQUE(coverage_run_id, word_key)

---

## Algorithm (Greedy Set Cover with Uniqueness and Quality)

Outline:
1) Load sentences (History/Job), normalize tokens per sentence (lemma-based).
2) Build inverted index: `word_key -> [sentence indices]`.
3) Precompute sentence quality score (length, clarity, optionally non-dialogue).
4) Greedy selection with objective:
   - score = gain(uncovered words) − α·duplicate_penalty + β·quality − γ·length_penalty
5) Assign newly covered words to the chosen sentence (first-assignment wins).
6) Post-process to reduce duplicates (reassign words among selected sentences if it improves uniqueness without losing coverage).
7) Persist assignments, stats, and reports.

Defaults:
- alpha=1.0, beta=0.3, gamma=0.1
- target_sentence_length=12
- max_sentences=600
- prefer_non_dialogue=true

---

## Backend Implementation Plan (unchanged, refined)

- Add spaCy + unidecode to requirements; prefer `fr_core_news_md` model.
- WordListService:
  - load_from_google_sheet(url_or_id) using Sheets API (readonly) or public CSV export fallback
  - load_from_csv(file_stream)
  - normalize_words(words, config):
    - split alternatives on `|` and `/`
    - strip determiners/prepositions for multi-token entries; take head lexical token (configurable)
    - diacritics/elision handling
    - lemmatize to derive canonical `word_key`
    - dedupe; build alias map and anomaly report
- CoverageService:
  - tokenize_and_normalize sentences using same pipeline (lemma mode default)
  - build inverted index and scores
  - greedy cover + post-process
  - assemble assignments and stats
- Endpoints:
  - POST /api/v1/coverage/run (start async)
  - GET /api/v1/coverage/runs/:id (status/results)
  - POST /api/v1/coverage/runs/:id/swap
  - POST /api/v1/coverage/runs/:id/reoptimize
  - POST /api/v1/coverage/runs/:id/export (Google Sheets)
- Celery task coverage_build_async(run_id):
  - read & normalize word list (Sheet/CSV) → store stats/aliases
  - load source sentences → normalize (lemma-based)
  - build coverage → persist → emit WS progress

Error handling:
- Do not fail on list anomalies; warn and continue
- 422 for empty/invalid list after normalization (e.g., all entries filtered out)

---

## Frontend Plan (unchanged, refined)

- Start Coverage UI:
  - Source selection (History or Job)
  - Word list source: paste Google Sheet URL/ID or upload CSV
  - Explain morphology support (singular/plural, verb conjugations via lemma)
  - Settings (weights, max sentences)
  - Submit and track progress
- Results UI:
  - KPIs (covered/total, selected sentences, uncovered)
  - Assignments table: Word (original) | Lemma/Key | Matched Surface | Sentence | Score | Actions (Swap)
  - Filters (uncovered only, search)
  - Swap with candidate suggestions
  - Export to Google Sheets
- Hooks (React Query) for start, fetch, swap, reoptimize, export

---

## Testing & Validation (include list ingestion QA)

Backend:
- Word list normalization:
  - Alternatives: `Le|La` → `le`, `la` → key `le` (determinant entries may remain separate targets; configurable aggregation)
  - Elisions: `Jusque/Jusqu’` → `jusque` key
  - Multi-token entries: `Un temps` → headword `temps` (and note choice)
  - Deduplication: detect and collapse duplicates (e.g., “Bien” occurring twice)
  - Typos: flag unknown tokens (e.g., “disours”) for report; allow manual correction path in future
- Morphology:
  - Noun plurals map to lemma (chevaux→cheval)
  - Verb conjugations map to lemma (étais/seront→être)
- Coverage on small fixture:
  - Deterministic greedy outcome with fixed config
  - Post-process reduces duplicates without losing coverage
- End-to-end:
  - Start run with the provided 2,000-word sheet; ensure stats align with expectations (deduped size, anomalies reported)

Frontend:
- Start dialog validates Sheet URL/CSV presence
- Results render; swap updates stats; export yields valid sheet link

---

## Performance & Observability

- Cache sentence tokenization per run; consider cross-run cache (keyed by sentence hash + config)
- Metrics:
  - coverage_runs_total{status}
  - coverage_build_duration_seconds
  - words_total, words_deduped, words_covered, words_uncovered
  - sentences_selected
- Logs:
  - Wordlist anomalies report (duplicates, typos, multi-token resolutions)
  - Top-gain sentences during greedy

---

## Rollout Plan

1) Backend
   - Models + migration
   - WordListService and CoverageService
   - Async task + WS integration
2) Frontend
   - Start dialog + results + swap + export
3) QA
   - Validate with the provided 2,000-word sheet and representative History
   - Tune defaults (alpha/beta/gamma, max sentences)
4) Production
   - Feature flag `VOCAB_COVERAGE_ENABLED`
   - Monitor metrics and logs

---

## Acceptance Criteria

- User can select a History (or Job), link the provided Google Sheet (or upload CSV), and run coverage.
- Matching respects morphological variants (singular/plural nouns; any verb conjugations) via lemma-based normalization.
- The tool covers as many of the 2,000 targets as possible with minimal sentences, ideally < 600.
- Each word is assigned to at most one sentence when feasible; duplicates minimized.
- Word list anomalies are handled gracefully and reported (dedupes, typos, multi-token rule decisions).
- Users can swap assignments and export results to Google Sheets.
- Documentation and tests are updated accordingly.

---

## Notes on the Provided 2,000-Word List

- Expect multiple-form entries (`|` and `/`) and multi-token entries with articles or function words (e.g., “Un temps”, “Le monde”).
  - V1 policy: target the head lexical token (temps, monde) while keeping original text in reports.
- Duplicates exist (e.g., “Bien” appears at least twice); we will deduplicate by canonical key.
- Some rows contain typos and POS inconsistencies; POS will not be used for lemmatization.
- Hidden/zero-width characters appear around some indices; indices will be sanitized.
- Gloss capitalization is irrelevant for matching and retained only for export.

These decisions ensure robust ingestion and consistency with our lemma-based matching requirement.

---
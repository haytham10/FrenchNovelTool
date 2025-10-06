# Vocabulary Coverage Tool — Complete Design & Implementation Plan

Status: Ready for implementation  
Priority: High  
Estimated Effort: 4–7 days (MVP) + 2–4 weeks (hardening & optimization)

Purpose
- Given a target word list (default: the supplied 2000 Most Commonly Used French Words), find a small set of sentences produced by the French Novel Automation Tool such that every target word is represented at least once, and/or filter sentences to maximize high-frequency vocabulary density. Where possible, each target word should appear in only one selected sentence. The user should be able to manage word lists in Settings, run coverage right after a Job finishes, from a History entry, or from a standalone Coverage page.

## Client Vision and Tool Intersection (Critical Context)

We need to solidify our understanding of the client’s complete vision before moving forward. The goal isn’t just about sentence structure; it’s about hyper‑efficient, vocabulary‑driven language learning.

Client Goal: Accelerated French Fluency
- The client, Stan, has a clear, actionable plan based on Zipf’s Law and auditory repetition to achieve conversational fluency in roughly ten days.

Learning components and tool requirements:
- High‑Frequency Vocabulary
  - The tool must use sentences composed almost entirely of the 2,000 to 5,000 most common French words to ensure he only learns what is immediately useful for conversation.
- Repetition Drills
  - The sentences must be short (4 to 8 words) and perfectly structured for repetition while walking or driving.
- Arithmetic
  - The final output needs to be a database of ~500 high‑quality sentences that meet the criteria, which he can then drill 50 per day.

How our tools must intersect:
1) Tool 1 — Current App (Sentence Rewriter)
- Function: Linguistic Rewriting.
- Purpose: Take complex French novel text and simplify it into a stream of complete, grammatically pure, 4–8 word sentences — ideal for repeatable drills.
- Status: The recent chunking/execution fixes ensure this foundation is structurally sound.

2) Tool 2 — Next Tool (2000‑Word List Filter)
- Function: Precision Vocabulary Filter on the rewritten sentences.
- Purpose: Cross‑reference every token in each rewritten sentence against the client’s supplied common vocabulary list(s).
- Required Output: Only those rewritten sentences that meet a minimum common‑vocabulary percentage threshold (e.g., ≥95% of tokens in the client’s common word list). Target a final curated set of ~500 sentences, optimized for drilling (50/day over ~10 days).

Conclusion:
- The output of Tool 1 (Rewriting) is the input for Tool 2 (Vocabulary Filtering). The structural integrity we just fixed is critical because fragmented sentences cannot be accurately filtered. Our next technical focus is the high‑stakes vocabulary filtering (Tool 2), while retaining the Coverage mode for set‑cover use cases.

---

## Operating Modes

This tool supports two complementary modes that operate on the rewritten sentences produced by Tool 1:

1) Coverage Mode (Set Cover)
- Goal: Select a minimal set of sentences such that each target word (from a chosen word list) appears at least once, with strong preference for per‑word uniqueness across sentences.
- Primary user: Teachers, linguists, or users aiming to guarantee presence of the entire list.

2) Filter Mode (Precision Vocabulary Filter)
- Goal: Return the subset of rewritten sentences whose tokens are predominantly from a chosen high‑frequency list (e.g., ≥95% in‑list), enforce a short length band (4–8 words), and rank to produce ~500 top sentences optimized for drilling.
- Primary user: Stan and learners seeking high‑efficiency auditory repetition, driven by Zipf’s Law.

Both modes share the same ingestion, normalization, and matching pipeline (lemma‑first), but apply different selection criteria and ranking.

---

## Acceptance Criteria (High Level)

General
- Word list management in Settings (upload CSV or import Google Sheet) and ability to set per‑user default; support multiple lists (e.g., 2K, 3K, 5K).
- Executable from Job‑finish CTA, from a History entry, and from a standalone Coverage page; the run records which word list was used.

Coverage Mode
- Lemma‑based matching handles singular/plural nouns and any verb conjugation; alternatives and elisions normalized.
- Selects a compact sentence set; for typical novels, targets < 600 sentences when feasible.
- Per‑word uniqueness enforced “as far as possible,” with diagnostics for duplicates and uncovered words.

Filter Mode (Vocabulary Filter)
- Enforces sentence length band (default 4–8 tokens, configurable).
- Enforces minimum in‑list token ratio per sentence (default ≥95%, configurable).
- Outputs ~500 highest‑quality sentences (configurable target count) for drilling; ranked by frequency, clarity, and diversity (low repetition).
- Exportable to Google Sheets; includes fields suitable for spaced‑repetition or audio drill apps.

Ingestion Reporting
- Lists duplicates, suspected typos, multi‑token decisions, zero‑width character anomalies.
- Does not fail on anomalies; warns and continues with best‑effort normalization.

---

## High‑Level Architecture

- Backend: Flask app, Celery workers, SQLAlchemy, Marshmallow schemas.
- Frontend: Next.js (App Router), React Query, Zustand (or current store), MUI.
- NLP: spaCy `fr_core_news_md` (preferred) with diacritic folding; plus inflection/conjugation table generation; curated irregulars map.
- External: Google Sheets API for import/export with user OAuth.
- Persistence: WordList, CoverageRun, CoverageAssignment, and UserSettings.

---

## Data Models

WordList (new)
- id (PK)
- owner_user_id (nullable; NULL = global/default)
- name (e.g., “French 2K Default”, “French 5K (user)”)
- source_type: 'google_sheet' | 'csv' | 'manual'
- source_ref: string (Sheet ID/URL or file name)
- normalized_count: int
- canonical_samples: JSON (small sample of normalized keys)
- is_global_default: bool
- created_at, updated_at

CoverageRun (updated)
- id, user_id
- mode: 'coverage' | 'filter'
- source_type: 'job' | 'history'
- source_id: int
- wordlist_id: FK WordList.id (nullable; default to user/global)
- config_json: JSON
  - normalize_mode ('lemma' default), ignore_diacritics (true), handle_elisions (true)
  - coverage: alpha, beta, gamma, target_sentence_length, max_sentences, prefer_non_dialogue, topK_per_word_for_ILP
  - filter: min_in_list_ratio (default 0.95), len_min (4), len_max (8), target_count (500), frequency_weighting, diversity_penalty
- status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
- progress_percent: int
- stats_json: JSON (ingestion_report, words_total/deduped/covered/uncovered, selected_count, runtime_ms, filter_acceptance_ratio, diversity metrics)
- created_at, completed_at, error_message

CoverageAssignment
- id, coverage_run_id (FK)
- word_original, word_key, lemma
- matched_surface
- sentence_index, sentence_text, sentence_score
- conflicts: JSON
- manual_edit: bool
- notes

UserSettings (extend)
- default_wordlist_id: FK WordList.id (nullable)
- coverage_defaults_json (including default mode, thresholds)

---

## Word List Ingestion Policy

Inputs
- CSV upload or Google Sheet URL/ID (single column by default; configurable tab/column).
Normalization
- Trim, remove zero‑width chars, split `|` and `/` variants.
- Unicode casefold; fold diacritics (configurable).
- Handle elisions (l’, d’, j’, n’, s’, t’, c’, qu’) → lexical head.
- For multi‑token entries (“Un temps”), default policy extracts head lexical token; flag in report.
- Lemmatize to canonical `word_key`; build alias map (surface → key).
Deduplication
- Deduplicate by `word_key`; keep alias chains; build ingestion_report (duplicates, typos via fuzzy detect, anomalies).
Persistence
- Store WordList metadata and sample keys; optionally persist full normalized list for user lists.

---

## Normalization & Matching Strategy

Default: lemma‑based matching to satisfy singular/plural and verb conjugations.
- Tokenize sentences with spaCy; fold diacritics if enabled; handle elisions; map tokens → lemma → canonical `word_key` via alias map.

Multi‑pass fallback (for robustness)
- Pass 1: lemma lookup (fast).
- Pass 2: inflection table lookup (generated conjugations/plurals).
- Pass 3: conservative fuzzy surface matching (Levenshtein threshold) on remaining words; log confidence.
- Pass 4: human‑in‑the‑loop assignment for any residual.

Confidence & audit trail
- Each match carries source (“lemma”, “inflection”, “fuzzy”) and confidence for later review.

---

## Candidate Generation & Scoring

Sentence constraints (shared)
- Quality filters: length band, non‑dialogue preference, punctuation heuristics.
- Quality score: length proximity to target, clarity/readability, optional metadata (e.g., avoid quoted dialogue if configured).

Coverage Mode scoring
- Gain = number of uncovered target words sentence covers.
- Objective: score = gain − α·duplicate_penalty + β·quality − γ·length_penalty.

Filter Mode scoring
- In‑list ratio r = tokens_in_list / tokens_total.
- Accept sentence if r ≥ min_in_list_ratio (default 0.95) and len_min ≤ tokens_total ≤ len_max (default 4–8).
- Rank accepted sentences by:
  - r (higher is better),
  - frequency weighting (favor higher Zipf‑frequency tokens),
  - diversity penalty (reduce near‑duplicate sentences),
  - clarity/quality score.
- Select top N (default 500; configurable). Provide stable ordering and seed for reproducibility.

---

## Selection Algorithms

Coverage Mode
- Stage 1: Greedy set‑cover (heap + lazy updates).
- Stage 2: Optional ILP (OR‑Tools/pulp) over pruned top‑K candidates per word to minimize selected count and reduce duplicates; time‑capped; fallback to greedy if timeout.
- Stage 3: Uniqueness post‑process; reassign to reduce duplicates; local swaps/hill‑climb.

Filter Mode
- Filter candidates via threshold (min ratio, length band).
- Rank by composite score (ratio + frequency + diversity + quality).
- Pick top N (default 500). Ensure minimal repetition by applying diversity penalty or clustering.

---

## APIs

WordList management
- GET /api/v1/wordlists — list global + user lists
- POST /api/v1/wordlists — create (CSV upload or Sheet URL)
- GET /api/v1/wordlists/:id — detail + ingestion report
- PATCH /api/v1/wordlists/:id — rename/update (owner only)
- DELETE /api/v1/wordlists/:id — delete (owner only)

User settings
- GET /api/v1/user/settings — returns default_wordlist_id, defaults
- PATCH /api/v1/user/settings — update default_wordlist_id, defaults

Coverage runs
- POST /api/v1/coverage/run
  - body: { mode: 'coverage'|'filter', source_type:'job'|'history', source_id:int, wordlist_id?:int, config?:{…} }
  - behavior: use provided wordlist_id, else user default, else global default
- GET /api/v1/coverage/runs/:id — status + summary + paginated assignments
- POST /api/v1/coverage/runs/:id/swap — { word_key, new_sentence_index } (Coverage Mode) or swap/blacklist (Filter Mode)
- POST /api/v1/coverage/runs/:id/reoptimize — local improvements (mode‑specific)
- POST /api/v1/coverage/runs/:id/export — export to Google Sheets (summary + assignments)

Integration hooks
- Job finish CTA → POST /coverage/run with mode, job_id, chosen wordlist
- History page CTA → similar, bound to history_id
- Standalone Coverage page → choose mode, wordlist, and source

---

## Backend Implementation Notes

Models & migrations
- Create WordList; seed canonical “French 2K” as global default.
- Add `mode` and `wordlist_id` to CoverageRun.
- Extend UserSettings with `default_wordlist_id` and defaults JSON.

Services
- WordListService: ingestion, normalization, alias map, ingestion_report, store samples.
- CoverageService:
  - Coverage Mode: indexing, greedy, optional ILP, post‑process.
  - Filter Mode: ratio calculation, ranking, diversity, top‑N selection.
- Linguistics utils: spaCy tokenization/lemmatization, diacritic folding, elisions; conjugation/plural generators; curated irregulars.
- GoogleSheetsService: import/export helpers.

Celery task
- coverage_build_async(run_id): load WordList, normalize sentences, run selected mode, persist assignments and stats, stream progress via WebSocket, handle errors gracefully.

Performance & caching
- Cache normalized keys for WordList; cache sentence tokenization per run (hash).
- Parallelize tokenization; use efficient data structures (sets/bitsets).
- Time‑cap ILP; record approximate flag if fallback used.

---

## Frontend Implementation Notes

Settings page (Vocabulary Coverage)
- WordList management: list global + user lists, upload CSV, import Sheet, set default.
- Show ingestion preview/report before saving.
- Defaults editor: mode, thresholds (min ratio, len band, target count).

Standalone Coverage page (/coverage)
- Mode selector: Coverage | Filter.
- WordList selector (global + user); import/upload affordance.
- Source selector: recent Jobs, History search, or direct ID entry.
- Settings panel: mode‑specific.
- Start Run → progress → results view.

Job finish / History CTAs
- Compact modal with mode, wordlist preview, quick settings; default to Filter Mode for Stan’s flow.

Results UI
- Summary KPIs; ingestion report link.
- Coverage Mode: assignments table per word with swap/reassign.
- Filter Mode: ranked sentence list (4–8 words, ≥95% in‑list), diversity indicators, blacklist/swap options.
- Export to Sheets with tabs: Summary, Selected Sentences (filter) or Assignments (coverage).

---

## Optimization & Hardening (Toward “Bulletproof”)

- Ensemble morphology: spaCy + generated inflections + curated irregulars.
- Multi‑pass matching with confidence scoring.
- Candidate pruning + ILP (Coverage) with time cap + fallback.
- Diversity controls (Filter) to avoid near‑duplicates; optional clustering.
- Human‑in‑the‑loop UI to reach 100% when corpus coverage exists.
- Extensive tests around normalization, ratios, and solver behavior.

---

## Testing Strategy

Backend unit tests
- Ingestion normalization: `|` and `/`, diacritics, elisions, multi‑token headword policy, duplicates, zero‑width chars.
- Morphology: plural nouns and verb conjugations → lemma mapping.
- Coverage Mode: greedy correctness on fixtures; ILP feasibility within caps.
- Filter Mode: ratio computation, ranking stability, diversity penalty behavior.
Backend integration
- WordList CRUD; Settings default; run creation with/without explicit wordlist_id; CTAs.
- End‑to‑end small corpus tests (both modes); export works.
Frontend tests
- Settings flows (upload/import/default).
- Standalone Coverage page flows (modes).
- Results interactions: swap, blacklist, reoptimize, export.

---

## Observability & Metrics

- Metrics:
  - `wordlists_total{owner=global|user}`
  - `coverage_runs_total{status,mode}`
  - `coverage_build_duration_seconds{mode}`
  - `coverage_sentences_selected` (coverage) / `filter_sentences_selected` (filter)
  - `filter_acceptance_ratio` (accepted/total)
- Logs:
  - Ingestion reports, unmatched words, solver timeouts, diversity stats
- Alerts:
  - Repeated failures/timeouts, low acceptance ratio for filter (< threshold), ingestion anomalies spike

---

## Security & Governance

- JWT on all endpoints; ownership checks for WordList CRUD.
- User WordLists private; global lists admin‑managed.
- Rate limits on uploads and runs; sanitize uploads.
- Google OAuth for Sheet access; store only IDs/URLs, not content.

---

## Performance & Scaling

- Typical corpus 5k–15k sentences; word lists up to 5k keys.
- Coverage: greedy + pruned ILP runs within seconds to tens of seconds.
- Filter: linear pass for ratios + ranking; fast; scalable to large corpora with streaming candidates and partial sort.

---

## Rollout Plan

1) MVP (≈1 week)
- WordList model + seed global 2K.
- CSV upload + normalization and Settings default.
- POST /coverage/run with modes ('coverage' initial + 'filter' basic).
- Standalone page, CTAs, basic results, export.

2) Harden (2–3 weeks)
- Inflection tables; multi‑pass matching with confidence.
- ILP optimization for Coverage; diversity/clustering for Filter.
- Ingestion report UI; robust tests and monitoring.

3) Production polish (≈1 week)
- Quotas, retention policies; admin tools for global lists.
- Feature flag rollout and performance tuning.

---

## Deliverables

- Alembic migrations (WordList, CoverageRun updates, UserSettings extension).
- Python services (WordListService, CoverageService, Linguistics utils), Celery task.
- REST endpoints & Marshmallow schemas.
- Frontend Settings page, Standalone Coverage, Job/History CTAs, Results UI.
- Tests (unit/integration/frontend) and dashboards.
- Documentation: user guide (Settings, Coverage vs Filter), API docs.

---

## Risk Summary & Mitigations

- Lemmatizer misses edge cases → ensemble morphology + curated irregulars + tests.
- Solver runtime spikes → prune candidates + time caps + heuristic fallback.
- Data anomalies → ingestion report + user confirmation step.
- UX complexity → clear defaults (Filter Mode for Stan), concise CTAs, progressive disclosure.

---

## Notes on Client‑Driven Defaults (Stan’s Flow)

- Default Mode: Filter.
- Default List: French 2K global (user can pick 3K/5K).
- Default Thresholds: min_in_list_ratio = 0.95; len_min = 4; len_max = 8; target_count = 500.
- Default Ranking: frequency‑weighted with diversity penalty to avoid near‑duplicates.
- Daily Drill Plan: export 500 sentences; user drills 50/day for ~10 days (supports spreadsheet tabs or tags for batching).

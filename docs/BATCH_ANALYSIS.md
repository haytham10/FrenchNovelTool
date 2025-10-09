# Batch Analysis Mode - Feature Documentation

## Overview

The **Batch Analysis** feature implements a sequential, multi-source vocabulary coverage workflow. Instead of processing all novels together in one large pool, it processes them one at a time like a "smart assembly line," ensuring maximum efficiency and guaranteeing optimal coverage with a minimal final sentence set.

## How It Works

### The Algorithm

1. **Starting Point**: Begins with the full target wordlist (e.g., 2000 words) and an ordered list of selected novels.

2. **First Pass (Novel A)**:
   - Runs coverage mode on Novel A
   - Selects sentences that cover the easiest/most common words
   - Example: Selects 350 sentences covering 1200 words
   - Saves these sentences and updates remaining words to 800

3. **Second Pass (Novel B)**:
   - Runs coverage mode on Novel B
   - **Only searches for the 800 remaining uncovered words**
   - Completely ignores the 1200 already-covered words
   - Example: Selects 120 sentences covering 750 of the remaining words
   - Updates remaining words to 50

4. **Final Pass (Novel C)**:
   - Runs coverage mode on Novel C
   - Searches only for the last 50 remaining words
   - Example: Selects 30 sentences covering all final words

5. **Result Assembly**:
   - Combines all selected sentences (350 + 120 + 30 = 500 total)
   - Presents as a single "Learning Set"
   - Provides detailed breakdown showing each source's contribution

## User Experience

### Selection
- Navigate to the Vocabulary Coverage Tool
- In Step 2 "Select Source", toggle **Batch Analysis Mode** switch
- Select multiple novels using checkboxes (minimum 2 required)
- A chip displays the count of selected sources

### Execution
- Click the **"Run Batch Analysis"** button
- The system processes novels sequentially in the background
- Progress updates show which source is being processed

### Results
- Single combined Learning Set with all selected sentences
- **Batch Analysis Summary** card showing:
  - Total sources processed
  - Coverage breakdown per source
  - Words covered by each novel
  - Sentences selected from each source

## Technical Implementation

### Backend

**Schema** (`backend/app/schemas.py`):
- Extended `CoverageRunCreateSchema` to accept `source_ids` array
- Added validation to ensure batch mode has minimum 2 sources

**Service** (`backend/app/services/coverage_service.py`):
- New method: `batch_coverage_mode(sources, progress_callback)`
- Implements sequential processing with shrinking wordlist
- Returns combined assignments and detailed statistics

**Task** (`backend/app/tasks.py`):
- New Celery task: `batch_coverage_build_async(run_id)`
- Fetches sentences from multiple sources
- Calls `batch_coverage_mode` and stores results
- Emits progress via WebSocket

**API** (`backend/app/coverage_routes.py`):
- Modified `create_coverage_run` endpoint
- Stores `source_ids` in `config_json` for batch mode
- Charges credits per source (fairness: batch mode costs more)
- Dispatches to `batch_coverage_build_async` task

### Frontend

**UI** (`frontend/src/app/coverage/page.tsx`):
- Batch mode toggle switch with descriptive label
- Checkbox selection for multiple history items
- Selected count chip
- Batch-specific button text and descriptions
- Results display with source breakdown

**API Client** (`frontend/src/lib/api.ts`):
- Extended `createCoverageRun` to accept `source_ids` array
- Supports mode `'batch'` in addition to `'coverage'` and `'filter'`

### Data Model

**CoverageRun**:
- Mode can be `'coverage'`, `'filter'`, or `'batch'`
- For batch mode, `config_json` contains `source_ids` array
- `source_id` field stores the first source ID for indexing

**Stats JSON** (batch mode):
```json
{
  "mode": "batch",
  "sources_count": 3,
  "sources_processed": 3,
  "words_total": 2000,
  "words_covered": 2000,
  "uncovered_words": 0,
  "coverage_percentage": 100.0,
  "selected_sentence_count": 500,
  "source_breakdown": [
    {
      "source_id": 1,
      "source_index": 0,
      "sentences_count": 5000,
      "selected_sentences": 350,
      "words_covered": 1200,
      "words_remaining": 800
    },
    {
      "source_id": 2,
      "source_index": 1,
      "sentences_count": 3000,
      "selected_sentences": 120,
      "words_covered": 750,
      "words_remaining": 50
    },
    {
      "source_id": 3,
      "source_index": 2,
      "sentences_count": 2000,
      "selected_sentences": 30,
      "words_covered": 50,
      "words_remaining": 0
    }
  ]
}
```

## Benefits

### Efficiency
- **Targeted Search**: Each novel only searches for words not yet covered
- **No Redundancy**: Avoids selecting multiple sentences for the same word
- **Optimal Size**: Minimal final sentence set for maximum coverage

### Transparency
- **Source Attribution**: Know which novel contributed which sentences
- **Progress Tracking**: See sequential reduction of uncovered words
- **Decision Support**: Understand the value of each source in the batch

### Flexibility
- **Order Matters**: Process novels in order of availability or difficulty
- **Partial Coverage**: System handles cases where full coverage isn't possible
- **Graceful Degradation**: Continues if a source is empty or unavailable

## Use Cases

1. **Language Learning Materials**:
   - Process multiple novels to build a comprehensive learning set
   - Ensure exposure to words across different contexts
   - Track which novels contribute most to vocabulary coverage

2. **Curriculum Development**:
   - Select texts that complement each other
   - Minimize overlap while maximizing coverage
   - Create efficient reading lists

3. **Research**:
   - Analyze vocabulary distribution across multiple texts
   - Study how different genres contribute to word coverage
   - Optimize corpus selection for linguistic studies

## Credit Costs

- **Single Mode**: 1 credit per run
- **Batch Mode**: 1 credit per source (e.g., 3 sources = 3 credits)
- This ensures fairness as batch mode processes multiple sources

## Limitations

- **Minimum 2 Sources**: Batch mode requires at least 2 novels
- **Sequential Processing**: Sources are processed one at a time
- **Memory**: Very large batches may require more processing time
- **Order Dependent**: The order of sources affects which sentences are selected

## Future Enhancements

Potential improvements for batch mode:

1. **Smart Ordering**: Automatically order sources by estimated difficulty or word frequency
2. **Preview Mode**: Show expected contribution before running
3. **Source Weighting**: Allow users to prioritize certain sources
4. **Partial Runs**: Support resuming interrupted batch runs
5. **Export Breakdown**: Export learning set with source annotations

## Testing

The batch analysis feature includes comprehensive tests:

- **Unit Tests** (`backend/tests/test_batch_coverage.py`):
  - Basic batch coverage with two sources
  - Sequential word reduction verification
  - Empty source handling
  - Comparison with single-source mode

- **Standalone Tests** (`backend/test_batch_standalone.py`):
  - Three-novel simulation
  - Edge cases
  - Coverage percentage verification

All tests verify:
- Sequential word reduction
- Combined result accuracy
- Source breakdown correctness
- Edge case handling

## Summary

The Batch Analysis feature provides an intelligent, efficient way to process multiple novels for vocabulary coverage. By processing sources sequentially with a shrinking target wordlist, it ensures optimal coverage with minimal redundancy, making it perfect for creating comprehensive language learning materials.

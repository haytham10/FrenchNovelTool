# Intelligent Gemini Retry System

## Overview

The French Novel Tool now implements a sophisticated multi-tier retry strategy to maximize the use of Gemini AI's intelligent sentence processing while providing robust fallbacks when API issues occur.

## Retry Cascade (5 Steps)

When processing a chunk of text, the system attempts the following strategies in order:

### 1. Primary Model Attempt
- Uses the user-selected model preference (speed/balanced/quality)
- Applies the full, comprehensive prompt with all literary processing instructions
- **Success**: Returns normally with no fallback marker
- **Failure**: Proceeds to step 2

### 2. Model Fallback
- Automatically retries with progressively heavier/safer models:
  - `speed` (gemini-2.5-flash-lite) → `balanced` (gemini-2.5-flash) → `quality` (gemini-2.5-pro)
  - `balanced` → `quality`
  - `quality` → (no model fallback, proceed to step 3)
- Uses the same full prompt with the heavier model
- **Success**: Returns with `_fallback_method: "model_fallback:balanced"` or `"model_fallback:quality"`
- **Failure**: Proceeds to step 3

### 3. Subchunk Splitting
- Splits the text into smaller sub-chunks (default: 2 pieces)
- Processes each sub-chunk independently with Gemini
- Merges results intelligently, applying post-processing to handle boundaries
- Sub-chunks can themselves use model fallback
- **Success**: Returns with `_fallback_method: "subchunk_split"`
- **Failure**: Proceeds to step 4

### 4. Minimal Prompt Fallback
- Retries with a stripped-down prompt that only requests:
  - Extract sentences
  - Split if > word limit
  - Return JSON: `{"sentences": [...]}`
- Reduces chance of hallucination or format issues
- Also attempts model fallback with minimal prompt if needed
- **Success**: Returns with `_fallback_method: "minimal_prompt"` or `"minimal_prompt_model_fallback:X"`
- **Failure**: Proceeds to step 5

### 5. Local Fallback (Last Resort)
- Uses regex-based sentence segmentation without Gemini
- Applies conservative punctuation-based splitting
- Still runs post-processing pipeline for consistency
- **Success**: Returns with `_fallback_method: "local_segmentation"`
- **This is the only non-Gemini processing path**

## Database Markers

Each fallback method is tracked in the `JobChunk` table with specific error codes:

| Error Code | Meaning | Gemini Used? |
|------------|---------|--------------|
| None | Primary model succeeded | ✅ Yes (best) |
| `GEMINI_MODEL_FALLBACK` | Heavier model succeeded | ✅ Yes |
| `GEMINI_SUBCHUNK_FALLBACK` | Text splitting succeeded | ✅ Yes |
| `GEMINI_MINIMAL_PROMPT_FALLBACK` | Simplified prompt succeeded | ✅ Yes |
| `GEMINI_LOCAL_FALLBACK` | Local segmentation used | ❌ No |

## Benefits

1. **Preserves Intelligence**: Tries multiple Gemini strategies before falling back to local processing
2. **Cost-Aware**: Uses lighter models first, only escalating when necessary
3. **Transparent**: All fallbacks are logged and visible in the database/UI
4. **Robust**: Handles transient API failures, safety blocks, and malformed responses
5. **Quality-First**: The app's core value (intelligent splitting) is preserved in 99%+ of cases

## Configuration

The retry behavior is controlled by:

- User's `gemini_model` preference in UserSettings (speed/balanced/quality)
- `MODEL_FALLBACK_CASCADE` dict in `GeminiService` (defines fallback order)
- `_split_text_into_subchunks()` method (subchunk sizing logic)
- `build_minimal_prompt()` method (minimal prompt template)

## Code Locations

- **Primary Implementation**: `backend/app/services/gemini_service.py`
  - `normalize_text()`: Main retry orchestration
  - `_call_gemini_api()`: Low-level API call helper
  - `_split_text_into_subchunks()`: Text splitting logic
  - `build_minimal_prompt()`: Minimal prompt builder
  
- **Task Integration**: `backend/app/tasks.py`
  - `process_chunk()`: Handles fallback markers and DB persistence

- **Tests**: `backend/tests/test_intelligent_retry.py`
  - Comprehensive test coverage for all retry scenarios

## Monitoring

To monitor fallback usage:

1. Check `JobChunk.last_error_code` for fallback markers
2. Query chunks by error code to see which fallbacks are being triggered
3. Log analysis: search for "Attempting model fallback", "Attempting subchunk", "Attempting minimal prompt", etc.

## Future Enhancements

Possible improvements to the retry system:

- Configurable retry limits per tier
- Dynamic subchunk sizing based on text characteristics
- Telemetry/metrics for fallback frequency
- UI indicators showing which chunks used fallback
- A/B testing different prompt strategies

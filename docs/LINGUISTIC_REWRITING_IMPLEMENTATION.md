# Linguistic Rewriting Implementation

## Overview

This document explains the transformation of the text processing system from **segmentation-based chunking** to **linguistic rewriting** using AI-powered paraphrasing.

## The Problem: Segmentation vs. Rewriting

### What Was Happening (Segmentation)

The original system was performing **text segmentation** - splitting sentences at natural break points (commas, conjunctions, prepositional phrases) to meet word limits. This created grammatically incomplete fragments:

**Examples of Segmentation Output (WRONG):**
```
❌ "le standard d'Elvis Presley"
❌ "It's Now or Never"
❌ "dans la rue sombre"
❌ "et froide"
❌ "Pour toujours et à jamais"
❌ "Avec le temps"
❌ "Dans quinze ans"
❌ "De retour dans la chambre"
```

These are **sentence fragments** - grammatically incomplete phrases that cannot stand alone.

### What We Need (Linguistic Rewriting)

**Linguistic rewriting** transforms complex sentences into multiple complete, independent, grammatically correct sentences:

**Examples of Rewriting Output (CORRECT):**
```
✅ "Le standard d'Elvis Presley joue à la radio."
✅ "La chanson It's Now or Never résonne."
✅ "La rue était sombre."
✅ "Il faisait froid."
✅ "Ils s'aimeront pour toujours."
✅ "Le temps passera lentement."
✅ "Dans quinze ans, ce sera différent."
✅ "Il est retourné dans la chambre."
```

## Implementation Strategy

### 1. Enhanced AI Prompt (`GeminiService.build_prompt()`)

The prompt has been completely redesigned to:

#### Emphasize Zero Tolerance for Fragments
```
🚫 CRITICAL CONSTRAINT: ZERO TOLERANCE FOR FRAGMENTS
ABSOLUTE RULE: Every output sentence MUST be a complete, independent, 
grammatically correct sentence.
```

#### Provide Explicit Examples
The prompt now includes side-by-side comparisons of WRONG vs. CORRECT approaches:

```
❌ WRONG (Segmentation):
   Input: "Il marchait lentement dans la rue sombre et froide, pensant à elle."
   Output: ["dans la rue sombre", "et froide", "pensant à elle"]

✅ CORRECT (Rewriting):
   Input: "Il marchait lentement dans la rue sombre et froide, pensant à elle."
   Output: ["Il marchait lentement dans la rue.", 
            "La rue était sombre et froide.", 
            "Il pensait à elle."]
```

#### Enforce Grammatical Completeness
Every sentence must pass these tests:
- ✓ Has a SUBJECT (explicit or understood)
- ✓ Has a CONJUGATED VERB (not just infinitive/participle)
- ✓ Expresses a COMPLETE THOUGHT
- ✓ Can stand alone with ZERO context
- ✓ Proper punctuation (. ! ? …)
- ✓ Correct word count range

### 2. Enhanced Fragment Detection (`_is_likely_fragment()`)

The fragment detector now identifies more patterns:

#### Patterns Detected as Fragments

1. **Prepositional phrases without verbs**
   - Starting with: dans, sur, avec, sans, pour, de, à, vers, chez, par
   - Must contain conjugated verb to be valid

2. **Conjunction starts without completion**
   - Starting with: et, mais, donc, car, or, ni, puis
   - Must have proper length and punctuation

3. **Temporal expressions without clauses**
   - Starting with: quand, lorsque, pendant, durant, avant, après, depuis
   - Too short to be complete sentences

4. **Relative pronouns without main clause**
   - Starting with: qui, que, dont, où, lequel, laquelle

5. **Participle phrases without auxiliaries**
   - Past participles without être/avoir
   - Present participles without context

#### Enhanced Verb Detection

The system now recognizes a wider range of French verb forms:
```python
# Verb endings checked:
- Infinitives: -er, -ir, -oir, -re
- Imperfect: -ais, -ait, -aient, -iez, -ions
- Present/Past: -ai, -as, -a, -ont, -ez
- Future: -era, -erai, -eras, -erez, -eront
- Past participles: -é, -ée, -és, -ées

# Common auxiliary verbs:
- est, sont, était, étaient, sera, seront
- a, ont, avait, avaient, aura, auront
- fut, furent, soit, soient, fût
```

### 3. Quality Assessment (`_post_process_sentences()`)

#### Fragment Rate Monitoring
The system now tracks:
- Total fragments detected
- Fragment rate (percentage)
- Sample fragments for debugging

#### Quality Thresholds
```python
if fragment_rate > 5.0:  # More than 5% is concerning
    logger.error('HIGH FRAGMENT RATE - AI performing SEGMENTATION not REWRITING')
```

#### Detailed Logging
```
Fragment detection summary: 15 potential fragments out of 639 sentences (2.3%)
Sample fragments (first 5): 
  - "Dans quinze ans, ce sera moi."
  - "Pour toujours et à jamais."
  - "Avec le temps."
```

### 4. Updated Minimal Prompt

Even the fallback prompt emphasizes complete sentences:
```
Rewrite this French text into complete, grammatically correct sentences.
Each sentence must be independent and have {min}-{max} words.
For long sentences, REWRITE them into multiple complete sentences with subject and verb.
DO NOT create fragments or dependent clauses.
```

## Testing & Validation

### How to Test if Rewriting is Working

1. **Run a processing job and check logs:**
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f backend | grep "Fragment detection"
   ```

2. **Look for fragment rate:**
   - Target: < 2% fragments
   - Warning level: 2-5% fragments
   - Error level: > 5% fragments

3. **Examine sample output:**
   - Every sentence should be grammatically complete
   - Test: Can you understand each sentence without context?
   - Test: Does each sentence have a subject and verb?

### Example Quality Check

**Input Text:**
```
Il marchait lentement dans la rue sombre et froide, pensant à elle 
constamment depuis leur séparation brutale il y a trois mois.
```

**Expected Rewriting Output (GOOD):**
```json
{
  "sentences": [
    "Il marchait lentement dans la rue.",
    "La rue était sombre et froide.",
    "Il pensait à elle constamment.",
    "Leur séparation avait été brutale.",
    "C'était il y a trois mois."
  ]
}
```

**Segmentation Output (BAD):**
```json
{
  "sentences": [
    "dans la rue sombre",
    "et froide",
    "pensant à elle constamment",
    "depuis leur séparation brutale",
    "il y a trois mois"
  ]
}
```

## Configuration

### Environment Variables

- `GEMINI_ALLOW_LOCAL_FALLBACK`: Set to `false` to prevent local segmentation fallback
  - Default: `false`
  - When disabled, API failures will raise errors instead of falling back to basic segmentation

### User Settings

In `UserSettings` model:
- `sentence_length_limit`: Maximum words per sentence (default: 8)
- `min_sentence_length`: Minimum words per sentence (default: 2)
- `model_preference`: AI model to use (speed/balanced/quality)
- `ignore_dialogue`: Whether to preserve dialogue unchanged

## Architecture Changes

### Modified Files

1. **`backend/app/services/gemini_service.py`**
   - `build_prompt()`: Complete rewrite with explicit rewriting instructions
   - `build_minimal_prompt()`: Updated for rewriting focus
   - `_is_likely_fragment()`: Enhanced detection with more patterns
   - `_post_process_sentences()`: Added quality assessment and reporting
   - `_split_sentence()`: Now warns instead of manually splitting

2. **`docs/LINGUISTIC_REWRITING_IMPLEMENTATION.md`** (this file)
   - Complete documentation of the transformation

### Removed/Disabled Features

- **Manual sentence splitting in `_split_sentence()`**: Disabled to prevent fragmentation
  - The method now only validates and warns
  - Trust the AI model to handle rewriting

## Expected Outcomes

### Before (Segmentation)
```
Fragment rate: 10-20%
Many incomplete phrases
Word limit: Met perfectly (but with fragments)
Readability: Poor (fragments hard to understand)
```

### After (Linguistic Rewriting)
```
Fragment rate: < 2%
Complete sentences only
Word limit: Met with complete thoughts
Readability: High (each sentence understandable)
```

## Monitoring

### Key Metrics to Watch

1. **Fragment Rate**
   - Monitor in logs during processing
   - Alert if > 5%

2. **Word Limit Violations**
   - AI should respect limits while maintaining completeness
   - Some flexibility acceptable if sentence cannot be simplified further

3. **User Feedback**
   - Do exported Google Sheets have readable, complete sentences?
   - Can users understand each sentence independently?

## Troubleshooting

### High Fragment Rate (> 5%)

**Possible causes:**
1. AI model not following prompt instructions
2. Prompt needs further refinement
3. Model preference set too low (try 'quality' instead of 'speed')

**Solutions:**
1. Check model preference in user settings
2. Try with `gemini-2.5-pro` (quality model)
3. Review prompt effectiveness
4. Consider adding more examples to prompt

### Sentences Exceeding Word Limit

**Expected behavior:**
- Some sentences may slightly exceed limit if:
  - Simplification would create fragments
  - The thought cannot be split further
  - Dialogue preservation is enabled

**Solutions:**
1. Log warnings (already implemented)
2. Review if word limit is too restrictive
3. Check if dialogue is being processed correctly

### AI Still Producing Fragments

**Immediate actions:**
1. Check logs for fragment samples
2. Identify common patterns in fragments
3. Add those patterns to `_is_likely_fragment()`
4. Update prompt with explicit examples of those fragments

## Future Enhancements

### Potential Improvements

1. **Automatic Retry on High Fragment Rate**
   - If fragment rate > 5%, automatically retry with stricter prompt
   - Implement in `normalize_text()` method

2. **Fragment Auto-Correction**
   - Attempt to merge fragments with adjacent sentences
   - Add subjects/verbs to fragments automatically

3. **Quality Scoring**
   - Calculate quality score based on:
     - Fragment rate
     - Word limit compliance
     - Grammatical completeness
   - Store score in job metadata

4. **A/B Testing**
   - Compare different prompt variations
   - Track which prompts produce lowest fragment rates

5. **User Feedback Loop**
   - Allow users to report fragments
   - Use feedback to improve prompts

## References

- **Main implementation**: `backend/app/services/gemini_service.py`
- **Project instructions**: `.github/copilot-instructions.md`
- **API documentation**: `backend/API_DOCUMENTATION.md`
- **Development guide**: `DEVELOPMENT.md`

## Conclusion

The shift from segmentation to linguistic rewriting is critical for the app's core mission: producing readable, linguistically pure French text within word limits. The enhanced prompt, robust fragment detection, and quality assessment ensure the AI performs true rewriting instead of simple chunking.

**Success Criteria:**
- ✅ Fragment rate < 2%
- ✅ Every sentence grammatically complete
- ✅ Word limits respected
- ✅ Original meaning preserved
- ✅ High readability

By enforcing these standards, the system now produces output that meets the app's true purpose: simplifying French novels into complete, understandable sentences suitable for language learners.

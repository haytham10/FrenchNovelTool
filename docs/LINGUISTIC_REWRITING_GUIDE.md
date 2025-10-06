# Linguistic Rewriting vs Segmentation - Implementation Guide

## Background

The French Novel Tool previously performed **segmentation/chunking** - splitting sentences at punctuation boundaries to meet word limits. This resulted in grammatically incorrect fragments such as:
- "le standard d'Elvis Presley,"
- "et froide"
- "dans la rue sombre"

These are dependent phrases, not complete sentences.

## Solution: Linguistic Rewriting

The system now performs **linguistic rewriting** - using AI to paraphrase complex sentences into complete, independent, grammatically correct sentences.

## How It Works

### 1. Prompt Instructions (build_prompt)

The AI model receives explicit instructions:

```
**CRITICAL: Linguistic Rewriting, NOT Segmentation**

Your goal is to produce a list of complete, independent, grammatically 
correct sentences where EACH sentence does not exceed N words.

**Core Instruction:**
- If a sentence is N words or shorter: keep it as-is
- If a sentence exceeds N words: REWRITE and PARAPHRASE it into multiple complete sentences
- Do NOT simply split at commas, conjunctions, or punctuation marks
- Each output sentence MUST be linguistically complete, independent, and grammatically pure
- FORBIDDEN: sentence fragments, dependent clauses, or incomplete thoughts as standalone sentences
```

### 2. Concrete Examples

The prompt includes examples of what NOT to do vs what to do:

```
Example of WRONG approach (segmentation): 
  splitting 'Il marchait lentement dans la rue sombre et froide' 
  into 'dans la rue sombre' and 'et froide'

Example of CORRECT approach (rewriting): 
  'Il marchait lentement dans la rue. La rue était sombre et froide.'
```

### 3. Quality Requirements

```
**Quality Requirements:**
- Every output sentence MUST be grammatically complete and able to stand alone
- NO dependent phrases like 'le standard d'Elvis Presley' or 'It's Now or Never' without context
- NO fragments that begin with conjunctions (et, mais, donc) unless they form complete imperative sentences
- Each sentence must convey a complete idea that a reader can understand independently
```

### 4. No Manual Chunking

The `_split_sentence()` method previously performed manual chunking at punctuation boundaries. This has been **disabled** - the method now:
- Returns the sentence as-is (trusts AI model)
- Only logs a warning if sentence exceeds word limit
- Does NOT create fragments through manual splitting

### 5. Fragment Detection

The `_is_likely_fragment()` method detects common fragment patterns:

1. **Sentences ending with comma**: `"le standard d'Elvis Presley,"`
2. **Conjunction starts without completion**: `"et froide"` (too short, improper ending)
3. **Prepositional phrases without verbs**: `"dans la rue sombre"` (no verb)

Detected fragments trigger warnings in logs for quality monitoring.

## Example Transformation

### Input
```
"Il marchait lentement dans la rue sombre et froide, pensant à sa vie passée."
(16 words - exceeds 8 word limit)
```

### OLD Output (Segmentation) ❌
```
1. Il marchait lentement dans la rue sombre
2. et froide,
3. pensant à sa vie passée.
```
**Problem**: Sentences 2 and 3 are fragments!

### NEW Output (Linguistic Rewriting) ✓
```
1. Il marchait lentement dans la rue.
2. La rue était sombre et froide.
3. Il pensait à sa vie passée.
```
**Success**: All three are complete, independent, grammatically correct sentences!

## Testing

### Fragment Detection Test
```python
service = GeminiService(sentence_length_limit=8)

# Fragments that should be detected
assert service._is_likely_fragment("et froide,")  # True
assert service._is_likely_fragment("le standard d'Elvis Presley,")  # True

# Complete sentences that should NOT be flagged
assert not service._is_likely_fragment("Il marchait dans la rue.")  # False
assert not service._is_likely_fragment("La rue était sombre.")  # False
```

### Prompt Verification Test
```python
prompt = service.build_prompt()
assert "CRITICAL: Linguistic Rewriting, NOT Segmentation" in prompt
assert "Do NOT simply split at commas, conjunctions" in prompt
assert "REWRITE and PARAPHRASE" in prompt
assert "FORBIDDEN: sentence fragments" in prompt
```

## Monitoring

The system logs fragment detection warnings:

```
WARNING: Potential sentence fragment detected at index 5: "et froide,"
WARNING: Fragment detection summary: 2 potential fragments found out of 45 sentences (4.4%)
```

Monitor these logs to:
- Assess AI model compliance with instructions
- Identify when the model isn't following rewriting rules
- Track quality metrics over time

## Configuration

No configuration changes needed. The transformation is achieved through:
1. Updated prompt instructions (automatic)
2. Disabled manual chunking (automatic)
3. Fragment detection (always active)

## Deployment

- ✅ No database migrations required
- ✅ No API changes required
- ✅ Backward compatible
- ✅ Existing documents can be reprocessed

## Success Metrics

Track these metrics to evaluate effectiveness:

1. **Fragment Rate**: Target <5% (from logs)
2. **User Feedback**: Reduction in grammar complaints
3. **AI Compliance**: Sentences within word limit (from warnings)
4. **Manual Review**: Spot-check output quality

## Troubleshooting

### High fragment rate in logs
- AI model may not be following instructions
- Consider using higher-quality model (gemini-2.5-pro)
- Review and enhance prompt if needed

### False positives in fragment detection
- Heuristics may flag valid constructions
- Review specific cases and update `_is_likely_fragment()` logic
- Fragment detection is for monitoring only, doesn't block output

### Sentences still exceeding word limit
- AI model not strictly following limit
- Check logs for specific warnings
- May need to strengthen prompt instructions

## Files Modified

1. `backend/app/services/gemini_service.py`
   - `build_prompt()` - Linguistic rewriting instructions
   - `_split_sentence()` - Disabled manual chunking
   - `_is_likely_fragment()` - Fragment detection (new)
   - `_post_process_sentences()` - Fragment logging

2. `backend/tests/test_prompt_improvements.py`
   - Updated tests for new prompt structure
   - Added fragment detection tests

3. `backend/tests/test_services.py`
   - Updated prompt verification test

## Further Reading

- Original issue: Problem statement describing segmentation vs rewriting
- Test files: `test_prompt_improvements.py` for examples
- Implementation: `gemini_service.py` for full code

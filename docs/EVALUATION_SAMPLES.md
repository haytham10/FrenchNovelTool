# Phase 1 Evaluation Samples

This document contains sample French text inputs to evaluate the effectiveness of the Phase 1 prompt improvements.

## Test Sample 1: Long Narrative Sentence with Conjunctions

### Input
```
Le jeune homme marchait lentement dans la rue sombre et froide, pensant à sa vie passée 
et aux choix qu'il avait faits durant toutes ces années difficiles qui l'avaient mené 
jusqu'à ce moment précis.
```

### Word Count
28 words (exceeds 8-word limit significantly)

### Expected Behavior
- Split at natural conjunction points ('et')
- Maintain chronological and logical flow
- Preserve all French words and literary tone
- Each resulting sentence should be ≤8 words or close to it

### Expected Good Output
```json
{
  "sentences": [
    "Le jeune homme marchait lentement dans la rue.",
    "Elle était sombre et froide.",
    "Il pensait à sa vie passée.",
    "Il pensait aux choix qu'il avait faits.",
    "Ces années difficiles l'avaient mené jusqu'ici."
  ]
}
```

### What to Avoid
- Breaking in the middle of "sa vie passée" (compound object)
- Losing pronoun references (Il/Elle)
- Modern phrasing like "Il se rappelait" instead of "pensant"

---

## Test Sample 2: Dialogue with Attribution

### Input
```
« Je ne comprends pas pourquoi tu es parti sans dire au revoir à personne dans cette 
maison où nous avons grandi ensemble, » dit-elle tristement en regardant par la fenêtre.
```

### Word Count
27 words (exceeds limit)

### Expected Behavior
- Keep dialogue intact if possible (priority: do not split dialogue)
- If must split, separate attribution from dialogue
- Maintain quotation marks (guillemets)
- Preserve emotional tone ("tristement")

### Expected Good Output (Dialogue Preserved)
```json
{
  "sentences": [
    "« Je ne comprends pas pourquoi tu es parti sans dire au revoir à personne, » dit-elle.",
    "Elle regardait tristement par la fenêtre.",
    "Ils avaient grandi ensemble dans cette maison."
  ]
}
```

### Alternative Output (If Split Required)
```json
{
  "sentences": [
    "« Je ne comprends pas pourquoi tu es parti. »",
    "« Tu n'as dit au revoir à personne, » dit-elle.",
    "Elle regardait tristement par la fenêtre.",
    "Ils avaient grandi ensemble dans cette maison."
  ]
}
```

### What to Avoid
- Breaking dialogue mid-sentence arbitrarily
- Losing quotation marks
- Changing "dit-elle" to "elle a dit" (maintain literary style)

---

## Test Sample 3: Context-Dependent Sequence

### Input (3 sentences)
```
Marie ouvrit la porte avec hésitation. Elle aperçut une silhouette immobile dans 
l'obscurité profonde qui régnait dans le couloir sombre et inquiétant de la vieille 
demeure abandonnée. La silhouette s'avança lentement vers elle.
```

### Word Count
- Sentence 1: 5 words ✓ (keep as-is)
- Sentence 2: 19 words ✗ (needs splitting)
- Sentence 3: 5 words ✓ (keep as-is)

### Expected Behavior
- Keep sentences 1 and 3 unchanged
- Split sentence 2 while maintaining context
- Preserve pronoun references (elle, la silhouette)
- Maintain suspenseful tone

### Expected Good Output
```json
{
  "sentences": [
    "Marie ouvrit la porte avec hésitation.",
    "Elle aperçut une silhouette dans l'obscurité profonde.",
    "L'obscurité régnait dans le couloir sombre.",
    "C'était une vieille demeure abandonnée.",
    "La silhouette s'avança lentement vers elle."
  ]
}
```

### What to Avoid
- Changing "Marie" to "Elle" in the first sentence (lose subject)
- Breaking "la silhouette" reference chain
- Simplifying "demeure" to "maison" (maintain formal vocabulary)

---

## Test Sample 4: Short Sentences (No Changes Needed)

### Input
```
Il pleuvait. La rue était déserte. Jean marchait seul. Il pensait à Marie.
```

### Word Count
- All sentences ≤ 4 words

### Expected Behavior
- Return all sentences unchanged
- Maintain original punctuation and structure

### Expected Output
```json
{
  "sentences": [
    "Il pleuvait.",
    "La rue était déserte.",
    "Jean marchait seul.",
    "Il pensait à Marie."
  ]
}
```

---

## Test Sample 5: Mixed Dialogue and Narrative

### Input
```
« Viens avec moi, » murmura-t-il doucement. Marie hésita un instant avant de répondre 
qu'elle ne pouvait pas abandonner tout ce qu'elle avait construit ici pendant ces 
longues années de travail acharné et de sacrifices personnels.
```

### Word Count
- Sentence 1: 5 words ✓ (dialogue, keep as-is)
- Sentence 2: 27 words ✗ (needs splitting)

### Expected Behavior
- Keep dialogue intact (sentence 1)
- Split long narrative response naturally
- Maintain cause-effect relationship
- Preserve formal tone

### Expected Good Output
```json
{
  "sentences": [
    "« Viens avec moi, » murmura-t-il doucement.",
    "Marie hésita un instant avant de répondre.",
    "Elle ne pouvait pas abandonner tout.",
    "Elle avait construit cela ici pendant des années.",
    "C'était des années de travail acharné.",
    "C'était des années de sacrifices personnels."
  ]
}
```

### What to Avoid
- Splitting the dialogue (sentence 1)
- Losing the hesitation detail
- Modernizing "travail acharné" to "dur travail"

---

## Test Sample 6: Descriptive Passage with Multiple Clauses

### Input
```
Le soleil, qui brillait intensément dans le ciel bleu et sans nuages, illuminait 
la petite place du village où les enfants jouaient joyeusement sans se soucier 
des problèmes du monde adulte.
```

### Word Count
32 words (needs significant splitting)

### Expected Behavior
- Identify the relative clause "qui brillait..."
- Split at natural points (commas, où)
- Maintain descriptive richness
- Preserve parallel structure (children playing / not worrying)

### Expected Good Output
```json
{
  "sentences": [
    "Le soleil brillait intensément dans le ciel.",
    "Le ciel était bleu et sans nuages.",
    "Il illuminait la petite place du village.",
    "Les enfants y jouaient joyeusement.",
    "Ils ne se souciaient pas des problèmes adultes."
  ]
}
```

### What to Avoid
- Breaking "bleu et sans nuages" (compound description)
- Losing the carefree tone
- Over-simplifying to "Les enfants jouaient"

---

## Evaluation Criteria

When testing with these samples, verify:

1. **Grammatical Correctness** ✓
   - Each sentence is grammatically complete
   - No dangling clauses or fragments

2. **Context Preservation** ✓
   - Pronoun references maintained
   - Logical flow preserved
   - Chronological order intact

3. **Dialogue Integrity** ✓
   - Dialogue kept intact when possible
   - Quotation marks preserved
   - Attribution maintained

4. **Style Consistency** ✓
   - Literary vocabulary retained
   - Formal tone maintained
   - No anachronisms or modern idioms

5. **JSON Validity** ✓
   - Valid JSON structure
   - "sentences" array present
   - All strings properly escaped

6. **Word Count Compliance** ✓
   - Short sentences unchanged
   - Long sentences split appropriately
   - Target limit respected (with reasonable flexibility for dialogue)

---

## Testing Instructions

To test these samples:

1. Upload a PDF containing these text samples
2. Process through the API endpoint
3. Compare output against expected results
4. Check for:
   - Grammatical correctness
   - Context preservation
   - Dialogue handling
   - Style maintenance
   - JSON validity

## Success Metrics

- **Quality**: 90%+ sentences maintain literary style
- **Accuracy**: 95%+ grammatically correct splits
- **Dialogue**: 100% dialogue preserved or split appropriately
- **JSON**: 99%+ valid JSON responses
- **Context**: 85%+ maintain logical flow across splits

---

## Notes

These samples represent common patterns in French literature:
- **Sample 1**: Complex narrative with internal thoughts
- **Sample 2**: Dialogue with emotional context
- **Sample 3**: Suspenseful sequential narrative
- **Sample 4**: Terse, dramatic style (already optimal)
- **Sample 5**: Mixed dialogue and complex response
- **Sample 6**: Rich descriptive passage

The improved prompt should handle all these cases gracefully while maintaining the literary quality of the original text.

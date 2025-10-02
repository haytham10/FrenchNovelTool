# Rewriting Algorithm Improvement Roadmap

This document outlines a phased approach to enhance the sentence rewriting algorithm used in the French Novel Tool. The goal is to move from a simple, length-based mechanical process to a more sophisticated, context-aware, and stylistically appropriate transformation.

---

## Current State Analysis

### Current Implementation
The current algorithm (`backend/app/routes.py`, line ~72) uses a single prompt to the Gemini model:

```python
prompt = (
    "You are a helpful assistant that processes French novels. "
    "Your task is to list the sentences from the provided text consecutively. "
    f"If a sentence is {sentence_length_limit} words long or less, add it to the list as is. "
    f"If a sentence is longer than {sentence_length_limit} words, you must rewrite it into shorter sentences, each with {sentence_length_limit} words or fewer. "
    "Preserve the exact original meaning and use as many of the original French words as possible. "
    "Present the final output as a JSON object with a single key 'sentences' which is an array of strings."
)
```

### Strengths
- ✅ Clear role and task definition
- ✅ Conditional logic based on user-configurable parameter
- ✅ Key constraints (preserve meaning, use original words)
- ✅ Structured JSON output for reliable parsing
- ✅ User-configurable sentence length limit

### Weaknesses
- ⚠️ Vague rewriting instructions ("rewrite it into shorter sentences")
- ⚠️ No guidance on HOW to split sentences (mechanical vs. literary)
- ⚠️ Lacks context preservation between sentences
- ⚠️ No style or tone preservation instructions
- ⚠️ Doesn't handle special cases (dialogue, titles, verse)
- ⚠️ No examples provided to guide the model
- ⚠️ Processes entire document in one call (no chunking for large texts)
- ⚠️ No validation of output quality

---

## Phase 1: Foundational Prompt Engineering (Short-Term, 1-2 weeks)

**Objective:** Immediately improve output quality with better prompt engineering.

### 1.1 Enhanced Prompt Structure
- [ ] **Add specific splitting rules**
    - Action: Guide the model on where to split sentences
    - Implementation:
        ```python
        "When splitting long sentences:
        1. Split at natural grammatical breaks (conjunctions like 'et', 'mais', 'donc', 'car')
        2. Split at subordinate clause boundaries (qui, que, où, quand)
        3. Preserve the logical flow of ideas
        4. Avoid creating awkward or unnatural sentence fragments"
        ```
    - Priority: HIGH

- [ ] **Add context preservation instruction**
    - Action: Ensure cohesion between sentences
    - Implementation:
        ```python
        "Ensure that rewritten sentences maintain narrative coherence. 
        If a pronoun or reference word is used, ensure it's clear from context. 
        The output must read as a continuous, natural text."
        ```
    - Priority: HIGH

- [ ] **Add style preservation instruction**
    - Action: Maintain literary quality
    - Implementation:
        ```python
        "Preserve the literary style and tone of the original text. 
        Maintain the author's voice, register (formal/informal), and any stylistic devices. 
        Avoid oversimplifying or modernizing the language."
        ```
    - Priority: HIGH

### 1.2 Special Case Handling
- [ ] **Add dialogue handling**
    - Action: Special treatment for quoted text
    - Implementation:
        ```python
        "For dialogue (text in quotation marks):
        - Keep dialogue intact unless absolutely necessary to split
        - If splitting is required, maintain natural speech patterns
        - Ensure speaker attribution remains clear"
        ```
    - Priority: MEDIUM

- [ ] **Add title and heading detection**
    - Action: Don't split chapter titles or section headings
    - Implementation:
        ```python
        "Do not split or rewrite:
        - Chapter titles or section headings
        - Proper nouns (names, places)
        - Dates and numbers"
        ```
    - Priority: MEDIUM

### 1.3 Output Quality Improvements
- [ ] **Add few-shot examples**
    - Action: Provide 2-3 examples in the prompt
    - Implementation:
        ```python
        "Example 1:
        Input: 'Le vieil homme, qui habitait seul dans une petite maison au bout du village depuis la mort de sa femme, se réveilla tôt ce matin-là.'
        Output: [
          'Le vieil homme habitait seul dans une petite maison au bout du village.',
          'Il y vivait depuis la mort de sa femme.',
          'Il se réveilla tôt ce matin-là.'
        ]"
        ```
    - Priority: MEDIUM

- [ ] **Strengthen JSON format requirement**
    - Action: Reduce parsing errors
    - Implementation:
        ```python
        "IMPORTANT: Your response MUST be valid JSON. Do not include any text before or after the JSON object.
        Format: {\"sentences\": [\"sentence 1\", \"sentence 2\", ...]}"
        ```
    - Priority: MEDIUM

---

## Phase 2: Multi-Step Processing Pipeline (Mid-Term, 1 month)

**Objective:** Implement a more sophisticated, multi-stage processing approach.

### 2.1 Pre-Processing Stage
- [ ] **Implement text analysis step**
    - Action: Create first AI call to analyze the text
    - Purpose: Identify structure before rewriting
    - Output:
        ```json
        {
          "segments": [
            {"id": 1, "text": "...", "type": "narrative", "word_count": 15, "needs_split": true},
            {"id": 2, "text": "...", "type": "dialogue", "word_count": 5, "needs_split": false}
          ]
        }
        ```
    - Priority: HIGH

- [ ] **Create sentence type classifier**
    - Types: `narrative`, `dialogue`, `description`, `title`
    - Action: Use separate prompt or lightweight model
    - Benefit: Apply different rewriting strategies per type
    - Priority: MEDIUM

### 2.2 Selective Rewriting
- [ ] **Implement conditional rewriting logic**
    - Action: Only rewrite sentences flagged as `needs_split: true`
    - Flow:
        1. Extract sentences from PDF
        2. Classify and measure each
        3. Only send long sentences to rewriting model
        4. Reassemble in original order
    - Benefit: Reduce API costs, preserve original where possible
    - Priority: HIGH

- [ ] **Create type-specific rewriting prompts**
    - Action: Different prompts for different text types
    - Prompts:
        - `narrative_rewrite_prompt`
        - `dialogue_rewrite_prompt`
        - `description_rewrite_prompt`
    - Priority: MEDIUM

### 2.3 Chain-of-Thought Processing
- [ ] **Implement CoT (Chain-of-Thought) prompting**
    - Action: Ask model to explain before rewriting
    - Implementation:
        ```python
        "Before providing the rewritten sentences, think step-by-step:
        1. Identify the main clauses in the sentence
        2. Determine the best split points
        3. Verify each resulting sentence is grammatically complete
        4. Check that meaning is preserved
        Then provide the JSON output."
        ```
    - Benefit: More logical, consistent splits
    - Priority: MEDIUM

### 2.4 Quality Validation
- [ ] **Implement post-processing validation**
    - Action: Verify rewritten output quality
    - Checks:
        - All sentences are under length limit
        - No empty strings
        - Preserve total word count (±10%)
        - No sentence starts with connector words only
    - Priority: HIGH

- [ ] **Add semantic similarity check**
    - Action: Verify meaning preservation
    - Tool: Use embedding model to compare original vs rewritten
    - Threshold: Similarity > 0.85
    - Priority: LOW

---

## Phase 3: Advanced Features & Optimization (Long-Term, 2-3 months)

**Objective:** Add sophisticated analysis and user control.

### 3.1 User-Controlled Rewriting Styles
- [ ] **Implement rewriting style selector**
    - Action: Add to user settings
    - Styles:
        - **Literal**: Minimal changes, mechanical splits
        - **Balanced**: Mix of preservation and flow (default)
        - **Interpretive**: More restructuring for readability
        - **Academic**: Formal, precise language
    - Priority: MEDIUM

- [ ] **Create style-specific prompts**
    - Action: Load different prompt based on user selection
    - Store: `app/prompts/` directory
    - Priority: MEDIUM

### 3.2 Named Entity Recognition (NER)
- [ ] **Implement NER pre-processing**
    - Action: Extract names, places, terms before rewriting
    - Tool: spaCy French model or Gemini NER
    - Implementation:
        ```python
        entities = extract_entities(text)  # ["Jean", "Paris", "École"]
        prompt += f"\nImportant terms to preserve exactly: {', '.join(entities)}"
        ```
    - Priority: MEDIUM

- [ ] **Create entity preservation validation**
    - Action: Verify all entities appear in output
    - Priority: MEDIUM

### 3.3 Caching & Cost Optimization
- [ ] **Implement result caching**
    - Action: Cache (hash of PDF + settings) → results
    - Storage: Redis or database
    - TTL: 30 days
    - Benefit: Instant results for re-processed texts
    - Priority: HIGH

- [ ] **Add chunking for large documents**
    - Current: Process entire PDF in one call
    - Improved: Split into chunks, process in parallel
    - Benefit: Handle longer documents, faster processing
    - Priority: MEDIUM

- [ ] **Implement progressive processing**
    - Action: Stream results to frontend as they're generated
    - Benefit: Better UX for long documents
    - Priority: LOW

### 3.4 Model Optimization
- [ ] **Experiment with different Gemini models**
    - Current: `gemini-2.0-flash-exp`
    - Test:
        - `gemini-pro` (more capable, slower, expensive)
        - `gemini-flash` (faster, cheaper)
    - Create A/B test framework
    - Priority: MEDIUM

- [ ] **Implement prompt optimization testing**
    - Action: Create test dataset with ground truth
    - Metric: BLEU score, human evaluation
    - Iterate on prompts based on metrics
    - Priority: LOW

- [ ] **Consider fine-tuning**
    - Action: If volume justifies, fine-tune smaller model
    - Dataset: Collect high-quality examples
    - Benefit: Lower cost, better quality, faster
    - Priority: LOW

### 3.5 Advanced Analysis
- [ ] **Add readability metrics**
    - Action: Calculate before/after readability
    - Metrics: Flesch reading ease, average sentence length
    - Display to user
    - Priority: LOW

- [ ] **Implement diff viewer**
    - Action: Show changes made to original text
    - Highlight: What was split, what was changed
    - Priority: LOW

---

## Phase 4: Quality Assurance & Monitoring (Ongoing)

**Objective:** Continuously improve algorithm performance.

### 4.1 Testing Framework
- [ ] **Create evaluation dataset**
    - Action: Curate set of French texts with ground truth
    - Size: 50-100 test cases
    - Include: Various genres, sentence types
    - Priority: HIGH

- [ ] **Implement automated quality tests**
    - Action: Run tests on every prompt change
    - Metrics:
        - Grammatical correctness (LanguageTool)
        - Meaning preservation (embedding similarity)
        - Length compliance (all under limit)
        - Coherence score
    - Priority: HIGH

### 4.2 User Feedback Loop
- [ ] **Add quality rating system**
    - Action: Allow users to rate rewriting quality
    - UI: 👍👎 or 1-5 stars on results page
    - Store ratings in database
    - Priority: MEDIUM

- [ ] **Implement manual correction feature**
    - Action: Allow users to edit results
    - Use edits to improve prompts
    - Priority: LOW

### 4.3 Monitoring & Analytics
- [ ] **Track algorithm performance metrics**
    - Metrics:
        - Average processing time
        - Retry rate (parsing failures)
        - User satisfaction rating
        - Cost per document
    - Dashboard: Grafana or similar
    - Priority: MEDIUM

- [ ] **Implement error classification**
    - Action: Categorize failures
    - Categories: `parsing_error`, `timeout`, `quality_issue`, `api_error`
    - Alert on spikes
    - Priority: MEDIUM

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ 90%+ of outputs parse successfully on first try
- ✅ User reports: "Rewriting feels more natural"
- ✅ Dialogue is properly preserved
- ✅ No chapter titles are split

### Phase 2 Success Criteria
- ✅ 50% reduction in unnecessary rewrites (preserve original when possible)
- ✅ Processing handles documents up to 100 pages
- ✅ 95%+ semantic similarity between original and rewritten
- ✅ 30% reduction in API costs (through selective rewriting)

### Phase 3 Success Criteria
- ✅ Cache hit rate > 20% (for common texts)
- ✅ Users can select and notice difference in rewriting styles
- ✅ Named entities preserved with 99%+ accuracy
- ✅ Processing time < 30 seconds for typical document

### Phase 4 Success Criteria
- ✅ Automated tests catch regressions
- ✅ User satisfaction > 4.2/5
- ✅ Less than 5% of results require manual correction
- ✅ Algorithm improvements data-driven (based on metrics)

---

## Estimated Timeline

- **Phase 1**: 1-2 weeks (immediate improvements)
- **Phase 2**: 1 month (architecture work)
- **Phase 3**: 2-3 months (advanced features)
- **Phase 4**: Ongoing (continuous improvement)

**Total to production-optimized**: ~3-4 months

---

## Implementation Priority

### Immediate (Do First)
1. Enhanced prompt with splitting rules (Phase 1.1)
2. Context and style preservation (Phase 1.1)
3. Dialogue handling (Phase 1.2)
4. Few-shot examples (Phase 1.3)

### Next (Within 1 Month)
1. Pre-processing text analysis (Phase 2.1)
2. Selective rewriting (Phase 2.2)
3. Result caching (Phase 3.3)
4. Evaluation dataset (Phase 4.1)

### Future (2-3 Months)
1. User style controls (Phase 3.1)
2. NER integration (Phase 3.2)
3. Model optimization (Phase 3.4)
4. User feedback loop (Phase 4.2)

---

## Priority Legend
- **HIGH**: Critical for quality and user satisfaction
- **MEDIUM**: Important for capabilities and efficiency
- **LOW**: Nice-to-have enhancements

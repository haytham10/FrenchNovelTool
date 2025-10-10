# French Novel Tool: Coverage Algorithm & UI Enhancement Request

## Project Overview
This is a full-stack Flask + Next.js application that helps language learner "Stan" build optimized French sentence lists for vocabulary drilling. The app processes novels and uses a greedy algorithm to create minimal "Learning Sets" covering target vocabulary.

**Current Problem:** Multiple errors and problems & Algorithm stops at 70% coverage instead of 85-90%+

---

## User Story: Stan's Workflow

1. **Upload novels** - PDFs converted to sentence database
2. **Configure analysis** - Pick 2K word list, Coverage Mode, sentence limit
3. **Select sources** - Choose from processed novels  
4. **Run analysis** - Algorithm builds Learning Set
5. **Review & export** - Dashboard shows results, exports to Google Sheets

**Stan's Non-Negotiable Requirements:**
- Sentences must be 4-8 words only (drillable length)
- Only content words count (nouns, verbs, adjectives, adverbs - NO pronouns, prepositions, etc.)
- Smallest possible set covering all vocabulary (target: under 600 sentences)

---

## BACKEND IMPROVEMENTS NEEDED

### Location: `backend/app/services/coverage_service.py`

#### 1. Add French Lemma Normalization
Create a helper function that handles French-specific quirks before matching words:
- Elisions: convert l' to le, d' to de, j' to je, qu' to que
- Reflexive pronouns: strip se_ prefixes  
- Standardize case and whitespace

Apply this to both the target word list and all sentence lemmas before comparing.

#### 2. Build Word Frequency Index (Performance)
Before starting the algorithm, scan all sentences once and count how many sentences contain each target word. Cache this in a dictionary. Use it during scoring instead of rescanning.

#### 3. Enhance the Scoring Formula
Current formula is too simple: `(new_words × 10) - length`

Make it adaptive and reward rare words:
- **Adaptive weight**: Start with 10x multiplier for new words, increase to 15x at 50% coverage, then 25x at 70%+ coverage
- **Rarity bonus**: If a word appears in fewer than 5 sentences, add +20 bonus. If fewer than 20 sentences, add +5 bonus
- **Efficiency bonus**: If sentence covers 3+ rare words at once (when past 60% coverage), add +10 bonus

#### 4. Pre-Filter Candidate Pool
Instead of scanning all 30k sentences every iteration:
- Build initial pool of only sentences that are 4-8 words AND contain at least one uncovered word
- After each selection, remove the chosen sentence from the pool
- Every 10 iterations without progress, rebuild the pool with remaining uncovered words

#### 5. Add Better Logging
Log progress every 50 sentences selected showing:
- Current iteration number
- Coverage percentage  
- Number of sentences selected so far
- Note when entering "aggressive mode" at 70% coverage

#### 6. Stagnation Detection
If algorithm goes 50+ iterations without finding any new words, stop early and log why it's stuck.

---

### Location: `backend/app/routes/coverage_routes.py`

#### 7. Add Diagnostic Endpoint
Create new endpoint: `GET /api/v1/coverage/runs/<run_id>/diagnosis`

This should analyze the missing 30% of words and categorize them into:
- **Not in corpus**: Words that don't appear in any source sentence
- **Only in long sentences**: Words only found in 9+ word sentences (outside 4-8 range)
- **Only in short sentences**: Words only found in 1-3 word sentences
- **In valid range but missed**: Words that ARE in 4-8 word sentences but algorithm didn't select them

Return JSON with counts and sample words (first 20-30) from each category.

---

## FRONTEND IMPROVEMENTS NEEDED

### Location: Coverage results page

#### 8. Add "Diagnose Coverage" Button
Next to "Download CSV" and "Export to Sheets", add a "Diagnose" button that:
- Calls the diagnostic endpoint
- Opens a modal/dialog showing the breakdown
- Displays each category with its count and sample words
- Shows a simple recommendation (e.g., "180 words not in source - upload more novels")

#### 9. Polish Results Dashboard
Enhance the "Completed" state after analysis runs:
- Make KPI cards more prominent (larger numbers, better color coding)
- Add visual gauge for coverage percentage
- Make "Uncovered Words" expandable section more discoverable
- Show sentence count vs target prominently

#### 10. Add Progress Context
During the "Processing" state, show which phase the algorithm is in:
- "Building candidate pool..."
- "Standard mode: 45% coverage..."  
- "Aggressive mode: 73% coverage..."
- "Finalizing results..."

---

## EXPECTED OUTCOMES

After these changes:
- **Coverage improves** from 70% to 85-90% (remaining 10-15% will be words genuinely missing from source novels)
- **Algorithm runs faster** due to pre-filtering and frequency caching
- **Better accuracy** from French lemma normalization (catches conjugations, elisions)
- **Clear diagnostics** show Stan exactly why remaining words aren't covered
- **Cleaner UX** with better progress feedback and results presentation

---

## TESTING CHECKLIST

After implementation, verify:
- Run the existing 2-novel batch that shows 70% - confirm it increases
- Check diagnostic endpoint returns sensible categorization
- Verify logs show adaptive scoring activating at 70%
- Test batch mode with 3+ novels
- Confirm UI displays diagnosis clearly in a modal/dialog

---

## KEY CONSTRAINTS TO MAINTAIN

**DO NOT CHANGE:**
- 4-8 word sentence range (critical for Stan's drilling method)
- Content-word-only filtering (nouns, verbs, adjectives, adverbs)
- Greedy set-cover approach (just make it smarter)
- Current API structure and database schema

**DO CHANGE:**
- Scoring formula (make adaptive + rarity-aware)
- Performance (add caching and pre-filtering)
- Lemma matching (add French normalization)
- Diagnostics (add new endpoint and UI)
- Logging (add progress visibility)

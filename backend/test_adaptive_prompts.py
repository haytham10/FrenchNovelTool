"""
Test script for adaptive prompt system (Stage 2 implementation).

This script tests the three-tier adaptive prompt system without requiring
Flask context or database connections.
"""


class PromptEngine:
    """Simplified PromptEngine for testing (copied from gemini_service.py)"""

    @staticmethod
    def build_passthrough_prompt(sentence_length_limit: int, min_sentence_length: int) -> str:
        """For sentences already meeting criteria - minimal processing."""
        return f"""You are a French text validator. The sentences below are already correctly formatted.
Return them unchanged in JSON format.

VALIDATION CRITERIA (already met):
✓ {min_sentence_length}-{sentence_length_limit} words
✓ Contains a conjugated verb
✓ Grammatically complete

YOUR TASK:
Simply verify and return the sentences as-is.

OUTPUT FORMAT (STRICT JSON):
{{"sentences": ["sentence 1", "sentence 2"]}}

No markdown, no code blocks, just JSON."""

    @staticmethod
    def build_light_rewrite_prompt(sentence_length_limit: int, min_sentence_length: int) -> str:
        """For sentences needing minor adjustments."""
        return f"""You are a French linguistic expert. Adjust the sentences to meet these criteria.

CRITICAL REQUIREMENTS (ALL MANDATORY):
1. Length: {min_sentence_length}-{sentence_length_limit} words (strict)
2. Must contain a conjugated verb (not infinitive)
3. Grammatically complete sentence
4. Preserves original vocabulary

ALLOWED ADJUSTMENTS:
• Add subject pronoun if missing (il, elle, on, je, tu, nous, vous)
• Add auxiliary verb if needed (est, sont, a, ont, était, sera)
• Add "C'est..." construction to convert phrases to sentences
• Remove redundant words to fit length constraint
• Simplify verb tense if necessary (keep present/imperfect/future)

FORBIDDEN:
• Changing core vocabulary
• Creating fragments (prepositional phrases alone)
• Removing the main verb
• Splitting into multiple sentences (that's for heavy rewrite)

VERB REQUIREMENT:
Every output sentence MUST contain a conjugated verb:
✓ "Elle marche." (present tense)
✓ "Il était triste." (imperfect)
✓ "Cela durera." (future)
✗ "Pour toujours." (NO VERB!)
✗ "Dans la rue." (NO VERB!)

EXAMPLES:

Input: "Pour toujours et à jamais."
❌ Wrong: ["Pour toujours et à jamais."] ← No verb!
✓ Correct: ["Cela durera pour toujours."] ← Has verb "durera", 4 words

Input: "Maintenant ou jamais."
❌ Wrong: ["Maintenant ou jamais."] ← No verb!
✓ Correct: ["C'est maintenant ou jamais."] ← Has verb "est", 4 words

Input: "Dans quinze ans, c'est moi qui serai là."
✓ Correct: ["Dans quinze ans, je serai là."] ← Already good, simplified slightly

VALIDATION CHECKLIST (before outputting):
☐ Each sentence is {min_sentence_length}-{sentence_length_limit} words
☐ Each sentence has a conjugated verb
☐ Each sentence is grammatically complete
☐ Original vocabulary is preserved

OUTPUT FORMAT (STRICT JSON):
{{"sentences": ["sentence 1", "sentence 2"]}}

No markdown, no code blocks, just JSON."""

    @staticmethod
    def build_heavy_rewrite_prompt(sentence_length_limit: int, min_sentence_length: int) -> str:
        """For complex sentences requiring decomposition."""
        return f"""You are a French linguistic expert. Decompose these complex sentences into multiple simple sentences.

═══════════════════════════════════════════════════════════════
CRITICAL REQUIREMENTS FOR EACH OUTPUT SENTENCE
═══════════════════════════════════════════════════════════════

1. Length: {min_sentence_length}-{sentence_length_limit} words (STRICT - count carefully!)
2. Structure: Subject + Conjugated Verb + (Object/Complement)
3. Completeness: Must be grammatically independent
4. Vocabulary: Preserve all meaningful words from the original

═══════════════════════════════════════════════════════════════
DECOMPOSITION STRATEGY
═══════════════════════════════════════════════════════════════

STEP 1: Identify core propositions
• Who does what?
• Who is what?
• What happens?

STEP 2: Extract each proposition
• Create a standalone sentence for each proposition
• Add subjects/verbs as needed for completeness

STEP 3: Verify each output sentence
• Has subject (explicit or pronoun)
• Has conjugated verb (not infinitive)
• Is {min_sentence_length}-{sentence_length_limit} words
• Can stand alone without context

═══════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════

Example 1: Long descriptive sentence
Input: "Il marchait lentement dans la rue sombre et froide, pensant à elle."
❌ WRONG (fragments): ["dans la rue sombre", "et froide", "pensant à elle"]
✓ CORRECT (complete): [
  "Il marchait dans la rue.",
  "La rue était sombre et froide.",
  "Il pensait à elle."
]

Example 2: Complex action sequence
Input: "Vous longez un kiosque à journaux, jetez un coup d'œil à la une du New York Times."
✓ CORRECT: [
  "Vous longez un kiosque à journaux.",
  "Vous regardez la une du journal.",
  "C'est le New York Times."
]

Example 3: Very long sentence
Input: "Ethan envoya une main hasardeuse qui tâtonna plusieurs secondes avant de stopper la montée en puissance de la sonnerie du réveil."
✓ CORRECT: [
  "Ethan envoya une main hasardeuse.",
  "Sa main tâtonna plusieurs secondes.",
  "Il stoppa la sonnerie du réveil."
]

Example 4: Embedded clauses
Input: "It's Now or Never, le standard d'Elvis Presley, se déverse bruyamment sur le trottoir."
✓ CORRECT: [
  "Le standard d'Elvis Presley joue.",
  "C'est It's Now or Never.",
  "La musique se déverse bruyamment."
]

═══════════════════════════════════════════════════════════════
VERB REQUIREMENT (CRITICAL!)
═══════════════════════════════════════════════════════════════

Every output sentence MUST contain a conjugated verb:
✓ "Il marche." (present)
✓ "Elle était triste." (imperfect)
✓ "Nous partirons." (future)
✓ "J'ai mangé." (passé composé)
✗ "Pour toujours." (no verb!)
✗ "Dans la rue sombre." (no verb!)
✗ "Pensant à elle." (participle only - no auxiliary!)

═══════════════════════════════════════════════════════════════
VALIDATION CHECKLIST (before outputting)
═══════════════════════════════════════════════════════════════

For EACH output sentence, verify:
☐ Has a subject (explicit noun/name OR pronoun: il/elle/je/vous/nous/ils/elles)
☐ Has a conjugated verb (est/sont/a/ont/marche/marchait/sera/etc.)
☐ Is {min_sentence_length}-{sentence_length_limit} words (COUNT CAREFULLY!)
☐ Can stand alone (not a prepositional phrase, not a conjunction fragment)
☐ Preserves vocabulary from original

COMMON ERRORS TO AVOID:
✗ Prepositional phrases: "dans la rue", "avec elle", "pour toujours"
✗ Conjunction fragments: "et froide", "mais aussi", "donc ensuite"
✗ Participial phrases: "pensant à elle", "marchant lentement"
✗ Infinitive phrases: "pour partir", "avant de stopper"

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT (STRICT JSON)
═══════════════════════════════════════════════════════════════

{{"sentences": ["sentence 1", "sentence 2", "sentence 3"]}}

No markdown, no code blocks, no explanations, JUST JSON."""


def test_prompts():
    """Test and analyze the adaptive prompt system"""

    # Build prompts
    passthrough = PromptEngine.build_passthrough_prompt(8, 4)
    light = PromptEngine.build_light_rewrite_prompt(8, 4)
    heavy = PromptEngine.build_heavy_rewrite_prompt(8, 4)

    # Count lines
    passthrough_lines = len(passthrough.split('\n'))
    light_lines = len(light.split('\n'))
    heavy_lines = len(heavy.split('\n'))

    # Estimate tokens (rough: 1 token ≈ 4 characters for English/French text)
    passthrough_tokens = len(passthrough) // 4
    light_tokens = len(light) // 4
    heavy_tokens = len(heavy) // 4

    # Character counts
    passthrough_chars = len(passthrough)
    light_chars = len(light)
    heavy_chars = len(heavy)

    print("=" * 70)
    print("ADAPTIVE PROMPT SYSTEM - SIZE ANALYSIS")
    print("=" * 70)
    print()

    print("TIER 1: PASSTHROUGH PROMPT (for sentences already 4-8 words + verb)")
    print("-" * 70)
    print(f"  Lines: {passthrough_lines}")
    print(f"  Characters: {passthrough_chars:,}")
    print(f"  Estimated tokens: ~{passthrough_tokens:,}")
    print(f"  Purpose: Minimal validation, return as-is (NO REWRITING)")
    print()

    print("TIER 2: LIGHT REWRITE PROMPT (for 3-10 word sentences)")
    print("-" * 70)
    print(f"  Lines: {light_lines}")
    print(f"  Characters: {light_chars:,}")
    print(f"  Estimated tokens: ~{light_tokens:,}")
    print(f"  Purpose: Minor adjustments (add verb, trim words)")
    print()

    print("TIER 3: HEAVY REWRITE PROMPT (for complex sentences)")
    print("-" * 70)
    print(f"  Lines: {heavy_lines}")
    print(f"  Characters: {heavy_chars:,}")
    print(f"  Estimated tokens: ~{heavy_tokens:,}")
    print(f"  Purpose: Full decomposition with examples")
    print()

    print("=" * 70)
    print("COMPARISON WITH OLD SYSTEM")
    print("=" * 70)
    print()

    # Old system estimate (from gemini_service.py build_prompt method)
    old_prompt_lines = 169  # Counted from lines 369-510 in build_prompt
    old_prompt_chars = 7000  # Rough estimate
    old_prompt_tokens = old_prompt_chars // 4

    print(f"OLD MONOLITHIC PROMPT:")
    print(f"  Lines: ~{old_prompt_lines}")
    print(f"  Characters: ~{old_prompt_chars:,}")
    print(f"  Estimated tokens: ~{old_prompt_tokens:,}")
    print()

    total_new_lines = passthrough_lines + light_lines + heavy_lines
    avg_new_chars = (passthrough_chars + light_chars + heavy_chars) // 3
    avg_new_tokens = (passthrough_tokens + light_tokens + heavy_tokens) // 3

    print(f"NEW ADAPTIVE SYSTEM (AVERAGE):")
    print(f"  Total lines across 3 tiers: {total_new_lines}")
    print(f"  Average characters per tier: ~{avg_new_chars:,}")
    print(f"  Average tokens per tier: ~{avg_new_tokens:,}")
    print()

    print("TOKEN SAVINGS:")
    print(f"  Passthrough vs Old: {old_prompt_tokens - passthrough_tokens:,} tokens saved ({((old_prompt_tokens - passthrough_tokens) / old_prompt_tokens * 100):.1f}%)")
    print(f"  Light vs Old: {old_prompt_tokens - light_tokens:,} tokens saved ({((old_prompt_tokens - light_tokens) / old_prompt_tokens * 100):.1f}%)")
    print(f"  Heavy vs Old: {old_prompt_tokens - heavy_tokens:,} tokens saved ({((old_prompt_tokens - heavy_tokens) / old_prompt_tokens * 100):.1f}%)")
    print()

    print("=" * 70)
    print("EXPECTED PERFORMANCE IMPROVEMENTS")
    print("=" * 70)
    print()
    print("Assuming 50% of sentences are passthrough (4-8 words + verb):")
    print(f"  - 50% passthrough: {passthrough_tokens:,} tokens × 0.5 = {passthrough_tokens * 0.5:,.0f} avg tokens")
    print(f"  - 30% light rewrite: {light_tokens:,} tokens × 0.3 = {light_tokens * 0.3:,.0f} avg tokens")
    print(f"  - 20% heavy rewrite: {heavy_tokens:,} tokens × 0.2 = {heavy_tokens * 0.2:,.0f} avg tokens")
    weighted_avg = (passthrough_tokens * 0.5) + (light_tokens * 0.3) + (heavy_tokens * 0.2)
    print(f"  - Weighted average: {weighted_avg:,.0f} tokens per sentence")
    print()
    print(f"  OLD SYSTEM: {old_prompt_tokens:,} tokens per sentence (always)")
    print(f"  NEW SYSTEM: {weighted_avg:,.0f} tokens per sentence (average)")
    print(f"  SAVINGS: {old_prompt_tokens - weighted_avg:,.0f} tokens per sentence ({((old_prompt_tokens - weighted_avg) / old_prompt_tokens * 100):.1f}%)")
    print()

    print("COST SAVINGS (for 1000 sentences):")
    old_total = old_prompt_tokens * 1000
    new_total = weighted_avg * 1000
    savings = old_total - new_total
    print(f"  OLD: {old_total:,} tokens")
    print(f"  NEW: {new_total:,.0f} tokens")
    print(f"  SAVINGS: {savings:,.0f} tokens ({(savings / old_total * 100):.1f}%)")
    print()

    print("=" * 70)
    print("SAMPLE PROMPTS")
    print("=" * 70)
    print()

    print("PASSTHROUGH PROMPT (first 300 chars):")
    print("-" * 70)
    print(passthrough[:300] + "...")
    print()

    print("LIGHT REWRITE PROMPT (first 300 chars):")
    print("-" * 70)
    print(light[:300] + "...")
    print()

    print("HEAVY REWRITE PROMPT (first 300 chars):")
    print("-" * 70)
    print(heavy[:300] + "...")
    print()


if __name__ == "__main__":
    test_prompts()

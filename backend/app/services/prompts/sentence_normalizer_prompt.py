"""
Sentence Normalizer Prompt - V2 (Few-Shot Edition)

This prompt uses few-shot learning to train the AI model to produce complete sentences
without fragments. The focus is on showing correct behavior through examples rather
than lengthy rule explanations.

Target: <0.5% fragment rate (down from 3-5% with legacy prompt)
"""

from typing import Dict, Any


def build_sentence_normalizer_prompt(
    sentence_length_limit: int = 8,
    min_sentence_length: int = 2,
    ignore_dialogue: bool = False,
    preserve_formatting: bool = True,
    fix_hyphenation: bool = True,
) -> str:
    """Build a concise few-shot prompt for French sentence normalization.

    Args:
        sentence_length_limit: Maximum words per sentence (default: 8)
        min_sentence_length: Minimum words per sentence (default: 2)
        ignore_dialogue: Whether to preserve dialogue without splitting
        preserve_formatting: Whether to preserve original formatting
        fix_hyphenation: Whether to rejoin hyphenated words

    Returns:
        Prompt string optimized for Gemini AI
    """

    # System role - clear and concise
    system_role = f"""You are a French linguistic expert. Your task: transform complex French text into simple, grammatically complete sentences of {min_sentence_length}-{sentence_length_limit} words each.

CRITICAL RULE: Every output sentence MUST be a complete, independent sentence with a subject and conjugated verb. NO sentence fragments allowed."""

    # Few-shot examples - demonstrate correct behavior
    few_shot_examples = """
EXAMPLES - Learn from these:

Example 1 - Correct Transformation:
Input: "Il marchait lentement dans la rue sombre et froide, pensant à elle constamment."
WRONG OUTPUT: ["dans la rue sombre", "et froide", "pensant à elle"]  ← FRAGMENTS!
CORRECT OUTPUT: ["Il marchait lentement dans la rue.", "La rue était sombre et froide.", "Il pensait à elle constamment."]
Why correct: Each sentence has subject + verb and can stand alone.

Example 2 - Reject Fragments:
Input: "Dans la rue."
WRONG OUTPUT: ["Dans la rue."]  ← FRAGMENT (no verb)
CORRECT OUTPUT: []  ← Reject incomplete fragments OR ["Il était dans la rue."]
Why correct: Don't output incomplete prepositional phrases.

Example 3 - Complete Temporal Phrases:
Input: "Pour toujours et à jamais."
WRONG OUTPUT: ["Pour toujours et à jamais."]  ← FRAGMENT
CORRECT OUTPUT: ["Ils s'aimeront pour toujours."] OR []
Why correct: Temporal phrases need a main clause.

Example 4 - Handle Dialogue:
Input: "Il dit : « Je t'aime. »"
CORRECT OUTPUT: ["Il dit qu'il l'aime."] OR ["Je t'aime, dit-il."]
Why correct: Complete sentence with reporting verb integrated.

Example 5 - Split Long Sentences WITHOUT Creating Fragments:
Input: "Le standard d'Elvis Presley, It's Now or Never, jouait à la radio pendant qu'ils dansaient."
WRONG OUTPUT: ["Le standard d'Elvis Presley", "It's Now or Never", "pendant qu'ils dansaient"]  ← FRAGMENTS!
CORRECT OUTPUT: ["Le standard d'Elvis Presley jouait à la radio.", "La chanson s'appelait It's Now or Never.", "Ils dansaient ensemble."]
Why correct: Each output is a complete sentence.
"""

    # Task instruction - simple and direct
    task_instruction = f"""
YOUR TASK:
1. Read the entire French text
2. For each sentence >{sentence_length_limit} words: REWRITE into multiple complete sentences
3. For each sentence ≤{sentence_length_limit} words: Keep as-is
4. NEVER output fragments - every sentence must be grammatically complete
5. Each sentence MUST have: subject + conjugated verb + complete thought

FRAGMENT TEST (ask yourself before outputting):
- Can this stand alone without context?
- Does it have a subject AND conjugated verb?
- Is it NOT a dependent clause?
If NO to any → REWRITE or REJECT."""

    # Additional rules if needed
    additional_rules = []
    if ignore_dialogue:
        additional_rules.append(
            "DIALOGUE: Keep quoted dialogue intact, regardless of length."
        )
    if fix_hyphenation:
        additional_rules.append(
            "HYPHENATION: Rejoin words split by hyphens (e.g., 'ex- ample' → 'exemple')."
        )
    if preserve_formatting:
        additional_rules.append(
            "FORMATTING: Preserve quotation marks, italics, and ellipses where grammatically appropriate."
        )

    rules_section = "\n".join(additional_rules) if additional_rules else ""

    # Output format - strict JSON
    output_format = """
OUTPUT FORMAT (STRICT):
Return ONLY valid JSON: {"sentences": ["Complete sentence 1.", "Complete sentence 2.", ...]}

Do NOT include:
- Markdown code blocks
- Explanations
- Fragments
- Incomplete thoughts"""

    # Combine all sections
    prompt_parts = [
        system_role,
        few_shot_examples,
        task_instruction,
    ]

    if rules_section:
        prompt_parts.append(rules_section)

    prompt_parts.append(output_format)

    return "\n\n".join(prompt_parts)


def build_minimal_prompt(
    sentence_length_limit: int = 8,
    min_sentence_length: int = 2,
) -> str:
    """Build a minimal fallback prompt for when the full prompt fails.

    This is used as a last resort when Gemini has issues with the full prompt.
    """
    return (
        f"Rewrite this French text into grammatically complete, independent sentences "
        f"({min_sentence_length}-{sentence_length_limit} words each). "
        f"Each sentence MUST have a subject and conjugated verb. "
        f"Return ONLY JSON: {{\"sentences\": [\"Sentence 1.\", \"Sentence 2.\"]}}"
    )


def get_prompt_config() -> Dict[str, Any]:
    """Return metadata about the prompt version for tracking and A/B testing."""
    return {
        "version": "v2",
        "name": "few_shot_fragment_eliminator",
        "description": "Few-shot learning approach to eliminate sentence fragments",
        "target_fragment_rate": 0.5,  # percent
        "estimated_lines": 45,
        "approach": "few_shot_examples",
        "created": "2025-10-12",
    }

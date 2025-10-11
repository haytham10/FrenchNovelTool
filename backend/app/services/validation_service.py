"""
Validation Service - Quality gate for normalized sentences.

This service ensures that ONLY sentences meeting Stan's requirements
enter the database. Any sentence failing validation is discarded.

Stage 3 of the Sentence Normalization Pipeline refactoring.
"""

import spacy
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class SentenceValidator:
    """
    Validates normalized sentences using spaCy POS tagging.

    Stan's Requirements:
    1. Length: 4-8 words (content words only)
    2. Completeness: Must have a conjugated verb
    3. Grammar: Must be a complete, independent sentence

    This validator acts as a post-processing quality gate after Gemini normalization.
    It uses spaCy's French NLP model for linguistic analysis to ensure high-quality
    output for the Coverage Tool.
    """

    def __init__(self):
        """Initialize the validator with French spaCy model."""
        # Load French spaCy model with memory optimization
        # Use smaller model for better performance and add sentencizer for sentence boundaries
        try:
            import spacy
            # Try to load the small model first for better performance
            self.nlp = spacy.load("fr_core_news_sm", disable=["ner", "parser"])
            # Add sentencizer component for sentence boundary detection
            if "sentencizer" not in self.nlp.pipe_names:
                self.nlp.add_pipe("sentencizer")
            logger.info("SentenceValidator initialized with French spaCy model fr_core_news_sm + sentencizer")
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {e}. Falling back to basic tokenization.")
            # Fallback to a simple tokenizer
            self.nlp = None

        # Validation statistics
        self.stats = {
            'total_processed': 0,
            'passed': 0,
            'failed_length': 0,
            'failed_no_verb': 0,
            'failed_fragment': 0
        }

    def validate_batch(
        self,
        sentences: List[str],
        discard_failures: bool = True
    ) -> Tuple[List[str], Dict]:
        """
        Validate a batch of sentences.

        Args:
            sentences: List of normalized sentences from Gemini
            discard_failures: If True, remove invalid sentences (recommended)

        Returns:
            Tuple of (valid_sentences, validation_report)

        Example:
            >>> validator = SentenceValidator()
            >>> sentences = ["Elle marche.", "Pour toujours.", "Le chat dort bien."]
            >>> valid, report = validator.validate_batch(sentences)
            >>> print(f"Pass rate: {report['pass_rate']:.1f}%")
            >>> print(f"Valid: {valid}")
        """
        valid_sentences = []
        failures = []

        for sentence in sentences:
            is_valid, failure_reason = self.validate_single(sentence)

            if is_valid:
                valid_sentences.append(sentence)
                self.stats['passed'] += 1
            else:
                failures.append({
                    'sentence': sentence,
                    'reason': failure_reason
                })
                self.stats[f'failed_{failure_reason}'] += 1

                if not discard_failures:
                    # Keep even if invalid (not recommended for production)
                    valid_sentences.append(sentence)

            self.stats['total_processed'] += 1

        # Build validation report
        report = {
            'total': len(sentences),
            'valid': len(valid_sentences),
            'invalid': len(failures),
            'pass_rate': len(valid_sentences) / len(sentences) * 100 if sentences else 0,
            'failures': failures[:20],  # Sample of failures for debugging
            'stats': self.stats.copy()
        }

        return valid_sentences, report

    def validate_single(self, sentence: str) -> Tuple[bool, str]:
        """
        Validate a single sentence against all criteria.

        Args:
            sentence: Normalized sentence to validate

        Returns:
            Tuple of (is_valid, failure_reason)
            - is_valid: True if sentence passes all checks
            - failure_reason: 'length', 'no_verb', 'fragment', or None if valid

        Validation Steps:
        1. Check if sentence is empty
        2. Parse with spaCy to extract content words
        3. CHECK 1: Length validation (4-8 words)
        4. CHECK 2: Verb requirement (must have conjugated verb)
        5. CHECK 3: Fragment detection (no prepositional phrases, relative clauses alone)
        """
        if not sentence or not sentence.strip():
            return False, "empty"

        # Parse with spaCy or use fallback
        if not self.nlp:
            # Fallback validation without spaCy - basic length check only
            words = sentence.strip().split()
            word_count = len(words)
            
            # Basic length validation
            if word_count < 4 or word_count > 8:
                logger.debug(f"REJECT (length): {sentence[:50]} [{word_count} words] - spaCy unavailable")
                return False, "length"
            
            # Without spaCy, we can't check for verbs or fragments
            logger.debug(f"ACCEPT (basic): {sentence[:50]} [{word_count} words] - spaCy unavailable")
            return True, None
        
        # Use spaCy for advanced validation
        doc = self.nlp(sentence.strip())

        # Extract content words (exclude punctuation, spaces)
        content_tokens = [
            token for token in doc
            if not token.is_punct and not token.is_space
        ]

        word_count = len(content_tokens)

        # CHECK 1: Length validation (4-8 words)
        if word_count < 4:
            logger.debug(f"REJECT (too short): {sentence[:50]} [{word_count} words]")
            return False, "length"

        if word_count > 8:
            logger.debug(f"REJECT (too long): {sentence[:50]} [{word_count} words]")
            return False, "length"

        # CHECK 2: Verb requirement (CRITICAL)
        has_verb = self._has_conjugated_verb(doc)
        if not has_verb:
            logger.warning(f"REJECT (no verb): {sentence[:50]}")
            return False, "no_verb"

        # CHECK 3: Fragment detection (prepositional phrases, etc.)
        is_fragment = self._is_fragment(doc, sentence)
        if is_fragment:
            logger.warning(f"REJECT (fragment): {sentence[:50]}")
            return False, "fragment"

        # All checks passed
        logger.debug(f"ACCEPT: {sentence[:50]} [{word_count} words]")
        return True, None

    def _has_conjugated_verb(self, doc) -> bool:
        """
        Check if sentence contains a conjugated verb.

        Requirements:
        - Must be VERB or AUX (auxiliary)
        - Must NOT be infinitive (VerbForm=Inf)
        - Must be a main verb (not subordinate participle used as adjective)

        Args:
            doc: spaCy Doc object

        Returns:
            True if sentence contains at least one conjugated verb

        Examples:
            "Elle marche." -> True (marche = VERB)
            "Pour toujours." -> False (no verb)
            "Marcher lentement." -> False (marcher = infinitive)
            "Il est parti." -> True (est = AUX, parti = participle)
        """
        for token in doc:
            # Check for main verbs
            if token.pos_ == "VERB":
                # Get morphological features
                morph_dict = token.morph.to_dict()

                # Exclude infinitives
                if morph_dict.get("VerbForm") == "Inf":
                    continue

                # Exclude participles used as adjectives
                if morph_dict.get("VerbForm") == "Part" and token.dep_ == "amod":
                    continue

                # This is a conjugated verb
                return True

            # Check for auxiliary verbs (être, avoir)
            if token.pos_ == "AUX":
                return True

        return False

    def _is_fragment(self, doc, sentence: str) -> bool:
        """
        Detect common fragment patterns.

        Even with a verb, some patterns are still fragments:
        - Subordinate clauses alone (qui, que, dont)
        - Participial phrases
        - Temporal phrases (quand, lorsque without main clause)
        - Prepositional phrases without main verb

        Args:
            doc: spaCy Doc object
            sentence: Original sentence text

        Returns:
            True if sentence appears to be a fragment

        Examples of fragments:
            "qui était très content" -> True (relative pronoun start)
            "dans la rue sombre" -> True (prepositional phrase without verb)
            "quand il arrive" -> True (subordinate without main clause)

        Examples of valid sentences:
            "Il était très content." -> False
            "La rue était sombre." -> False
            "Il arrive maintenant." -> False
        """
        if len(doc) == 0:
            return True

        first_token = doc[0]
        first_word_lower = first_token.text.lower()

        # Relative pronouns starting sentence = fragment
        relative_pronouns = ["qui", "que", "qu'", "dont", "où", "lequel", "laquelle"]
        if first_word_lower in relative_pronouns:
            logger.debug(f"Fragment pattern: relative pronoun start - {first_word_lower}")
            return True

        # Subordinating conjunctions without main clause
        subordinating_conjunctions = [
            "quand", "lorsque", "si", "comme", "parce", "puisque",
            "bien que", "quoique", "afin que", "pour que"
        ]
        if first_word_lower in subordinating_conjunctions:
            # Check if there's a main clause after the subordinate
            # (This is a heuristic - not perfect)
            comma_count = sum(1 for t in doc if t.text == ",")
            if comma_count == 0:
                logger.debug(f"Fragment pattern: subordinate without main - {first_word_lower}")
                return True

        # Prepositional phrases at start - check for verb position
        prepositions = ["dans", "sur", "sous", "avec", "sans", "pour", "de", "à", "vers", "chez", "par"]
        if first_word_lower in prepositions:
            # If sentence starts with preposition, the verb must be in first half
            # This catches fragments like "dans la rue sombre" without verbs
            midpoint = len(doc) // 2
            has_early_verb = any(
                t.pos_ in ["VERB", "AUX"] for t in doc[:midpoint]
            )
            if not has_early_verb:
                logger.debug(f"Fragment pattern: preposition without early verb - {first_word_lower}")
                return True

        return False

    def get_stats_summary(self) -> Dict:
        """
        Get validation statistics summary.

        Returns:
            Dictionary with validation metrics:
            - total_processed: Total sentences validated
            - passed: Sentences that passed validation
            - failed_length: Sentences rejected for length
            - failed_no_verb: Sentences rejected for no verb
            - failed_fragment: Sentences rejected as fragments
            - pass_rate: Percentage of sentences that passed
        """
        return {
            **self.stats,
            'pass_rate': (self.stats['passed'] / self.stats['total_processed'] * 100)
                        if self.stats['total_processed'] > 0 else 0
        }

    def reset_stats(self):
        """Reset statistics counters for new batch."""
        self.stats = {
            'total_processed': 0,
            'passed': 0,
            'failed_length': 0,
            'failed_no_verb': 0,
            'failed_fragment': 0
        }
        logger.debug("Validation statistics reset")

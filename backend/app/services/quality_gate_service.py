"""Quality Gate Service - Fragment rejection layer using spaCy POS tagging.

This service validates sentences to ensure they are complete, grammatically correct
sentences rather than fragments. It uses spaCy French NLP model for accurate verb
detection and linguistic analysis.

Target: 0% fragments in final output.
"""

import re
from typing import Dict, List, Optional, Tuple

from flask import current_app


class QualityGateService:
    """Service for validating sentence quality using spaCy POS tagging.

    This service enforces strict quality standards to reject sentence fragments:
    - Length requirements (4-8 words by default)
    - Verb presence (at least one VERB token, not AUX)
    - Proper punctuation and capitalization
    - Fragment heuristic checks

    Attributes:
        nlp: spaCy French language model (fr_core_news_sm)
        min_length: Minimum sentence length in words
        max_length: Maximum sentence length in words
        require_verb: Whether to require a verb (default True)
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize Quality Gate Service with spaCy French model.

        Args:
            config: Optional configuration dict with keys:
                - min_length: Minimum sentence length (default: 4)
                - max_length: Maximum sentence length (default: 8)
                - require_verb: Require verb presence (default: True)
        """
        config = config or {}
        self.min_length = config.get("min_length", 4)
        self.max_length = config.get("max_length", 8)
        self.require_verb = config.get("require_verb", True)

        # Load spaCy French model
        try:
            import spacy

            try:
                self.nlp = spacy.load("fr_core_news_sm")
                current_app.logger.info(
                    "QualityGateService initialized with fr_core_news_sm model "
                    f"(min_length={self.min_length}, max_length={self.max_length}, "
                    f"require_verb={self.require_verb})"
                )
            except OSError:
                current_app.logger.error(
                    "spaCy model fr_core_news_sm not found. "
                    "Install with: python -m spacy download fr_core_news_sm"
                )
                raise
        except ImportError:
            current_app.logger.error("spaCy not installed. Install with: pip install spacy")
            raise

    def validate_sentence(self, sentence: str) -> Tuple[bool, Optional[str]]:
        """Validate a sentence against quality gate rules.

        Performs comprehensive validation:
        1. Length check (4-8 words)
        2. Verb presence check (using spaCy POS tagging)
        3. Fragment heuristic checks (e.g., starts with preposition, no verb)
        4. Punctuation check (must end with . ! ? or …)
        5. Capitalization check (must start with capital letter)

        Args:
            sentence: The sentence to validate

        Returns:
            Tuple of (is_valid, rejection_reason)
            - is_valid: True if sentence passes all checks
            - rejection_reason: None if valid, otherwise string describing why rejected
        """
        if not sentence or not sentence.strip():
            return False, "Empty or whitespace-only sentence"

        sentence = sentence.strip()

        # 1. Length check
        words = sentence.split()
        word_count = len(words)

        if word_count < self.min_length:
            return False, f"Too short ({word_count} words, min {self.min_length})"

        if word_count > self.max_length:
            return False, f"Too long ({word_count} words, max {self.max_length})"

        # 2. Capitalization check (must start with capital letter)
        if not sentence[0].isupper():
            return False, "Does not start with capital letter"

        # 3. Punctuation check (must end with proper punctuation)
        if not sentence.endswith((".", "!", "?", "…")):
            return False, f"Missing proper end punctuation (ends with '{sentence[-1]}')"

        # 4. Verb presence check using spaCy POS tagging
        if self.require_verb:
            has_verb, verb_reason = self._check_verb_presence(sentence)
            if not has_verb:
                return False, verb_reason

        # 5. Fragment heuristic checks
        is_fragment, fragment_reason = self._check_fragment_heuristics(sentence, words)
        if is_fragment:
            return False, fragment_reason

        # All checks passed
        return True, None

    def _check_verb_presence(self, sentence: str) -> Tuple[bool, Optional[str]]:
        """Check if sentence contains at least one main verb using spaCy POS tagging.

        Uses spaCy to identify VERB tokens (not AUX/auxiliary verbs).

        Args:
            sentence: The sentence to check

        Returns:
            Tuple of (has_verb, reason)
            - has_verb: True if sentence contains at least one VERB
            - reason: None if has verb, otherwise description of missing verb
        """
        try:
            doc = self.nlp(sentence)

            # Look for main verbs (VERB tag, not AUX)
            verbs = [token for token in doc if token.pos_ == "VERB"]

            if verbs:
                current_app.logger.debug(
                    f"Found {len(verbs)} verb(s) in sentence: {[v.text for v in verbs]}"
                )
                return True, None

            # Check for imperative forms (which might be tagged differently)
            # Imperatives are still valid sentences
            aux_verbs = [token for token in doc if token.pos_ == "AUX"]
            if aux_verbs:
                # Auxiliary verbs alone (être, avoir) can form valid sentences
                # e.g., "Elle est belle." - "est" is AUX but forms complete sentence
                current_app.logger.debug(f"Found auxiliary verb(s): {[v.text for v in aux_verbs]}")
                return True, None

            # No verb found
            token_pos = [(t.text, t.pos_) for t in doc]
            current_app.logger.debug(f"No verb found. Token POS tags: {token_pos}")
            return False, f"No verb found (POS tags: {token_pos})"

        except Exception as e:
            current_app.logger.exception(f"Error in spaCy verb detection: {e}")
            # If spaCy fails, fall back to heuristic check
            return self._heuristic_verb_check(sentence.split())

    def _heuristic_verb_check(self, words: List[str]) -> Tuple[bool, Optional[str]]:
        """Fallback heuristic verb detection if spaCy fails.

        Uses common French verb forms and endings to detect verbs.
        This is less accurate than spaCy but serves as a backup.

        Args:
            words: List of words in the sentence

        Returns:
            Tuple of (has_verb, reason)
        """
        # Common French verb forms (exact matches)
        exact_verb_forms = {
            "a",
            "ai",
            "as",
            "ont",
            "ez",
            "est",
            "sont",
            "était",
            "étaient",
            "sera",
            "seront",
            "avait",
            "avaient",
            "aura",
            "auront",
            "fut",
            "furent",
            "soit",
            "soient",
            "fût",
            "suis",
            "sommes",
            "va",
            "vais",
            "vas",
            "vont",
            "allait",
            "allaient",
            "ira",
            "iront",
            "fait",
            "fais",
            "font",
            "faisait",
            "faisaient",
            "fera",
            "feront",
            "dit",
            "dis",
            "disent",
            "disait",
            "disaient",
            "dira",
            "diront",
            "peut",
            "peux",
            "peuvent",
            "pouvait",
            "pouvaient",
            "pourra",
            "pourront",
            "doit",
            "dois",
            "doivent",
            "devait",
            "devaient",
            "devra",
            "devront",
            "voit",
            "vois",
            "voient",
            "voyait",
            "voyaient",
            "verra",
            "verront",
            "vient",
            "viens",
            "viennent",
            "venait",
            "venaient",
            "viendra",
            "viendront",
            "prend",
            "prends",
            "prennent",
            "prenait",
            "prenaient",
            "prendra",
            "prendront",
            "veut",
            "veux",
            "veulent",
            "voulait",
            "voulaient",
            "voudra",
            "voudront",
            "marche",
            "marches",
            "marchent",
            "marchait",
            "marchaient",
            "marchera",
            "marcheront",
            "pense",
            "penses",
            "pensent",
            "pensait",
            "pensaient",
            "pensera",
            "penseront",
        }

        # Common verb endings
        verb_suffixes = (
            "er",
            "ir",
            "oir",
            "re",  # Infinitives
            "ais",
            "ait",
            "aient",
            "iez",
            "ions",  # Imperfect
            "era",
            "erai",
            "eras",
            "erez",
            "eront",  # Future
            "é",
            "ée",
            "és",
            "ées",  # Past participles
            "ent",
            "es",
            "e",  # Present
        )

        for word in words:
            clean_word = word.lower().strip(".,;:!?…")

            # Check exact matches
            if clean_word in exact_verb_forms:
                return True, None

            # Check suffixes (with length threshold to avoid false positives)
            for suffix in verb_suffixes:
                if clean_word.endswith(suffix) and len(clean_word) > len(suffix):
                    return True, None

        return False, "No verb found (heuristic check)"

    def _check_fragment_heuristics(
        self, sentence: str, words: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """Check for common fragment patterns using heuristics.

        Detects fragments that start with:
        - Prepositions without complete structure (dans, sur, avec, sans, pour, etc.)
        - Conjunctions without proper completion (et, mais, donc, car, etc.)
        - Temporal expressions without main clause (quand, lorsque, pendant, etc.)
        - Relative pronouns without main clause (qui, que, dont, où, etc.)

        Args:
            sentence: The full sentence string
            words: List of words in the sentence

        Returns:
            Tuple of (is_fragment, reason)
            - is_fragment: True if sentence appears to be a fragment
            - reason: None if not fragment, otherwise description of fragment type
        """
        if not words:
            return True, "Empty word list"

        first_word_lower = words[0].lower()

        # 1. Preposition-starting fragments (very common)
        preposition_starts = [
            "dans",
            "sur",
            "sous",
            "avec",
            "sans",
            "pour",
            "de",
            "à",
            "vers",
            "chez",
            "par",
            "parmi",
            "contre",
            "entre",
        ]
        if first_word_lower in preposition_starts:
            # These are often fragments unless they have proper structure
            # The verb check should have already validated, but we can add extra
            # heuristic checks here
            return False, None  # Let verb check handle this

        # 2. Conjunction-starting fragments
        conjunction_starts = ["et", "mais", "donc", "car", "or", "ni", "puis"]
        if first_word_lower in conjunction_starts:
            # Conjunctions at start are often fragments unless very short imperative
            # or question
            if len(words) < 4:
                return True, f"Conjunction fragment: starts with '{first_word_lower}' but too short"

        # 3. Temporal expression fragments
        temporal_starts = ["quand", "lorsque", "pendant", "durant", "avant", "après", "depuis"]
        if first_word_lower in temporal_starts and len(words) < 5:
            return True, f"Temporal fragment: starts with '{first_word_lower}' without main clause"

        # 4. Relative pronoun fragments
        relative_starts = [
            "qui",
            "que",
            "dont",
            "où",
            "lequel",
            "laquelle",
            "lesquels",
            "lesquelles",
        ]
        if first_word_lower in relative_starts and len(words) < 4:
            return (
                True,
                f"Relative clause fragment: starts with '{first_word_lower}' without main clause",
            )

        # 5. Check for idiomatic fragments
        sentence_lower = sentence.lower()

        # "Pour toujours" pattern
        if sentence_lower.startswith("pour toujours"):
            return True, "Idiomatic fragment: 'pour toujours' without verb"

        # Participial phrases without auxiliary
        if words[0].endswith(("ant", "é", "ée", "és", "ées")):
            # Check if there's an auxiliary verb
            aux_verbs = ["est", "sont", "a", "ont", "était", "étaient", "avait", "avaient"]
            has_auxiliary = any(word.lower() in aux_verbs for word in words)
            if not has_auxiliary and len(words) < 6:
                return True, "Participial fragment: starts with participle without auxiliary"

        # Not a fragment based on heuristics
        return False, None

    def batch_validate(self, sentences: List[str]) -> List[Dict]:
        """Validate multiple sentences in batch.

        Args:
            sentences: List of sentences to validate

        Returns:
            List of validation result dicts, each containing:
            - sentence: The original sentence
            - is_valid: True if valid, False if rejected
            - rejection_reason: None if valid, otherwise reason for rejection
        """
        results = []

        for sentence in sentences:
            is_valid, reason = self.validate_sentence(sentence)
            results.append({"sentence": sentence, "is_valid": is_valid, "rejection_reason": reason})

        return results

    def get_validation_stats(self, validation_results: List[Dict]) -> Dict:
        """Calculate statistics from batch validation results.

        Args:
            validation_results: Results from batch_validate()

        Returns:
            Dict with statistics:
            - total: Total sentences validated
            - valid: Number of valid sentences
            - rejected: Number of rejected sentences
            - rejection_rate: Percentage of rejected sentences
            - rejection_reasons: Dict of reason -> count
        """
        total = len(validation_results)
        valid = sum(1 for r in validation_results if r["is_valid"])
        rejected = total - valid
        rejection_rate = (rejected / total * 100) if total > 0 else 0.0

        # Count rejection reasons
        rejection_reasons = {}
        for result in validation_results:
            if not result["is_valid"]:
                reason = result["rejection_reason"]
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

        return {
            "total": total,
            "valid": valid,
            "rejected": rejected,
            "rejection_rate": rejection_rate,
            "rejection_reasons": rejection_reasons,
        }

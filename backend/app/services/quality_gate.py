"""Quality Gate service: validates sentences returned by the LLM.

This module provides comprehensive validation for Project Battleship Phase 1.3.
It validates that sentences are grammatically complete, audio-ready, and meet
all quality criteria including:
- Verb presence (using spaCy POS tagging)
- Length constraints (4-8 words)
- Fragment detection (structural completeness)
"""
from typing import List, Dict, Optional
import re

try:
    import spacy
    from spacy.language import Language

    _nlp: Language | None = spacy.load("fr_core_news_sm")
except Exception:  # pragma: no cover - fallback when spaCy model not present
    _nlp = None


class QualityGate:
    """Battleship Phase 1.3: The Quality Gate - Ensures audio-ready sentences only."""
    
    # Fragment indicators: sentences starting with these are likely fragments
    FRAGMENT_STARTERS = {
        'dans', 'sur', 'avec', 'sans', 'pour', 'sous', 'entre', 'vers',
        'depuis', 'pendant', 'après', 'avant', 'et', 'mais', 'donc',
        'car', 'or', 'ni', 'de', 'du', 'des', 'à', 'au', 'aux'
    }
    
    def __init__(self, min_words: int = 4, max_words: int = 8):
        """Initialize Quality Gate with configurable word limits.
        
        Args:
            min_words: Minimum word count (default 4)
            max_words: Maximum word count (default 8)
        """
        self._nlp = _nlp
        self.min_words = min_words
        self.max_words = max_words

    def has_verb(self, sentence: str) -> bool:
        """Return True if sentence contains a verb (Phase 1.3 Check #1).

        If spaCy is available uses POS tags. Otherwise, uses a naive verb lookup.
        Accepts both VERB and AUX (auxiliary verbs like être, avoir).
        """
        if self._nlp:
            doc = self._nlp(sentence)
            for tok in doc:
                if tok.pos_ in ("VERB", "AUX"):
                    return True
            return False

        # Fallback naive check (expanded verb list for better coverage)
        naive_verbs = {
            "être", "avoir", "faire", "aller", "venir", "dire", "voir", "prendre",
            "pouvoir", "vouloir", "devoir", "savoir", "falloir", "mettre", "donner",
            "passer", "trouver", "rester", "partir", "arriver", "croire", "tenir"
        }
        tokens = [t.strip(".,;:!?()\"'«»") for t in sentence.lower().split()]
        return any(tok in naive_verbs for tok in tokens)

    def token_count(self, sentence: str) -> int:
        """Return token count for the sentence (Phase 1.3 Check #2).

        Uses spaCy tokenization when available, otherwise splits on whitespace.
        """
        if self._nlp:
            doc = self._nlp(sentence)
            # filter punctuation tokens
            return sum(1 for t in doc if not t.is_punct and not t.is_space)
        return len([t for t in sentence.split() if t.strip()])

    def is_fragment(self, sentence: str) -> bool:
        """Detect if sentence is likely a fragment (Phase 1.3 Check #3).
        
        A fragment is detected by:
        1. Missing proper capitalization at start
        2. Missing proper punctuation at end
        3. Starting with fragment-prone prepositions/conjunctions
        4. Being a dependent clause without main clause
        
        Returns:
            True if sentence appears to be a fragment
        """
        if not sentence or not sentence.strip():
            return True
            
        sentence = sentence.strip()
        
        # Check 1: Must start with capital letter (ignore leading quotes/dashes)
        leading_strip = '«"\'\(\[—–-\s'
        i = 0
        while i < len(sentence) and sentence[i] in ' «"\'\(\[—–-':
            i += 1
        if i < len(sentence):
            if not sentence[i].isupper():
                return True
        else:
            return True
        
        # Check 2: Must end with proper punctuation (allow closing quotes)
        j = len(sentence) - 1
        while j >= 0 and sentence[j] in ' »"\'\)]':
            j -= 1
        if j < 0 or sentence[j] not in '.!?…':
            return True
        
        # Check 3: Check for fragment-prone starters
        # Extract first word (lowercased, without punctuation)
        first_word = sentence.split()[0].lower().strip('«"\'')
        if first_word in self.FRAGMENT_STARTERS:
            # Could be a fragment - additional verification needed
            # If it's very short and starts with preposition, likely fragment
            word_count = len(sentence.split())
            if word_count < 5:  # Short sentences starting with prepositions are suspect
                return True
        
        # Check 4: Very simple dependent clause detection
        # Sentences that are just "Participle phrase." or "Adjective phrase."
        if self._nlp:
            doc = self._nlp(sentence)
            # Count content tokens (exclude punctuation)
            content_tokens = [t for t in doc if not t.is_punct and not t.is_space]
            
            # If no verb at all, definitely a fragment (redundant with has_verb but explicit here)
            has_any_verb = any(t.pos_ in ("VERB", "AUX") for t in content_tokens)
            if not has_any_verb:
                return True
            
            # Check for participial phrases without auxiliary
            # e.g., "Marchant lentement." vs "Il marchait lentement."
            verbs = [t for t in content_tokens if t.pos_ in ("VERB", "AUX")]
            if verbs and len(content_tokens) <= 4:
                # If only verb is a participle and there's no subject, likely fragment
                first_verb = verbs[0]
                if first_verb.pos_ == "VERB" and first_verb.tag_ in ["VBG", "VBN"]:
                    # Check if there's a clear subject (pronoun or noun before verb)
                    has_subject = any(
                        t.pos_ in ["PRON", "PROPN", "NOUN"] and t.i < first_verb.i 
                        for t in content_tokens
                    )
                    if not has_subject:
                        return True
        
        # If all checks pass, not a fragment
        return False

    def validate_sentence(self, sentence: str) -> Dict[str, any]:
        """Validate a single sentence against all quality criteria.
        
        Returns a dictionary with validation results:
        {
            'valid': bool,
            'sentence': str,
            'reasons': List[str]  # reasons for rejection if invalid
        }
        """
        reasons = []
        
        if not isinstance(sentence, str):
            return {'valid': False, 'sentence': sentence, 'reasons': ['Not a string']}
        
        sentence = sentence.strip()
        if not sentence:
            return {'valid': False, 'sentence': sentence, 'reasons': ['Empty sentence']}
        
        # Check 1: Verb presence
        if not self.has_verb(sentence):
            reasons.append('No verb found')
        
        # Check 2: Length check
        tc = self.token_count(sentence)
        if tc < self.min_words:
            reasons.append(f'Too short ({tc} words, min {self.min_words})')
        elif tc > self.max_words:
            reasons.append(f'Too long ({tc} words, max {self.max_words})')
        
        # Check 3: Fragment check
        if self.is_fragment(sentence):
            reasons.append('Likely fragment (incomplete structure)')
        
        return {
            'valid': len(reasons) == 0,
            'sentence': sentence,
            'reasons': reasons
        }

    def validate_sentences(self, sentences: List[str], return_details: bool = False) -> List[str] | List[Dict]:
        """Validate a list of candidate sentences and return only those that pass.

        Phase 1.3 Requirements:
        - Must contain a verb (spaCy POS tagging)
        - Must have token count between min_words and max_words (inclusive)
        - Must not be a fragment (complete grammatical structure)
        
        Args:
            sentences: List of candidate sentences
            return_details: If True, return validation details for each sentence
            
        Returns:
            If return_details=False: List of valid sentences
            If return_details=True: List of validation result dicts
        """
        results: List[str] = []
        details: List[Dict] = []
        
        for s in sentences:
            try:
                validation = self.validate_sentence(s)
                
                if return_details:
                    details.append(validation)
                
                if validation['valid']:
                    results.append(s)
                    
            except Exception as e:
                # On any unexpected error skip the sentence (defensive)
                if return_details:
                    details.append({
                        'valid': False,
                        'sentence': s,
                        'reasons': [f'Validation error: {str(e)}']
                    })
                continue
        
        return details if return_details else results


quality_gate = QualityGate()

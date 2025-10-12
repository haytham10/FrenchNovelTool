"""Quality Gate service: validates sentences returned by the LLM.

This module provides a small API used by the Battleship Phase 1.3 agent.
It tries to use spaCy if available; if not, it falls back to a lightweight tokenizer
and a naive verb check using a small verb list. The Phase 1.3 agent should
replace the fallback with spaCy in production.
"""
from typing import List

try:
    import spacy
    from spacy.language import Language

    _nlp: Language | None = spacy.load("fr_core_news_sm")
except Exception:  # pragma: no cover - fallback when spaCy model not present
    _nlp = None


class QualityGate:
    def __init__(self):
        self._nlp = _nlp

    def has_verb(self, sentence: str) -> bool:
        """Return True if sentence contains a verb.

        If spaCy is available uses POS tags. Otherwise, uses a naive verb lookup.
        """
        if self._nlp:
            doc = self._nlp(sentence)
            for tok in doc:
                if tok.pos_ == "VERB":
                    return True
            return False

        # Fallback naive check (very small verb list)
        naive_verbs = {"être", "avoir", "faire", "aller", "venir", "dire", "voir", "prendre"}
        tokens = [t.strip(".,;:!?()\"'«»") for t in sentence.lower().split()]
        return any(tok in naive_verbs for tok in tokens)

    def token_count(self, sentence: str) -> int:
        """Return token count for the sentence.

        Uses spaCy tokenization when available, otherwise splits on whitespace.
        """
        if self._nlp:
            doc = self._nlp(sentence)
            # filter punctuation tokens
            return sum(1 for t in doc if not t.is_punct and not t.is_space)
        return len([t for t in sentence.split() if t.strip()])

    def validate_sentences(self, sentences: List[str]) -> List[str]:
        """Validate a list of candidate sentences and return only those that pass.

        Rules:
        - Must contain a verb
        - Must have token count between 4 and 8 (inclusive)
        """
        results: List[str] = []
        for s in sentences:
            try:
                if not isinstance(s, str):
                    continue
                tc = self.token_count(s)
                if tc < 4 or tc > 8:
                    continue
                if not self.has_verb(s):
                    continue
                results.append(s)
            except Exception:
                # On any unexpected error skip the sentence (defensive)
                continue
        return results


quality_gate = QualityGate()

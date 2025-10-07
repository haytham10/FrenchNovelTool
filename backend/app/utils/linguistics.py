"""Linguistics utilities for French text processing with spaCy"""
import logging
from typing import List, Dict, Set, Optional, Tuple
import unicodedata
import re

logger = logging.getLogger(__name__)

# Lazy loading of spaCy to avoid import errors if not installed
_nlp = None


def get_nlp():
    """Lazy load spaCy French model."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            # Prefer the medium French model, but fall back to the small model if the
            # medium model isn't available. Avoid attempting an automatic download
            # inside worker processes because network access or pip installs can
            # fail in ephemeral environments (and was observed to produce HTTP 404
            # errors). If neither model is available, fall back to the DummyNLP
            # which provides a graceful degradation.
            import os
            preferred = os.environ.get("SPACY_MODEL", "fr_core_news_md")
            tried = []
            for model in (preferred, "fr_core_news_sm"):
                if model in tried:
                    continue
                tried.append(model)
                try:
                    _nlp = spacy.load(model)
                    logger.info("Loaded spaCy French model: %s", model)
                    break
                except OSError:
                    logger.warning("spaCy model %s not found, will try next fallback", model)
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            # Return a dummy object that will cause graceful degradation
            class DummyNLP:
                def __call__(self, text):
                    class DummyDoc:
                        def __iter__(self):
                            # Simple whitespace tokenization fallback
                            for word in text.split():
                                yield type('Token', (), {'text': word, 'lemma_': word.lower()})()
                    return DummyDoc()
            _nlp = DummyNLP()
    return _nlp


class LinguisticsUtils:
    """Utilities for French text processing, tokenization, and lemmatization"""
    
    @staticmethod
    def normalize_text(text: str, fold_diacritics: bool = True) -> str:
        """
        Normalize text for matching.
        
        Args:
            text: Input text
            fold_diacritics: Whether to remove diacritics
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Trim and casefold
        text = text.strip().casefold()
        
        # Remove zero-width characters
        text = re.sub(r'[\u200b-\u200f\ufeff]', '', text)
        
        # Fold diacritics if requested
        if fold_diacritics:
            text = ''.join(
                c for c in unicodedata.normalize('NFD', text)
                if unicodedata.category(c) != 'Mn'
            )
        
        # Strip apostrophes which can cause matching issues
        text = text.replace("'", "")
        
        return text
    
    @staticmethod
    def handle_elision(word: str) -> str:
        """
        Handle French elisions (l', d', etc.) by extracting the lexical head.
        This is a simple implementation; a more robust solution might use POS tagging.
        
        Args:
            word: Input word potentially with elision
            
        Returns:
            Word with elision removed
        """
        # Elision prefixes in French (case-insensitive)
        elision_prefixes = ["l'", "d'", "j'", "n'", "s'", "t'", "c'", "qu'"]
        
        word_lower = word.lower()
        for prefix in elision_prefixes:
            if word_lower.startswith(prefix):
                return word[len(prefix):]
        
        return word
    
    @staticmethod
    def tokenize_and_lemmatize(
        text: str,
        fold_diacritics: bool = True,
        handle_elisions: bool = True
    ) -> List[Dict[str, str]]:
        """
        Tokenize and lemmatize French text using spaCy.
        
        Args:
            text: Input text to process
            fold_diacritics: Whether to remove diacritics
            handle_elisions: Whether to handle elisions
            
        Returns:
            List of dicts with 'surface', 'lemma', 'normalized' keys
        """
        nlp = get_nlp()
        doc = nlp(text)
        
        tokens = []
        for token in doc:
            # Skip punctuation and whitespace
            # Use getattr for compatibility with DummyNLP fallback
            if getattr(token, 'is_punct', False) or getattr(token, 'is_space', False):
                continue
            
            surface = token.text
            
            # Handle elisions on the surface form *before* lemmatization
            if handle_elisions:
                surface_for_lemma = LinguisticsUtils.handle_elision(surface)
            else:
                surface_for_lemma = surface

            # Get lemma from the (potentially elision-handled) surface form
            # We create a temporary doc to get the lemma of the modified surface form
            temp_doc = nlp(surface_for_lemma)
            lemma = temp_doc[0].lemma_.lower() if temp_doc and len(temp_doc) > 0 else surface_for_lemma.lower()

            # Normalize the final lemma
            normalized = LinguisticsUtils.normalize_text(lemma, fold_diacritics=fold_diacritics)
            
            if not normalized:
                continue

            tokens.append({
                'surface': surface,
                'lemma': lemma,
                'normalized': normalized
            })
        
        return tokens
    
    @staticmethod
    def match_tokens_to_wordlist(
        tokens: List[Dict[str, str]],
        wordlist_keys: Set[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Match tokenized sentence against word list keys.
        
        Args:
            tokens: List of token dicts from tokenize_and_lemmatize
            wordlist_keys: Set of normalized word keys from word list
            
        Returns:
            Tuple of (matched_words, unmatched_words) as normalized keys
        """
        matched = []
        unmatched = []
        
        for token in tokens:
            normalized = token['normalized']
            if normalized in wordlist_keys:
                matched.append(normalized)
            else:
                unmatched.append(normalized)
        
        return matched, unmatched
    
    @staticmethod
    def calculate_in_list_ratio(
        sentence: str,
        wordlist_keys: Set[str],
        fold_diacritics: bool = True,
        handle_elisions: bool = True
    ) -> Tuple[float, int, int]:
        """
        Calculate the ratio of tokens in a sentence that are in the word list.
        
        Args:
            sentence: Input sentence
            wordlist_keys: Set of normalized word keys
            fold_diacritics: Whether to fold diacritics
            handle_elisions: Whether to handle elisions
            
        Returns:
            Tuple of (ratio, matched_count, total_count)
        """
        tokens = LinguisticsUtils.tokenize_and_lemmatize(
            sentence,
            fold_diacritics=fold_diacritics,
            handle_elisions=handle_elisions
        )
        
        if not tokens:
            return 0.0, 0, 0
        
        matched, _ = LinguisticsUtils.match_tokens_to_wordlist(tokens, wordlist_keys)
        
        ratio = len(matched) / len(tokens) if tokens else 0.0
        return ratio, len(matched), len(tokens)
    
    @staticmethod
    def find_word_in_sentence(
        word_key: str,
        sentence: str,
        fold_diacritics: bool = True,
        handle_elisions: bool = True
    ) -> Optional[str]:
        """
        Find if a word key appears in a sentence and return the surface form.
        
        Args:
            word_key: Normalized word key to find
            sentence: Sentence to search in
            fold_diacritics: Whether to fold diacritics
            handle_elisions: Whether to handle elisions
            
        Returns:
            Surface form if found, None otherwise
        """
        tokens = LinguisticsUtils.tokenize_and_lemmatize(
            sentence,
            fold_diacritics=fold_diacritics,
            handle_elisions=handle_elisions
        )
        
        for token in tokens:
            if token['normalized'] == word_key:
                return token['surface']
        
        return None

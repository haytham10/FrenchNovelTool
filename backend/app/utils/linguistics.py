"""Linguistics utilities for French text processing with spaCy"""
import logging
from typing import List, Dict, Set, Optional, Tuple
import unicodedata
import re

logger = logging.getLogger(__name__)

# Lazy loading of spaCy to avoid import errors if not installed
_nlp = None


def get_nlp():
    """Lazy load spaCy French model.

    Notes:
        - To reduce memory usage, we disable heavy components not needed for our
          use-cases (parser, ner). POS tagging and lemmatization remain enabled.
        - Model name can be controlled via SPACY_MODEL env var.
        - Components to disable can be controlled via SPACY_DISABLE env var
          (comma-separated), defaults to "parser,ner".
    """
    global _nlp
    if _nlp is None:
        # Allow an environment override to force the DummyNLP (useful on
        # memory-constrained hosts where loading any spaCy model would cause
        # worker OOMs). Set SPACY_FORCE_DUMMY=true to enable.
        import os
        force_dummy = os.environ.get('SPACY_FORCE_DUMMY', 'false').lower() in ('1', 'true', 'yes')
        if force_dummy:
            logger.info('SPACY_FORCE_DUMMY is set; using DummyNLP to avoid loading spaCy model')
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

        try:
            import spacy
            # Prefer the medium French model, but fall back to the small model if the
            # medium model isn't available. Avoid attempting an automatic download
            # inside worker processes because network access or pip installs can
            # fail in ephemeral environments (and was observed to produce HTTP 404
            # errors). If neither model is available, fall back to the DummyNLP
            # which provides a graceful degradation.
            import os
            preferred = os.environ.get("SPACY_MODEL", "fr_core_news_sm")
            tried = []
            # Determine disabled components to save RAM
            disable_env = os.environ.get("SPACY_DISABLE", "parser,ner").strip()
            disable = [c.strip() for c in disable_env.split(",") if c.strip()]

            for model in (preferred, "fr_core_news_sm"):
                if model in tried:
                    continue
                tried.append(model)
                try:
                    _nlp = spacy.load(model, disable=disable)
                    # Add sentencizer for sentence boundary detection when parser is disabled
                    if "parser" in disable and "sentencizer" not in _nlp.pipe_names:
                        _nlp.add_pipe("sentencizer")
                    logger.info("Loaded spaCy French model: %s (disable=%s)", model, ",".join(disable))
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


def preload_spacy(model_name: Optional[str] = None) -> None:
    """Preload spaCy model to enable copy-on-write memory sharing in forked workers.

    Call this in the Celery parent process before worker processes are forked so
    that model memory pages are shared among children (dramatically reducing RSS).

    Args:
        model_name: Optional explicit model to load; if not provided, env var
            SPACY_MODEL or the default inside get_nlp() will be used.
    """
    # If a specific model is requested, honor it via environment override for this load
    if model_name:
        import os
        os.environ.setdefault("SPACY_MODEL", model_name)
    nlp = get_nlp()
    # Touch the pipeline to ensure it's fully initialized
    try:
        _ = nlp.pipe_names  # noqa: F841
    except Exception:  # pragma: no cover
        pass


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
    def normalize_french_lemma(lemma: str) -> str:
        """
        Enhanced French lemma normalization for better word matching.
        Handles French-specific quirks before matching against word lists.

        This function addresses:
        - Elisions: l' → le, d' → de, j' → je, qu' → que, etc.
        - Reflexive pronouns: se_ prefix removal (from spaCy lemmas)
        - Case and whitespace standardization

        Args:
            lemma: Input lemma to normalize

        Returns:
            Normalized lemma suitable for word list matching
        """
        if not lemma:
            return ""

        # Trim and lowercase
        lemma = lemma.strip().lower()

    # Handle reflexive pronouns FIRST: spaCy often lemmatizes reflexive verbs
        # with a "se_" or "s'" prefix (e.g., "se_laver", "s'appeler").
        # Strip this prefix to match against word lists that contain the base verb form.
        # Note: "s'" as an elision of "si" (e.g., "s'il" = "si il") won't appear in
        # lemma form because spaCy tokenizes it as separate tokens.
        if lemma.startswith("se_"):
            lemma = lemma[3:]  # Remove "se_"
        elif lemma.startswith("s'"):
            lemma = lemma[2:]  # Remove "s'"

        # Handle elisions: expand common contractions
        # Note: We do this AFTER reflexive pronoun handling to avoid confusion with s'
        elision_expansions = {
            "l'": "le",
            "d'": "de",
            "j'": "je",
            "qu'": "que",
            "n'": "ne",
            "t'": "te",
            "c'": "ce",
            "m'": "me",
        }

        for contraction, expansion in elision_expansions.items():
            if lemma.startswith(contraction):
                # Replace the contraction with the full form
                lemma = expansion + lemma[len(contraction):]
                break

        # Remove any remaining apostrophes that might interfere with matching
        lemma = lemma.replace("'", "")

        # Normalize whitespace
        lemma = " ".join(lemma.split())

        return lemma
    
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
            if getattr(token, 'is_punct', False) or getattr(token, 'is_space', False):
                continue

            surface = token.text

            # For performance, avoid creating a temporary doc per-token.
            # Use the token's lemma_ provided by spaCy and include POS information so
            # callers can make content-word decisions without re-running the pipeline.
            lemma = getattr(token, 'lemma_', surface).lower()
            pos = getattr(token, 'pos_', None)

            # If requested, apply simple elision handling to the surface before
            # normalizing. We do not re-run the pipeline here for performance.
            if handle_elisions:
                surface_for_norm = LinguisticsUtils.handle_elision(surface)
            else:
                surface_for_norm = surface

            # Apply French-specific lemma normalization first (handles elisions, reflexives)
            # then apply general text normalization (diacritics, etc.)
            lemma_normalized = LinguisticsUtils.normalize_french_lemma(lemma if lemma else surface_for_norm)
            normalized = LinguisticsUtils.normalize_text(lemma_normalized, fold_diacritics=fold_diacritics)

            if not normalized:
                logger.debug(f"Skipping empty normalized token from lemma '{lemma}'")
                continue

            logger.debug(f"Token: surface='{surface}', lemma='{lemma}', normalized='{normalized}', pos='{pos}'")

            tokens.append({
                'surface': surface,
                'lemma': lemma,
                'normalized': normalized,
                'pos': pos
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

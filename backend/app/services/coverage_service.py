"""Service for vocabulary coverage analysis (Coverage and Filter modes)"""
import logging
import os
import datetime
from typing import Dict, List, Set, Tuple, Optional, Callable, Any
from collections import defaultdict
import heapq
from app.utils.linguistics import LinguisticsUtils

logger = logging.getLogger(__name__)


class CoverageService:
    """Handles vocabulary coverage analysis in Coverage and Filter modes"""

    def __init__(
        self,
        wordlist_keys: Set[str],
        config: Optional[Dict] = None,
    ):
        """
        Initialize coverage service.

        Args:
            wordlist_keys: Set of normalized word keys from word list
            config: Configuration dict with mode-specific settings
        """
        self.wordlist_keys = wordlist_keys
        self.config = config or {}

        # Filter mode defaults
        self.len_min = self.config.get('len_min', 3)
        self.len_max = self.config.get('len_max', 8)
        self.target_count = self.config.get('target_count', 500)

        # Scaled min_in_list_ratio for filter mode
        self.scaled_min_ratios = self.config.get('scaled_min_ratios', {
            3: 0.99, 4: 0.99, 5: 0.9, 6: 0.8, 7: 0.7, 8: 0.65
        })
        self.default_min_ratio = self.config.get('default_min_ratio', 0.6)

        # Normalization settings
        self.fold_diacritics = self.config.get('fold_diacritics', True)
        self.handle_elisions = self.config.get('handle_elisions', True)
    
    def build_sentence_index(self, sentences: List[str]) -> Dict[int, Dict]:
        """
        Build an index of sentences with their token information.
        
        Args:
            sentences: List of sentence strings
            
        Returns:
            Dict mapping sentence_index -> {text, tokens, words_in_list, ratio, ...}
        """
        index = {}

        # Attempt to batch-process sentences with spaCy's pipe to greatly reduce
        # overhead when tokenizing many sentences. If spaCy's nlp doesn't support
        # pipe (e.g., DummyNLP fallback), fall back to per-sentence tokenization.
        try:
            from app.utils.linguistics import get_nlp
            nlp = get_nlp()
        except Exception:
            nlp = None

        if nlp is not None and hasattr(nlp, 'pipe'):
            docs = nlp.pipe(sentences)
            for idx, (sentence, doc) in enumerate(zip(sentences, docs)):
                tokens = []
                for token in doc:
                    if getattr(token, 'is_punct', False) or getattr(token, 'is_space', False):
                        continue

                    surface = token.text
                    lemma = getattr(token, 'lemma_', surface).lower()
                    pos = getattr(token, 'pos_', None)

                    if self.handle_elisions:
                        surface_for_norm = LinguisticsUtils.handle_elision(surface)
                    else:
                        surface_for_norm = surface

                    normalized_source = lemma if lemma else surface_for_norm
                    normalized = LinguisticsUtils.normalize_text(normalized_source, fold_diacritics=self.fold_diacritics)

                    if not normalized:
                        continue

                    tokens.append({
                        'surface': surface,
                        'lemma': lemma,
                        'normalized': normalized,
                        'pos': pos
                    })

                matched, unmatched = LinguisticsUtils.match_tokens_to_wordlist(tokens, self.wordlist_keys)
                ratio = len(matched) / len(tokens) if tokens else 0.0

                index[idx] = {
                    'text': sentence,
                    'tokens': tokens,
                    'token_count': len(tokens),
                    'words_in_list': set(matched),
                    'words_not_in_list': set(unmatched),
                    'in_list_ratio': ratio,
                    'sentence_obj': sentence
                }
        else:
            # Fallback: per-sentence tokenization
            for idx, sentence in enumerate(sentences):
                tokens = LinguisticsUtils.tokenize_and_lemmatize(
                    sentence,
                    fold_diacritics=self.fold_diacritics,
                    handle_elisions=self.handle_elisions
                )

                matched, unmatched = LinguisticsUtils.match_tokens_to_wordlist(tokens, self.wordlist_keys)
                ratio = len(matched) / len(tokens) if tokens else 0.0

                index[idx] = {
                    'text': sentence,
                    'tokens': tokens,
                    'token_count': len(tokens),
                    'words_in_list': set(matched),
                    'words_not_in_list': set(unmatched),
                    'in_list_ratio': ratio,
                    'sentence_obj': sentence
                }

        return index
    
    @staticmethod
    def count_content_words_in_matched(sentence_text: str, matched_words: Set[str], 
                                       fold_diacritics: bool = True, 
                                       handle_elisions: bool = True) -> int:
        """
        Count how many of the matched words are "content words" (nouns, verbs, adjectives, adverbs).
        
        Args:
            sentence_text: The original sentence text
            matched_words: Set of normalized matched words from word list
            fold_diacritics: Whether diacritics were folded
            handle_elisions: Whether elisions were handled
            
        Returns:
            Count of matched content words
        """
        # This helper is kept for backward compatibility but prefers tokenized
        # input from build_sentence_index. When used directly with sentence text,
        # it falls back to tokenizing via LinguisticsUtils.tokenize_and_lemmatize.
        from app.utils.linguistics import LinguisticsUtils

        if not matched_words:
            return 0

        content_pos_tags = {'NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN'}

        # Try to use pre-tokenized form if available (caller may pass sentence_text
        # as a dict with tokens). If it's a raw string, tokenize once.
        tokens = None
        if isinstance(sentence_text, dict) and 'tokens' in sentence_text:
            tokens = sentence_text['tokens']
        else:
            tokens = LinguisticsUtils.tokenize_and_lemmatize(
                sentence_text,
                fold_diacritics=fold_diacritics,
                handle_elisions=handle_elisions
            )

        content_count = 0
        for token in tokens:
            pos = token.get('pos') if isinstance(token, dict) else None
            if pos is None:
                # If pos not available, be conservative and treat as non-content
                continue

            normalized = token.get('normalized') if isinstance(token, dict) else None
            if normalized in matched_words and pos in content_pos_tags:
                content_count += 1

        return content_count
    
    @staticmethod
    def filter_content_words_only(sentence_text: str, wordlist_keys: Set[str],
                                   fold_diacritics: bool = True,
                                   handle_elisions: bool = True) -> Set[str]:
        """
        Match words from the sentence against the wordlist, but only return content words.
        This filters out function words (pronouns, determiners, conjunctions) so they don't
        contribute to vocabulary coverage metrics.
        
        Args:
            sentence_text: The original sentence text
            wordlist_keys: Set of normalized word keys from word list
            fold_diacritics: Whether diacritics were folded
            handle_elisions: Whether elisions were handled
            
        Returns:
            Set of normalized content words that are in the wordlist
        """
        from app.utils.linguistics import LinguisticsUtils

        if not wordlist_keys:
            return set()

        content_pos_tags = {'NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN'}

        # If caller passed a pre-tokenized sentence dict, use it directly.
        matched_content = set()
        if isinstance(sentence_text, dict) and 'tokens' in sentence_text:
            tokens = sentence_text['tokens']
            for token in tokens:
                pos = token.get('pos')
                if pos not in content_pos_tags:
                    continue
                normalized = token.get('normalized')
                if normalized in wordlist_keys:
                    matched_content.add(normalized)
            return matched_content

        # Fallback: tokenize once and process tokens
        tokens = LinguisticsUtils.tokenize_and_lemmatize(
            sentence_text,
            fold_diacritics=fold_diacritics,
            handle_elisions=handle_elisions
        )

        for token in tokens:
            pos = token.get('pos')
            if pos not in content_pos_tags:
                continue
            normalized = token.get('normalized')
            if normalized in wordlist_keys:
                matched_content.add(normalized)

        return matched_content
    
    def coverage_mode_greedy(
        self,
        sentences: List[str],
        progress_callback: Optional[Callable[[int], Any]] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Coverage Mode: Greedy algorithm to select sentences that cover all words.
        
        Scoring: Score = (new_words × 10) - sentence_length
        Goal: Cover all 2000 target words in 500 sentences or less.
        
        Args:
            sentences: List of sentence strings
            progress_callback: Optional progress callback
            
        Returns:
            Tuple of (assignments, stats)
        """
        # Build sentence index
        sentence_index = self.build_sentence_index(sentences)
        if progress_callback:
            try:
                progress_callback(10)
            except Exception:
                pass
        
        # Track uncovered words
        uncovered_words = self.wordlist_keys.copy()
        
        # Track assignments and selections
        assignments = []
        word_to_sentence = {}
        selected_sentence_order = []
        selected_sentence_set = set()
        sentence_contribution = defaultdict(int)
        sentence_selection_score = {}
        
        max_sentences = 500
        
        # Greedy selection loop
        while uncovered_words and len(selected_sentence_order) < max_sentences:
            best_idx = None
            best_score = float('-inf')
            best_new_words = set()
            
            # Find the sentence with the highest score
            for idx, info in sentence_index.items():
                if idx in selected_sentence_set:
                    continue
                    
                # Get content words in this sentence that are in wordlist
                sentence_words = self.filter_content_words_only(
                    info,
                    self.wordlist_keys,
                    fold_diacritics=self.fold_diacritics,
                    handle_elisions=self.handle_elisions
                )
                
                # Find NEW words (not yet covered)
                new_words = sentence_words & uncovered_words
                
                if not new_words:
                    continue
                
                # Calculate score: (new_words × 10) - sentence_length
                score = (len(new_words) * 10) - info['token_count']
                
                if score > best_score:
                    best_score = score
                    best_idx = idx
                    best_new_words = new_words
            
            # If no sentence can cover new words, stop
            if best_idx is None:
                break
            
            # Select this sentence
            selected_sentence_set.add(best_idx)
            selected_sentence_order.append(best_idx)
            sentence_contribution[best_idx] = len(best_new_words)
            sentence_selection_score[best_idx] = best_score
            
            # Mark words as covered
            for word_key in best_new_words:
                word_to_sentence[word_key] = best_idx
                uncovered_words.discard(word_key)
            
            # Progress callback
            if progress_callback:
                try:
                    covered = len(word_to_sentence)
                    total = len(self.wordlist_keys) if self.wordlist_keys else 1
                    pct = 10 + int(85 * (covered / total))
                    pct = min(max(pct, 10), 95)
                    progress_callback(pct)
                except Exception:
                    pass
        
        # Build assignments list
        for word_key, sentence_idx in word_to_sentence.items():
            sentence_info = sentence_index[sentence_idx]
            matched_surface = LinguisticsUtils.find_word_in_sentence(
                word_key,
                sentence_info['text'],
                fold_diacritics=self.fold_diacritics,
                handle_elisions=self.handle_elisions
            )
            
            assignments.append({
                'word_key': word_key,
                'word_original': word_key,
                'lemma': word_key,
                'matched_surface': matched_surface,
                'sentence_index': sentence_idx,
                'sentence_text': sentence_info['text'],
                'sentence_score': sentence_info['in_list_ratio']
            })
        
        # Calculate statistics
        covered_words = set(word_to_sentence.keys())
        stats = {
            'words_total': len(self.wordlist_keys),
            'words_covered': len(covered_words),
            'uncovered_words': len(uncovered_words),
            'selected_sentence_count': len(selected_sentence_set),
            'learning_set_count': len(selected_sentence_order),
            'learning_set': [
                {
                    'rank': rank,
                    'sentence_index': idx,
                    'sentence_text': sentence_index[idx]['text'],
                    'token_count': sentence_index[idx]['token_count'],
                    'new_word_count': sentence_contribution.get(idx, 0),
                    'score': sentence_selection_score.get(idx),
                }
                for rank, idx in enumerate(selected_sentence_order, start=1)
            ],
        }

        # Log covered and uncovered words to files
        self._log_word_sets(covered_words, uncovered_words)

        if progress_callback:
            try:
                progress_callback(95)
            except Exception:
                pass

        logger.info(f"Coverage mode: {stats['words_covered']}/{stats['words_total']} words covered "
                   f"with {stats['selected_sentence_count']} sentences")
        
        return assignments, stats
    
    def _log_word_sets(self, covered_words: Set[str], uncovered_words: Set[str]):
        """Logs covered and uncovered words to timestamped text files."""
        log_dir = 'logs'
        try:
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            # Write covered words
            covered_filename = os.path.join(log_dir, f"coverage_covered_{timestamp}.txt")
            with open(covered_filename, 'w', encoding='utf-8') as f:
                for word in sorted(list(covered_words)):
                    f.write(f"{word}\n")

            # Write uncovered words
            uncovered_filename = os.path.join(log_dir, f"coverage_uncovered_{timestamp}.txt")
            with open(uncovered_filename, 'w', encoding='utf-8') as f:
                for word in sorted(list(uncovered_words)):
                    f.write(f"{word}\n")

        except IOError as e:
            logger.error(f"Error writing coverage word lists to file: {e}")

    def filter_mode(
        self,
        sentences: List[str],
        progress_callback: Optional[Callable[[int], Any]] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Filter Mode (revised): select ALL sentences that contain at least N content words
        (nouns, verbs, adjectives, adverbs) from the word list AND have token length <= 8.
        
        Content words = NOUN, VERB, ADJ, ADV, PROPN (excludes pronouns, determiners, etc.)
        No selection cap is applied.

    No scoring: sentences are selected if they meet the content-word and
    length criteria and returned in their original order.

        Args:
            sentences: List of sentence strings
            progress_callback: Optional callable(progress_percent: int)

        Returns:
            Tuple of (selected_sentences, stats)
        """
        # Thresholds
        min_content_words = 4  # Minimum content words (not function words)
        max_tokens = 8

        # Build sentence index
        sentence_index = self.build_sentence_index(sentences)
        if progress_callback:
            try:
                progress_callback(10)
            except Exception:
                pass

        selected: List[Dict] = []

        total = len(sentence_index) if sentence_index else 1
        # Emit periodic progress during scanning
        step = max(1, total // 50)  # ~2% granularity

        for i, (idx, info) in enumerate(sentence_index.items(), start=1):
            token_count = info['token_count']
            
            # First check basic criteria
            if token_count > max_tokens:
                if progress_callback and (i % step == 0 or i == total):
                    try:
                        pct = 10 + int(80 * (i / total))
                        pct = min(max(pct, 10), 90)
                        progress_callback(pct)
                    except Exception:
                        pass
                continue
            
            # Filter to only content words from the matched set using pre-tokenized tokens
            matched_content_words = self.filter_content_words_only(
                info,
                info['words_in_list'],
                fold_diacritics=self.fold_diacritics,
                handle_elisions=self.handle_elisions
            )
            
            content_word_count = len(matched_content_words)
            
            if content_word_count >= min_content_words:
                ratio = info['in_list_ratio'] if token_count > 0 else 0.0
                selected.append({
                    'sentence_index': idx,
                    'sentence_text': info['text'],
                    'in_list_ratio': round(ratio, 3),
                    'token_count': token_count,
                    'words_in_list': list(matched_content_words),  # Only content words
                    'content_word_count': content_word_count
                })

            if progress_callback and (i % step == 0 or i == total):
                try:
                    pct = 10 + int(80 * (i / total))
                    pct = min(max(pct, 10), 90)
                    progress_callback(pct)
                except Exception:
                    pass

    # No sorting/scoring: preserve original sentence order for selected results

        # Stats (preserve some keys for compatibility)
        selected_count = len(selected)
        stats = {
            'total_sentences': len(sentences),
            'selected_count': selected_count,
            'filter_acceptance_ratio': (selected_count / len(sentences)) if sentences else 0.0,
            'min_content_words': min_content_words,
            'max_tokens': max_tokens,
            # Compatibility fields retained (not used by this simplified filter):
            'scaled_min_ratios': self.scaled_min_ratios,
            'default_min_ratio': self.default_min_ratio,
            'len_min': self.len_min,
            'len_max': self.len_max,
            'target_count': self.target_count,
            'candidates_by_pass': {
                'content_words_>=4_len_<=8': selected_count
            },
        }

        logger.info(
            "Filter mode (>= %s content words): %s/%s sentences selected",
            min_content_words, selected_count, len(sentences)
        )

        if progress_callback:
            try:
                progress_callback(95)
            except Exception:
                pass

        return selected, stats

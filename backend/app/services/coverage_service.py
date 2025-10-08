"""Service for vocabulary coverage analysis (Coverage and Filter modes)"""
import logging
from typing import Dict, List, Set, Tuple, Optional, Callable, Any
from collections import defaultdict
from app.utils.linguistics import LinguisticsUtils

logger = logging.getLogger(__name__)


class CoverageService:
    """Handles vocabulary coverage analysis in Coverage and Filter modes"""
    
    def __init__(self, wordlist_keys: Set[str], config: Optional[Dict] = None):
        """
        Initialize coverage service.
        
        Args:
            wordlist_keys: Set of normalized word keys from word list
            config: Configuration dict with mode-specific settings
        """
        self.wordlist_keys = wordlist_keys
        self.config = config or {}
        logger.info(f"CoverageService initialized with {len(wordlist_keys)} wordlist keys. Sample: {list(wordlist_keys)[:10]}")

        # Coverage mode defaults
        self.alpha = self.config.get('alpha', 0.5)  # Duplicate penalty weight
        self.beta = self.config.get('beta', 0.3)   # Quality weight
        self.gamma = self.config.get('gamma', 0.2)  # Length penalty weight
        self.coverage_quality_weight = float(self.config.get('quality_weight', 10))
        self.coverage_length_penalty = float(self.config.get('length_penalty', 1))
        self.coverage_prune_max_tokens = self.config.get('coverage_prune_max_tokens', 8)

        # Filter mode defaults
        self.len_min = self.config.get('len_min', 3)
        self.len_max = self.config.get('len_max', 8)
        self.target_count = self.config.get('target_count', 500)

        # Scaled min_in_list_ratio: high for short sentences, lower for longer ones
        # A dict mapping token_count -> min_ratio
        self.scaled_min_ratios = self.config.get('scaled_min_ratios', {
            3: 0.99,
            4: 0.99,
            5: 0.9,
            6: 0.8,
            7: 0.7,
            8: 0.65
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
        
        for idx, sentence in enumerate(sentences):
            tokens = LinguisticsUtils.tokenize_and_lemmatize(
                sentence,
                fold_diacritics=self.fold_diacritics,
                handle_elisions=self.handle_elisions
            )
            
            matched, unmatched = LinguisticsUtils.match_tokens_to_wordlist(
                tokens,
                self.wordlist_keys
            )
            
            ratio = len(matched) / len(tokens) if tokens else 0.0
            
            index[idx] = {
                'text': sentence,
                'tokens': tokens,
                'token_count': len(tokens),
                'words_in_list': set(matched),
                'words_not_in_list': set(unmatched),
                'in_list_ratio': ratio,
                'sentence_obj': sentence  # Store original for POS analysis if needed
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
        Coverage Mode: Greedy set cover algorithm to select minimal sentences
        that cover all words in the word list.
        
        Args:
            sentences: List of sentence strings
            
        Returns:
            Tuple of (assignments, stats)
            - assignments: List of dicts with word_key, sentence_index, etc.
            - stats: Dict with coverage statistics
        """
        # Build sentence index
        sentence_index = self.build_sentence_index(sentences)
        if progress_callback:
            try:
                progress_callback(10)
            except Exception:
                pass
        
        # Optional pruning: remove long sentences before selection to tighten the pool
        candidate_sentence_index = sentence_index
        pruned_sentence_ids = set()
        prune_threshold = self.coverage_prune_max_tokens
        if prune_threshold is not None:
            candidate_sentence_index = {
                idx: info for idx, info in sentence_index.items()
                if info['token_count'] <= prune_threshold
            }
            pruned_sentence_ids = {
                idx for idx, info in sentence_index.items()
                if info['token_count'] > prune_threshold
            }
            if not candidate_sentence_index:
                logger.warning(
                    "Coverage pruning removed all sentences (threshold=%s); falling back to full set",
                    prune_threshold,
                )
                candidate_sentence_index = sentence_index
                pruned_sentence_ids = set()

        # Track uncovered words
        uncovered_words = self.wordlist_keys.copy()
        
        # Track assignments
        assignments = []
        word_to_sentence = {}  # word_key -> sentence_index

        selected_sentence_order: List[int] = []
        selected_sentence_set = set()
        sentence_contribution: Dict[int, int] = defaultdict(int)
        sentence_selection_score: Dict[int, float] = {}

        # Precompute content-word sets and token counts for the pool to avoid
        # recomputing spaCy/token processing repeatedly inside the greedy loop.
        pool_content_words: Dict[int, Set[str]] = {}
        pool_token_counts: Dict[int, int] = {}
        for idx, info in candidate_sentence_index.items():
            pool_content_words[idx] = self.filter_content_words_only(
                info,
                self.wordlist_keys,
                fold_diacritics=self.fold_diacritics,
                handle_elisions=self.handle_elisions
            )
            pool_token_counts[idx] = info['token_count']

        def _select_from_pool(pool: Dict[int, Dict]) -> None:
            nonlocal uncovered_words
            while uncovered_words:
                best_sentence_idx = None
                best_score = float('-inf')
                best_covered_words: Set[str] = set()
                best_length = None

                for idx, info in pool.items():
                    # Use precomputed content-word sets when available
                    content_words_in_sentence = pool_content_words.get(idx)
                    if content_words_in_sentence is None:
                        # Fall back to computing it once
                        content_words_in_sentence = self.filter_content_words_only(
                            info,
                            self.wordlist_keys,
                            fold_diacritics=self.fold_diacritics,
                            handle_elisions=self.handle_elisions
                        )
                        pool_content_words[idx] = content_words_in_sentence
                    
                    covered_by_this = content_words_in_sentence & uncovered_words
                    if not covered_by_this:
                        continue

                    gain = len(covered_by_this)
                    length_penalty = pool_token_counts.get(idx, info['token_count']) * self.coverage_length_penalty
                    score = (gain * self.coverage_quality_weight) - length_penalty

                    if (
                        best_sentence_idx is None
                        or score > best_score
                        or (
                            score == best_score
                            and (
                                gain > len(best_covered_words)
                                or (
                                    gain == len(best_covered_words)
                                    and (best_length is None or info['token_count'] < best_length)
                                )
                            )
                        )
                    ):
                        best_sentence_idx = idx
                        best_score = score
                        best_covered_words = covered_by_this
                        best_length = info['token_count']

                if best_sentence_idx is None:
                    break

                for word_key in best_covered_words:
                    word_to_sentence[word_key] = best_sentence_idx
                    uncovered_words.discard(word_key)

                sentence_contribution[best_sentence_idx] += len(best_covered_words)
                sentence_selection_score[best_sentence_idx] = best_score

                if best_sentence_idx not in selected_sentence_set:
                    selected_sentence_set.add(best_sentence_idx)
                    selected_sentence_order.append(best_sentence_idx)

                if progress_callback:
                    try:
                        covered = len(word_to_sentence)
                        total = len(self.wordlist_keys) if self.wordlist_keys else 1
                        pct = 10 + int(80 * (covered / total))
                        pct = min(max(pct, 10), 95)
                        progress_callback(pct)
                    except Exception:
                        pass

        # Primary pass on pruned pool
        _select_from_pool(candidate_sentence_index)

        # Fallback pass on full set if needed (captures stragglers that only exist in long sentences)
        if uncovered_words and candidate_sentence_index is not sentence_index:
            logger.info(
                "Coverage fallback: %s words remain after pruned pass; evaluating full sentence set",
                len(uncovered_words),
            )
            _select_from_pool(sentence_index)
        
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
                'word_original': word_key,  # Will be filled by caller if available
                'lemma': word_key,
                'matched_surface': matched_surface,
                'sentence_index': sentence_idx,
                'sentence_text': sentence_info['text'],
                'sentence_score': sentence_info['in_list_ratio']
            })
        
        # Calculate statistics
        stats = {
            'words_total': len(self.wordlist_keys),
            'words_covered': len(word_to_sentence),
            'words_uncovered': len(uncovered_words),
            'uncovered_words': sorted(list(uncovered_words))[:50],  # Sample
            'selected_sentence_count': len(set(word_to_sentence.values())),
            'total_sentences': len(sentences),
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
            'coverage_quality_weight': self.coverage_quality_weight,
            'coverage_length_penalty': self.coverage_length_penalty,
            'coverage_prune_max_tokens': prune_threshold,
            'pruned_sentence_count': len(pruned_sentence_ids),
        }
        
        if progress_callback:
            try:
                progress_callback(95)
            except Exception:
                pass

        logger.info(f"Coverage mode: {stats['words_covered']}/{stats['words_total']} words covered "
                   f"with {stats['selected_sentence_count']} sentences")
        
        return assignments, stats
    
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

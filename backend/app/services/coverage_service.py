"""Service for vocabulary coverage analysis (Coverage and Filter modes)"""
import logging
from typing import Dict, List, Set, Tuple, Optional
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
                'in_list_ratio': ratio
            }
        
        return index
    
    def coverage_mode_greedy(
        self,
        sentences: List[str],
        progress_callback: callable | None = None
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
        
        # Track uncovered words
        uncovered_words = self.wordlist_keys.copy()
        
        # Track assignments
        assignments = []
        word_to_sentence = {}  # word_key -> sentence_index
        
    # Greedy selection
        while uncovered_words:
            best_sentence_idx = None
            best_gain = 0
            best_covered_words = set()
            
            # Find sentence that covers most uncovered words
            for idx, info in sentence_index.items():
                covered_by_this = info['words_in_list'] & uncovered_words
                gain = len(covered_by_this)
                
                if gain > best_gain:
                    best_gain = gain
                    best_sentence_idx = idx
                    best_covered_words = covered_by_this
            
            # If no sentence covers any remaining word, break
            if best_gain == 0:
                break
            
            # Assign covered words to this sentence
            for word_key in best_covered_words:
                word_to_sentence[word_key] = best_sentence_idx
                uncovered_words.discard(word_key)

            # Emit progress based on coverage of words
            if progress_callback:
                try:
                    covered = len(word_to_sentence)
                    total = len(self.wordlist_keys) if self.wordlist_keys else 1
                    pct = 10 + int(80 * (covered / total))
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
            'total_sentences': len(sentences)
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
        progress_callback: callable | None = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Filter Mode (revised): select ALL sentences that contain at least N words
        from the word list, where N defaults to 4. No selection cap is applied.

        Scoring: integer score equal to the number of matched wordlist tokens
        in the sentence (rounded by definition).

        Args:
            sentences: List of sentence strings
            progress_callback: Optional callable(progress_percent: int)

        Returns:
            Tuple of (selected_sentences, stats)
        """
        # Threshold for minimum matched words (configurable later if needed)
        min_matched_words = 4

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
            matched_count = len(info['words_in_list'])
            if matched_count >= min_matched_words:
                # Integer score equal to matched word count
                selected.append({
                    'sentence_index': idx,
                    'sentence_text': info['text'],
                    'sentence_score': int(matched_count),
                    'in_list_ratio': info['in_list_ratio'],
                    'token_count': info['token_count'],
                    'words_in_list': list(info['words_in_list'])
                })

            if progress_callback and (i % step == 0 or i == total):
                try:
                    pct = 10 + int(80 * (i / total))
                    pct = min(max(pct, 10), 90)
                    progress_callback(pct)
                except Exception:
                    pass

        # Sort by score desc (then stable index order as tie-breaker)
        selected.sort(key=lambda x: x['sentence_score'], reverse=True)

        # Stats (preserve some keys for compatibility)
        selected_count = len(selected)
        stats = {
            'total_sentences': len(sentences),
            'selected_count': selected_count,
            'filter_acceptance_ratio': (selected_count / len(sentences)) if sentences else 0.0,
            'min_matched_words': min_matched_words,
            # Compatibility fields retained (not used by this simplified filter):
            'scaled_min_ratios': self.scaled_min_ratios,
            'default_min_ratio': self.default_min_ratio,
            'len_min': self.len_min,
            'len_max': self.len_max,
            'target_count': self.target_count,
            'candidates_by_pass': {
                'matched_words_>=4': selected_count
            },
        }

        logger.info(
            "Filter mode (>= %s matched words): %s/%s sentences selected",
            min_matched_words, selected_count, len(sentences)
        )

        if progress_callback:
            try:
                progress_callback(95)
            except Exception:
                pass

        return selected, stats

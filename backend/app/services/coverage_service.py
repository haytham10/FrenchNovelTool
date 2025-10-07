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
        
        # Coverage mode defaults
        self.alpha = self.config.get('alpha', 0.5)  # Duplicate penalty weight
        self.beta = self.config.get('beta', 0.3)   # Quality weight
        self.gamma = self.config.get('gamma', 0.2)  # Length penalty weight
        
        # Filter mode defaults
        self.min_in_list_ratio = self.config.get('min_in_list_ratio', 0.95)
        self.len_min = self.config.get('len_min', 3)
        self.len_max = self.config.get('len_max', 10)
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
        sentences: List[str]
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
        
        logger.info(f"Coverage mode: {stats['words_covered']}/{stats['words_total']} words covered "
                   f"with {stats['selected_sentence_count']} sentences")
        
        return assignments, stats
    
    def filter_mode(
        self,
        sentences: List[str]
    ) -> Tuple[List[Dict], Dict]:
        """
        Filter Mode: Select sentences with high vocabulary density and rank them.
        Uses a multi-pass approach prioritizing ideal sentence lengths.
        
        Args:
            sentences: List of sentence strings
            
        Returns:
            Tuple of (selected_sentences, stats)
            - selected_sentences: List of dicts with sentence info
            - stats: Dict with filter statistics
        """
        # Build sentence index
        sentence_index = self.build_sentence_index(sentences)
        
        # Multi-pass approach: prioritize 4-word sentences, then fall back to 3-word
        selected = []
        candidates_by_pass = {}
        
        # Pass 1: Look for 4-word sentences first (ideal length)
        pass_1_candidates = []
        for idx, info in sentence_index.items():
            token_count = info['token_count']
            ratio = info['in_list_ratio']
            
            # Use scaled ratio based on token count
            min_ratio = self.scaled_min_ratios.get(token_count, self.default_min_ratio)

            if token_count == 4 and ratio >= min_ratio:
                score = ratio * 10.0 + (1.0 / token_count) * 0.5
                pass_1_candidates.append({
                    'sentence_index': idx,
                    'sentence_text': info['text'],
                    'sentence_score': score,
                    'in_list_ratio': ratio,
                    'token_count': token_count,
                    'words_in_list': list(info['words_in_list'])
                })
        
        # Sort and select from pass 1
        pass_1_candidates.sort(key=lambda x: x['sentence_score'], reverse=True)
        selected.extend(pass_1_candidates[:self.target_count])
        candidates_by_pass['pass_1_4word'] = len(pass_1_candidates)
        
        logger.info(f"Filter mode pass 1 (4-word): {len(selected)}/{len(pass_1_candidates)} sentences selected")
        
        # Pass 2: If we don't have enough, look for 3-word sentences
        if len(selected) < self.target_count:
            remaining_needed = self.target_count - len(selected)
            pass_2_candidates = []
            
            for idx, info in sentence_index.items():
                # Skip if already selected
                if any(s['sentence_index'] == idx for s in selected):
                    continue
                
                token_count = info['token_count']
                ratio = info['in_list_ratio']
                
                # Use scaled ratio
                min_ratio = self.scaled_min_ratios.get(token_count, self.default_min_ratio)

                if token_count == 3 and ratio >= min_ratio:
                    score = ratio * 10.0 + (1.0 / token_count) * 0.5
                    pass_2_candidates.append({
                        'sentence_index': idx,
                        'sentence_text': info['text'],
                        'sentence_score': score,
                        'in_list_ratio': ratio,
                        'token_count': token_count,
                        'words_in_list': list(info['words_in_list'])
                    })
            
            # Sort and select from pass 2
            pass_2_candidates.sort(key=lambda x: x['sentence_score'], reverse=True)
            selected.extend(pass_2_candidates[:remaining_needed])
            candidates_by_pass['pass_2_3word'] = len(pass_2_candidates)
            
            logger.info(f"Filter mode pass 2 (3-word): {len(pass_2_candidates)} candidates found, "
                       f"added {min(remaining_needed, len(pass_2_candidates))} sentences")
        
        # Pass 3: If still not enough, use original range-based approach for remaining lengths
        if len(selected) < self.target_count:
            remaining_needed = self.target_count - len(selected)
            pass_3_candidates = []
            
            for idx, info in sentence_index.items():
                # Skip if already selected
                if any(s['sentence_index'] == idx for s in selected):
                    continue
                
                token_count = info['token_count']
                ratio = info['in_list_ratio']
                
                # Use scaled ratio
                min_ratio = self.scaled_min_ratios.get(token_count, self.default_min_ratio)

                # Accept sentences in the configured range, excluding 3 and 4 words (already processed)
                if (self.len_min <= token_count <= self.len_max and 
                    token_count not in [3, 4] and 
                    ratio >= min_ratio):
                    score = ratio * 10.0 + (1.0 / token_count) * 0.5
                    pass_3_candidates.append({
                        'sentence_index': idx,
                        'sentence_text': info['text'],
                        'sentence_score': score,
                        'in_list_ratio': ratio,
                        'token_count': token_count,
                        'words_in_list': list(info['words_in_list'])
                    })
            
            # Sort and select from pass 3
            pass_3_candidates.sort(key=lambda x: x['sentence_score'], reverse=True)
            selected.extend(pass_3_candidates[:remaining_needed])
            candidates_by_pass['pass_3_other'] = len(pass_3_candidates)
            
            logger.info(f"Filter mode pass 3 (other lengths): {len(pass_3_candidates)} candidates found, "
                       f"added {min(remaining_needed, len(pass_3_candidates))} sentences")
        
        # Calculate total candidates across all passes
        total_candidates = sum(candidates_by_pass.values())
        
        # Calculate statistics
        stats = {
            'total_sentences': len(sentences),
            'candidates_passed_filter': total_candidates,
            'selected_count': len(selected),
            'filter_acceptance_ratio': total_candidates / len(sentences) if sentences else 0.0,
            'scaled_min_ratios': self.scaled_min_ratios,
            'default_min_ratio': self.default_min_ratio,
            'len_min': self.len_min,
            'len_max': self.len_max,
            'target_count': self.target_count,
            'candidates_by_pass': candidates_by_pass
        }
        
        logger.info(f"Filter mode complete: {len(selected)}/{total_candidates} sentences selected "
                   f"from {len(sentences)} total (passes: {candidates_by_pass})")
        
        return selected, stats

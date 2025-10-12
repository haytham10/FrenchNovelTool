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
        self.wordlist_keys = {LinguisticsUtils.normalize_french_lemma(key) for key in wordlist_keys}
        self.config = config or {}

        # Filter mode defaults
        self.len_min = self.config.get("len_min", 3)
        self.len_max = self.config.get("len_max", 8)
        self.target_count = self.config.get("target_count", 500)

        # Scaled min_in_list_ratio for filter mode
        self.scaled_min_ratios = self.config.get(
            "scaled_min_ratios", {3: 0.99, 4: 0.99, 5: 0.9, 6: 0.8, 7: 0.7, 8: 0.65}
        )
        self.default_min_ratio = self.config.get("default_min_ratio", 0.6)

        # Normalization settings
        self.fold_diacritics = self.config.get("fold_diacritics", True)
        self.handle_elisions = self.config.get("handle_elisions", True)

    def build_sentence_index(self, sentences: List[str]) -> Dict[int, Dict]:
        index = {}

        try:
            from app.utils.linguistics import get_nlp

            nlp = get_nlp()
        except Exception:
            nlp = None

        if nlp is not None and hasattr(nlp, "pipe"):
            # Process in batches to prevent memory spikes. Batch size can be tuned
            # at runtime via the COVERAGE_SPACY_BATCH_SIZE environment variable.
            try:
                batch_size = int(os.getenv("COVERAGE_SPACY_BATCH_SIZE", "100"))
            except Exception:
                batch_size = 100
            for batch_start in range(0, len(sentences), batch_size):
                batch_end = min(batch_start + batch_size, len(sentences))
                batch_sentences = sentences[batch_start:batch_end]

                docs = nlp.pipe(batch_sentences)
                for offset, (sentence, doc) in enumerate(zip(batch_sentences, docs)):
                    idx = batch_start + offset
                    tokens = []
                    for token in doc:
                        if getattr(token, "is_punct", False) or getattr(token, "is_space", False):
                            continue

                        surface = token.text
                        lemma = getattr(token, "lemma_", surface).lower()
                        pos = getattr(token, "pos_", None)

                        if self.handle_elisions:
                            surface_for_norm = LinguisticsUtils.handle_elision(surface)
                        else:
                            surface_for_norm = surface

                        normalized_source = lemma if lemma else surface_for_norm
                        normalized = LinguisticsUtils.normalize_french_lemma(
                            LinguisticsUtils.normalize_text(
                                normalized_source, fold_diacritics=self.fold_diacritics
                            )
                        )

                        # Skip common English stopwords entirely
                        from app.utils.linguistics import is_english_stopword
                        if is_english_stopword(normalized):
                            continue

                        if not normalized:
                            continue

                        tokens.append(
                            {
                                "surface": surface,
                                "lemma": lemma,
                                "normalized": normalized,
                                "pos": pos,
                            }
                        )

                    token_count = len(tokens)
                    # Skip indexing sentences outside the configured token-length window
                    # This avoids carrying large numbers of irrelevant candidates into the
                    # greedy selection loop and can dramatically reduce runtime for large
                    # corpora. The defaults are defined on the service instance.
                    if token_count < self.len_min or token_count > self.len_max:
                        continue

                    matched, unmatched = LinguisticsUtils.match_tokens_to_wordlist(
                        tokens, self.wordlist_keys
                    )
                    ratio = len(matched) / token_count if token_count else 0.0

                    index[idx] = {
                        "text": sentence,
                        "tokens": tokens,
                        "token_count": token_count,
                        "words_in_list": set(matched),
                        "words_not_in_list": set(unmatched),
                        "in_list_ratio": ratio,
                        "sentence_obj": sentence,
                    }
        else:
            # Fallback: per-sentence tokenization
            for idx, sentence in enumerate(sentences):
                tokens = LinguisticsUtils.tokenize_and_lemmatize(
                    sentence,
                    fold_diacritics=self.fold_diacritics,
                    handle_elisions=self.handle_elisions,
                )

                token_count = len(tokens)
                # Skip sentences that are outside the desired length window early
                if token_count < self.len_min or token_count > self.len_max:
                    continue

                matched, unmatched = LinguisticsUtils.match_tokens_to_wordlist(
                    tokens, self.wordlist_keys
                )
                ratio = len(matched) / token_count if token_count else 0.0

                index[idx] = {
                    "text": sentence,
                    "tokens": tokens,
                    "token_count": token_count,
                    "words_in_list": set(matched),
                    "words_not_in_list": set(unmatched),
                    "in_list_ratio": ratio,
                    "sentence_obj": sentence,
                }

        return index

    @staticmethod
    def count_content_words_in_matched(
        sentence_text: str,
        matched_words: Set[str],
        fold_diacritics: bool = True,
        handle_elisions: bool = True,
    ) -> int:
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

        content_pos_tags = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}

        # Try to use pre-tokenized form if available (caller may pass sentence_text
        # as a dict with tokens). If it's a raw string, tokenize once.
        tokens = None
        if isinstance(sentence_text, dict) and "tokens" in sentence_text:
            tokens = sentence_text["tokens"]
        else:
            tokens = LinguisticsUtils.tokenize_and_lemmatize(
                sentence_text, fold_diacritics=fold_diacritics, handle_elisions=handle_elisions
            )

        content_count = 0
        for token in tokens:
            pos = token.get("pos") if isinstance(token, dict) else None
            normalized = token.get("normalized") if isinstance(token, dict) else None
            if normalized in matched_words:
                # Treat unknown POS as content in no-spaCy environments
                if pos is None or pos in content_pos_tags:
                    content_count += 1

        return content_count

    @staticmethod
    def filter_content_words_only(
        sentence_text: str,
        wordlist_keys: Set[str],
        fold_diacritics: bool = True,
        handle_elisions: bool = True,
    ) -> Set[str]:
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

        content_pos_tags = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}

        # If caller passed a pre-tokenized sentence dict, use it directly.
        matched_content = set()
        if isinstance(sentence_text, dict) and "tokens" in sentence_text:
            tokens = sentence_text["tokens"]
            for token in tokens:
                pos = token.get("pos")
                # Treat unknown POS as content when spaCy isn't available
                if pos is not None and pos not in content_pos_tags:
                    continue
                normalized = token.get("normalized")
                if normalized in wordlist_keys:
                    matched_content.add(normalized)
            return matched_content

        # Fallback: tokenize once and process tokens
        tokens = LinguisticsUtils.tokenize_and_lemmatize(
            sentence_text, fold_diacritics=fold_diacritics, handle_elisions=handle_elisions
        )

        for token in tokens:
            pos = token.get("pos")
            if pos is not None and pos not in content_pos_tags:
                continue
            normalized = token.get("normalized")
            if normalized in wordlist_keys:
                matched_content.add(normalized)

        return matched_content

    def coverage_mode_greedy(
        self,
        sentences: List[str],
        progress_callback: Optional[Callable[[int, Optional[str]], Any]] = None,
    ) -> Tuple[List[Dict], Dict]:
        """
        Coverage Mode: Enhanced greedy algorithm with adaptive scoring and pre-filtering.

        Features:
        - Word frequency index for performance
        - Adaptive scoring weights based on coverage percentage
        - Rarity bonuses for hard-to-find words
        - Pre-filtered candidate pool with dynamic rebuilding
        - Stagnation detection (stops after 50 iterations without progress)
        - Enhanced logging every 50 sentences

        Args:
            sentences: List of sentence strings
            progress_callback: Optional progress callback (percent, optional_message)

        Returns:
            Tuple of (assignments, stats)
        """
        logger.info("Starting coverage_mode_greedy with enhanced algorithm")

        # Build sentence index (only 4-8 word sentences)
        if progress_callback:
            try:
                progress_callback(5, "Building sentence index...")
            except Exception:
                pass

        sentence_index = self.build_sentence_index(sentences)
        logger.info(f"Built sentence index with {len(sentence_index)} candidates")

        if progress_callback:
            try:
                progress_callback(10, "Building word frequency index...")
            except Exception:
                pass

        # TASK 2: Build word frequency index for performance
        # Maps each word_key -> list of sentence indices containing that word
        word_frequency_index = defaultdict(list)
        for idx, info in sentence_index.items():
            sentence_words = self.filter_content_words_only(
                info,
                self.wordlist_keys,
                fold_diacritics=self.fold_diacritics,
                handle_elisions=self.handle_elisions,
            )
            for word_key in sentence_words:
                word_frequency_index[word_key].append(idx)

        logger.info(f"Built word frequency index for {len(word_frequency_index)} words")

        # Track uncovered words
        uncovered_words = self.wordlist_keys.copy()

        # Track assignments and selections
        assignments = []
        word_to_sentence = {}
        selected_sentence_order = []
        selected_sentence_set = set()
        sentence_contribution = defaultdict(int)
        sentence_selection_score = {}
        sentence_covered_words = {}  # Track which words each sentence covered

        # Determine maximum sentences to select
        if self.target_count in (0, None):
            max_sentences = None
        else:
            try:
                max_sentences = int(self.target_count)
            except Exception:
                max_sentences = None

        # TASK 4: Pre-filter candidate pool (only sentences with uncovered words)
        def build_candidate_pool():
            """Build pool of candidate sentences that contain at least one uncovered word"""
            pool = set()
            for word_key in uncovered_words:
                if word_key in word_frequency_index:
                    for sent_idx in word_frequency_index[word_key]:
                        if sent_idx not in selected_sentence_set:
                            pool.add(sent_idx)
            return pool

        candidate_pool = build_candidate_pool()
        logger.info(f"Initial candidate pool: {len(candidate_pool)} sentences")

        if progress_callback:
            try:
                progress_callback(15, "Standard mode: starting greedy selection...")
            except Exception:
                pass

        # TASK 6: Stagnation detection
        iterations_without_progress = 0
        max_stagnant_iterations = 50
        iteration_count = 0
        last_pool_rebuild = 0

        # Greedy selection loop
        while uncovered_words and (
            max_sentences is None or len(selected_sentence_order) < max_sentences
        ):
            iteration_count += 1
            best_idx = None
            best_score = float("-inf")
            best_new_words = set()

            # Calculate current coverage percentage for adaptive scoring
            total_words = len(self.wordlist_keys) if self.wordlist_keys else 1
            covered_count = len(word_to_sentence)
            coverage_pct = (covered_count / total_words) * 100 if total_words else 0

            # TASK 3: Adaptive scoring weights based on coverage
            if coverage_pct < 50:
                new_word_weight = 10
                mode_label = "Standard"
            elif coverage_pct < 70:
                new_word_weight = 15
                mode_label = "Aggressive"
            else:
                new_word_weight = 25
                mode_label = "Very Aggressive"

            # Find the sentence with the highest score from candidate pool
            for idx in candidate_pool:
                info = sentence_index[idx]

                # Get content words in this sentence
                sentence_words = self.filter_content_words_only(
                    info,
                    self.wordlist_keys,
                    fold_diacritics=self.fold_diacritics,
                    handle_elisions=self.handle_elisions,
                )

                # Find NEW words (not yet covered)
                new_words = sentence_words & uncovered_words

                if not new_words:
                    continue

                # OPTIMIZATION 4: Enhanced scoring with multi-level rarity bonuses
                score = (len(new_words) * new_word_weight) - info["token_count"]

                # Get word-source counts if available (from batch mode)
                word_source_counts = self.config.get("word_source_counts", {})

                # Rarity bonuses at two levels:
                # 1. Within-source rarity (how often word appears in THIS source)
                # 2. Cross-source rarity (how many sources contain this word)
                for word in new_words:
                    # Within-source rarity
                    freq_in_source = len(word_frequency_index.get(word, []))
                    if freq_in_source < 5:
                        score += 20  # Very rare in source
                    elif freq_in_source < 20:
                        score += 5  # Somewhat rare in source

                    # Cross-source rarity (only in batch mode)
                    if word_source_counts and word in word_source_counts:
                        source_count = word_source_counts[word]
                        if source_count == 1:
                            score += 30  # Exclusive to this source!
                        elif source_count == 2:
                            score += 15  # Very rare across sources
                        elif source_count <= 3:
                            score += 5  # Somewhat rare across sources

                # Efficiency bonus: reward sentences covering many rare words (past 60%)
                if coverage_pct > 60 and len(new_words) >= 3:
                    # Check if at least 3 are rare
                    rare_count = sum(
                        1 for w in new_words if len(word_frequency_index.get(w, [])) < 20
                    )
                    if rare_count >= 3:
                        score += 10

                if score > best_score:
                    best_score = score
                    best_idx = idx
                    best_new_words = new_words

            # If no sentence can cover new words, check stagnation
            if best_idx is None:
                iterations_without_progress += 1

                # TASK 4: Rebuild candidate pool every 10 stagnant iterations
                if (iteration_count - last_pool_rebuild) >= 10:
                    logger.info(
                        f"Rebuilding candidate pool after {iterations_without_progress} stagnant iterations"
                    )
                    candidate_pool = build_candidate_pool()
                    last_pool_rebuild = iteration_count

                    # Try again with rebuilt pool
                    if not candidate_pool:
                        logger.info("Candidate pool empty after rebuild - stopping")
                        break
                    continue

                # OPTIMIZATION 5: Adaptive stagnation - don't give up on rare words easily
                # Check if remaining words are rare (appear in few sentences)
                rare_words_remaining = sum(
                    1
                    for word in uncovered_words
                    if word in word_frequency_index and len(word_frequency_index[word]) < 10
                )
                rare_word_ratio = rare_words_remaining / max(1, len(uncovered_words))

                # Increase stagnation tolerance if many rare words remain
                if rare_word_ratio > 0.5:  # More than 50% are rare
                    effective_stagnation_limit = max_stagnant_iterations * 3  # 150 iterations
                elif rare_word_ratio > 0.3:  # 30-50% are rare
                    effective_stagnation_limit = max_stagnant_iterations * 2  # 100 iterations
                else:
                    effective_stagnation_limit = max_stagnant_iterations  # 50 iterations

                if iterations_without_progress >= effective_stagnation_limit:
                    logger.info(
                        f"Stopping: {iterations_without_progress} iterations without progress "
                        f"(rare_words={rare_words_remaining}/{len(uncovered_words)}, "
                        f"limit={effective_stagnation_limit})"
                    )
                    if progress_callback:
                        try:
                            progress_callback(
                                int(10 + coverage_pct * 0.85),
                                f"Stopped: no progress after {iterations_without_progress} iterations",
                            )
                        except Exception:
                            pass
                    break
                continue

            # Reset stagnation counter (we found a sentence)
            iterations_without_progress = 0

            # Select this sentence
            selected_sentence_set.add(best_idx)
            selected_sentence_order.append(best_idx)
            sentence_contribution[best_idx] = len(best_new_words)
            sentence_selection_score[best_idx] = best_score
            sentence_covered_words[best_idx] = list(best_new_words)

            # Remove from candidate pool
            candidate_pool.discard(best_idx)

            # Mark words as covered
            for word_key in best_new_words:
                word_to_sentence[word_key] = best_idx
                uncovered_words.discard(word_key)

            # TASK 5: Enhanced logging every 50 sentences
            if len(selected_sentence_order) % 50 == 0:
                logger.info(
                    f"[Iteration {iteration_count}] {mode_label} mode: "
                    f"Coverage {coverage_pct:.1f}% ({covered_count + len(best_new_words)}/{total_words} words), "
                    f"Selected {len(selected_sentence_order)} sentences, "
                    f"Candidate pool size: {len(candidate_pool)}"
                )

            # Progress callback with context
            if progress_callback:
                try:
                    new_coverage_pct = ((covered_count + len(best_new_words)) / total_words) * 100
                    pct = 15 + int(75 * (new_coverage_pct / 100))
                    pct = min(max(pct, 15), 90)
                    msg = f"{mode_label} mode: {new_coverage_pct:.1f}% coverage..."
                    progress_callback(pct, msg)
                except Exception:
                    pass

        # Final statistics
        covered_words = set(word_to_sentence.keys())
        final_coverage_pct = (
            (len(covered_words) / len(self.wordlist_keys) * 100) if self.wordlist_keys else 0
        )

        logger.info(
            f"Coverage complete: {len(covered_words)}/{len(self.wordlist_keys)} words ({final_coverage_pct:.1f}%), "
            f"{len(selected_sentence_order)} sentences selected, "
            f"{iteration_count} total iterations"
        )

        if progress_callback:
            try:
                progress_callback(95, "Finalizing results...")
            except Exception:
                pass

        # Build assignments list with covered words metadata
        for word_key, sentence_idx in word_to_sentence.items():
            sentence_info = sentence_index[sentence_idx]
            matched_surface = LinguisticsUtils.find_word_in_sentence(
                word_key,
                sentence_info["text"],
                fold_diacritics=self.fold_diacritics,
                handle_elisions=self.handle_elisions,
            )

            assignments.append(
                {
                    "word_key": word_key,
                    "word_original": word_key,
                    "lemma": word_key,
                    "matched_surface": matched_surface,
                    "sentence_index": sentence_idx,
                    "sentence_text": sentence_info["text"],
                    "sentence_score": sentence_info["in_list_ratio"],
                    "covered_words": sentence_covered_words.get(
                        sentence_idx, []
                    ),  # For "Why this sentence?" tooltip
                }
            )

        # Calculate statistics
        stats = {
            "words_total": len(self.wordlist_keys),
            "words_covered": len(covered_words),
            "uncovered_words": len(uncovered_words),
            # Backward-compatible synonyms expected by some tests/clients
            "words_uncovered": len(uncovered_words),
            "coverage_percentage": final_coverage_pct,
            "selected_sentence_count": len(selected_sentence_set),
            "learning_set_count": len(selected_sentence_order),
            "total_iterations": iteration_count,
            "stopped_reason": "stagnation"
            if iterations_without_progress >= max_stagnant_iterations
            else "complete",
            "learning_set": [
                {
                    "rank": rank,
                    "sentence_index": idx,
                    "sentence_text": sentence_index[idx]["text"],
                    "token_count": sentence_index[idx]["token_count"],
                    "new_word_count": sentence_contribution.get(idx, 0),
                    "score": sentence_selection_score.get(idx),
                    "covered_words": sentence_covered_words.get(idx, []),
                }
                for rank, idx in enumerate(selected_sentence_order, start=1)
            ],
        }

        # Log covered and uncovered words to files
        self._log_word_sets(covered_words, uncovered_words)

        if progress_callback:
            try:
                progress_callback(100, "Complete")
            except Exception:
                pass

        logger.info(
            f"Coverage mode: {stats['words_covered']}/{stats['words_total']} words covered "
            f"({final_coverage_pct:.1f}%) with {stats['selected_sentence_count']} sentences"
        )

        return assignments, stats

    def _analyze_sources_for_batch(
        self,
        sources: List[Tuple[int, List[str]]],
        target_words: Set[str],
        progress_callback: Optional[Callable[[int, str], Any]] = None,
    ) -> List[Dict]:
        """
        Pre-analyze sources to determine word coverage and rarity for smart ordering.

        Returns list of analysis dicts with:
        - source_id: ID of the source
        - unique_words: Count of unique target words in this source
        - rare_words: Count of words appearing in ≤2 sources
        - value_score: rare_words / total_sentences (higher = process first)
        - word_source_counts: Shared dict mapping word -> count of sources containing it
        """
        from collections import defaultdict

        # Build word-to-source-count mapping
        word_source_counts = defaultdict(int)
        source_word_sets = []

        # First pass: count which sources contain which words
        for source_id, sentences in sources:
            # Quick tokenization to find words (no need for full indexing)
            from app.utils.linguistics import LinguisticsUtils

            words_in_source = set()
            for sentence in sentences[:1000]:  # Sample first 1000 sentences for speed
                tokens = LinguisticsUtils.tokenize_and_lemmatize(
                    sentence,
                    fold_diacritics=self.fold_diacritics,
                    handle_elisions=self.handle_elisions,
                )
                for token in tokens:
                    normalized = token.get("normalized") if isinstance(token, dict) else None
                    if normalized and normalized in target_words:
                        words_in_source.add(normalized)

            source_word_sets.append(words_in_source)

            # Update word-to-source counts
            for word in words_in_source:
                word_source_counts[word] += 1

        # Second pass: analyze each source
        analyses = []
        for idx, (source_info, word_set) in enumerate(zip(sources, source_word_sets)):
            source_id, sentences = source_info

            # Count rare words (appear in ≤2 sources)
            rare_words = sum(1 for word in word_set if word_source_counts[word] <= 2)

            # Value score: prioritize sources with high rare-word density
            value_score = rare_words / max(1, len(sentences)) if sentences else 0

            analyses.append(
                {
                    "source_id": source_id,
                    "unique_words": len(word_set),
                    "rare_words": rare_words,
                    "value_score": value_score,
                    "word_source_counts": word_source_counts,  # Shared reference
                }
            )

        return analyses

    def batch_coverage_mode(
        self,
        sources: List[Tuple[int, List[str]]],
        progress_callback: Optional[Callable[[int, str], Any]] = None,
    ) -> Tuple[List[Dict], Dict, List[Dict]]:
        """
        Batch Coverage Mode: Process multiple sources sequentially with dynamic budget allocation.

        This implements the "smart assembly line" approach with fair budget distribution:
        - Process sources sequentially, searching only for uncovered words
        - Dynamically allocate budget based on remaining words, not remaining total budget
        - Later sources get fair share to cover rare words not found in earlier sources
        - Last source receives any remaining budget to maximize coverage

        Dynamic Budget Allocation Algorithm:
        1. Calculate words_remaining = uncovered_words.count()
        2. Estimate sentences_needed = words_remaining / expected_words_per_sentence (2.0)
        3. Allocate source_budget = min(sentences_needed, remaining_global_budget)
        4. If last source: source_budget = remaining_global_budget (avoid waste)
        5. Ensure minimum budget of 10 sentences (unless global budget exhausted)

        Benefits:
        - Prevents first source from consuming entire budget
        - Later sources can find rare words missed by earlier sources
        - Expected coverage: 70-75% with 500 sentence budget across multiple novels

        Args:
            sources: List of tuples (source_id, sentences_list)
            progress_callback: Optional progress callback (percent, step_description)

        Returns:
            Tuple of (combined_assignments, combined_stats, combined_learning_set)
        """
        logger.info(f"Starting batch coverage mode with {len(sources)} sources")

        # Track global state across all sources
        all_assignments = []
        all_selected_sentences = []
        uncovered_words = self.wordlist_keys.copy()
        total_words_initial = len(self.wordlist_keys)

        # Global sentence limit from config (0 = unlimited)
        target_count_config = self.config.get("target_count", 500)
        unlimited_mode = target_count_config == 0
        global_sentence_limit = None if unlimited_mode else target_count_config
        total_sentences_selected = 0

        # Statistics per source
        source_stats = []

        if unlimited_mode:
            logger.info(
                f"Unlimited mode enabled - no sentence cap, Target words: {total_words_initial}"
            )
        else:
            logger.info(
                f"Global sentence limit: {global_sentence_limit}, Target words: {total_words_initial}"
            )

        # OPTIMIZATION 1: Pre-analyze sources for word coverage and rarity
        logger.info("Pre-analyzing sources for smart ordering...")
        source_analysis = self._analyze_sources_for_batch(
            sources, uncovered_words, progress_callback
        )

        # OPTIMIZATION 2: Sort sources by value score (rare words / total sentences)
        # This ensures rare-word-rich sources get processed first with larger budgets
        sorted_source_indices = sorted(
            range(len(source_analysis)),
            key=lambda i: source_analysis[i]["value_score"],
            reverse=True,
        )

        logger.info("Source processing order (by rare-word density):")
        for rank, idx in enumerate(sorted_source_indices, 1):
            analysis = source_analysis[idx]
            logger.info(
                f"  Rank {rank}: Source {analysis['source_id']} - "
                f"{analysis['unique_words']} unique words, "
                f"{analysis['rare_words']} rare words, "
                f"value_score={analysis['value_score']:.4f}"
            )

        # Build word-to-source-count mapping for rarity weighting
        word_source_counts = source_analysis[0]["word_source_counts"]  # Shared across all analyses

        # Process each source sequentially in optimized order
        for process_rank, source_list_idx in enumerate(sorted_source_indices):
            source_id, sentences = sources[source_list_idx]
            analysis = source_analysis[source_list_idx]

            # Check stopping conditions
            if not uncovered_words:
                logger.info(f"All words covered after processing {process_rank} sources")
                break

            if not unlimited_mode and total_sentences_selected >= global_sentence_limit:
                logger.info(
                    f"Global sentence limit ({global_sentence_limit}) reached after {process_rank} sources"
                )
                break

            # Calculate remaining sentence budget for this source
            if unlimited_mode:
                remaining_global_budget = None  # No limit
            else:
                remaining_global_budget = global_sentence_limit - total_sentences_selected

            # OPTIMIZATION 3: DYNAMIC BUDGET ALLOCATION
            # Allocate budget intelligently based on remaining words and source value
            words_remaining = len(uncovered_words)
            sources_remaining = len(sources) - process_rank
            is_last_source = process_rank == len(sources) - 1

            if unlimited_mode:
                # No budget limit - let algorithm run until stagnation or completion
                source_budget = None
                logger.info(
                    f"Processing source {process_rank + 1}/{len(sources)} (ID: {source_id}) - "
                    f"UNLIMITED MODE, {words_remaining} words remaining"
                )
            else:
                # SMART BUDGET CALCULATION using pre-analysis
                unique_words_in_source = analysis["unique_words"]
                rare_words_in_source = analysis["rare_words"]

                # Expected coverage rate from this source (words / sentence)
                # Higher for sources with more unique target words
                if unique_words_in_source > 0 and len(sentences) > 0:
                    expected_rate = max(
                        1.5, min(3.5, unique_words_in_source / (len(sentences) * 0.1))
                    )
                else:
                    expected_rate = 2.0

                # Estimate sentences needed to cover remaining words
                sentences_needed = int(words_remaining / expected_rate)

                # Fair share: divide remaining budget by remaining sources
                fair_share = remaining_global_budget // max(1, sources_remaining)

                # Allocate based on need, but allow high-value sources to take more
                # Rare-word-rich sources get up to 2.5x fair share
                rarity_bonus_multiplier = 1.0 + (
                    rare_words_in_source / max(1, unique_words_in_source)
                )
                source_budget = min(sentences_needed, int(fair_share * rarity_bonus_multiplier))

                # Cap at remaining budget
                source_budget = min(source_budget, remaining_global_budget)

                # Last source gets all remaining budget (avoid waste)
                if is_last_source:
                    source_budget = remaining_global_budget

                # Ensure minimum viable budget (unless exhausted)
                if source_budget < 20 and remaining_global_budget >= 20:
                    source_budget = 20

                logger.info(
                    f"Processing source {process_rank + 1}/{len(sources)} (ID: {source_id}), "
                    f"{words_remaining} words remaining, "
                    f"budget={source_budget}/{remaining_global_budget}, "
                    f"unique_words={unique_words_in_source}, rare_words={rare_words_in_source}"
                )

            # Update progress
            if progress_callback:
                try:
                    base_progress = int(10 + (process_rank / len(sources)) * 80)
                    step_desc = f"Processing source {process_rank + 1}/{len(sources)}"
                    progress_callback(base_progress, step_desc)
                except Exception:
                    pass

            # Create a temporary CoverageService with current uncovered words,
            # allocated budget, and word rarity information for weighting
            temp_config = self.config.copy()
            temp_config["target_count"] = source_budget if not unlimited_mode else 0
            temp_config["word_source_counts"] = word_source_counts  # For rarity weighting
            temp_service = CoverageService(wordlist_keys=uncovered_words, config=temp_config)

            # Run coverage mode on this source
            source_assignments, source_stats_dict = temp_service.coverage_mode_greedy(
                sentences, progress_callback=None  # We handle progress at batch level
            )

            # Track which words were covered by this source
            words_covered_by_source = set()
            for assignment in source_assignments:
                word_key = assignment["word_key"]
                words_covered_by_source.add(word_key)

                # Add source_id and rank to assignment for tracking
                assignment["source_id"] = source_id
                assignment["source_rank"] = process_rank  # Rank in processing order
                assignment["source_list_index"] = source_list_idx  # Original position
                all_assignments.append(assignment)

            # Update uncovered words
            newly_covered = len(words_covered_by_source)
            uncovered_words -= words_covered_by_source

            # Track total sentences selected
            source_sentence_count = source_stats_dict["selected_sentence_count"]
            total_sentences_selected += source_sentence_count

            # Record stats for this source
            source_stats.append(
                {
                    "source_id": source_id,
                    "source_rank": process_rank,
                    "source_list_index": source_list_idx,
                    "sentences_count": len(sentences),
                    "selected_sentence_count": source_sentence_count,
                    "words_covered": newly_covered,
                    "words_remaining": len(uncovered_words),
                    "unique_words_available": analysis["unique_words"],
                    "rare_words_available": analysis["rare_words"],
                }
            )

            # Append learning set from this source run
            for item in source_stats_dict.get("learning_set", []):
                all_selected_sentences.append(
                    {"source_id": source_id, "source_rank": process_rank, **item}
                )

            if unlimited_mode:
                logger.info(
                    f"Source {process_rank + 1} (ID: {source_id}) covered {newly_covered} new words, "
                    f"{len(uncovered_words)} words remaining, "
                    f"{source_sentence_count} sentences selected, "
                    f"{total_sentences_selected} total (unlimited)"
                )
            else:
                logger.info(
                    f"Source {process_rank + 1} (ID: {source_id}) covered {newly_covered} new words, "
                    f"{len(uncovered_words)} words remaining, "
                    f"{source_sentence_count} sentences selected, "
                    f"{total_sentences_selected}/{global_sentence_limit} total"
                )

        # Build combined learning set and stats
        all_assignments.sort(key=lambda a: (a.get("source_rank", 0), a.get("sentence_index", 0)))

        # Re-rank the combined learning set
        # If we still have remaining budget and uncovered words, attempt a consolidation
        # pass: run a final greedy selection across all selected sentences to try and
        # cover any remaining words using available sentence slots.
        combined_learning_set = []
        for rank, sentence_data in enumerate(all_selected_sentences, start=1):
            combined_learning_set.append({"rank": rank, **sentence_data})

        total_words_covered = total_words_initial - len(uncovered_words)
        coverage_percentage = (
            (total_words_covered / total_words_initial * 100) if total_words_initial > 0 else 0
        )

        combined_stats = {
            "words_total": total_words_initial,
            "words_covered": total_words_covered,
            "uncovered_words": len(uncovered_words),
            "coverage_percentage": coverage_percentage,
            "selected_sentence_count": total_sentences_selected,
            "learning_set_count": len(combined_learning_set),
            "source_stats": source_stats,
            "batch_summary": {
                "source_count": len(sources),
                "sources_processed": len(source_stats),
                "total_sentences_selected": total_sentences_selected,
                "sentence_limit": global_sentence_limit if not unlimited_mode else None,
                "unlimited_mode": unlimited_mode,
                "limit_reached": not unlimited_mode
                and total_sentences_selected >= global_sentence_limit,
                "optimization_features": [
                    "pre_analysis",
                    "smart_ordering",
                    "dynamic_budget_allocation",
                    "word_rarity_weighting",
                    "adaptive_stagnation",
                ],
            },
            # Store learning set in stats for API compatibility
            "learning_set": combined_learning_set,
        }

        # If coverage seems low and we have budget left, attempt a consolidation pass
        try:
            if (
                (not unlimited_mode)
                and total_sentences_selected < global_sentence_limit
                and uncovered_words
            ):
                remaining_slots = global_sentence_limit - total_sentences_selected
                if remaining_slots > 0 and all_selected_sentences:
                    # Prepare a unified sentence pool from all sources and run a light-weight
                    # coverage greedy to pick sentences that cover remaining uncovered words.
                    # Build a pool of all sentences from all sources (not just previously selected)
                    pool_sentences = []
                    for _src_id, src_sentences in sources:
                        pool_sentences.extend(src_sentences)

                    temp_service = CoverageService(
                        wordlist_keys=uncovered_words,
                        config={
                            "len_min": self.len_min,
                            "len_max": self.len_max,
                            "target_count": remaining_slots,
                        },
                    )

                    # Run greedy on the pool to try to pick extra sentences
                    extra_assignments, extra_stats = temp_service.coverage_mode_greedy(
                        pool_sentences
                    )

                    # Append any new assignments we found and compute newly covered words
                    if extra_assignments:
                        existing_words = {a.get("word_key") for a in all_assignments}
                        added = 0
                        newly_covered_words = set()
                        for a in extra_assignments:
                            wk = a.get("word_key")
                            if not wk:
                                continue
                            if wk in existing_words or wk in newly_covered_words:
                                continue
                            newly_covered_words.add(wk)
                            a["source_id"] = None
                            a["source_rank"] = None
                            a["source_list_index"] = None
                            all_assignments.append(a)
                            combined_learning_set.append(
                                {
                                    "rank": len(combined_learning_set) + 1,
                                    "source_id": None,
                                    "sentence_index": None,
                                    "sentence_text": a.get("sentence_text"),
                                    "token_count": None,
                                    "new_word_count": 1,
                                    "score": None,
                                }
                            )
                            added += 1

                        if added:
                            # Update covered counts and coverage percentage
                            total_words_covered += len(newly_covered_words)
                            coverage_percentage = (
                                (total_words_covered / total_words_initial * 100)
                                if total_words_initial > 0
                                else 0
                            )
                            combined_stats["words_covered"] = total_words_covered
                            combined_stats["coverage_percentage"] = coverage_percentage
                            combined_stats["selected_sentence_count"] = (
                                total_sentences_selected + added
                            )
                            combined_stats["learning_set"] = combined_learning_set
        except Exception:
            # Non-fatal: consolidation is an optimization. If it fails, continue.
            logger.exception("Consolidation pass failed - continuing without it")

        if unlimited_mode:
            logger.info(
                f"Batch coverage complete (UNLIMITED). Words covered: {total_words_covered}/{total_words_initial} "
                f"({coverage_percentage:.1f}%). Sentences selected: {total_sentences_selected} from {len(source_stats)} sources."
            )
        else:
            logger.info(
                f"Batch coverage complete. Words covered: {total_words_covered}/{total_words_initial} "
                f"({coverage_percentage:.1f}%). Sentences: {total_sentences_selected}/{global_sentence_limit} from {len(source_stats)} sources."
            )

        # Log final combined word sets
        final_covered_words = self.wordlist_keys - uncovered_words
        self._log_word_sets(final_covered_words, uncovered_words)

        if progress_callback:
            progress_callback(100, "Batch processing complete")

        return all_assignments, combined_stats, combined_learning_set

    def _log_word_sets(self, covered_words: Set[str], uncovered_words: Set[str]):
        """Log covered and uncovered words to files for debugging."""
        log_dir = "logs"
        try:
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            # Write covered words
            covered_filename = os.path.join(log_dir, f"coverage_covered_{timestamp}.txt")
            with open(covered_filename, "w", encoding="utf-8") as f:
                for word in sorted(list(covered_words)):
                    f.write(f"{word}\n")

            # Write uncovered words
            uncovered_filename = os.path.join(log_dir, f"coverage_uncovered_{timestamp}.txt")
            with open(uncovered_filename, "w", encoding="utf-8") as f:
                for word in sorted(list(uncovered_words)):
                    f.write(f"{word}\n")

        except IOError as e:
            logger.error(f"Error writing coverage word lists to file: {e}")

    def filter_mode(
        self, sentences: List[str], progress_callback: Optional[Callable[[int], Any]] = None
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
        # Thresholds (min_content_words is configurable via service config)
        min_content_words = int(self.config.get("min_content_words", 3))
        max_tokens = int(self.config.get("max_tokens", 8))
        # Back-compat ratio criteria used by older tests/clients
        min_ratio = float(self.config.get("min_in_list_ratio", self.default_min_ratio))

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
            token_count = info["token_count"]

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
                info["words_in_list"],
                fold_diacritics=self.fold_diacritics,
                handle_elisions=self.handle_elisions,
            )

            content_word_count = len(matched_content_words)

            ratio = info["in_list_ratio"] if token_count > 0 else 0.0
            # Select if meets either criterion: content-word threshold OR ratio threshold
            if content_word_count >= min_content_words or ratio >= min_ratio:
                selected.append(
                    {
                        "sentence_index": idx,
                        "sentence_text": info["text"],
                        "in_list_ratio": round(ratio, 3),
                        # Backwards-compatible score field expected by frontend components
                        "sentence_score": round(ratio, 3),
                        "token_count": token_count,
                        "words_in_list": list(matched_content_words) if matched_content_words else list(info["words_in_list"]),
                        "content_word_count": content_word_count,
                    }
                )

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
            "total_sentences": len(sentences),
            "selected_count": selected_count,
            "filter_acceptance_ratio": (selected_count / len(sentences)) if sentences else 0.0,
            # Backwards-compatible key expected by some front-end tests/components
            "candidates_passed_filter": selected_count,
            # Provide more granular breakdown for multi-pass filtering
            "min_content_words": min_content_words,
            "max_tokens": max_tokens,
            # Compatibility fields retained (not used by this simplified filter):
            "scaled_min_ratios": self.scaled_min_ratios,
            "default_min_ratio": self.default_min_ratio,
            "len_min": self.len_min,
            "len_max": self.len_max,
            "target_count": self.target_count,
            "candidates_by_pass": {
                # Keep an informative pass key for legacy UI that looks for 4-8 word pass
                f"content_words_>={min_content_words}_len_<={max_tokens}": selected_count
            },
        }

        logger.info(
            "Filter mode (>= %s content words): %s/%s sentences selected",
            min_content_words,
            selected_count,
            len(sentences),
        )

        if progress_callback:
            try:
                progress_callback(95)
            except Exception:
                pass

        return selected, stats

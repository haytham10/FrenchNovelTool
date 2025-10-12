import json
import pathlib
import re
from typing import List, Optional, Dict, Any

from flask import current_app
from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Import new modular prompt system
from app.services.prompts import build_sentence_normalizer_prompt
from app.services.prompts.sentence_normalizer_prompt import (
    build_minimal_prompt as build_minimal_prompt_v2,
)


class GeminiAPIError(Exception):
    """Raised when Gemini returns an empty, malformed or unparseable response.

    Attributes:
        message: human readable message
        raw_response: the original raw text returned by Gemini (may be None)
    """

    def __init__(self, message: str, raw_response: str | None = None):
        super().__init__(message)
        self.raw_response = raw_response


class GeminiService:
    """Service wrapper around Gemini PDF processing with advanced post-processing."""

    MODEL_PREFERENCE_MAP = {
        "balanced": "gemini-2.5-flash",
        "quality": "gemini-2.5-pro",
        "speed": "gemini-2.5-flash-lite",
    }

    # Model fallback cascade: if current model fails, try these in order
    MODEL_FALLBACK_CASCADE = {
        "speed": ["balanced", "quality"],
        "balanced": ["quality"],
        "quality": [],  # No fallback for quality (already best model)
    }

    DIALOGUE_BOUNDARIES = ('"', "'", "«", "»", "“", "”")

    def __init__(
        self,
        sentence_length_limit: int = 8,
        *,
        model_preference: str = "speed",
        ignore_dialogue: bool = False,
        preserve_formatting: bool = True,
        fix_hyphenation: bool = True,
        min_sentence_length: int = 2,
    ) -> None:
        self.client = genai.Client(api_key=current_app.config["GEMINI_API_KEY"])
        self.model_preference = model_preference
        self.model_name = self.MODEL_PREFERENCE_MAP.get(
            model_preference, current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
        )
        self.sentence_length_limit = sentence_length_limit
        self.ignore_dialogue = ignore_dialogue
        self.preserve_formatting = preserve_formatting
        self.fix_hyphenation = fix_hyphenation
        self.min_sentence_length = min_sentence_length
        self.max_retries = current_app.config["GEMINI_MAX_RETRIES"]
        self.retry_delay = current_app.config["GEMINI_RETRY_DELAY"]
        # Allow operator to disable local segmentation fallback via config.
        # Default: True to preserve existing behaviour unless explicitly changed.
        self.allow_local_fallback = current_app.config.get("GEMINI_ALLOW_LOCAL_FALLBACK", False)
        # Repair controls (to limit additional Gemini API calls which can be slow)
        # Enable / disable the targeted long-sentence repair step
        self.enable_repair = bool(current_app.config.get("GEMINI_ENABLE_REPAIR", True))
        # Only attempt repair if sentence length > sentence_length_limit * repair_multiplier
        self.repair_multiplier = float(current_app.config.get("GEMINI_REPAIR_MULTIPLIER", 1.5))
        # Maximum repair attempts per unique chunk within a single request
        self.max_repair_attempts = int(current_app.config.get("GEMINI_MAX_REPAIR_ATTEMPTS", 1))
        # Simple in-request cache to avoid repeating repairs for identical chunks
        self._repair_cache = {}

        # Runtime stats from last post-processing step
        self.last_fragment_rate = 0.0
        self.last_fragment_count = 0
        self.last_fragment_details = []
        self.last_processed_sentences = []

        # Retry / QC configuration
        self.fragment_rate_retry_threshold = float(
            current_app.config.get("GEMINI_FRAGMENT_RATE_RETRY_THRESHOLD", 3.0)
        )
        self.reject_on_high_fragment_rate = bool(
            current_app.config.get("GEMINI_REJECT_ON_HIGH_FRAGMENT_RATE", False)
        )

        # Use new prompt framework exclusively
        current_app.logger.info(
            "GeminiService initialized with new prompt framework (v2)"
        )

        # Quality Gate: spaCy-based fragment rejection
        self.quality_gate_enabled = bool(current_app.config.get("QUALITY_GATE_ENABLED", True))
        self.quality_gate = None
        self.rejected_sentences = []  # Track rejected sentences
        self.quality_gate_rejections = 0  # Track rejection count

        if self.quality_gate_enabled:
            try:
                from app.services.quality_gate_service import QualityGateService

                self.quality_gate = QualityGateService(
                    config={
                        "min_length": self.min_sentence_length,
                        "max_length": self.sentence_length_limit,
                        "require_verb": True,
                    }
                )
                current_app.logger.info("Quality Gate enabled with spaCy verb detection")
            except Exception as e:
                current_app.logger.warning(
                    "Failed to initialize Quality Gate (will continue without it): %s", str(e)
                )
                self.quality_gate_enabled = False

    def build_prompt(self, base_prompt: Optional[str] = None) -> str:
        """Build the Gemini prompt using the new prompt framework.

        Args:
            base_prompt: If provided, use this exact prompt (overrides default)

        Returns:
            Prompt string for Gemini API
        """
        if base_prompt:
            return base_prompt

        return self.build_prompt_v2()

    def build_prompt_v2(self) -> str:
        """Build the new few-shot prompt (v2) designed to eliminate fragments.

        This is a concise ~40-line prompt using few-shot examples instead of
        lengthy rule explanations. Target fragment rate: <0.5%
        """
        return build_sentence_normalizer_prompt(
            sentence_length_limit=self.sentence_length_limit,
            min_sentence_length=self.min_sentence_length,
            ignore_dialogue=self.ignore_dialogue,
            preserve_formatting=self.preserve_formatting,
            fix_hyphenation=self.fix_hyphenation,
        )

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Ask the model to rewrite a single long sentence into multiple sentences
        each within the configured word limit. Returns normalized sentences.
        This is a targeted repair for sentences that exceed sentence_length_limit.
        """
        if not sentence or not str(sentence).strip():
            return []

        max_words = self.sentence_length_limit
        repair_prompt = (
            f"Rewrite the following French sentence into one or more short, independent, "
            f"grammatically complete sentences. Each output sentence must contain at most {max_words} words. "
            'Return ONLY a JSON object: {"sentences": ["Sentence 1.", "Sentence 2."]}.'
        )

        try:
            resp = self._call_gemini_api(
                sentence,
                repair_prompt,
                self.MODEL_PREFERENCE_MAP.get("balanced") or self.model_name,
            )
            # resp['sentences'] is a list of {"normalized": s, "original": s}
            sentences = [
                item.get("normalized") if isinstance(item, dict) else str(item)
                for item in resp.get("sentences", [])
            ]
            # Ensure returned strings are stripped and non-empty
            return [s.strip() for s in sentences if s and str(s).strip()]
        except Exception as e:
            current_app.logger.warning(
                "Long-sentence repair failed: %s; sentence=%r", e, sentence[:200]
            )
            return []

    def build_minimal_prompt(self) -> str:
        """Build a minimal prompt using the new prompt framework.

        Used as a fallback when the full prompt fails due to hallucination or format issues.
        """
        return build_minimal_prompt_v2(
            sentence_length_limit=self.sentence_length_limit,
            min_sentence_length=self.min_sentence_length,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def generate_content_from_pdf(self, prompt: str, pdf_path: str) -> List[str]:
        """Generate content from a PDF using inline data and post-process sentences."""
        filepath = pathlib.Path(pdf_path)
        pdf_bytes = filepath.read_bytes()

        pdf_size_kb = len(pdf_bytes) / 1024
        current_app.logger.info("Processing PDF: %s, Size: %.2fKB", filepath.name, pdf_size_kb)
        try:
            from app.pdf_compat import PdfReader

            with open(pdf_path, "rb") as file_handle:
                try:
                    reader = PdfReader(file_handle)
                    current_app.logger.info(
                        "PDF info: %s, Pages: %d", filepath.name, len(reader.pages)
                    )
                except Exception as exc:  # pragma: no cover - diagnostic logging
                    current_app.logger.warning("Couldn't extract PDF metadata: %s", exc)
        except ImportError:  # pragma: no cover - optional dependency
            current_app.logger.info("PDF backend not available for metadata extraction")
            current_app.logger.info("PyPDF2 not available for metadata extraction")

        pdf_part = types.Part.from_bytes(
            data=pdf_bytes,
            mime_type="application/pdf",
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[pdf_part, prompt],
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"
                    ),
                ]
            ),
        )

        # Some SDKs may set response.text to None; coerce to empty string to
        # avoid failing calls to .strip() or slicing when logging.
        response_text = getattr(response, "text", "") or ""
        current_app.logger.debug(
            "Raw Gemini response: %s",
            (response_text[:1000] if isinstance(response_text, str) else ""),
        )

        cleaned_response = response_text.strip().replace("```json", "").replace("```", "")

        if not cleaned_response:
            current_app.logger.error("Received empty response from Gemini API.")
            raise GeminiAPIError("Gemini returned an empty response.", response_text)

        try:
            data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            current_app.logger.warning("Initial JSON parsing failed, attempting recovery...")
            try:
                data = self._recover_json(cleaned_response)
            except Exception:
                # _recover_json will log details; raise a GeminiAPIError attaching raw response
                raise GeminiAPIError("Failed to parse Gemini JSON response.", response_text)

        sentences = self._extract_sentence_list(data)
        processed_sentences = self._post_process_sentences(sentences)

        if not processed_sentences:
            current_app.logger.error(
                "Gemini response contained no valid sentences after post-processing."
            )
            raise ValueError("Gemini response did not contain any valid sentences.")

        return processed_sentences

    def _recover_json(self, response: str) -> dict:
        """Attempt to recover a JSON document from a loosely formatted response."""
        json_start = response.find("{")
        if json_start >= 0:
            open_braces = 0
            json_end = -1
            for idx, char in enumerate(response[json_start:], start=json_start):
                if char == "{":
                    open_braces += 1
                elif char == "}":
                    open_braces -= 1
                    if open_braces == 0:
                        json_end = idx + 1
                        break
            if json_end > 0:
                try:
                    return json.loads(response[json_start:json_end])
                except json.JSONDecodeError:
                    pass

        list_match = re.search(r'\[(?:\s*"[^"]+"\s*,?\s*)+\]', response)
        if list_match:
            sentences = re.findall(r'"([^"]+)"', list_match.group(0))
            return {"sentences": sentences}

        current_app.logger.error("Failed to decode Gemini response: %s", response[:1000])
        raise ValueError("Failed to parse response from Gemini API.")

    def _extract_sentence_list(self, data) -> List[str]:
        """Normalise the sentences payload from a Gemini response."""
        sentences = None
        if isinstance(data, dict):
            sentences = data.get("sentences")
            if not sentences:
                if "results" in data and isinstance(data["results"], list):
                    sentences = data["results"]
                else:
                    for key, value in data.items():
                        if isinstance(value, list) and (
                            "sentence" in key.lower() or "text" in key.lower()
                        ):
                            sentences = value
                            break
        elif isinstance(data, list) and all(isinstance(item, str) for item in data):
            sentences = data

        if (
            isinstance(sentences, str)
            and sentences.strip().startswith("[")
            and sentences.strip().endswith("]")
        ):
            try:
                sentences = json.loads(sentences)
                current_app.logger.info("Converted string representation of list to actual list.")
            except json.JSONDecodeError:
                sentences = None

        if not isinstance(sentences, list):
            current_app.logger.error(
                "Gemini response 'sentences' is not in list format: %s", sentences
            )
            raise ValueError("Gemini response 'sentences' is not in list format.")

        normalised = [
            str(sentence).strip() for sentence in sentences if sentence and str(sentence).strip()
        ]
        if not normalised:
            current_app.logger.error("Gemini response contained no valid sentences: %s", sentences)
            raise GeminiAPIError(
                "Gemini response did not contain any valid sentences.", str(sentences)
            )

        return normalised

    def _post_process_sentences(self, sentences: List[str]) -> List[str]:
        """Apply manual splitting, merging, and normalisation rules to sentences.

        This method validates the quality of the AI's output and enforces the
        linguistic rewriting requirement by detecting and logging fragments.
        """
        processed: List[str] = []
        fragment_count = 0
        fragment_details = []

        for idx, raw_sentence in enumerate(sentences):
            # Defensive: skip None inputs and log for diagnostics
            if raw_sentence is None:
                current_app.logger.warning(
                    "Skipping None sentence at index %s during post-processing", idx
                )
                continue

            # Normalize with guard
            try:
                text = self._normalise_sentence(raw_sentence)
            except Exception as e:
                current_app.logger.exception(
                    "Error normalising sentence at index %s: %s; raw=%r", idx, e, raw_sentence
                )
                continue

            if not text:
                continue

            if self.ignore_dialogue and self._looks_like_dialogue(text):
                processed.append(text)
                continue

            try:
                chunks = self._split_sentence(text)
            except Exception as e:
                current_app.logger.exception(
                    "Error splitting sentence at index %s: %s; text=%r", idx, e, text
                )
                chunks = [text]

            original_unsplit = len(chunks) == 1 and chunks[0] == text

            for chunk in chunks:
                try:
                    chunk = (chunk or "").strip()
                except Exception:
                    # If chunk is unexpectedly non-string, coerce and continue
                    chunk = str(chunk).strip() if chunk is not None else ""

                if not chunk:
                    continue

                # If this chunk exceeds configured length, attempt targeted repair
                try:
                    word_count = len(chunk.split())
                except Exception:
                    word_count = len(str(chunk).split())

                if word_count > self.sentence_length_limit:
                    # Decide whether to attempt a repair. Repairing every slightly-overlong
                    # chunk causes many extra API calls and high latency. Use configuration
                    # to limit attempts.
                    repaired = []
                    if not self.enable_repair:
                        current_app.logger.debug(
                            "Repair disabled for chunk (len=%d): %s", word_count, chunk[:80]
                        )
                    else:
                        # Only attempt repair if chunk is significantly over the limit
                        if word_count < int(self.sentence_length_limit * self.repair_multiplier):
                            current_app.logger.debug(
                                "Skipping repair for slightly-overlong chunk (len=%d, threshold=%s): %s",
                                word_count,
                                self.sentence_length_limit * self.repair_multiplier,
                                chunk[:80],
                            )
                        else:
                            # Use cache to avoid duplicate repairs in the same request
                            cached = self._repair_cache.get(chunk)
                            if cached is not None:
                                repaired = cached
                            else:
                                try:
                                    repaired = self._split_long_sentence(chunk)
                                except Exception as e:
                                    current_app.logger.warning(
                                        "Exception during long-sentence repair: %s", e
                                    )
                                    repaired = []
                                # Store whatever we got (including empty list) to avoid retry storms
                                self._repair_cache[chunk] = repaired

                    if repaired:
                        # Re-run post-processing on repaired pieces before continuing
                        for r in repaired:
                            processed.append(r)
                        # Skip the normal handling for this original chunk
                        continue

                # Quality Gate validation (spaCy-based verb detection)
                if self.quality_gate_enabled and self.quality_gate:
                    is_valid, rejection_reason = self.quality_gate.validate_sentence(chunk)
                    if not is_valid:
                        self.quality_gate_rejections += 1
                        self.rejected_sentences.append(
                            {"text": chunk, "reason": rejection_reason, "index": idx}
                        )
                        current_app.logger.warning(
                            'Quality gate rejected sentence at index %s: "%s" (reason: %s)',
                            idx,
                            chunk[:50],
                            rejection_reason,
                        )
                        continue  # Skip this sentence - do not add to processed

                # Check for fragments and log warnings (legacy heuristic)
                if self._is_likely_fragment(chunk):
                    fragment_count += 1
                    fragment_details.append(
                        {"index": idx, "text": chunk[:100], "word_count": len(chunk.split())}
                    )
                    current_app.logger.warning(
                        'Potential sentence fragment detected at index %s: "%s"', idx, chunk[:100]
                    )

                if (
                    len(chunk.split()) < self.min_sentence_length
                    and processed
                    and not original_unsplit
                ):
                    processed[-1] = f"{processed[-1]} {chunk}".strip()
                else:
                    processed.append(chunk)

        # Enhanced fragment reporting with quality assessment
        # Compute and store fragment stats on the instance for callers to inspect
        fragment_rate = (fragment_count / len(processed) * 100) if processed else 0
        self.last_fragment_rate = fragment_rate
        self.last_fragment_count = fragment_count
        self.last_fragment_details = fragment_details
        self.last_processed_sentences = [s.strip() for s in processed if s and s.strip()]

        if fragment_count > 0:
            current_app.logger.warning(
                "Fragment detection summary: %d potential fragments found out of %d sentences (%.1f%%)",
                fragment_count,
                len(processed),
                fragment_rate,
            )

            # Log sample fragments for debugging
            if fragment_details:
                sample_size = min(5, len(fragment_details))
                current_app.logger.warning(
                    "Sample fragments (first %d): %s",
                    sample_size,
                    [f["text"] for f in fragment_details[:sample_size]],
                )

        # If configured to reject on high fragment rate, raise an error so callers
        # can attempt fallback strategies (model swap, stricter prompt, etc.)
        if fragment_rate > self.fragment_rate_retry_threshold:
            msg = (
                f"HIGH FRAGMENT RATE DETECTED ({fragment_rate:.1f}%) - "
                f"fragment_count={fragment_count}, threshold={self.fragment_rate_retry_threshold}"
            )
            current_app.logger.error(msg)
            if self.reject_on_high_fragment_rate:
                raise GeminiAPIError(msg)

        return self.last_processed_sentences

    def _split_sentence(self, sentence: str) -> List[str]:
        """Validate and return sentence - no longer performs manual splitting.

        The AI model should handle all rewriting. This method now only serves as
        a pass-through that could log warnings for sentences exceeding limits.
        Manual chunking has been disabled to prevent sentence fragmentation.
        """
        # Defensive: coerce to string so None or other types don't crash
        sentence = "" if sentence is None else str(sentence)
        words = sentence.split()

        # Log a warning if Gemini returned a sentence that exceeds the limit
        # This helps identify when the AI model isn't following instructions
        if len(words) > self.sentence_length_limit:
            current_app.logger.warning(
                "Gemini returned sentence exceeding word limit (%d > %d): %s",
                len(words),
                self.sentence_length_limit,
                sentence[:100],
            )

        # Return the sentence as-is - trust the AI model's rewriting
        # Manual splitting/chunking is disabled to avoid creating fragments
        return [sentence]

    def _normalise_sentence(self, sentence: str) -> str:
        """Normalise whitespace and optional hyphenation fixes."""
        if sentence is None:
            return ""
        text = str(sentence).replace("\n", " ").strip()
        if self.fix_hyphenation:
            text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
        text = re.sub(r"\s+", " ", text)
        # Remove guillemets and smart quotes — we never want these characters
        # in the normalized output. Treat dialogue as normal sentences and
        # let the rewriting logic handle speaker attribution / content.
        text = re.sub(r"[«»“”]", "", text)

        # If the whole sentence is wrapped in ASCII quotes, remove them so
        # the model output will not include surrounding quotation marks.
        text = re.sub(r"^[\"\']\s*(.*?)\s*[\"\']$", r"\1", text)

        # Optionally preserve other formatting; at this point guillemets have
        # been removed regardless of preserve_formatting to satisfy user preference.
        if not self.preserve_formatting:
            # Keep minimal adjustments for spacing around any remaining markers
            text = text.replace("« ", "«").replace(" »", "»")

        # Remove leading reporting clauses like "Il dit :", "Sam dit :", "Elle ajouta :"
        # Pattern: optional speaker (capitalized name or pronoun) followed by up to 3 small tokens
        # then a reporting verb (dit, ajouta, répondit, etc.) and optional punctuation. Case-insensitive.
        try:
            reporting_re = re.compile(
                r"^\s*(?:(?:[A-Z][\w'’\-]+(?:\s+[A-Z][\w'’\-]+)*)|(?:il|elle|ils|elles|on|je|tu|nous|vous|lui|leur))(?:\s+\S{1,30}){0,3}\s+(?:a\s+dit|avait\s+dit|avait\s+r[ée]pondu|a\s+r[ée]pondu|r[ée]pondu|r[ée]pondit|dit|ditait|ajouta|ajoutait|ajoute|ajout[ée])\s*[:\-,\u2013\u2014]?\s*",
                flags=re.IGNORECASE,
            )
            new_text = reporting_re.sub("", text, count=1)
            # Also remove stray leading punctuation like multiple colons, dashes, or opening quotes
            new_text = re.sub(r'^[\s:;\'"«»\-–—]+', "", new_text)
            # Remove trailing closing quotes/punctuation so both opening and closing
            # quotation marks are removed when stripping reporting clauses
            new_text = re.sub(r'[\s:;\'"«»\-–—]+$', "", new_text)
            # Only accept the stripped form if it results in non-empty text
            if new_text and len(new_text.split()) >= 1:
                text = new_text
        except Exception:
            # If regex fails for some reason, just keep the original text
            pass

        return text.strip()

    def _looks_like_dialogue(self, sentence: str) -> bool:
        """Determine whether the sentence is likely dialogue."""
        if sentence is None:
            return False
        stripped = str(sentence).strip()
        if any(stripped.startswith(ch) for ch in self.DIALOGUE_BOUNDARIES):
            return True
        if stripped.endswith((":", "—")):
            return True
        return False

    def _is_likely_fragment(self, sentence: str) -> bool:
        """Check if a sentence appears to be a fragment rather than a complete sentence.

        This is an enhanced heuristic check to detect common patterns of sentence fragmentation.
        The AI model should produce zero fragments - any detected fragment indicates the model
        is performing segmentation instead of linguistic rewriting.

        Returns True if the sentence is likely a fragment.
        """
        if not sentence or not str(sentence).strip():
            return True

        sentence = str(sentence).strip()
        words = sentence.split()

        # Quick pattern checks for known idiomatic fragments (case-insensitive)
        # e.g., "Pour toujours et à jamais" should be considered a fragment
        if re.match(r"(?i)^\s*pour\s+toujours", sentence):
            current_app.logger.debug(
                'Fragment detected (idiomatic "pour toujours" start): %s', sentence[:60]
            )
            return True

        # Helper: conservative verb detection used in multiple checks below
        def _contains_conjugated_verb(tokens: List[str]) -> bool:
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
                "fait",
                "font",
                "vont",
                "va",
                "vais",
                "vas",
                "allons",
                "allez",
                "peut",
                "peuvent",
                "doit",
                "doivent",
                "veut",
                "veulent",
                "dit",
                "dis",
                "disent",
                "dites",
                "disait",
                "disaient",
                "voit",
                "voient",
                "vois",
                "voyez",
                "voyait",
                "voyaient",
                "prend",
                "prennent",
                "prends",
                "prenez",
                "prenait",
                "prenaient",
            }
            suffix_verb_forms = (
                "er",
                "ir",
                "oir",
                "ais",
                "ait",
                "aient",
                "iez",
                "ions",
                "ai",
                "as",
                "ont",
                "ez",
                "era",
                "erai",
                "eras",
                "erez",
                "eront",
                "é",
                "ée",
                "és",
                "ées",
            )

            for w in tokens:
                lw = w.lower().strip(".,;:!?…")

                # Check for exact verb forms
                if lw in exact_verb_forms:
                    return True

                # Check for verb forms in contractions (e.g., "est-il", "sont-ils")
                for verb in exact_verb_forms:
                    if lw.startswith(verb + "-"):
                        return True

                # Check for suffix verb forms
                for suf in suffix_verb_forms:
                    if lw.endswith(suf) and len(lw) > len(suf):
                        return True
            return False

        # Very short sentences are often fragments (unless they're valid imperatives,
        # exclamations, or interrogatives with a conjugated verb).
        if len(words) < 2:
            # Allow single-word imperatives, exclamations, or dialogue
            if sentence.endswith(("!", "?", ".")) or self._looks_like_dialogue(sentence):
                return False
            return True

        # If sentence is a question ending with '?' and contains a conjugated verb,
        # consider it a valid sentence (e.g., "Où est-il ?"). This reduces false positives
        # from the fragment detector for short interrogatives.
        if sentence.strip().endswith("?") and _contains_conjugated_verb(words):
            return False

        # Sentences ending only with comma are definite fragments
        if sentence.endswith(","):
            current_app.logger.debug("Fragment detected (ends with comma): %s", sentence[:50])
            return True

        # Sentences ending with semicolon are often fragments
        if sentence.endswith(";"):
            current_app.logger.debug("Fragment detected (ends with semicolon): %s", sentence[:50])
            return True

        first_word_lower = words[0].lower()

        # Dependent clauses starting with conjunctions without proper structure
        # Common fragment patterns in French
        fragment_starts_conjunctions = ["et", "mais", "donc", "car", "or", "ni", "puis"]
        if first_word_lower in fragment_starts_conjunctions:
            # Check if it's a complete sentence despite starting with conjunction
            # Must have proper punctuation and reasonable length
            if len(words) < 4 or not sentence.endswith((".", "!", "?", "…")):
                current_app.logger.debug(
                    "Fragment detected (conjunction start without completion): %s", sentence[:50]
                )
                return True

        # Prepositional phrases without a main verb - VERY common fragment pattern
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
        ]
        if first_word_lower in preposition_starts:
            # These are often fragments unless they're part of a complete sentence
            # Enhanced verb detection: look for common French verb patterns
            # Check for verb-like tokens. Use exact matching for very short
            # tokens (like 'a') to avoid false positives (e.g., 'la' ending with 'a').
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
            }
            suffix_verb_forms = (
                "er",
                "ir",
                "oir",  # Infinitives
                "ais",
                "ait",
                "aient",
                "iez",
                "ions",  # Imperfect
                "ai",
                "as",
                "ont",
                "ez",  # Present/past
                "era",
                "erai",
                "eras",
                "erez",
                "eront",  # Future
                "é",
                "ée",
                "és",
                "ées",  # Past participles
            )

            # Use conservative helper to detect any conjugated verb or
            # strong verb morphology in the token list.
            has_verb = _contains_conjugated_verb(words)
            if not has_verb:
                current_app.logger.debug(
                    "Fragment detected (preposition without verb): %s", sentence[:50]
                )
                return True

        # Special-case common idiomatic fragments like "pour toujours..." which
        # are often temporal/phrasing fragments without a verb
        low_sentence = sentence.lower()
        if "pour toujours" in low_sentence and not _contains_conjugated_verb(words):
            current_app.logger.debug(
                'Fragment detected ("pour toujours" idiomatic fragment): %s', sentence[:60]
            )
            return True

        # Temporal/time expressions that are often fragments
        temporal_starts = ["quand", "lorsque", "pendant", "durant", "avant", "après", "depuis"]
        if first_word_lower in temporal_starts and len(words) < 5:
            current_app.logger.debug(
                "Fragment detected (temporal expression without clause): %s", sentence[:50]
            )
            return True

        # Relative pronouns without main clause
        relative_starts = ["qui", "que", "dont", "où", "lequel", "laquelle"]
        if first_word_lower in relative_starts and len(words) < 4:
            current_app.logger.debug(
                "Fragment detected (relative pronoun without main clause): %s", sentence[:50]
            )
            return True

        # Participle phrases without auxiliary
        if len(words) >= 2:
            # Check if starts with past participle without auxiliary
            participle_patterns = ["tombaient", "retourné", "pensant", "marchant"]
            if any(words[0].lower().endswith(("ant", "é", "ée", "és", "ées")) for w in [words[0]]):
                # Check for auxiliary verb
                has_auxiliary = any(
                    word.lower()
                    in ("est", "sont", "a", "ont", "était", "étaient", "avait", "avaient")
                    for word in words
                )
                if not has_auxiliary and len(words) < 6:
                    current_app.logger.debug(
                        "Fragment detected (participle without auxiliary): %s", sentence[:50]
                    )
                    return True

        return False

    def local_normalize_text(self, text: str) -> Dict[str, Any]:
        """Local fallback when Gemini API fails completely.

        This is used when the Gemini API returns an empty or malformed response.
        It performs a conservative sentence segmentation using punctuation.
        Note: This fallback cannot perform linguistic rewriting and may produce
        fragments - it's a last resort when API calls fail.
        """
        if not text or not str(text).strip():
            return {"sentences": [], "tokens": 0}

        # Conservative segmentation: split on sentence-ending punctuation
        # followed by whitespace. Keep the punctuation with the sentence.
        try:
            segments = re.findall(r"[^.!?…]+[.!?…]?\s*", str(text))
            sentences = [s.strip() for s in segments if s and s.strip()]
            if not sentences:
                sentences = [str(text).strip()]

            processed = self._post_process_sentences(sentences)
            sentence_dicts = [{"normalized": s, "original": s} for s in processed]
            return {"sentences": sentence_dicts, "tokens": 0}
        except Exception as e:
            current_app.logger.exception("Local fallback segmentation failed: %s", e)
            # As a last resort, return the entire text as a single sentence
            t = str(text).strip()
            return {"sentences": [{"normalized": t, "original": t}], "tokens": 0}

    def _split_text_into_subchunks(self, text: str, num_subchunks: int = 2) -> List[str]:
        """Split text into smaller sub-chunks for recursive Gemini processing.

        Args:
            text: The text to split
            num_subchunks: Number of sub-chunks to create (default: 2)

        Returns:
            List of text sub-chunks
        """
        if not text or num_subchunks < 1:
            return [text] if text else []

        # Split on paragraph boundaries first (double newlines or sentence boundaries)
        paragraphs = re.split(r"\n\n+", text)
        if len(paragraphs) < num_subchunks:
            # Not enough paragraphs; split on sentence boundaries
            sentences = re.findall(r"[^.!?…]+[.!?…]", text)
            if len(sentences) < num_subchunks:
                # Not enough sentences; split by character count
                chunk_size = len(text) // num_subchunks
                return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
            else:
                # Distribute sentences evenly across subchunks
                chunk_size = len(sentences) // num_subchunks
                subchunks = []
                for i in range(0, len(sentences), chunk_size):
                    subchunk = "".join(sentences[i : i + chunk_size])
                    if subchunk.strip():
                        subchunks.append(subchunk.strip())
                return subchunks[:num_subchunks] if len(subchunks) > num_subchunks else subchunks
        else:
            # Distribute paragraphs evenly across subchunks
            chunk_size = len(paragraphs) // num_subchunks
            subchunks = []
            for i in range(0, len(paragraphs), chunk_size):
                subchunk = "\n\n".join(paragraphs[i : i + chunk_size])
                if subchunk.strip():
                    subchunks.append(subchunk.strip())
            return subchunks[:num_subchunks] if len(subchunks) > num_subchunks else subchunks

    def _merge_subchunk_results(self, subchunk_results: List[List[str]]) -> List[str]:
        """Merge results from processing multiple sub-chunks.

        Args:
            subchunk_results: List of sentence lists from each sub-chunk

        Returns:
            Merged and post-processed sentence list
        """
        # Simply concatenate all sentences from all subchunks
        all_sentences = []
        for sentences in subchunk_results:
            all_sentences.extend(sentences)

        # Run post-processing on merged result to handle any edge cases
        # at subchunk boundaries
        return self._post_process_sentences(all_sentences)

    def _call_gemini_api(self, text: str, prompt: str, model_name: str) -> Dict[str, Any]:
        """Low-level Gemini API call helper with timeout protection.

        Args:
            text: Text to process
            prompt: Prompt to use
            model_name: Model name to use

        Returns:
            Dict with 'sentences' list and 'tokens' count

        Raises:
            GeminiAPIError: If API returns empty or malformed response
            TimeoutError: If API call exceeds configured timeout
        """
        import signal

        # Get timeout from config (default 3 minutes)
        timeout_seconds = int(current_app.config.get("GEMINI_CALL_TIMEOUT_SECONDS", 180))

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Gemini API call exceeded {timeout_seconds}s timeout")

        # Place the user text/document before the prompt to match the PDF path
        # ordering used in generate_content_from_pdf. Some SDKs/models behave
        # more reliably when the primary content is provided first.
        contents = [text, prompt]

        current_app.logger.debug(
            "Calling Gemini API model=%s prompt_len=%s text_len=%s timeout=%ss",
            model_name,
            (len(prompt) if prompt else 0),
            (len(text) if text else 0),
            timeout_seconds,
        )

        # Set timeout alarm (Unix only; Windows will skip this)
        old_handler = None
        try:
            if hasattr(signal, "SIGALRM"):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)
        except (AttributeError, ValueError):
            # Windows or restricted environment - skip signal-based timeout
            current_app.logger.debug(
                "Signal-based timeout not available; relying on Celery soft_time_limit"
            )

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"
                        ),
                    ]
                ),
            )
        finally:
            # Cancel alarm if set
            if hasattr(signal, "SIGALRM") and old_handler is not None:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        # Coerce None to empty string
        response_text = getattr(response, "text", "") or ""
        cleaned_response = response_text.strip().replace("```json", "").replace("```", "")

        if not cleaned_response:
            # Log extra diagnostics for empty responses
            try:
                resp_repr = repr(response)
            except Exception:
                resp_repr = "<unrepresentable response>"
            current_app.logger.warning(
                "Gemini API returned empty cleaned_response for model=%s; raw_len=%s repr=%s",
                model_name,
                len(response_text),
                resp_repr[:1000],
            )
            raise GeminiAPIError("Gemini returned an empty response.", response_text)

        try:
            data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            # Attempt recovery
            try:
                data = self._recover_json(cleaned_response)
            except Exception:
                raise GeminiAPIError("Failed to parse Gemini JSON response.", response_text)

        sentences = self._extract_sentence_list(data)
        processed = self._post_process_sentences(sentences)

        sentence_dicts = [{"normalized": s, "original": s} for s in processed]
        return {"sentences": sentence_dicts, "tokens": 0}

    def _repair_fragments(
        self,
        fragments: List[Dict[str, Any]],
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
    ) -> List[str]:
        """Attempt to repair detected fragments by asking the model to rewrite them into full sentences.

        We build a small prompt providing the fragment and optional surrounding context.
        Returns a list of repaired sentences (one per fragment) or original fragment if repair failed.
        """
        repaired: List[str] = []
        if not fragments:
            return repaired

        # Build a compact repair prompt
        for frag in fragments:
            frag_text = frag.get("text") if isinstance(frag, dict) else str(frag)
            repair_prompt = (
                "Rewrite the following French fragment into a complete, independent, grammatically correct sentence. "
                "If needed, use the provided context. Return ONLY the single rewritten sentence.\n"
            )
            if context_before:
                repair_prompt += f"Context before: {context_before}\n"
            repair_prompt += f"Fragment: {frag_text}\n"

            try:
                resp = self._call_gemini_api(
                    frag_text, repair_prompt, self.MODEL_PREFERENCE_MAP.get("balanced")
                )
                sentences = [s["normalized"] for s in resp["sentences"]]
                if sentences:
                    repaired.append(sentences[0])
                else:
                    repaired.append(frag_text)
            except Exception:
                current_app.logger.debug("Fragment repair failed for fragment: %s", frag_text)
                repaired.append(frag_text)

        return repaired

    # Public helper for processing already-extracted text (non-PDF)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def normalize_text(self, text: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Normalize and split raw text into sentences using intelligent Gemini retry cascade.

        This method implements a multi-step fallback strategy:
        1. Try with the selected model and full prompt
        2. On failure, retry with a safer/heavier model (speed->balanced->quality)
        3. If still failing, split into sub-chunks and process each
        4. If still failing, try with minimal stripped prompt
        5. As absolute last resort, use local fallback (marked in result)

        Returns a dict with 'sentences' as a list of {normalized, original}.
        The dict may include '_fallback_method' to indicate which method succeeded.
        """
        if not text or not text.strip():
            return {"sentences": [], "tokens": 0}

        prompt_text = self.build_prompt(prompt)

        # Step 1: Try with original model and full prompt
        current_app.logger.info(
            "Attempting Gemini normalize_text with model=%s (preference=%s)",
            self.model_name,
            self.model_preference,
        )
        try:
            result = self._call_gemini_api(text, prompt_text, self.model_name)
            current_app.logger.info(
                "Successfully processed with original model %s", self.model_name
            )

            # Quality gate: if fragment rate exceeds retry threshold, attempt
            # stricter retry strategies before accepting the response.
            if self.last_fragment_rate <= self.fragment_rate_retry_threshold:
                return result

            current_app.logger.warning(
                "Fragment rate %.1f%% exceeds threshold %.1f%%; attempting retries",
                self.last_fragment_rate,
                self.fragment_rate_retry_threshold,
            )

            # 1) Retry with a stricter prompt (same model)
            strict_prompt = (
                prompt_text
                + "\n\nSTRICT: ZERO fragments. If any segment would be a fragment, rewrite it to be a complete sentence. Return valid JSON only."
            )
            try:
                strict_result = self._call_gemini_api(text, strict_prompt, self.model_name)
                if self.last_fragment_rate <= self.fragment_rate_retry_threshold:
                    strict_result["_fallback_method"] = "strict_prompt_retry"
                    current_app.logger.info(
                        "Recovered via strict prompt retry with model %s", self.model_name
                    )
                    return strict_result
            except Exception as e:
                current_app.logger.warning("Strict prompt retry failed: %s", str(e))

            # 2) Retry using higher-quality model
            quality_model = self.MODEL_PREFERENCE_MAP.get("quality")
            if quality_model and quality_model != self.model_name:
                try:
                    quality_result = self._call_gemini_api(text, prompt_text, quality_model)
                    if self.last_fragment_rate <= self.fragment_rate_retry_threshold:
                        quality_result["_fallback_method"] = "quality_model_retry"
                        current_app.logger.info("Recovered via quality model %s", quality_model)
                        return quality_result
                except Exception as e:
                    current_app.logger.warning("Quality model retry failed: %s", str(e))

            # 3) Attempt fragment repair pass (targeted corrections)
            try:
                fragments = self.last_fragment_details or []
                repaired = self._repair_fragments(fragments)
                if repaired:
                    # Replace fragment strings in last_processed_sentences with repaired ones
                    repaired_iter = iter(repaired)
                    merged = []
                    for s in self.last_processed_sentences:
                        replaced = False
                        for frag in fragments:
                            if s == (frag.get("text") if isinstance(frag, dict) else str(frag)):
                                try:
                                    merged.append(next(repaired_iter))
                                except StopIteration:
                                    merged.append(s)
                                replaced = True
                                break
                        if not replaced:
                            merged.append(s)

                    # Re-run post-processing on merged list to normalise
                    try:
                        repaired_processed = self._post_process_sentences(merged)
                        sentence_dicts = [
                            {"normalized": s, "original": s} for s in repaired_processed
                        ]
                        current_app.logger.info("Recovered via fragment repair pass")
                        return {
                            "sentences": sentence_dicts,
                            "tokens": 0,
                            "_fallback_method": "fragment_repair",
                        }
                    except Exception:
                        current_app.logger.warning("Post-processing of repaired sentences failed")
            except Exception as e:
                current_app.logger.warning("Fragment repair pass failed: %s", str(e))

            # If all corrective attempts failed, fall through to existing fallback cascade
            current_app.logger.warning(
                "All corrective retries failed; proceeding with fallback cascade"
            )
        except GeminiAPIError as e:
            current_app.logger.warning(
                "Primary Gemini call failed with model=%s: %s", self.model_name, str(e)
            )
            # Dump a short snippet of the raw response to debug intermittent empty responses
            if getattr(e, "raw_response", None):
                try:
                    current_app.logger.debug(
                        "Gemini raw_response (snippet): %s", e.raw_response[:2000]
                    )
                except Exception:
                    current_app.logger.debug(
                        "Gemini raw_response present but could not be displayed"
                    )
        except Exception as e:
            current_app.logger.exception(
                "Unexpected error during primary Gemini call with model=%s: %s",
                self.model_name,
                str(e),
            )

        # Step 2: Try model fallback cascade
        fallback_models = self.MODEL_FALLBACK_CASCADE.get(self.model_preference, [])
        for fallback_pref in fallback_models:
            fallback_model = self.MODEL_PREFERENCE_MAP.get(fallback_pref)
            if not fallback_model:
                continue

            current_app.logger.info(
                "Attempting model fallback: %s -> %s (%s)",
                self.model_preference,
                fallback_pref,
                fallback_model,
            )
            try:
                result = self._call_gemini_api(text, prompt_text, fallback_model)
                result["_fallback_method"] = f"model_fallback:{fallback_pref}"
                current_app.logger.info(
                    "Successfully processed with fallback model %s", fallback_model
                )
                return result
            except GeminiAPIError as e:
                current_app.logger.warning("Model fallback %s failed: %s", fallback_model, str(e))
            except Exception as e:
                current_app.logger.exception(
                    "Unexpected error during model fallback %s: %s", fallback_model, str(e)
                )

        # Step 3: Try subchunk splitting (divide and conquer)
        current_app.logger.info("Attempting subchunk processing (split into 2 parts)")
        try:
            subchunks = self._split_text_into_subchunks(text, num_subchunks=2)
            if len(subchunks) > 1:
                subchunk_results = []
                for i, subchunk in enumerate(subchunks):
                    current_app.logger.info("Processing subchunk %d/%d", i + 1, len(subchunks))
                    try:
                        # Try with original model first, then fallback models
                        sub_result = self._call_gemini_api(subchunk, prompt_text, self.model_name)
                        subchunk_results.append(sub_result["sentences"])
                    except Exception:
                        # Try fallback models for this subchunk
                        sub_processed = False
                        for fallback_pref in fallback_models:
                            fallback_model = self.MODEL_PREFERENCE_MAP.get(fallback_pref)
                            if not fallback_model:
                                continue
                            try:
                                sub_result = self._call_gemini_api(
                                    subchunk, prompt_text, fallback_model
                                )
                                subchunk_results.append(sub_result["sentences"])
                                sub_processed = True
                                break
                            except Exception:
                                continue

                        if not sub_processed:
                            raise Exception(f"All models failed for subchunk {i}")

                # Merge results from all subchunks
                merged_sentences = []
                for sub_sentences in subchunk_results:
                    merged_sentences.extend([s["normalized"] for s in sub_sentences])

                # Post-process merged sentences
                processed = self._post_process_sentences(merged_sentences)
                sentence_dicts = [{"normalized": s, "original": s} for s in processed]
                result = {
                    "sentences": sentence_dicts,
                    "tokens": 0,
                    "_fallback_method": "subchunk_split",
                }
                current_app.logger.info("Successfully processed via subchunk splitting")
                return result
            else:
                current_app.logger.info("Text too small to split into subchunks")
        except Exception as e:
            current_app.logger.warning("Subchunk processing failed: %s", str(e))

        # Step 4: Try minimal/stripped prompt
        current_app.logger.info("Attempting minimal prompt fallback")
        minimal_prompt = self.build_minimal_prompt()
        try:
            result = self._call_gemini_api(text, minimal_prompt, self.model_name)
            result["_fallback_method"] = "minimal_prompt"
            current_app.logger.info("Successfully processed with minimal prompt")
            return result
        except Exception as e:
            current_app.logger.warning("Minimal prompt fallback failed: %s", str(e))

            # Try minimal prompt with fallback models
            for fallback_pref in fallback_models:
                fallback_model = self.MODEL_PREFERENCE_MAP.get(fallback_pref)
                if not fallback_model:
                    continue
                try:
                    result = self._call_gemini_api(text, minimal_prompt, fallback_model)
                    result["_fallback_method"] = f"minimal_prompt_model_fallback:{fallback_pref}"
                    current_app.logger.info(
                        "Successfully processed with minimal prompt and model %s", fallback_model
                    )
                    return result
                except Exception:
                    continue

        # Step 5: Absolute last resort - local fallback (can be disabled by config)
        if not self.allow_local_fallback:
            # If local fallback is disabled, raise an explicit error so the
            # caller/task can decide whether to retry or fail the chunk. This
            # prevents silent degradation to conservative segmentation.
            current_app.logger.warning(
                "All Gemini retry strategies exhausted and local fallback is disabled by configuration."
            )
            raise GeminiAPIError("All Gemini retry strategies exhausted; local fallback disabled.")

        current_app.logger.warning(
            "All Gemini retry strategies exhausted; using local fallback as last resort"
        )
        result = self.local_normalize_text(text)
        result["_fallback_method"] = "local_segmentation"
        return result

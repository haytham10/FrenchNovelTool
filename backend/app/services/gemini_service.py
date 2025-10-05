import json
import pathlib
import re
from typing import List, Optional, Dict, Any

from flask import current_app
from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


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
        'balanced': 'gemini-2.5-flash',
        'quality': 'gemini-2.5-pro',
        'speed': 'gemini-2.5-flash-lite',
    }
    
    # Model fallback cascade: if current model fails, try these in order
    MODEL_FALLBACK_CASCADE = {
        'speed': ['balanced', 'quality'],
        'balanced': ['quality'],
        'quality': []  # No fallback for quality (already best model)
    }

    DIALOGUE_BOUNDARIES = ('"', "'", '«', '»', '“', '”')

    def __init__(
        self,
        sentence_length_limit: int = 8,
        *,
        model_preference: str = 'speed',
        ignore_dialogue: bool = False,
        preserve_formatting: bool = True,
        fix_hyphenation: bool = True,
        min_sentence_length: int = 2,
    ) -> None:
        self.client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
        self.model_preference = model_preference
        self.model_name = self.MODEL_PREFERENCE_MAP.get(
            model_preference,
            current_app.config.get('GEMINI_MODEL', 'gemini-2.5-flash-lite')
        )
        self.sentence_length_limit = sentence_length_limit
        self.ignore_dialogue = ignore_dialogue
        self.preserve_formatting = preserve_formatting
        self.fix_hyphenation = fix_hyphenation
        self.min_sentence_length = min_sentence_length
        self.max_retries = current_app.config['GEMINI_MAX_RETRIES']
        self.retry_delay = current_app.config['GEMINI_RETRY_DELAY']
        # Allow operator to disable local segmentation fallback via config.
        # Default: True to preserve existing behaviour unless explicitly changed.
        self.allow_local_fallback = current_app.config.get('GEMINI_ALLOW_LOCAL_FALLBACK', True)

    def build_prompt(self, base_prompt: Optional[str] = None) -> str:
        """Build the advanced Gemini prompt for French literary processing."""
        if base_prompt:
            return base_prompt

        dialogue_rule = (
            "If a sentence is enclosed in quotation marks (« », \" \", or ' '), "
            "keep it as-is without splitting regardless of length." if self.ignore_dialogue
            else "Do not split it unless absolutely necessary. If a split is unavoidable, "
                 "preserve the cadence and meaning of the dialogue."
        )

        min_length_rule = (
            f"If any rewritten sentence becomes shorter than {self.min_sentence_length} words, "
            "merge it with the previous or next sentence so that the narrative remains natural."
        )

        formatting_rules: List[str] = []
        if self.preserve_formatting:
            formatting_rules.append("Preserve the original quotation marks, italics markers, and ellipses.")
            formatting_rules.append("Keep the literary formatting intact unless it conflicts with readability.")
        if self.fix_hyphenation:
            formatting_rules.append(
                "If words are split with hyphens because of line breaks (e.g., 'ex- ample'), rejoin them into a single word."
            )

        sections = [
            "You are a literary assistant specialized in processing French novels. Your task is to extract and process "
            "EVERY SINGLE SENTENCE from the entire document. You must process the complete text from beginning to end "
            "without skipping any content.",
            f"If a sentence is {self.sentence_length_limit} words long or less, add it to the list as is. If a sentence is longer than "
            f"{self.sentence_length_limit} words, rewrite it into shorter sentences, each with {self.sentence_length_limit} words or fewer.",
            "",
            "**Rewriting Rules:**",
            "- Split long sentences at natural grammatical breaks (conjunctions like 'et', 'mais', 'donc', 'car', 'or'), subordinate clauses, or logical shifts in thought.",
            "- Maintain semantic integrity; each new sentence must stand alone grammatically and semantically.",
            "",
            "**Context-Awareness:**",
            "- Ensure the rewritten sentences maintain the logical flow and connection to the surrounding text.",
            "- The final output must read as a continuous, coherent narrative.",
            "",
            "**Dialogue Handling:**",
            f"- {dialogue_rule}",
            "",
            "**Style and Tone Preservation:**",
            "- Maintain the literary tone and voice of the original French text.",
            "- Preserve the exact original meaning and vocabulary where possible.",
            "",
            "**Sentence Length Guardrails:**",
            f"- {min_length_rule}",
            "- Do not create sentences with excessive repetition or filler words.",
            "",
            "**Hyphenation & Formatting:**",
        ]

        if formatting_rules:
            sections.extend(f"- {rule}" for rule in formatting_rules)
        else:
            sections.append("- Maintain consistent spacing and punctuation.")

        sections.extend([
            "",
            "**Output Format:**",
            "Present the final output as a JSON object with a single key 'sentences' containing an array of strings.",
            "For example: {\"sentences\": [\"Voici la première phrase.\", \"Et voici la deuxième.\"]}"
        ])

        return "\n".join(sections)
    
    def build_minimal_prompt(self) -> str:
        """Build a minimal prompt that only asks for JSON sentence list.
        
        Used as a fallback when the full prompt fails due to hallucination or format issues.
        """
        return (
            f"Extract and split all French sentences from the text. "
            f"If a sentence has more than {self.sentence_length_limit} words, split it into shorter sentences. "
            f"Return ONLY a JSON object: {{\"sentences\": [\"sentence 1\", \"sentence 2\", ...]}}. "
            f"Do not include any explanations or additional text."
        )


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    def generate_content_from_pdf(self, prompt: str, pdf_path: str) -> List[str]:
        """Generate content from a PDF using inline data and post-process sentences."""
        filepath = pathlib.Path(pdf_path)
        pdf_bytes = filepath.read_bytes()

        pdf_size_kb = len(pdf_bytes) / 1024
        current_app.logger.info("Processing PDF: %s, Size: %.2fKB", filepath.name, pdf_size_kb)

        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file_handle:
                try:
                    reader = PyPDF2.PdfReader(file_handle)
                    current_app.logger.info("PDF info: %s, Pages: %d", filepath.name, len(reader.pages))
                except Exception as exc:  # pragma: no cover - diagnostic logging
                    current_app.logger.warning("Couldn't extract PDF metadata: %s", exc)
        except ImportError:  # pragma: no cover - optional dependency
            current_app.logger.info("PyPDF2 not available for metadata extraction")

        pdf_part = types.Part.from_bytes(
            data=pdf_bytes,
            mime_type='application/pdf',
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[pdf_part, prompt],
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
                ]
            ),
        )

        # Some SDKs may set response.text to None; coerce to empty string to
        # avoid failing calls to .strip() or slicing when logging.
        response_text = getattr(response, 'text', '') or ''
        current_app.logger.debug('Raw Gemini response: %s', (response_text[:1000] if isinstance(response_text, str) else ''))

        cleaned_response = response_text.strip().replace('```json', '').replace('```', '')

        if not cleaned_response:
            current_app.logger.error('Received empty response from Gemini API.')
            raise GeminiAPIError('Gemini returned an empty response.', response_text)

        try:
            data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            current_app.logger.warning('Initial JSON parsing failed, attempting recovery...')
            try:
                data = self._recover_json(cleaned_response)
            except Exception:
                # _recover_json will log details; raise a GeminiAPIError attaching raw response
                raise GeminiAPIError('Failed to parse Gemini JSON response.', response_text)

        sentences = self._extract_sentence_list(data)
        processed_sentences = self._post_process_sentences(sentences)

        if not processed_sentences:
            current_app.logger.error('Gemini response contained no valid sentences after post-processing.')
            raise ValueError('Gemini response did not contain any valid sentences.')

        return processed_sentences

    def _recover_json(self, response: str) -> dict:
        """Attempt to recover a JSON document from a loosely formatted response."""
        json_start = response.find('{')
        if json_start >= 0:
            open_braces = 0
            json_end = -1
            for idx, char in enumerate(response[json_start:], start=json_start):
                if char == '{':
                    open_braces += 1
                elif char == '}':
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
            return {'sentences': sentences}

        current_app.logger.error('Failed to decode Gemini response: %s', response[:1000])
        raise ValueError('Failed to parse response from Gemini API.')

    def _extract_sentence_list(self, data) -> List[str]:
        """Normalise the sentences payload from a Gemini response."""
        sentences = None
        if isinstance(data, dict):
            sentences = data.get('sentences')
            if not sentences:
                if 'results' in data and isinstance(data['results'], list):
                    sentences = data['results']
                else:
                    for key, value in data.items():
                        if isinstance(value, list) and ('sentence' in key.lower() or 'text' in key.lower()):
                            sentences = value
                            break
        elif isinstance(data, list) and all(isinstance(item, str) for item in data):
            sentences = data

        if isinstance(sentences, str) and sentences.strip().startswith('[') and sentences.strip().endswith(']'):
            try:
                sentences = json.loads(sentences)
                current_app.logger.info('Converted string representation of list to actual list.')
            except json.JSONDecodeError:
                sentences = None

        if not isinstance(sentences, list):
            current_app.logger.error("Gemini response 'sentences' is not in list format: %s", sentences)
            raise ValueError("Gemini response 'sentences' is not in list format.")

        normalised = [str(sentence).strip() for sentence in sentences if sentence and str(sentence).strip()]
        if not normalised:
            current_app.logger.error('Gemini response contained no valid sentences: %s', sentences)
            raise GeminiAPIError('Gemini response did not contain any valid sentences.', str(sentences))

        return normalised

    def _post_process_sentences(self, sentences: List[str]) -> List[str]:
        """Apply manual splitting, merging, and normalisation rules to sentences."""
        processed: List[str] = []
        for idx, raw_sentence in enumerate(sentences):
            # Defensive: skip None inputs and log for diagnostics
            if raw_sentence is None:
                current_app.logger.warning('Skipping None sentence at index %s during post-processing', idx)
                continue

            # Normalize with guard
            try:
                text = self._normalise_sentence(raw_sentence)
            except Exception as e:
                current_app.logger.exception('Error normalising sentence at index %s: %s; raw=%r', idx, e, raw_sentence)
                continue

            if not text:
                continue

            if self.ignore_dialogue and self._looks_like_dialogue(text):
                processed.append(text)
                continue

            try:
                chunks = self._split_sentence(text)
            except Exception as e:
                current_app.logger.exception('Error splitting sentence at index %s: %s; text=%r', idx, e, text)
                chunks = [text]

            original_unsplit = len(chunks) == 1 and chunks[0] == text

            for chunk in chunks:
                try:
                    chunk = (chunk or '').strip()
                except Exception:
                    # If chunk is unexpectedly non-string, coerce and continue
                    chunk = str(chunk).strip() if chunk is not None else ''

                if not chunk:
                    continue

                if len(chunk.split()) < self.min_sentence_length and processed and not original_unsplit:
                    processed[-1] = f"{processed[-1]} {chunk}".strip()
                else:
                    processed.append(chunk)

        return [sentence.strip() for sentence in processed if sentence and sentence.strip()]

    def _split_sentence(self, sentence: str) -> List[str]:
        """Split sentences at natural boundaries while respecting word limits."""
        # Defensive: coerce to string so None or other types don't crash
        sentence = '' if sentence is None else str(sentence)
        words = sentence.split()
        if len(words) <= self.sentence_length_limit:
            return [sentence]

        chunks: List[str] = []
        current_words: List[str] = []
        for word in words:
            current_words.append(word)
            is_boundary = bool(re.search(r'[.!?;:,…]+["»”]*$', word))
            limit_reached = len(current_words) >= self.sentence_length_limit

            if limit_reached and not is_boundary:
                chunks.append(' '.join(current_words).strip())
                current_words = []
            elif is_boundary and len(current_words) >= max(self.min_sentence_length, self.sentence_length_limit // 2):
                chunks.append(' '.join(current_words).strip())
                current_words = []

        if current_words:
            tail = ' '.join(current_words).strip()
            if len(tail.split()) < self.min_sentence_length and chunks:
                chunks[-1] = f"{chunks[-1]} {tail}".strip()
            else:
                chunks.append(tail)

        return chunks

    def _normalise_sentence(self, sentence: str) -> str:
        """Normalise whitespace and optional hyphenation fixes."""
        if sentence is None:
            return ''
        text = str(sentence).replace('\n', ' ').strip()
        if self.fix_hyphenation:
            text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
        text = re.sub(r'\s+', ' ', text)
        if not self.preserve_formatting:
            text = text.replace('« ', '«').replace(' »', '»')
        return text.strip()

    def _looks_like_dialogue(self, sentence: str) -> bool:
        """Determine whether the sentence is likely dialogue."""
        if sentence is None:
            return False
        stripped = str(sentence).strip()
        if any(stripped.startswith(ch) for ch in self.DIALOGUE_BOUNDARIES):
            return True
        if stripped.endswith((':', '—')):
            return True
        return False

    def local_normalize_text(self, text: str) -> Dict[str, Any]:
        """Local fallback to segment and post-process text without calling Gemini.

        This is used when the Gemini API returns an empty or malformed response.
        It performs a conservative sentence segmentation using punctuation and
        then runs the existing post-processing pipeline.
        """
        if not text or not str(text).strip():
            return {"sentences": [], "tokens": 0}

        # Conservative segmentation: split on sentence-ending punctuation
        # followed by whitespace. Keep the punctuation with the sentence.
        try:
            segments = re.findall(r'[^.!?…]+[.!?…]?\s*', str(text))
            sentences = [s.strip() for s in segments if s and s.strip()]
            if not sentences:
                sentences = [str(text).strip()]

            processed = self._post_process_sentences(sentences)
            sentence_dicts = [{"normalized": s, "original": s} for s in processed]
            return {"sentences": sentence_dicts, "tokens": 0}
        except Exception as e:
            current_app.logger.exception('Local fallback segmentation failed: %s', e)
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
        paragraphs = re.split(r'\n\n+', text)
        if len(paragraphs) < num_subchunks:
            # Not enough paragraphs; split on sentence boundaries
            sentences = re.findall(r'[^.!?…]+[.!?…]', text)
            if len(sentences) < num_subchunks:
                # Not enough sentences; split by character count
                chunk_size = len(text) // num_subchunks
                return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
            else:
                # Distribute sentences evenly across subchunks
                chunk_size = len(sentences) // num_subchunks
                subchunks = []
                for i in range(0, len(sentences), chunk_size):
                    subchunk = ''.join(sentences[i:i+chunk_size])
                    if subchunk.strip():
                        subchunks.append(subchunk.strip())
                return subchunks[:num_subchunks] if len(subchunks) > num_subchunks else subchunks
        else:
            # Distribute paragraphs evenly across subchunks
            chunk_size = len(paragraphs) // num_subchunks
            subchunks = []
            for i in range(0, len(paragraphs), chunk_size):
                subchunk = '\n\n'.join(paragraphs[i:i+chunk_size])
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
        """Low-level Gemini API call helper.
        
        Args:
            text: Text to process
            prompt: Prompt to use
            model_name: Model name to use
            
        Returns:
            Dict with 'sentences' list and 'tokens' count
            
        Raises:
            GeminiAPIError: If API returns empty or malformed response
        """
        contents = [prompt, text]
        
        response = self.client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
                ]
            ),
        )
        
        # Coerce None to empty string
        response_text = getattr(response, 'text', '') or ''
        cleaned_response = response_text.strip().replace('```json', '').replace('```', '')
        
        if not cleaned_response:
            raise GeminiAPIError('Gemini returned an empty response.', response_text)
        
        try:
            data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            # Attempt recovery
            try:
                data = self._recover_json(cleaned_response)
            except Exception:
                raise GeminiAPIError('Failed to parse Gemini JSON response.', response_text)
        
        sentences = self._extract_sentence_list(data)
        processed = self._post_process_sentences(sentences)
        
        sentence_dicts = [{"normalized": s, "original": s} for s in processed]
        return {"sentences": sentence_dicts, "tokens": 0}


    # Public helper for processing already-extracted text (non-PDF)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
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
            'Attempting Gemini normalize_text with model=%s (preference=%s)',
            self.model_name, self.model_preference
        )
        try:
            result = self._call_gemini_api(text, prompt_text, self.model_name)
            current_app.logger.info('Successfully processed with original model %s', self.model_name)
            return result
        except GeminiAPIError as e:
            current_app.logger.warning(
                'Primary Gemini call failed with model=%s: %s',
                self.model_name, str(e)
            )
        except Exception as e:
            current_app.logger.exception(
                'Unexpected error during primary Gemini call with model=%s: %s',
                self.model_name, str(e)
            )
        
        # Step 2: Try model fallback cascade
        fallback_models = self.MODEL_FALLBACK_CASCADE.get(self.model_preference, [])
        for fallback_pref in fallback_models:
            fallback_model = self.MODEL_PREFERENCE_MAP.get(fallback_pref)
            if not fallback_model:
                continue
            
            current_app.logger.info(
                'Attempting model fallback: %s -> %s (%s)',
                self.model_preference, fallback_pref, fallback_model
            )
            try:
                result = self._call_gemini_api(text, prompt_text, fallback_model)
                result['_fallback_method'] = f'model_fallback:{fallback_pref}'
                current_app.logger.info('Successfully processed with fallback model %s', fallback_model)
                return result
            except GeminiAPIError as e:
                current_app.logger.warning(
                    'Model fallback %s failed: %s',
                    fallback_model, str(e)
                )
            except Exception as e:
                current_app.logger.exception(
                    'Unexpected error during model fallback %s: %s',
                    fallback_model, str(e)
                )
        
        # Step 3: Try subchunk splitting (divide and conquer)
        current_app.logger.info('Attempting subchunk processing (split into 2 parts)')
        try:
            subchunks = self._split_text_into_subchunks(text, num_subchunks=2)
            if len(subchunks) > 1:
                subchunk_results = []
                for i, subchunk in enumerate(subchunks):
                    current_app.logger.info('Processing subchunk %d/%d', i+1, len(subchunks))
                    try:
                        # Try with original model first, then fallback models
                        sub_result = self._call_gemini_api(subchunk, prompt_text, self.model_name)
                        subchunk_results.append(sub_result['sentences'])
                    except Exception:
                        # Try fallback models for this subchunk
                        sub_processed = False
                        for fallback_pref in fallback_models:
                            fallback_model = self.MODEL_PREFERENCE_MAP.get(fallback_pref)
                            if not fallback_model:
                                continue
                            try:
                                sub_result = self._call_gemini_api(subchunk, prompt_text, fallback_model)
                                subchunk_results.append(sub_result['sentences'])
                                sub_processed = True
                                break
                            except Exception:
                                continue
                        
                        if not sub_processed:
                            raise Exception(f'All models failed for subchunk {i}')
                
                # Merge results from all subchunks
                merged_sentences = []
                for sub_sentences in subchunk_results:
                    merged_sentences.extend([s['normalized'] for s in sub_sentences])
                
                # Post-process merged sentences
                processed = self._post_process_sentences(merged_sentences)
                sentence_dicts = [{"normalized": s, "original": s} for s in processed]
                result = {"sentences": sentence_dicts, "tokens": 0, "_fallback_method": "subchunk_split"}
                current_app.logger.info('Successfully processed via subchunk splitting')
                return result
            else:
                current_app.logger.info('Text too small to split into subchunks')
        except Exception as e:
            current_app.logger.warning('Subchunk processing failed: %s', str(e))
        
        # Step 4: Try minimal/stripped prompt
        current_app.logger.info('Attempting minimal prompt fallback')
        minimal_prompt = self.build_minimal_prompt()
        try:
            result = self._call_gemini_api(text, minimal_prompt, self.model_name)
            result['_fallback_method'] = 'minimal_prompt'
            current_app.logger.info('Successfully processed with minimal prompt')
            return result
        except Exception as e:
            current_app.logger.warning('Minimal prompt fallback failed: %s', str(e))
            
            # Try minimal prompt with fallback models
            for fallback_pref in fallback_models:
                fallback_model = self.MODEL_PREFERENCE_MAP.get(fallback_pref)
                if not fallback_model:
                    continue
                try:
                    result = self._call_gemini_api(text, minimal_prompt, fallback_model)
                    result['_fallback_method'] = f'minimal_prompt_model_fallback:{fallback_pref}'
                    current_app.logger.info(
                        'Successfully processed with minimal prompt and model %s',
                        fallback_model
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
                'All Gemini retry strategies exhausted and local fallback is disabled by configuration.'
            )
            raise GeminiAPIError('All Gemini retry strategies exhausted; local fallback disabled.')

        current_app.logger.warning(
            'All Gemini retry strategies exhausted; using local fallback as last resort'
        )
        result = self.local_normalize_text(text)
        result['_fallback_method'] = 'local_segmentation'
        return result
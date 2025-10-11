import json
import pathlib
import re
from typing import List, Optional, Dict, Any, Callable

from flask import current_app
from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class PromptEngine:
    """Generates adaptive prompts based on sentence characteristics.

    This class implements a three-tier prompt system:
    1. Passthrough: For sentences already meeting 4-8 word + verb criteria
    2. Light Rewrite: For sentences needing minor adjustments
    3. Heavy Rewrite: For complex sentences requiring decomposition

    This replaces the monolithic 1,265-line prompt with focused, contextual prompts.
    """

    @staticmethod
    def classify_sentence_tier(metadata: Dict) -> str:
        """Classify sentence into processing tier based on metadata.

        Args:
            metadata: Dictionary with 'token_count', 'has_verb', 'complexity_score'

        Returns:
            'passthrough', 'light', or 'heavy'
        """
        token_count = metadata.get('token_count', 0)
        has_verb = metadata.get('has_verb', False)
        complexity_score = metadata.get('complexity_score', 0)

        # TIER 1: Already perfect (4-8 words + verb)
        if 4 <= token_count <= 8 and has_verb:
            return 'passthrough'

        # TIER 2: Needs minor adjustment (close to target)
        # 3-10 words, or missing verb but otherwise simple
        elif 3 <= token_count <= 10:
            return 'light'

        # TIER 3: Needs aggressive rewriting (complex/long)
        else:
            return 'heavy'

    @staticmethod
    def generate_prompt(tier: str, sentence_length_limit: int, min_sentence_length: int) -> str:
        """Generate appropriate prompt based on tier.

        Args:
            tier: 'passthrough', 'light', or 'heavy'
            sentence_length_limit: Maximum word count
            min_sentence_length: Minimum word count

        Returns:
            Prompt string
        """
        if tier == 'passthrough':
            return PromptEngine.build_passthrough_prompt(sentence_length_limit, min_sentence_length)
        elif tier == 'light':
            return PromptEngine.build_light_rewrite_prompt(sentence_length_limit, min_sentence_length)
        else:
            return PromptEngine.build_heavy_rewrite_prompt(sentence_length_limit, min_sentence_length)

    @staticmethod
    def build_passthrough_prompt(sentence_length_limit: int, min_sentence_length: int) -> str:
        """For sentences already meeting criteria - minimal processing.

        ~30 lines - just validation and return.
        """
        return f"""You are a French text validator. The sentences below are already correctly formatted.
Return them unchanged in JSON format.

VALIDATION CRITERIA (already met):
✓ {min_sentence_length}-{sentence_length_limit} words
✓ Contains a conjugated verb
✓ Grammatically complete

YOUR TASK:
Simply verify and return the sentences as-is.

OUTPUT FORMAT (STRICT JSON):
{{"sentences": ["sentence 1", "sentence 2"]}}

No markdown, no code blocks, just JSON."""

    @staticmethod
    def build_light_rewrite_prompt(sentence_length_limit: int, min_sentence_length: int) -> str:
        """For sentences needing minor adjustments.

        ~80-100 lines - focused adjustments without full decomposition.
        """
        return f"""You are a French linguistic expert. Adjust the sentences to meet these criteria.

CRITICAL REQUIREMENTS (ALL MANDATORY):
1. Length: {min_sentence_length}-{sentence_length_limit} words (strict)
2. Must contain a conjugated verb (not infinitive)
3. Grammatically complete sentence
4. Preserves original vocabulary

ALLOWED ADJUSTMENTS:
• Add subject pronoun if missing (il, elle, on, je, tu, nous, vous)
• Add auxiliary verb if needed (est, sont, a, ont, était, sera)
• Add "C'est..." construction to convert phrases to sentences
• Remove redundant words to fit length constraint
• Simplify verb tense if necessary (keep present/imperfect/future)

FORBIDDEN:
• Changing core vocabulary
• Creating fragments (prepositional phrases alone)
• Removing the main verb
• Splitting into multiple sentences (that's for heavy rewrite)

VERB REQUIREMENT:
Every output sentence MUST contain a conjugated verb:
✓ "Elle marche." (present tense)
✓ "Il était triste." (imperfect)
✓ "Cela durera." (future)
✗ "Pour toujours." (NO VERB!)
✗ "Dans la rue." (NO VERB!)

EXAMPLES:

Input: "Pour toujours et à jamais."
❌ Wrong: ["Pour toujours et à jamais."] ← No verb!
✓ Correct: ["Cela durera pour toujours."] ← Has verb "durera", 4 words

Input: "Maintenant ou jamais."
❌ Wrong: ["Maintenant ou jamais."] ← No verb!
✓ Correct: ["C'est maintenant ou jamais."] ← Has verb "est", 4 words

Input: "Dans quinze ans, c'est moi qui serai là."
✓ Correct: ["Dans quinze ans, je serai là."] ← Already good, simplified slightly

VALIDATION CHECKLIST (before outputting):
☐ Each sentence is {min_sentence_length}-{sentence_length_limit} words
☐ Each sentence has a conjugated verb
☐ Each sentence is grammatically complete
☐ Original vocabulary is preserved

OUTPUT FORMAT (STRICT JSON):
{{"sentences": ["sentence 1", "sentence 2"]}}

No markdown, no code blocks, just JSON."""

    @staticmethod
    def build_heavy_rewrite_prompt(sentence_length_limit: int, min_sentence_length: int) -> str:
        """For complex sentences requiring decomposition.

        ~120-140 lines - full decomposition strategy with examples.
        """
        return f"""You are a French linguistic expert. Decompose these complex sentences into multiple simple sentences.

═══════════════════════════════════════════════════════════════
CRITICAL REQUIREMENTS FOR EACH OUTPUT SENTENCE
═══════════════════════════════════════════════════════════════

1. Length: {min_sentence_length}-{sentence_length_limit} words (STRICT - count carefully!)
2. Structure: Subject + Conjugated Verb + (Object/Complement)
3. Completeness: Must be grammatically independent
4. Vocabulary: Preserve all meaningful words from the original

═══════════════════════════════════════════════════════════════
DECOMPOSITION STRATEGY
═══════════════════════════════════════════════════════════════

STEP 1: Identify core propositions
• Who does what?
• Who is what?
• What happens?

STEP 2: Extract each proposition
• Create a standalone sentence for each proposition
• Add subjects/verbs as needed for completeness

STEP 3: Verify each output sentence
• Has subject (explicit or pronoun)
• Has conjugated verb (not infinitive)
• Is {min_sentence_length}-{sentence_length_limit} words
• Can stand alone without context

═══════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════

Example 1: Long descriptive sentence
Input: "Il marchait lentement dans la rue sombre et froide, pensant à elle."
❌ WRONG (fragments): ["dans la rue sombre", "et froide", "pensant à elle"]
✓ CORRECT (complete): [
  "Il marchait dans la rue.",
  "La rue était sombre et froide.",
  "Il pensait à elle."
]

Example 2: Complex action sequence
Input: "Vous longez un kiosque à journaux, jetez un coup d'œil à la une du New York Times."
✓ CORRECT: [
  "Vous longez un kiosque à journaux.",
  "Vous regardez la une du journal.",
  "C'est le New York Times."
]

Example 3: Very long sentence
Input: "Ethan envoya une main hasardeuse qui tâtonna plusieurs secondes avant de stopper la montée en puissance de la sonnerie du réveil."
✓ CORRECT: [
  "Ethan envoya une main hasardeuse.",
  "Sa main tâtonna plusieurs secondes.",
  "Il stoppa la sonnerie du réveil."
]

Example 4: Embedded clauses
Input: "It's Now or Never, le standard d'Elvis Presley, se déverse bruyamment sur le trottoir."
✓ CORRECT: [
  "Le standard d'Elvis Presley joue.",
  "C'est It's Now or Never.",
  "La musique se déverse bruyamment."
]

═══════════════════════════════════════════════════════════════
VERB REQUIREMENT (CRITICAL!)
═══════════════════════════════════════════════════════════════

Every output sentence MUST contain a conjugated verb:
✓ "Il marche." (present)
✓ "Elle était triste." (imperfect)
✓ "Nous partirons." (future)
✓ "J'ai mangé." (passé composé)
✗ "Pour toujours." (no verb!)
✗ "Dans la rue sombre." (no verb!)
✗ "Pensant à elle." (participle only - no auxiliary!)

═══════════════════════════════════════════════════════════════
VALIDATION CHECKLIST (before outputting)
═══════════════════════════════════════════════════════════════

For EACH output sentence, verify:
☐ Has a subject (explicit noun/name OR pronoun: il/elle/je/vous/nous/ils/elles)
☐ Has a conjugated verb (est/sont/a/ont/marche/marchait/sera/etc.)
☐ Is {min_sentence_length}-{sentence_length_limit} words (COUNT CAREFULLY!)
☐ Can stand alone (not a prepositional phrase, not a conjunction fragment)
☐ Preserves vocabulary from original

COMMON ERRORS TO AVOID:
✗ Prepositional phrases: "dans la rue", "avec elle", "pour toujours"
✗ Conjunction fragments: "et froide", "mais aussi", "donc ensuite"
✗ Participial phrases: "pensant à elle", "marchant lentement"
✗ Infinitive phrases: "pour partir", "avant de stopper"

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT (STRICT JSON)
═══════════════════════════════════════════════════════════════

{{"sentences": ["sentence 1", "sentence 2", "sentence 3"]}}

No markdown, no code blocks, no explanations, JUST JSON."""


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
        self.allow_local_fallback = current_app.config.get('GEMINI_ALLOW_LOCAL_FALLBACK', False)
        # Repair controls (to limit additional Gemini API calls which can be slow)
        # Enable / disable the targeted long-sentence repair step
        self.enable_repair = bool(current_app.config.get('GEMINI_ENABLE_REPAIR', True))
        # Only attempt repair if sentence length > sentence_length_limit * repair_multiplier
        self.repair_multiplier = float(current_app.config.get('GEMINI_REPAIR_MULTIPLIER', 1.5))
        # Maximum repair attempts per unique chunk within a single request
        self.max_repair_attempts = int(current_app.config.get('GEMINI_MAX_REPAIR_ATTEMPTS', 1))
        # Simple in-request cache to avoid repeating repairs for identical chunks
        self._repair_cache = {}

        # Runtime stats from last post-processing step
        self.last_fragment_rate = 0.0
        self.last_fragment_count = 0
        self.last_fragment_details = []
        self.last_processed_sentences = []

        # Retry / QC configuration
        self.fragment_rate_retry_threshold = float(
            current_app.config.get('GEMINI_FRAGMENT_RATE_RETRY_THRESHOLD', 3.0)
        )
        self.reject_on_high_fragment_rate = bool(
            current_app.config.get('GEMINI_REJECT_ON_HIGH_FRAGMENT_RATE', False)
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
            "Return ONLY a JSON object: {\"sentences\": [\"Sentence 1.\", \"Sentence 2.\"]}."
        )

        try:
            resp = self._call_gemini_api(sentence, repair_prompt, self.MODEL_PREFERENCE_MAP.get('balanced') or self.model_name)
            # resp['sentences'] is a list of {"normalized": s, "original": s}
            sentences = [item.get('normalized') if isinstance(item, dict) else str(item) for item in resp.get('sentences', [])]
            # Ensure returned strings are stripped and non-empty
            return [s.strip() for s in sentences if s and str(s).strip()]
        except Exception as e:
            current_app.logger.warning('Long-sentence repair failed: %s; sentence=%r', e, sentence[:200])
            return []
    
    def build_minimal_prompt(self) -> str:
        """Build a minimal prompt that only asks for JSON sentence list.
        
        Used as a fallback when the full prompt fails due to hallucination or format issues.
        Even in minimal mode, we emphasize complete sentences over segmentation.
        """
        # Compact minimal prompt (keeps it short for quick fallback use)
        return (
            f"Rewrite into independent French sentences ({self.min_sentence_length}-{self.sentence_length_limit} words). "
            f"Return ONLY JSON: {{\"sentences\": [\"Sentence 1.\", \"Sentence 2.\"]}}."
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
            from app.pdf_compat import PdfReader
            with open(pdf_path, 'rb') as file_handle:
                try:
                    reader = PdfReader(file_handle)
                    current_app.logger.info("PDF info: %s, Pages: %d", filepath.name, len(reader.pages))
                except Exception as exc:  # pragma: no cover - diagnostic logging
                    current_app.logger.warning("Couldn't extract PDF metadata: %s", exc)
        except ImportError:  # pragma: no cover - optional dependency
            current_app.logger.info("PDF backend not available for metadata extraction")
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
                        current_app.logger.debug('Repair disabled for chunk (len=%d): %s', word_count, chunk[:80])
                    else:
                        # Only attempt repair if chunk is significantly over the limit
                        if word_count < int(self.sentence_length_limit * self.repair_multiplier):
                            current_app.logger.debug(
                                'Skipping repair for slightly-overlong chunk (len=%d, threshold=%s): %s',
                                word_count, self.sentence_length_limit * self.repair_multiplier, chunk[:80]
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
                                    current_app.logger.warning('Exception during long-sentence repair: %s', e)
                                    repaired = []
                                # Store whatever we got (including empty list) to avoid retry storms
                                self._repair_cache[chunk] = repaired

                    if repaired:
                        # Re-run post-processing on repaired pieces before continuing
                        for r in repaired:
                            processed.append(r)
                        # Skip the normal handling for this original chunk
                        continue
                
                # Check for fragments and log warnings
                if self._is_likely_fragment(chunk):
                    fragment_count += 1
                    fragment_details.append({
                        'index': idx,
                        'text': chunk[:100],
                        'word_count': len(chunk.split())
                    })
                    current_app.logger.warning(
                        'Potential sentence fragment detected at index %s: "%s"',
                        idx, chunk[:100]
                    )

                if len(chunk.split()) < self.min_sentence_length and processed and not original_unsplit:
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
                'Fragment detection summary: %d potential fragments found out of %d sentences (%.1f%%)',
                fragment_count, len(processed), fragment_rate
            )

            # Log sample fragments for debugging
            if fragment_details:
                sample_size = min(5, len(fragment_details))
                current_app.logger.warning(
                    'Sample fragments (first %d): %s',
                    sample_size,
                    [f['text'] for f in fragment_details[:sample_size]]
                )

        # If configured to reject on high fragment rate, raise an error so callers
        # can attempt fallback strategies (model swap, stricter prompt, etc.)
        if fragment_rate > self.fragment_rate_retry_threshold:
            msg = (
                f'HIGH FRAGMENT RATE DETECTED ({fragment_rate:.1f}%) - ' 
                f'fragment_count={fragment_count}, threshold={self.fragment_rate_retry_threshold}'
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
        sentence = '' if sentence is None else str(sentence)
        words = sentence.split()
        
        # Log a warning if Gemini returned a sentence that exceeds the limit
        # This helps identify when the AI model isn't following instructions
        if len(words) > self.sentence_length_limit:
            current_app.logger.warning(
                'Gemini returned sentence exceeding word limit (%d > %d): %s',
                len(words), self.sentence_length_limit, sentence[:100]
            )
        
        # Return the sentence as-is - trust the AI model's rewriting
        # Manual splitting/chunking is disabled to avoid creating fragments
        return [sentence]


    def _normalise_sentence(self, sentence: str) -> str:
        """Normalise whitespace and optional hyphenation fixes."""
        if sentence is None:
            return ''
        text = str(sentence).replace('\n', ' ').strip()
        if self.fix_hyphenation:
            text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
        text = re.sub(r'\s+', ' ', text)
        # Remove guillemets and smart quotes — we never want these characters
        # in the normalized output. Treat dialogue as normal sentences and
        # let the rewriting logic handle speaker attribution / content.
        text = re.sub(r'[«»“”]', '', text)

        # If the whole sentence is wrapped in ASCII quotes, remove them so
        # the model output will not include surrounding quotation marks.
        text = re.sub(r'^[\"\']\s*(.*?)\s*[\"\']$', r'\1', text)

        # Optionally preserve other formatting; at this point guillemets have
        # been removed regardless of preserve_formatting to satisfy user preference.
        if not self.preserve_formatting:
            # Keep minimal adjustments for spacing around any remaining markers
            text = text.replace('« ', '«').replace(' »', '»')

        # Remove leading reporting clauses like "Il dit :", "Sam dit :", "Elle ajouta :"
        # Pattern: optional speaker (capitalized name or pronoun) followed by up to 3 small tokens
        # then a reporting verb (dit, ajouta, répondit, etc.) and optional punctuation. Case-insensitive.
        try:
            reporting_re = re.compile(
                r"^\s*(?:(?:[A-Z][\w'’\-]+(?:\s+[A-Z][\w'’\-]+)*)|(?:il|elle|ils|elles|on|je|tu|nous|vous|lui|leur))(?:\s+\S{1,30}){0,3}\s+(?:a\s+dit|avait\s+dit|avait\s+r[ée]pondu|a\s+r[ée]pondu|r[ée]pondu|r[ée]pondit|dit|ditait|ajouta|ajoutait|ajoute|ajout[ée])\s*[:\-,\u2013\u2014]?\s*",
                flags=re.IGNORECASE,
            )
            new_text = reporting_re.sub('', text, count=1)
            # Also remove stray leading punctuation like multiple colons, dashes, or opening quotes
            new_text = re.sub(r'^[\s:;\'"«»\-–—]+', '', new_text)
            # Remove trailing closing quotes/punctuation so both opening and closing
            # quotation marks are removed when stripping reporting clauses
            new_text = re.sub(r'[\s:;\'"«»\-–—]+$', '', new_text)
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
        if stripped.endswith((':', '—')):
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
        if re.match(r'(?i)^\s*pour\s+toujours', sentence):
            current_app.logger.debug('Fragment detected (idiomatic "pour toujours" start): %s', sentence[:60])
            return True

        # Helper: conservative verb detection used in multiple checks below
        def _contains_conjugated_verb(tokens: List[str]) -> bool:
            exact_verb_forms = {
                'a', 'ai', 'as', 'ont', 'ez', 'est', 'sont', 'était', 'étaient',
                'sera', 'seront', 'avait', 'avaient', 'aura', 'auront',
                'fut', 'furent', 'soit', 'soient', 'fût'
            }
            suffix_verb_forms = (
                'er', 'ir', 'oir',
                'ais', 'ait', 'aient', 'iez', 'ions',
                'ai', 'as', 'ont', 'ez',
                'era', 'erai', 'eras', 'erez', 'eront',
                'é', 'ée', 'és', 'ées'
            )

            for w in tokens:
                lw = w.lower().strip(".,;:!?…")
                if lw in exact_verb_forms:
                    return True
                for suf in suffix_verb_forms:
                    if lw.endswith(suf) and len(lw) > len(suf):
                        return True
            return False
        
        # Very short sentences are often fragments (unless they're valid imperatives,
        # exclamations, or interrogatives with a conjugated verb).
        if len(words) < 2:
            # Allow single-word imperatives, exclamations, or dialogue
            if sentence.endswith(('!', '?', '.')) or self._looks_like_dialogue(sentence):
                return False
            return True

        # If sentence is a question ending with '?' and contains a conjugated verb,
        # consider it a valid sentence (e.g., "Où est-il ?"). This reduces false positives
        # from the fragment detector for short interrogatives.
        if sentence.strip().endswith('?') and _contains_conjugated_verb(words):
            return False
        
        # Sentences ending only with comma are definite fragments
        if sentence.endswith(','):
            current_app.logger.debug('Fragment detected (ends with comma): %s', sentence[:50])
            return True
        
        # Sentences ending with semicolon are often fragments
        if sentence.endswith(';'):
            current_app.logger.debug('Fragment detected (ends with semicolon): %s', sentence[:50])
            return True
        
        first_word_lower = words[0].lower()
        
        # Dependent clauses starting with conjunctions without proper structure
        # Common fragment patterns in French
        fragment_starts_conjunctions = ['et', 'mais', 'donc', 'car', 'or', 'ni', 'puis']
        if first_word_lower in fragment_starts_conjunctions:
            # Check if it's a complete sentence despite starting with conjunction
            # Must have proper punctuation and reasonable length
            if len(words) < 4 or not sentence.endswith(('.', '!', '?', '…')):
                current_app.logger.debug(
                    'Fragment detected (conjunction start without completion): %s',
                    sentence[:50]
                )
                return True
        
        # Prepositional phrases without a main verb - VERY common fragment pattern
        preposition_starts = ['dans', 'sur', 'sous', 'avec', 'sans', 'pour', 'de', 'à', 'vers', 'chez', 'par']
        if first_word_lower in preposition_starts:
            # These are often fragments unless they're part of a complete sentence
            if not _contains_conjugated_verb(words):
                current_app.logger.debug('Fragment detected (preposition without verb): %s', sentence[:50])
                return True

        # Special-case common idiomatic fragments like "pour toujours..." which
        # are often temporal/phrasing fragments without a verb
        low_sentence = sentence.lower()
        if 'pour toujours' in low_sentence and not _contains_conjugated_verb(words):
            current_app.logger.debug('Fragment detected ("pour toujours" idiomatic fragment): %s', sentence[:60])
            return True
        
        # Temporal/time expressions that are often fragments
        temporal_starts = ['quand', 'lorsque', 'pendant', 'durant', 'avant', 'après', 'depuis']
        if first_word_lower in temporal_starts and len(words) < 5:
            current_app.logger.debug(
                'Fragment detected (temporal expression without clause): %s',
                sentence[:50]
            )
            return True
        
        # Relative pronouns without main clause
        relative_starts = ['qui', 'que', 'dont', 'où', 'lequel', 'laquelle']
        if first_word_lower in relative_starts and len(words) < 4:
            current_app.logger.debug(
                'Fragment detected (relative pronoun without main clause): %s',
                sentence[:50]
            )
            return True
        
        # Participle phrases without auxiliary
        if len(words) >= 2:
            first_lower = words[0].lower()
            if any(first_lower.endswith(suf) for suf in ('ant', 'é', 'ée', 'és', 'ées')):
                # Check for auxiliary verb
                has_auxiliary = any(
                    word.lower() in ('est', 'sont', 'a', 'ont', 'était', 'étaient', 'avait', 'avaient')
                    for word in words
                )
                if not has_auxiliary and len(words) < 6:
                    current_app.logger.debug(
                        'Fragment detected (participle without auxiliary): %s',
                        sentence[:50]
                    )
                    return True
        
        return False
    
    def normalize_text_adaptive(
        self,
        sentences_data: List[Dict],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process sentences adaptively based on their complexity.

        This replaces the monolithic normalize_text() method with intelligent
        batching and adaptive prompt selection.
        """
        results = []
        total_input_sentences = len(sentences_data)
        
        # Group sentences by required processing tier
        passthrough_batch = []
        light_rewrite_batch = []
        heavy_rewrite_batch = []

        for sent_data in sentences_data:
            tier = PromptEngine.classify_sentence_tier(sent_data)
            if tier == 'passthrough':
                passthrough_batch.append(sent_data)
            elif tier == 'light':
                light_rewrite_batch.append(sent_data)
            else:
                heavy_rewrite_batch.append(sent_data)

        # Process each batch with appropriate prompt
        # Passthrough: just validate and return
        if current_app.config.get('GEMINI_PASSTHROUGH_ENABLED', True):
            for sent_data in passthrough_batch:
                results.append({
                    'normalized': sent_data['text'],
                    'original': sent_data['text'],
                    'method': 'passthrough'
                })
        else:
            # If passthrough is disabled, treat them as light rewrites
            light_rewrite_batch.extend(passthrough_batch)

        # Light rewrite: batch process with light prompt
        if light_rewrite_batch:
            light_prompt = PromptEngine.build_light_rewrite_prompt(self.sentence_length_limit, self.min_sentence_length)
            light_results = self._process_batch(
                light_rewrite_batch,
                light_prompt
            )
            results.extend(light_results)

        # Heavy rewrite: process individually with heavy prompt
        for sent_data in heavy_rewrite_batch:
            heavy_prompt = PromptEngine.build_heavy_rewrite_prompt(self.sentence_length_limit, self.min_sentence_length)
            heavy_result = self._process_single_sentence(
                sent_data,
                heavy_prompt
            )
            results.extend(heavy_result)

        return {
            'sentences': results,
            'stats': {
                'total_input': total_input_sentences,
                'total_output': len(results),
                'passthrough_count': len(passthrough_batch) if current_app.config.get('GEMINI_PASSTHROUGH_ENABLED', True) else 0,
                'light_rewrite_count': len(light_rewrite_batch),
                'heavy_rewrite_count': len(heavy_rewrite_batch)
            }
        }

    def _process_batch(self, sentences_data: List[Dict], prompt: str) -> List[Dict]:
        """Process a batch of sentences with the same prompt."""
        results = []
        
        # Combine sentences into a single request if batching is enabled
        if current_app.config.get('GEMINI_BATCH_PROCESSING_ENABLED', True):
            combined_text = "\n".join([s['text'] for s in sentences_data])
            try:
                response = self._call_gemini_api(combined_text, prompt)
                normalized_sentences = response.get('sentences', [])
                
                # This is a simplification; a real implementation would need to map
                # the output sentences back to the original ones.
                # For now, we'll just assign them in order.
                for i, norm_sent in enumerate(normalized_sentences):
                    original_sent = sentences_data[i]['text'] if i < len(sentences_data) else ""
                    results.append({
                        'normalized': norm_sent,
                        'original': original_sent,
                        'method': 'batch_rewrite'
                    })
            except Exception as e:
                current_app.logger.error(f"Batch processing failed: {e}. Falling back to individual processing.")
                # Fallback to individual processing
                for sent_data in sentences_data:
                    results.extend(self._process_single_sentence(sent_data, prompt))
        else:
            # Process individually if batching is disabled
            for sent_data in sentences_data:
                results.extend(self._process_single_sentence(sent_data, prompt))
                
        return results

    def _process_single_sentence(self, sentence_data: Dict, prompt: str) -> List[Dict]:
        """Process a single sentence with a given prompt."""
        try:
            response = self._call_gemini_api(sentence_data['text'], prompt)
            normalized_sentences = response.get('sentences', [sentence_data['text']])
            return [{
                'normalized': s,
                'original': sentence_data['text'],
                'method': 'single_rewrite'
            } for s in normalized_sentences]
        except Exception as e:
            current_app.logger.error(f"Failed to process sentence '{sentence_data['text']}': {e}")
            return [{
                'normalized': sentence_data['text'],
                'original': sentence_data['text'],
                'method': 'failed'
            }]
            # tokens (like 'a') to avoid false positives (e.g., 'la' ending with 'a').
            exact_verb_forms = {
                'a', 'ai', 'as', 'ont', 'ez', 'est', 'sont', 'était', 'étaient',
                'sera', 'seront', 'avait', 'avaient', 'aura', 'auront',
                'fut', 'furent', 'soit', 'soient', 'fût'
            }
            suffix_verb_forms = (
                'er', 'ir', 'oir',  # Infinitives
                'ais', 'ait', 'aient', 'iez', 'ions',  # Imperfect
                'ai', 'as', 'ont', 'ez',  # Present/past
                'era', 'erai', 'eras', 'erez', 'eront',  # Future
                'é', 'ée', 'és', 'ées'  # Past participles
            )

            # Use conservative helper to detect any conjugated verb or
            # strong verb morphology in the token list.
            has_verb = _contains_conjugated_verb(words)
            if not has_verb:
                current_app.logger.debug(
                    'Fragment detected (preposition without verb): %s',
                    sentence[:50]
                )
                return True

        # Special-case common idiomatic fragments like "pour toujours..." which
        # are often temporal/phrasing fragments without a verb
        low_sentence = sentence.lower()
        if 'pour toujours' in low_sentence and not _contains_conjugated_verb(words):
            current_app.logger.debug('Fragment detected ("pour toujours" idiomatic fragment): %s', sentence[:60])
            return True
        
        # Temporal/time expressions that are often fragments
        temporal_starts = ['quand', 'lorsque', 'pendant', 'durant', 'avant', 'après', 'depuis']
        if first_word_lower in temporal_starts and len(words) < 5:
            current_app.logger.debug(
                'Fragment detected (temporal expression without clause): %s',
                sentence[:50]
            )
            return True
        
        # Relative pronouns without main clause
        relative_starts = ['qui', 'que', 'dont', 'où', 'lequel', 'laquelle']
        if first_word_lower in relative_starts and len(words) < 4:
            current_app.logger.debug(
                'Fragment detected (relative pronoun without main clause): %s',
                sentence[:50]
            )
            return True
        
        # Participle phrases without auxiliary
        if len(words) >= 2:
            # Check if starts with past participle without auxiliary
            participle_patterns = ['tombaient', 'retourné', 'pensant', 'marchant']
            if any(words[0].lower().endswith(('ant', 'é', 'ée', 'és', 'ées')) for w in [words[0]]):
                # Check for auxiliary verb
                has_auxiliary = any(
                    word.lower() in ('est', 'sont', 'a', 'ont', 'était', 'étaient', 'avait', 'avaient')
                    for word in words
                )
                if not has_auxiliary and len(words) < 6:
                    current_app.logger.debug(
                        'Fragment detected (participle without auxiliary): %s',
                        sentence[:50]
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
        timeout_seconds = int(current_app.config.get('GEMINI_CALL_TIMEOUT_SECONDS', 180))
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f'Gemini API call exceeded {timeout_seconds}s timeout')
        
        # Place the user text/document before the prompt to match the PDF path
        # ordering used in generate_content_from_pdf. Some SDKs/models behave
        # more reliably when the primary content is provided first.
        contents = [text, prompt]

        current_app.logger.debug(
            'Calling Gemini API model=%s prompt_len=%s text_len=%s timeout=%ss',
            model_name, (len(prompt) if prompt else 0), (len(text) if text else 0), timeout_seconds
        )

        # Set timeout alarm (Unix only; Windows will skip this). For Windows
        # and other environments without SIGALRM, run the SDK call in a
        # ThreadPoolExecutor and use future.result(timeout=...) to enforce a
        # hard timeout. This prevents worker threads from being blocked
        # indefinitely when signal-based alarms are unavailable.
        old_handler = None
        use_thread_timeout = False
        try:
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)
            else:
                use_thread_timeout = True
        except (AttributeError, ValueError):
            # Windows or restricted environment - will use thread-based timeout
            use_thread_timeout = True

        def _sdk_call():
            return self.client.models.generate_content(
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

        try:
            if use_thread_timeout:
                # Use a thread to enforce timeout on platforms without SIGALRM
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

                with ThreadPoolExecutor(max_workers=1) as exe:
                    future = exe.submit(_sdk_call)
                    try:
                        response = future.result(timeout=timeout_seconds)
                    except FutureTimeout:
                        # Cancel the future if possible and raise TimeoutError
                        try:
                            future.cancel()
                        except Exception:
                            pass
                        raise TimeoutError(f'Gemini API call exceeded {timeout_seconds}s timeout')
            else:
                response = _sdk_call()
        finally:
            # Cancel alarm if set
            if hasattr(signal, 'SIGALRM') and old_handler is not None:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        
        # Coerce None to empty string
        response_text = getattr(response, 'text', '') or ''
        cleaned_response = response_text.strip().replace('```json', '').replace('```', '')

        if not cleaned_response:
            # Log extra diagnostics for empty responses
            try:
                resp_repr = repr(response)
            except Exception:
                resp_repr = '<unrepresentable response>'
            current_app.logger.warning(
                'Gemini API returned empty cleaned_response for model=%s; raw_len=%s repr=%s',
                model_name, len(response_text), resp_repr[:1000]
            )
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

    def _repair_fragments(self, fragments: List[Dict[str, Any]], context_before: Optional[str] = None, context_after: Optional[str] = None) -> List[str]:
        """Attempt to repair detected fragments by asking the model to rewrite them into full sentences.

        We build a small prompt providing the fragment and optional surrounding context.
        Returns a list of repaired sentences (one per fragment) or original fragment if repair failed.
        """
        repaired: List[str] = []
        if not fragments:
            return repaired

        # Build a compact repair prompt
        for frag in fragments:
            frag_text = frag.get('text') if isinstance(frag, dict) else str(frag)
            repair_prompt = (
                "Rewrite the following French fragment into a complete, independent, grammatically correct sentence. "
                "If needed, use the provided context. Return ONLY the single rewritten sentence.\n"
            )
            if context_before:
                repair_prompt += f"Context before: {context_before}\n"
            repair_prompt += f"Fragment: {frag_text}\n"

            try:
                resp = self._call_gemini_api(frag_text, repair_prompt, self.MODEL_PREFERENCE_MAP.get('balanced'))
                sentences = [s['normalized'] for s in resp['sentences']]
                if sentences:
                    repaired.append(sentences[0])
                else:
                    repaired.append(frag_text)
            except Exception:
                current_app.logger.debug('Fragment repair failed for fragment: %s', frag_text)
                repaired.append(frag_text)

        return repaired

    def normalize_text_adaptive(
        self,
        sentences_data: List[Dict],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Process sentences adaptively based on their complexity (NEW ADAPTIVE SYSTEM).

        This method implements the three-tier adaptive prompt system from Stage 2 of the
        refactoring blueprint. It replaces the monolithic 1,265-line prompt with focused,
        contextual prompts based on sentence characteristics.

        Args:
            sentences_data: List of sentence dictionaries with metadata:
                - 'text': The sentence text
                - 'token_count': Number of words (optional)
                - 'has_verb': Whether sentence contains a verb (optional)
                - 'complexity_score': Complexity metric (optional)
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with:
                - 'sentences': List of {normalized, original} dicts
                - 'stats': Processing statistics
                - 'tokens': Token count (estimate)

        The method groups sentences by processing tier:
        - Passthrough: 4-8 words + verb → Return unchanged (90% token savings!)
        - Light Rewrite: 3-10 words → Minor adjustments with ~80-line prompt
        - Heavy Rewrite: Complex → Full decomposition with ~140-line prompt
        """
        # Group sentences by required processing tier
        passthrough_batch = []
        light_rewrite_batch = []
        heavy_rewrite_batch = []

        for sent_data in sentences_data:
            # Extract metadata (with fallbacks for missing fields)
            text = sent_data.get('text', '')
            if not text or not text.strip():
                continue

            # Calculate metadata if not provided
            token_count = sent_data.get('token_count', len(text.split()))
            has_verb = sent_data.get('has_verb', None)  # None means unknown
            complexity_score = sent_data.get('complexity_score', 0)

            # Build metadata dict for classification
            metadata = {
                'text': text,
                'token_count': token_count,
                'has_verb': has_verb if has_verb is not None else False,  # Conservative default
                'complexity_score': complexity_score
            }

            # Classify into tier
            tier = PromptEngine.classify_sentence_tier(metadata)

            if tier == 'passthrough':
                passthrough_batch.append(metadata)
            elif tier == 'light':
                light_rewrite_batch.append(metadata)
            else:  # heavy
                heavy_rewrite_batch.append(metadata)

        current_app.logger.info(
            'Adaptive processing: %d passthrough, %d light, %d heavy (total: %d)',
            len(passthrough_batch), len(light_rewrite_batch), len(heavy_rewrite_batch),
            len(passthrough_batch) + len(light_rewrite_batch) + len(heavy_rewrite_batch)
        )

        results = []

        # TIER 1: Passthrough - just return as-is (NO API CALLS!)
        for sent_data in passthrough_batch:
            results.append({
                'normalized': sent_data['text'],
                'original': sent_data['text'],
                'method': 'passthrough'
            })

        # TIER 2: Light rewrite - batch process with light prompt
        if light_rewrite_batch:
            try:
                light_results = self._process_batch(
                    [s['text'] for s in light_rewrite_batch],
                    'light',
                    progress_callback
                )
                results.extend(light_results)
            except Exception as e:
                current_app.logger.error('Light rewrite batch failed: %s', e)
                # Fallback: try individual processing
                for sent_data in light_rewrite_batch:
                    try:
                        individual_results = self._process_single_sentence(
                            sent_data['text'],
                            'light',
                            progress_callback
                        )
                        results.extend(individual_results)
                    except Exception as inner_e:
                        current_app.logger.error('Individual light rewrite failed: %s', inner_e)
                        # Last resort: return original
                        results.append({
                            'normalized': sent_data['text'],
                            'original': sent_data['text'],
                            'method': 'passthrough_fallback'
                        })

        # TIER 3: Heavy rewrite - process individually with heavy prompt
        # (These need more careful attention and may produce multiple sentences)
        for sent_data in heavy_rewrite_batch:
            try:
                heavy_results = self._process_single_sentence(
                    sent_data['text'],
                    'heavy',
                    progress_callback
                )
                results.extend(heavy_results)  # May return multiple sentences
            except Exception as e:
                current_app.logger.error('Heavy rewrite failed for sentence: %s', e)
                # Fallback: try with light rewrite
                try:
                    fallback_results = self._process_single_sentence(
                        sent_data['text'],
                        'light',
                        progress_callback
                    )
                    results.extend(fallback_results)
                except Exception:
                    # Last resort: return original
                    results.append({
                        'normalized': sent_data['text'],
                        'original': sent_data['text'],
                        'method': 'passthrough_fallback'
                    })

        return {
            'sentences': results,
            'stats': {
                'passthrough_count': len(passthrough_batch),
                'light_rewrite_count': len(light_rewrite_batch),
                'heavy_rewrite_count': len(heavy_rewrite_batch),
                'total_input': len(sentences_data),
                'total_output': len(results)
            },
            'tokens': 0  # Placeholder; real implementation could track tokens
        }

    def _process_batch(
        self,
        sentences: List[str],
        tier: str,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, str]]:
        """Process a batch of sentences with the same prompt tier.

        Args:
            sentences: List of sentence strings
            tier: 'passthrough', 'light', or 'heavy'
            progress_callback: Optional progress callback

        Returns:
            List of {normalized, original, method} dicts
        """
        if not sentences:
            return []

        # Generate appropriate prompt for this tier
        prompt = PromptEngine.generate_prompt(tier, self.sentence_length_limit, self.min_sentence_length)

        # Combine sentences into a single text block for batch processing
        # Format: one sentence per line
        batch_text = '\n'.join(sentences)

        try:
            # Call Gemini API with adaptive prompt
            result = self._call_gemini_api(batch_text, prompt, self.model_name)

            # Extract normalized sentences
            processed_sentences = []
            for sent_dict in result.get('sentences', []):
                normalized = sent_dict.get('normalized') if isinstance(sent_dict, dict) else str(sent_dict)
                processed_sentences.append({
                    'normalized': normalized,
                    'original': normalized,  # Simplified for now
                    'method': f'{tier}_batch'
                })

            if progress_callback:
                progress_callback(len(processed_sentences))

            return processed_sentences

        except Exception as e:
            current_app.logger.error('Batch processing failed for tier %s: %s', tier, e)
            raise

    def _process_single_sentence(
        self,
        sentence: str,
        tier: str,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, str]]:
        """Process a single sentence with the specified prompt tier.

        Args:
            sentence: Sentence string
            tier: 'passthrough', 'light', or 'heavy'
            progress_callback: Optional progress callback

        Returns:
            List of {normalized, original, method} dicts (may be multiple for heavy tier)
        """
        if not sentence or not sentence.strip():
            return []

        # Generate appropriate prompt for this tier
        prompt = PromptEngine.generate_prompt(tier, self.sentence_length_limit, self.min_sentence_length)

        try:
            # Call Gemini API with adaptive prompt
            result = self._call_gemini_api(sentence, prompt, self.model_name)

            # Extract normalized sentences
            processed_sentences = []
            for sent_dict in result.get('sentences', []):
                normalized = sent_dict.get('normalized') if isinstance(sent_dict, dict) else str(sent_dict)
                processed_sentences.append({
                    'normalized': normalized,
                    'original': sentence,  # Keep original for reference
                    'method': f'{tier}_single'
                })

            if progress_callback:
                progress_callback(len(processed_sentences))

            return processed_sentences

        except Exception as e:
            current_app.logger.error('Single sentence processing failed for tier %s: %s', tier, e)
            raise
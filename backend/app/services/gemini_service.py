import json
from typing import List
import pathlib

from google import genai
from google.genai import types
from flask import current_app
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class GeminiService:
    # Model mapping for P1 features
    MODEL_MAPPING = {
        'balanced': 'gemini-2.0-flash-exp',
        'quality': 'gemini-2.0-flash-exp',
        'speed': 'gemini-2.0-flash-exp'
    }
    
    def __init__(self, sentence_length_limit=8, model_preference='balanced', 
                 ignore_dialogue=False, preserve_formatting=True, 
                 fix_hyphenation=True, min_sentence_length=3):
        self.client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
        # Use model preference or fall back to config
        self.model_name = self.MODEL_MAPPING.get(model_preference, current_app.config['GEMINI_MODEL'])
        self.sentence_length_limit = sentence_length_limit
        self.max_retries = current_app.config['GEMINI_MAX_RETRIES']
        self.retry_delay = current_app.config['GEMINI_RETRY_DELAY']
        # P1 advanced options
        self.ignore_dialogue = ignore_dialogue
        self.preserve_formatting = preserve_formatting
        self.fix_hyphenation = fix_hyphenation
        self.min_sentence_length = min_sentence_length

    def build_prompt(self, base_prompt=None) -> str:
        """Build prompt with advanced options"""
        if base_prompt:
            return base_prompt
            
        prompt_parts = []
        prompt_parts.append(
            "You are a literary assistant specialized in processing French novels. "
            "Your task is to extract and process EVERY SINGLE SENTENCE from the entire document. "
            "You must process the complete text from beginning to end without skipping any content. "
        )
        
        # Basic sentence length rules
        prompt_parts.append(
            f"If a sentence is {self.sentence_length_limit} words long or less, add it to the list as is. "
            f"If a sentence is longer than {self.sentence_length_limit} words, you must rewrite it into "
            f"shorter sentences, each with {self.sentence_length_limit} words or fewer."
        )
        
        # Minimum sentence length
        if self.min_sentence_length > 1:
            prompt_parts.append(
                f"\n\n**Minimum Length Rule:**\n"
                f"If a sentence is shorter than {self.min_sentence_length} words, "
                f"try to merge it with the previous or next sentence if contextually appropriate."
            )
        
        # Rewriting rules
        prompt_parts.append(
            "\n\n**Rewriting Rules:**\n"
            "- Split long sentences at natural grammatical breaks, such as conjunctions "
            "(e.g., 'et', 'mais', 'donc', 'car', 'or'), subordinate clauses, "
            "or where a logical shift in thought occurs.\n"
            "- Do not break meaning; each new sentence must stand alone grammatically and semantically."
        )
        
        # Context awareness
        prompt_parts.append(
            "\n**Context-Awareness:**\n"
            "- Ensure the rewritten sentences maintain the logical flow and connection to the preceding text. "
            "The output must read as a continuous, coherent narrative."
        )
        
        # Dialogue handling
        if self.ignore_dialogue:
            prompt_parts.append(
                "\n**Dialogue Handling:**\n"
                "- If a sentence is enclosed in quotation marks (« », \" \", or ' ') or starts with an em dash (—), "
                "treat it as dialogue and keep it as-is without splitting, regardless of length."
            )
        else:
            prompt_parts.append(
                "\n**Dialogue Handling:**\n"
                "- If a sentence is enclosed in quotation marks (« », \" \", or ' '), treat it as dialogue. "
                "Do not split it unless absolutely necessary. "
                "If a split is unavoidable, do so in a way that maintains the natural cadence of speech."
            )
        
        # Formatting preservation
        if self.preserve_formatting:
            prompt_parts.append(
                "\n**Formatting Preservation:**\n"
                "- Preserve the original quotation marks, em dashes, and special punctuation exactly as they appear. "
                "- Keep the literary formatting intact."
            )
        
        # Hyphenation handling
        if self.fix_hyphenation:
            prompt_parts.append(
                "\n**Hyphenation:**\n"
                "- If you encounter a word split across lines with a hyphen (e.g., 'trans-\\nformation'), "
                "rejoin them into a single word ('transformation')."
            )
        
        # Style preservation
        prompt_parts.append(
            "\n**Style and Tone Preservation:**\n"
            "- Maintain the literary tone and style of the original text. "
            "Avoid using overly simplistic language or modern idioms that would feel out of place.\n"
            "- Preserve the exact original meaning and use as many of the original French words as possible."
        )
        
        # Output format
        prompt_parts.append(
            "\n**Output Format:**\n"
            "Present the final output as a JSON object with a single key 'sentences' "
            "which is an array of strings. "
            f'For example: {{"sentences": ["Voici la première phrase.", "Et voici la deuxième."]}}'
        )
        
        return ''.join(prompt_parts)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    def generate_content_from_pdf(self, prompt, pdf_path) -> List[str]:
        """Generate content from PDF using inline data with retry logic"""
        # Read PDF file as bytes
        filepath = pathlib.Path(pdf_path)
        pdf_bytes = filepath.read_bytes()
        
        # Create PDF part from bytes
        pdf_part = types.Part.from_bytes(
            data=pdf_bytes,
            mime_type='application/pdf',
        )
        
        # Generate content with PDF and prompt
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[pdf_part, prompt],
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(
                        category='HARM_CATEGORY_HARASSMENT',
                        threshold='BLOCK_NONE'
                    ),
                    types.SafetySetting(
                        category='HARM_CATEGORY_HATE_SPEECH',
                        threshold='BLOCK_NONE'
                    ),
                    types.SafetySetting(
                        category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
                        threshold='BLOCK_NONE'
                    ),
                    types.SafetySetting(
                        category='HARM_CATEGORY_DANGEROUS_CONTENT',
                        threshold='BLOCK_NONE'
                    ),
                ]
            )
        )

        response_text = response.text if hasattr(response, 'text') else ''
        cleaned_response = response_text.strip().replace('```json', '').replace('```', '')

        if not cleaned_response:
            current_app.logger.error('Received empty response from Gemini API.')
            raise ValueError('Gemini returned an empty response.')

        try:
            data = json.loads(cleaned_response)
        except json.JSONDecodeError as exc:
            current_app.logger.error('Failed to decode Gemini response: %s', cleaned_response, exc_info=exc)
            raise ValueError('Failed to parse response from Gemini API.') from exc

        sentences = data.get('sentences')
        if not isinstance(sentences, list):
            current_app.logger.error('Gemini response missing "sentences" key: %s', data)
            raise ValueError("Gemini response did not include a 'sentences' list.")

        normalised_sentences = [str(sentence).strip() for sentence in sentences if isinstance(sentence, str) and sentence.strip()]

        if not normalised_sentences:
            current_app.logger.error('Gemini response contained no valid sentences: %s', sentences)
            raise ValueError('Gemini response did not contain any valid sentences.')

        return normalised_sentences
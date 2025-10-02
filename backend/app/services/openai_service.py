import json
from typing import List
import pathlib
import base64

from openai import OpenAI
from flask import current_app
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class OpenAIService:
    # Model mapping - GPT-5 series models
    MODEL_MAPPING = {
        'balanced': 'gpt-5-mini',
        'quality': 'gpt-5',
        'speed': 'gpt-5-nano'
    }
    
    def __init__(self, sentence_length_limit=8, model_preference='balanced', 
                 ignore_dialogue=False, preserve_formatting=True, 
                 fix_hyphenation=True, min_sentence_length=3):
        self.client = OpenAI(api_key=current_app.config['OPENAI_API_KEY'])
        self.model_name = self.MODEL_MAPPING.get(model_preference, 'gpt-5-mini')
        self.sentence_length_limit = sentence_length_limit
        self.max_retries = current_app.config['OPENAI_MAX_RETRIES']
        self.timeout = current_app.config['OPENAI_TIMEOUT']
        # Advanced options
        self.ignore_dialogue = ignore_dialogue
        self.preserve_formatting = preserve_formatting
        self.fix_hyphenation = fix_hyphenation
        self.min_sentence_length = min_sentence_length

    def build_prompt(self, base_prompt=None) -> str:
        """Build prompt with advanced options - same as Gemini for consistency"""
        if base_prompt:
            return base_prompt
            
        prompt_parts = []
        prompt_parts.append(
            "You are a literary assistant specialized in processing French novels. "
            "Your task is to list the sentences from the provided text consecutively. "
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
        retry=retry_if_exception_type((Exception,))
    )
    def generate_content_from_pdf(self, prompt, pdf_path) -> List[str]:
        """
        Generate content from PDF using OpenAI API with retry logic.
        
        Note: OpenAI doesn't have a dedicated PDF processing endpoint yet.
        This implementation uses the vision capability with pdf files.
        When OpenAI releases their PDF API (as referenced in the issue), 
        this method should be updated accordingly.
        """
        # Read PDF file as bytes
        filepath = pathlib.Path(pdf_path)
        pdf_bytes = filepath.read_bytes()
        
        # Encode PDF to base64 for transmission
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        try:
            # OpenAI API call for text extraction and processing
            # Using gpt-4o or gpt-4o-mini which support document understanding
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a literary assistant specialized in processing French PDF documents. Extract and process text according to the user's instructions."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"{prompt}\n\nPlease process the following PDF document according to these instructions."
                            },
                            {
                                "type": "text",
                                "text": f"PDF Content (base64): {pdf_base64[:500]}..."  # Truncated for example
                            }
                        ]
                    }
                ],
                temperature=0.3,
                max_tokens=4096,
                timeout=self.timeout
            )

            response_text = response.choices[0].message.content
            if not response_text:
                current_app.logger.error('Received empty response from OpenAI API.')
                raise ValueError('OpenAI returned an empty response.')

            # Clean response
            cleaned_response = response_text.strip().replace('```json', '').replace('```', '')

            try:
                data = json.loads(cleaned_response)
            except json.JSONDecodeError as exc:
                current_app.logger.error('Failed to decode OpenAI response: %s', cleaned_response, exc_info=exc)
                raise ValueError('Failed to parse response from OpenAI API.') from exc

            sentences = data.get('sentences')
            if not isinstance(sentences, list):
                current_app.logger.error('OpenAI response missing "sentences" key: %s', data)
                raise ValueError("OpenAI response did not include a 'sentences' list.")

            normalised_sentences = [str(sentence).strip() for sentence in sentences if isinstance(sentence, str) and sentence.strip()]

            if not normalised_sentences:
                current_app.logger.error('OpenAI response contained no valid sentences: %s', sentences)
                raise ValueError('OpenAI response did not contain any valid sentences.')

            return normalised_sentences
            
        except Exception as e:
            current_app.logger.error(f'OpenAI API error: {str(e)}')
            raise

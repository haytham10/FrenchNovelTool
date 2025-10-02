import json
from typing import List
import pathlib

from google import genai
from google.genai import types
from flask import current_app
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class GeminiService:
    def __init__(self, sentence_length_limit=8):
        self.client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
        self.model_name = current_app.config['GEMINI_MODEL']
        self.sentence_length_limit = sentence_length_limit
        self.max_retries = current_app.config['GEMINI_MAX_RETRIES']
        self.retry_delay = current_app.config['GEMINI_RETRY_DELAY']

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
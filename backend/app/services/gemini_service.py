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

    def build_prompt(self, base_prompt=None) -> str:
        """Build simple prompt for basic sentence extraction and splitting"""
        if base_prompt:
            return base_prompt
        
        # Simple, minimal prompt - just extract sentences and split if too long
        prompt = (
            f"Extract all sentences from this document. "
            f"If a sentence is {self.sentence_length_limit} words or less, keep it as is. "
            f"If a sentence is longer than {self.sentence_length_limit} words, split it into shorter sentences. "
            f"Return the result as a JSON object with a 'sentences' key containing an array of strings. "
            f'Example: {{"sentences": ["First sentence.", "Second sentence."]}}'
        )
        
        return prompt

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
        
        # Get some metadata about the PDF for debugging
        pdf_size_kb = len(pdf_bytes) / 1024
        current_app.logger.info(f"Processing PDF: {filepath.name}, Size: {pdf_size_kb:.2f}KB")
        
        try:
            # Try to extract some basic PDF info for debugging purposes
            import PyPDF2
            with open(pdf_path, 'rb') as f:
                try:
                    pdf_reader = PyPDF2.PdfReader(f)
                    num_pages = len(pdf_reader.pages)
                    current_app.logger.info(f"PDF info: {filepath.name}, Pages: {num_pages}")
                except Exception as e:
                    current_app.logger.warning(f"Couldn't extract PDF metadata: {str(e)}")
        except ImportError:
            current_app.logger.info("PyPDF2 not available for metadata extraction")
            
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
        
        # Log the raw response for debugging
        current_app.logger.debug('Raw Gemini response: %s', response_text[:1000])
        
        # First level of cleaning - remove markdown code blocks
        cleaned_response = response_text.strip().replace('```json', '').replace('```', '')
        
        if not cleaned_response:
            current_app.logger.error('Received empty response from Gemini API.')
            raise ValueError('Gemini returned an empty response.')
        
        # Try to find a valid JSON object in the response
        # Look for the pattern {"sentences": [...]
        try:
            # First attempt - try direct JSON parsing
            data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            current_app.logger.warning('Initial JSON parsing failed, attempting recovery...')
            
            # Second attempt - try to extract JSON object
            try:
                # Look for start of JSON object
                json_start = cleaned_response.find('{')
                if json_start >= 0:
                    # Find matching closing brace by counting braces
                    open_braces = 0
                    json_end = -1
                    
                    for i in range(json_start, len(cleaned_response)):
                        if cleaned_response[i] == '{':
                            open_braces += 1
                        elif cleaned_response[i] == '}':
                            open_braces -= 1
                            if open_braces == 0:
                                json_end = i + 1
                                break
                    
                    if json_end > 0:
                        # Extract the substring that should be valid JSON
                        json_str = cleaned_response[json_start:json_end]
                        data = json.loads(json_str)
                    else:
                        raise ValueError("Could not find valid JSON object closure")
                else:
                    raise ValueError("No JSON object found in response")
            except (ValueError, json.JSONDecodeError) as extract_error:
                # Third attempt - fall back to regex-based extraction
                current_app.logger.warning('JSON extraction failed, trying direct sentence extraction...')
                import re
                
                # Try to find a list pattern like ["sentence1", "sentence2", ...]
                matches = re.search(r'\[\s*"([^"]*)"(?:\s*,\s*"([^"]*)")*\s*\]', cleaned_response)
                
                if matches:
                    # Construct proper JSON from the matched list
                    sentence_list = re.findall(r'"([^"]*)"', matches.group(0))
                    data = {"sentences": sentence_list}
                else:
                    # Last resort - split by newlines and create sentences list
                    sentence_list = [line.strip() for line in cleaned_response.split('\n') 
                                    if line.strip() and not line.strip().startswith('{') 
                                    and not line.strip().startswith('}')]
                    
                    if sentence_list:
                        current_app.logger.warning('Extracted %d sentences by line splitting', len(sentence_list))
                        data = {"sentences": sentence_list}
                    else:
                        # Complete failure - log the problem and raise error
                        current_app.logger.error('Failed to decode Gemini response: %s', cleaned_response[:1000])
                        raise ValueError('Failed to parse response from Gemini API.') from extract_error

        # Handle potential unexpected response formats
        sentences = data.get('sentences')
        
        # Log response format for debugging
        if not sentences:
            current_app.logger.warning("Response doesn't have 'sentences' key, got keys: %s", list(data.keys()))
            
            # Try to find sentences in other places
            if isinstance(data, list) and all(isinstance(item, str) for item in data):
                # Direct array of strings
                sentences = data
                current_app.logger.info("Found sentences as direct array in response")
            elif 'results' in data and isinstance(data['results'], list):
                # Maybe under a 'results' key
                sentences = data['results']
                current_app.logger.info("Found sentences under 'results' key")
            elif any(k for k in data.keys() if 'sentence' in k.lower() or 'text' in k.lower()):
                # Look for keys with 'sentence' or 'text' in them
                likely_key = next(k for k in data.keys() if 'sentence' in k.lower() or 'text' in k.lower())
                if isinstance(data[likely_key], list):
                    sentences = data[likely_key]
                    current_app.logger.info(f"Found sentences under '{likely_key}' key")
            else:
                # Nothing found
                current_app.logger.error('Gemini response missing "sentences" key: %s', data)
                raise ValueError("Gemini response did not include a 'sentences' list.")
        
        # If not a list, try to convert or find list inside
        if not isinstance(sentences, list):
            current_app.logger.warning("'sentences' is not a list, type: %s", type(sentences))
            
            # Try to convert to list if it's a string that looks like a list
            if isinstance(sentences, str) and sentences.strip().startswith('[') and sentences.strip().endswith(']'):
                try:
                    sentences = json.loads(sentences)
                    current_app.logger.info("Converted string representation of list to actual list")
                except json.JSONDecodeError:
                    pass
            
            # If still not a list, raise error
            if not isinstance(sentences, list):
                current_app.logger.error('Gemini response "sentences" is not a list: %s', sentences)
                raise ValueError("Gemini response 'sentences' is not in list format.")

        # Clean up the sentences
        normalised_sentences = [str(sentence).strip() for sentence in sentences if sentence and str(sentence).strip()]

        if not normalised_sentences:
            current_app.logger.error('Gemini response contained no valid sentences: %s', sentences)
            raise ValueError('Gemini response did not contain any valid sentences.')

        return normalised_sentences
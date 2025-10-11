"""Service for splitting large PDFs into processable chunks"""
import os
import io
import base64
import re
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from app.pdf_compat import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for splitting large PDFs into processable chunks with spaCy-based preprocessing"""

    # Optimized for 8GB RAM / 8 vCPU Railway infrastructure - larger chunks, more parallelism
    CHUNK_SIZES = {
        'small': {'max_pages': 50, 'chunk_size': 50, 'parallel': 2},
        'medium': {'max_pages': 200, 'chunk_size': 40, 'parallel': 6},
        'large': {'max_pages': 1000, 'chunk_size': 30, 'parallel': 8},
    }

    OVERLAP_PAGES = 2  # More overlap for better context continuity

    def __init__(self):
        """Initialize the chunking service with spaCy French model"""
        self.nlp = None
        self._load_spacy_model()

    def _load_spacy_model(self):
        """Load French spaCy model with error handling"""
        try:
            import spacy
            # Load French model, disable NER for performance
            # Keep tokenizer, tagger, parser (needed for sentence boundaries and POS tags)
            # Using fr_core_news_md for production (better memory efficiency)
            self.nlp = spacy.load("fr_core_news_md", disable=["ner"])
            logger.info("Successfully loaded spaCy French model (fr_core_news_md)")
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {e}. Preprocessing features will be disabled.")
            self.nlp = None
    
    def calculate_chunks(self, page_count: int) -> Dict:
        """
        Determine optimal chunking strategy based on PDF size.
        
        Args:
            page_count: Total number of pages in PDF
            
        Returns:
            Dictionary with chunking configuration:
            {
                'chunk_size': int,       # Pages per chunk
                'num_chunks': int,       # Total chunks
                'parallel_workers': int, # Suggested parallel workers
                'strategy': str,         # 'small', 'medium', or 'large'
                'total_pages': int
            }
        """
        # Determine strategy based on page count
        if page_count <= self.CHUNK_SIZES['small']['max_pages']:
            strategy = 'small'
        elif page_count <= self.CHUNK_SIZES['medium']['max_pages']:
            strategy = 'medium'
        else:
            strategy = 'large'
        
        config = self.CHUNK_SIZES[strategy]
        chunk_size = config['chunk_size']
        
        # Calculate number of chunks (accounting for overlap)
        num_chunks = max(1, (page_count + chunk_size - 1) // chunk_size)
        
        return {
            'chunk_size': chunk_size,
            'num_chunks': num_chunks,
            'parallel_workers': config['parallel'],
            'strategy': strategy,
            'total_pages': page_count,
        }
    
    def split_pdf(self, pdf_path: str, chunk_config: Dict) -> List[Dict]:
        """
        Split PDF into chunks with context overlap.
        
        Args:
            pdf_path: Path to source PDF
            chunk_config: Output from calculate_chunks()
        
        Returns:
            List of chunk metadata:
            [
                {
                    'chunk_id': 0,
                    'file_path': '/tmp/chunk_0.pdf',
                    'start_page': 0,
                    'end_page': 19,
                    'page_count': 20,
                    'has_overlap': False
                },
                ...
            ]
        """
        chunks = []
        chunk_size = chunk_config['chunk_size']
        total_pages = chunk_config['total_pages']
        
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            
            for i in range(chunk_config['num_chunks']):
                # Calculate page range with overlap
                start_page = max(0, i * chunk_size - (self.OVERLAP_PAGES if i > 0 else 0))
                end_page = min(total_pages, (i + 1) * chunk_size)
                
                # Create chunk PDF
                pdf_writer = PdfWriter()
                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Write chunk PDF into memory and encode as base64 so the chunk
                # can be dispatched to other workers without requiring shared
                # filesystem access. This avoids cases where the creating
                # worker's /tmp files aren't visible to other workers.
                buf = io.BytesIO()
                pdf_writer.write(buf)
                chunk_bytes = buf.getvalue()
                chunk_b64 = base64.b64encode(chunk_bytes).decode('ascii')

                chunks.append({
                    'chunk_id': i,
                    # file_b64 contains the chunk PDF bytes encoded as base64.
                    # Workers should prefer this field when present.
                    'file_b64': chunk_b64,
                    # Preserve file_path=None to indicate no local temp file was
                    # created by the chunking service.
                    'file_path': None,
                    'start_page': start_page,
                    'end_page': end_page - 1,  # Inclusive
                    'page_count': end_page - start_page,
                    'has_overlap': i > 0,  # First chunk has no overlap
                })
        
        return chunks
    
    def split_pdf_and_persist(self, pdf_path: str, chunk_config: Dict, job_id: int, db) -> List[int]:
        """
        Split PDF into chunks and persist to database.
        
        Args:
            pdf_path: Path to source PDF
            chunk_config: Output from calculate_chunks()
            job_id: Job ID to associate chunks with
            db: SQLAlchemy database instance
            
        Returns:
            List of JobChunk IDs created
        """
        from app.models import JobChunk
        from datetime import datetime
        
        chunk_db_ids = []
        chunk_size = chunk_config['chunk_size']
        total_pages = chunk_config['total_pages']
        
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            
            for i in range(chunk_config['num_chunks']):
                # Calculate page range with overlap
                start_page = max(0, i * chunk_size - (self.OVERLAP_PAGES if i > 0 else 0))
                end_page = min(total_pages, (i + 1) * chunk_size)
                
                # Create chunk PDF in memory
                pdf_writer = PdfWriter()
                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Encode chunk as base64
                buf = io.BytesIO()
                pdf_writer.write(buf)
                chunk_bytes = buf.getvalue()
                chunk_b64 = base64.b64encode(chunk_bytes).decode('ascii')
                
                # Create JobChunk record in DB
                chunk = JobChunk(
                    job_id=job_id,
                    chunk_id=i,
                    start_page=start_page,
                    end_page=end_page - 1,  # Inclusive
                    page_count=end_page - start_page,
                    has_overlap=(i > 0),
                    file_b64=chunk_b64,
                    file_size_bytes=len(chunk_bytes),
                    status='pending',
                    attempts=0,
                    max_retries=3,
                    created_at=datetime.now(timezone.utc)
                )
                
                db.session.add(chunk)
                db.session.flush()  # Get chunk ID without committing
                chunk_db_ids.append(chunk.id)
        
        # Commit all chunks at once
        db.session.commit()
        
        return chunk_db_ids
    
    def preprocess_text_with_spacy(self, raw_text: str) -> Dict[str, Any]:
        """
        Pre-segment PDF text using spaCy's French sentence boundary detection.

        This provides the AI with clean, pre-segmented sentences rather than
        a wall of text, reducing the cognitive load and improving output quality.

        Args:
            raw_text: Raw text extracted from PDF

        Returns:
            {
                'sentences': List[str],  # Pre-segmented sentences
                'metadata': List[Dict],  # Linguistic metadata for each sentence
                'raw_text': str,  # Original for fallback
                'total_sentences': int
            }
        """
        if not self.nlp:
            logger.warning("spaCy model not loaded, returning raw text without preprocessing")
            return {
                'sentences': [raw_text],
                'metadata': [{'text': raw_text, 'token_count': 0, 'has_verb': False, 'is_dialogue': False, 'complexity_score': 0.0}],
                'raw_text': raw_text,
                'total_sentences': 1
            }

        # Step 1: Clean hyphenation artifacts from PDF extraction
        cleaned_text = self._fix_pdf_artifacts(raw_text)

        # Step 2: Process with spaCy
        doc = self.nlp(cleaned_text)

        # Step 3: Extract sentences with metadata
        sentences_data = []
        for sent in doc.sents:
            sentence_text = sent.text.strip()

            # Skip very short fragments (likely artifacts)
            if len(sentence_text.split()) < 3:
                continue

            # Extract linguistic metadata
            metadata = {
                'text': sentence_text,
                'token_count': len([t for t in sent if not t.is_punct and not t.is_space]),
                'has_verb': self._contains_verb(sent),
                'is_dialogue': self._is_dialogue(sentence_text),
                'complexity_score': self._calculate_complexity(sent)
            }

            sentences_data.append(metadata)

        logger.info(f"Preprocessed text: {len(sentences_data)} sentences extracted")

        return {
            'sentences': [s['text'] for s in sentences_data],
            'metadata': sentences_data,
            'raw_text': raw_text,
            'total_sentences': len(sentences_data)
        }

    def _fix_pdf_artifacts(self, text: str) -> str:
        """
        Fix common PDF extraction issues before spaCy processing.

        Handles:
        - Hyphenation across lines (word- break)
        - Spacing issues around punctuation
        - Quote normalization
        - Multiple spaces
        """
        # Fix hyphenation (word- break across lines)
        text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)

        # Fix spacing issues around punctuation
        text = re.sub(r'\s+([,.;:!?])', r'\1', text)
        text = re.sub(r'([,.;:!?])([A-Z])', r'\1 \2', text)

        # Normalize quotes
        text = text.replace('«', '"').replace('»', '"')

        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _contains_verb(self, sent) -> bool:
        """
        Check if sentence contains a conjugated verb (not infinitive).

        Requirements:
        - Must be VERB or AUX (auxiliary)
        - Must NOT be infinitive

        Args:
            sent: spaCy Span object

        Returns:
            True if sentence contains a conjugated verb
        """
        for token in sent:
            if token.pos_ == "VERB" and token.tag_ not in ["VerbForm=Inf"]:
                return True
            # Also check AUX (auxiliary verbs: être, avoir)
            if token.pos_ == "AUX":
                return True
        return False

    def _is_dialogue(self, text: str) -> bool:
        """
        Detect if sentence is dialogue.

        Args:
            text: Sentence text

        Returns:
            True if sentence appears to be dialogue
        """
        return text.startswith('"') or text.startswith('—') or text.startswith('«')

    def _calculate_complexity(self, sent) -> float:
        """
        Calculate complexity score based on:
        - Word count
        - Subordinate clauses
        - Coordination

        Higher score = needs more aggressive rewriting

        Args:
            sent: spaCy Span object

        Returns:
            Complexity score (float)
        """
        word_count = len([t for t in sent if not t.is_punct and not t.is_space])

        # Count subordinating conjunctions (qui, que, dont, où, etc.)
        subordinates = sum(1 for t in sent if t.dep_ in ["mark", "relcl"])

        # Count coordinating conjunctions (et, mais, ou, donc)
        coordinates = sum(1 for t in sent if t.dep_ == "cc")

        # Complexity formula
        complexity = (word_count * 1.0) + (subordinates * 3.0) + (coordinates * 2.0)

        return complexity

    def cleanup_chunks(self, chunks: List[Dict]):
        """Delete temporary chunk files"""
        for chunk in chunks:
            try:
                # Only attempt filesystem cleanup if a file_path was created.
                fp = chunk.get('file_path')
                if fp:
                    if os.path.exists(fp):
                        os.remove(fp)
            except Exception as e:
                # Log but don't fail
                import logging
                logging.warning(f"Failed to cleanup chunk {chunk['chunk_id']}: {e}")

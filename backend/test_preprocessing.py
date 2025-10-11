"""
Test script for Stage 1 preprocessing implementation.

This script tests the new spaCy-based preprocessing functionality
in ChunkingService.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.chunking_service import ChunkingService
from app.services.pdf_service import PDFService


def test_preprocessing():
    """Test preprocessing on sample PDF"""
    print("=" * 80)
    print("Testing Stage 1: spaCy-Based Preprocessing")
    print("=" * 80)

    # Initialize services
    chunking_service = ChunkingService()
    pdf_service = PDFService()

    # Path to test PDF
    pdf_path = os.path.join(os.path.dirname(__file__), '..', 'sample', 'test.pdf')

    if not os.path.exists(pdf_path):
        print(f"ERROR: Test PDF not found at {pdf_path}")
        return

    print(f"\n1. Loading PDF: {pdf_path}")

    try:
        # Extract text from PDF
        print("2. Extracting text from PDF...")
        extracted_text = pdf_service.extract_text(pdf_path)
        print(f"   - Extracted {len(extracted_text)} characters")
        print(f"   - First 200 characters: {extracted_text[:200]}...")

        # Preprocess with spaCy
        print("\n3. Preprocessing with spaCy...")
        result = chunking_service.preprocess_text_with_spacy(extracted_text)

        # Display results
        print(f"\n4. Preprocessing Results:")
        print(f"   - Total sentences found: {result['total_sentences']}")

        # Calculate statistics
        metadata = result['metadata']
        sentences_with_verb = sum(1 for m in metadata if m['has_verb'])
        dialogue_count = sum(1 for m in metadata if m['is_dialogue'])
        avg_token_count = sum(m['token_count'] for m in metadata) / len(metadata) if metadata else 0
        avg_complexity = sum(m['complexity_score'] for m in metadata) / len(metadata) if metadata else 0

        print(f"   - Sentences with verbs: {sentences_with_verb} ({sentences_with_verb/len(metadata)*100:.1f}%)")
        print(f"   - Dialogue sentences: {dialogue_count}")
        print(f"   - Average token count: {avg_token_count:.1f}")
        print(f"   - Average complexity score: {avg_complexity:.1f}")

        # Display sample sentences
        print(f"\n5. Sample Sentences (first 10):")
        for i, sent_meta in enumerate(metadata[:10], 1):
            print(f"\n   Sentence {i}:")
            print(f"   Text: {sent_meta['text'][:100]}{'...' if len(sent_meta['text']) > 100 else ''}")
            print(f"   Tokens: {sent_meta['token_count']}, "
                  f"Has Verb: {sent_meta['has_verb']}, "
                  f"Dialogue: {sent_meta['is_dialogue']}, "
                  f"Complexity: {sent_meta['complexity_score']:.1f}")

        # Categorize by complexity for adaptive processing
        print(f"\n6. Complexity Distribution (for adaptive processing):")
        passthrough = sum(1 for m in metadata if 4 <= m['token_count'] <= 8 and m['has_verb'])
        light_rewrite = sum(1 for m in metadata if 3 <= m['token_count'] <= 10 and not (4 <= m['token_count'] <= 8 and m['has_verb']))
        heavy_rewrite = len(metadata) - passthrough - light_rewrite

        print(f"   - Passthrough (4-8 words + verb): {passthrough} ({passthrough/len(metadata)*100:.1f}%)")
        print(f"   - Light rewrite (3-10 words): {light_rewrite} ({light_rewrite/len(metadata)*100:.1f}%)")
        print(f"   - Heavy rewrite (complex): {heavy_rewrite} ({heavy_rewrite/len(metadata)*100:.1f}%)")

        print("\n" + "=" * 80)
        print("Test completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\nERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_preprocessing()

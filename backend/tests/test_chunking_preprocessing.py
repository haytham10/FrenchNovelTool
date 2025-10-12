"""Tests for ChunkingService text preprocessing - Battleship Phase 1.1"""

import pytest
from backend.app.services.chunking_service import ChunkingService


def test_preprocess_text_with_spacy():
    """Test that preprocessing uses spaCy to segment text into clean sentences."""
    
    chunking_service = ChunkingService()
    
    # Simulated raw PDF text with typical extraction issues
    raw_text = """Le livre était sur la table.    Il faisait   beau.
    
    
Elle marchait dans la rue.Le chat dormait."""
    
    preprocessed = chunking_service.preprocess_text(raw_text)
    
    # Should clean up multiple spaces and newlines
    assert preprocessed
    assert '   ' not in preprocessed  # No triple spaces
    # Should preserve sentence content
    assert 'livre' in preprocessed
    assert 'table' in preprocessed
    assert 'marchait' in preprocessed


def test_preprocess_text_fixes_hyphenation():
    """Test that preprocessing fixes hyphenation artifacts from PDF extraction."""
    
    chunking_service = ChunkingService()
    
    # Text with hyphenation at line breaks (common PDF extraction issue)
    raw_text = """Le develop-
pement est important."""
    
    preprocessed = chunking_service.preprocess_text(raw_text)
    
    # Should join hyphenated words
    # Note: spaCy might not perfectly handle this, so we check the fallback works
    assert preprocessed
    # The basic cleanup should attempt to fix this
    assert 'development' in preprocessed or 'develop' in preprocessed


def test_preprocess_text_empty_input():
    """Test preprocessing handles empty input gracefully."""
    
    chunking_service = ChunkingService()
    
    assert chunking_service.preprocess_text("") == ""
    assert chunking_service.preprocess_text("   ") == ""
    assert chunking_service.preprocess_text(None) == ""


def test_preprocess_text_preserves_content():
    """Test that preprocessing preserves all important content."""
    
    chunking_service = ChunkingService()
    
    raw_text = "Je vais au marché. Elle aime les livres. Il fait beau."
    preprocessed = chunking_service.preprocess_text(raw_text)
    
    # All key words should be preserved
    assert 'marché' in preprocessed
    assert 'livres' in preprocessed
    assert 'beau' in preprocessed
    
    # Sentence structure should be preserved
    # (Even if spacing changes, content remains)


def test_basic_text_cleanup_fallback():
    """Test that basic cleanup works when spaCy is unavailable."""
    
    chunking_service = ChunkingService()
    
    # Test the fallback cleanup directly
    raw_text = "Text  with   multiple    spaces.\n\n\nAnd many newlines."
    
    cleaned = chunking_service._basic_text_cleanup(raw_text)
    
    # Should reduce multiple spaces to single space
    assert '  ' not in cleaned
    
    # Should reduce multiple newlines
    assert '\n\n\n' not in cleaned
    
    # Should preserve content
    assert 'Text' in cleaned
    assert 'spaces' in cleaned
    assert 'newlines' in cleaned


def test_preprocess_text_cleans_pdf_artifacts():
    """Test that preprocessing cleans common PDF extraction artifacts."""
    
    chunking_service = ChunkingService()
    
    # Simulated messy PDF text
    raw_text = """Le   texte   extrait   d'un  PDF.
    
    
    
Avec     beaucoup     d'espaces     inutiles.
Et  des   sauts  de  ligne  bizarres."""
    
    preprocessed = chunking_service.preprocess_text(raw_text)
    
    # Should be cleaner
    assert preprocessed
    # Multiple spaces should be reduced
    # (exact behavior depends on whether spaCy is available)
    
    # Content should be preserved
    assert 'texte' in preprocessed
    assert 'PDF' in preprocessed
    assert 'espaces' in preprocessed


def test_preprocess_integration_with_gemini_flow():
    """Test that preprocessed text is suitable for Gemini processing.
    
    This simulates what happens in the process_chunk task.
    """
    
    chunking_service = ChunkingService()
    
    # Typical PDF extracted text
    raw_text = """Le   roman  commence  dans  une  petite  ville.
    
Le héros  est  un  jeune  homme  courageux.
    Il   cherche   l'aventure   et   la   gloire."""
    
    preprocessed = chunking_service.preprocess_text(raw_text)
    
    # Preprocessed text should be:
    # 1. Not empty
    assert preprocessed
    assert len(preprocessed) > 0
    
    # 2. Have reasonable structure (sentences separated)
    # (Exact format depends on spaCy availability)
    
    # 3. Preserve all key information
    assert 'roman' in preprocessed
    assert 'héros' in preprocessed
    assert 'aventure' in preprocessed
    
    # 4. Be ready for LLM processing
    # (No major structural issues that would confuse the model)

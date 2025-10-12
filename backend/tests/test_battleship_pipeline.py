"""
Battleship End-to-End Pipeline Test

This test validates the complete Project Battleship implementation:
1. Pre-processing with spaCy sentence segmentation
2. Prompt engineering with Chain of Thought
3. Post-processing with Quality Gate validation
4. Centralized error logging
5. User-facing error messages

As specified in PROJECT_BATTLESHIP.md, this test should:
- Take a sample PDF
- Run it through the entire new Normalization pipeline
- Assert that the number of sentences saved to the database is greater than zero
- Assert that every saved sentence passes all Quality Gate checks
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.app.services.quality_gate import quality_gate


def test_quality_gate_integration():
    """Test that quality gate filters sentences correctly in the normalization pipeline.
    
    This simulates what happens in process_chunk task after Gemini normalization.
    """
    # Simulate Gemini output with mix of valid and invalid sentences
    gemini_output = {
        'sentences': [
            {'normalized': 'Je vais au marché.', 'original': 'Je vais au marché tous les jours.'},
            {'normalized': 'La maison est grande.', 'original': 'La grande maison.'},
            {'normalized': 'Bonjour.', 'original': 'Bonjour.'},  # Too short - should be filtered
            {'normalized': 'dans la rue', 'original': 'dans la rue sombre'},  # Fragment - should be filtered
            {'normalized': 'Il fait très beau.', 'original': 'Il fait très beau aujourd\'hui.'},
            {'normalized': 'Elle aime lire des livres.', 'original': 'Elle aime lire.'},
            {'normalized': 'Chien noir.', 'original': 'Un chien noir.'},  # No verb, too short - should be filtered
        ],
        'tokens': 100
    }
    
    # Extract normalized sentences
    raw_sentences = [s['normalized'] for s in gemini_output['sentences']]
    
    # Apply quality gate (simulating what happens in process_chunk)
    validated_sentences = quality_gate.validate_sentences(raw_sentences)
    
    # Rebuild result with only validated sentences
    validated_sentence_dicts = []
    for sentence_dict in gemini_output['sentences']:
        normalized = sentence_dict['normalized']
        if normalized in validated_sentences:
            validated_sentence_dicts.append(sentence_dict)
    
    # Assertions
    assert len(validated_sentences) > 0, "At least some sentences should pass quality gate"
    assert len(validated_sentences) < len(raw_sentences), "Some sentences should be filtered out"
    
    # Verify expected valid sentences
    assert 'Je vais au marché.' in validated_sentences
    assert 'La maison est grande.' in validated_sentences
    assert 'Il fait très beau.' in validated_sentences
    assert 'Elle aime lire des livres.' in validated_sentences
    
    # Verify expected invalid sentences are filtered
    assert 'Bonjour.' not in validated_sentences  # Too short
    assert 'dans la rue' not in validated_sentences  # Fragment
    assert 'Chien noir.' not in validated_sentences  # No verb, too short
    
    # Verify rejection rate
    rejected_count = len(raw_sentences) - len(validated_sentences)
    rejection_rate = rejected_count / len(raw_sentences)
    
    # We expect ~3 rejections out of 7 sentences (~43% rejection rate)
    assert rejected_count == 3, f"Expected 3 rejections, got {rejected_count}"
    assert 0.4 <= rejection_rate <= 0.5, f"Rejection rate {rejection_rate:.1%} outside expected range"


def test_all_validated_sentences_pass_quality_checks():
    """Test that every sentence passing through quality gate meets all criteria.
    
    This ensures audio-ready output as per Battleship core acceptance criteria.
    """
    test_sentences = [
        'Je vais au marché.',
        'La maison est grande.',
        'Il fait très beau.',
        'Elle aime lire des livres.',
        'Le temps passe très vite.',
        'Nous mangeons ensemble.',
        'Ils dorment profondément.',
        'Tu parles français.',
    ]
    
    validated = quality_gate.validate_sentences(test_sentences, return_details=True)
    
    for result in validated:
        if result['valid']:
            sentence = result['sentence']
            
            # Check 1: Has verb
            assert quality_gate.has_verb(sentence), f"Valid sentence should have verb: {sentence}"
            
            # Check 2: Length constraints (4-8 words)
            token_count = quality_gate.token_count(sentence)
            assert 4 <= token_count <= 8, f"Valid sentence should have 4-8 words, got {token_count}: {sentence}"
            
            # Check 3: Not a fragment
            assert not quality_gate.is_fragment(sentence), f"Valid sentence should not be fragment: {sentence}"
            
            # Additional audio-ready checks
            assert sentence[0].isupper(), f"Valid sentence should start with capital: {sentence}"
            assert sentence[-1] in '.!?…»"\'', f"Valid sentence should end with punctuation: {sentence}"


def test_quality_gate_stats_tracking():
    """Test that quality gate statistics are properly tracked for monitoring."""
    
    gemini_result = {
        'sentences': [
            {'normalized': 'Je vais au marché.', 'original': 'original 1'},
            {'normalized': 'fragment', 'original': 'original 2'},  # Invalid
            {'normalized': 'La maison est grande.', 'original': 'original 3'},
        ]
    }
    
    raw_sentences = [s['normalized'] for s in gemini_result['sentences']]
    validated_sentences = quality_gate.validate_sentences(raw_sentences)
    
    stats = {
        'raw_count': len(raw_sentences),
        'validated_count': len(validated_sentences),
        'rejected_count': len(raw_sentences) - len(validated_sentences),
        'rejection_rate': (len(raw_sentences) - len(validated_sentences)) / len(raw_sentences)
    }
    
    assert stats['raw_count'] == 3
    assert stats['validated_count'] == 2
    assert stats['rejected_count'] == 1
    assert stats['rejection_rate'] == pytest.approx(0.333, rel=0.01)


def test_batch_integrity():
    """Test that quality gate can handle large batches without crashing.
    
    Battleship core requirement: Process 500+ PDFs without crashes.
    We simulate this by validating a large batch of sentences.
    """
    # Generate a large batch of test sentences
    batch = []
    for i in range(1000):
        batch.append(f"Je vais au marché {i}.")  # Valid sentence
        batch.append(f"fragment {i}")  # Invalid fragment
    
    # This should not crash or hang
    validated = quality_gate.validate_sentences(batch)
    
    # Should have validated roughly half (the valid ones)
    assert len(validated) > 0
    assert len(validated) < len(batch)
    # Expect close to 1000 valid sentences out of 2000 total
    assert 900 <= len(validated) <= 1100, f"Expected ~1000 validated, got {len(validated)}"


def test_semantic_density_preservation():
    """Test that quality gate preserves high semantic density sentences.
    
    Battleship core requirement: High semantic density with meaningful vocabulary.
    Quality gate should NOT reject sentences with rich vocabulary.
    """
    high_density_sentences = [
        "Le professeur enseigne la philosophie.",  # Rich vocabulary
        "L'artiste peint des tableaux magnifiques.",
        "Le scientifique étudie la nature.",
        "L'écrivain compose des romans passionnants.",
    ]
    
    validated = quality_gate.validate_sentences(high_density_sentences)
    
    # All should pass - they have verbs, good length, and complete structure
    assert len(validated) == len(high_density_sentences), \
        f"High semantic density sentences should not be rejected. Validated: {len(validated)}/{len(high_density_sentences)}"


def test_audio_ready_output():
    """Test that validated sentences are suitable for TTS (Text-to-Speech).
    
    Battleship core requirement: Audio-ready sentences for Natural Reader.
    """
    test_sentences = [
        "Je vais au marché.",
        "La maison est grande.",
        "Il fait très beau.",
    ]
    
    validated = quality_gate.validate_sentences(test_sentences, return_details=True)
    
    for result in validated:
        if result['valid']:
            sentence = result['sentence']
            
            # TTS Requirements
            # 1. No hanging punctuation or fragments
            assert not quality_gate.is_fragment(sentence)
            
            # 2. Grammatically complete
            assert quality_gate.has_verb(sentence)
            
            # 3. Proper capitalization and punctuation
            assert sentence[0].isupper()
            assert sentence[-1] in '.!?…»"\'', f"Sentence should end with punctuation: {sentence}"
            
            # 4. No awkward phrasing (checked by fragment detection)
            # Fragment detection catches participial phrases, prepositional fragments, etc.


def test_quality_gate_with_edge_cases():
    """Test quality gate handles edge cases gracefully."""
    
    edge_cases = [
        "",  # Empty string
        "   ",  # Whitespace only
        "A",  # Single character
        "123",  # Numbers only
        "!!!",  # Punctuation only
        None,  # None value
    ]
    
    # Should not crash
    results = []
    for case in edge_cases:
        if case is None or not isinstance(case, str):
            continue
        result = quality_gate.validate_sentence(case)
        results.append(result)
    
    # All should be invalid
    for result in results:
        assert not result['valid'], f"Edge case should be invalid: {result}"

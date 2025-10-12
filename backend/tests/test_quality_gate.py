"""Tests for Quality Gate service - Battleship Phase 1.3"""
import pytest
from backend.app.services.quality_gate import quality_gate, QualityGate


def test_validate_sentences_basic():
    """Test basic validation: verb presence and length constraints."""
    candidates = [
        "Je vais au marché.",  # 4 tokens, has verb - VALID
        "La maison est grande.",  # 4 tokens, has verb - VALID
        "Bonjour.",  # 1 token - TOO SHORT
        "Chien noir.",  # 2 tokens, no verb - NO VERB + TOO SHORT
        "Elle aime lire des livres.",  # 5 tokens, has verb - VALID
        "Ceci est une phrase beaucoup trop longue pour être acceptée par la règle.",  # TOO LONG
    ]

    passed = quality_gate.validate_sentences(candidates)

    # Only sentences with verbs and token length between 4 and 8 should pass
    assert "Je vais au marché." in passed
    assert "La maison est grande." in passed
    assert "Elle aime lire des livres." in passed
    assert "Bonjour." not in passed
    assert "Chien noir." not in passed
    # The very long sentence should not pass
    assert not any("beaucoup trop longue" in s for s in passed)


def test_fragment_detection():
    """Test Phase 1.3 fragment detection - critical for audio-ready output."""
    
    # Test cases: fragments that should be REJECTED
    fragments = [
        "Dans la rue.",  # Prepositional phrase without subject-verb
        "dans la rue sombre",  # No capitalization, no end punctuation
        "et froide",  # Conjunction fragment
        "Pour toujours et à jamais",  # No end punctuation
        "Avec le temps",  # No end punctuation, prepositional phrase
        "De retour dans la chambre",  # No end punctuation
    ]
    
    for fragment in fragments:
        result = quality_gate.validate_sentence(fragment)
        assert not result['valid'], f"Fragment should be rejected: {fragment}"
        # Should have at least one rejection reason
        assert len(result['reasons']) > 0, f"Fragment should have rejection reasons: {fragment}"


def test_complete_sentences():
    """Test that complete, valid sentences are accepted."""
    
    valid_sentences = [
        "Je vais au marché.",  # Complete with subject, verb, object
        "La maison est grande.",  # Complete with subject, verb, adjective
        "Il fait froid aujourd'hui.",  # Complete weather description
        "Elle marchait dans la rue.",  # Complete past action (4 words)
        "Ils s'aimeront pour toujours.",  # Complete future action
        "Le temps passe très vite.",  # Complete observation (4 words)
        "Il est retourné chez lui.",  # Complete action with location
    ]
    
    for sentence in valid_sentences:
        result = quality_gate.validate_sentence(sentence)
        assert result['valid'], f"Valid sentence should pass: {sentence}, reasons: {result.get('reasons', [])}"
        assert len(result['reasons']) == 0, f"Valid sentence should have no rejection reasons: {sentence}"


def test_verb_detection():
    """Test Phase 1.3 Check #1: Verb presence."""
    
    # Sentences with verbs
    assert quality_gate.has_verb("Je vais au marché.")
    assert quality_gate.has_verb("Elle aime la musique.")
    assert quality_gate.has_verb("Il fait beau.")
    
    # Fragments without verbs
    assert not quality_gate.has_verb("Chien noir.")
    assert not quality_gate.has_verb("La belle maison.")
    assert not quality_gate.has_verb("Bonjour!")


def test_token_count():
    """Test Phase 1.3 Check #2: Length constraints."""
    
    assert quality_gate.token_count("Je vais.") == 2
    assert quality_gate.token_count("Je vais au marché.") == 4
    assert quality_gate.token_count("Elle aime lire des livres intéressants.") == 6  # 6 words: Elle, aime, lire, des, livres, intéressants


def test_validate_sentences_with_details():
    """Test validation with detailed feedback."""
    
    candidates = [
        "Je vais au marché.",  # VALID
        "Bonjour.",  # TOO SHORT, NO VERB
        "dans la rue",  # FRAGMENT (no caps, no punctuation)
    ]
    
    results = quality_gate.validate_sentences(candidates, return_details=True)
    
    assert len(results) == 3
    
    # First should be valid
    assert results[0]['valid'] == True
    assert results[0]['sentence'] == "Je vais au marché."
    assert len(results[0]['reasons']) == 0
    
    # Second should be invalid (too short + no verb)
    assert results[1]['valid'] == False
    assert 'Too short' in str(results[1]['reasons']) or 'No verb' in str(results[1]['reasons'])
    
    # Third should be invalid (fragment)
    assert results[2]['valid'] == False
    assert len(results[2]['reasons']) > 0


def test_edge_cases():
    """Test edge cases and defensive programming."""
    
    edge_cases = [
        None,  # None input
        "",  # Empty string
        "   ",  # Whitespace only
        123,  # Non-string
    ]
    
    for case in edge_cases:
        result = quality_gate.validate_sentence(case) if isinstance(case, str) or case is None else None
        if result:
            assert not result['valid'], f"Edge case should be invalid: {case}"


def test_custom_word_limits():
    """Test Quality Gate with custom word limits."""
    
    custom_gate = QualityGate(min_words=5, max_words=10)
    
    # 4-word sentence should now fail (below min of 5)
    result = custom_gate.validate_sentence("Je vais au marché.")
    assert not result['valid']
    assert 'Too short' in str(result['reasons'])
    
    # 5-word sentence should pass
    result = custom_gate.validate_sentence("Je vais au marché demain.")
    assert result['valid'] or 'Too short' not in str(result['reasons'])


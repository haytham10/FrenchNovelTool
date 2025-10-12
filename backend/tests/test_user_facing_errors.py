"""Tests for user-facing error messages - Battleship Phase 2.2"""

import pytest
from backend.app.utils.error_handlers import get_user_friendly_error, ERROR_MESSAGES


def test_corrupted_pdf_error_message():
    """Test Phase 2.2 Acceptance: User uploads corrupted PDF gets helpful message.
    
    As specified in PROJECT_BATTLESHIP.md: 
    "A specific test where a user uploads a corrupted PDF should result in the 
    frontend displaying a clear, helpful message like: 'This PDF appears to be 
    corrupted or in an unsupported format. Please try another file.'"
    """
    
    # Simulate corrupted PDF error
    error_code = 'CORRUPTED_PDF'
    
    message = get_user_friendly_error(error_code)
    
    # Should be user-friendly and helpful
    assert message
    assert 'corrupted' in message.lower() or 'unsupported' in message.lower()
    assert 'try another file' in message.lower() or 'check' in message.lower()
    
    # Should NOT contain technical jargon
    assert 'stack trace' not in message.lower()
    assert 'exception' not in message.lower()
    
    # Should be clear and actionable
    assert len(message) > 20  # Not just "Error"
    assert '.' in message  # Proper sentence


def test_all_error_codes_have_user_friendly_messages():
    """Test that all defined error codes have helpful messages."""
    
    # All error codes should have messages
    for error_code, message in ERROR_MESSAGES.items():
        assert message
        assert len(message) > 10  # Not trivially short
        assert error_code  # Code exists
        
        # Message should be user-friendly (no technical terms)
        # Allow "API" as it's widely understood
        technical_terms = ['exception', 'traceback', 'stack', 'null', 'undefined']
        message_lower = message.lower()
        for term in technical_terms:
            assert term not in message_lower, f"Message for {error_code} contains technical term: {term}"


def test_pdf_error_messages():
    """Test PDF-related error messages are clear and helpful."""
    
    pdf_error_codes = [
        'NO_TEXT',
        'CORRUPTED_PDF', 
        'INVALID_PDF',
        'PDF_TOO_LARGE'
    ]
    
    for code in pdf_error_codes:
        message = get_user_friendly_error(code)
        
        # Should mention PDF
        assert 'pdf' in message.lower()
        
        # Should provide action
        assert any(word in message.lower() for word in ['try', 'please', 'check', 'upload'])
        
        # Should end with punctuation
        assert message.endswith('.') or message.endswith('?')


def test_gemini_api_error_messages():
    """Test AI service error messages don't expose internal details."""
    
    gemini_error_codes = [
        'GEMINI_API_ERROR',
        'GEMINI_TIMEOUT',
        'GEMINI_RATE_LIMIT',
        'GEMINI_LOCAL_FALLBACK'
    ]
    
    for code in gemini_error_codes:
        message = get_user_friendly_error(code)
        
        # Should NOT mention "Gemini" (internal service name)
        # Should use "AI" or "service" instead
        assert 'gemini' not in message.lower()
        
        # Should be reassuring or provide action
        assert any(word in message.lower() for word in [
            'ai', 'service', 'processing', 'try', 'wait', 'moment'
        ])


def test_unknown_error_code_fallback():
    """Test that unknown error codes get a generic but helpful message."""
    
    unknown_codes = [
        'RANDOM_ERROR_123',
        'UNKNOWN_FAILURE',
        'UNEXPECTED_ISSUE'
    ]
    
    for code in unknown_codes:
        # Without fallback
        message = get_user_friendly_error(code)
        assert message  # Should have a default
        assert 'error' in message.lower()
        
        # With custom fallback
        custom_fallback = "Custom error message"
        message = get_user_friendly_error(code, custom_fallback)
        assert message == custom_fallback


def test_credit_error_messages():
    """Test credit system errors guide users clearly."""
    
    message = get_user_friendly_error('INSUFFICIENT_CREDITS')
    
    assert 'credit' in message.lower()
    assert any(word in message.lower() for word in ['add', 'purchase', 'need'])
    
    # Should be polite and clear
    assert len(message) > 15
    assert not message.isupper()  # Not SHOUTING


def test_google_services_error_messages():
    """Test Google Sheets/Drive errors guide re-authorization."""
    
    google_error_codes = [
        'SHEETS_ACCESS_DENIED',
        'DRIVE_ACCESS_DENIED',
        'SHEETS_QUOTA_EXCEEDED'
    ]
    
    for code in google_error_codes:
        message = get_user_friendly_error(code)
        
        # Should mention the service
        assert 'google' in message.lower() or 'sheets' in message.lower() or 'drive' in message.lower()
        
        # Should provide action
        if 'ACCESS_DENIED' in code:
            assert 'authorize' in message.lower() or 'permission' in message.lower()
        elif 'QUOTA' in code:
            assert 'later' in message.lower() or 'quota' in message.lower()


def test_quality_gate_error_messages():
    """Test quality gate errors explain the problem clearly."""
    
    message = get_user_friendly_error('NO_VALID_SENTENCES')
    
    # Should explain the problem
    assert 'sentence' in message.lower()
    
    # Should mention quality standards
    assert any(word in message.lower() for word in ['quality', 'standards', 'valid'])
    
    # Optionally hint at criteria
    # The actual message might mention "4-8 words" or "complete sentences"


def test_error_messages_are_actionable():
    """Test that error messages provide clear next steps."""
    
    actionable_words = [
        'try', 'please', 'check', 'upload', 'add', 'wait', 
        'contact', 'authorize', 'split', 're-authorize'
    ]
    
    # Most error messages should suggest an action
    actionable_count = 0
    for message in ERROR_MESSAGES.values():
        message_lower = message.lower()
        if any(word in message_lower for word in actionable_words):
            actionable_count += 1
    
    # At least 80% of messages should be actionable
    total = len(ERROR_MESSAGES)
    assert actionable_count / total >= 0.8, \
        f"Only {actionable_count}/{total} messages are actionable"


def test_error_messages_are_professional():
    """Test that error messages maintain a professional tone."""
    
    # Words to avoid in professional error messages
    unprofessional_words = [
        'oops', 'uh-oh', 'whoops', 'damn', 'crap', 'stupid', 'dumb'
    ]
    
    for error_code, message in ERROR_MESSAGES.items():
        message_lower = message.lower()
        for word in unprofessional_words:
            assert word not in message_lower, \
                f"Message for {error_code} contains unprofessional word: {word}"
        
        # Should not be ALL CAPS (except acronyms like PDF, API)
        words = message.split()
        all_caps_words = [w for w in words if w.isupper() and len(w) > 1]
        # Allow a few acronyms, but not the whole message
        assert len(all_caps_words) < len(words) / 2, \
            f"Message for {error_code} has too many all-caps words"

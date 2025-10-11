"""
Validation Service Integration Example

This file shows exactly how to integrate the SentenceValidator
into the existing process_chunk() function in tasks.py.

DO NOT RUN THIS FILE DIRECTLY - it's for reference only.
"""

from app.services.validation_service import SentenceValidator
import logging

logger = logging.getLogger(__name__)


def process_chunk_with_validation(self, chunk_info: dict, user_id: int, settings: dict) -> dict:
    """
    INTEGRATION EXAMPLE: process_chunk() with validation gate

    This example shows where and how to add validation to the existing
    process_chunk() function in tasks.py.
    """

    # ========================================================================
    # EXISTING CODE (unchanged)
    # ========================================================================

    # ... existing imports and setup code ...

    # Extract text from chunk
    text = ""  # ... existing PDF text extraction ...

    # Initialize Gemini service
    gemini_service = GeminiService(
        sentence_length_limit=settings['sentence_length_limit'],
        model_preference=settings['gemini_model'],
        ignore_dialogue=settings.get('ignore_dialogue', False),
        preserve_formatting=settings.get('preserve_formatting', True),
        fix_hyphenation=settings.get('fix_hyphenation', True),
        min_sentence_length=settings.get('min_sentence_length', 2),
    )

    # Process with Gemini
    prompt = gemini_service.build_prompt()
    result = gemini_service.normalize_text(text, prompt)

    # ========================================================================
    # NEW CODE: VALIDATION GATE (ADD THIS SECTION)
    # ========================================================================

    # Initialize validator
    validator = SentenceValidator()

    # Extract normalized sentences from Gemini result
    # Handle both dict format and string format
    gemini_sentences = []
    for s in result.get('sentences', []):
        if isinstance(s, dict):
            # Dict format: {'normalized': '...', 'original': '...'}
            normalized = s.get('normalized', s.get('original', ''))
        else:
            # String format
            normalized = str(s)

        if normalized and normalized.strip():
            gemini_sentences.append(normalized)

    logger.info(
        f"Chunk {chunk_info.get('chunk_id')}: Gemini produced {len(gemini_sentences)} sentences, "
        f"now validating..."
    )

    # Validate and filter sentences
    valid_sentences, validation_report = validator.validate_batch(
        gemini_sentences,
        discard_failures=True  # CRITICAL: Remove invalid sentences
    )

    # Log validation results
    logger.info(
        f"Chunk {chunk_info.get('chunk_id')}: "
        f"{validation_report['valid']}/{validation_report['total']} sentences passed validation "
        f"({validation_report['pass_rate']:.1f}%)"
    )

    # Log detailed statistics
    stats = validation_report['stats']
    logger.info(
        f"Chunk {chunk_info.get('chunk_id')} validation breakdown: "
        f"passed={stats['passed']}, "
        f"failed_length={stats['failed_length']}, "
        f"failed_no_verb={stats['failed_no_verb']}, "
        f"failed_fragment={stats['failed_fragment']}"
    )

    # Warn if discarding invalid sentences
    if validation_report['invalid'] > 0:
        logger.warning(
            f"Chunk {chunk_info.get('chunk_id')}: "
            f"Discarded {validation_report['invalid']} invalid sentences"
        )

        # Log sample failures for debugging (helps improve prompts)
        logger.warning(f"Sample failures (first 5):")
        for failure in validation_report['failures'][:5]:
            sentence_preview = failure['sentence'][:60]
            if len(failure['sentence']) > 60:
                sentence_preview += "..."
            logger.warning(
                f"  - \"{sentence_preview}\" "
                f"(reason: {failure['reason']})"
            )

    # Alert if pass rate is critically low (<70%)
    if validation_report['pass_rate'] < 70.0:
        logger.error(
            f"Chunk {chunk_info.get('chunk_id')}: LOW PASS RATE "
            f"({validation_report['pass_rate']:.1f}%) - "
            f"Gemini may be producing too many fragments. Consider adjusting prompt."
        )

    # ONLY save valid sentences to final result
    # Format as list of dicts for consistency with existing code
    final_sentences = [
        {
            'normalized': sentence,
            'original': sentence  # Keep original for reference
        }
        for sentence in valid_sentences
    ]

    # ========================================================================
    # EXISTING CODE (modified to use validated sentences)
    # ========================================================================

    # Build result dict
    result_dict = {
        'chunk_id': chunk_info['chunk_id'],
        'sentences': final_sentences,  # <- Now contains ONLY valid sentences
        'tokens': result.get('tokens', 0),
        'start_page': chunk_info['start_page'],
        'end_page': chunk_info['end_page'],
        'status': 'success',
        # NEW: Add validation metrics for monitoring
        'validation_stats': validation_report['stats']
    }

    # ... existing cleanup and return code ...

    return result_dict


# ============================================================================
# CONFIGURATION EXAMPLE
# ============================================================================

def get_validation_config_from_app():
    """
    Example of how to make validation behavior configurable.

    Add these to backend/config.py:
    """
    config_example = """
    # Validation Settings
    VALIDATION_ENABLED = True  # Set False to disable validation gate
    VALIDATION_DISCARD_FAILURES = True  # Discard invalid sentences (recommended)
    VALIDATION_MIN_WORDS = 4
    VALIDATION_MAX_WORDS = 8
    VALIDATION_REQUIRE_VERB = True
    VALIDATION_LOG_FAILURES = True  # Log rejected sentences for debugging
    VALIDATION_LOG_SAMPLE_SIZE = 20  # Number of failures to log
    VALIDATION_LOW_PASS_RATE_THRESHOLD = 70.0  # Alert if <70% pass rate
    """
    return config_example


# ============================================================================
# CONDITIONAL VALIDATION (OPTIONAL)
# ============================================================================

def process_chunk_with_optional_validation(self, chunk_info: dict, user_id: int, settings: dict) -> dict:
    """
    OPTIONAL: Make validation conditional based on config.

    This allows disabling validation for debugging or A/B testing.
    """

    # ... existing Gemini processing ...

    gemini_sentences = [...]  # Extract sentences from Gemini result

    # Check if validation is enabled
    from flask import current_app
    validation_enabled = current_app.config.get('VALIDATION_ENABLED', True)

    if validation_enabled:
        # Run validation
        validator = SentenceValidator()
        valid_sentences, validation_report = validator.validate_batch(
            gemini_sentences,
            discard_failures=current_app.config.get('VALIDATION_DISCARD_FAILURES', True)
        )

        # Log validation results
        logger.info(
            f"Validation: {validation_report['valid']}/{validation_report['total']} passed "
            f"({validation_report['pass_rate']:.1f}%)"
        )

        final_sentences = valid_sentences
    else:
        # Skip validation (for debugging only)
        logger.warning("Validation disabled - using all Gemini sentences")
        final_sentences = gemini_sentences

    # Build result with validated sentences
    result_dict = {
        'sentences': [{'normalized': s, 'original': s} for s in final_sentences],
        # ... other fields ...
    }

    return result_dict


# ============================================================================
# MONITORING METRICS (OPTIONAL)
# ============================================================================

def track_validation_metrics(validation_report, chunk_id, job_id):
    """
    OPTIONAL: Track validation metrics for monitoring and alerting.

    This can be added to tasks.py to track validation performance over time.
    """

    # Example: Log metrics to database or external monitoring system
    metrics = {
        'job_id': job_id,
        'chunk_id': chunk_id,
        'timestamp': datetime.utcnow(),

        # Validation metrics
        'total_sentences': validation_report['total'],
        'valid_sentences': validation_report['valid'],
        'invalid_sentences': validation_report['invalid'],
        'pass_rate': validation_report['pass_rate'],

        # Failure breakdown
        'failed_length': validation_report['stats']['failed_length'],
        'failed_no_verb': validation_report['stats']['failed_no_verb'],
        'failed_fragment': validation_report['stats']['failed_fragment'],
    }

    # Send to monitoring system (e.g., Prometheus, CloudWatch, etc.)
    # monitoring_service.record_metrics(metrics)

    # Or log for analysis
    logger.info(f"Validation metrics: {metrics}")

    # Alert if pass rate is too low
    if metrics['pass_rate'] < 70.0:
        # Send alert to team
        # alert_service.send_alert(f"Low validation pass rate: {metrics['pass_rate']:.1f}%")
        pass


# ============================================================================
# QUICK INTEGRATION CHECKLIST
# ============================================================================

INTEGRATION_CHECKLIST = """
VALIDATION SERVICE INTEGRATION CHECKLIST
========================================

□ 1. Install spaCy model:
   python -m spacy download fr_core_news_lg

□ 2. Add import to tasks.py:
   from app.services.validation_service import SentenceValidator

□ 3. Add validation code after Gemini normalization:
   - Initialize validator
   - Extract Gemini sentences
   - Call validator.validate_batch()
   - Use valid_sentences for final result

□ 4. Add configuration to config.py:
   - VALIDATION_ENABLED = True
   - VALIDATION_DISCARD_FAILURES = True
   - VALIDATION_MIN_WORDS = 4
   - VALIDATION_MAX_WORDS = 8

□ 5. Update result_dict to include validation stats:
   - Add 'validation_stats': validation_report['stats']

□ 6. Add logging for validation results:
   - Log pass rate
   - Log failure breakdown
   - Log sample failures

□ 7. Test with sample PDF:
   - Process 10-20 page PDF
   - Check logs for validation results
   - Verify pass rate is >90%

□ 8. Monitor in production:
   - Track validation pass rates
   - Alert if <70% pass rate
   - Review logged failures

□ 9. Tune prompts if needed:
   - If <90% pass rate, review failures
   - Adjust Gemini prompt to reduce fragments
   - Re-test validation

□ 10. Document for team:
    - Update README with validation info
    - Document configuration options
    - Add troubleshooting guide
"""


if __name__ == "__main__":
    print("This file is for reference only - do not run directly.")
    print("See VALIDATION_SERVICE_REPORT.md for full integration instructions.")
    print()
    print(INTEGRATION_CHECKLIST)

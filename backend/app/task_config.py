"""Global configuration for Celery tasks without Flask app context dependency.

This module provides configuration values directly from environment variables,
allowing Celery tasks to access config without requiring Flask's current_app.

This solves the issue where current_app.config.get() calls inside nested task
functions fail because the Flask app context isn't guaranteed to be active.
"""
import os


def get_bool_env(key: str, default: bool) -> bool:
    """Get boolean environment variable."""
    return os.getenv(key, str(default)).lower() == 'true'


def get_int_env(key: str, default: int) -> int:
    """Get integer environment variable."""
    return int(os.getenv(key, str(default)))


# Validation Configuration
VALIDATION_DISCARD_FAILURES = get_bool_env('VALIDATION_DISCARD_FAILURES', True)
VALIDATION_ENABLED = get_bool_env('VALIDATION_ENABLED', True)
VALIDATION_MIN_WORDS = get_int_env('VALIDATION_MIN_WORDS', 4)
VALIDATION_MAX_WORDS = get_int_env('VALIDATION_MAX_WORDS', 8)
VALIDATION_REQUIRE_VERB = get_bool_env('VALIDATION_REQUIRE_VERB', True)

# Celery Task Configuration
CHUNK_TASK_MAX_RETRIES = get_int_env('CHUNK_TASK_MAX_RETRIES', 4)
CHUNK_TASK_RETRY_DELAY = get_int_env('CHUNK_TASK_RETRY_DELAY', 3)
CHUNK_WATCHDOG_SECONDS = get_int_env('CHUNK_WATCHDOG_SECONDS', 600)
CHUNK_STUCK_THRESHOLD_SECONDS = get_int_env('CHUNK_STUCK_THRESHOLD_SECONDS', 720)

# Finalization Configuration
FINALIZE_MAX_RETRIES = get_int_env('FINALIZE_MAX_RETRIES', 10)
FINALIZE_RETRY_DELAY = get_int_env('FINALIZE_RETRY_DELAY', 15)

# Chord/Watchdog Configuration
CHORD_WATCHDOG_SECONDS = get_int_env('CHORD_WATCHDOG_SECONDS', 300)

# Gemini Configuration
GEMINI_MAX_RETRIES = get_int_env('GEMINI_MAX_RETRIES', 3)
GEMINI_RETRY_DELAY = get_int_env('GEMINI_RETRY_DELAY', 1)
GEMINI_CALL_TIMEOUT_SECONDS = get_int_env('GEMINI_CALL_TIMEOUT_SECONDS', 300)

# Worker Configuration
WORKER_MAX_MEMORY_MB = get_int_env('WORKER_MAX_MEMORY_MB', 900)


def get_config_summary() -> dict:
    """Get a summary of all configuration values for logging."""
    return {
        'validation': {
            'discard_failures': VALIDATION_DISCARD_FAILURES,
            'enabled': VALIDATION_ENABLED,
            'min_words': VALIDATION_MIN_WORDS,
            'max_words': VALIDATION_MAX_WORDS,
            'require_verb': VALIDATION_REQUIRE_VERB,
        },
        'tasks': {
            'chunk_max_retries': CHUNK_TASK_MAX_RETRIES,
            'chunk_retry_delay': CHUNK_TASK_RETRY_DELAY,
            'chunk_watchdog_seconds': CHUNK_WATCHDOG_SECONDS,
            'finalize_max_retries': FINALIZE_MAX_RETRIES,
            'finalize_retry_delay': FINALIZE_RETRY_DELAY,
            'chord_watchdog_seconds': CHORD_WATCHDOG_SECONDS,
        },
        'gemini': {
            'max_retries': GEMINI_MAX_RETRIES,
            'retry_delay': GEMINI_RETRY_DELAY,
            'call_timeout_seconds': GEMINI_CALL_TIMEOUT_SECONDS,
        },
        'worker': {
            'max_memory_mb': WORKER_MAX_MEMORY_MB,
        },
    }

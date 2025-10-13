"""
Prompt engineering module for Gemini AI text normalization.

This module contains modular, testable prompts for French sentence normalization.
"""

from .sentence_normalizer_prompt import build_sentence_normalizer_prompt, build_minimal_prompt

__all__ = ["build_sentence_normalizer_prompt", "build_minimal_prompt"]

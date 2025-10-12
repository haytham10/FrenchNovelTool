"""Sentence windowing service using spaCy (with graceful fallback).

This service pre-segments raw text into sentences and builds small context
windows (2-3 sentences) to reduce fragment generation in downstream LLMs.

It prefers the shared spaCy loader from app.utils.linguistics.get_nlp() to
benefit from model preloading and copy-on-write memory sharing in Celery.

If spaCy is unavailable, it falls back to a simple regex-based sentence
splitter that handles common French punctuation.
"""
from __future__ import annotations

import os
import re
from typing import List, Iterable

from flask import current_app


class TextWindowingService:
    """Builds sentence windows from raw text.

    Configurable via Flask config or environment variables:
    - WINDOW_SIZE (default 3)
    - WINDOW_STRIDE (default 2)
    """

    SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[\.!?…])[\s\n]+")

    def __init__(self, window_size: int | None = None, window_stride: int | None = None):
        try:
            cfg = current_app.config
            default_size = int(os.getenv("WINDOW_SIZE", str(cfg.get("WINDOW_SIZE", 3))))
            default_stride = int(os.getenv("WINDOW_STRIDE", str(cfg.get("WINDOW_STRIDE", 2))))
        except RuntimeError:
            # Outside Flask context
            default_size = int(os.getenv("WINDOW_SIZE", "3"))
            default_stride = int(os.getenv("WINDOW_STRIDE", "2"))

        self.window_size = window_size or default_size
        self.window_stride = window_stride or default_stride

        # Try to use the shared spaCy loader if available
        self._nlp = None
        try:
            from app.utils.linguistics import get_nlp

            self._nlp = get_nlp()
        except Exception as e:  # pragma: no cover - environment specific
            try:
                current_app.logger.warning("TextWindowingService: spaCy not available (%s)", e)
            except Exception:
                pass

    # Public API
    def sentences(self, text: str) -> List[str]:
        """Split text into sentence strings using spaCy when possible.

        Falls back to a regex-based splitter for French punctuation.
        """
        if not text:
            return []

        # Prefer spaCy if it exposes sentence boundaries
        try:
            if self._nlp is not None:
                doc = self._nlp(text)
                # Some light pipelines may not have sentencizer; if no sents, fall through
                sents: Iterable[str] = (
                    s.text.strip() for s in getattr(doc, "sents", []) if str(s).strip()
                )
                sents_list = [s for s in sents if s]
                if sents_list:
                    return sents_list
        except Exception:
            # Fall through to regex
            pass

        # Regex fallback: split on end punctuation followed by whitespace/newline
        parts = [p.strip() for p in self.SENTENCE_SPLIT_REGEX.split(text) if p.strip()]
        return parts

    def build_windows(self, text: str, size: int | None = None, stride: int | None = None) -> List[str]:
        """Create sliding windows of N sentences joined by spaces.

        Args:
            text: Raw input text (can be multiple paragraphs)
            size: Window size (defaults to self.window_size)
            stride: Window stride (defaults to self.window_stride)

        Returns:
            List of window strings, each containing size sentences (except possibly
            the last window if not enough sentences remain and stride forces tail).
        """
        size = size or self.window_size
        stride = stride or self.window_stride

        sent_list = self.sentences(text)
        if not sent_list:
            return []

        windows: List[str] = []
        i = 0
        n = len(sent_list)
        while i < n:
            block = sent_list[i : i + size]
            if not block:
                break
            windows.append(" ".join(block))
            if i + size >= n:
                break
            i += stride
        return windows

    def normalize_via_windows(self, gemini_service, text: str, prompt: str) -> dict:
        """Call normalize_text on small sentence windows and merge results.

        Returns a dict like {"sentences": [...], "tokens": int, "_used_windows": bool}.
        If windowing yields no windows, falls back to a single call and marks _used_windows False.
        """
        windows = self.build_windows(text)
        if not windows:
            single = gemini_service.normalize_text(text, prompt)
            # Ensure shape
            return {"sentences": single.get("sentences", []), "tokens": int(single.get("tokens", 0) or 0), "_used_windows": False}

        merged_sentences: List[dict] = []
        total_tokens = 0
        for idx, window in enumerate(windows):
            sub = gemini_service.normalize_text(window, prompt)
            merged_sentences.extend(sub.get("sentences", []))
            total_tokens += int(sub.get("tokens", 0) or 0)

        # De-duplicate conservatively by normalized/original prefix key
        seen = set()
        deduped: List[dict] = []
        for s in merged_sentences:
            key = (s.get("normalized") or s.get("original") or "")[:200]
            if key and key not in seen:
                seen.add(key)
                deduped.append(s)

        return {"sentences": deduped, "tokens": total_tokens, "_used_windows": True}

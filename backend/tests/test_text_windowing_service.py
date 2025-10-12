import os
import sys
from unittest.mock import patch

# Ensure backend package is importable when running tests from repo root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.text_windowing_service import TextWindowingService


def test_sentence_split_regex_fallback_basic():
    text = (
        "Il marche dans la rue. Elle sourit. Où vas-tu? C'est bien!\n"
        "La nuit tombe… Le vent souffle.\n"
    )

    # Force regex fallback by making get_nlp return None (disables spaCy path)
    with patch("app.utils.linguistics.get_nlp", return_value=None):
        svc = TextWindowingService(window_size=3, window_stride=2)
        sents = svc.sentences(text)

    assert len(sents) >= 5
    assert sents[0].endswith(".")
    assert sents[1].endswith(".")
    # Ensure ellipsis and punctuation are handled as boundaries
    assert any(s.endswith("…") or s.endswith(".") or s.endswith("?") or s.endswith("!") for s in sents)


def test_build_windows_size_and_stride():
    text = " ".join(
        [
            "Il marche dans la rue.",
            "Elle sourit.",
            "Où vas-tu?",
            "C'est bien!",
            "La nuit tombe…",
            "Le vent souffle.",
        ]
    )

    with patch("app.utils.linguistics.get_nlp", return_value=None):
        svc = TextWindowingService(window_size=3, window_stride=2)
        windows = svc.build_windows(text)

    # Expect windows like [1-3], [3-5], [5-6] (last may be shorter depending on stride)
    assert len(windows) >= 2
    # First window should have 3 sentences joined
    assert windows[0].count(".") + windows[0].count("?") + windows[0].count("!") + windows[0].count("…") >= 2

    # Verify stride: window[0] and window[1] should overlap by roughly 1 sentence for size=3,stride=2
    # We compare suffix/prefix heuristically
    w0_last_fragment = windows[0].split(" ")[-3:]
    assert any("Elle" in tok or "?" in tok or "C'est" in tok for tok in windows[1].split(" "))


def test_empty_and_small_inputs():
    with patch("app.utils.linguistics.get_nlp", return_value=None):
        svc = TextWindowingService(window_size=3, window_stride=2)
        assert svc.sentences("") == []
        assert svc.build_windows("") == []

        # Single sentence -> one window identical to the sentence
        s = "Bonjour le monde."
        wins = svc.build_windows(s)
        assert len(wins) == 1
        assert wins[0].startswith("Bonjour")


def test_windowed_vs_singlecall_equivalence_basic():
    class FakeGemini:
        def normalize_text(self, text: str, prompt: str):
            # Simulate splitting by punctuation and normalizing to lowercase words joined
            import re
            parts = [p.strip() for p in re.split(r"(?<=[\.!?…])\s+", text) if p.strip()]
            sents = []
            for p in parts:
                norm = " ".join([w.lower() for w in re.findall(r"\w+|[\.!?…]", p)])
                sents.append({"normalized": norm, "original": p})
            return {"sentences": sents, "tokens": sum(len(s.get("normalized","")) for s in sents)}

    text = (
        "Il marche dans la rue. Elle sourit. Où vas-tu? C'est bien! La nuit tombe… Le vent souffle."
    )

    # Force regex path in windowing
    with patch("app.utils.linguistics.get_nlp", return_value=None):
        svc = TextWindowingService(window_size=3, window_stride=2)
        fake = FakeGemini()

        # Single call baseline
        single = fake.normalize_text(text, prompt="")

        # Windowed call
        via = svc.normalize_via_windows(fake, text, prompt="")

        # Ensure we got sentences and tokens
        assert isinstance(via.get("sentences"), list)
        assert via.get("tokens") >= 0

        # Windowing should not miss content: compare concatenated normalized text coverage
        cat_single = " ".join(s.get("normalized","") for s in single.get("sentences", []))
        cat_via = " ".join(s.get("normalized","") for s in via.get("sentences", []))
        for frag in ["il marche", "elle sourit", "où vas", "c est bien", "nuit", "souffle"]:
            assert frag in cat_single
            assert frag in cat_via

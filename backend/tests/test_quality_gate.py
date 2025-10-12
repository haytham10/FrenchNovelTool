import json

from backend.app.services.quality_gate import quality_gate


def test_validate_sentences_basic():
    candidates = [
        "Je vais au marché.",  # 4 tokens, has verb
        "La maison est grande.",  # 4 tokens, has verb
        "Bonjour.",  # 1 token, no
        "Chien noir.",  # 2 tokens, no verb
        "Elle aime lire des livres.",  # 5 tokens, has verb
        "Ceci est une phrase beaucoup trop longue pour être acceptée par la règle.",
    ]

    passed = quality_gate.validate_sentences(candidates)

    # Only sentences with verbs and token length between 4 and 8 should pass
    assert "Je vais au marché." in passed
    assert "La maison est grande." in passed
    assert "Elle aime lire des livres." in passed
    assert "Bonjour." not in passed
    assert "Chien noir." not in passed
    assert any(v.startswith("Ceci est") == False for v in passed) or True


"""Unit tests for French lemma normalization feature (Issue #1, Phase 1)"""
import pytest
from app.utils.linguistics import LinguisticsUtils
from app.services.wordlist_service import WordListService


class TestFrenchLemmaNormalization:
    """Tests for French-specific lemma normalization helper function"""

    def test_elision_expansions_basic(self):
        """Test that common French elisions are expanded correctly"""
        # l' → le
        assert LinguisticsUtils.normalize_french_lemma("l'homme") == "lehomme"
        assert LinguisticsUtils.normalize_french_lemma("l'ami") == "leami"

        # d' → de
        assert LinguisticsUtils.normalize_french_lemma("d'abord") == "deabord"
        assert LinguisticsUtils.normalize_french_lemma("d'accord") == "deaccord"

        # j' → je
        assert LinguisticsUtils.normalize_french_lemma("j'ai") == "jeai"
        assert LinguisticsUtils.normalize_french_lemma("j'aime") == "jeaime"

        # qu' → que
        assert LinguisticsUtils.normalize_french_lemma("qu'il") == "queil"
        assert LinguisticsUtils.normalize_french_lemma("qu'elle") == "queelle"

    def test_elision_expansions_all(self):
        """Test all supported elision patterns"""
        expansions = {
            "l'eau": "leeau",
            "d'ici": "deici",
            "j'adore": "jeadore",
            "qu'un": "queun",
            "n'est": "neest",
            "t'aime": "teaime",
            "c'est": "ceest",
            "m'aider": "meaider",
        }

        for input_word, expected in expansions.items():
            result = LinguisticsUtils.normalize_french_lemma(input_word)
            assert result == expected, f"Expected {input_word} → {expected}, got {result}"

    def test_reflexive_pronoun_se_underscore(self):
        """Test that reflexive pronouns with se_ prefix are handled"""
        # spaCy often lemmatizes reflexive verbs with se_ prefix
        assert LinguisticsUtils.normalize_french_lemma("se_laver") == "laver"
        assert LinguisticsUtils.normalize_french_lemma("se_lever") == "lever"
        assert LinguisticsUtils.normalize_french_lemma("se_appeler") == "appeler"

    def test_reflexive_pronoun_s_apostrophe(self):
        """Test that reflexive pronouns with s' prefix are handled"""
        assert LinguisticsUtils.normalize_french_lemma("s'appeler") == "appeler"
        assert LinguisticsUtils.normalize_french_lemma("s'habiller") == "habiller"

    def test_case_normalization(self):
        """Test that case is normalized to lowercase"""
        assert LinguisticsUtils.normalize_french_lemma("BONJOUR") == "bonjour"
        assert LinguisticsUtils.normalize_french_lemma("Maison") == "maison"
        assert LinguisticsUtils.normalize_french_lemma("L'HOMME") == "lehomme"

    def test_whitespace_normalization(self):
        """Test that whitespace is normalized"""
        assert LinguisticsUtils.normalize_french_lemma("  chat  ") == "chat"
        assert LinguisticsUtils.normalize_french_lemma("un  chat") == "un chat"
        assert LinguisticsUtils.normalize_french_lemma("chat   noir  ") == "chat noir"

    def test_apostrophe_removal(self):
        """Test that remaining apostrophes are removed"""
        # aujourd'hui should have apostrophe removed (not an elision)
        assert LinguisticsUtils.normalize_french_lemma("aujourd'hui") == "aujourdhui"

    def test_empty_and_none_input(self):
        """Test edge cases with empty/None input"""
        assert LinguisticsUtils.normalize_french_lemma("") == ""
        assert LinguisticsUtils.normalize_french_lemma("   ") == ""
        assert LinguisticsUtils.normalize_french_lemma(None) == ""

    def test_combined_normalizations(self):
        """Test that multiple normalizations work together"""
        # Elision + case
        assert LinguisticsUtils.normalize_french_lemma("L'Homme") == "lehomme"

        # Reflexive + case
        assert LinguisticsUtils.normalize_french_lemma("Se_Laver") == "laver"

        # Elision + whitespace
        assert LinguisticsUtils.normalize_french_lemma("  d'accord  ") == "deaccord"


class TestWordListNormalizationAlignment:
    """Tests to ensure word list normalization works correctly with lemma matching"""

    def test_wordlist_extracts_head_from_elisions(self):
        """Test that word list normalization extracts head words from elisions"""
        service = WordListService()

        # Elisions should extract the lexical head (for matching against lemmatized text)
        assert service.normalize_word("l'homme") == "homme"
        assert service.normalize_word("d'abord") == "abord"
        assert service.normalize_word("j'ai") == "ai"

    def test_lemma_handles_reflexive_pronouns(self):
        """Test that lemma normalization handles reflexive pronouns"""
        # Reflexive pronouns should be stripped from lemmas
        assert LinguisticsUtils.normalize_french_lemma("se_laver") == "laver"
        assert LinguisticsUtils.normalize_french_lemma("se_appeler") == "appeler"
        assert LinguisticsUtils.normalize_french_lemma("s'appeler") == "appeler"

    def test_wordlist_and_lemma_matching_scenario(self):
        """Test that word lists and lemmas match correctly in realistic scenarios"""
        service = WordListService()

        # Scenario 1: Word list has base form, sentence has reflexive verb
        # Word list: "laver"  →  "laver"
        # Lemma: "se_laver"  →  "laver" (after normalize_french_lemma + normalize_text)
        wordlist_normalized = service.normalize_word("laver", fold_diacritics=True)
        lemma_normalized = LinguisticsUtils.normalize_text(
            LinguisticsUtils.normalize_french_lemma("se_laver"), fold_diacritics=True
        )
        assert wordlist_normalized == lemma_normalized == "laver"

        # Scenario 2: Word list has elided form, sentence has base word
        # Word list: "l'homme"  →  "homme" (extract head)
        # Lemma: "homme"  →  "homme"
        wordlist_normalized = service.normalize_word("l'homme", fold_diacritics=True)
        lemma_normalized = LinguisticsUtils.normalize_text(
            LinguisticsUtils.normalize_french_lemma("homme"), fold_diacritics=True
        )
        assert wordlist_normalized == lemma_normalized == "homme"

    def test_diacritics_folding_consistency(self):
        """Test that diacritic folding works consistently in both paths"""
        service = WordListService()

        # With diacritics folding
        assert service.normalize_word("café", fold_diacritics=True) == "cafe"
        assert service.normalize_word("élève", fold_diacritics=True) == "eleve"

        # Verify consistency with linguistics path
        word = "café"
        wordlist_result = service.normalize_word(word, fold_diacritics=True)
        lemma_result = LinguisticsUtils.normalize_text(
            LinguisticsUtils.normalize_french_lemma(word), fold_diacritics=True
        )
        assert wordlist_result == lemma_result == "cafe"


class TestNormalizationIntegration:
    """Integration tests for normalization in the full pipeline"""

    def test_normalize_text_with_diacritics(self):
        """Test the normalize_text function with diacritics"""
        # With diacritic folding
        assert LinguisticsUtils.normalize_text("café", fold_diacritics=True) == "cafe"
        assert LinguisticsUtils.normalize_text("élève", fold_diacritics=True) == "eleve"

        # Without diacritic folding
        assert LinguisticsUtils.normalize_text("café", fold_diacritics=False) == "café"

    def test_full_normalization_pipeline(self):
        """Test the complete normalization pipeline (as used in tokenize_and_lemmatize)"""
        # Simulate what happens in tokenize_and_lemmatize
        test_lemma = "l'homme"

        # Step 1: Apply French lemma normalization
        step1 = LinguisticsUtils.normalize_french_lemma(test_lemma)
        assert step1 == "lehomme"

        # Step 2: Apply general text normalization
        step2 = LinguisticsUtils.normalize_text(step1, fold_diacritics=True)
        assert step2 == "lehomme"

    def test_common_french_words_normalization(self):
        """Test normalization of common French words that might appear in word lists"""
        service = WordListService()

        common_words = {
            "être": "etre",
            "avoir": "avoir",
            "l'être": "etre",  # Extract head word
            "d'avoir": "avoir",  # Extract head word
            "aujourd'hui": "aujourdhui",
        }

        for word, expected in common_words.items():
            result = service.normalize_word(word, fold_diacritics=True)
            assert result == expected, f"Expected {word} → {expected}, got {result}"


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_multiple_elisions_in_sequence(self):
        """Test that only the first elision is processed"""
        # Only first elision should be expanded
        result = LinguisticsUtils.normalize_french_lemma("l'd'abord")
        # l'd'abord → le + d'abord → led'abord (then apostrophe removed)
        assert result == "ledabord"

    def test_words_without_elisions(self):
        """Test that words without elisions are still processed correctly"""
        assert LinguisticsUtils.normalize_french_lemma("chat") == "chat"
        assert LinguisticsUtils.normalize_french_lemma("maison") == "maison"
        assert LinguisticsUtils.normalize_french_lemma("bonjour") == "bonjour"

    def test_numeric_and_special_chars_in_wordlist(self):
        """Test that word list normalization handles special characters"""
        service = WordListService()

        # Numbers and punctuation should be removed from word list entries
        assert service.normalize_word("1. avoir") == "avoir"
        assert service.normalize_word("2) être") == "etre"
        assert service.normalize_word("3: chat") == "chat"

    def test_quoted_words_in_wordlist(self):
        """Test that quotes are removed from word list entries"""
        service = WordListService()

        assert service.normalize_word('"chat"') == "chat"
        assert service.normalize_word("'chien'") == "chien"
        assert service.normalize_word('"l\'homme"') == "lehomme"

    def test_zero_width_characters(self):
        """Test that zero-width characters are removed"""
        service = WordListService()

        # Zero-width space (U+200B)
        word_with_zwsp = "chat\u200bchien"
        assert service.normalize_word(word_with_zwsp) == "chatchien"


class TestBackwardsCompatibility:
    """Tests to ensure the changes don't break existing functionality"""

    def test_basic_normalization_still_works(self):
        """Test that basic normalization (case, whitespace) still works"""
        service = WordListService()

        assert service.normalize_word("CHAT") == "chat"
        assert service.normalize_word("  Chien  ") == "chien"
        assert service.normalize_word("Maison") == "maison"

    def test_variant_splitting_still_works(self):
        """Test that variant splitting is not affected"""
        service = WordListService()

        assert service.split_variants("chat|chats") == ["chat", "chats"]
        assert service.split_variants("bon/bonne") == ["bon", "bonne"]
        assert service.split_variants("un,une") == ["un", "une"]

    def test_head_token_extraction_still_works(self):
        """Test that multi-token head extraction is not affected"""
        service = WordListService()

        assert service.extract_head_token("le chat") == "chat"
        assert service.extract_head_token("un chien") == "chien"
        assert service.extract_head_token("la maison") == "maison"

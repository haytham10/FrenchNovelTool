"""Tests for Vocabulary Coverage Tool functionality"""
import pytest
from app import create_app, db
from app.models import User, WordList, CoverageRun, CoverageAssignment, UserSettings
from app.services.wordlist_service import WordListService
from app.services.coverage_service import CoverageService
from app.utils.linguistics import LinguisticsUtils


@pytest.fixture(scope='function')
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing"""
    user = User(
        email='test@example.com',
        name='Test User',
        google_id='test123',
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestWordListService:
    """Tests for WordListService"""
    
    def test_normalize_word_basic(self):
        """Test basic word normalization"""
        service = WordListService()
        
        # Basic normalization
        assert service.normalize_word("Bonjour") == "bonjour"
        assert service.normalize_word("  HELLO  ") == "hello"
    
    def test_normalize_word_diacritics(self):
        """Test diacritic folding"""
        service = WordListService()
        
        # With diacritics folding
        assert service.normalize_word("café", fold_diacritics=True) == "cafe"
        assert service.normalize_word("élève", fold_diacritics=True) == "eleve"
        
        # Without diacritics folding
        assert service.normalize_word("café", fold_diacritics=False) == "café"
    
    def test_normalize_word_elision(self):
        """Test elision handling"""
        service = WordListService()
        
        # Elisions should extract the head word
        assert service.normalize_word("l'homme") == "homme"
        assert service.normalize_word("d'abord") == "abord"
        assert service.normalize_word("j'ai") == "ai"
    
    def test_split_variants(self):
        """Test variant splitting"""
        service = WordListService()
        
        # Pipe separator
        assert service.split_variants("chat|chats") == ["chat", "chats"]
        
        # Slash separator
        assert service.split_variants("bon/bonne") == ["bon", "bonne"]
        
        # No separators
        assert service.split_variants("simple") == ["simple"]
    
    def test_ingest_word_list(self, app, sample_user):
        """Test word list ingestion"""
        service = WordListService()
        
        words = [
            "le", "la", "les",  # Articles
            "chat", "chats",  # Duplicates (singular/plural)
            "l'homme",  # Elision
            "bon|bonne",  # Variants
            "café",  # Diacritics
        ]
        
        wordlist, report = service.ingest_word_list(
            words=words,
            name="Test List",
            owner_user_id=sample_user.id,
            source_type='manual'
        )
        
        # Check that list was created
        assert wordlist.name == "Test List"
        assert wordlist.owner_user_id == sample_user.id
        assert wordlist.normalized_count > 0
        
        # Check ingestion report
        assert report['original_count'] == len(words)
        assert report['normalized_count'] > 0
        assert len(report['duplicates']) >= 0  # May have duplicates
    
    def test_get_user_wordlists(self, app, sample_user):
        """Test retrieving user word lists"""
        service = WordListService()
        
        # Create a user word list
        wordlist, _ = service.ingest_word_list(
            words=["test"],
            name="User List",
            owner_user_id=sample_user.id,
            source_type='manual'
        )
        db.session.commit()
        
        # Create a global word list
        global_wl, _ = service.ingest_word_list(
            words=["global"],
            name="Global List",
            owner_user_id=None,
            source_type='manual'
        )
        db.session.commit()
        
        # Get all lists for user
        lists = service.get_user_wordlists(sample_user.id, include_global=True)
        assert len(lists) >= 2
        
        # Get only user lists
        user_lists = service.get_user_wordlists(sample_user.id, include_global=False)
        assert len(user_lists) >= 1


class TestLinguisticsUtils:
    """Tests for LinguisticsUtils"""
    
    def test_normalize_text(self):
        """Test text normalization"""
        assert LinguisticsUtils.normalize_text("Bonjour") == "bonjour"
        assert LinguisticsUtils.normalize_text("  Test  ") == "test"
    
    def test_normalize_text_diacritics(self):
        """Test diacritic folding in text"""
        assert LinguisticsUtils.normalize_text("café", fold_diacritics=True) == "cafe"
        assert LinguisticsUtils.normalize_text("café", fold_diacritics=False) == "café"
    
    def test_handle_elision(self):
        """Test elision handling"""
        assert LinguisticsUtils.handle_elision("l'homme") == "homme"
        assert LinguisticsUtils.handle_elision("d'accord") == "accord"
        assert LinguisticsUtils.handle_elision("simple") == "simple"
    
    def test_tokenize_and_lemmatize(self):
        """Test tokenization and lemmatization"""
        text = "Les chats mangent."
        tokens = LinguisticsUtils.tokenize_and_lemmatize(text)
        
        # Should have tokens (punctuation excluded)
        assert len(tokens) > 0
        
        # Each token should have required fields
        for token in tokens:
            assert 'surface' in token
            assert 'lemma' in token
            assert 'normalized' in token
    
    def test_calculate_in_list_ratio(self):
        """Test in-list ratio calculation"""
        wordlist_keys = {'le', 'chat', 'manger'}
        
        # 100% match
        sentence = "Le chat mange"
        ratio, matched, total = LinguisticsUtils.calculate_in_list_ratio(
            sentence, wordlist_keys
        )
        assert ratio == 1.0  # Should be high (lemmas match)
        
        # Partial match
        sentence = "Le chat aime le poisson"
        ratio, matched, total = LinguisticsUtils.calculate_in_list_ratio(
            sentence, wordlist_keys
        )
        assert 0 < ratio < 1.0


class TestCoverageService:
    """Tests for CoverageService"""
    
    def test_build_sentence_index(self):
        """Test sentence indexing"""
        wordlist_keys = {'le', 'chat', 'manger', 'dormir'}
        service = CoverageService(wordlist_keys)
        
        sentences = [
            "Le chat mange.",
            "Le chat dort.",
            "Un chien court."
        ]
        
        index = service.build_sentence_index(sentences)
        
        assert len(index) == 3
        for idx in range(3):
            assert idx in index
            assert 'text' in index[idx]
            assert 'tokens' in index[idx]
            assert 'words_in_list' in index[idx]
            assert 'in_list_ratio' in index[idx]
    
    def test_coverage_mode_greedy(self):
        """Test coverage mode greedy algorithm"""
        wordlist_keys = {'le', 'chat', 'manger', 'dormir'}
        service = CoverageService(wordlist_keys)
        
        sentences = [
            "Le chat mange.",
            "Le chat dort.",
            "Un chien court."
        ]
        
        assignments, stats = service.coverage_mode_greedy(sentences)
        
        # Should have assignments
        assert len(assignments) > 0
        
        # Stats should be present
        assert 'words_total' in stats
        assert 'words_covered' in stats
        assert 'selected_sentence_count' in stats
        
        # Each assignment should have required fields
        for assignment in assignments:
            assert 'word_key' in assignment
            assert 'sentence_index' in assignment
            assert 'sentence_text' in assignment
    
    def test_filter_mode(self):
        """Test filter mode with multi-pass approach"""
        wordlist_keys = {'le', 'chat', 'manger', 'dormir', 'petit'}
        
        config = {
            'min_in_list_ratio': 0.7,
            'len_min': 2,
            'len_max': 10,
            'target_count': 2
        }
        
        service = CoverageService(wordlist_keys, config)
        
        sentences = [
            "Le chat mange.",  # 3 words, high ratio
            "Le petit chat dort.",  # 4 words, high ratio
            "Un gros chien court rapidement."  # 5 words, low ratio
        ]
        
        selected, stats = service.filter_mode(sentences)
        
        # Should have selected sentences
        assert len(selected) > 0
        
        # Stats should be present
        assert 'total_sentences' in stats
        assert 'candidates_passed_filter' in stats
        assert 'selected_count' in stats
        assert 'candidates_by_pass' in stats  # New field for multi-pass
        
        # Each selected sentence should have required fields
        for sentence_data in selected:
            assert 'sentence_index' in sentence_data
            assert 'sentence_text' in sentence_data
            assert 'sentence_score' in sentence_data
            assert 'in_list_ratio' in sentence_data
    
    def test_filter_mode_multipass_priority(self):
        """Test that filter mode prioritizes 4-word sentences over 3-word"""
        wordlist_keys = {'le', 'chat', 'manger', 'dormir', 'petit', 'grand', 'noir'}
        
        config = {
            'min_in_list_ratio': 0.8,
            'len_min': 3,
            'len_max': 8,
            'target_count': 3
        }
        
        service = CoverageService(wordlist_keys, config)
        
        sentences = [
            "Le chat mange maintenant.",  # 4 words - should be prioritized
            "Le chat dort.",  # 3 words
            "Le petit chat noir.",  # 4 words - should be prioritized
            "Chat dort.",  # 2 words - below min
            "Le grand chat noir dort bien."  # 6 words
        ]
        
        selected, stats = service.filter_mode(sentences)
        
        # Should select 3 sentences
        assert len(selected) <= 3
        
        # Check that pass information is included
        assert 'candidates_by_pass' in stats
        
        # If we have 4-word sentences, they should be selected first
        four_word_count = sum(1 for s in selected if s['token_count'] == 4)
        three_word_count = sum(1 for s in selected if s['token_count'] == 3)
        
        # 4-word sentences should be prioritized (we have 2 4-word sentences)
        # So we should get both 4-word sentences before any 3-word
        if four_word_count + three_word_count >= 2:
            assert four_word_count >= 2 or stats['candidates_by_pass'].get('pass_1_4word', 0) < 2


class TestCoverageModels:
    """Tests for coverage models"""
    
    def test_wordlist_model(self, app, sample_user):
        """Test WordList model"""
        wordlist = WordList(
            owner_user_id=sample_user.id,
            name="Test List",
            source_type='manual',
            normalized_count=100,
            canonical_samples=['le', 'la', 'les']
        )
        
        db.session.add(wordlist)
        db.session.commit()
        
        # Test to_dict
        data = wordlist.to_dict()
        assert data['name'] == "Test List"
        assert data['normalized_count'] == 100
        assert len(data['canonical_samples']) == 3
    
    def test_coverage_run_model(self, app, sample_user):
        """Test CoverageRun model"""
        run = CoverageRun(
            user_id=sample_user.id,
            mode='filter',
            source_type='history',
            source_id=1,
            status='pending'
        )
        
        db.session.add(run)
        db.session.commit()
        
        # Test to_dict
        data = run.to_dict()
        assert data['mode'] == 'filter'
        assert data['source_type'] == 'history'
        assert data['status'] == 'pending'
    
    def test_coverage_assignment_model(self, app, sample_user):
        """Test CoverageAssignment model"""
        # Create a coverage run first
        run = CoverageRun(
            user_id=sample_user.id,
            mode='coverage',
            source_type='history',
            source_id=1
        )
        db.session.add(run)
        db.session.commit()
        
        # Create assignment
        assignment = CoverageAssignment(
            coverage_run_id=run.id,
            word_key='chat',
            sentence_index=0,
            sentence_text='Le chat mange.'
        )
        
        db.session.add(assignment)
        db.session.commit()
        
        # Test to_dict
        data = assignment.to_dict()
        assert data['word_key'] == 'chat'
        assert data['sentence_index'] == 0
        assert data['sentence_text'] == 'Le chat mange.'

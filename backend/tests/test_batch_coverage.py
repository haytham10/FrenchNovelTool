"""Tests for Batch Coverage Mode functionality"""
import pytest
from app import create_app, db
from app.models import User, WordList, CoverageRun, CoverageAssignment
from app.services.coverage_service import CoverageService
from config import Config


class TestConfig(Config):
    """Test configuration that works with SQLite"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Override engine options for SQLite compatibility
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }


@pytest.fixture(scope='function')
def app():
    """Create application for testing"""
    app = create_app(config_class=TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


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


class TestBatchCoverageMode:
    """Tests for batch coverage analysis"""
    
    def test_batch_coverage_basic(self, app):
        """Test basic batch coverage with two sources"""
        # Define a simple wordlist
        wordlist_keys = {'chat', 'chien', 'maison', 'voiture', 'livre', 'table', 'chaise', 'porte'}
        
        # Source 1: Contains chat, chien, maison, voiture (4 words)
        source1 = [
            "Le chat est sur la table.",
            "Le chien court vite.",
            "La maison est grande.",
            "La voiture est rouge."
        ]
        
        # Source 2: Contains livre, table, chaise, porte (4 words, but table already covered)
        source2 = [
            "Le livre est intéressant.",
            "La table est en bois.",
            "La chaise est confortable.",
            "La porte est fermée."
        ]
        
        # Create coverage service
        service = CoverageService(
            wordlist_keys=wordlist_keys,
            config={'len_min': 3, 'len_max': 10, 'target_count': 0}
        )
        
        # Run batch coverage
        sources = [
            (1, source1),
            (2, source2)
        ]
        
        assignments, stats = service.batch_coverage_mode(sources)
        
        # Verify statistics
        assert stats['mode'] == 'batch'
        assert stats['sources_count'] == 2
        assert stats['words_total'] == 8
        assert stats['words_covered'] >= 7  # Should cover most words
        
        # Verify source breakdown
        assert 'source_breakdown' in stats
        assert len(stats['source_breakdown']) == 2
        
        # First source should cover some words
        source1_stats = stats['source_breakdown'][0]
        assert source1_stats['source_id'] == 1
        assert source1_stats['words_covered'] > 0
        
        # Second source should cover remaining words
        source2_stats = stats['source_breakdown'][1]
        assert source2_stats['source_id'] == 2
        
        # Verify we have assignments
        assert len(assignments) > 0
        
        # Verify learning set is created
        assert 'learning_set' in stats
        assert len(stats['learning_set']) > 0
    
    def test_batch_coverage_sequential_reduction(self, app):
        """Test that batch mode reduces uncovered words sequentially"""
        # Define wordlist
        wordlist_keys = {'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit'}
        
        # Source 1: Contains un, deux, trois, quatre
        source1 = [
            "Un chat mange.",
            "Deux chiens courent.",
            "Trois oiseaux volent.",
            "Quatre chevaux galopent."
        ]
        
        # Source 2: Contains cinq, six
        source2 = [
            "Cinq enfants jouent.",
            "Six livres sont là."
        ]
        
        # Source 3: Contains sept, huit
        source3 = [
            "Sept jours par semaine.",
            "Huit heures du matin."
        ]
        
        service = CoverageService(
            wordlist_keys=wordlist_keys,
            config={'len_min': 2, 'len_max': 10, 'target_count': 0}
        )
        
        sources = [
            (1, source1),
            (2, source2),
            (3, source3)
        ]
        
        assignments, stats = service.batch_coverage_mode(sources)
        
        # Check that words_remaining decreases with each source
        breakdown = stats['source_breakdown']
        
        # After source 1, we should have fewer remaining words
        assert breakdown[0]['words_remaining'] < 8
        
        # After source 2, even fewer
        if len(breakdown) > 1:
            assert breakdown[1]['words_remaining'] <= breakdown[0]['words_remaining']
        
        # After source 3, ideally all covered (or very few remaining)
        if len(breakdown) > 2:
            assert breakdown[2]['words_remaining'] <= breakdown[1]['words_remaining']
    
    def test_batch_coverage_empty_source(self, app):
        """Test batch coverage handles empty sources gracefully"""
        wordlist_keys = {'test', 'word'}
        
        # Source 1 has sentences
        source1 = ["Test sentence with word."]
        
        # Source 2 is empty
        source2 = []
        
        service = CoverageService(
            wordlist_keys=wordlist_keys,
            config={'len_min': 2, 'len_max': 10, 'target_count': 0}
        )
        
        sources = [
            (1, source1),
            (2, source2)
        ]
        
        # Should not crash
        assignments, stats = service.batch_coverage_mode(sources)
        
        # Should process at least source 1
        assert stats['sources_processed'] >= 1
    
    def test_batch_coverage_vs_single_coverage(self, app):
        """Compare batch coverage efficiency vs single combined source"""
        wordlist_keys = {'maison', 'chat', 'livre', 'table'}
        
        # Novel A: maison, chat
        novel_a = [
            "La maison est belle.",
            "Le chat est noir."
        ]
        
        # Novel B: livre, table  
        novel_b = [
            "Le livre est bon.",
            "La table est ronde."
        ]
        
        # Test batch mode
        service_batch = CoverageService(
            wordlist_keys=wordlist_keys,
            config={'len_min': 2, 'len_max': 10, 'target_count': 0}
        )
        
        assignments_batch, stats_batch = service_batch.batch_coverage_mode([
            (1, novel_a),
            (2, novel_b)
        ])
        
        # Test single mode (combined)
        service_single = CoverageService(
            wordlist_keys=wordlist_keys,
            config={'len_min': 2, 'len_max': 10, 'target_count': 0}
        )
        
        combined_sentences = novel_a + novel_b
        assignments_single, stats_single = service_single.coverage_mode_greedy(combined_sentences)
        
        # Both should cover all words
        assert stats_batch['words_covered'] == stats_single['words_covered']
        
        # Batch mode should provide source breakdown
        assert 'source_breakdown' in stats_batch
        assert len(stats_batch['source_breakdown']) == 2
    
    def test_batch_coverage_respects_sentence_limit(self, app):
        """Test that batch coverage respects the target_count (sentence_limit)"""
        # Define a wordlist with many words to ensure we get more sentences than our limit
        wordlist_keys = {'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix'}
        
        # Source 1: Several sentences
        source1 = [
            "Un chat mange du poisson.",
            "Deux chiens courent dans le parc.",
            "Trois oiseaux volent haut.",
            "Quatre chevaux galopent vite.",
            "Cinq enfants jouent ensemble."
        ]
        
        # Source 2: More sentences
        source2 = [
            "Six livres sont sur la table.",
            "Sept jours composent une semaine.",
            "Huit heures du matin arrivent.",
            "Neuf personnes attendent dehors.",
            "Dix minutes restent seulement."
        ]
        
        # Set a sentence limit lower than total potential sentences
        sentence_limit = 6
        
        service = CoverageService(
            wordlist_keys=wordlist_keys,
            config={'len_min': 2, 'len_max': 15, 'target_count': sentence_limit}
        )
        
        sources = [
            (1, source1),
            (2, source2)
        ]
        
        assignments, stats = service.batch_coverage_mode(sources)
        
        # Verify the learning set respects the limit
        assert 'learning_set' in stats
        learning_set = stats['learning_set']
        
        # This is the critical assertion: learning set should not exceed sentence_limit
        assert len(learning_set) <= sentence_limit, \
            f"Learning set has {len(learning_set)} sentences, expected <= {sentence_limit}"
        
        # Verify all entries have required metadata
        for entry in learning_set:
            assert 'rank' in entry
            assert 'sentence_text' in entry
            assert 'token_count' in entry, "Missing token_count in learning_set entry"
            assert 'new_word_count' in entry, "Missing new_word_count in learning_set entry"
            assert 'score' in entry, "Missing score in learning_set entry"
        
        # Verify ranks are sequential starting from 1
        ranks = [entry['rank'] for entry in learning_set]
        assert ranks == list(range(1, len(learning_set) + 1)), \
            "Ranks should be sequential starting from 1"
        
        # Verify sentences are sorted by quality score (descending)
        if len(learning_set) > 1:
            for i in range(len(learning_set) - 1):
                # Score should be decreasing or equal (ties allowed)
                assert learning_set[i]['score'] >= learning_set[i + 1]['score'], \
                    "Learning set should be sorted by score (descending)"
    
    def test_batch_coverage_metadata_completeness(self, app):
        """Test that batch coverage includes all required metadata in learning_set"""
        wordlist_keys = {'chat', 'chien', 'maison'}
        
        source1 = [
            "Le chat est sur la maison.",
            "Le chien court vite."
        ]
        
        service = CoverageService(
            wordlist_keys=wordlist_keys,
            config={'len_min': 2, 'len_max': 10, 'target_count': 10}
        )
        
        assignments, stats = service.batch_coverage_mode([(1, source1)])
        
        # Verify learning_set has complete metadata
        assert 'learning_set' in stats
        learning_set = stats['learning_set']
        assert len(learning_set) > 0
        
        for entry in learning_set:
            # Check all required fields are present
            assert 'rank' in entry
            assert 'source_id' in entry
            assert 'source_index' in entry
            assert 'sentence_index' in entry
            assert 'sentence_text' in entry
            assert 'token_count' in entry
            assert 'new_word_count' in entry
            assert 'score' in entry
            
            # Verify types
            assert isinstance(entry['rank'], int)
            assert isinstance(entry['token_count'], int)
            assert isinstance(entry['new_word_count'], int)
            assert isinstance(entry['score'], (int, float))
            assert isinstance(entry['sentence_text'], str)

"""Integration tests for Vocabulary Coverage Tool metrics and end-to-end flows"""
import pytest
import json
from app import create_app, db
from app.models import User, WordList, CoverageRun, CoverageAssignment, History, Job
from app.services.wordlist_service import WordListService
from app.services.coverage_service import CoverageService
from flask_jwt_extended import create_access_token


@pytest.fixture(scope='function')
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'test-secret-key'

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


@pytest.fixture
def auth_headers(app, sample_user):
    """Create authentication headers"""
    access_token = create_access_token(identity=str(sample_user.id))
    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def sample_wordlist(app, sample_user):
    """Create a sample word list"""
    service = WordListService()
    wordlist, _ = service.ingest_word_list(
        words=["le", "chat", "chien", "maison", "manger", "dormir"],
        name="Test Word List",
        owner_user_id=sample_user.id,
        source_type='manual'
    )
    db.session.commit()
    return wordlist


@pytest.fixture
def sample_history(app, sample_user):
    """Create a sample history entry with sentences"""
    history = History(
        user_id=sample_user.id,
        original_filename='test.pdf',
        processed_sentences_count=3,
        sentences=[
            {'normalized': 'Le chat mange.', 'original': 'Le chat mange.'},
            {'normalized': 'Le chien dort.', 'original': 'Le chien dort.'},
            {'normalized': 'La maison est grande.', 'original': 'La maison est grande.'}
        ]
    )
    db.session.add(history)
    db.session.commit()
    return history


class TestMetricsEndpoint:
    """Tests for Prometheus metrics endpoint"""
    
    def test_metrics_endpoint_accessible(self, client):
        """Test that metrics endpoint is accessible without auth"""
        response = client.get('/api/v1/metrics')
        assert response.status_code == 200
        
        # Check content type
        assert 'text/plain' in response.content_type
    
    def test_metrics_content(self, client, sample_wordlist):
        """Test that metrics contain expected data"""
        response = client.get('/api/v1/metrics')
        assert response.status_code == 200
        
        content = response.data.decode('utf-8')
        
        # Should contain wordlist metrics
        assert 'wordlists_total' in content
        assert 'wordlists_created_total' in content
        
        # Should contain coverage metrics
        assert 'coverage_runs_total' in content
        assert 'coverage_build_duration_seconds' in content


class TestWordListAPIs:
    """Integration tests for WordList CRUD APIs"""
    
    def test_list_wordlists(self, client, auth_headers, sample_wordlist):
        """Test listing word lists"""
        response = client.get('/api/v1/wordlists', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'wordlists' in data
        assert 'pagination' in data
        assert len(data['wordlists']) >= 1
    
    def test_create_wordlist_json(self, client, auth_headers):
        """Test creating word list via JSON"""
        payload = {
            'name': 'New List',
            'source_type': 'manual',
            'words': ['test', 'words', 'list'],
            'fold_diacritics': True
        }
        
        response = client.post(
            '/api/v1/wordlists',
            headers=auth_headers,
            data=json.dumps(payload)
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'wordlist' in data
        assert 'ingestion_report' in data
        assert data['wordlist']['name'] == 'New List'
    
    def test_get_wordlist(self, client, auth_headers, sample_wordlist):
        """Test getting specific word list"""
        response = client.get(
            f'/api/v1/wordlists/{sample_wordlist.id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == sample_wordlist.id
        assert data['name'] == sample_wordlist.name
    
    def test_update_wordlist(self, client, auth_headers, sample_wordlist):
        """Test updating word list"""
        payload = {'name': 'Updated Name'}
        
        response = client.patch(
            f'/api/v1/wordlists/{sample_wordlist.id}',
            headers=auth_headers,
            data=json.dumps(payload)
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Updated Name'
    
    def test_delete_wordlist(self, client, auth_headers, sample_wordlist):
        """Test deleting word list"""
        response = client.delete(
            f'/api/v1/wordlists/{sample_wordlist.id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify it's deleted
        check_response = client.get(
            f'/api/v1/wordlists/{sample_wordlist.id}',
            headers=auth_headers
        )
        assert check_response.status_code == 404


class TestCoverageRunAPIs:
    """Integration tests for Coverage Run APIs"""
    
    def test_create_coverage_run(self, client, auth_headers, sample_wordlist, sample_history):
        """Test creating a coverage run"""
        payload = {
            'mode': 'coverage',
            'source_type': 'history',
            'source_id': sample_history.id,
            'wordlist_id': sample_wordlist.id,
            'config': {
                'alpha': 0.5,
                'beta': 0.3
            }
        }
        
        response = client.post(
            '/api/v1/coverage/run',
            headers=auth_headers,
            data=json.dumps(payload)
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'coverage_run' in data
        assert 'task_id' in data
        assert data['coverage_run']['mode'] == 'coverage'
        assert data['coverage_run']['status'] == 'pending'
    
    def test_get_coverage_run(self, client, auth_headers, sample_user, sample_wordlist, sample_history):
        """Test getting coverage run details"""
        # Create a coverage run
        coverage_run = CoverageRun(
            user_id=sample_user.id,
            mode='coverage',
            source_type='history',
            source_id=sample_history.id,
            wordlist_id=sample_wordlist.id,
            status='completed'
        )
        db.session.add(coverage_run)
        db.session.commit()
        
        response = client.get(
            f'/api/v1/coverage/runs/{coverage_run.id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'coverage_run' in data
        assert data['coverage_run']['id'] == coverage_run.id


class TestCoverageServiceIntegration:
    """Integration tests for CoverageService end-to-end"""
    
    def test_coverage_mode_end_to_end(self, app):
        """Test complete coverage mode flow"""
        wordlist_keys = {'le', 'chat', 'chien', 'maison'}
        sentences = [
            "Le chat mange.",
            "Le chien dort dans la maison.",
            "La maison est grande."
        ]
        
        service = CoverageService(wordlist_keys, {})
        assignments, stats = service.coverage_mode_greedy(sentences)
        
        # Should have assignments
        assert len(assignments) > 0
        
        # Stats should be complete
        assert 'words_total' in stats
        assert 'words_covered' in stats
        assert 'words_uncovered' in stats
        assert stats['words_total'] == len(wordlist_keys)
    
    def test_filter_mode_end_to_end(self, app):
        """Test complete filter mode flow"""
        wordlist_keys = {'le', 'chat', 'chien', 'dormir', 'manger'}
        sentences = [
            "Le chat mange.",  # 3 words, high ratio
            "Le chien dort.",  # 3 words, high ratio
            "La maison est très grande et belle.",  # Many words, low ratio
            "Le chat dort.",  # 3 words, high ratio
        ]
        
        config = {
            'min_in_list_ratio': 0.6,
            'len_min': 3,
            'len_max': 4,
            'target_count': 10
        }
        
        service = CoverageService(wordlist_keys, config)
        selected, stats = service.filter_mode(sentences)
        
        # Should have selections
        assert len(selected) > 0
        
        # Stats should be complete
        assert 'total_sentences' in stats
        assert 'selected_count' in stats
        assert 'filter_acceptance_ratio' in stats
        
        # Selected sentences should meet criteria
        for item in selected:
            assert 'sentence_text' in item
            assert 'sentence_score' in item


class TestIngestionReporting:
    """Tests for ingestion report generation"""
    
    def test_ingestion_report_duplicates(self, app, sample_user):
        """Test that duplicates are reported correctly"""
        service = WordListService()
        
        words = ["chat", "Chat", "CHAT", "chats"]  # Duplicates
        wordlist, report = service.ingest_word_list(
            words=words,
            name="Duplicate Test",
            owner_user_id=sample_user.id,
            source_type='manual'
        )
        
        assert report['original_count'] == 4
        assert len(report['duplicates']) > 0
    
    def test_ingestion_report_variants(self, app, sample_user):
        """Test that variants are expanded correctly"""
        service = WordListService()
        
        words = ["bon/bonne", "chat|chats"]  # Variants
        wordlist, report = service.ingest_word_list(
            words=words,
            name="Variant Test",
            owner_user_id=sample_user.id,
            source_type='manual'
        )
        
        assert report['variants_expanded'] > 0
    
    def test_ingestion_report_multi_token(self, app, sample_user):
        """Test that multi-token entries are flagged"""
        service = WordListService()
        
        words = ["bon jour", "au revoir"]  # Multi-token
        wordlist, report = service.ingest_word_list(
            words=words,
            name="Multi-token Test",
            owner_user_id=sample_user.id,
            source_type='manual'
        )
        
        assert len(report['multi_token_entries']) > 0

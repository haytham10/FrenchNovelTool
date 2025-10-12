"""
Tests for Global Wordlist Manager functionality.

This module tests the GlobalWordlistManager class and related API endpoints
to ensure proper handling of global wordlists with versioning and automatic seeding.
"""
import pytest
from pathlib import Path
from app import create_app, db
from app.models import User, WordList
from app.services.global_wordlist_manager import GlobalWordlistManager
from tempfile import NamedTemporaryFile


@pytest.fixture(scope='function')
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
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
        google_id='12345'
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestGlobalWordlistManager:
    """Tests for GlobalWordlistManager class"""
    
    def test_create_from_file(self, app):
        """Test creating a global wordlist from a file"""
        # Create a temporary wordlist file
        with NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("# Test wordlist\n")
            f.write("chat\n")
            f.write("chien\n")
            f.write("maison\n")
            f.write("livre\n")
            f.write("bon\n")
            temp_file = Path(f.name)
        
        try:
            wordlist = GlobalWordlistManager.create_from_file(
                filepath=temp_file,
                name="Test Global Wordlist",
                set_as_default=True,
                version="1.0.0"
            )
            
            assert wordlist is not None
            assert wordlist.name == "Test Global Wordlist"
            assert wordlist.owner_user_id is None  # Global wordlist
            assert wordlist.is_global_default is True
            assert wordlist.normalized_count > 0
        finally:
            temp_file.unlink()
    
    def test_ensure_global_default_exists_creates_when_missing(self, app):
        """Test that ensure_global_default_exists creates wordlist when none exists"""
        # Ensure no global default exists
        assert WordList.query.filter_by(is_global_default=True).first() is None
        
        # Create a test wordlist file
        test_file = Path(__file__).parent.parent / 'data' / 'wordlists' / 'french_2k.txt'
        
        # Only run if the file exists
        if test_file.exists():
            wordlist = GlobalWordlistManager.ensure_global_default_exists()
            
            assert wordlist is not None
            assert wordlist.is_global_default is True
            assert wordlist.owner_user_id is None
    
    def test_ensure_global_default_exists_idempotent(self, app):
        """Test that ensure_global_default_exists is idempotent"""
        # Create a global default manually
        wordlist1 = WordList(
            owner_user_id=None,
            name="Test Global Default",
            source_type='manual',
            normalized_count=10,
            words_json=['word1', 'word2'],
            is_global_default=True
        )
        db.session.add(wordlist1)
        db.session.commit()
        
        # Call ensure_global_default_exists - should return existing
        wordlist2 = GlobalWordlistManager.ensure_global_default_exists()
        
        assert wordlist2.id == wordlist1.id
        assert WordList.query.filter_by(is_global_default=True).count() == 1
    
    def test_get_global_default(self, app):
        """Test getting the global default wordlist"""
        # Create a global default
        wordlist = WordList(
            owner_user_id=None,
            name="Test Global Default",
            source_type='manual',
            normalized_count=10,
            words_json=['word1', 'word2'],
            is_global_default=True
        )
        db.session.add(wordlist)
        db.session.commit()
        
        # Get global default
        default = GlobalWordlistManager.get_global_default()
        
        assert default is not None
        assert default.id == wordlist.id
        assert default.is_global_default is True
    
    def test_set_global_default(self, app):
        """Test setting a wordlist as global default"""
        # Create two global wordlists
        wordlist1 = WordList(
            owner_user_id=None,
            name="Wordlist 1",
            source_type='manual',
            normalized_count=10,
            words_json=['word1'],
            is_global_default=True
        )
        wordlist2 = WordList(
            owner_user_id=None,
            name="Wordlist 2",
            source_type='manual',
            normalized_count=10,
            words_json=['word2'],
            is_global_default=False
        )
        db.session.add_all([wordlist1, wordlist2])
        db.session.commit()
        
        # Set wordlist2 as default
        new_default = GlobalWordlistManager.set_global_default(wordlist2.id)
        
        assert new_default.id == wordlist2.id
        assert new_default.is_global_default is True
        
        # Check that wordlist1 is no longer default
        db.session.refresh(wordlist1)
        assert wordlist1.is_global_default is False
    
    def test_set_global_default_user_wordlist_fails(self, app, sample_user):
        """Test that setting a user wordlist as global default fails"""
        # Create a user wordlist
        wordlist = WordList(
            owner_user_id=sample_user.id,
            name="User Wordlist",
            source_type='manual',
            normalized_count=10,
            words_json=['word1'],
            is_global_default=False
        )
        db.session.add(wordlist)
        db.session.commit()
        
        # Try to set as global default - should fail
        with pytest.raises(ValueError, match="Only global wordlists"):
            GlobalWordlistManager.set_global_default(wordlist.id)
    
    def test_list_global_wordlists(self, app, sample_user):
        """Test listing all global wordlists"""
        # Create global and user wordlists
        global_wl1 = WordList(
            owner_user_id=None,
            name="Global 1",
            source_type='manual',
            normalized_count=10,
            words_json=['word1'],
            is_global_default=True
        )
        global_wl2 = WordList(
            owner_user_id=None,
            name="Global 2",
            source_type='manual',
            normalized_count=10,
            words_json=['word2'],
            is_global_default=False
        )
        user_wl = WordList(
            owner_user_id=sample_user.id,
            name="User Wordlist",
            source_type='manual',
            normalized_count=10,
            words_json=['word3'],
            is_global_default=False
        )
        db.session.add_all([global_wl1, global_wl2, user_wl])
        db.session.commit()
        
        # List global wordlists
        global_wordlists = GlobalWordlistManager.list_global_wordlists()
        
        assert len(global_wordlists) == 2
        assert all(wl.owner_user_id is None for wl in global_wordlists)
        # Default should be first
        assert global_wordlists[0].is_global_default is True
    
    def test_get_stats(self, app):
        """Test getting statistics about global wordlists"""
        # Create a global default
        wordlist = WordList(
            owner_user_id=None,
            name="Test Global Default",
            source_type='manual',
            normalized_count=100,
            words_json=['word1', 'word2'],
            is_global_default=True
        )
        db.session.add(wordlist)
        db.session.commit()
        
        # Get stats
        stats = GlobalWordlistManager.get_stats()
        
        assert stats['total_global_wordlists'] == 1
        assert stats['has_default'] is True
        assert stats['default_wordlist'] is not None
        assert stats['default_wordlist']['id'] == wordlist.id
        assert stats['default_wordlist']['normalized_count'] == 100
        assert len(stats['all_global_wordlists']) == 1


class TestGlobalWordlistAPIs:
    """Tests for global wordlist API endpoints"""
    
    def test_get_global_wordlist_stats(self, client, app, sample_user):
        """Test GET /api/v1/wordlists/global/stats"""
        from flask_jwt_extended import create_access_token
        
        # Create a global default
        wordlist = WordList(
            owner_user_id=None,
            name="Test Global",
            source_type='manual',
            normalized_count=50,
            words_json=['word1'],
            is_global_default=True
        )
        db.session.add(wordlist)
        db.session.commit()
        
        # Get JWT token
        access_token = create_access_token(identity=str(sample_user.id))
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Call API
        response = client.get('/api/v1/wordlists/global/stats', headers=headers)
        
        assert response.status_code == 200
        data = response.json
        assert data['has_default'] is True
        assert data['total_global_wordlists'] == 1
        assert data['default_wordlist']['normalized_count'] == 50
    
    def test_get_global_default_wordlist(self, client, app, sample_user):
        """Test GET /api/v1/wordlists/global/default"""
        from flask_jwt_extended import create_access_token
        
        # Create a global default
        wordlist = WordList(
            owner_user_id=None,
            name="Test Global",
            source_type='manual',
            normalized_count=50,
            words_json=['word1'],
            is_global_default=True
        )
        db.session.add(wordlist)
        db.session.commit()
        
        # Get JWT token
        access_token = create_access_token(identity=str(sample_user.id))
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Call API
        response = client.get('/api/v1/wordlists/global/default', headers=headers)
        
        assert response.status_code == 200
        data = response.json
        assert data['name'] == "Test Global"
        assert data['is_global_default'] is True
        assert data['normalized_count'] == 50
    
    def test_get_global_default_wordlist_not_found(self, client, app, sample_user):
        """Test GET /api/v1/wordlists/global/default when none exists"""
        from flask_jwt_extended import create_access_token
        
        # Get JWT token
        access_token = create_access_token(identity=str(sample_user.id))
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Call API
        response = client.get('/api/v1/wordlists/global/default', headers=headers)
        
        assert response.status_code == 404
    
    def test_list_global_wordlists_api(self, client, app, sample_user):
        """Test GET /api/v1/wordlists/global"""
        from flask_jwt_extended import create_access_token
        
        # Create global wordlists
        global_wl1 = WordList(
            owner_user_id=None,
            name="Global 1",
            source_type='manual',
            normalized_count=10,
            words_json=['word1'],
            is_global_default=True
        )
        global_wl2 = WordList(
            owner_user_id=None,
            name="Global 2",
            source_type='manual',
            normalized_count=20,
            words_json=['word2'],
            is_global_default=False
        )
        db.session.add_all([global_wl1, global_wl2])
        db.session.commit()
        
        # Get JWT token
        access_token = create_access_token(identity=str(sample_user.id))
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Call API
        response = client.get('/api/v1/wordlists/global', headers=headers)
        
        assert response.status_code == 200
        data = response.json
        assert data['total'] == 2
        assert len(data['wordlists']) == 2
        # Default should be first
        assert data['wordlists'][0]['is_global_default'] is True

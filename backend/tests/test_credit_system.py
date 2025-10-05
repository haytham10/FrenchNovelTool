"""Tests for credit and job services"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from flask import Flask
from app import db
from app.models import User, CreditLedger, Job
from app.services.credit_service import CreditService
from app.services.job_service import JobService
from app.constants import (
    CREDIT_REASON_MONTHLY_GRANT,
    CREDIT_REASON_JOB_RESERVE,
    CREDIT_REASON_JOB_REFUND,
    CREDIT_REASON_ADMIN_ADJUSTMENT,
    JOB_STATUS_PENDING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    MONTHLY_CREDIT_GRANT
)
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    RATELIMIT_ENABLED = False


@pytest.fixture
def app():
    """Create Flask app for testing"""
    from app import create_app
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_user(app):
    """Create a test user"""
    user = User(
        email='test@example.com',
        name='Test User',
        google_id='test_google_id'
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestCreditService:
    """Tests for CreditService"""
    
    def test_get_current_month(self, app):
        """Test getting current month"""
        month = CreditService.get_current_month()
        assert len(month) == 7
        assert month[:4].isdigit()  # Year
        assert month[4] == '-'
        assert month[5:].isdigit()  # Month
    
    def test_grant_monthly_credits(self, app, test_user):
        """Test granting monthly credits"""
        month = CreditService.get_current_month()
        
        # Grant credits
        entry = CreditService.grant_monthly_credits(test_user.id, month)
        
        assert entry is not None
        assert entry.user_id == test_user.id
        assert entry.month == month
        assert entry.delta_credits == MONTHLY_CREDIT_GRANT
        assert entry.reason == CREDIT_REASON_MONTHLY_GRANT
        
        # Try granting again - should return existing entry
        entry2 = CreditService.grant_monthly_credits(test_user.id, month)
        assert entry2.id == entry.id
    
    def test_ensure_monthly_grant(self, app, test_user):
        """Test ensuring monthly grant"""
        # First call should create grant
        created = CreditService.ensure_monthly_grant(test_user.id)
        assert created is True
        
        # Second call should not create duplicate
        created = CreditService.ensure_monthly_grant(test_user.id)
        assert created is False
    
    def test_calculate_balance(self, app, test_user):
        """Test calculating balance"""
        month = CreditService.get_current_month()
        
        # Initially 0
        balance = CreditService.calculate_balance(test_user.id, month)
        assert balance == 0
        
        # Grant credits
        CreditService.grant_monthly_credits(test_user.id, month)
        balance = CreditService.calculate_balance(test_user.id, month)
        assert balance == MONTHLY_CREDIT_GRANT
        
        # Reserve some credits (simulate job)
        job = Job(
            user_id=test_user.id,
            original_filename='test.pdf',
            model='gemini-2.5-flash',
            estimated_tokens=1000,
            estimated_credits=10,
            pricing_version='v1.0',
            pricing_rate=1.0,
            status=JOB_STATUS_PENDING
        )
        db.session.add(job)
        db.session.commit()
        
        success, _ = CreditService.reserve_credits(test_user.id, job.id, 10)
        assert success is True
        
        balance = CreditService.calculate_balance(test_user.id, month)
        assert balance == MONTHLY_CREDIT_GRANT - 10
    
    def test_reserve_credits_insufficient(self, app, test_user):
        """Test reserving credits with insufficient balance"""
        month = CreditService.get_current_month()
        
        # Create a job
        job = Job(
            user_id=test_user.id,
            original_filename='test.pdf',
            model='gemini-2.5-flash',
            estimated_tokens=100000,
            estimated_credits=100000,
            pricing_version='v1.0',
            pricing_rate=1.0,
            status=JOB_STATUS_PENDING
        )
        db.session.add(job)
        db.session.commit()
        
        # Grant only 100 credits
        CreditService.grant_monthly_credits(test_user.id, month, amount=100)
        
        # Try to reserve 100000 credits
        success, error = CreditService.reserve_credits(test_user.id, job.id, 100000)
        assert success is False
        assert 'Insufficient credits' in error
    
    def test_adjust_final_credits(self, app, test_user):
        """Test adjusting credits after job completion"""
        month = CreditService.get_current_month()
        CreditService.grant_monthly_credits(test_user.id, month)
        
        # Create and reserve for a job
        job = Job(
            user_id=test_user.id,
            original_filename='test.pdf',
            model='gemini-2.5-flash',
            estimated_tokens=1000,
            estimated_credits=10,
            pricing_version='v1.0',
            pricing_rate=1.0,
            status=JOB_STATUS_PENDING
        )
        db.session.add(job)
        db.session.commit()
        
        CreditService.reserve_credits(test_user.id, job.id, 10)
        
        # Adjust final (used only 5)
        entry = CreditService.adjust_final_credits(test_user.id, job.id, 10, 5)
        assert entry is not None
        assert entry.delta_credits == 5  # Refund 5 credits
        
        # Balance should be back to original - 5
        balance = CreditService.calculate_balance(test_user.id, month)
        assert balance == MONTHLY_CREDIT_GRANT - 5
    
    def test_refund_credits(self, app, test_user):
        """Test refunding credits for failed job"""
        month = CreditService.get_current_month()
        CreditService.grant_monthly_credits(test_user.id, month)
        
        # Create and reserve for a job
        job = Job(
            user_id=test_user.id,
            original_filename='test.pdf',
            model='gemini-2.5-flash',
            estimated_tokens=1000,
            estimated_credits=10,
            pricing_version='v1.0',
            pricing_rate=1.0,
            status=JOB_STATUS_PENDING
        )
        db.session.add(job)
        db.session.commit()
        
        CreditService.reserve_credits(test_user.id, job.id, 10)
        balance_after_reserve = CreditService.calculate_balance(test_user.id, month)
        
        # Refund all credits
        entry = CreditService.refund_credits(test_user.id, job.id, 10, 'Job failed')
        assert entry is not None
        assert entry.delta_credits == 10
        assert entry.reason == CREDIT_REASON_JOB_REFUND
        
        # Balance should be back to original
        balance = CreditService.calculate_balance(test_user.id, month)
        assert balance == MONTHLY_CREDIT_GRANT
    
    def test_admin_adjustment(self, app, test_user):
        """Test admin credit adjustment"""
        month = CreditService.get_current_month()
        
        # Add admin adjustment
        entry = CreditService.admin_adjustment(
            test_user.id,
            amount=5000,
            description='Bonus credits',
            month=month
        )
        
        assert entry is not None
        assert entry.delta_credits == 5000
        assert entry.reason == CREDIT_REASON_ADMIN_ADJUSTMENT
        
        balance = CreditService.calculate_balance(test_user.id, month)
        assert balance == 5000
    
    def test_get_credit_summary(self, app, test_user):
        """Test getting credit summary"""
        month = CreditService.get_current_month()
        
        # Grant credits
        CreditService.grant_monthly_credits(test_user.id, month)
        
        summary = CreditService.get_credit_summary(test_user.id, month)
        
        assert summary['balance'] == MONTHLY_CREDIT_GRANT
        assert summary['granted'] == MONTHLY_CREDIT_GRANT
        assert summary['used'] == 0
        assert summary['refunded'] == 0
        assert summary['month'] == month
        assert 'next_reset' in summary


class TestJobService:
    """Tests for JobService"""
    
    def test_get_model_name(self, app):
        """Test model name mapping"""
        assert JobService.get_model_name('balanced') == 'gemini-2.5-flash'
        assert JobService.get_model_name('quality') == 'gemini-2.5-pro'
        assert JobService.get_model_name('speed') == 'gemini-2.5-flash-lite'
    
    def test_get_pricing_rate(self, app):
        """Test getting pricing rate"""
        assert JobService.get_pricing_rate('gemini-2.5-flash') == 1
        assert JobService.get_pricing_rate('gemini-2.5-pro') == 5
        assert JobService.get_pricing_rate('gemini-2.5-flash-lite') == 1
    
    def test_estimate_tokens_heuristic(self, app):
        """Test heuristic token estimation"""
        text = 'a' * 400  # 400 characters
        tokens = JobService.estimate_tokens_heuristic(text)
        
        # 400 / 4 = 100 tokens, with 10% buffer = 110
        assert tokens >= 100
        assert tokens <= 150
    
    def test_calculate_credits(self, app):
        """Test credit calculation"""
        # 1000 tokens with rate 1 = 1 credit
        credits = JobService.calculate_credits(1000, 'gemini-2.5-flash-lite')
        assert credits == 1
        
        # 1000 tokens with rate 5 = 5 credits
        credits = JobService.calculate_credits(1000, 'gemini-2.5-pro')
        assert credits == 5
        
        # 500 tokens with rate 1 = 1 credit (rounded up)
        credits = JobService.calculate_credits(500, 'gemini-2.5-flash')
        assert credits == 1
    
    def test_create_job(self, app, test_user):
        """Test creating a job"""
        job = JobService.create_job(
            user_id=test_user.id,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=1000,
            processing_settings={'test': 'settings'}
        )
        
        assert job is not None
        assert job.user_id == test_user.id
        assert job.original_filename == 'test.pdf'
        assert job.model == 'gemini-2.5-flash'
        assert job.estimated_tokens == 1000
        assert job.status == JOB_STATUS_PENDING
        assert job.processing_settings == {'test': 'settings'}
    
    def test_start_job(self, app, test_user):
        """Test starting a job"""
        job = JobService.create_job(
            user_id=test_user.id,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=1000,
            processing_settings={}
        )
        
        success = JobService.start_job(job.id)
        assert success is True
        
        # Refresh job
        job = Job.query.get(job.id)
        assert job.status == 'processing'
        assert job.started_at is not None
    
    def test_complete_job(self, app, test_user):
        """Test completing a job"""
        job = JobService.create_job(
            user_id=test_user.id,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=1000,
            processing_settings={}
        )
        
        JobService.start_job(job.id)
        completed_job = JobService.complete_job(job.id, actual_tokens=800)
        
        assert completed_job.status == JOB_STATUS_COMPLETED
        assert completed_job.actual_tokens == 800
        assert completed_job.actual_credits > 0
        assert completed_job.completed_at is not None
    
    def test_fail_job(self, app, test_user):
        """Test failing a job"""
        job = JobService.create_job(
            user_id=test_user.id,
            original_filename='test.pdf',
            model_preference='balanced',
            estimated_tokens=1000,
            processing_settings={}
        )
        
        failed_job = JobService.fail_job(job.id, 'Test error', 'TEST_ERROR')
        
        assert failed_job.status == JOB_STATUS_FAILED
        assert failed_job.error_message == 'Test error'
        assert failed_job.error_code == 'TEST_ERROR'
        assert failed_job.completed_at is not None
    
    def test_estimate_job_cost(self, app):
        """Test estimating job cost"""
        text = 'a' * 4000  # Should be ~1000 tokens with heuristic
        
        estimate = JobService.estimate_job_cost(text, 'balanced', prefer_api=False)
        
        assert 'model' in estimate
        assert estimate['model'] == 'gemini-2.5-flash'
        assert estimate['model_preference'] == 'balanced'
        assert 'estimated_tokens' in estimate
        assert 'estimated_credits' in estimate
        assert estimate['pricing_rate'] == 1
        assert estimate['estimation_method'] == 'heuristic'

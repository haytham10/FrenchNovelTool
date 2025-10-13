"""Service for managing processing jobs and token estimation"""
import math
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from flask import current_app
from app import db
from app.models import Job, History
from app.constants import (
    JOB_STATUS_PENDING,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
    MODEL_PRICING,
    MODEL_PREFERENCE_MAP,
    PRICING_VERSION,
    TOKEN_ESTIMATION_CHARS_PER_TOKEN,
    TOKEN_ESTIMATION_SAFETY_BUFFER,
)


class JobService:
    """Service for job lifecycle management and token estimation"""

    @staticmethod
    def get_model_name(model_preference: str) -> str:
        """
        Convert user-facing model preference to actual Gemini model name.

        Args:
            model_preference: 'balanced', 'quality', or 'speed'

        Returns:
            Actual Gemini model name
        """
        return MODEL_PREFERENCE_MAP.get(model_preference, MODEL_PREFERENCE_MAP["speed"])

    @staticmethod
    def get_pricing_rate(model_name: str) -> float:
        """
        Get pricing rate for a model (credits per 1K tokens).

        Args:
            model_name: Actual Gemini model name

        Returns:
            Pricing rate (credits per 1K tokens)
        """
        return MODEL_PRICING.get(model_name, MODEL_PRICING["gemini-2.5-flash"])

    @staticmethod
    def estimate_tokens_heuristic(text: str) -> int:
        """
        Estimate token count using character-based heuristic.
        Fallback method when API estimation is not available.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        char_count = len(text)
        estimated_tokens = math.ceil(char_count / TOKEN_ESTIMATION_CHARS_PER_TOKEN)

        # Apply safety buffer
        buffered_tokens = math.ceil(estimated_tokens * TOKEN_ESTIMATION_SAFETY_BUFFER)

        return buffered_tokens

    @staticmethod
    def estimate_tokens_api(text: str, model_name: str) -> Optional[int]:
        """
        Estimate token count using Gemini API countTokens endpoint.

        Args:
            text: Input text
            model_name: Gemini model name

        Returns:
            Estimated token count, or None if API call fails
        """
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=current_app.config["GEMINI_API_KEY"])

            # Use countTokens endpoint
            response = client.models.count_tokens(model=model_name, contents=text)

            if response and hasattr(response, "total_tokens"):
                # Apply safety buffer
                buffered_tokens = math.ceil(response.total_tokens * TOKEN_ESTIMATION_SAFETY_BUFFER)
                return buffered_tokens

            return None

        except Exception as e:
            current_app.logger.warning(f"Failed to estimate tokens via API: {str(e)}")
            return None

    @staticmethod
    def estimate_tokens(text: str, model_name: str, prefer_api: bool = True) -> int:
        """
        Estimate token count, preferring API method with fallback to heuristic.

        Args:
            text: Input text
            model_name: Gemini model name
            prefer_api: Whether to try API estimation first

        Returns:
            Estimated token count
        """
        if prefer_api:
            api_estimate = JobService.estimate_tokens_api(text, model_name)
            if api_estimate is not None:
                return api_estimate

        # Fallback to heuristic
        return JobService.estimate_tokens_heuristic(text)

    @staticmethod
    def calculate_credits(tokens: int, model_name: str) -> int:
        """
        Calculate credits required for a given number of tokens.

        Args:
            tokens: Number of tokens
            model_name: Gemini model name

        Returns:
            Credits required (rounded up)
        """
        rate = JobService.get_pricing_rate(model_name)
        # Rate is per 1K tokens
        credits = math.ceil((tokens / 1000.0) * rate)
        return max(1, credits)  # Minimum 1 credit

    @staticmethod
    def create_job(
        user_id: int,
        original_filename: str,
        model_preference: str,
        estimated_tokens: int,
        processing_settings: Dict[str, Any],
    ) -> Job:
        """
        Create a new job with estimated credits.

        Args:
            user_id: User ID
            original_filename: Original PDF filename
            model_preference: User-facing model preference
            estimated_tokens: Estimated token count
            processing_settings: Processing settings snapshot

        Returns:
            Created Job
        """
        model_name = JobService.get_model_name(model_preference)
        pricing_rate = JobService.get_pricing_rate(model_name)
        estimated_credits = JobService.calculate_credits(estimated_tokens, model_name)

        job = Job(
            user_id=user_id,
            original_filename=original_filename,
            model=model_name,
            estimated_tokens=estimated_tokens,
            estimated_credits=estimated_credits,
            pricing_version=PRICING_VERSION,
            pricing_rate=pricing_rate,
            processing_settings=processing_settings,
            status=JOB_STATUS_PENDING,
        )

        db.session.add(job)
        db.session.commit()

        return job

    @staticmethod
    def start_job(job_id: int) -> bool:
        """
        Mark job as processing.

        Args:
            job_id: Job ID

        Returns:
            True if successful, False otherwise
        """
        job = Job.query.get(job_id)
        if not job or job.status != JOB_STATUS_PENDING:
            return False

        job.status = JOB_STATUS_PROCESSING
        job.started_at = datetime.now(timezone.utc)
        db.session.commit()

        return True

    @staticmethod
    def complete_job(job_id: int, actual_tokens: int, history_id: Optional[int] = None) -> Job:
        """
        Mark job as completed and record actual token usage.

        Args:
            job_id: Job ID
            actual_tokens: Actual tokens used
            history_id: Optional history entry ID to link

        Returns:
            Updated Job
        """
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = JOB_STATUS_COMPLETED
        job.actual_tokens = actual_tokens
        job.actual_credits = JobService.calculate_credits(actual_tokens, job.model)
        job.completed_at = datetime.now(timezone.utc)

        if history_id:
            job.history_id = history_id

        db.session.commit()

        return job

    @staticmethod
    def fail_job(job_id: int, error_message: str, error_code: Optional[str] = None) -> Job:
        """
        Mark job as failed.

        Args:
            job_id: Job ID
            error_message: Error message
            error_code: Optional error code

        Returns:
            Updated Job
        """
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = JOB_STATUS_FAILED
        job.error_message = error_message
        job.error_code = error_code
        job.completed_at = datetime.now(timezone.utc)

        db.session.commit()

        return job

    @staticmethod
    def cancel_job(job_id: int) -> Job:
        """
        Cancel a pending job.

        Args:
            job_id: Job ID

        Returns:
            Updated Job
        """
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.status not in [JOB_STATUS_PENDING, JOB_STATUS_PROCESSING]:
            raise ValueError(f"Cannot cancel job with status {job.status}")

        job.status = JOB_STATUS_CANCELLED
        job.completed_at = datetime.now(timezone.utc)

        db.session.commit()

        return job

    @staticmethod
    def get_job(job_id: int) -> Optional[Job]:
        """Get job by ID"""
        return Job.query.get(job_id)

    @staticmethod
    def get_user_jobs(
        user_id: int, limit: Optional[int] = None, status: Optional[str] = None
    ) -> list[Job]:
        """
        Get jobs for a user.

        Args:
            user_id: User ID
            limit: Maximum number of jobs to return
            status: Filter by status

        Returns:
            List of Jobs
        """
        query = Job.query.filter_by(user_id=user_id)

        if status:
            query = query.filter_by(status=status)

        query = query.order_by(Job.created_at.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def estimate_job_cost(
        text: str, model_preference: str, prefer_api: bool = True
    ) -> Dict[str, Any]:
        """
        Estimate cost for a job without creating it.

        Args:
            text: Input text (PDF content)
            model_preference: User-facing model preference
            prefer_api: Whether to try API estimation first

        Returns:
            Dictionary with estimation details
        """
        model_name = JobService.get_model_name(model_preference)
        estimated_tokens = JobService.estimate_tokens(text, model_name, prefer_api)
        estimated_credits = JobService.calculate_credits(estimated_tokens, model_name)
        pricing_rate = JobService.get_pricing_rate(model_name)

        return {
            "model": model_name,
            "model_preference": model_preference,
            "estimated_tokens": estimated_tokens,
            "estimated_credits": estimated_credits,
            "pricing_rate": pricing_rate,
            "pricing_version": PRICING_VERSION,
            "estimation_method": "api" if prefer_api else "heuristic",
        }

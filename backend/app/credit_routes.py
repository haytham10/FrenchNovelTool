"""Credit and job-related API routes"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app import limiter, db
from app.models import User, Job
from app.services.credit_service import CreditService
from app.services.job_service import JobService
from app.schemas import EstimateRequestSchema, JobConfirmSchema, JobFinalizeSchema
from app.constants import (
    ERROR_INSUFFICIENT_CREDITS,
    ERROR_JOB_NOT_FOUND,
    ERROR_INVALID_JOB_STATUS,
    JOB_STATUS_PENDING,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED
)

credit_bp = Blueprint('credits', __name__)

# Initialize schemas
estimate_schema = EstimateRequestSchema()
job_confirm_schema = JobConfirmSchema()
job_finalize_schema = JobFinalizeSchema()


@credit_bp.route('/me/credits', methods=['GET'])
@jwt_required()
def get_credits():
    """
    Get current user's credit balance and summary.
    
    Returns:
        {
            'balance': int,
            'granted': int,
            'used': int,
            'refunded': int,
            'adjusted': int,
            'month': str,
            'next_reset': str
        }
    """
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Get credit summary
        summary = CreditService.get_credit_summary(user_id)
        
        return jsonify(summary), 200
        
    except Exception as e:
        current_app.logger.exception('Failed to get credits')
        return jsonify({'error': str(e)}), 500


@credit_bp.route('/estimate', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
def estimate_cost():
    """
    Estimate credit cost for processing text.
    
    Request:
        {
            'text': str,
            'model_preference': 'balanced' | 'quality' | 'speed'
        }
    
    Returns:
        {
            'model': str,
            'model_preference': str,
            'estimated_tokens': int,
            'estimated_credits': int,
            'pricing_rate': float,
            'pricing_version': str,
            'estimation_method': str,
            'current_balance': int,
            'allowed': bool,
            'message': str (optional)
        }
    """
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Validate request
        try:
            data = estimate_schema.load(request.json)
        except ValidationError as e:
            return jsonify({'error': 'Invalid request data', 'details': e.messages}), 400
        
        text = data['text']
        model_preference = data['model_preference']
        
        # Get cost estimate
        estimate = JobService.estimate_job_cost(text, model_preference, prefer_api=True)
        
        # Get current balance
        summary = CreditService.get_credit_summary(user_id)
        current_balance = summary['balance']
        
        # Check if user can afford it
        estimated_credits = estimate['estimated_credits']
        allowed = current_balance >= estimated_credits
        
        response = {
            **estimate,
            'current_balance': current_balance,
            'allowed': allowed
        }
        
        if not allowed:
            response['message'] = f'Insufficient credits. Required: {estimated_credits}, Available: {current_balance}'
        
        return jsonify(response), 200
        
    except Exception as e:
        current_app.logger.exception('Failed to estimate cost')
        return jsonify({'error': str(e)}), 500


@credit_bp.route('/jobs/confirm', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def confirm_job():
    """
    Confirm a job and reserve credits.
    This is called after user sees the estimate and confirms.
    
    Request:
        {
            'estimated_credits': int,
            'model_preference': str,
            'processing_settings': dict (optional)
        }
    
    Returns:
        {
            'job_id': int,
            'status': str,
            'estimated_credits': int,
            'reserved': bool,
            'message': str
        }
    """
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Validate request
        try:
            data = job_confirm_schema.load(request.json)
        except ValidationError as e:
            return jsonify({'error': 'Invalid request data', 'details': e.messages}), 400
        
        estimated_credits = data['estimated_credits']
        model_preference = data['model_preference']
        processing_settings = data.get('processing_settings', {})
        original_filename = processing_settings.get('original_filename', 'unknown.pdf')
        estimated_tokens = processing_settings.get('estimated_tokens', 0)
        
        # Create job first (without reserving credits yet)
        job = JobService.create_job(
            user_id=user_id,
            original_filename=original_filename,
            model_preference=model_preference,
            estimated_tokens=estimated_tokens,
            processing_settings=processing_settings
        )
        
        # Reserve credits with race condition protection
        success, error_message = CreditService.reserve_credits(
            user_id=user_id,
            job_id=job.id,
            amount=estimated_credits,
            description=f'Reserved for {original_filename}'
        )
        
        if not success:
            # Delete the job if credit reservation failed
            db.session.delete(job)
            db.session.commit()
            
            return jsonify({
                'error': error_message,
                'error_code': ERROR_INSUFFICIENT_CREDITS,
                'reserved': False
            }), 402  # Payment Required
        
        current_app.logger.info(f'User {user.email} confirmed job {job.id}, reserved {estimated_credits} credits')
        
        return jsonify({
            'job_id': job.id,
            'status': job.status,
            'estimated_credits': estimated_credits,
            'reserved': True,
            'message': 'Credits reserved successfully'
        }), 201
        
    except Exception as e:
        current_app.logger.exception('Failed to confirm job')
        return jsonify({'error': str(e)}), 500


@credit_bp.route('/jobs/<int:job_id>/finalize', methods=['POST'])
@jwt_required()
def finalize_job(job_id):
    """
    Finalize a job after processing completes.
    Adjusts credits based on actual usage or refunds on failure.
    
    Request:
        {
            'actual_tokens': int,
            'success': bool,
            'error_message': str (optional),
            'error_code': str (optional)
        }
    
    Returns:
        {
            'job_id': int,
            'status': str,
            'estimated_credits': int,
            'actual_credits': int,
            'adjustment': int,
            'refunded': bool,
            'message': str
        }
    """
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Validate request
        try:
            data = job_finalize_schema.load(request.json)
        except ValidationError as e:
            return jsonify({'error': 'Invalid request data', 'details': e.messages}), 400
        
        # Get job
        job = Job.query.get(job_id)
        if not job:
            return jsonify({'error': 'Job not found', 'error_code': ERROR_JOB_NOT_FOUND}), 404
        
        # Verify ownership
        if job.user_id != user_id:
            return jsonify({'error': 'Not authorized to finalize this job'}), 403
        
        # Verify job status
        if job.status not in [JOB_STATUS_PENDING, JOB_STATUS_PROCESSING]:
            return jsonify({
                'error': f'Cannot finalize job with status {job.status}',
                'error_code': ERROR_INVALID_JOB_STATUS
            }), 400
        
        actual_tokens = data['actual_tokens']
        success = data['success']
        error_message = data.get('error_message')
        error_code = data.get('error_code')
        
        if success:
            # Complete job successfully
            job = JobService.complete_job(job_id, actual_tokens)
            
            # Adjust credits (refund if actual < estimated, charge more if actual > estimated)
            adjustment_entry = CreditService.adjust_final_credits(
                user_id=user_id,
                job_id=job_id,
                reserved_amount=job.estimated_credits,
                actual_amount=job.actual_credits
            )
            
            adjustment = adjustment_entry.delta_credits if adjustment_entry else 0
            
            current_app.logger.info(
                f'User {user.email} finalized job {job_id} successfully. '
                f'Estimated: {job.estimated_credits}, Actual: {job.actual_credits}, Adjustment: {adjustment}'
            )
            
            return jsonify({
                'job_id': job.id,
                'status': job.status,
                'estimated_credits': job.estimated_credits,
                'actual_credits': job.actual_credits,
                'adjustment': adjustment,
                'refunded': False,
                'message': 'Job finalized successfully'
            }), 200
        else:
            # Fail job and refund credits
            job = JobService.fail_job(job_id, error_message or 'Processing failed', error_code)
            
            # Refund all reserved credits
            refund_entry = CreditService.refund_credits(
                user_id=user_id,
                job_id=job_id,
                amount=job.estimated_credits,
                description=f'Refund for failed job: {error_message or "Processing failed"}'
            )
            
            current_app.logger.info(
                f'User {user.email} finalized job {job_id} as failed. '
                f'Refunded {job.estimated_credits} credits'
            )
            
            return jsonify({
                'job_id': job.id,
                'status': job.status,
                'estimated_credits': job.estimated_credits,
                'actual_credits': 0,
                'adjustment': 0,
                'refunded': True,
                'refund_amount': job.estimated_credits,
                'message': 'Job failed, credits refunded'
            }), 200
        
    except Exception as e:
        current_app.logger.exception(f'Failed to finalize job {job_id}')
        return jsonify({'error': str(e)}), 500


@credit_bp.route('/jobs/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    """Get job details"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        job = Job.query.get(job_id)
        if not job:
            return jsonify({'error': 'Job not found', 'error_code': ERROR_JOB_NOT_FOUND}), 404
        
        # Verify ownership
        if job.user_id != user_id:
            return jsonify({'error': 'Not authorized to view this job'}), 403
        
        return jsonify(job.to_dict()), 200
        
    except Exception as e:
        current_app.logger.exception(f'Failed to get job {job_id}')
        return jsonify({'error': str(e)}), 500


@credit_bp.route('/jobs', methods=['GET'])
@jwt_required()
def get_jobs():
    """Get user's jobs"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        limit = request.args.get('limit', type=int)
        status = request.args.get('status', type=str)
        
        jobs = JobService.get_user_jobs(user_id, limit=limit, status=status)
        
        return jsonify([job.to_dict() for job in jobs]), 200
        
    except Exception as e:
        current_app.logger.exception('Failed to get jobs')
        return jsonify({'error': str(e)}), 500


@credit_bp.route('/credits/ledger', methods=['GET'])
@jwt_required()
def get_ledger():
    """Get user's credit ledger entries"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        month = request.args.get('month', type=str)
        limit = request.args.get('limit', type=int)
        
        entries = CreditService.get_ledger_entries(user_id, month=month, limit=limit)
        
        return jsonify([entry.to_dict() for entry in entries]), 200
        
    except Exception as e:
        current_app.logger.exception('Failed to get ledger')
        return jsonify({'error': str(e)}), 500

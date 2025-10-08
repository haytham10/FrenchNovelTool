"""WebSocket event handlers for real-time job updates"""
from flask import request
from flask_socketio import emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
from jwt import ExpiredSignatureError, InvalidTokenError
from app import socketio
from app.models import Job, CoverageRun
import logging

logger = logging.getLogger(__name__)


def emit_job_progress(job_id: int):
    """Emit job progress update to all clients subscribed to this job
    
    Args:
        job_id: ID of the job to emit progress for
    """
    try:
        job = Job.query.get(job_id)
        if job:
            room = f'job_{job_id}'
            socketio.emit('job_progress', job.to_dict(), room=room)
            logger.debug(f'Emitted job_progress for job {job_id}: {job.progress_percent}% - {job.current_step}')
    except Exception as e:
        logger.error(f'Error emitting job progress for job {job_id}: {e}')


def emit_coverage_progress(run_id: int):
    """Emit coverage run progress update to clients subscribed to this run"""
    try:
        run = CoverageRun.query.get(run_id)
        if run:
            room = f'coverage_run_{run_id}'
            socketio.emit('coverage_progress', run.to_dict(), room=room)
            logger.debug(f'Emitted coverage_progress for run {run_id}: {run.progress_percent}% - {run.status}')
    except Exception as e:
        logger.error(f'Error emitting coverage progress for run {run_id}: {e}')


@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection with JWT authentication"""
    try:
        # Extract JWT from auth dict or query string
        token = auth.get('token') if auth else request.args.get('token')
        
        if not token:
            logger.warning('WebSocket connection attempt without token')
            disconnect()
            return False
        
        # Verify JWT token
        try:
            decoded = decode_token(token)
        except ExpiredSignatureError:
            logger.info('WebSocket auth failed: token expired')
            # Client should refresh their access token and reconnect
            disconnect()
            return False
        except InvalidTokenError as e:
            logger.warning(f'WebSocket auth failed: invalid token: {e}')
            disconnect()
            return False

        user_id = int(decoded['sub'])

        logger.info(f'WebSocket connected: user_id={user_id}')
        return True

    except Exception as e:
        logger.error(f'WebSocket auth failed: {e}')
        disconnect()
        return False


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect"""
    logger.info('WebSocket client disconnected')


@socketio.on('join_job')
def handle_join_job(data):
    """Subscribe client to job-specific room for progress updates
    
    Args:
        data: {'job_id': int, 'token': str}
    """
    try:
        job_id = data.get('job_id')
        token = data.get('token')
        
        if not job_id or not token:
            emit('error', {'message': 'Missing job_id or token'})
            return
        
        # Verify user owns this job
        try:
            decoded = decode_token(token)
            user_id = int(decoded['sub'])
        except ExpiredSignatureError:
            emit('error', {'message': 'token_expired'})
            return
        except InvalidTokenError:
            emit('error', {'message': 'invalid_token'})
            return
        
        job = Job.query.get(job_id)
        if not job:
            emit('error', {'message': f'Job {job_id} not found'})
            return
            
        if job.user_id != user_id:
            emit('error', {'message': 'Unauthorized access to job'})
            return
        
        # Join job-specific room
        room = f'job_{job_id}'
        join_room(room)
        
        logger.info(f'User {user_id} joined room {room}')
        
        # Send initial job state
        emit('job_progress', job.to_dict(), room=room)
        
    except Exception as e:
        logger.error(f'Error joining job room: {e}')
        emit('error', {'message': 'Failed to join job room'})


@socketio.on('join_coverage_run')
def handle_join_coverage_run(data):
    """Subscribe client to coverage-run-specific room for progress updates"""
    try:
        run_id = data.get('run_id')
        token = data.get('token')

        if not run_id or not token:
            emit('error', {'message': 'Missing run_id or token'})
            return

        # Verify user owns this run
        try:
            decoded = decode_token(token)
            user_id = int(decoded['sub'])
        except ExpiredSignatureError:
            emit('error', {'message': 'token_expired'})
            return
        except InvalidTokenError:
            emit('error', {'message': 'invalid_token'})
            return

        run = CoverageRun.query.get(run_id)
        if not run:
            emit('error', {'message': f'CoverageRun {run_id} not found'})
            return

        if run.user_id != user_id:
            emit('error', {'message': 'Unauthorized access to coverage run'})
            return

        # Join coverage-run-specific room
        room = f'coverage_run_{run_id}'
        join_room(room)

        logger.info(f'User {user_id} joined room {room}')

        # Send initial run state
        emit('coverage_progress', run.to_dict(), room=room)

    except Exception as e:
        logger.error(f'Error joining coverage run room: {e}')
        emit('error', {'message': 'Failed to join coverage run room'})


@socketio.on('leave_coverage_run')
def handle_leave_coverage_run(data):
    """Unsubscribe client from coverage run room"""
    try:
        run_id = data.get('run_id')

        if not run_id:
            emit('error', {'message': 'Missing run_id'})
            return

        room = f'coverage_run_{run_id}'
        leave_room(room)

        logger.info(f'Client left room {room}')

    except Exception as e:
        logger.error(f'Error leaving coverage run room: {e}')
        emit('error', {'message': 'Failed to leave coverage run room'})


@socketio.on('leave_job')
def handle_leave_job(data):
    """Unsubscribe client from job room
    
    Args:
        data: {'job_id': int}
    """
    try:
        job_id = data.get('job_id')
        
        if not job_id:
            emit('error', {'message': 'Missing job_id'})
            return
        
        room = f'job_{job_id}'
        leave_room(room)
        
        logger.info(f'Client left room {room}')
        
    except Exception as e:
        logger.error(f'Error leaving job room: {e}')
        emit('error', {'message': 'Failed to leave job room'})

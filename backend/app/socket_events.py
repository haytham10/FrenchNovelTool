"""WebSocket event handlers for real-time job updates"""
from flask import request
from flask_socketio import emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
from app import socketio
from app.models import Job
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
        decoded = decode_token(token)
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
        decoded = decode_token(token)
        user_id = int(decoded['sub'])
        
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

"""
Monitoring utilities for Project Battleship structured logging.

Provides tools to aggregate, query, and analyze structured logs for:
- Fragment rate monitoring across jobs
- Error aggregation by category
- Performance metrics collection
- Quality gate effectiveness tracking
"""
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass

try:
    from flask import current_app
    from app.models import Job, JobChunk, History
    from app import db
except ImportError:
    # Handle case where Flask/SQLAlchemy not available
    current_app = None
    Job = JobChunk = History = db = None


@dataclass
class FragmentRateMetric:
    """Fragment rate metrics for a specific job or time period."""
    job_id: Optional[int]
    fragment_rate: float
    fragment_count: int
    total_sentences: int
    timestamp: datetime
    model_name: str
    processing_settings: Dict[str, Any]


@dataclass
class ErrorMetric:
    """Error metrics with context."""
    error_category: str
    error_count: int
    job_ids: List[int]
    error_messages: List[str]
    first_occurrence: datetime
    last_occurrence: datetime


@dataclass
class PerformanceMetric:
    """Performance metrics."""
    metric_name: str
    avg_value: float
    min_value: float
    max_value: float
    sample_count: int
    unit: str


class LogAnalyzer:
    """
    Analyze structured logs from Project Battleship.
    
    Note: In production, logs are typically streamed to Railway logs or external
    systems. This analyzer works with data stored in the database processing_metadata
    field and provides utilities for log aggregation.
    """
    
    def __init__(self):
        """Initialize log analyzer."""
        self.db = db
    
    def get_fragment_rate_history(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None
    ) -> List[FragmentRateMetric]:
        """
        Get fragment rate history from job processing metadata.
        
        Args:
            start_date: Start date for filtering (default: 7 days ago)
            end_date: End date for filtering (default: now)
            user_id: Filter by specific user ID
            
        Returns:
            List of FragmentRateMetric objects
        """
        if not self.db or not Job:
            return []
        
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.utcnow()
        
        query = Job.query.filter(
            Job.completed_at.between(start_date, end_date),
            Job.status == 'completed',
            Job.processing_metadata.isnot(None)
        )
        
        if user_id:
            query = query.filter(Job.user_id == user_id)
        
        jobs = query.all()
        metrics = []
        
        for job in jobs:
            metadata = job.processing_metadata or {}
            fragment_data = metadata.get('fragment_analysis', {})
            
            if fragment_data:
                metrics.append(FragmentRateMetric(
                    job_id=job.id,
                    fragment_rate=fragment_data.get('fragment_rate', 0.0),
                    fragment_count=fragment_data.get('fragment_count', 0),
                    total_sentences=fragment_data.get('total_sentences', 0),
                    timestamp=job.completed_at,
                    model_name=job.model,
                    processing_settings=job.processing_settings or {}
                ))
        
        return sorted(metrics, key=lambda x: x.timestamp)
    
    def get_error_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        error_category: Optional[str] = None
    ) -> List[ErrorMetric]:
        """
        Get error summary from job processing metadata and chunk errors.
        
        Args:
            start_date: Start date for filtering (default: 24 hours ago)
            end_date: End date for filtering (default: now)
            error_category: Filter by specific error category
            
        Returns:
            List of ErrorMetric objects grouped by error category
        """
        if not self.db or not Job:
            return []
        
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(hours=24)
        if end_date is None:
            end_date = datetime.utcnow()
        
        # Get job-level errors
        job_errors = defaultdict(lambda: {
            'count': 0,
            'job_ids': set(),
            'messages': [],
            'first': None,
            'last': None
        })
        
        failed_jobs = Job.query.filter(
            Job.updated_at.between(start_date, end_date),
            Job.status == 'failed',
            Job.error_code.isnot(None)
        ).all()
        
        for job in failed_jobs:
            category = job.error_code or 'UNKNOWN_ERROR'
            if error_category and category != error_category:
                continue
                
            job_errors[category]['count'] += 1
            job_errors[category]['job_ids'].add(job.id)
            job_errors[category]['messages'].append(job.error_message or '')
            
            timestamp = job.updated_at
            if not job_errors[category]['first'] or timestamp < job_errors[category]['first']:
                job_errors[category]['first'] = timestamp
            if not job_errors[category]['last'] or timestamp > job_errors[category]['last']:
                job_errors[category]['last'] = timestamp
        
        # Get chunk-level errors
        if JobChunk:
            failed_chunks = JobChunk.query.filter(
                JobChunk.updated_at.between(start_date, end_date),
                JobChunk.status == 'failed',
                JobChunk.last_error_code.isnot(None)
            ).all()
            
            for chunk in failed_chunks:
                category = chunk.last_error_code or 'UNKNOWN_CHUNK_ERROR'
                if error_category and category != error_category:
                    continue
                    
                job_errors[category]['count'] += 1
                job_errors[category]['job_ids'].add(chunk.job_id)
                job_errors[category]['messages'].append(chunk.last_error or '')
                
                timestamp = chunk.updated_at
                if not job_errors[category]['first'] or timestamp < job_errors[category]['first']:
                    job_errors[category]['first'] = timestamp
                if not job_errors[category]['last'] or timestamp > job_errors[category]['last']:
                    job_errors[category]['last'] = timestamp
        
        # Convert to ErrorMetric objects
        metrics = []
        for category, data in job_errors.items():
            metrics.append(ErrorMetric(
                error_category=category,
                error_count=data['count'],
                job_ids=list(data['job_ids']),
                error_messages=data['messages'][:10],  # Limit to first 10 messages
                first_occurrence=data['first'],
                last_occurrence=data['last']
            ))
        
        return sorted(metrics, key=lambda x: x.error_count, reverse=True)
    
    def get_performance_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PerformanceMetric]:
        """
        Get performance metrics from job processing metadata.
        
        Args:
            start_date: Start date for filtering (default: 24 hours ago)
            end_date: End date for filtering (default: now)
            
        Returns:
            List of PerformanceMetric objects
        """
        if not self.db or not Job:
            return []
        
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(hours=24)
        if end_date is None:
            end_date = datetime.utcnow()
        
        jobs = Job.query.filter(
            Job.completed_at.between(start_date, end_date),
            Job.status == 'completed',
            Job.processing_metadata.isnot(None)
        ).all()
        
        # Aggregate performance metrics
        metrics_data = defaultdict(list)
        
        for job in jobs:
            metadata = job.processing_metadata or {}
            
            # Processing time
            if job.processing_time_seconds:
                metrics_data['processing_time'].append(job.processing_time_seconds)
            
            # API calls per job
            if job.gemini_api_calls:
                metrics_data['gemini_api_calls'].append(job.gemini_api_calls)
            
            # Tokens per job
            if job.gemini_tokens_used:
                metrics_data['gemini_tokens_used'].append(job.gemini_tokens_used)
            
            # Extract performance metrics from metadata
            perf_data = metadata.get('performance_metrics', {})
            for metric_name, values in perf_data.items():
                if isinstance(values, list):
                    metrics_data[metric_name].extend(values)
                elif isinstance(values, (int, float)):
                    metrics_data[metric_name].append(values)
        
        # Convert to PerformanceMetric objects
        performance_metrics = []
        metric_units = {
            'processing_time': 'seconds',
            'gemini_api_calls': 'count',
            'gemini_tokens_used': 'tokens',
            'memory_usage': 'kib',
            'fragment_rate': 'percent'
        }
        
        for metric_name, values in metrics_data.items():
            if values:
                performance_metrics.append(PerformanceMetric(
                    metric_name=metric_name,
                    avg_value=sum(values) / len(values),
                    min_value=min(values),
                    max_value=max(values),
                    sample_count=len(values),
                    unit=metric_units.get(metric_name, 'unknown')
                ))
        
        return sorted(performance_metrics, key=lambda x: x.metric_name)
    
    def get_quality_gate_effectiveness(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Analyze Quality Gate effectiveness from processing metadata.
        
        Args:
            start_date: Start date for filtering (default: 7 days ago)
            end_date: End date for filtering (default: now)
            
        Returns:
            Dict with quality gate statistics
        """
        if not self.db or not Job:
            return {}
        
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.utcnow()
        
        jobs = Job.query.filter(
            Job.completed_at.between(start_date, end_date),
            Job.status == 'completed',
            Job.processing_metadata.isnot(None)
        ).all()
        
        total_jobs = len(jobs)
        quality_gate_enabled_jobs = 0
        total_sentences = 0
        total_rejections = 0
        rejection_reasons = Counter()
        fragment_rates = []
        
        for job in jobs:
            metadata = job.processing_metadata or {}
            
            # Check if Quality Gate was enabled
            settings = job.processing_settings or {}
            if settings.get('quality_gate_enabled', True):  # Default True for new system
                quality_gate_enabled_jobs += 1
            
            # Aggregate Quality Gate statistics
            qg_data = metadata.get('quality_gate', {})
            if qg_data:
                total_sentences += qg_data.get('total_sentences', 0)
                total_rejections += qg_data.get('rejections', 0)
                
                for reason, count in qg_data.get('rejection_reasons', {}).items():
                    rejection_reasons[reason] += count
            
            # Fragment rate data
            fragment_data = metadata.get('fragment_analysis', {})
            if fragment_data and fragment_data.get('total_sentences', 0) > 0:
                fragment_rates.append(fragment_data.get('fragment_rate', 0.0))
        
        # Calculate statistics
        avg_fragment_rate = sum(fragment_rates) / len(fragment_rates) if fragment_rates else 0.0
        rejection_rate = (total_rejections / total_sentences) if total_sentences > 0 else 0.0
        
        return {
            'total_jobs_analyzed': total_jobs,
            'quality_gate_enabled_jobs': quality_gate_enabled_jobs,
            'quality_gate_adoption_rate': quality_gate_enabled_jobs / total_jobs if total_jobs > 0 else 0.0,
            'total_sentences_processed': total_sentences,
            'total_sentences_rejected': total_rejections,
            'sentence_rejection_rate': rejection_rate,
            'rejection_reasons': dict(rejection_reasons.most_common(10)),
            'average_fragment_rate': avg_fragment_rate,
            'fragment_rate_distribution': {
                'excellent': len([r for r in fragment_rates if r < 0.5]),
                'good': len([r for r in fragment_rates if 0.5 <= r < 1.0]),
                'acceptable': len([r for r in fragment_rates if 1.0 <= r < 3.0]),
                'poor': len([r for r in fragment_rates if r >= 3.0])
            },
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        }
    
    def update_job_metadata(
        self,
        job_id: int,
        fragment_analysis: Optional[Dict[str, Any]] = None,
        quality_gate: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Update job processing metadata for monitoring.
        
        Args:
            job_id: Job ID to update
            fragment_analysis: Fragment rate analysis data
            quality_gate: Quality gate statistics
            performance_metrics: Performance metrics
            errors: Error context data
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db or not Job:
            return False
        
        try:
            job = Job.query.get(job_id)
            if not job:
                return False
            
            # Initialize or update metadata
            metadata = job.processing_metadata or {}
            
            if fragment_analysis:
                metadata['fragment_analysis'] = fragment_analysis
            
            if quality_gate:
                metadata['quality_gate'] = quality_gate
            
            if performance_metrics:
                metadata['performance_metrics'] = performance_metrics
            
            if errors:
                metadata.setdefault('errors', []).extend(errors)
            
            # Add update timestamp
            metadata['last_updated'] = datetime.utcnow().isoformat()
            
            job.processing_metadata = metadata
            self.db.session.commit()
            
            return True
            
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Failed to update job metadata: {e}")
            self.db.session.rollback()
            return False


class LogQueryBuilder:
    """
    Build queries for log analysis from structured logs.
    
    Note: This is designed for external log systems (Railway, Sentry).
    For database-stored metadata, use LogAnalyzer instead.
    """
    
    @staticmethod
    def build_fragment_rate_query(
        job_id: Optional[int] = None,
        min_fragment_rate: Optional[float] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> str:
        """
        Build query string for fragment rate logs.
        
        Args:
            job_id: Filter by specific job ID
            min_fragment_rate: Minimum fragment rate threshold
            time_range: (start_date, end_date) tuple
            
        Returns:
            Query string for log aggregation systems
        """
        conditions = ['metric_type:"fragment_rate"']
        
        if job_id:
            conditions.append(f'job_id:{job_id}')
        
        if min_fragment_rate is not None:
            conditions.append(f'fragment_rate_percent:>={min_fragment_rate}')
        
        if time_range:
            start_str = time_range[0].isoformat()
            end_str = time_range[1].isoformat()
            conditions.append(f'timestamp:[{start_str} TO {end_str}]')
        
        return ' AND '.join(conditions)
    
    @staticmethod
    def build_error_query(
        error_category: Optional[str] = None,
        job_id: Optional[int] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> str:
        """
        Build query string for error logs.
        
        Args:
            error_category: Filter by error category
            job_id: Filter by specific job ID
            time_range: (start_date, end_date) tuple
            
        Returns:
            Query string for log aggregation systems
        """
        conditions = ['level:ERROR']
        
        if error_category:
            conditions.append(f'error_category:"{error_category}"')
        
        if job_id:
            conditions.append(f'job_id:{job_id}')
        
        if time_range:
            start_str = time_range[0].isoformat()
            end_str = time_range[1].isoformat()
            conditions.append(f'timestamp:[{start_str} TO {end_str}]')
        
        return ' AND '.join(conditions)
    
    @staticmethod
    def build_performance_query(
        metric_name: str,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> str:
        """
        Build query string for performance metric logs.
        
        Args:
            metric_name: Name of the performance metric
            time_range: (start_date, end_date) tuple
            
        Returns:
            Query string for log aggregation systems
        """
        conditions = [
            'metric_type:"performance"',
            f'metric_name:"{metric_name}"'
        ]
        
        if time_range:
            start_str = time_range[0].isoformat()
            end_str = time_range[1].isoformat()
            conditions.append(f'timestamp:[{start_str} TO {end_str}]')
        
        return ' AND '.join(conditions)


# Global instance for easy access
log_analyzer = LogAnalyzer()


def get_fragment_rate_dashboard_data(
    days: int = 7,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get fragment rate dashboard data for the frontend.
    
    Args:
        days: Number of days to look back
        user_id: Filter by specific user ID
        
    Returns:
        Dashboard data dict
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    fragment_metrics = log_analyzer.get_fragment_rate_history(
        start_date=start_date,
        user_id=user_id
    )
    
    if not fragment_metrics:
        return {
            'total_jobs': 0,
            'average_fragment_rate': 0.0,
            'trend': 'stable',
            'daily_stats': [],
            'model_performance': {},
            'quality_improvement': 0.0
        }
    
    # Calculate daily aggregates
    daily_stats = defaultdict(lambda: {'jobs': 0, 'total_fragments': 0, 'total_sentences': 0})
    model_performance = defaultdict(lambda: {'jobs': 0, 'total_fragments': 0, 'total_sentences': 0})
    
    for metric in fragment_metrics:
        date_key = metric.timestamp.date().isoformat()
        daily_stats[date_key]['jobs'] += 1
        daily_stats[date_key]['total_fragments'] += metric.fragment_count
        daily_stats[date_key]['total_sentences'] += metric.total_sentences
        
        model_performance[metric.model_name]['jobs'] += 1
        model_performance[metric.model_name]['total_fragments'] += metric.fragment_count
        model_performance[metric.model_name]['total_sentences'] += metric.total_sentences
    
    # Calculate rates
    daily_data = []
    for date_str, stats in sorted(daily_stats.items()):
        rate = (stats['total_fragments'] / stats['total_sentences'] * 100) if stats['total_sentences'] > 0 else 0
        daily_data.append({
            'date': date_str,
            'fragment_rate': round(rate, 2),
            'jobs': stats['jobs'],
            'total_sentences': stats['total_sentences']
        })
    
    model_data = {}
    for model, stats in model_performance.items():
        rate = (stats['total_fragments'] / stats['total_sentences'] * 100) if stats['total_sentences'] > 0 else 0
        model_data[model] = {
            'fragment_rate': round(rate, 2),
            'jobs': stats['jobs'],
            'total_sentences': stats['total_sentences']
        }
    
    # Calculate trend
    if len(daily_data) >= 2:
        recent_rate = sum(d['fragment_rate'] for d in daily_data[-3:]) / min(3, len(daily_data))
        older_rate = sum(d['fragment_rate'] for d in daily_data[:-3]) / max(1, len(daily_data) - 3)
        
        if recent_rate < older_rate * 0.8:
            trend = 'improving'
        elif recent_rate > older_rate * 1.2:
            trend = 'degrading'
        else:
            trend = 'stable'
    else:
        trend = 'stable'
    
    avg_rate = sum(m.fragment_rate for m in fragment_metrics) / len(fragment_metrics)
    
    return {
        'total_jobs': len(fragment_metrics),
        'average_fragment_rate': round(avg_rate, 2),
        'trend': trend,
        'daily_stats': daily_data,
        'model_performance': model_data,
        'quality_improvement': max(0, 3.0 - avg_rate),  # Improvement from 3% baseline
        'period_days': days
    }
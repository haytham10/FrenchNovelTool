"""Prometheus metrics for monitoring Vocabulary Coverage Tool"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Coverage run metrics
coverage_runs_total = Counter(
    'coverage_runs_total',
    'Total number of coverage runs',
    ['mode', 'status']  # coverage/filter, completed/failed/cancelled
)

coverage_build_duration_seconds = Histogram(
    'coverage_build_duration_seconds',
    'Time to build coverage analysis',
    ['mode'],  # coverage/filter
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]  # Up to 10 minutes
)

# Word list metrics
wordlists_total = Gauge(
    'wordlists_total',
    'Total number of word lists',
    ['source_type', 'is_global']  # csv/google_sheet/manual, true/false
)

wordlists_created_total = Counter(
    'wordlists_created_total',
    'Total number of word lists created',
    ['source_type']  # csv/google_sheet/manual
)

# Coverage assignment metrics
coverage_assignments_total = Gauge(
    'coverage_assignments_total',
    'Total number of coverage assignments',
    ['mode']  # coverage/filter
)

# Word list operations
wordlist_ingestion_errors_total = Counter(
    'wordlist_ingestion_errors_total',
    'Total number of word list ingestion errors',
    ['source_type', 'error_type']
)


def generate_metrics():
    """Generate Prometheus metrics in text format"""
    return generate_latest()


def get_content_type():
    """Get content type for Prometheus metrics"""
    return CONTENT_TYPE_LATEST

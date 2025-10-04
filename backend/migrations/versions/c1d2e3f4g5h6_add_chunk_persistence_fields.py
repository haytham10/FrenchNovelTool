"""add chunk persistence fields

Revision ID: c1d2e3f4g5h6
Revises: ba1e2c3d4f56
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'ba1e2c3d4f56'
branch_labels = None
depends_on = None


def upgrade():
    """Add persistence and retry tracking fields to job_chunks table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Helper to check if column exists
    def column_exists(table_name: str, column_name: str) -> bool:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    
    # Helper to check if index exists
    def index_exists(name: str) -> bool:
        try:
            return bool(bind.execute(sa.text("SELECT to_regclass(:iname)"), {'iname': f'public.{name}'}).scalar())
        except Exception:
            return False
    
    # Only add columns if they don't exist (idempotent migration)
    columns_to_add = [
        ('page_count', sa.Integer()),
        ('has_overlap', sa.Boolean(), {'server_default': 'false'}),
        ('storage_url', sa.String(512)),
        ('celery_task_id', sa.String(155)),
        ('max_retries', sa.Integer(), {'server_default': '3'}),
        ('last_error_code', sa.String(50)),
        ('result_json', postgresql.JSON()),
        ('processed_at', sa.DateTime()),
    ]
    
    for col_info in columns_to_add:
        col_name = col_info[0]
        col_type = col_info[1]
        kwargs = col_info[2] if len(col_info) > 2 else {}
        
        if not column_exists('job_chunks', col_name):
            op.add_column('job_chunks', sa.Column(col_name, col_type, **kwargs))
    
    # Rename chunk_index to chunk_id if needed
    if column_exists('job_chunks', 'chunk_index') and not column_exists('job_chunks', 'chunk_id'):
        op.alter_column('job_chunks', 'chunk_index', new_column_name='chunk_id')
    
    # Add composite index if not exists
    if not index_exists('idx_job_chunks_job_status'):
        op.create_index(
            'idx_job_chunks_job_status',
            'job_chunks',
            ['job_id', 'status']
        )


def downgrade():
    """Remove persistence fields from job_chunks table"""
    bind = op.get_bind()
    
    # Drop index
    def index_exists(name: str) -> bool:
        try:
            return bool(bind.execute(sa.text("SELECT to_regclass(:iname)"), {'iname': f'public.{name}'}).scalar())
        except Exception:
            return False
    
    if index_exists('idx_job_chunks_job_status'):
        op.drop_index('idx_job_chunks_job_status', table_name='job_chunks')
    
    # Rename chunk_id back to chunk_index
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('job_chunks')]
    
    if 'chunk_id' in columns and 'chunk_index' not in columns:
        op.alter_column('job_chunks', 'chunk_id', new_column_name='chunk_index')
    
    # Drop added columns
    columns_to_drop = [
        'page_count', 'has_overlap', 'storage_url', 'celery_task_id',
        'max_retries', 'last_error_code', 'result_json', 'processed_at'
    ]
    
    for col in columns_to_drop:
        if col in columns:
            op.drop_column('job_chunks', col)

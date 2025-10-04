"""add job_chunks table

Revision ID: ba1e2c3d4f56
Revises: 48fd2dc76953
Create Date: 2025-10-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ba1e2c3d4f56'
down_revision = '48fd2dc76953'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Helper to check index existence using Postgres to_regclass
    def index_exists(name: str) -> bool:
        try:
            return bool(bind.execute(sa.text("SELECT to_regclass(:iname)"), {'iname': f'public.{name}'}).scalar())
        except Exception:
            # If the DB doesn't support to_regclass, fall back to inspector
            return False

    table_exists = 'job_chunks' in inspector.get_table_names()

    # Create table if missing
    if not table_exists:
        op.create_table(
            'job_chunks',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id'), nullable=False, index=True),
            sa.Column('chunk_index', sa.Integer(), nullable=False),
            sa.Column('file_b64', sa.Text(), nullable=True),
            sa.Column('file_url', sa.String(length=512), nullable=True),
            sa.Column('file_size_bytes', sa.Integer(), nullable=True),
            sa.Column('start_page', sa.Integer(), nullable=False),
            sa.Column('end_page', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    # Ensure indexes exist, create them only if missing
    if not index_exists('ix_job_chunks_job_id'):
        op.create_index('ix_job_chunks_job_id', 'job_chunks', ['job_id'])
    if not index_exists('ix_job_chunks_status'):
        op.create_index('ix_job_chunks_status', 'job_chunks', ['status'])
    if not index_exists('idx_job_chunk_unique'):
        op.create_index('idx_job_chunk_unique', 'job_chunks', ['job_id', 'chunk_index'], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'job_chunks' in inspector.get_table_names():
        # Use to_regclass to check index existence before dropping.
        get_index = lambda name: bind.execute(sa.text("SELECT to_regclass(:iname)"), {'iname': f'public.{name}'}).scalar()
        if get_index('idx_job_chunk_unique'):
            op.drop_index('idx_job_chunk_unique', table_name='job_chunks')
        if get_index('ix_job_chunks_status'):
            op.drop_index('ix_job_chunks_status', table_name='job_chunks')
        if get_index('ix_job_chunks_job_id'):
            op.drop_index('ix_job_chunks_job_id', table_name='job_chunks')
        op.drop_table('job_chunks')

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
    # If the table doesn't exist, create it and the indexes
    if 'job_chunks' not in inspector.get_table_names():
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
        op.create_index('ix_job_chunks_job_id', 'job_chunks', ['job_id'])
        op.create_index('ix_job_chunks_status', 'job_chunks', ['status'])
        op.create_index('idx_job_chunk_unique', 'job_chunks', ['job_id', 'chunk_index'], unique=True)
    else:
        # Table exists (partial migration ran before). Ensure indexes exist.
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('job_chunks')}
        if 'ix_job_chunks_job_id' not in existing_indexes:
            op.create_index('ix_job_chunks_job_id', 'job_chunks', ['job_id'])
        if 'ix_job_chunks_status' not in existing_indexes:
            op.create_index('ix_job_chunks_status', 'job_chunks', ['status'])
        if 'idx_job_chunk_unique' not in existing_indexes:
            op.create_index('idx_job_chunk_unique', 'job_chunks', ['job_id', 'chunk_index'], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'job_chunks' in inspector.get_table_names():
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('job_chunks')}
        if 'idx_job_chunk_unique' in existing_indexes:
            op.drop_index('idx_job_chunk_unique', table_name='job_chunks')
        if 'ix_job_chunks_status' in existing_indexes:
            op.drop_index('ix_job_chunks_status', table_name='job_chunks')
        if 'ix_job_chunks_job_id' in existing_indexes:
            op.drop_index('ix_job_chunks_job_id', table_name='job_chunks')
        op.drop_table('job_chunks')

"""Add async processing and chunking fields to Job model

Revision ID: add_async_chunking_fields
Revises: e1b51492b2e1
Create Date: 2025-01-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_async_chunking_fields'
down_revision = 'e1b51492b2e1'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to jobs table
    op.add_column('jobs', sa.Column('page_count', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('chunk_size', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('total_chunks', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('completed_chunks', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('progress_percent', sa.Float(), nullable=True))
    op.add_column('jobs', sa.Column('parent_job_id', sa.Integer(), nullable=True))
    
    # Add foreign key for parent_job_id
    op.create_foreign_key('fk_jobs_parent_job_id', 'jobs', 'jobs', ['parent_job_id'], ['id'])
    op.create_index('ix_jobs_parent_job_id', 'jobs', ['parent_job_id'])
    
    # Set default values for existing jobs
    op.execute("UPDATE jobs SET total_chunks = 1 WHERE total_chunks IS NULL")
    op.execute("UPDATE jobs SET completed_chunks = 0 WHERE completed_chunks IS NULL")
    op.execute("UPDATE jobs SET progress_percent = 0.0 WHERE progress_percent IS NULL")


def downgrade():
    # Remove foreign key and index
    op.drop_index('ix_jobs_parent_job_id', table_name='jobs')
    op.drop_constraint('fk_jobs_parent_job_id', 'jobs', type_='foreignkey')
    
    # Remove columns
    op.drop_column('jobs', 'parent_job_id')
    op.drop_column('jobs', 'progress_percent')
    op.drop_column('jobs', 'completed_chunks')
    op.drop_column('jobs', 'total_chunks')
    op.drop_column('jobs', 'chunk_size')
    op.drop_column('jobs', 'page_count')

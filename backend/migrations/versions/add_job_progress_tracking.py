"""Add job progress tracking fields

Revision ID: add_job_progress_tracking
Revises: e1b51492b2e1
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_job_progress_tracking'
down_revision = 'e1b51492b2e1'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to jobs table
    op.add_column('jobs', sa.Column('total_chunks', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('completed_chunks', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('progress_percent', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('celery_task_id', sa.String(length=255), nullable=True))
    
    # Create index on celery_task_id
    op.create_index(op.f('ix_jobs_celery_task_id'), 'jobs', ['celery_task_id'], unique=False)
    
    # Set default values for existing rows
    op.execute("UPDATE jobs SET total_chunks = 0 WHERE total_chunks IS NULL")
    op.execute("UPDATE jobs SET completed_chunks = 0 WHERE completed_chunks IS NULL")
    op.execute("UPDATE jobs SET progress_percent = 0 WHERE progress_percent IS NULL")


def downgrade():
    # Remove index
    op.drop_index(op.f('ix_jobs_celery_task_id'), table_name='jobs')
    
    # Remove columns
    op.drop_column('jobs', 'celery_task_id')
    op.drop_column('jobs', 'progress_percent')
    op.drop_column('jobs', 'completed_chunks')
    op.drop_column('jobs', 'total_chunks')

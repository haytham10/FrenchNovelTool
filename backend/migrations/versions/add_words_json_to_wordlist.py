"""Add words_json column to word_lists table

Revision ID: vocab_coverage_v2
Revises: vocab_coverage_v1
Create Date: 2024-01-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'vocab_coverage_v2'
down_revision = 'vocab_coverage_v1'
branch_labels = None
depends_on = None


def upgrade():
    # Add words_json column to store full normalized word list
    op.add_column('word_lists', sa.Column('words_json', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('word_lists', 'words_json')

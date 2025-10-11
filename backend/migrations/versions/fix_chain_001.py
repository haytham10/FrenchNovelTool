"""fix_chain_001

Revision ID: fix_chain_001
Revises: vocab_coverage_v2
Create Date: 2025-10-10 06:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_chain_001'
down_revision = 'vocab_coverage_v2'
branch_labels = None
depends_on = None


def upgrade():
    # This is a stub migration to fix the broken chain
    # The actual migration was likely removed from the codebase
    # but is still referenced in the database
    pass


def downgrade():
    # This is a stub migration to fix the broken chain
    pass
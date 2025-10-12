"""Fix migration chain from vocab_coverage_v2

Revision ID: fix_chain_001
Revises: vocab_coverage_v2
Create Date: 2025-10-10 05:55:00.000000

This migration bridges from the old vocab_coverage_v2 to the new unified schema.
It's a no-op because the schema should already exist.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_chain_001'
down_revision = 'vocab_coverage_v2'  # The revision Railway is looking for
branch_labels = None
depends_on = None


def upgrade():
    # No-op: schema should already exist
    pass


def downgrade():
    # No-op
    pass

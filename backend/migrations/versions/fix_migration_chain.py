"""Fix migration chain from initial schema

Revision ID: fix_chain_001
Revises: 0299e3b2e149
Create Date: 2025-10-10 05:55:00.000000

This migration bridges from the initial schema to the new unified schema.
It's a no-op because the schema should already exist.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_chain_001'
down_revision = '0299e3b2e149'  # The initial schema revision
branch_labels = None
depends_on = None


def upgrade():
    # No-op: schema should already exist
    pass


def downgrade():
    # No-op
    pass

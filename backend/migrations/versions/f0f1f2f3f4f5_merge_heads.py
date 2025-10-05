"""merge heads

Revision ID: f0f1f2f3f4f5
Revises: c1d2e3f4g5h6, d2e3f4g5h6i7
Create Date: 2025-10-05 03:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f0f1f2f3f4f5'
down_revision = ('c1d2e3f4g5h6', 'd2e3f4g5h6i7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge revision to unify multiple heads. No DB changes.
    pass


def downgrade() -> None:
    # Downgrade would be complex in a branching history; keep no-op.
    pass

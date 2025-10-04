"""add sentences and chunk tracking to history

Revision ID: d2e3f4g5h6i7
Revises: e1b51492b2e1
Create Date: 2025-01-15 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd2e3f4g5h6i7'
down_revision = 'e1b51492b2e1'
branch_labels = None
depends_on = None


def upgrade():
    """Add sentences storage and chunk tracking fields to history table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Helper to check if column exists
    def column_exists(table_name: str, column_name: str) -> bool:
        try:
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            return column_name in columns
        except Exception:
            return False
    
    # Helper to check if index exists
    def index_exists(name: str) -> bool:
        try:
            return bool(bind.execute(sa.text("SELECT to_regclass(:iname)"), {'iname': f'public.{name}'}).scalar())
        except Exception:
            return False
    
    # Add new columns to history table (idempotent)
    columns_to_add = [
        ('sentences', postgresql.JSON(), {}),  # Array of {normalized: str, original: str}
        ('exported_to_sheets', sa.Boolean(), {'server_default': 'false', 'nullable': False}),
        ('export_sheet_url', sa.String(256), {}),
        ('chunk_ids', postgresql.JSON(), {}),  # Array of chunk IDs for drill-down
    ]
    
    for col_info in columns_to_add:
        col_name = col_info[0]
        col_type = col_info[1]
        kwargs = col_info[2]
        
        if not column_exists('history', col_name):
            op.add_column('history', sa.Column(col_name, col_type, **kwargs))
    
    # Create index for faster exported queries
    if not index_exists('idx_history_exported'):
        op.create_index('idx_history_exported', 'history', ['exported_to_sheets'])


def downgrade():
    """Remove sentences and chunk tracking fields from history table"""
    # Drop index
    op.drop_index('idx_history_exported', table_name='history')
    
    # Remove columns
    op.drop_column('history', 'chunk_ids')
    op.drop_column('history', 'export_sheet_url')
    op.drop_column('history', 'exported_to_sheets')
    op.drop_column('history', 'sentences')

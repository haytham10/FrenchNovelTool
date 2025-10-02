"""Add P1 feature fields

Revision ID: add_p1_feature_fields
Revises: 997f943cdd21
Create Date: 2025-01-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_p1_feature_fields'
down_revision = '997f943cdd21'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to history table
    with op.batch_alter_table('history', schema=None) as batch_op:
        batch_op.add_column(sa.Column('failed_step', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('error_code', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('error_details', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('processing_settings', sa.JSON(), nullable=True))

    # Add new columns to user_settings table
    with op.batch_alter_table('user_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('gemini_model', sa.String(length=50), nullable=True, server_default='balanced'))
        batch_op.add_column(sa.Column('ignore_dialogue', sa.Boolean(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('preserve_formatting', sa.Boolean(), nullable=True, server_default='1'))
        batch_op.add_column(sa.Column('fix_hyphenation', sa.Boolean(), nullable=True, server_default='1'))
        batch_op.add_column(sa.Column('min_sentence_length', sa.Integer(), nullable=True, server_default='3'))


def downgrade():
    # Remove columns from user_settings table
    with op.batch_alter_table('user_settings', schema=None) as batch_op:
        batch_op.drop_column('min_sentence_length')
        batch_op.drop_column('fix_hyphenation')
        batch_op.drop_column('preserve_formatting')
        batch_op.drop_column('ignore_dialogue')
        batch_op.drop_column('gemini_model')

    # Remove columns from history table
    with op.batch_alter_table('history', schema=None) as batch_op:
        batch_op.drop_column('processing_settings')
        batch_op.drop_column('error_details')
        batch_op.drop_column('error_code')
        batch_op.drop_column('failed_step')

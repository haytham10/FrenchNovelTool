"""Add authentication system

Revision ID: 6deaf3110825
Revises: 
Create Date: 2025-10-02 05:04:47.538599

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6deaf3110825'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table if not exists
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if 'users' not in insp.get_table_names():
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=True),
            sa.Column('picture', sa.String(length=512), nullable=True),
            sa.Column('google_id', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('last_login', sa.DateTime(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('email'),
            sa.UniqueConstraint('google_id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)

    # Ensure history table exists with user_id FK
    if 'history' not in insp.get_table_names():
        op.create_table(
            'history',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('original_filename', sa.String(length=128), nullable=True),
            sa.Column('processed_sentences_count', sa.Integer(), nullable=True),
            sa.Column('spreadsheet_url', sa.String(length=256), nullable=True),
            sa.Column('error_message', sa.String(length=512), nullable=True),
        )
        op.create_index(op.f('ix_history_user_id'), 'history', ['user_id'], unique=False)
    else:
        # Add user_id if missing
        existing_cols = [c['name'] for c in insp.get_columns('history')]
        if 'user_id' not in existing_cols:
            with op.batch_alter_table('history', schema=None) as batch_op:
                batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=False))
                batch_op.create_index(batch_op.f('ix_history_user_id'), ['user_id'], unique=False)
                batch_op.create_foreign_key('fk_history_user_id', 'users', ['user_id'], ['id'])

    # Ensure user_settings table exists with user_id FK
    if 'user_settings' not in insp.get_table_names():
        op.create_table(
            'user_settings',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
            sa.Column('sentence_length_limit', sa.Integer(), nullable=False, server_default=sa.text('8')),
            sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        )
        op.create_index(op.f('ix_user_settings_user_id'), 'user_settings', ['user_id'], unique=True)
    else:
        # Add user_id if missing
        existing_cols = [c['name'] for c in insp.get_columns('user_settings')]
        if 'user_id' not in existing_cols:
            with op.batch_alter_table('user_settings', schema=None) as batch_op:
                batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=False))
                batch_op.create_index(batch_op.f('ix_user_settings_user_id'), ['user_id'], unique=True)
                batch_op.create_foreign_key('fk_user_settings_user_id', 'users', ['user_id'], ['id'])


def downgrade():
    # Best-effort downgrade: drop dependent tables and indexes
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if 'user_settings' in insp.get_table_names():
        try:
            op.drop_index(op.f('ix_user_settings_user_id'), table_name='user_settings')
        except Exception:
            pass
        op.drop_table('user_settings')

    if 'history' in insp.get_table_names():
        try:
            op.drop_index(op.f('ix_history_user_id'), table_name='history')
        except Exception:
            pass
        op.drop_table('history')

    if 'users' in insp.get_table_names():
        try:
            op.drop_index(op.f('ix_users_google_id'), table_name='users')
        except Exception:
            pass
        try:
            op.drop_index(op.f('ix_users_email'), table_name='users')
        except Exception:
            pass
        op.drop_table('users')

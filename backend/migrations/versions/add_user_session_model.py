"""Add UserSession model for robust server-side session management

Revision ID: user_session_v1
Revises: fix_chain_001
Create Date: 2025-10-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'user_session_v1'
down_revision = 'fix_chain_001'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(length=128), nullable=False),
        sa.Column('refresh_token_jti', sa.String(length=128), nullable=False),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_activity', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient lookups
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_session_token'), 'user_sessions', ['session_token'], unique=True)
    op.create_index(op.f('ix_user_sessions_refresh_token_jti'), 'user_sessions', ['refresh_token_jti'], unique=True)
    op.create_index(op.f('ix_user_sessions_expires_at'), 'user_sessions', ['expires_at'], unique=False)
    op.create_index(op.f('ix_user_sessions_is_active'), 'user_sessions', ['is_active'], unique=False)


def downgrade():
    # Drop indexes first
    op.drop_index(op.f('ix_user_sessions_is_active'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_expires_at'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_refresh_token_jti'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_session_token'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    
    # Drop table
    op.drop_table('user_sessions')

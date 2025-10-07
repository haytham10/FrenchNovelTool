"""Add vocabulary coverage models (WordList, CoverageRun, CoverageAssignment)

Revision ID: vocab_coverage_v1
Revises: f0f1f2f3f4f5
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'vocab_coverage_v1'
down_revision = 'f0f1f2f3f4f5'
branch_labels = None
depends_on = None


def upgrade():
    # Create word_lists table
    op.create_table('word_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_ref', sa.String(length=512), nullable=True),
        sa.Column('normalized_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('canonical_samples', sa.JSON(), nullable=True),
        sa.Column('is_global_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_wordlist_owner_name', 'word_lists', ['owner_user_id', 'name'])
    op.create_index(op.f('ix_word_lists_is_global_default'), 'word_lists', ['is_global_default'])
    op.create_index(op.f('ix_word_lists_owner_user_id'), 'word_lists', ['owner_user_id'])

    # Create coverage_runs table
    op.create_table('coverage_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('wordlist_id', sa.Integer(), nullable=True),
        sa.Column('config_json', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('progress_percent', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('stats_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.String(length=512), nullable=True),
        sa.Column('celery_task_id', sa.String(length=155), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['wordlist_id'], ['word_lists.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_coverage_run_source', 'coverage_runs', ['source_type', 'source_id'])
    op.create_index('idx_coverage_run_user_status', 'coverage_runs', ['user_id', 'status'])
    op.create_index(op.f('ix_coverage_runs_celery_task_id'), 'coverage_runs', ['celery_task_id'])
    op.create_index(op.f('ix_coverage_runs_mode'), 'coverage_runs', ['mode'])
    op.create_index(op.f('ix_coverage_runs_source_id'), 'coverage_runs', ['source_id'])
    op.create_index(op.f('ix_coverage_runs_status'), 'coverage_runs', ['status'])
    op.create_index(op.f('ix_coverage_runs_user_id'), 'coverage_runs', ['user_id'])
    op.create_index(op.f('ix_coverage_runs_wordlist_id'), 'coverage_runs', ['wordlist_id'])

    # Create coverage_assignments table
    op.create_table('coverage_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('coverage_run_id', sa.Integer(), nullable=False),
        sa.Column('word_original', sa.String(length=255), nullable=True),
        sa.Column('word_key', sa.String(length=255), nullable=False),
        sa.Column('lemma', sa.String(length=255), nullable=True),
        sa.Column('matched_surface', sa.String(length=255), nullable=True),
        sa.Column('sentence_index', sa.Integer(), nullable=False),
        sa.Column('sentence_text', sa.Text(), nullable=False),
        sa.Column('sentence_score', sa.Float(), nullable=True),
        sa.Column('conflicts', sa.JSON(), nullable=True),
        sa.Column('manual_edit', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['coverage_run_id'], ['coverage_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_coverage_assignment_run_word', 'coverage_assignments', ['coverage_run_id', 'word_key'])
    op.create_index(op.f('ix_coverage_assignments_coverage_run_id'), 'coverage_assignments', ['coverage_run_id'])
    op.create_index(op.f('ix_coverage_assignments_word_key'), 'coverage_assignments', ['word_key'])

    # Extend user_settings table
    op.add_column('user_settings', sa.Column('default_wordlist_id', sa.Integer(), nullable=True))
    op.add_column('user_settings', sa.Column('coverage_defaults_json', sa.JSON(), nullable=True))
    op.create_foreign_key('fk_user_settings_default_wordlist', 'user_settings', 'word_lists', ['default_wordlist_id'], ['id'])


def downgrade():
    # Drop foreign key and columns from user_settings
    op.drop_constraint('fk_user_settings_default_wordlist', 'user_settings', type_='foreignkey')
    op.drop_column('user_settings', 'coverage_defaults_json')
    op.drop_column('user_settings', 'default_wordlist_id')

    # Drop coverage_assignments table
    op.drop_index(op.f('ix_coverage_assignments_word_key'), table_name='coverage_assignments')
    op.drop_index(op.f('ix_coverage_assignments_coverage_run_id'), table_name='coverage_assignments')
    op.drop_index('idx_coverage_assignment_run_word', table_name='coverage_assignments')
    op.drop_table('coverage_assignments')

    # Drop coverage_runs table
    op.drop_index(op.f('ix_coverage_runs_wordlist_id'), table_name='coverage_runs')
    op.drop_index(op.f('ix_coverage_runs_user_id'), table_name='coverage_runs')
    op.drop_index(op.f('ix_coverage_runs_status'), table_name='coverage_runs')
    op.drop_index(op.f('ix_coverage_runs_source_id'), table_name='coverage_runs')
    op.drop_index(op.f('ix_coverage_runs_mode'), table_name='coverage_runs')
    op.drop_index(op.f('ix_coverage_runs_celery_task_id'), table_name='coverage_runs')
    op.drop_index('idx_coverage_run_user_status', table_name='coverage_runs')
    op.drop_index('idx_coverage_run_source', table_name='coverage_runs')
    op.drop_table('coverage_runs')

    # Drop word_lists table
    op.drop_index(op.f('ix_word_lists_owner_user_id'), table_name='word_lists')
    op.drop_index(op.f('ix_word_lists_is_global_default'), table_name='word_lists')
    op.drop_index('idx_wordlist_owner_name', table_name='word_lists')
    op.drop_table('word_lists')

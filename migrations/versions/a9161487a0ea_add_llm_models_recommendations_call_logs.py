"""add_llm_models_recommendations_call_logs

Revision ID: a9161487a0ea
Revises: 76f3d8327f1a
Create Date: 2025-09-08 14:03:09.272633

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9161487a0ea'
down_revision: Union[str, None] = '76f3d8327f1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create llm_recommendations table
    op.create_table('llm_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=False),
        sa.Column('course_id', sa.String(), nullable=False),
        sa.Column('cache_key', sa.String(), nullable=False),
        sa.Column('data_version', sa.String(), nullable=False),
        sa.Column('recommendations_json', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_recommendations_student_id'), 'llm_recommendations', ['student_id'], unique=False)
    op.create_index(op.f('ix_llm_recommendations_course_id'), 'llm_recommendations', ['course_id'], unique=False)
    op.create_index(op.f('ix_llm_recommendations_cache_key'), 'llm_recommendations', ['cache_key'], unique=True)
    op.create_index(op.f('ix_llm_recommendations_data_version'), 'llm_recommendations', ['data_version'], unique=False)
    op.create_index(op.f('ix_llm_recommendations_expires_at'), 'llm_recommendations', ['expires_at'], unique=False)

    # Create llm_call_logs table
    op.create_table('llm_call_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=True),
        sa.Column('course_id', sa.String(), nullable=True),
        sa.Column('request_type', sa.String(), nullable=False),
        sa.Column('prompt_hash', sa.String(), nullable=False),
        sa.Column('request_tokens', sa.Integer(), nullable=True),
        sa.Column('response_tokens', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('model_used', sa.String(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('response_preview', sa.String(), nullable=True),
        sa.Column('recommendations_count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_call_logs_student_id'), 'llm_call_logs', ['student_id'], unique=False)
    op.create_index(op.f('ix_llm_call_logs_course_id'), 'llm_call_logs', ['course_id'], unique=False)
    op.create_index(op.f('ix_llm_call_logs_request_type'), 'llm_call_logs', ['request_type'], unique=False)
    op.create_index(op.f('ix_llm_call_logs_prompt_hash'), 'llm_call_logs', ['prompt_hash'], unique=False)
    op.create_index(op.f('ix_llm_call_logs_status'), 'llm_call_logs', ['status'], unique=False)
    op.create_index(op.f('ix_llm_call_logs_created_at'), 'llm_call_logs', ['created_at'], unique=False)

    # Create llm_feedback table
    op.create_table('llm_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recommendation_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=False),
        sa.Column('course_id', sa.String(), nullable=False),
        sa.Column('feedback_type', sa.String(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback_text', sa.String(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=True),
        sa.Column('edited_recommendation', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_feedback_recommendation_id'), 'llm_feedback', ['recommendation_id'], unique=False)
    op.create_index(op.f('ix_llm_feedback_student_id'), 'llm_feedback', ['student_id'], unique=False)
    op.create_index(op.f('ix_llm_feedback_course_id'), 'llm_feedback', ['course_id'], unique=False)
    op.create_index(op.f('ix_llm_feedback_feedback_type'), 'llm_feedback', ['feedback_type'], unique=False)
    op.create_index(op.f('ix_llm_feedback_created_by'), 'llm_feedback', ['created_by'], unique=False)

    # Create llm_usage_stats table
    op.create_table('llm_usage_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=False),
        sa.Column('successful_requests', sa.Integer(), nullable=False),
        sa.Column('failed_requests', sa.Integer(), nullable=False),
        sa.Column('total_tokens_used', sa.Integer(), nullable=False),
        sa.Column('total_cost_usd', sa.Float(), nullable=False),
        sa.Column('unique_students', sa.Integer(), nullable=False),
        sa.Column('unique_courses', sa.Integer(), nullable=False),
        sa.Column('avg_response_time_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_usage_stats_date'), 'llm_usage_stats', ['date'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_llm_usage_stats_date'), table_name='llm_usage_stats')
    op.drop_table('llm_usage_stats')
    op.drop_index(op.f('ix_llm_feedback_created_by'), table_name='llm_feedback')
    op.drop_index(op.f('ix_llm_feedback_feedback_type'), table_name='llm_feedback')
    op.drop_index(op.f('ix_llm_feedback_course_id'), table_name='llm_feedback')
    op.drop_index(op.f('ix_llm_feedback_student_id'), table_name='llm_feedback')
    op.drop_index(op.f('ix_llm_feedback_recommendation_id'), table_name='llm_feedback')
    op.drop_table('llm_feedback')
    op.drop_index(op.f('ix_llm_call_logs_created_at'), table_name='llm_call_logs')
    op.drop_index(op.f('ix_llm_call_logs_status'), table_name='llm_call_logs')
    op.drop_index(op.f('ix_llm_call_logs_prompt_hash'), table_name='llm_call_logs')
    op.drop_index(op.f('ix_llm_call_logs_request_type'), table_name='llm_call_logs')
    op.drop_index(op.f('ix_llm_call_logs_course_id'), table_name='llm_call_logs')
    op.drop_index(op.f('ix_llm_call_logs_student_id'), table_name='llm_call_logs')
    op.drop_table('llm_call_logs')
    op.drop_index(op.f('ix_llm_recommendations_expires_at'), table_name='llm_recommendations')
    op.drop_index(op.f('ix_llm_recommendations_data_version'), table_name='llm_recommendations')
    op.drop_index(op.f('ix_llm_recommendations_cache_key'), table_name='llm_recommendations')
    op.drop_index(op.f('ix_llm_recommendations_course_id'), table_name='llm_recommendations')
    op.drop_index(op.f('ix_llm_recommendations_student_id'), table_name='llm_recommendations')
    op.drop_table('llm_recommendations')

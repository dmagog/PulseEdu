"""Add ML monitoring tables

Revision ID: bbe13e760a0f
Revises: 5e521b26e602
Create Date: 2025-09-10 17:46:15.211675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbe13e760a0f'
down_revision: Union[str, None] = 'a9161487a0ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create clustering_quality_metrics table
    op.create_table('clustering_quality_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('algorithm_used', sa.String(), nullable=False),
        sa.Column('algorithm_params', sa.String(), nullable=False),
        sa.Column('silhouette_score', sa.Float(), nullable=False),
        sa.Column('calinski_harabasz_score', sa.Float(), nullable=False),
        sa.Column('combined_score', sa.Float(), nullable=False),
        sa.Column('n_clusters', sa.Integer(), nullable=False),
        sa.Column('total_students', sa.Integer(), nullable=False),
        sa.Column('clustered_students', sa.Integer(), nullable=False),
        sa.Column('processing_time_seconds', sa.Float(), nullable=False),
        sa.Column('memory_usage_mb', sa.Float(), nullable=False),
        sa.Column('import_job_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clustering_quality_metrics_course_id'), 'clustering_quality_metrics', ['course_id'], unique=False)
    op.create_index(op.f('ix_clustering_quality_metrics_import_job_id'), 'clustering_quality_metrics', ['import_job_id'], unique=False)
    op.create_index('ix_clustering_quality_metrics_course_id_created_at', 'clustering_quality_metrics', ['course_id', 'created_at'], unique=False)
    op.create_index('ix_clustering_quality_metrics_algorithm_used_created_at', 'clustering_quality_metrics', ['algorithm_used', 'created_at'], unique=False)

    # Create ml_model_performance table
    op.create_table('ml_model_performance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('algorithm_name', sa.String(), nullable=False),
        sa.Column('algorithm_params', sa.String(), nullable=False),
        sa.Column('avg_silhouette_score', sa.Float(), nullable=False),
        sa.Column('avg_calinski_harabasz_score', sa.Float(), nullable=False),
        sa.Column('avg_combined_score', sa.Float(), nullable=False),
        sa.Column('avg_processing_time', sa.Float(), nullable=False),
        sa.Column('avg_memory_usage', sa.Float(), nullable=False),
        sa.Column('total_runs', sa.Integer(), nullable=False),
        sa.Column('successful_runs', sa.Integer(), nullable=False),
        sa.Column('failed_runs', sa.Integer(), nullable=False),
        sa.Column('quality_threshold', sa.Float(), nullable=False),
        sa.Column('threshold_met_count', sa.Integer(), nullable=False),
        sa.Column('first_used', sa.DateTime(), nullable=False),
        sa.Column('last_used', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ml_model_performance_algorithm_name'), 'ml_model_performance', ['algorithm_name'], unique=False)
    op.create_index('ix_ml_model_performance_algorithm_name_updated_at', 'ml_model_performance', ['algorithm_name', 'updated_at'], unique=False)

    # Create clustering_alerts table
    op.create_table('clustering_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(), nullable=False),
        sa.Column('alert_level', sa.String(), nullable=False),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('details', sa.String(), nullable=False),
        sa.Column('silhouette_score', sa.Float(), nullable=True),
        sa.Column('combined_score', sa.Float(), nullable=True),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.String(), nullable=True),
        sa.Column('import_job_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clustering_alerts_course_id'), 'clustering_alerts', ['course_id'], unique=False)
    op.create_index(op.f('ix_clustering_alerts_import_job_id'), 'clustering_alerts', ['import_job_id'], unique=False)
    op.create_index('ix_clustering_alerts_course_id_created_at', 'clustering_alerts', ['course_id', 'created_at'], unique=False)
    op.create_index('ix_clustering_alerts_alert_type_resolved', 'clustering_alerts', ['alert_type', 'resolved'], unique=False)
    op.create_index('ix_clustering_alerts_alert_level_resolved', 'clustering_alerts', ['alert_level', 'resolved'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('clustering_alerts')
    op.drop_table('ml_model_performance')
    op.drop_table('clustering_quality_metrics')

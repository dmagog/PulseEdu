"""Merge ML monitoring and user course assignments

Revision ID: 65656932b26f
Revises: 5e521b26e602, bbe13e760a0f
Create Date: 2025-09-10 17:47:12.349959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65656932b26f'
down_revision: Union[str, None] = ('5e521b26e602', 'bbe13e760a0f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

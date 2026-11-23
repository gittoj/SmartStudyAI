"""stored files: keep worksheet file bytes in Postgres instead of local disk

Revision ID: b7d41c2e9a10
Revises: ece86fc5c7d2
Create Date: 2026-11-23 12:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7d41c2e9a10'
down_revision: Union[str, None] = 'ece86fc5c7d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('stored_files',
    sa.Column('key', sa.String(length=200), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )


def downgrade() -> None:
    op.drop_table('stored_files')

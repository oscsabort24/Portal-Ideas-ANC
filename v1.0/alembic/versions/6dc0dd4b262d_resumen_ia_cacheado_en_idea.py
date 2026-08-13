"""resumen ia cacheado en idea

Revision ID: 6dc0dd4b262d
Revises: 3f8b6d2a91ec
Create Date: 2026-08-13 10:31:13.179266

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6dc0dd4b262d'
down_revision: Union[str, Sequence[str], None] = '3f8b6d2a91ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('ideas', sa.Column('resumen_ia', sa.Unicode(), nullable=True))
    op.add_column('ideas', sa.Column('resumen_ia_generado_en', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ideas', 'resumen_ia_generado_en')
    op.drop_column('ideas', 'resumen_ia')

"""historial de retroalimentacion de revision

Revision ID: 2ee467d36546
Revises: d284eb86257d
Create Date: 2026-07-14 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ee467d36546'
down_revision: Union[str, Sequence[str], None] = 'd284eb86257d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('historial_retroalimentacion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('revision_id', sa.Integer(), nullable=False),
    sa.Column('retroalimentacion', sa.Text(), nullable=False),
    sa.Column('creada_por_id', sa.Integer(), nullable=False),
    sa.Column('creada_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['creada_por_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['revision_id'], ['revision_ideas.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('historial_retroalimentacion')

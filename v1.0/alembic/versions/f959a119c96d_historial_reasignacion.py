"""historial de reasignacion de revisor

Revision ID: f959a119c96d
Revises: f196da5a6b27
Create Date: 2026-07-15 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f959a119c96d'
down_revision: Union[str, Sequence[str], None] = 'f196da5a6b27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('historial_reasignacion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('revision_id', sa.Integer(), nullable=False),
    sa.Column('revisor_anterior_id', sa.Integer(), nullable=False),
    sa.Column('revisor_nuevo_id', sa.Integer(), nullable=False),
    sa.Column('creada_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['revision_id'], ['revision_ideas.id'], ),
    sa.ForeignKeyConstraint(['revisor_anterior_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['revisor_nuevo_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('historial_reasignacion')

"""creado_en en revision_ideas

Revision ID: a6ebfa06c875
Revises: e47dea031bf6
Create Date: 2026-07-14 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6ebfa06c875'
down_revision: Union[str, Sequence[str], None] = 'e47dea031bf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Se agrega nullable=True primero porque SQL Server no permite añadir una
    # columna NOT NULL sin default a una tabla con filas existentes.
    op.add_column(
        'revision_ideas',
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=True),
    )

    revision_ideas = sa.table(
        'revision_ideas',
        sa.column('id', sa.Integer),
        sa.column('fecha_asignacion', sa.DateTime(timezone=True)),
        sa.column('creado_en', sa.DateTime(timezone=True)),
    )
    # Backfill: hoy solo existe una fila real en revision_ideas (idea_id=6,
    # ya aprobada, con fecha_asignacion poblada) y NINGUNA en
    # pendiente_asignacion. Usamos fecha_asignacion como aproximación de
    # creado_en porque refleja cuándo se activó esa revisión — es razonable
    # SOLO en este contexto puntual. Si en una migración futura existen filas
    # reales en pendiente_asignacion (fecha_asignacion NULL), NO asumir este
    # mismo criterio sin revisarlo: no hay fecha de creación real de la que
    # derivarlo para esas filas.
    op.execute(
        revision_ideas.update()
        .where(revision_ideas.c.fecha_asignacion.isnot(None))
        .values(creado_en=revision_ideas.c.fecha_asignacion)
    )
    op.execute(
        revision_ideas.update()
        .where(revision_ideas.c.creado_en.is_(None))
        .values(creado_en=sa.func.now())
    )

    op.alter_column(
        'revision_ideas', 'creado_en',
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('CURRENT_TIMESTAMP'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('revision_ideas', 'creado_en')

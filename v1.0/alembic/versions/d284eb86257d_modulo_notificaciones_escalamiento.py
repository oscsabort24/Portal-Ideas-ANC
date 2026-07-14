"""modulo notificaciones - escalamiento por inactividad

Revision ID: d284eb86257d
Revises: a6ebfa06c875
Create Date: 2026-07-14 15:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd284eb86257d'
down_revision: Union[str, Sequence[str], None] = 'a6ebfa06c875'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('configuraciones_escalamiento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('etapa', sa.Enum('revision', 'clasificacion', 'comites', name='etapa_escalamiento_config'), nullable=False),
    sa.Column('plazo_dias', sa.Integer(), nullable=True),
    sa.Column('responsable_id', sa.Integer(), nullable=True),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['responsable_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('etapa')
    )

    op.create_table('notificaciones_escalamiento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('etapa', sa.Enum('revision', 'clasificacion', 'comites', name='etapa_escalamiento_notificacion'), nullable=False),
    sa.Column('idea_id', sa.Integer(), nullable=False),
    sa.Column('responsable_id', sa.Integer(), nullable=True),
    sa.Column('dias_transcurridos', sa.Integer(), nullable=False),
    sa.Column('generada_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('enviada', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['idea_id'], ['ideas.id'], ),
    sa.ForeignKeyConstraint(['responsable_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )

    # Seed: una fila por etapa, ambas columnas configurables en NULL — las
    # 3 etapas nacen "sin configurar" hasta que el admin les asigne plazo
    # y responsable. Ningún plazo se inventa aquí.
    configuraciones_escalamiento = sa.table(
        'configuraciones_escalamiento',
        sa.column('etapa', sa.Enum('revision', 'clasificacion', 'comites', name='etapa_escalamiento_config')),
        sa.column('plazo_dias', sa.Integer),
        sa.column('responsable_id', sa.Integer),
    )
    op.bulk_insert(
        configuraciones_escalamiento,
        [
            {'etapa': 'revision', 'plazo_dias': None, 'responsable_id': None},
            {'etapa': 'clasificacion', 'plazo_dias': None, 'responsable_id': None},
            {'etapa': 'comites', 'plazo_dias': None, 'responsable_id': None},
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('notificaciones_escalamiento')
    op.drop_table('configuraciones_escalamiento')

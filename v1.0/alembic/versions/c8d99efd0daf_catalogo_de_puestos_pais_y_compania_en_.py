"""catalogo de puestos, pais y compania en usuario

Revision ID: c8d99efd0daf
Revises: 9f4557192f21
Create Date: 2026-07-14 13:07:31.359167

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d99efd0daf'
down_revision: Union[str, Sequence[str], None] = '9f4557192f21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('puestos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=200), nullable=False),
    sa.Column('departamento_id', sa.Integer(), nullable=False),
    sa.Column('es_unico_por_pais', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['departamento_id'], ['departamentos.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nombre', 'departamento_id', name='uq_puesto_nombre_departamento')
    )

    # server_default temporal: ya existen 2 usuarios de prueba en la tabla.
    # CR / ANC_CAR son placeholders — corregir manualmente por la UI el
    # pais/compania real de esos 2 usuarios después de esta migración.
    op.add_column(
        'usuarios',
        sa.Column(
            'pais', sa.Enum('CR', 'GT', 'NI', 'PE', name='pais_usuario'),
            server_default='CR', nullable=False,
        ),
    )
    op.add_column(
        'usuarios',
        sa.Column(
            'compania', sa.Enum('ANC_CAR', 'RENTING', 'RENTAS_INT', name='compania_usuario'),
            server_default='ANC_CAR', nullable=False,
        ),
    )
    op.alter_column('usuarios', 'pais', server_default=None)
    op.alter_column('usuarios', 'compania', server_default=None)

    op.add_column('usuarios', sa.Column('puesto_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_usuarios_puesto_id', 'usuarios', 'puestos', ['puesto_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_usuarios_puesto_id', 'usuarios', type_='foreignkey')
    op.drop_column('usuarios', 'puesto_id')
    op.drop_column('usuarios', 'compania')
    op.drop_column('usuarios', 'pais')
    op.drop_table('puestos')

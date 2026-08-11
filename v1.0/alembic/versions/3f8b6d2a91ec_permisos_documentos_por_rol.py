"""permisos documentos por rol

Revision ID: 3f8b6d2a91ec
Revises: 7e2c4a91b3f0
Create Date: 2026-07-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f8b6d2a91ec'
down_revision: Union[str, Sequence[str], None] = '7e2c4a91b3f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Roles que pueden tener fila en esta tabla — admin queda fuera a propósito
# (siempre puede generar cualquier tipo, ver documentos/router.py:_puede_generar_tipo).
ROLES_CONFIGURABLES = ["colaborador", "encargado_area", "gerente"]
TIPOS_DOCUMENTO = ["charter", "bpmn", "onepager", "raci", "bmc", "business_case"]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'permisos_documentos_rol',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rol', sa.Enum('colaborador', 'encargado_area', 'gerente', 'admin', name='rol_usuario'), nullable=False),
        sa.Column('tipo_documento', sa.Enum('charter', 'bpmn', 'onepager', 'raci', 'bmc', 'business_case', name='tipo_documento'), nullable=False),
        sa.Column('permitido', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rol', 'tipo_documento', name='uq_permiso_rol_tipo_documento'),
    )

    # Semilla: "One Pager" habilitado para los 3 roles configurables, todo
    # lo demás deshabilitado hasta que el admin lo configure manualmente
    # desde ConfiguracionDocumentosView.
    tabla = sa.table(
        'permisos_documentos_rol',
        sa.column('rol', sa.String),
        sa.column('tipo_documento', sa.String),
        sa.column('permitido', sa.Boolean),
    )
    op.bulk_insert(
        tabla,
        [
            {"rol": rol, "tipo_documento": tipo, "permitido": tipo == "onepager"}
            for rol in ROLES_CONFIGURABLES
            for tipo in TIPOS_DOCUMENTO
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('permisos_documentos_rol')

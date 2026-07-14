"""modulo documentos - documentos generados al aprobar por cab

Revision ID: f196da5a6b27
Revises: 2ee467d36546
Create Date: 2026-07-14 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f196da5a6b27'
down_revision: Union[str, Sequence[str], None] = '2ee467d36546'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('documentos_generados',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('idea_id', sa.Integer(), nullable=False),
    sa.Column('tipo_documento', sa.Enum('charter', 'bpmn', 'onepager', 'raci', 'bmc', 'business_case', name='tipo_documento'), nullable=False),
    sa.Column('contenido', sa.Text(), nullable=False),
    sa.Column('ruta_archivo', sa.String(length=500), nullable=False),
    sa.Column('generado_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['idea_id'], ['ideas.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('idea_id', 'tipo_documento', name='uq_documento_idea_tipo'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('documentos_generados')

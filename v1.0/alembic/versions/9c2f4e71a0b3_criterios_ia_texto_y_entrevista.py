"""criterios de IA: de documento subido a texto editable, + tipo entrevista con scoping por departamento

Revision ID: 9c2f4e71a0b3
Revises: 4d81f6c93a52
Create Date: 2026-08-18

CONTEXTO: ver diseno-pendiente/cascada-revisor-y-criterios-texto.md.preview,
sección 2 (diseño aprobado). Reemplaza `documentos_criterio` (archivo
subido, PIN, versionado) por `criterios_ia` (texto puro, mismo PIN, mismo
versionado, sin archivo), y agrega el tipo 'entrevista' al enum, con
scoping opcional por departamento (departamento_id NULL = default
aplicado a los 18 departamentos salvo excepción).

SIN PRESERVACIÓN DE DATOS A PROPÓSITO: los documentos_criterio existentes
son de prueba, sin contenido de negocio real (confirmado por el usuario)
— esta migración DROPEA la tabla vieja en vez de migrar sus filas.
"""
from alembic import op
import sqlalchemy as sa

revision = "9c2f4e71a0b3"
down_revision = "4d81f6c93a52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("documentos_criterio")

    op.create_table(
        "criterios_ia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tipo",
            sa.Enum("clasificacion", "asignacion_revisor", "entrevista", name="tipo_criterio"),
            nullable=False,
        ),
        sa.Column("departamento_id", sa.Integer(), sa.ForeignKey("departamentos.id"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("contenido", sa.Unicode(), nullable=False),
        sa.Column("descripcion", sa.Unicode(length=500), nullable=True),
        sa.Column("creado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "tipo", "departamento_id", "version", name="uq_criterio_ia_tipo_departamento_version"
        ),
    )


def downgrade() -> None:
    """ADVERTENCIA DE PÉRDIDA DE DATOS: recrea documentos_criterio VACÍA.
    Cualquier criterio de texto guardado en criterios_ia (incluidas todas
    las excepciones por departamento del tipo 'entrevista', sin
    equivalente en el esquema viejo) se pierde al hacer este downgrade."""
    op.drop_table("criterios_ia")

    op.create_table(
        "documentos_criterio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tipo", sa.Enum("clasificacion", "asignacion_revisor", name="tipo_criterio"), nullable=False
        ),
        sa.Column("nombre_archivo", sa.Unicode(length=300), nullable=False),
        sa.Column("ruta_archivo", sa.Unicode(length=500), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("contenido", sa.Unicode(), nullable=True),
        sa.Column("descripcion", sa.Unicode(length=500), nullable=True),
        sa.Column("actualizado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subido_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("subido_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tipo", "version", name="uq_documento_criterio_tipo_version"),
    )

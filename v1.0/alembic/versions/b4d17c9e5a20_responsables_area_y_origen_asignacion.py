"""responsables_area + origen_asignacion — asignación determinística por área

Revision ID: b4d17c9e5a20
Revises: 9c2f4e71a0b3
Create Date: 2026-08-19

Dos cambios:

1. Tabla `responsables_area`: mapeo determinístico área -> persona. Nace
   VACÍA y, a propósito, NO se activa todavía en el código
   (revision/service.py:_buscar_encargado_activo sigue resolviendo por
   departamento+rol, no por esta tabla) — falta la carga con los datos
   reales del negocio. La tabla queda lista para cuando exista ese seed.

2. Columna `origen_asignacion` en `revision_ideas`, NOT NULL. Se agrega en
   tres pasos porque la tabla ya tiene filas y SQL Server rechaza un
   ALTER ADD NOT NULL sin default sobre una tabla poblada.
"""
from alembic import op
import sqlalchemy as sa

revision = "b4d17c9e5a20"
down_revision = "9c2f4e71a0b3"
branch_labels = None
depends_on = None

ORIGEN_ASIGNACION = sa.Enum(
    "mapeo_area",
    "fallback_departamento_autor",
    "manual",
    "sin_asignar",
    name="origen_asignacion",
)

PAIS_RESPONSABLE = sa.Enum("CR", "GT", "NI", "PE", name="pais_responsable_area")
COMPANIA_RESPONSABLE = sa.Enum("ANC_CAR", "RENTING", "RENTAS_INT", name="compania_responsable_area")


def upgrade() -> None:
    op.create_table(
        "responsables_area",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("departamento_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("prioridad", sa.Integer(), nullable=False),
        sa.Column("pais", PAIS_RESPONSABLE, nullable=True),
        sa.Column("compania", COMPANIA_RESPONSABLE, nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("vigente_desde", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vigente_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["departamento_id"], ["departamentos.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "departamento_id", "pais", "compania", "prioridad",
            name="uq_responsable_area_depto_pais_compania_prioridad",
        ),
    )
    op.create_index(
        "ix_responsable_area_depto_prioridad", "responsables_area", ["departamento_id", "prioridad"]
    )

    op.add_column("revision_ideas", sa.Column("origen_asignacion", ORIGEN_ASIGNACION, nullable=True))
    op.execute(
        """
        UPDATE revision_ideas
           SET origen_asignacion =
                CASE
                    WHEN revisor_id IS NULL THEN 'sin_asignar'
                    WHEN departamento_sugerido_ia_id IS NOT NULL THEN 'mapeo_area'
                    ELSE 'fallback_departamento_autor'
                END
        """
    )
    op.alter_column("revision_ideas", "origen_asignacion", existing_type=ORIGEN_ASIGNACION, nullable=False)


def downgrade() -> None:
    op.drop_column("revision_ideas", "origen_asignacion")
    op.drop_index("ix_responsable_area_depto_prioridad", table_name="responsables_area")
    op.drop_table("responsables_area")
